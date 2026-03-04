#!/bin/sh
echo "🔍 Checking Knowledge Index (builds only if KB changed)..."
python3 -m app.backend.retrieval.build_index

echo "🚀 Starting WDD PulseX Backend (hot-reload enabled)..."
exec uvicorn app.backend.main:app --host 0.0.0.0 --port 8000 --reload --reload-dir app
