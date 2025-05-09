from supabase import create_client, Client
from typing import List, Dict
import logging
from dotenv import load_dotenv
import os
from medium_clone_suggestion.logger import get_logger

logger = get_logger(__name__)
load_dotenv()

class DatabaseManager:
    def __init__(self, supabase_url: str, supabase_key: str):
        self.client = create_client(supabase_url, supabase_key)
        
    def fetch_articles(self, limit: int = 100) -> List[Dict]:
        # Implementation here (mock or real)
        return self.fetch_articles_from_supabase()
    
    def fetch_articles_from_supabase(self, table_name: str = "posts", 
                                     id_column: str = "postid",
                                     content_column: str = "content",
                                     filter_column: str = None,
                                     filter_value: str = None,
                                     limit: int = 100) -> List[Dict]:
        """
        Fetch articles either from Supabase or mockup file (for testing).
        """
        # Production (Supabase) query is commented for testing:
        """
        query = self.supabase.table(table_name).select(f"{id_column}, title, {content_column}")
        if filter_column and filter_value is not None:
            query = query.eq(filter_column, filter_value)
        response = query.limit(limit).execute()
        articles = []
        for item in response.data:
            item['content'] = item.pop(content_column, '')
            item['id'] = item.pop(id_column, None)
            articles.append(item)
        logger.info(f"Fetched {len(articles)} articles from Supabase table '{table_name}'")
        """
        # Testing: load from mockup.txt
        articles = []
        with open('mockup.txt', 'r', encoding='utf-8') as f:
            current_article = {}
            for line in f:
                line = line.strip()
                if line.startswith('ID: '):
                    if current_article:
                        articles.append(current_article)
                    current_article = {'id': line[4:]}
                elif line.startswith('Title: '):
                    current_article['title'] = line[7:]
                elif line.startswith('Content: '):
                    current_article['content'] = line[9:]
            if current_article:
                articles.append(current_article)
        logger.info(f"Loaded {len(articles)} articles from mockup.txt")
        return articles
    
    
    def update_processed(self, processed_articles: List[Dict]):
        # Update processed status in Supabase
        print("Received batch!",processed_articles)
        return self.save_keywords(processed_articles)
        
    def save_keywords(self, processed_articles: List[Dict]) -> None:
        file_path = os.path.abspath("result.txt")
        print("Saving results to:", file_path)
        with open('result.txt', 'w', encoding='utf-8') as f:
            for article in processed_articles:
                # Write basic info
                f.write(f"Article ID: {article.get('id', 'N/A')}\n")
                f.write(f"Title: {article.get('title', 'No title')}\n")
                
                # Write the summary if available
                if 'summary' in article:
                    f.write(f"Summary: {article['summary']}\n")
                
                # Write keywords (extract just the text from keyword tuples)
                if 'keywords' in article:
                    keywords_str = ", ".join([kw for kw, _ in article['keywords']])
                    f.write("Keywords: " + keywords_str + "\n")
                
                # Write topics
                if 'topics' in article:
                    topics_str = ", ".join(article['topics'])
                    f.write("Topics: " + topics_str + "\n")
                
                # Write entities, if any
                if 'entities' in article:
                    f.write("Entities:\n")
                    for entity_type, entities in article['entities'].items():
                        f.write(f"  {entity_type}: {', '.join(entities)}\n")
                        
                if 'field' in article:
                    f.write(f"field: {article['field']}\n")
                    
                f.write("\n" + "=" * 50 + "\n\n")
        
        logger.info(f"Saved results for {len(processed_articles)} articles to {file_path}")


    