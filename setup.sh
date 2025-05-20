#!/bin/bash
# One-time setup: Poetry, Python 3.10, dependencies, lockfile

echo "▶️ Installing poetry if missing..."
# Check if poetry is already installed to avoid re-installing if not necessary
if ! command -v poetry &> /dev/null
then
    echo "   Poetry not found, installing..."
    pip install --user poetry
    # Ensure Poetry is in PATH (common issue, especially with --user install)
    export PATH="$HOME/.local/bin:$PATH"
    echo "   Poetry installed. Please ensure '$HOME/.local/bin' is in your PATH."
    echo "   You might need to open a new terminal session for the PATH change to take effect."
else
    echo "   Poetry is already installed."
fi

echo "▶️ IMPORTANT: Make sure Python 3.10 is installed and accessible."
echo "   Poetry will attempt to use 'python3.10' or a compatible version."

echo "▶️ Initializing Python 3.10 virtualenv with Poetry..."
# Poetry will try to find python3.10. If it can't, this step might fail or pick another Python.
# You can be more explicit if you know the exact path to your python3.10 interpreter,
# e.g., poetry env use /usr/bin/python3.10
poetry env use python3.10

echo "▶️ Installing project dependencies via poetry..."
poetry install

echo "▶️ Installing additional packages (uvicorn, requirements.txt) within poetry env..."

VENV_PATH=$(poetry env info --path 2>/dev/null) 

if [ -n "$VENV_PATH" ] && [ -f "$VENV_PATH/bin/activate" ]; then
  echo "   Activating virtualenv: $VENV_PATH"
  source "$VENV_PATH/bin/activate"

  if [ -f "requirements.txt" ]; then
    echo "   Installing requirements.txt..."
    pip install -r requirements.txt
  else
    echo "   requirements.txt not found, skipping."
  fi

  echo "   Installing uvicorn..."
  pip install uvicorn

 
else
  echo "⚠️ Could not reliably determine or activate poetry environment."
  echo "   If 'poetry install' created an environment, it might not be active for the pip installs."
  echo "   Consider running 'poetry shell' then 'pip install -r requirements.txt' and 'pip install uvicorn' manually if needed."
fi

echo "✅ Setup complete."
echo "   If a Poetry environment was successfully activated by this script, it remains active in this script's session."
echo "   To use it in your terminal for subsequent commands, run 'poetry shell'."