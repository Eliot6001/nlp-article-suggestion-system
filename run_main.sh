#!/bin/bash
# Activate poetry environment and run main FastAPI app

VENV_PATH=$(poetry env info --path)
source "$VENV_PATH/bin/activate"

echo "▶ Starting FastAPI server..."
uvicorn medium_clone_suggestion.main:app \
    --reload \
    --port 8800 \
    --app-dir src
