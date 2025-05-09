import json
import random
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any
import re

class MockSupabaseManager:
    """Mock implementation of SupabaseManager for local testing"""
    def __init__(self, test_data_path=None):
        """Initialize with optional test data path or generate from articles"""
        self.test_data = {}
        if test_data_path:
            with open(test_data_path, 'r') as f:
                self.test_data = json.load(f)
        else:
            # Generate test data using articles from result.txt
            self.test_data = self.generate_test_data_from_articles('../../result.txt')
        
    def generate_test_data_from_articles(self, file_path: str) -> Dict[str, Any]:
        """Generate complete test data structure from article data"""
        # Load articles from file
        articles_data = self.load_article_data(file_path)
        articles = articles_data.get('articles', [])
        
        # Extract post IDs and build metadata
        post_ids = [str(article.get('id', f"post_{i}")) for i, article in enumerate(articles, 1)]
        metadata = {}
        for article in articles:
            post_id = article.get('id', f"post_{articles.index(article)+1}")
            metadata[post_id] = {
                'keywords': article.get('keywords', []),
                'topics': article.get('topics', []),
                'entities': [{'name': e} for e in article.get('entities', {}).values()]
                if isinstance(article.get('entities'), dict)
                else article.get('entities', [])
            }
        
        # Generate user data and activities
        user_ids = [f"user_{i}" for i in range(1, 11)]  # 10 test users
        now = datetime.now(timezone.utc)
        activities = []
        
        for user_id in user_ids:
            # Each user has 5-15 activities
            for _ in range(random.randint(5, 15)):
                post_id = random.choice(post_ids)
                days_ago = random.uniform(0, 7)
                activity_date = now - timedelta(days=days_ago)
                
                activities.append({
                    'userid': user_id,
                    'postid': post_id,
                    'created_at': activity_date.isoformat(),
                    'segment': random.choice([None] + [random.randint(1, 5)])
                })
        
        return {
            'user_ids': user_ids,
            'post_ids': post_ids,
            'activities': activities,
            'metadata': metadata
        }
        
    @staticmethod
    def load_article_data(file_path: str) -> Dict[str, Any]:
        """
        Parse article data from a text file.
        
        Expected format is blocks of text separated by lines containing a series of '='.
        Each block should contain fields such as:
        - Article ID or ID:
        - Title:
        - Summary: or Content:
        - Keywords:
        - Topics:
        - Entities:
        - field:
        
        Returns a dictionary with a key 'articles' mapping to a list of article dicts.
        """
        articles = []
        
        # Read full file content
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Split the file into blocks. This uses a delimiter of a line with 10 or more '=' signs.
        blocks = re.split(r'\n\s*=+\s*\n', content)
        
        for block in blocks:
            block = block.strip()
            if not block:
                continue
            article = {}
            
            # Extract Article ID using 'Article ID:' or 'ID:' pattern.
            id_match = re.search(r'(Article ID|ID):\s*(.+)', block, re.IGNORECASE)
            if id_match:
                article['id'] = id_match.group(2).strip()
            
            # Extract Title
            title_match = re.search(r'Title:\s*(.+)', block, re.IGNORECASE)
            if title_match:
                article['title'] = title_match.group(1).strip()
            
            # Extract Summary or Content (using DOTALL for multi-line)
            summary_match = re.search(r'(Summary|Content):\s*([\s\S]+?)(?=\n[A-Z][a-z]+:|$)', block, re.IGNORECASE)
            if summary_match:
                article['summary'] = summary_match.group(2).strip()
            
            # Extract Keywords
            keywords_match = re.search(r'Keywords:\s*(.+)', block, re.IGNORECASE)
            if keywords_match:
                keywords_str = keywords_match.group(1).strip()
                # Assume keywords are comma-separated
                article['keywords'] = [kw.strip() for kw in keywords_str.split(',') if kw.strip()]
            
            # Extract Topics
            topics_match = re.search(r'Topics:\s*(.+)', block, re.IGNORECASE)
            if topics_match:
                topics_str = topics_match.group(1).strip()
                article['topics'] = [topic.strip() for topic in topics_str.split(',') if topic.strip()]
            
            # Extract Entities
            # This looks for "Entities:" until encountering "field:" or the end of block
            entities_match = re.search(r'Entities:\s*([\s\S]+?)(?=\n(field|$))', block, re.IGNORECASE)
            if entities_match:
                # Try to split each entity line (assuming "Type: Name")
                entities_str = entities_match.group(1).strip()
                entities = {}
                for line in entities_str.splitlines():
                    if ':' in line:
                        key, value = line.split(':', 1)
                        entities[key.strip()] = value.strip()
                article['entities'] = entities if entities else entities_str
            
            # Extract field
            field_match = re.search(r'field:\s*(.+)', block, re.IGNORECASE)
            if field_match:
                article['field'] = field_match.group(1).strip()
            print("article Gotten", article)
            articles.append(article)
        
        return {'articles': articles}
    def fetch_active_users(self, limit: int, max_days: int) -> List[str]:
        """Mock implementation of fetch_active_users"""
        # In a real implementation, this would filter by date
        return self.test_data['user_ids'][:limit]
    
    def fetch_user_activities(self, user_ids: List[str], max_days: int) -> List[Dict]:
        """Mock implementation of fetch_user_activities"""
        # Filter activities by user_ids
        filtered = [a for a in self.test_data['activities'] 
                   if a['userid'] in user_ids]
        
        # In a real implementation, this would also filter by date
        return filtered
    
    def fetch_article_metadata(self, post_ids: List[str]) -> Dict[str, Any]:
        """Mock implementation of fetch_article_metadata"""
        return {post_id: self.test_data['metadata'].get(post_id, {}) 
                for post_id in post_ids if post_id in self.test_data['metadata']}
    
    def upsert_user_profile(self, user_id: str, profile_data: Dict) -> bool:
        """Mock implementation of upsert_user_profile"""
        # Write profile data to file
        with open("../../user_processed.txt", "a") as f:
            f.write(f"User ID: {user_id}\n")
            f.write(json.dumps(profile_data, indent=2))
            f.write("\n" + "="*50 + "\n")
        return True
    
    def close(self):
        """Mock implementation of close"""
        pass



def write_test_data_to_file(file_path="mock_data.json"):
    """Generate and write test data to file using real articles"""
    mock_manager = MockSupabaseManager()  # This will now use result.txt
    with open(file_path, 'w') as f:
        json.dump(mock_manager.test_data, f, indent=2, default=str)
    print(f"Test data written to {file_path}")

# For testing this module directly
if __name__ == "__main__":
    write_test_data_to_file()
    print("Test complete!")