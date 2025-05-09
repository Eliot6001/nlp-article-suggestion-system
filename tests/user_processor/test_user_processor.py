import pytest
from datetime import datetime, timedelta, timezone
from medium_clone_suggestion.user_processor.processing import ProfileProcessor

class DummyConfig:
    FRESHNESS_DECAY_RATE = 0.1
    WEIGHTS = {
        "view": 1.0,
        "rating": 2.0,
        "engagement_segments": {
            0: 1.0,
            1: 1.5,
            2: 2.0
        }
    }

@pytest.fixture
def processor():
    return ProfileProcessor(DummyConfig())

def test_calculate_freshness_factor_recent(processor):
    now = datetime.now(timezone.utc)
    factor = processor.calculate_freshness_factor(now.isoformat())
    assert round(factor, 2) == 1.0

def test_calculate_freshness_factor_older(processor):
    old = datetime.now(timezone.utc) - timedelta(days=10)
    factor = processor.calculate_freshness_factor(old.isoformat())
    assert round(factor, 2) < 1.0

def test_calculate_engagement_weight(processor):
    recent = datetime.now(timezone.utc)
    weight = processor.calculate_engagement_weight(segment=2, created_at=recent)
    assert weight > 1.0

def test_get_activity_weight_all_types(processor):
    recent = datetime.now(timezone.utc).isoformat()
    activity = {
        "created_at": recent,
        "activity_type": "engagement_and_rating",
        "segment": 1,
        "rating": 0.8
    }
    weight = processor._get_activity_weight(activity)
    assert weight > 0  # exact value depends on freshness factor

def test_calculate_scores(processor):
    now = datetime.now(timezone.utc).isoformat()
    activities = [
        {
            "postid": "p1",
            "activity_type": "engagement",
            "segment": 2,
            "created_at": now
        },
        {
            "postid": "p2",
            "activity_type": "rating",
            "rating": 0.5,
            "created_at": now
        }
    ]

    metadata = {
        "p1": {
            "keywords": [("neuro", 0.9)],
            "topics": ["brain"],
            "entities": [{"name": "cortex"}]
        },
        "p2": {
            "keywords": [("ai", 0.9)],
            "topics": ["tech"],
            "entities": [{"name": "GPT"}]
        }
    }

    k, t, e = processor.calculate_scores(activities, metadata)
    assert "neuro" in k and "ai" in k
    assert "brain" in t and "tech" in t
    assert "cortex" in e and "GPT" in e
    assert all(0 <= v <= 1 for v in k.values())
