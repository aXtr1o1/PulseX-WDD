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
info "Hard-resetting Docker project state (Project: pulsex_master)..."
# Defensive ghost-kill for the specific ID corrupting the daemon metadata
docker rm -f 1ed41d6a385b991b71662b5f0584aadcc89bb9b3dd91bbf5cabd5aad3b396573 2>/dev/null || true
# Deep scrub of standard service names to flush daemon mappings
docker stop pulsex_api pulsex_web api web 2>/dev/null || true
docker rm -f pulsex_api pulsex_web api web 2>/dev/null || true
$COMPOSE -p pulsex_master down -v --remove-orphans --timeout 0 2>/dev/null || true

# ── 3. Free ports 8081 and 3001 if occupied ───────────────────
free_port() {
  local PORT=$1
  
  # A) Check for ALL Docker containers holding the port
  local CIDS
  CIDS=$(docker ps -a --filter "publish=$PORT" --format "{{.ID}}" 2>/dev/null || true)
  if [ -n "$CIDS" ]; then
    for CID in $CIDS; do
      local CNAME
      CNAME=$(docker inspect --format '{{.Name}}' "$CID" 2>/dev/null | sed 's/^\///')
      warn "Port $PORT is held by Docker container '$CNAME' ($CID) — forcing removal..."
      docker stop "$CID" 2>/dev/null || true
      docker rm -f "$CID" 2>/dev/null || true
    done
  fi

  # B) Check for local processes (dev servers, etc.)
  local PIDS
  PIDS=$(lsof -ti tcp:"$PORT" 2>/dev/null || true)
  if [ -z "$PIDS" ]; then return; fi

  warn "Port $PORT is occupied. Cleaning up..."
  for PID in $PIDS; do
    local PNAME
    PNAME=$(ps -p "$PID" -o comm= 2>/dev/null || true)
    warn "Killing '$PNAME' (PID $PID)..."
    kill -9 "$PID" 2>/dev/null || true
  done
  sleep 1
  success "Port $PORT freed"
}

info "Thermal Cleanup: Clearing stale network metadata..."
docker network prune -f 2>/dev/null || true

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
info "Ensuring runtime directories..."
mkdir -p "$REPO/runtime/index" "$REPO/runtime/leads" "$REPO/runtime/exports"

LEADS_CSV="$REPO/runtime/leads/leads.csv"
AUDIT_CSV="$REPO/runtime/leads/audit.csv"

LEADS_HDR="timestamp,lead_id,session_id,name,phone,email,interest_projects,interest_projects_display,preferred_region,unit_type,budget_min,budget_max,budget_band,purpose,timeline,contact_channel,consent_contact,confirmed_by_user,lead_temperature,reason_codes,reason_codes_display,tags,tags_display,lead_summary,raw_json,kb_version_hash"
AUDIT_HDR="timestamp,session_id,intent,empty_retrieval,top_entities_json,latency_ms,status,error_reason"

[ ! -f "$LEADS_CSV" ] && echo "$LEADS_HDR" > "$LEADS_CSV"
[ ! -f "$AUDIT_CSV" ] && echo "$AUDIT_HDR" > "$AUDIT_CSV"

success "Runtime ready"

# ── 6. Build images ───────────────────────────────────────────
info "Building Docker images (may take ~2 min on first run)..."
$COMPOSE -p pulsex_master build
success "Images built"

# ── 7. Start services ─────────────────────────────────────────
info "Starting containers..."
$COMPOSE -p pulsex_master up -d
success "Containers started"

# ── 8. Wait for API health ────────────────────────────────────
info "Waiting for API to become healthy..."
MAX=40
COUNT=0
until curl -sf http://localhost:8081/api/health >/dev/null 2>&1; do
  COUNT=$((COUNT + 1))
  [ "$COUNT" -ge "$MAX" ] && { echo ""; warn "API health timeout. Check logs: $COMPOSE logs pulsex_api"; break; }
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
echo -e "  🌐  Concierge:           ${CYAN}http://localhost:3001${RESET}"
echo -e "  🔑  Admin dashboard:     ${CYAN}http://localhost:3001/admin${RESET}"
echo -e "  🔌  Widget iframe:       ${CYAN}http://localhost:3001/widget${RESET}"
echo -e "  📡  API (health check):  ${CYAN}http://localhost:8081/api/health${RESET}"
echo -e "  📖  API docs (Swagger):  ${CYAN}http://localhost:8081/docs${RESET}"
echo ""
[ -n "$ADMIN_PASS" ] && echo -e " If needed, Admin password: ${YELLOW}${ADMIN_PASS}${RESET}"
echo ""
  echo -e "  View logs:  ${BOLD}docker compose -p pulsex_master logs -f${RESET}"
  echo -e "  Stop:       ${BOLD}docker compose -p pulsex_master down${RESET}"
echo ""
