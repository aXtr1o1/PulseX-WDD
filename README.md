# PulseX-WDD: Luxury Real Estate Sales Concierge & Lead Intelligence

**Production-grade Web Concierge + Hybrid RAG Knowledge Engine + Lead Intelligence Admin Dashboard**
Built for **Wadi Degla Developments (WDD)**.

---

## System Overview

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

## Technical Architecture

| Component | Technology | Role |
|-----------|------------|------|
| **Backend** | FastAPI + Python 3.11 | High-performance async API with Pydantic v2 validation. |
| **Frontend** | Next.js 14 + Tailwind | Modern, responsive dashboard and embeddable chat widget. |
| **Hybrid RAG** | FAISS + RapidFuzz | Dual-index retrieval: Semantic (FAISS) + Keyword (RapidFuzz). |
| **Data Layer** | Portalocker-Safe CSV | Concurrency-safe, human-readable leads and audit logs. |

### The Hybrid RAG Engine
The core intelligence of PulseX-WDD relies on a sophisticated hybrid retrieval system to ensure high-accuracy property matching:

1.  **Semantic Retrieval (FAISS)**: Converts properties and user queries into high-dimensional vectors. This allows the system to understand intent (e.g., "quiet coastal retreat") even if specific keywords aren't used.
2.  **Keyword Matching (RapidFuzz)**: Uses fuzzy string matching to ensure specific project names (e.g., "ClubTown", "Edge") are prioritized even with typos or incomplete entries.
3.  **Hard Gating & Filtering**: 
    - **Sales Status Gating**: Automatically excludes projects marked as "not selling" in the KnowledgeBase.
    - **Entity Filtering**: Forces results to match extracted filters like `Region`, `Unit Type`, or `Project Type` (Residential/Commercial).
4.  **Zero-Latency Rebuilds**: Uses a SHA-256 file hashing mechanism (`kb_hash.txt`) to bypass index rebuilding on startup if the KnowledgeBase hasn't changed, saving OpenAI API cost and startup time.

---

### KnowledgeBase Governance & Schema
The system operates on a strictly governed CSV-based KnowledgeBase, ensuring that the AI only recommends verified WDD properties.

1.  **Canonical Identity**: Every project uses a `canon_project_slug` (ID) and `canon_project_name` for consistent cross-system referencing.
2.  **Pricing Intelligence**: Supports multi-state pricing:
    - **Official**: Displays precise `starting_price_value`.
    - **On Request**: Suppresses pricing and forces a lead capture intent.
3.  **Amenity Aggregation**: Automatically merges list-based amenities with high-level boolean flags (e.g., `golf_flag`, `beach_access_flag`) into a unified project profile.
4.  **Context Construction**: The `kb_service` dynamically builds "Project Cards"—normalized text summaries—used to generate FAISS embeddings for semantic search.

---

## Execution & Deployment

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

## Data Features & Intelligence

### Lead Lifecycle & De-duplication
PulseX implements a sophisticated lead management system optimized for the WDD sales pipeline:

- **Session-Matched Upserts**: The system uses `session_id` to detect repeat interactions. If a user provides more info (e.g., updates their budget), the existing record is updated in-place instead of creating a duplicate entry.
- **Audit Trails**: Every user query and AI response is logged in `audit.csv` with intent classification and similarity scores for quality monitoring.
- **Budget Tiering**: Automatically classifies leads into segmentations (**ULTRA** >20M, **HIGH** 10-20M, **MID** 5-10M, **LOW** <5M) to help sales prioritize high-value prospect follow-ups.
- **Fault-Tolerant Parsing**: The Admin dashboard utilizes robust numeric parsing and "on bad lines skip" logic to handle manual CSV edits or dirty data without impacting system uptime.

---

## Developer Workflow

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

## Security & Performance
- **Zero Hallucination**: Strict RAG gating ensures the AI only speaks from WDD-approved data.
- **Concurrency**: `portalocker` prevents file corruption during simultaneous lead captures.
- **Resilience**: Frontend utilizes `Promise.allSettled` patterns to load dashboards even if partial API services are down.

---

**© 2026 Wadi Degla Developments. All Rights Reserved.**
