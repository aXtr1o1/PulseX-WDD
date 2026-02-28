#!/usr/bin/env python3
"""
PulseX-WDD – Build Retrieval Indices
Builds SQLite FTS5 keyword index + FAISS vector index from buyerKB.csv.

Usage:
    python scripts/build_index.py
    # or via Makefile: make build-index
"""
from __future__ import annotations

import json
import logging
import sqlite3
import sys
from pathlib import Path

# Adjust Python path so we can import app config from the repo root
REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "apps" / "api"))

from app.config import get_settings
from app.utils.kb_loader import load_kb

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────────────────────
# SQLite FTS5 keyword index
# ──────────────────────────────────────────────────────────────────────────────

def build_keyword_index(entities, db_path: Path) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.executescript("""
        DROP TABLE IF EXISTS kb_fts;
        CREATE VIRTUAL TABLE kb_fts USING fts5(
            entity_id UNINDEXED,
            name,
            aliases,
            region,
            city_area,
            location_text,
            unit_types,
            amenities,
            brand_family,
            project_type,
            zones,
            full_text,
            tokenize="porter ascii"
        );
    """)
    rows = []
    for e in entities:
        rows.append((
            e["entity_id"],
            e["display_name"],
            " ".join(e.get("zones", [])),        # zone names as aliases
            e.get("region") or "",
            e.get("city_area") or "",
            e.get("location_text") or "",
            " ".join(e.get("unit_types", [])),
            " ".join(e.get("amenities", [])[:15]),
            e.get("brand_family") or "",
            e.get("project_type") or "",
            " ".join(e.get("zones", [])),
            e.get("index_text") or "",
        ))
    conn.executemany("INSERT INTO kb_fts VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", rows)
    conn.commit()
    conn.close()
    logger.info("Keyword (FTS5) index written -> %s (%d entities)", db_path, len(rows))


# ──────────────────────────────────────────────────────────────────────────────
# FAISS vector index
# ──────────────────────────────────────────────────────────────────────────────

def build_vector_index(entities, index_path: Path, meta_path: Path, settings) -> None:
    try:
        import faiss  # type: ignore
        import numpy as np
        from openai import AzureOpenAI, OpenAI
    except ImportError as e:
        logger.error("Missing dependency for vector index: %s. Skipping vector build.", e)
        return

    # Create LLM client (sync for script use)
    if settings.azure_openai_api_key and settings.azure_openai_endpoint:
        client = AzureOpenAI(
            api_key=settings.azure_openai_api_key,
            azure_endpoint=settings.azure_openai_endpoint,
            api_version=settings.azure_openai_api_version,
        )
        embed_model = settings.azure_openai_embed_deployment
    elif settings.openai_api_key:
        client = OpenAI(api_key=settings.openai_api_key)
        embed_model = settings.openai_embedding_model
    else:
        logger.warning("No API key for embeddings. Skipping vector index build.")
        return

    logger.info("Embedding %d entities with model=%s ...", len(entities), embed_model)
    texts = [e["index_text"] for e in entities]
    metadata = []
    embeddings = []

    BATCH = 16
    for i in range(0, len(texts), BATCH):
        batch = texts[i:i + BATCH]
        try:
            resp = client.embeddings.create(input=batch, model=embed_model)
            for j, item in enumerate(resp.data):
                embeddings.append(item.embedding)
                entity = entities[i + j]
                metadata.append({
                    "entity_id": entity["entity_id"],
                    "display_name": entity["display_name"],
                    "region": entity.get("region"),
                    "unit_types": entity.get("unit_types", []),
                })
            logger.info("  Embedded %d/%d", min(i + BATCH, len(texts)), len(texts))
        except Exception as e:
            logger.error("Embedding batch %d failed: %s", i // BATCH, e)

    if not embeddings:
        logger.warning("No embeddings generated; vector index not created.")
        return

    vecs = np.array(embeddings, dtype="float32")
    dim = vecs.shape[1]
    index = faiss.IndexFlatL2(dim)
    index.add(vecs)

    index_path.parent.mkdir(parents=True, exist_ok=True)
    faiss.write_index(index, str(index_path))
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)

    logger.info(
        "Vector index written -> %s (%d vectors, dim=%d)",
        index_path, index.ntotal, dim,
    )


# ──────────────────────────────────────────────────────────────────────────────
# Entry point
# ──────────────────────────────────────────────────────────────────────────────

def build_all() -> None:
    settings = get_settings()
    logger.info("Loading KB from %s", settings.kb_csv_path)
    entities = load_kb(settings.kb_csv_path)
    if not entities:
        logger.error("No entities loaded from KB. Aborting index build.")
        return

    build_keyword_index(entities, settings.keyword_index_path)
    build_vector_index(
        entities,
        settings.vector_index_path,
        settings.vector_meta_path,
        settings,
    )
    logger.info("All indices built successfully.")


if __name__ == "__main__":
    build_all()
