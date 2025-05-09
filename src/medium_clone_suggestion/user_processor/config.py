import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    """Configuration settings for the user profile builder."""
    # Database
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_NAME = os.getenv("DB_NAME", "postgres")
    DB_USER = os.getenv("DB_USER", "postgres")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "postgres")
    DB_PORT = os.getenv("DB_PORT", "5432")
    
    # Processing
    BATCH_SIZE = 100
    MAX_HISTORY_DAYS = 2
    MIN_ENGAGEMENT_SCORE = 0.3
    USER_PROCESS_LIMIT = 1000  # Default limit of users to process
    
    # Freshness decay (exponential decay with daily decay rate)
    FRESHNESS_DECAY_RATE = 0.1  # 10% daily decay
    
    # Weights
    WEIGHTS = {
        "view": 1.0,
        "engagement_segments": {
            1: 1.5, 2: 2.0, 3: 3.0, 4: 4.0, 5: 5.0
        },
        "rating": 1.2
    }
    
    # Scheduling
    RUN_INTERVAL_HOURS = 8
    ENABLE_CACHING = True
    CACHE_TTL_HOURS = 24