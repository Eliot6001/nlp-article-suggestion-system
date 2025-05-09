import argparse
import logging
import time
from typing import List
from datetime import datetime, timedelta, timezone
from medium_clone_suggestion.user_processor.config import Config
from medium_clone_suggestion.database import DatabaseManager
from medium_clone_suggestion.user_processor.processing import ProfileProcessor
from  medium_clone_suggestion.logger import get_logger

logger = get_logger(__name__)

class UserProfileBuilder:
    def __init__(self, config: Config):
        self.config = config
        self.db = DatabaseManager()
        self.processor = ProfileProcessor(config)
        self.logger = self._setup_logging()

    def _setup_logging(self) -> logging.Logger:
        """Configure application logging."""
        return logger
    
    def get_active_users(self, limit: int) -> List[str]:
        """Retrieve active users with processing limit"""
        return self.db.fetch_active_users(
            limit=limit,
            max_days=self.config.MAX_HISTORY_DAYS
        )
    
    def process_users(self, user_limit: int = None):
        limit = user_limit or self.config.USER_PROCESS_LIMIT
        self.logger.info(f"Starting processing for up to {limit} users")

        users = self.get_active_users(limit)
        for user_id in users:
            # 1) pull their last updated—or fall back to global cutoff
            last   = self.db.get_user_profile_last_updated(user_id)
            cutoff = last or (datetime.now(timezone.utc) - timedelta(days=self.config.MAX_HISTORY_DAYS)).isoformat()

            # 2) fetch only THEIR new activities, Have done as a hack to fix a logic understanding
            ## of my process.
            activities = self.db.get_user_activities_since(user_id, cutoff)
            if not activities:
                continue

            # 3) gather metadata for those postids
            postids  = {a["postid"] for a in activities}
            metadata = self.db.fetch_article_metadata(list(postids))

            # 4) process this single user
            self._process_user(user_id, activities, metadata)
       
    def _process_user(self, user_id: str, activities: List[dict], metadata: dict):
        if not activities:
            self.logger.debug(f"No activities for user {user_id}")
            return

        try:
            formatted_activities = []
            
            for item in activities:
                if item.get('segment') is None and item.get('rating') is None:
                    activity_type = 'view'
                elif item.get('segment') is None and item.get('rating') is not None:
                    activity_type = 'rating'
                elif item.get('segment') is not None and item.get('rating') is None:
                    activity_type = 'engagement'
                else:
                    activity_type = 'engagement_and_rating'

                activity = {
                    'userid': user_id,
                    'postid': item['postid'],
                    'activity_type': activity_type,
                    'created_at': item['created_at']
                }

                if activity_type in ('rating', 'engagement_and_rating'):
                    activity['rating'] = item['rating']
                if activity_type in ('engagement', 'engagement_and_rating'):
                    activity['segment'] = item['segment']

                formatted_activities.append(activity)

            print(f" {formatted_activities} ")

            kw_scores, topic_scores, entity_scores = self.processor.calculate_scores(
                formatted_activities, metadata
            )

            profile_data = {
                'keywords': {k: v for k, v in kw_scores.items() if v >= self.config.MIN_ENGAGEMENT_SCORE},
                'topics': {k: v for k, v in topic_scores.items() if v >= self.config.MIN_ENGAGEMENT_SCORE},
                'entities': {k: v for k, v in entity_scores.items() if v >= self.config.MIN_ENGAGEMENT_SCORE}
            }

            self.db.update_user_interests(user_id, profile_data)
            self.db.update_user_profile_last_updated(user_id, datetime.now(timezone.utc))
            self.logger.info(f"Updated suggestions for user {user_id}")

        except Exception as e:
            self.logger.error(f"Error processing user {user_id}: {e}")


    def _process_batch(self, max_users: int):
        """Process a batch of active users (by count), fetches data once then groups"""
        self.logger.info(f"Processing up to {max_users} active users")

        # Get recent activities from multiple users
        activities = self.db.fetch_active_users(
            limit=max_users,
            max_days=self.config.MAX_HISTORY_DAYS
        )

        all_post_ids = set()
        user_activities = {}

        # Group activities by user
        for item in activities:
            uid = item.get('userid')
            if not uid:
                continue
            user_activities.setdefault(uid, []).append(item)
            all_post_ids.add(item['postid'])

        metadata = self.db.fetch_article_metadata(list(all_post_ids))
        # Process N most active users (based on unique user count)
        for user_id in list(user_activities.keys()):
            self._process_user(user_id, user_activities[user_id], metadata)



def main():
    """Command line app main for user profile processor."""
    parser = argparse.ArgumentParser(description='User Profile Builder')
    parser.add_argument('--limit', type=int, default=50,
                    help='Maximum number of users to process')
    
    args = parser.parse_args()
    
    config = Config()
    builder = UserProfileBuilder(config)
    
    # Run once with optional limit
    builder.process_users(args)
    
    # Uncomment for scheduled runs
    # schedule.every(config.RUN_INTERVAL_HOURS).hours.do(builder.process_users)
    # while True:
    #     schedule.run_pending()
    #     time.sleep(60)

if __name__ == "__main__":
    main()