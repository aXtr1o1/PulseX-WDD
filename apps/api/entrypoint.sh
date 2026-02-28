#!/usr/bin/env bash
# API container entrypoint
# 1. Seeds runtime CSVs (idempotent)
# 2. Builds indices if missing
# 3. Starts uvicorn
set -e

PYTHONPATH=/app/apps/api
export PYTHONPATH

echo "→ Seeding runtime CSVs..."
python scripts/seed_leads.py 2>/dev/null || echo "  (seed skipped — no seed file)"

echo "→ Checking retrieval indices..."
if [ ! -f "/app/indices/keyword_index.db" ]; then
  echo "  Building indices (first run)..."
  python scripts/build_index.py
else
  echo "  Indices already present — skipping build."
fi

echo "→ Starting PulseX-WDD API..."
exec uvicorn apps.api.app.main:app \
  --host 0.0.0.0 \
  --port 8000 \
  --workers 2 \
  --log-level info
