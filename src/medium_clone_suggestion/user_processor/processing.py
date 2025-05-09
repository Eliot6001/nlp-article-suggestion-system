'''
#This code calculates a user profile (keywords, topics, entities) based on their past interactions with articles. 
# It weights recent interactions more heavily (freshness decay) and considers different levels of engagement or ratings. 
# The final scores are normalized to a 0-1 range.

'''

from datetime import datetime, timezone
from typing import Dict, List, Tuple
from medium_clone_suggestion.user_processor.config import Config
from dateutil.parser import parse

class ProfileProcessor:
    """Handles user profile calculations with freshness decay."""
    
    def __init__(self, config: Config):
        self.config = config
        
    def calculate_freshness_factor(self, created_at: str) -> float:
        """Parse ISO datetime string and calculate freshness"""
        dt = parse(created_at) if isinstance(created_at, str) else created_at
        days_old = (datetime.now(timezone.utc) - dt).days
        return 1 / (1 + self.config.FRESHNESS_DECAY_RATE * days_old)
    
    def calculate_engagement_weight(
        self, 
        segment: int, 
        created_at: datetime
    ) -> float:
        """Calculate combined engagement weight with freshness."""
        base_weight = self.config.WEIGHTS["engagement_segments"].get(segment, 1.0)
        return base_weight * self.calculate_freshness_factor(created_at)
    
    def calculate_scores(
        self, 
        activities: List[Dict], 
        metadata: Dict[str, Dict]
    ) -> Tuple[Dict, Dict, Dict]:
        """Calculate normalized scores for keywords, topics, and entities."""
        keyword_scores: Dict[str, float] = {}
        topic_scores: Dict[str, float] = {}
        entity_scores: Dict[str, float] = {}
        
        for activity in activities:
            post_id = activity['postid']
            if post_id not in metadata:
                continue
            
            weight = self._get_activity_weight(activity)
            metadata_entry = metadata[post_id]
            print(f"metadata entry: {metadata} || {activity}")
            
            raw_keywords = metadata_entry.get('keywords', [])
            keywords = [kw[0] for kw in raw_keywords if isinstance(kw, (list, tuple))]
            self._update_scores(keywords, keyword_scores, weight)

            # Topics are already strings
            self._update_scores(
                metadata_entry.get('topics', []),
                topic_scores,
                weight
            )

            # Entities: list of dicts or strings
            self._update_entity_scores(
                metadata_entry.get('entities', []),
                entity_scores,
                weight
            )
        
        return (
            self._normalize_scores(keyword_scores),
            self._normalize_scores(topic_scores),
            self._normalize_scores(entity_scores)
        )
    
    def _get_activity_weight(self, activity: Dict) -> float:
        """Determine weight for an activity based on type and freshness."""

        dt = parse(activity["created_at"]) if isinstance(activity["created_at"], str) else activity["created_at"]
        fresh = self.calculate_freshness_factor(dt)
        
        atype   = activity.get("activity_type", "view")
        weight  = 0.0

        if atype == "view":
            weight += self.config.WEIGHTS["view"]

        # engagement (segment defined)
        if atype in ("engagement", "engagement_and_rating"):
            seg = activity.get("segment", 0) or 0
            weight += self.config.WEIGHTS["engagement_segments"].get(seg, 1.0)

        # rating
        if atype in ("rating", "engagement_and_rating"):
            rating = activity.get("rating", 0) or 0
            weight += self.config.WEIGHTS["rating"] * rating

        return weight * fresh
    
    def _update_scores(self, items: List[str], scores: Dict, weight: float):
        for item in items:
            key = item[0] if isinstance(item, (list, tuple)) else item
            scores[key] = scores.get(key, 0.0) + weight
    
    def _update_entity_scores(self, entities: List, scores: Dict, weight: float):
        for entity in entities:
            name = entity.get('name') if isinstance(entity, dict) else entity
            if name:
                scores[name] = scores.get(name, 0.0) + weight
    
    def _normalize_scores(self, scores: Dict) -> Dict:
        if not scores:
            return {}
        max_score = max(scores.values())
        return {k: v/max_score for k, v in scores.items()}