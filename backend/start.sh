#!/usr/bin/env bash
# Start the NFP Article Formatter Flask backend
set -e

cd "$(dirname "$0")"

if [ ! -d ".venv" ]; then
  echo "Creating Python virtual environment…"
  python3 -m venv .venv
fi

echo "Installing/updating dependencies…"
.venv/bin/pip install -r requirements.txt -q

if [ ! -f ".env" ] && [ -f ".env.example" ]; then
  cp .env.example .env
  echo "Created .env from .env.example — add your ANTHROPIC_API_KEY"
fi

echo "Starting Flask on port 5001…"
FLASK_PORT=5001 DYLD_LIBRARY_PATH="/opt/homebrew/lib:${DYLD_LIBRARY_PATH}" .venv/bin/python app.py
