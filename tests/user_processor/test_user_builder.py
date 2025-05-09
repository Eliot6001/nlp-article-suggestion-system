import pytest
from unittest.mock import MagicMock
from medium_clone_suggestion.user_processor.user_profile_builder import UserProfileBuilder

@pytest.fixture
def mock_config():
    mock = MagicMock()
    mock.USER_PROCESS_LIMIT = 2
    mock.MAX_HISTORY_DAYS = 30
    mock.MIN_ENGAGEMENT_SCORE = 0.1
    return mock

@pytest.fixture
def builder(mock_config):
    builder = UserProfileBuilder(mock_config)
    builder.db = MagicMock()
    builder.processor = MagicMock()
    return builder

def test_process_users_basic_flow(builder):
    builder.db.fetch_active_users.return_value = ['user1']
    builder.db.get_user_profile_last_updated.return_value = None
    builder.db.get_user_activities_since.return_value = [
        {'postid': 'p1', 'rating': 0.9, 'created_at': '2023-01-01T00:00:00Z'}
    ]
    builder.db.fetch_article_metadata.return_value = {'p1': {'keywords': ['AI']}}

    builder.processor.calculate_scores.return_value = (
        {'AI': 0.9}, {'Tech': 0.7}, {'EntityX': 0.5}
    )

    builder.process_users()

    builder.db.update_user_interests.assert_called_once()
    builder.db.update_user_profile_last_updated.assert_called_once()
