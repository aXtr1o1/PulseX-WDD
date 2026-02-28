# PulseX-WDD Architecture

## System Overview

```
┌─────────────────────────────────────────────────────┐
│  Website visitor / WDD.com page                     │
│  <script src="/widget.js" data-project="murano">    │
└─────────────────────┬───────────────────────────────┘
                      │ iframe → /widget?project=murano
                      ▼
┌─────────────────────────────────────────────────────┐
│         apps/web  (Next.js 14 App Router)            │
│  /           Landing + floating ChatWidget          │
│  /widget     Embeddable full-page ChatWidget        │
│  /admin      Admin dashboard (auth-gated)           │
└──────────────────┬──────────────────────────────────┘
                   │ fetch /api/* (proxied via Next.js rewrites)
                   ▼
┌─────────────────────────────────────────────────────┐
│          apps/api  (FastAPI + Uvicorn)               │
│                                                     │
│  POST /api/chat         → Chat orchestration        │
│  POST /api/chat/stream  → SSE streaming             │
│  POST /api/lead         → Lead submission           │
│  POST /api/admin/login  → Cookie auth               │
│  GET  /api/admin/dashboard → KPIs + trends         │
│  GET  /api/admin/leads  → Filtered lead list       │
│  GET  /api/admin/sheets/{name}/rows                │
│  GET  /api/admin/sheets/{name}/download/{csv/xlsx} │
│  GET  /api/health       → Health check             │
└──────────────┬──────────────────────────────────────┘
               │
    ┌──────────┴──────────────────────┐
    │                                 │
    ▼                                 ▼
┌──────────────┐              ┌───────────────────┐
│  Retrieval   │              │  OpenAI / Azure   │
│  (Hybrid)    │              │  Embeddings + Chat│
│              │              └───────────────────┘
│ ┌──────────┐ │
│ │SQLite FTS│ │       ┌──────────────────────────┐
│ │keyword   │ │       │  engine-KB/              │
│ └──────────┘ │       │  PulseX-WDD_buyerKB.csv  │
│ ┌──────────┐ │       └──────────────────────────┘
│ │FAISS vec │ │
│ │index     │ │       ┌──────────────────────────┐
│ └──────────┘ │       │  runtime/                │
│              │       │  leads.csv (append-only) │
│  Hard Gating │       │  audit.csv               │
│  project/    │       │  sessions.csv            │
│  region/     │       └──────────────────────────┘
│  unit_type   │
└──────────────┘
```

## Data Flow: Chat Request

1. **User sends message** via widget (EN or AR)
2. `ChatWidget.tsx` POSTs to `POST /api/chat` (or `/api/chat/stream`)
3. FastAPI router:
   - `detect_intent()` → classify into WDD intent lane
   - If non-RAG intent → `get_handoff_message()` → respond immediately
   - If RAG intent → extract project/region/unit_type hints
4. **Hybrid retrieval** (`HybridRetriever.retrieve()`):
   - BM25-style FTS5 keyword search → top-N candidates with scores
   - FAISS vector search with query embedding → top-N candidates
   - Blend scores: `0.55 × keyword + 0.45 × vector`
   - Apply hard metadata gating (project → region → unit_type)
   - Return deduplicated top-K entities with `blended_score`
5. **Answer generation** (`generate_answer()`):
   - Constrained system prompt: cite entities, no invented prices, offer callback
   - LLM generates grounded answer
6. **Response** includes: `answer`, `evidence[]`, `lead_trigger`, `intent`
7. **Audit row** appended to `runtime/audit.csv`

## Data Flow: Lead Capture

1. Widget triggers lead form when `lead_trigger=true` or user requests callback
2. Progressive profiling: ask phone → name → project → unit_type → budget → consent
3. On submit: `POST /api/lead` with full payload
4. Backend validates (phone/email format, consent required), normalises phone to E.164
5. Computes `budget_band` (low/mid/high/ultra_high)
6. Appends row to `runtime/leads.csv` (portalocker file lock)
7. Returns `lead_id` reference (e.g. `LID-A3F8B2C1`)

## Components

| Component | Tech | Purpose |
|---|---|---|
| `apps/api` | FastAPI + Pydantic v2 | Orchestration, RAG, lead capture |
| `apps/web` | Next.js 14 App Router | Widget UI + Admin dashboard |
| `scripts/build_index.py` | SQLite FTS5 + FAISS | Offline index building |
| `engine-KB/` | CSV | Canonical knowledge base |
| `runtime/` | CSV | Live leads, audit, sessions |
| `indices/` | SQLite + FAISS | Search indices (generated) |
