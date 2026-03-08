# PulseX-WDD: Luxury Real Estate Sales Concierge & Lead Intelligence

**Production-grade Web Concierge + Hybrid RAG Knowledge Engine + Lead Intelligence Admin Dashboard**
Built for **Wadi Degla Developments (WDD)**.

---

## 🌟 System Overview

PulseX-WDD is a sophisticated "Sales Concierge" platform that transforms passive web traffic into high-intent leads. Unlike traditional chatbots, PulseX follows a strict 6-stage sales funnel grounded in the WDD KnowledgeBase, ensuring zero hallucinations and deterministic lead qualification.

### The Intelligence Layer (Sales Funnel)
The system uses a stateful conversation logic that guides users through:
1.  **Stage 1: Research & Discovery** — Answering property-specific queries (location, amenities, delivery).
2.  **Stage 2: Interest Mapping** — Identifying specific projects (e.g., Vyon, Neo, Murano).
3.  **Stage 3: Unit Selection** — Extracting preferred unit types (Villa, Apartment, Penthouse).
4.  **Stage 4: Budget & Timeline** — Extracting numeric budgets (EGP/USD) and purchase windows.
5.  **Stage 5: Recap & Verification** — Presenting a summary for user confirmation.
6.  **Stage 6: Consent-Gated Handoff** — Capturing verified WhatsApp/Phone with explicit callback consent.

---

## 🏗️ Technical Architecture

| Component | Technology | Role |
|-----------|------------|------|
| **Backend** | FastAPI + Python 3.11 | High-performance async API with Pydantic v2 validation. |
| **Frontend** | Next.js 14 + Tailwind | Modern, responsive dashboard and embeddable chat widget. |
| **Hybrid RAG** | SQLite FTS5 + FAISS | Dual-index retrieval: Keyword (FTS5) + Semantic (FAISS). |
| **Data Layer** | Portalocker-Safe CSV | Concurrency-safe, human-readable leads and audit logs. |

---

## ⚡ Execution & Deployment

### One-Shot Startup (Recommended)
The `start.sh` script automates the entire Docker-based lifecycle including thermal cleanup of stale networks and volume mounting for live development.

```bash
# 1. Clone and enter directory
cd PulseX-WDD

# 2. Run the one-shot starter
bash start.sh
```

### Manual Docker Control
```bash
docker compose -p pulsex_master up -d    # Start services
docker compose -p pulsex_master logs -f    # Tail logs
docker compose -p pulsex_master down       # Stop and cleanup
```

### Port Mappings
| Service | Internal | External | Description |
|---------|----------|----------|-------------|
| `pulsex_api` | 8000 | **8081** | Backend Service |
| `pulsex_web` | 3000 | **3001** | Dashboard & Widget |

---

## 📊 Data Features & Nuances

### Lead De-duplication (Upsert Logic)
The `LeadsService` implements a **session-based upsert mechanism**. If a lead with the same `session_id` already exists (e.g., user updates their preferences), the system updates the existing row instead of appending duplicates. This ensures the 29-column `leads.csv` remains clean and actionable.

### Intelligent Extraction
- **Budget Formatting**: Numeric values (e.g., "18,600,000 EGP") are automatically extracted and indexed for the dashboard KPIs.
- **Next Action Mapping**: Technical enums are converted to human-readable CTAs (e.g., "Send Project Brochures & Details").
- **Dashboard Resilience**: The admin loader skips malformed CSV lines (`on_bad_lines='skip'`) to ensure the dashboard never crashes on dirty data.

---

## 🔧 Developer Workflow

### Refreshing KnowledgeBase
If you update the `engine-KB/PulseX-WDD_buyerKB.csv`, run:
```bash
make kb-refresh   # Cleans and validates data rules
make index        # Rebuilds SQLite and FAISS indices
```

### Environment Configuration
Key variables in `.env`:
- `AZURE_OPENAI_API_KEY`: Required for LLM and Embeddings.
- `ADMIN_PASSWORD`: For dashboard access (`http://localhost:3001/admin`).
- `KB_VERSION_HASH`: Controlled versioning of the active KnowledgeBase.

---

## 🔒 Security & Performance
- **Zero Hallucination**: Strict RAG gating ensures the AI only speaks from WDD-approved data.
- **Concurrency**: `portalocker` prevents file corruption during simultaneous lead captures.
- **Resilience**: Frontend utilizes `Promise.allSettled` patterns to load dashboards even if partial API services are down.

---

**© 2026 Wadi Degla Developments. All Rights Reserved.**
