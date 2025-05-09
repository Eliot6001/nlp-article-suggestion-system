import logging
import argparse
from typing import List
from datetime import datetime, timezone
import json
from config import Config
from processing import ProfileProcessor
from mock_supabase import MockSupabaseManager, write_test_data_to_file
import os

# Set up path to be relative to this file
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(SCRIPT_DIR)
class LocalUserProfileBuilder:
    """Modified UserProfileBuilder for local testing"""
    def __init__(self, config, test_data_path=None):
        self.config = config
        self.db = MockSupabaseManager(test_data_path)
        self.processor = ProfileProcessor(config)
        self.logger = self._setup_logging()

    def _setup_logging(self) -> logging.Logger:
        """Configure application logging."""
        logger = logging.getLogger("LocalUserProfileBuilder")
        logger.setLevel(logging.INFO)
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        handlers = [
            logging.FileHandler("local_profile_builder.log"),
            logging.StreamHandler()
        ]
        for handler in handlers:
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        
        return logger
    
    def get_active_users(self, limit: int) -> List[str]:
        """Retrieve active users with processing limit"""
        return self.db.fetch_active_users(
            limit=limit,
            max_days=self.config.MAX_HISTORY_DAYS
        )
    
    def process_users(self, user_limit: int = None):
        """Main processing method with user limit."""
        limit = user_limit or self.config.USER_PROCESS_LIMIT
        self.logger.info(f"Starting processing for up to {limit} users")
        
        try:
            users = self.get_active_users(limit)
            self.logger.info(f"Found {len(users)} active users to process")
            
            for i in range(0, len(users), self.config.BATCH_SIZE):
                batch = users[i:i+self.config.BATCH_SIZE]
                self._process_batch(batch)
                
        except Exception as e:
            self.logger.error(f"Processing failed: {e}")
        finally:
            self.db.close()

    def _process_batch(self, user_ids: List[str]):
        """Process a batch of users with mock data fetching"""
        self.logger.info(f"Processing batch of {len(user_ids)} users")
        
        # Fetch all activities for the batch
        activities = self.db.fetch_user_activities(
            user_ids=user_ids,
            max_days=self.config.MAX_HISTORY_DAYS
        )
        
        # Get unique post IDs
        post_ids = list({a['postid'] for a in activities if a.get('postid')})
        
        # Fetch metadata
        metadata = self.db.fetch_article_metadata(post_ids)
        
        # Process each user
        for user_id in user_ids:
            user_acts = [a for a in activities if a['userid'] == user_id]
            self._process_user(user_id, user_acts, metadata)

    def _process_user(self, user_id: str, activities: List[dict], metadata: dict):
        """Process individual user's activities"""
        if not activities:
            self.logger.debug(f"No activities for user {user_id}")
            return
        
        try:
            kw_scores, topic_scores, entity_scores = self.processor.calculate_scores(
                activities, metadata
            )
            
            # Filter scores
            profile_data = {
                'keywords': {k: v for k, v in kw_scores.items() 
                            if v >= self.config.MIN_ENGAGEMENT_SCORE},
                'topics': {k: v for k, v in topic_scores.items() 
                          if v >= self.config.MIN_ENGAGEMENT_SCORE},
                'entities': {k: v for k, v in entity_scores.items() 
                            if v >= self.config.MIN_ENGAGEMENT_SCORE}
            }
            
            # Update via mock database
            self.db.upsert_user_profile(user_id, profile_data)
            self.logger.info(f"Updated suggestions for user {user_id}")
            
        except Exception as e:
            self.logger.error(f"Error processing user {user_id}: {e}")
            
def main():
    """Command line app main for local user profile processor."""
    parser = argparse.ArgumentParser(description='Local User Profile Builder')
    parser.add_argument('--limit', type=int, default=5,
                      help='Maximum number of users to process')
    parser.add_argument('--data', type=str, default=None,
                      help='Path to test data JSON file')
    args = parser.parse_args()
    

    
    config = Config()
    
    # Create test data if not provided
    if not args.data:
        data_path = "mock_data.json"
        write_test_data_to_file(data_path)
    else:
        data_path = args.data
    
    # Run builder with test data
    builder = LocalUserProfileBuilder(config, data_path)
    builder.process_users(args.limit)


if __name__ == "__main__":
    main()