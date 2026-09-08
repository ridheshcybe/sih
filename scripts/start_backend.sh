#!/usr/bin/env bash
# Start the FastAPI backend on http://localhost:8000
set -e
cd "$(dirname "$0")/.."

if [ -f ".venv/Scripts/python.exe" ]; then
  PYTHON=".venv/Scripts/python.exe"
else
  PYTHON=".venv/bin/python"
fi

exec "$PYTHON" -m uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000