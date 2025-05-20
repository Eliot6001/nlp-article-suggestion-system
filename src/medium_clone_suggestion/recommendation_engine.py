import os
import json
import random
from typing import List, Dict

from datetime import datetime, timedelta, timezone
import sys 
import hashlib
from medium_clone_suggestion.config import FIELDS, CACHE_DIR
from medium_clone_suggestion.caching import CacheManager
from medium_clone_suggestion.feature_extraction import FeatureExtractor
from medium_clone_suggestion.similarity import SimilarityCalculator
from  medium_clone_suggestion.database import DatabaseManager


from typing import List, Dict, Any

from medium_clone_suggestion.logger import get_logger

logger = get_logger(__name__)
    
ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..")
)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
    

  
def hash_history(history_list: List[str]) -> str:
    sorted_ids = sorted(history_list)
    serialized = json.dumps(sorted_ids, sort_keys=True)
    return hashlib.sha256(serialized.encode()).hexdigest()


class RecommendationSystem:
    def __init__(self, testing_mode: bool = True):
        """
        Initialize the recommendation system.
        If needed, preload a global TF-IDF corpus here.
        """
        self.data_access = DatabaseManager()
        self.feature_extractor = FeatureExtractor()
        self.similarity_calculator = SimilarityCalculator()
        self.cache_manager = CacheManager()
        
        self.global_article_ids = set()
        self.global_corpus_docs = []
        
        # build initial global corpus at startup
        self.initialize_global_corpus()


    def initialize_global_corpus(self, num_articles: int = 1000):
        if self.global_article_ids:
            logger.info("Global corpus already initialized.")
            return

        logger.info("Initializing global TF-IDF corpus…")
        top_ids = self.data_access.fetch_top_articles(limit=num_articles)
        metadata = self.data_access.fetch_article_metadata(top_ids)

        
        docs: List[str] = []
        ids: List[str] = []
        for pid in top_ids:
            if pid in metadata:
                feats = metadata[pid]
                post = self.data_access.fetch_article_content(pid)
                text = self.similarity_calculator._build_article_str(
                    {**feats, "summary": post.get("content", "")}
                )
                docs.append(text)
                ids.append(pid)

        # store and fit
        self.global_corpus_docs = docs
        self.global_article_ids = set(ids)
        self.similarity_calculator.build_global_corpus(docs)
        logger.info("TF-IDF global vectorizer built with initial corpus.")
        
        
    def _incremental_corpus_update(self, num_new: int = 100, refit_threshold: int = 50):
        """Every 8h: fetch top N, add unseen, re‑fit TF‑IDF."""
        top_ids = self.data_access.fetch_top_articles(limit=num_new)
        metadata = self.data_access.fetch_article_metadata(top_ids)

        new_docs, new_ids = [], []
        for pid in top_ids:
            if pid not in self.global_article_ids and pid in metadata:
                feats = metadata[pid]
                post = self.data_access.fetch_article_content(pid)
                text = self.similarity_calculator._build_article_str(
                    {**feats, "summary": post.get("content", "")}
                )
                new_docs.append(text)
                new_ids.append(pid)

        if not new_docs:
            logger.info("No new articles to add to TF-IDF corpus.")
            return

        # extend and re‑fit
        self.global_corpus_docs.extend(new_docs)
        self.global_article_ids.update(new_ids)
                
        if len(new_docs) >= refit_threshold:
            logger.info(f"Adding {len(new_docs)} docs to corpus and re-fitting TF-IDF.")
            self.similarity_calculator.build_global_corpus(self.global_corpus_docs)
        else:
            logger.info(f"Added {len(new_docs)} docs, but not refitting TF-IDF yet.")
    
    
    def recommend_articles(
        self,
        user_id: str,
        num_recommendations: int = 20,
        exploration_ratio: float = 0.2,
        articles_per_field: int = 20
    ) -> List[Dict[str, Any]]:
        # 1. Fetch history and hash
        logger.info(f"Generating recommendations for user profile '{user_id}'...")
        history = self.data_access.get_user_history(user_id)
        history_hash = hash_history(history)
        now = datetime.now(timezone.utc)

        # 2. Check cache
        cached = self.cache_manager.check_and_update_cache(
            user_id, history, history_hash, now, []
        )
        #Remove cache for debugging!!!
        if cached:
            logger.info("Cache hit! Returning cached recommendations.")
            return cached

        # 3. Load profile & seen IDs
        user_profile = self.data_access.get_user_profile(user_id)
        seen_ids = set(history)

        # 4. Determine field pools
        pf_fields = user_profile.get("preferred_fields") or FIELDS
        try:
            hist_fields = self.data_access.get_user_history_fields(user_id) or []
            hist_fields = [f for f in hist_fields if f not in pf_fields]
        except Exception:
            hist_fields = []

        # 5. Fetch unseen articles per pool
        def fetch_pool(fields: List[str]) -> List[Dict[str, Any]]:
            pool = []
            for field in fields:
                try:
                    pool.extend(
                        self.data_access.fetch_unseen_articles(
                            user_id, field, articles_per_field
                        )
                    )
                except Exception:
                    continue
            # remove seen and dedupe
            unique = {a["postid"]: a for a in pool if a["postid"] not in seen_ids}
            logger.debug(f"Retrieved {len(unique)} unseen articles.")
            return list(unique.values())

        pf_raw = fetch_pool(pf_fields)
        hist_raw = fetch_pool(hist_fields)
        all_articles = pf_raw + hist_raw

        # 6. Score all articles in a single TF-IDF space

        if all_articles:
            candidate_feats = [self.feature_extractor.extract_features(a) for a in all_articles]
            logger.debug(f"Scoring {len(candidate_feats)} articles against user profile.")
            scores = self.similarity_calculator.score_with_global_corpus(
                user_profile, candidate_feats
            )
            print(f"scores {scores}")
            for art, score in zip(all_articles, scores):
                art["score"] = score
        else:
            all_articles = []

        # split scored pools
        pf_scored = sorted(
            [a for a in all_articles if a in pf_raw],
            key=lambda x: x["score"], reverse=True
        )
        hist_scored = sorted(
            [a for a in all_articles if a in hist_raw],
            key=lambda x: x["score"], reverse=True
        )

        # sort each
        pf_scored.sort(key=lambda x: x["score"], reverse=True)
        hist_scored.sort(key=lambda x: x["score"], reverse=True)

        N = num_recommendations
        n_pf = int(N * (1 - exploration_ratio))
        n_hist = N - n_pf
        
        recs = pf_scored[:n_pf] + hist_scored[:n_hist]

                
        if len(recs) < N:
            extras = (pf_scored[n_pf:] + hist_scored[n_hist:])
            recs.extend(extras[: (N - len(recs)) ])
        if len(recs) < N:
            field = pf_fields[0] if pf_fields else "Technology"
            recs.extend(
                self.data_access.fetch_random_unseen(user_id, field, N - len(recs))
            )
        logger.debug(f"Top exploitation scores (pf_scored): {[a['score'] for a in pf_scored[:5]]}")
        logger.debug(f"Top exploration scores (hist_scored): {[a['score'] for a in hist_scored[:5]]}")

        # 8. Cache & return
        self.cache_manager.set_cache(
            user_id,
            history_hash,
            {"hash": history_hash, "recs": recs, "ts": now}
        )
        logger.info("Combined recommendation list prepared.")
        return recs


    
 ##moved out caching for clarity.

    def batch_process_recommendations(self, user_ids: List[str],
                                     num_recommendations: int = 10,
                                     exploration_ratio: float = 0.2,
                                     articles_per_field: int = 20) -> Dict[str, List[Dict]]:
        """
        Process recommendations for multiple users at once.

        Args:
            user_ids: List of user IDs
            num_recommendations: Number of articles to recommend per user
            exploration_ratio: Ratio of random recommendations
            articles_per_field: Number of articles to fetch per field

        Returns:
            Dictionary mapping user IDs to their recommendations
        """
        results = {}

        for user_id in user_ids:
            results[user_id] = self.recommend_articles(
                user_id,
                20,
                exploration_ratio,
                articles_per_field
            )

        return results