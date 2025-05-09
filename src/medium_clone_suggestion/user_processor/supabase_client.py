from supabase import create_client, Client
import os

class SupabaseClient:
    def __init__(self):
        self.url = os.environ.get("SUPABASE_URL")
        self.key = os.environ.get("SUPABASE_KEY")
        self.client = create_client(self.url, self.key)

    def get_client(self) -> Client:
        return self.client