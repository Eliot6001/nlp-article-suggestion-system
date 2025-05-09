
from typing import Dict
from medium_clone_suggestion.database import DatabaseManager
from medium_clone_suggestion.article_processor.processing import ArticleProcessor
from medium_clone_suggestion.article_processor.models import ModelManager
import nltk 
from medium_clone_suggestion.logger import get_logger

logger = get_logger(__name__)
nltk.download('words')
nltk.download('maxent_ne_chunker_tab')
nltk.download('stopwords')
#I msised some of these, gotta include them

class ProcessingPipeline:
    def __init__(self):
        self.db = DatabaseManager()
        self.model_manager = ModelManager()
        self.processor = ArticleProcessor(self.model_manager)

    def run(self) -> Dict:
        articles = self.db.fetch_uncategorized_articles()
        processed = self.processor.process_batch(articles)
        print(processed)
        errors = self.db.update_processed(processed)
        if errors:
            print(f"There were {len(errors)} errors.")
        return {"processed": len(processed)}