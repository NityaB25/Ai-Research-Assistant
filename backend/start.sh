#!/usr/bin/env bash
set -e

echo "🔍 Checking environment..."

if [ ! -f .env ]; then
  cp .env.example .env
  echo "⚠️  Created .env from .env.example — please add your OPENROUTER_API_KEY"
  exit 1
fi

source .env
if [ -z "$OPENROUTER_API_KEY" ] || [ "$OPENROUTER_API_KEY" = "your_openrouter_api_key_here" ]; then
  echo "❌ OPENROUTER_API_KEY is not set in .env"
  exit 1
fi

echo "📦 Installing dependencies..."
pip install -r requirements.txt -q

echo "🚀 Starting FastAPI server on http://localhost:8000"
echo "📖 API docs at http://localhost:8000/docs"
uvicorn main:app --reload --host 0.0.0.0 --port 8000
