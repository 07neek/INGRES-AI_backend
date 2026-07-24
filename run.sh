#!/usr/bin/env bash
# One-command setup + run. Safe to re-run — skips steps already done.
set -e
cd "$(dirname "$0")"

if [ ! -d ".venv" ]; then
  echo "Creating virtual environment..."
  python3 -m venv .venv
fi

. .venv/bin/activate

echo "Installing dependencies..."
pip install -q -r requirements.txt

if [ ! -f ".env" ]; then
  cp .env.example .env
  echo "Created .env from .env.example — edit it to add your real GROQ_API_KEY / WATER_DATA_* values."
fi

echo "Starting server on http://localhost:8000 (docs at /docs, Ctrl+C to stop)..."
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
