import pytest
from medium_clone_suggestion.recommendation_engine import RecommendationSystem

class DummyDB:
    def __init__(self):
        self.history = ["seen1", "seen2"]
        self.articles = [
            {"postid": "a", "field": "X", "keywords":[["foo",1]], "topics":[], "entities":[], "summary":""},
            {"postid": "b", "field": "X", "keywords":[["bar",1]], "topics":[], "entities":[], "summary":""},
            {"postid": "seen1", "field": "X", "keywords":[["baz",1]], "topics":[], "entities":[], "summary":""},
        ]
    def get_user_history(self, uid): return self.history
    def get_user_profile(self, uid): return {"keywords":{"foo":1}, "topics":{}, "entities":{}, "preferred_fields":["X"]}
    def get_user_history_fields(self, uid): return ["X"]
    def fetch_unseen_articles(self, uid, fld, lim):
        return [a for a in self.articles if a["postid"] not in self.history and a["field"]==fld]
    def fetch_random_unseen(self, uid, fld, num):
        return [{"postid": p["postid"]} for p in self.fetch_unseen_articles(uid, fld, num)]
    def fetch_top_articles(self, limit): return ["a","b","seen1"]
    def fetch_article_metadata(self, ids):
        return {p["postid"]:{"keywords":p["keywords"],"topics":p["topics"],"entities":p["entities"]} for p in self.articles if p["postid"] in ids}
    def fetch_article_content(self, pid):
        return {"content": next(a for a in self.articles if a["postid"]==pid)["summary"]}

class DummyCache:
    def check_and_update_cache(self, *args, **kw): return None
    def set_cache(self, *args, **kw): pass

@pytest.fixture
def recsys(monkeypatch):
    sys = RecommendationSystem(testing_mode=True)
    monkeypatch.setattr(sys, "data_access", DummyDB())
    monkeypatch.setattr(sys, "cache_manager", DummyCache())
    return sys
