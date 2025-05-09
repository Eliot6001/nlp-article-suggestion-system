from datetime import datetime, timedelta, time, timezone
from typing import List, Dict, Any
from supabase_client import SupabaseClient
import logging

logger = logging.getLogger(__name__)

class SupabaseManager:
    """Handles Supabase interactions with rate limiting"""
    def __init__(self):
        self.client = SupabaseClient().get_client()
        self.last_request_time = datetime.min
        self.min_request_interval = 0.1  # 100ms between requests
        
    def _rate_limit(self):
        """Enforce minimum time between requests"""
        now = datetime.now(timezone.utc)
        elapsed = (now - self.last_request_time).total_seconds()
        if elapsed < self.min_request_interval:
            time.sleep(self.min_request_interval - elapsed)
        self.last_request_time = datetime.now(timezone.utc)
    
    def fetch_active_users(self, limit: int, max_days: int) -> List[str]:
        """Fetch distinct active user IDs using the RPC union function for history and engagements"""
        self._rate_limit()
        cutoff = datetime.now(timezone.utc) - timedelta(days=max_days)
        combined = set()

        try:
            # Call the RPC function 'fetch_user_activities' with the cutoff timestamp
            # Check README.md for more information!
            response = self.client.rpc('fetch_user_activities', {'cutoff': cutoff.isoformat()}).execute()
            activities = response.data if response and response.data else []
            
            # Extract distinct user IDs from the combined activities
            for row in activities:
                user_id = row.get('userid')
                if user_id and isinstance(user_id, (str, int)):
                    combined.add(str(user_id))
        except Exception as e:
            logger.error(f"Error fetching active users via RPC: {e}")
        
        return list(combined)[:limit]

    
    def fetch_user_activities(self, user_ids: List[str], max_days: int) -> List[Dict]:
        """Fetch combined history and engagements for a batch of users via RPC"""
        """Check README.md for more data!"""
        self._rate_limit()
        cutoff = datetime.now(timezone.utc) - timedelta(days=max_days)
        
        if not user_ids:
            return []
        
        try:
            response = self.client.rpc(
                'fetch_user_activities_by_users', 
                {'cutoff': cutoff.isoformat(), 'user_ids': user_ids}
            ).execute()
            return response.data if response.data else []
        except Exception as e:
            logger.error(f"Error fetching user activities via RPC: {e}")
            return []

    
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

    
    def upsert_user_profile(self, user_id: str, profile_data: Dict) -> bool:
        """Upsert user suggestion profile with error handling"""
        self._rate_limit()
        if not user_id or not isinstance(profile_data, dict):
            logger.error("Invalid input for profile upsert")
            return False

        try:
            response = self.client.table('user_suggestions').upsert({
                'userid': str(user_id),
                'keywords': profile_data.get('keywords', {}),
                'topics': profile_data.get('topics', {}),
                'entities': profile_data.get('entities', {}),
                'updated_at': datetime.now(timezone.utc).isoformat()
            }).execute()

            if not response.data:
                logger.warning(f"Empty response for user {user_id} upsert")
                return False

            return True
        except ClientException as e:
            logger.error(f"Error upserting profile for user {user_id}: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error updating profile {user_id}: {e}")
            return False