# ============================================================
# PulseX-WDD — Makefile
# ============================================================

REPO_ROOT := $(shell pwd)
API_DIR   := $(REPO_ROOT)/apps/api
WEB_DIR   := $(REPO_ROOT)/apps/web
PY        := python3

.DEFAULT_GOAL := help

.PHONY: help setup dev api web index seed validate test lint build up down clean

help:		## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-16s\033[0m %s\n", $$1, $$2}'

setup:		## Install all dependencies (Python + Node)
	@echo "→ Installing Python dependencies..."
	cd $(REPO_ROOT) && pip install -r $(API_DIR)/requirements.txt
	@echo "→ Installing Node dependencies..."
	cd $(WEB_DIR) && npm install --legacy-peer-deps
	@echo "→ Creating runtime dirs..."
	mkdir -p $(REPO_ROOT)/runtime $(REPO_ROOT)/indices
	@echo "✅ Setup complete."

dev:		## Run API + Web concurrently (requires two terminals or tmux)
	@echo "→ Starting API on :8000 and Web on :3000"
	@trap 'kill %1; kill %2' SIGINT; \
	  (cd $(REPO_ROOT) && PYTHONPATH=$(API_DIR) uvicorn apps.api.app.main:app --reload --port 8000) & \
	  (cd $(WEB_DIR) && npm run dev) & \
	  wait

api:		## Run FastAPI backend only
	cd $(REPO_ROOT) && PYTHONPATH=$(API_DIR) uvicorn apps.api.app.main:app --reload --port 8000 --log-level info

web:		## Run Next.js frontend only
	cd $(WEB_DIR) && npm run dev

index:		## Build keyword (SQLite FTS5) + vector (FAISS) indices from buyerKB.csv
	@echo "→ Building retrieval indices..."
	cd $(REPO_ROOT) && PYTHONPATH=$(API_DIR) $(PY) scripts/build_index.py
	@echo "✅ Indices written to indices/"

seed:		## Seed runtime/leads.csv from runtime/leads_seed.csv
	@echo "→ Seeding leads..."
	cd $(REPO_ROOT) && PYTHONPATH=$(API_DIR) $(PY) scripts/seed_leads.py
	@echo "✅ Leads seeded."

validate:	## Validate buyerKB.csv (incl. installment-years false-positive check)
	@echo "→ Validating KB..."
	cd $(REPO_ROOT) && PYTHONPATH=$(API_DIR) $(PY) scripts/validate_kb.py

test:		## Run backend tests (pytest) + frontend lint
	@echo "→ Running pytest..."
	cd $(REPO_ROOT) && PYTHONPATH=$(API_DIR) pytest tests/ -v
	@echo "→ Running Next.js lint..."
	cd $(WEB_DIR) && npm run lint

lint:		## Lint backend Python files
	cd $(REPO_ROOT) && python -m flake8 apps/api/ scripts/ --max-line-length=110 --ignore=E501 || true

build:		## Build Next.js for production
	cd $(WEB_DIR) && npm run build

up:		## Start with Docker Compose
	docker compose up --build -d
	@echo "✅ API: http://localhost:8000  |  Web: http://localhost:3000"

down:		## Stop Docker Compose
	docker compose down

clean:		## Remove generated indices and __pycache__
	rm -rf $(REPO_ROOT)/indices/*.faiss $(REPO_ROOT)/indices/*.json $(REPO_ROOT)/indices/*.db
	find $(REPO_ROOT) -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
	find $(REPO_ROOT) -name "*.pyc" -delete 2>/dev/null || true
