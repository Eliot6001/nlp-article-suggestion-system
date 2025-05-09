from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from typing import List, Dict, Any
import json
import hashlib
import joblib
import os

from medium_clone_suggestion.logger import get_logger

logger = get_logger(__name__)

class SimilarityCalculator:
    """
    Calculates similarity scores between a single user profile and multiple candidate articles
    using TF-IDF vectorization and cosine similarity.
    """
    def __init__(self):
        self.vectorizer = TfidfVectorizer()
        self.global_fitted = False  # Track if the vectorizer has been fitted

    def _build_article_str(self, features: Dict[str, Any]) -> str:
        print(f"article_str : {features}")
        if not isinstance(features, dict):
            raise TypeError(f"Expected article features dict, got {type(features)}: {features}")

        ak = []
        for item in features.get("keywords", []):
            if isinstance(item, (list, tuple)) and item:
                ak.append(str(item[0]))

        at = []
        for t in features.get("topics", []):
            if isinstance(t, dict):
                at.append(t.get("name", ""))
            else:
                at.append(str(t))

        ae = []
        for e in features.get("entities", []):
            if isinstance(e, dict):
                ae.append(e.get("name", ""))
            else:
                ae.append(str(e))

        body = features.get("summary", "")
        return " ".join(ak + at + ae + [body])

    def _build_user_str(self, profile: Dict[str, Any]) -> str:
        """
        Concatenate user profile keywords, topics, and entities into a single text string.
        Handles malformed or missing data without crashing.
        """
        def safe_keys(field):
            try:
                return list(field.keys()) if isinstance(field, dict) else []
            except Exception:
                return []
            
        logger.info("Extracting user_preferences", profile)
        uk = safe_keys(profile.get("keywords", {}))
        ut = safe_keys(profile.get("topics", {}))
        ue = safe_keys(profile.get("entities", {}))
        return " ".join(uk + ut + ue)

    def calculate_similarity(self, article_features: Dict[str, Any]) -> float:
        """
        (-Deprecated-) Calculate similarity for a single article after a fit.
        Use score_all for batch scoring instead.
        """
        raise NotImplementedError(
            "calculate_similarity is deprecated, use score_all for batch scoring."
        )

    def build_global_corpus(self, articles: List[Dict[str, Any]]) -> None:
        """
        Fit the TF-IDF vectorizer on the global set of article texts or load a stored vectorizer
        if the corpus hasn't changed, based on article IDs.
        """
        # Build document strings
        docs = [self._build_article_str(a) if isinstance(a, dict) else a for a in articles]
        
        # Extract article IDs if present
        ids = [a.get('postid') for a in articles if isinstance(a, dict) and 'postid' in a]
        
        # If no IDs are provided, fit the vectorizer directly
        if not ids:
            logger.warning("No 'postid' found in articles, fitting new vectorizer.")
            self.vectorizer.fit(docs)
            self.global_fitted = True
            return
        
        # Compute a hash of the sorted article IDs to detect corpus changes
        id_hash = hashlib.sha256(json.dumps(sorted(ids), sort_keys=True).encode()).hexdigest()
        vectorizer_file = 'vectorizer.joblib'
        
        # Check for a stored vectorizer
        if os.path.exists(vectorizer_file):
            try:
                stored_data = joblib.load(vectorizer_file)
                if stored_data['id_hash'] == id_hash:
                    self.vectorizer = stored_data['vectorizer']
                    self.global_fitted = True
                    logger.info("Loaded stored TF-IDF vectorizer.")
                    return
            except Exception as e:
                logger.warning(f"Failed to load stored vectorizer: {e}")
        
        # Fit a new vectorizer if no valid stored one is found
        self.vectorizer.fit(docs)
        self.global_fitted = True
        
        # Save the vectorizer with the ID hash
        joblib.dump({'vectorizer': self.vectorizer, 'id_hash': id_hash}, vectorizer_file)
        logger.info("Fitted and saved new TF-IDF vectorizer.")

    def score_with_global_corpus(
        self,
        user_profile: Dict[str, Any],
        candidate_articles: List[Dict[str, Any]]
    ) -> List[float]:
        """
        Transform user and candidate articles using the pre-fit global TF-IDF,
        then compute cosine similarity.
        """
        user_str = self._build_user_str(user_profile)
        article_strs = [self._build_article_str(a) for a in candidate_articles]
        tf_user = self.vectorizer.transform([user_str])
        tf_articles = self.vectorizer.transform(article_strs)
        sims = cosine_similarity(tf_user, tf_articles)[0]
        logger.debug(f"Calculated cosine similarities for {len(candidate_articles)} articles.")
        return sims.tolist()

    def score_all(
        self,
        user_profile: Dict[str, Any],
        candidate_articles: List[Dict[str, Any]]
    ) -> List[float]:
        """
        DEPRECATED in favor of score_with_global_corpus for more efficiency.
        """
        raise NotImplementedError(
            "score_all is deprecated, use score_with_global_corpus instead."
        )