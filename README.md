# PulseX-WDD

**Production-grade Web Concierge + Hybrid RAG Knowledge Engine + Lead Intelligence Admin Dashboard**
Built for **Wadi Degla Developments (WDD)**.

---

## System Components

| Component | Tech | Port |
|-----------|------|------|
| FastAPI backend | Python 3.11 + uvicorn | 8000 |
| Next.js frontend | Next.js 14 App Router + TypeScript | 3000 |
| Retrieval engine | SQLite FTS5 + FAISS (hybrid) | — |
| Data layer | CSV-first (portalocker-safe) | — |

---

## Prerequisites

- Python 3.11 (`python3.11`)
- Node.js 18+
- A valid `.env` file (copy from `.env.example`)

```bash
cp .env.example .env
# Edit .env and add:
# AZURE_OPENAI_API_KEY, AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_CHAT_DEPLOYMENT
# AZURE_OPENAI_EMBED_DEPLOYMENT, ADMIN_PASSWORD
```

---

## Quick Start (Local)

```bash
# 1. Install all dependencies
make setup

# 2. Build retrieval indices (requires valid embedding API key)
make index

# 3. Seed demo leads
make seed

# 4. Validate KB
make validate

# 5. Run backend + frontend (two concurrent processes)
make dev
# Or run separately:
#   Terminal 1: make api    → http://localhost:8000
#   Terminal 2: make web    → http://localhost:3000
```

Open:
- 🌐 **Landing + Widget**: http://localhost:3000
- 🔑 **Admin Dashboard**: http://localhost:3000/admin
- 📦 **Widget embed demo**: http://localhost:3000/widget
- 📡 **API docs** (dev only): http://localhost:8000/api/docs

---

## Docker Compose

```bash
# Build and start
make up          # → api:8000 + web:3000

# Stop
make down
```

---

## Project Structure

```
PulseX-WDD/
├── apps/
│   ├── api/                  FastAPI backend
│   │   ├── app/
│   │   │   ├── config.py     Settings (pydantic-settings)
│   │   │   ├── main.py       App factory + lifespan
│   │   │   ├── routers/      chat.py, lead.py, admin.py
│   │   │   ├── services/     answer.py, retrieval.py, router.py, lead.py, audit.py
│   │   │   ├── middleware/   auth.py (cookie session)
│   │   │   ├── schemas/      models.py (Pydantic v2)
│   │   │   └── utils/        csv_io.py, kb_loader.py
│   │   ├── requirements.txt
│   │   └── Dockerfile
│   └── web/                  Next.js 14 App Router
│       ├── app/              layout.tsx, page.tsx, admin/page.tsx, widget/page.tsx
│       ├── components/
│       │   ├── widget/       ChatWidget, MessageBubble, LeadForm, IntentChips, ConsentBlock
│       │   ├── admin/        KPITile, Charts, LeadTable, LeadDrawer, DataViewer
│       │   └── ui/           Button, Card, Drawer, Badge, Spinner
│       ├── lib/              api.ts, i18n.ts, gtm.ts
│       ├── public/
│       │   ├── brand/        WDD_blockLogo.png, WDD_fullLogo.png
│       │   └── widget.js     Embeddable script
│       └── Dockerfile
├── scripts/
│   ├── build_index.py        Build SQLite FTS5 + FAISS indices
│   ├── validate_kb.py        Validate buyerKB.csv
│   └── seed_leads.py         PalmX-grade Lead & Telemetry Generator (Deterministic)
├── engine-KB/                PulseX-WDD_buyerKB.csv
├── runtime/                  leads.csv, audit.csv, sessions.csv, leads_seed.csv
├── indices/                  keyword_index.db, vectors.faiss, metadata.json (generated)
├── docs/                     ARCHITECTURE.md, RAG_GATING.md, SECURITY.md
├── Makefile
├── docker-compose.yml
├── .env.example
└── README.md
```

---

## Embedding Widget on WDD Website

```html
<script
  src="https://your-pulsex-domain.com/widget.js"
  data-project="murano"
  data-region="ain-sokhna"
  data-lang="en"
  defer
></script>
```

**Attributes:**
- `data-project` — slug of the project page (gates retrieval to that project)
- `data-region` — region context hint
- `data-lang` — `en` or `ar` (auto-selected by language picker in widget)

---

## API Reference

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/api/chat` | — | Non-streaming chat |
| POST | `/api/chat/stream` | — | SSE streaming chat |
| POST | `/api/lead` | — | Submit lead |
| POST | `/api/admin/login` | — | Admin login (sets cookie) |
| POST | `/api/admin/logout` | Cookie | Admin logout |
| GET | `/api/admin/dashboard` | Cookie | KPIs + trends |
| GET | `/api/admin/leads` | Cookie | Filtered leads list |
| GET | `/api/admin/sheets/{sheet}/rows` | Cookie | Sheet rows (paginated) |
| GET | `/api/admin/sheets/{sheet}/download/csv` | Cookie | Download CSV |
| GET | `/api/admin/sheets/{sheet}/download/xlsx` | Cookie | Download XLSX |
| GET | `/api/health` | — | Health check |

---

## GTM Events

| Event | Trigger |
|-------|---------|
| `pulseX_session_start` | Widget opened, language selected |
| `pulseX_intent_selected` | User taps an intent chip |
| `pulseX_lead_qualified` | Lead form submitted |
| `pulseX_handoff_success` | Sales handoff completed |
| `pulseX_callback_requested` | "Request a Sales Call" tapped |
| `pulseX_consent_opt_in` | Consent checkboxes submitted |

---

## Makefile Targets

```bash
make setup      # Install all deps
make dev        # Run API + Web concurrently
make api        # Run backend only (:8000)
make web        # Run frontend only (:3000)
make index      # Build FTS5 + FAISS indices
make seed       # Seed leads.csv from leads_seed.csv
make validate   # Validate buyerKB.csv
make test       # Run pytest + Next lint
make build      # Build Next.js production bundle
make up         # Docker Compose up
make down       # Docker Compose down
make clean      # Remove generated indices + pycache
```

---

## Runtime CSVs

All appends are concurrency-safe via `portalocker`.

| File | Purpose |
|------|---------|
| `runtime/leads.csv` | Captured leads (append-only) |
| `runtime/audit.csv` | Every chat request (cost, latency, model) |
| `runtime/sessions.csv` | Session metadata |
| `runtime/leads_seed.csv` | Demo seed data |

---

## Security

- Admin password: `ADMIN_PASSWORD` in `.env` (never hardcoded)
- Admin sessions: itsdangerous signed cookies, configurable TTL
- Input sanitization: Pydantic v2 strict validation on all inputs
- Phone/email normalized server-side before persistence
- Hallucination prevention: grounded-only LLM prompts + hard KB gating
- No inventory availability claimed unless KB explicitly states it

See `docs/SECURITY.md` and `docs/RAG_GATING.md` for details.
