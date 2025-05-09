import json
import hashlib
import os
from typing import Dict, List
from datetime import datetime, timedelta
import copy

class CacheManager:
    def __init__(self, cache_file="cache.json"):
        self.cache_file = cache_file
        self.cache = {}
        self.load_cache_from_file()

    def load_cache_from_file(self):
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, 'r') as f:
                    loaded_cache = json.load(f)
                for key, value in loaded_cache.items():
                    if isinstance(value, dict) and 'ts' in value and isinstance(value['ts'], str):
                        try:
                            value['ts'] = datetime.fromisoformat(value['ts'])
                        except ValueError:
                            value['ts'] = None
                self.cache = loaded_cache
            except json.JSONDecodeError:
                self.cache = {}
            except Exception:
                self.cache = {}

    def save_cache_to_file(self):
        cache_to_save = copy.deepcopy(self.cache)
        for key, value in cache_to_save.items():
            if isinstance(value, dict) and 'ts' in value and isinstance(value['ts'], datetime):
                value['ts'] = value['ts'].isoformat()
        try:
            with open(self.cache_file, 'w') as f:
                json.dump(cache_to_save, f)
        except Exception:
            pass

    def set_cache(self, user_id: str, history_hash: str, value: Dict):
        cache_key = f"{user_id}-{history_hash}"
        self.cache[cache_key] = value
        self.save_cache_to_file()

    def check_and_update_cache(self, user_id: str, history: List[str], history_hash: str, timestamp: datetime, recs: list):
        cache_key = f"{user_id}-{history_hash}"
        cached_data = self.cache.get(cache_key)

        # Fix: Ensure history_hash is consistent with how it's generated in main code
        if history and not history_hash:
            history_hash = self._hash_history(history)
            cache_key = f"{user_id}-{history_hash}"
            cached_data = self.cache.get(cache_key)

        # Fix: Handle datetime comparison properly
        if cached_data and isinstance(cached_data.get('ts'), datetime):
            # Make sure timestamps have the same timezone info for comparison
            cached_ts = cached_data['ts']
            if cached_ts.tzinfo != timestamp.tzinfo:
                if cached_ts.tzinfo is None and timestamp.tzinfo is not None:
                    cached_ts = cached_ts.replace(tzinfo=timestamp.tzinfo)
                elif cached_ts.tzinfo is not None and timestamp.tzinfo is None:
                    timestamp = timestamp.replace(tzinfo=cached_ts.tzinfo)
                    
            if timestamp - cached_ts <= timedelta(hours=2):
                return cached_data.get("recs", [])

        # If no cached data or expired, just return empty list to signal cache miss
        return []

    def _hash_history(self, history_list):
        # Ensure this matches the hash_history function in the main code
        sorted_ids = sorted(history_list)
        serialized = json.dumps(sorted_ids, sort_keys=True)
        return hashlib.sha256(serialized.encode()).hexdigest()