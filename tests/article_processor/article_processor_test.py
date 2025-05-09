import pytest
from unittest.mock import MagicMock
from medium_clone_suggestion.article_processor.processing import ArticleProcessor

@pytest.fixture
def mock_model_manager():
    return MagicMock()

@pytest.fixture
def processor(mock_model_manager):
    # Patch summarizer and keyword extractor
    mock_summarizer = MagicMock()
    mock_summarizer.summarize.return_value = "This is a summary."

    mock_keyword_model = MagicMock()
    mock_keyword_model.extract_keywords.return_value = ["ai", "python"]
    mock_keyword_model.assign_field.return_value = "technology"

    # Patch model manager to return those
    mock_model_manager.get_summarizer.return_value = mock_summarizer
    mock_model_manager.get_keyword_model.return_value = mock_keyword_model

    processor = ArticleProcessor(mock_model_manager)
    processor.summarizer = mock_summarizer
    processor.keyword_extractor = mock_keyword_model
    return processor

def test_article_processor_basic_flow(processor):
    dummy_article = {"title": "Test", "content": "This is a long test article. " * 20}
    results = processor.process_batch([dummy_article])
    result = results[0]

    assert "summary" in result
    assert result["summary"] == "This is a summary."
    assert result["keywords"] == ["ai", "python"]
    assert result["field"] == "technology"
    assert result["is_gibberish"] is False
