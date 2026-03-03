#!/usr/bin/env bash
# ============================================================
# PulseX-WDD — start.sh
# One-shot script: builds and starts everything via Docker.
# Usage: bash start.sh
# ============================================================

set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$REPO"

# ── Colours ──────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; BOLD='\033[1m'; RESET='\033[0m'

info()    { echo -e "${CYAN}→${RESET} $*"; }
success() { echo -e "${GREEN}✅${RESET} $*"; }
warn()    { echo -e "${YELLOW}⚠️${RESET}  $*"; }
error()   { echo -e "${RED}❌ ERROR:${RESET} $*" >&2; exit 1; }

echo -e "\n${BOLD}PulseX-WDD — Starting...${RESET}\n"

# ── 1. Docker check ───────────────────────────────────────────
info "Checking prerequisites..."

command -v docker >/dev/null 2>&1 || error "Docker not installed. Get it from https://docs.docker.com/get-docker/"
docker info >/dev/null 2>&1 || error "Docker daemon is not running. Please start Docker Desktop."

if docker compose version >/dev/null 2>&1; then
  COMPOSE="docker compose"
elif docker-compose version >/dev/null 2>&1; then
  COMPOSE="docker-compose"
else
  error "docker compose not found. Install Docker Desktop (v2+)."
fi

success "Docker OK"

# ── 2. Stop any existing PulseX containers ────────────────────
info "Stopping any existing PulseX containers..."
$COMPOSE down --remove-orphans 2>/dev/null || true

# ── 3. Free ports 8000 and 3000 if occupied ───────────────────
free_port() {
  local PORT=$1
  # Get all PIDs on this port
  local PIDS
  PIDS=$(lsof -ti tcp:"$PORT" 2>/dev/null || true)
  if [ -z "$PIDS" ]; then return; fi

  # Only kill known safe dev-server processes; never kill Docker internals
  local SAFE_NAMES="uvicorn|node|python|python3|next"
  local KILLED=0
  for PID in $PIDS; do
    local PNAME
    PNAME=$(ps -p "$PID" -o comm= 2>/dev/null || true)
    if echo "$PNAME" | grep -qiE "$SAFE_NAMES"; then
      warn "Port $PORT in use by '$PNAME' (PID $PID) — stopping it..."
      kill -9 "$PID" 2>/dev/null || true
      KILLED=1
    else
      warn "Port $PORT in use by '$PNAME' (PID $PID) — skipping (not a dev server)"
    fi
  done
  if [ "$KILLED" -eq 1 ]; then
    sleep 1
    success "Port $PORT freed"
  fi
}

free_port 8081
free_port 3001

# ── 4. .env check ────────────────────────────────────────────
if [ ! -f "$REPO/.env" ]; then
  if [ -f "$REPO/.env.example" ]; then
    warn ".env not found — copying from .env.example"
    cp "$REPO/.env.example" "$REPO/.env"
    echo ""
    echo -e "${YELLOW}  ┌─────────────────────────────────────────────────┐"
    echo -e "  │  ACTION REQUIRED: edit .env before continuing  │"
    echo -e "  │                                                 │"
    echo -e "  │    AZURE_OPENAI_ENDPOINT                        │"
    echo -e "  │    AZURE_OPENAI_API_KEY                         │"
    echo -e "  │    AZURE_OPENAI_CHAT_DEPLOYMENT                 │"
    echo -e "  │    AZURE_OPENAI_EMBED_DEPLOYMENT                │"
    echo -e "  │    ADMIN_PASSWORD   ← pick a strong one         │"
    echo -e "  └─────────────────────────────────────────────────┘${RESET}"
    echo ""
    read -rp "  Press ENTER after editing .env (Ctrl-C to abort): "
  else
    error ".env and .env.example both missing."
  fi
fi

ADMIN_PASS=$(grep -E '^ADMIN_PASSWORD=' "$REPO/.env" | cut -d= -f2- | tr -d '"' | tr -d "'" | xargs)
if [[ "$ADMIN_PASS" == "changeme_use_strong_password" || -z "$ADMIN_PASS" ]]; then
  warn "ADMIN_PASSWORD is still the default — update it in .env!"
fi

success ".env OK"

# ── 5. Ensure runtime dirs + CSV headers ─────────────────────
info "Ensuring runtime directories and CSV headers..."
mkdir -p "$REPO/runtime" "$REPO/indices"

LEADS_HDR="timestamp,session_id,lang,name,phone,email,interest_projects,preferred_region,unit_type,budget_min,budget_max,budget_band,purpose,timeline,tags,consent_callback,consent_marketing,consent_timestamp,source_url,page_title,summary,raw_json"
AUDIT_HDR="timestamp,request_id,session_id,endpoint,intent,kb_version_hash,keyword_hits,vector_hits,blended_hits,top_entities_json,model,tokens_in,tokens_out,latency_ms,status,error_reason,cost_estimate_usd,message_hash"
SESS_HDR="session_id,created_at,last_seen,turn_count,lang,last_intent,page_url,ip_hash,user_agent"

[ ! -f "$REPO/runtime/leads.csv" ]    && echo "$LEADS_HDR"  > "$REPO/runtime/leads.csv"
[ ! -f "$REPO/runtime/audit.csv" ]    && echo "$AUDIT_HDR"  > "$REPO/runtime/audit.csv"
[ ! -f "$REPO/runtime/sessions.csv" ] && echo "$SESS_HDR"   > "$REPO/runtime/sessions.csv"

success "Runtime ready"

# ── 6. Build images ───────────────────────────────────────────
info "Building Docker images (parallel, may take ~2 min on first run)..."
$COMPOSE build --parallel
success "Images built"

# ── 7. Start services ─────────────────────────────────────────
info "Starting containers..."
$COMPOSE down --remove-orphans 2>/dev/null || true
$COMPOSE up -d --force-recreate
success "Containers started"

# ── 8. Wait for API health ────────────────────────────────────
info "Waiting for API to become healthy..."
MAX=40
COUNT=0
until curl -sf http://localhost:8081/api/health >/dev/null 2>&1; do
  COUNT=$((COUNT + 1))
  [ "$COUNT" -ge "$MAX" ] && { echo ""; warn "API health timeout. Check logs: $COMPOSE logs api"; break; }
  printf "."
  sleep 2
done
echo ""
success "API is healthy"

# ── 9. Done ───────────────────────────────────────────────────
echo ""
echo -e "${BOLD}════════════════════════════════════════════════${RESET}"
echo -e "${GREEN}  PulseX-WDD is running! 🚀${RESET}"
echo -e "${BOLD}════════════════════════════════════════════════${RESET}"
echo ""
echo -e "  🌐  Landing + Widget:    ${CYAN}http://localhost:3001${RESET}"
echo -e "  🔑  Admin dashboard:     ${CYAN}http://localhost:3001/admin${RESET}"
echo -e "  🔌  Widget iframe:       ${CYAN}http://localhost:3001/widget${RESET}"
echo -e "  📡  API (health check):  ${CYAN}http://localhost:8081/api/health${RESET}"
echo -e "  📖  API docs (dev):      ${CYAN}http://localhost:8081/api/docs${RESET}"
echo ""
[ -n "$ADMIN_PASS" ] && echo -e "  Admin password: ${YELLOW}${ADMIN_PASS}${RESET}"
echo ""
echo -e "  View logs:  ${BOLD}docker compose logs -f${RESET}"
echo -e "  Stop:       ${BOLD}docker compose down${RESET}"
echo ""
