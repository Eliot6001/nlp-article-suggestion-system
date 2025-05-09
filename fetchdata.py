import os
import dotenv
from supabase import create_client

dotenv.load_dotenv()
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")

supabase = create_client(url, key)

result = supabase.table("article_metadata").select("*, posts(field)").execute() 

print(f"Data fetched {result}")