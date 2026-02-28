#!/usr/bin/env bash
# ============================================================
# PulseX-WDD — start.sh
# One-shot script to get the entire system running via Docker.
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

# ── 1. Prerequisite checks ────────────────────────────────────
info "Checking prerequisites..."

command -v docker >/dev/null 2>&1 || error "Docker is not installed. Install from https://docs.docker.com/get-docker/"

docker info >/dev/null 2>&1 || error "Docker daemon is not running. Please start Docker Desktop."

# docker compose (v2) check
if docker compose version >/dev/null 2>&1; then
  COMPOSE="docker compose"
elif docker-compose version >/dev/null 2>&1; then
  COMPOSE="docker-compose"
else
  error "docker compose not found. Install Docker Desktop (includes Compose v2)."
fi

success "Docker OK  (compose: $COMPOSE)"

# ── 2. .env check ────────────────────────────────────────────
if [ ! -f "$REPO/.env" ]; then
  if [ -f "$REPO/.env.example" ]; then
    warn ".env not found — copying from .env.example"
    cp "$REPO/.env.example" "$REPO/.env"
    echo ""
    echo -e "${YELLOW}  ┌─────────────────────────────────────────────────┐"
    echo -e "  │  ACTION REQUIRED: edit .env before continuing  │"
    echo -e "  │                                                 │"
    echo -e "  │  Required values:                               │"
    echo -e "  │    AZURE_OPENAI_ENDPOINT                        │"
    echo -e "  │    AZURE_OPENAI_API_KEY                         │"
    echo -e "  │    AZURE_OPENAI_CHAT_DEPLOYMENT                 │"
    echo -e "  │    AZURE_OPENAI_EMBED_DEPLOYMENT                │"
    echo -e "  │    ADMIN_PASSWORD   (pick a strong one)         │"
    echo -e "  └─────────────────────────────────────────────────┘${RESET}"
    echo ""
    read -rp "  Press ENTER once you've edited .env, or Ctrl-C to abort: "
  else
    error ".env and .env.example both missing. Cannot continue."
  fi
fi

# Warn if ADMIN_PASSWORD is still the default
ADMIN_PASS=$(grep -E '^ADMIN_PASSWORD=' "$REPO/.env" | cut -d= -f2 | tr -d '"' | tr -d "'")
if [[ "$ADMIN_PASS" == "changeme_use_strong_password" || -z "$ADMIN_PASS" ]]; then
  warn "ADMIN_PASSWORD is still the default. Update it in .env!"
fi

success ".env found"

# ── 3. Create runtime dirs + seed CSVs ───────────────────────
info "Ensuring runtime dirs and CSV headers..."
mkdir -p "$REPO/runtime" "$REPO/indices"

# Create headers-only CSVs if they don't exist
LEADS_HDR="timestamp,session_id,lang,name,phone,email,interest_projects,preferred_region,unit_type,budget_min,budget_max,budget_band,purpose,timeline,tags,consent_callback,consent_marketing,consent_timestamp,source_url,page_title,summary,raw_json"
AUDIT_HDR="timestamp,request_id,session_id,endpoint,intent,kb_version_hash,keyword_hits,vector_hits,blended_hits,top_entities_json,model,tokens_in,tokens_out,latency_ms,status,error_reason,cost_estimate_usd,message_hash"
SESS_HDR="session_id,created_at,last_seen,turn_count,lang,last_intent,page_url,ip_hash,user_agent"

[ ! -f "$REPO/runtime/leads.csv" ]    && echo "$LEADS_HDR"  > "$REPO/runtime/leads.csv"
[ ! -f "$REPO/runtime/audit.csv" ]    && echo "$AUDIT_HDR"  > "$REPO/runtime/audit.csv"
[ ! -f "$REPO/runtime/sessions.csv" ] && echo "$SESS_HDR"   > "$REPO/runtime/sessions.csv"

success "Runtime CSVs ready"

# ── 4. Build Docker images ────────────────────────────────────
info "Building Docker images (this may take a few minutes on first run)..."
$COMPOSE build --parallel
success "Images built"

# ── 5. Start services ─────────────────────────────────────────
info "Starting services..."
$COMPOSE up -d
success "Containers started"

# ── 6. Wait for API health ────────────────────────────────────
info "Waiting for API to be ready..."
MAX_RETRIES=30
COUNT=0
until curl -sf http://localhost:8000/api/health >/dev/null 2>&1; do
  COUNT=$((COUNT + 1))
  if [ "$COUNT" -ge "$MAX_RETRIES" ]; then
    echo ""
    warn "API did not become healthy within 60s. Check logs:"
    echo "  $COMPOSE logs api"
    break
  fi
  printf "."
  sleep 2
done
echo ""
success "API is healthy"

# ── 7. Print URLs ─────────────────────────────────────────────
echo ""
echo -e "${BOLD}════════════════════════════════════════════${RESET}"
echo -e "${GREEN}  PulseX-WDD is up and running! 🚀${RESET}"
echo -e "${BOLD}════════════════════════════════════════════${RESET}"
echo ""
echo -e "  🌐 Web (widget + landing):  ${CYAN}http://localhost:3000${RESET}"
echo -e "  🔑 Admin dashboard:         ${CYAN}http://localhost:3000/admin${RESET}"
echo -e "  🔌 Widget iframe demo:      ${CYAN}http://localhost:3000/widget${RESET}"
echo -e "  📡 API docs (dev):          ${CYAN}http://localhost:8000/api/docs${RESET}"
echo -e "  ❤️  API health:              ${CYAN}http://localhost:8000/api/health${RESET}"
echo ""
echo -e "  Admin password:  ${YELLOW}${ADMIN_PASS:-<see ADMIN_PASSWORD in .env>}${RESET}"
echo ""
echo -e "  To view logs:  docker compose logs -f"
echo -e "  To stop:       docker compose down"
echo ""
