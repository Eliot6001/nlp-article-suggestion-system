import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Fields for categorization
FIELDS = [
    'Technology', 'Culture', 'Science', 'History', 'Geography',
    'Politics', 'Economics', 'Mathematics', 'Literature',
    'Performing Arts', 'Visual Arts', 'Health & Wellness', 'Sports',
    'Business & Finance', 'Environment'
]

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
CACHE_DIR = "recommendation_cache"