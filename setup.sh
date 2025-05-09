#!/bin/bash
# One-time setup: Python 3.10, poetry, dependencies, lockfile

echo "▶ Creating Python 3.10 virtualenv..."
pyenv install 3.10.13 -s
pyenv local 3.10.13

echo "▶ Installing poetry if missing..."
pip install --user poetry

echo "▶ Installing project dependencies..."
poetry install

echo "▶ Installing requirements.txt for non-poetry systems..."
poetry export --without-hashes --format=requirements.txt > requirements.txt

echo "✔ Setup complete."
