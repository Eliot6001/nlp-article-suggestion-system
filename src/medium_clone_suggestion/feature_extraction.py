from typing import Dict, List, Union

class FeatureExtractor:
    def extract_features(self, article: Dict) -> Dict:
        """
        Extract feature vectors from article data.
        
        Args:
            article: Article dictionary with metadata

        Returns:
            Dictionary of feature vectors
        """
        features = {}
        print(f"Features Initiation Extraction  : {article}")
        # Extract keywords
        keywords = article.get("keywords", [])
        if isinstance(keywords, str):
            keywords = [k.strip() for k in keywords.split(",")]
        features["keywords"] = keywords
        
        # Extract entities
        entities = []
        article_entities = article.get("entities", {})
        if isinstance(article_entities, dict):
            for entity_type, values in article_entities.items():
                entities.extend([v.strip() for v in values])
        features["entities"] = entities

        # Extract topics
        topics = article.get("topics", [])
        if isinstance(topics, str):
            topics = [t.strip() for t in topics.split(",")]
        features["topics"] = topics
        
        summary = article.get("summary", "")
        features["summary"] = summary
        
        # Field as a feature
        features["field"] = article.get("field", "Unknown")
        
        print(f"Features Extracted : {features}")
        return features