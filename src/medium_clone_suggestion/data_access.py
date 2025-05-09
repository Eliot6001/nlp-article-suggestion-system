import os
import json
import re
from typing import List, Dict, Optional
from supabase import create_client, Client
from medium_clone_suggestion.config import SUPABASE_URL, SUPABASE_KEY
from bs4 import BeautifulSoup


# Typically a useless file, it has lots of my mockup phase data interaction
# Shouldn't be used as a reference for anything.
class DataAccess:
    def __init__(self, testing_mode: bool = True):
        self.testing_mode = testing_mode
        self.supabase = self._initialize_supabase()

    def _initialize_supabase(self) -> Optional[Client]:
        if not self.testing_mode:
            if not SUPABASE_URL or not SUPABASE_KEY:
                raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in .env file")
            return create_client(SUPABASE_URL, SUPABASE_KEY)
        else:
            print("Running in testing mode with local files")
            return None

    def fetch_articles(self, field: str, limit: int = 100) -> List[Dict]:
        if self.testing_mode:
            return self._fetch_test_articles(field, limit)

        if self.supabase:
            result = (self.supabase
                     .table("posts")
                     .select("postid, title, content, field")
                     .eq("field", field)
                     .limit(limit)
                     .execute())

            if result.data:
                post_ids = [article["postid"] for article in result.data]
                metadata_result = (self.supabase
                                  .table("article_metadata")
                                  .select("*")
                                  .in_("postid", post_ids)
                                  .execute())

                metadata_lookup = {item["postid"]: item for item in metadata_result.data}

                for article in result.data:
                    article_id = article["postid"]
                    if article_id in metadata_lookup:
                        article.update(metadata_lookup[article_id])

                return result.data
        return []

    def _fetch_test_articles(self, field: str, limit: int) -> List[Dict]:
        """
        Fetch test articles from local files with HTML cleanup and field filtering.
        """
        articles = []

        # result.txt – structured metadata
        try:
            with open("result.txt", "r") as f:
                content = f.read()
                article_blocks = re.split(r'\n\n(?=Article ID:|Title:)', content)

                for block in article_blocks:
                    if not block.strip():
                        continue

                    article = {}

                    # ID
                    id_match = re.search(r'Article ID: ([\w-]+)', block)
                    if id_match:
                        article["postid"] = id_match.group(1)

                    # Title
                    title_match = re.search(r'Title: (.+)', block)
                    if title_match:
                        article["title"] = title_match.group(1)

                    # Field
                    field_match = re.search(r'field: (.+)', block)
                    if field_match and field_match.group(1).strip() == field:
                        article["field"] = field_match.group(1).strip()
                    elif field.lower() == "any" or not field:
                        if field_match:
                            article["field"] = field_match.group(1).strip()
                    else:
                        continue  # skip if field mismatch

                    # Summary
                    summary_match = re.search(r'Summary: (.+)', block)
                    if summary_match:
                        article["summary"] = summary_match.group(1)

                    # Keywords
                    keywords_match = re.search(r'Keywords: (.+)', block)
                    if keywords_match:
                        article["keywords"] = [k.strip() for k in keywords_match.group(1).split(",")]
                    print(f"keywords: {keywords_match}")
                    # Topics
                    topics_match = re.search(r'Topics: (.+)', block)
                    if topics_match:
                        article["topics"] = [t.strip() for t in topics_match.group(1).split(",")]

                    # Entities
                    entities_block = re.search(r'Entities:\s+([\s\S]+?)(?=\n\w+:|$)', block)
                    if entities_block:
                        entities_text = entities_block.group(1).strip()
                        entities = {}
                        for line in entities_text.split('\n'):
                            if ':' in line:
                                entity_type, values = line.split(':', 1)
                                entities[entity_type.strip()] = [v.strip() for v in values.strip().split(',')]
                        article["entities"] = entities

                    articles.append(article)
        except FileNotFoundError:
            print("result.txt not found.")

        # text.txt – HTML cleanup
        try:
            with open("text.txt", "r") as f:
                content = f.read()
                article_blocks = re.split(r'\n\n(?=ID:|Title:)', content)

                for block in article_blocks:
                    if not block.strip():
                        continue

                    article = {}

                    id_match = re.search(r'ID: ([\w-]+)', block)
                    if id_match:
                        article["postid"] = id_match.group(1)

                    title_match = re.search(r'Title: (.+)', block)
                    if title_match:
                        article["title"] = title_match.group(1)

                    content_match = re.search(r'Content: (.+)', block, re.DOTALL)
                    if content_match:
                        raw_html = content_match.group(1).strip()
                        clean_text = BeautifulSoup(raw_html, "html.parser").get_text(separator=' ', strip=True)

                        # skip if text is too short or looks spammy
                        if len(clean_text) < 50 or re.search(r'(test|shgit|hail|wowohoo)', clean_text, re.I):
                            continue

                        article["summary"] = clean_text

                    article["field"] = field if field else "Unknown"
                    articles.append(article)
        except FileNotFoundError:
            print("text.txt not found.")
        print(f"articles fetched ${articles}")
        return articles[:limit]

    def get_user_history(self, user_id: str) -> List[str]:
        if self.testing_mode:
            return []
        if self.supabase:
            result = (self.supabase
                     .table("history")
                     .select("postid")
                     .eq("userid", user_id)
                     .execute())
            return [item["postid"] for item in result.data] if result.data else []
        return []

    def get_user_profile(self, user_id: str) -> Dict:
        if self.testing_mode:
            with open("user_processed.txt", "r") as f:
                lines = f.read().split("==================================================")
                for block in lines:
                    block = block.strip()
                    if not block:
                        continue
                    if f"User ID: {user_id}" in block:
                        parts = block.split("\n", 1)
                        if len(parts) == 2:
                            try:
                                data = json.loads(parts[1].strip())
                                # Convert weighted dicts to flat list for old components
                                flat_interests = set()
                                for key in ["keywords", "topics", "entities"]:
                                    flat_interests.update(data.get(key, {}).keys())

                                return {
                                    "interests": list(flat_interests),
                                    "preferred_fields": ["History", "Culture", "Geography"],  # fallback or dynamically extract later
                                    "activity_weight": {
                                        "Culture": 0.8,
                                        "History": 0.6,
                                        "Geography": 0.5
                                    },
                                    **data
                                }
                            except json.JSONDecodeError as e:
                                print(f"JSON parsing error: {e}")
                                print(f"[ERROR] User ID {user_id} not found.")
                                return {}
        if self.supabase:
            result = (self.supabase
                     .table("user_profiles")
                     .select("*")
                     .eq("userid", user_id)
                     .execute())
            return result.data[0] if result.data else {}
        return {}

    def get_user_profile_processed(self, user_id: str) -> Dict:
        if not self.testing_mode:
            raise NotImplementedError("Processed user profile only available in testing mode")

        try:
            with open("user_processed.txt", "r") as f:
                content = f.read()
                blocks = re.split(r'\n(?=User ID:)', content)
                for block in blocks:
                    if f"User ID: {user_id}" in block:
                        json_match = re.search(r'{[\s\S]+}', block)
                        if json_match:
                            return json.loads(json_match.group(0))
        except FileNotFoundError:
            print("user_processed.txt not found.")
        return {}
