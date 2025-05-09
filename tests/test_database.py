def test_fetch_random_unseen_filters_seen(recsys):
    db = recsys.data_access
    unseen = db.fetch_random_unseen("u", "X", 10)
    ids = {d["postid"] for d in unseen}
    assert ids == {"a", "b"}
