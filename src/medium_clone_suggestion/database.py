
import os
import json
import time
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional, Tuple, Set

# Third-party libraries (ensure these are in your pyproject.toml/requirements.txt)
from supabase import create_client, Client
from dotenv import load_dotenv
from bs4 import BeautifulSoup # For cleaning HTML in mock data if needed
import hashlib
import json
import random
from medium_clone_suggestion.logger import get_logger

logger = get_logger(__name__)

# Load environment variables from .env file
load_dotenv()

# --- Configuration ---
SUPABASE_URL = os.environ.get("SUPABASE_URL", "YOUR_SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "YOUR_SUPABASE_KEY")
MOCK_DATA_FILE = "testing.json"
MOCK_DATA_FETCH_LIMIT = 10 # How many items per table to fetch for mock data
CACHE_EXPIRY_HOURS = 8 # For caching mechanism (Placeholder - not implemented in this version)
RECENT_ACTIVITY_HOURS = 8 # For periodic user processing



def rate_limited(fn):
    def wrapper(self, *a, **k):
        self._rate_limit()
        return fn(self, *a, **k)
    return wrapper

class DatabaseManager:
    def __init__(self):
        self.client = create_client(
            os.getenv('SUPABASE_URL'),
            os.getenv('SUPABASE_KEY')
        )
        self.last_request_time = datetime.min.replace(tzinfo=timezone.utc)
        self.min_request_interval = timedelta(milliseconds=100)

    def _rate_limit(self):
        now = datetime.now(timezone.utc)
        elapsed = now - self.last_request_time
        if elapsed < self.min_request_interval:
            time.sleep((self.min_request_interval - elapsed).total_seconds())
        self.last_request_time = now

    # Article operations
    @rate_limited
    def fetch_uncategorized_articles(self, limit: int = 100) -> List[Dict]:
        response = self.client.table('posts')\
            .select('postid, title, content')\
            .eq('isCategorized', False)\
            .limit(limit)\
            .execute()
        return response.data
    
    
    @rate_limited
    def update_article_metadata(self, postid: str, metadata: Dict) -> bool:
        update_response = self.client.table('posts')\
            .update({'isCategorized': True, 'field': metadata.get('field')})\
            .eq('postid', postid)\
            .execute()

        metadata['postid'] = postid
        metadata_response = self.client.table('article_metadata')\
            .upsert(metadata, on_conflict='postid')\
            .execute()

        return len(update_response.data) > 0 and len(metadata_response.data) > 0
    
    def update_processed(self, articles: List[Dict]) -> List[Dict]:
        errors = []
        for art in articles:
            postid = art['postid']
            # build metadata payload
            metadata = {
                'postid':  postid,
                'keywords': art.get('keywords', []),
                'topics':  art.get('topics', []),
                'entities': art.get('entities', []),
                'summary': art.get('summary', ' ')
            }
            print(f"saving field!!! {art.get('field', 'Unknown')}")
            # 1) mark as categorized
            upd = self.client.table('posts')\
                .update({'isCategorized': True, 'field': art.get('field', 'Unknown')})\
                .eq('postid', postid)\
                .execute()

            # 2) upsert metadata
            meta = self.client.table('article_metadata')\
                .upsert(metadata, on_conflict="postid")\
                .execute()

            # collect errors
            upd_err = None
            if getattr(upd, 'status_code', 200) >= 300:
                upd_json = upd.json() if hasattr(upd, 'json') else {}
                upd_err = upd_json.get('error') or f"HTTP {upd.status_code}"
            
            meta_err = None
            if getattr(meta, 'status_code', 200) >= 300:
                meta_json = meta.json() if hasattr(meta, 'json') else {}
                meta_err = meta_json.get('error') or f"HTTP {meta.status_code}"

            if upd_err or meta_err:
                errors.append({
                    'postid':         postid,
                    'update_error':   upd_err,
                    'metadata_error': meta_err
                })

        # dump errors.json if any
        if errors:
            with open('errors.json', 'w') as f:
                json.dump(errors, f, indent=2)

        return errors
    # User operations
    @rate_limited
    def get_user_activity(self, user_id: str, max_days: int = 7) -> Dict:
        cutoff = datetime.now(timezone.utc) - timedelta(days=max_days)
        history = self.client.table('history')\
            .select('postid, created_at')\
            .eq('userid', user_id)\
            .gt('created_at', cutoff)\
            .execute().data
        
        engagements = self.client.table('engagements')\
            .select('postid, segment, created_at')\
            .eq('userid', user_id)\
            .gt('created_at', cutoff)\
            .execute().data
        
        ratings = self.client.table('article_ratings')\
            .select('postid, rating, created_at')\
            .eq('userid', user_id)\
            .gt('created_at', cutoff)\
            .execute().data

        return {
          'history': [{'postid': h['postid'], 'created_at': h['created_at']} for h in history],
            'engagements': [{'postid': e['postid'], 'segment': e['segment'], 'created_at': e['created_at']} for e in engagements],
            'ratings': [{'postid': r['postid'], 'rating': r['rating'], 'created_at': r['created_at']} for r in ratings]
        }
        
    @rate_limited
    def fetch_active_users(self, limit: int, max_days: int) -> List[str]:
        self._rate_limit()
        cutoff = (datetime.now(timezone.utc)
                - timedelta(days=max_days)).isoformat()

        try:
            response = self.client.rpc(
                'fetch_user_activities',
                {'cutoff': cutoff}
            ).execute()
            activities = response.data or []
        except Exception as e:
            logger.error(f"Error fetching active users via RPC: {e}")
            return []

        # Extract distinct user IDs
        user_ids = {row['userid'] for row in activities if row.get('userid')}
        return list(user_ids)
    
    
    def get_user_profile_last_updated(self, user_id: str) -> str:
        resp = self.client\
            .from_("user_profile_interests")\
            .select("last_updated")\
            .eq("userid", user_id)\
            .single()\
            .execute()
        return resp.data.get("last_updated") if resp.data else None
    
    def get_user_activities_since(self, user_id: str, since_iso: str):
        # re‐use your RPC but pass cutoff=since_iso AND filter by userid
        resp = self.client.rpc(
            "fetch_user_activities", {"cutoff": since_iso}
        ).execute()
        return [a for a in (resp.data or []) if a.get("userid")==user_id]
    
    def update_user_profile_last_updated(self, user_id, ts):
        self.client.table('user_profile_interests')\
            .update({'last_updated': ts.isoformat()})\
            .eq('userid', user_id).execute()

    # Recommendation operations
    @rate_limited
    def get_recommendations(self, user_id: str, field: str = 'any', limit: int = 10) -> List[Dict]:
        query = self.client.table('posts')\
            .select('*, article_metadata(*)')\
            .eq('isCategorized', True)\
            .limit(limit)
        
        if field != 'any':
            query = query.eq('field', field)
        
        # Exclude viewed posts
        viewed_posts = self.get_user_history(user_id)
        if viewed_posts:
            query = query.not_.in_('postid', viewed_posts)
        
        response = query.execute()
        return response.data

    # User interest management
    @rate_limited
    def update_user_interests(self, user_id: str, interests: Dict) -> bool:
        print(f" {interests}")
        response = self.client.table('user_profile_interests')\
            .upsert({
                    'userid': user_id,
                    'keywords': interests.get('keywords', []),
                    'topics': interests.get('topics', []),
                    'entities': interests.get('entities', {}),
                    'last_updated': datetime.now(timezone.utc).isoformat()
            })\
            .execute()
        return len(response.data) > 0

    # Helper methods
    def get_user_history(self, user_id: str) -> List[str]:
        response = self.client.table('history')\
            .select('postid')\
            .eq('userid', user_id)\
            .order('postid')\
            .execute()
        return [item['postid'] for item in response.data]
    
    def fetch_random_unseen(self, user_id: str, field: str, num_articles: int = 10):
        """
        Fetch random unseen post IDs for a user from a specific field.

        Args:
            user_id: The ID of the user.
            field: The field to fetch posts from.
            num_articles: Number of random post IDs to fetch.

        Returns:
            A list of dicts like [{ "postid": str }]
        """
        # 1. Fetch seen postids from history
        seen_res = self.client\
            .from_("history")\
            .select("postid")\
            .eq("userid", user_id)\
            .execute()

        seen_ids = {record["postid"] for record in (seen_res.data or [])}

        # 2. Fetch postids from posts table
        posts_res = self.client\
            .from_("posts")\
            .select("postid")\
            .eq("field", field)\
            .eq("deleted", False)\
            .execute()
        
        postids = [post["postid"] for post in (posts_res.data or [])]

        # 3. Filter unseen postids
        unseen_postids = [pid for pid in postids if pid not in seen_ids]

        if not unseen_postids:
            return []

        # 4. Randomly sample unseen postids
        sampled_postids = random.sample(unseen_postids, min(num_articles, len(unseen_postids)))

        # 5. Wrap into dicts for compatibility
        return [{"postid": pid} for pid in sampled_postids]
    
##i know could be much more efficient to get them both but for now just writing them
    def get_user_history_fields(self, user_id: str) -> List[str]:
        response = self.client.table('history')\
            .select('posts(field)')\
            .eq('userid', user_id)\
            .execute()
        return [item['posts']['field'] for item in response.data if item.get('posts')] if response.data else []


    def hash_history(history_list):
        # Sort and serialize the history to track for changes
        serialized = json.dumps(history_list, sort_keys=True)
        return hashlib.sha256(serialized.encode('utf-8')).hexdigest()
    
    @rate_limited
    def fetch_article_metadata(self, post_ids: List[str]) -> Dict[str, Any]:
        """Fetch metadata for multiple posts with batch error handling"""
        metadata = {}
        if not post_ids:
            return metadata

        self._rate_limit()
        batch_size = 200

        for i in range(0, len(post_ids), batch_size):
            batch = post_ids[i:i+batch_size]
            if not batch:
                continue

            try:
                result = self.client.table('article_metadata').select('postid,keywords,topics,entities').in_('postid', batch).execute()
                for item in result.data:
                    if isinstance(item, dict) and item.get('postid'):
                        metadata[item['postid']] = {
                            'keywords': item.get('keywords') or [],
                            'topics': item.get('topics') or [],
                            'entities': item.get('entities') or []
                        }
            except Exception as e:
                logger.error(f"Error fetching metadata batch {i//batch_size}: {e}")
                continue

        return metadata

    def batch_process_articles(self, articles: List[Dict]):
        for article in articles:
            success = self.update_article_metadata(
                article['postid'],
                {
                    'field': article['field'],
                    'keywords': article.get('keywords', []),
                    'topics': article.get('topics', []),
                    'entities': article.get('entities', {}),
                    'summary': article.get('summary', '')
                }
            )
            if not success:
                logger.warning(f"Failed to process article {article['postid']}")
                
                
    def get_user_profile(self, user_id: str) -> dict:
        res = self.client\
            .from_("user_profile_interests")\
            .select("keywords,topics,entities, preferred_fields")\
            .eq("userid", user_id)\
            .single()\
            .execute()
        return res.data or {"keywords": [], "topics": [], "entities": {}}

    
    def fetch_unseen_articles(self, user_id: str, field: str, limit : int =20):
        # utilizes an Rpc function fetch_unseen_articles_metadata takes in post_userid uuid, post_field text, post_limit int  
        # there is also fetch_unseen_articles with same args, if you want the articles info!  
        res = self.client.rpc(
            "fetch_unseen_articles_metadata",
            {"p_userid": user_id, "p_field": field, "p_limit": limit}
        ).execute()
        for article in res.data:
            raw = article.get('summary') or ''
            article['summary'] = BeautifulSoup(raw, 'html.parser').get_text()

        print(res.data)   
        return res.data or []
    
    def fetch_top_articles(self, limit: int = 1000) -> List[str]:
        """
        Fetch top `limit` article IDs sorted by engagement or createdAt.
        """
        res = self.client.rpc("rank_articles").execute()
        print(f"res ${res}")
        return [item["postid"] for item in (res.data or [])][:limit]


    def fetch_article_content(self, postid: str) -> Dict[str, Any]:
        """
        Fetch the full content of a single article.
        """
        res = self.client.from_("posts")\
            .select("content, created_at")\
            .eq("postid", postid)\
            .single()\
            .execute()
        return res.data or {}