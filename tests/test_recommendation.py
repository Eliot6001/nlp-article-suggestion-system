def test_recommend_length_and_fields(recsys):
    recs = recsys.recommend_articles("u", num_recommendations=2, exploration_ratio=0.0)
    # should get 2 items, none with postid in history
    assert len(recs) == 2
    assert all(r["postid"] not in ["seen1","seen2"] for r in recs)

def test_exploitation_only(recsys):
    # force exploration_ratio=0 so only pf_scored returned
    recs = recsys.recommend_articles("u", num_recommendations=1, exploration_ratio=0.0)
    # since profile keyword="foo" matches article "a", that should come first
    assert recs[0]["postid"] == "a"

def test_exploration_fallback(recsys, monkeypatch):
    db = recsys.data_access

    # Kill primary fetch
    monkeypatch.setattr(db, "fetch_unseen_articles", lambda *a, **kw: [])

    # Force fallback to return a dummy post
    monkeypatch.setattr(db, "fetch_random_unseen", lambda *a, **kw: [{"postid": "dummy"}])

    recs = recsys.recommend_articles("u", num_recommendations=1, exploration_ratio=0.0)
    assert len(recs) == 1
    assert recs[0]["postid"] == "dummy"

