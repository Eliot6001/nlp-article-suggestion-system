#!/bin/bash
# Activate poetry environment and run tests

VENV_PATH=$(poetry env info --path)
source "$VENV_PATH/bin/activate"

echo "▶ Running all tests..."
pytest tests/ --tb=short --disable-warnings

echo "▶ Testing article_processor..."
pytest tests/article_processor --tb=short --disable-warnings

echo "▶ Testing user_processor..."
pytest tests/user_processor --tb=short --disable-warnings
