from typing import List, Dict, Tuple
import concurrent.futures
import logging
import medium_clone_suggestion.article_processor.utils as utility 
from medium_clone_suggestion.article_processor.models import SummarizationModel, KeywordModel
import traceback

from medium_clone_suggestion.logger import get_logger

logger = get_logger(__name__)

class ArticleProcessor:
    def __init__(self, model_manager, max_workers: int = 4):
        self.model_manager = model_manager
        self.max_workers = max_workers
        self.summarizer = SummarizationModel(model_manager)
        self.keyword_extractor = KeywordModel(model_manager)

    def process_batch(self, articles: List[Dict]) -> List[Dict]:
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {
                executor.submit(self._process_single, article): article
                for article in articles
            }
            return self._collect_results(futures)


    def _process_single(self, article: Dict) -> Dict:
        try:
            article = utility.clean_article(article)
        except Exception as e:
            logger.exception(f"Error in clean_article: {e}\nTraceback: {traceback.format_exc()}")
            article.setdefault('errors', []).append("clean_article failed")
        ##Given in clean_article the is_gebberish processing
        ##So that i don't waste processing cycles on garbage text
        ##And at the same time it would be set as isCategorized
        ##So it won't be fetched again!
        article.setdefault('is_gibberish', False)
        if not article['is_gibberish'] == True:
            try:
                article = self._add_summary(article)
            except Exception as e:
                logger.exception(f"Error in _add_summary: {e}\nTraceback: {traceback.format_exc()}")
                article.setdefault('errors', []).append("_add_summary failed")
            
            try:
                article = self._extract_keywords(article)
            except Exception as e:
                logger.exception(f"Error in _extract_keywords: {e}\nTraceback: {traceback.format_exc()}")
                article.setdefault('errors', []).append("_extract_keywords failed")
            
            try:
                article = self._add_field(article)
            except Exception as e:
                logger.exception(f"Error in _add_field: {e}\nTraceback: {traceback.format_exc()}")
                article.setdefault('errors', []).append("_add_field failed")
            
            try:
                article = utility.add_entities(article)
            except Exception as e:
                logger.exception(f"Error in add_entities: {e}\nTraceback: {traceback.format_exc()}")
                article.setdefault('errors', []).append("add_entities failed")
            
            try:
                article = utility.add_topics(article)
            except Exception as e:
                logger.exception(f"Error in add_topics: {e}\nTraceback: {traceback.format_exc()}")
                article.setdefault('errors', []).append("add_topics failed")
            
        return article


    def _add_summary(self, article: Dict) -> Dict:
        content = article.get('content', '')
        if len(content) > 384:
            article['summary'] = self.summarizer.summarize(content)
            print(f"Summarized: {article['summary']}")
        else:
            article['summary'] = ''  
    

        return article

    #Took down the summary vs Total text just to reduce 
    #overall processing.
    
    def _extract_keywords(self, article: Dict) -> Dict:
        keywords = self.keyword_extractor.extract_keywords(article['content'])
        article['keywords'] = keywords
        return article
    
    def _add_field(self, article: Dict) -> Dict:
        field = self.keyword_extractor.assign_field(article['keywords'])
        article['field'] = field
        return article
    
    def _collect_results(self, futures):
        results = []
        for future in concurrent.futures.as_completed(futures):
            results.append(future.result())
        return results