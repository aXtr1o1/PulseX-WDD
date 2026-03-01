#!/usr/bin/env bash
set -e

echo "→ Starting API for E2E..."
export ADMIN_AUTH_MODE=off
export APP_ENV=test
export PYTHONPATH=apps/api

# Run uvicorn in background
uvicorn apps.api.app.main:app --port 8001 > /dev/null 2>&1 &
PID=$!

function cleanup {
  echo "→ Stopping API ($PID)..."
  kill $PID || true
}
trap cleanup EXIT

echo "→ Waiting for API to start..."
sleep 4

echo "→ Checking /api/health"
curl -sSf http://localhost:8001/api/health | grep -q '"status":"ok"'
echo "  ✅ Health check passed."

echo "→ Checking /api/chat (greeting)"
curl -sSf -X POST -H "Content-Type: application/json" \
  -d '{"message":"hi","lang":"en","session_id":"smoke1"}' \
  http://localhost:8001/api/chat | grep -q '"intent_lane":"greeting"'
echo "  ✅ Chat greeting recognized."

echo "→ Checking /api/chat (sales intent)"
curl -sSf -X POST -H "Content-Type: application/json" \
  -d '{"message":"I want to book a visit at Murano","lang":"en","session_id":"smoke1"}' \
  http://localhost:8001/api/chat | grep -q '"intent_lane":"sales_intent"'
echo "  ✅ Chat sales intent recognized."

echo "→ Checking /api/admin/dashboard (bypass check)"
curl -sSf http://localhost:8001/api/admin/dashboard | grep -q '"total_leads"'
echo "  ✅ Admin dashboard accessed without auth."

echo "✅ All E2E smoke checks passed."
