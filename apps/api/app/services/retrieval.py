"""
PulseX-WDD – Hybrid RAG Retrieval Service
Combines SQLite FTS5 keyword search + FAISS vector similarity.
Applies hard metadata gating to prevent wrong-project answers.
"""
from __future__ import annotations

import json
import logging
import math
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from rapidfuzz import process, fuzz

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────────────────────
# Gating guards
# ──────────────────────────────────────────────────────────────────────────────

def _region_matches(entity_region: Optional[str], user_region: Optional[str]) -> bool:
    if user_region is None or entity_region is None:
        return True  # no filter requested
    ur = str(user_region).lower()
    er = str(entity_region).lower()
    return ur in er or er in ur


def _unit_type_matches(entity_units: List[str], user_unit: Optional[str]) -> bool:
    if not user_unit:
        return True
    uu = user_unit.lower()
    return any(uu in u.lower() or u.lower() in uu for u in entity_units)


def _project_matches(entity: Dict[str, Any], project_query: Optional[str]) -> bool:
    """Hard-match: returns True if entity belongs to the queried project family."""
    if not project_query:
        return True
    pq = project_query.lower().strip()
    checks = [
        entity.get("entity_id", "").lower(),
        entity.get("display_name", "").lower(),
        entity.get("parent_project", "").lower() if entity.get("parent_project") else "",
        entity.get("is_alias_of", "").lower() if entity.get("is_alias_of") else "",
    ]
    return any(pq in c or c in pq for c in checks if c)


# ──────────────────────────────────────────────────────────────────────────────
# Keyword (SQLite FTS5)
# ──────────────────────────────────────────────────────────────────────────────

class KeywordIndex:
    def __init__(self, db_path: Path):
        self.db_path = db_path

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def search(self, query: str, top_k: int = 10) -> List[Tuple[str, float]]:
        """Returns list of (entity_id, normalized_bm25_score)."""
        if not self.db_path.exists():
            return []
            
        import re
        clean_query = re.sub(r'[^\w\s]', ' ', query).strip()
        if not clean_query:
            return []
            
        with self._conn() as conn:
            try:
                rows = conn.execute(
                    """
                    SELECT entity_id, bm25(kb_fts) AS score
                    FROM kb_fts
                    WHERE kb_fts MATCH ?
                    ORDER BY score
                    LIMIT ?
                    """,
                    (clean_query, top_k),
                ).fetchall()
                if not rows:
                    return []
                # BM25 scores from SQLite are negative; lower is better
                scores = [abs(r["score"]) for r in rows]
                max_s = max(scores) if scores else 1.0
                return [(rows[i]["entity_id"], scores[i] / max_s) for i in range(len(rows))]
            except Exception as e:
                logger.warning("FTS search error: %s", e)
                return []


# ──────────────────────────────────────────────────────────────────────────────
# Vector (FAISS)
# ──────────────────────────────────────────────────────────────────────────────

class VectorIndex:
    def __init__(self, index_path: Path, meta_path: Path):
        self.index_path = index_path
        self.meta_path = meta_path
        self._index = None
        self._meta: List[Dict[str, Any]] = []

    def load(self) -> bool:
        if not self.index_path.exists() or not self.meta_path.exists():
            return False
        try:
            import faiss  # type: ignore
            self._index = faiss.read_index(str(self.index_path))
            with open(self.meta_path, "r", encoding="utf-8") as f:
                self._meta = json.load(f)
            logger.info("FAISS index loaded: %d vectors", self._index.ntotal)
            return True
        except Exception as e:
            logger.error("Failed to load FAISS index: %s", e)
            return False

    def search(self, query_vec: np.ndarray, top_k: int = 10) -> List[Tuple[str, float]]:
        if self._index is None:
            return []
        q = query_vec.reshape(1, -1).astype("float32")
        distances, indices = self._index.search(q, top_k)
        results = []
        for dist, idx in zip(distances[0], indices[0]):
            if idx < 0 or idx >= len(self._meta):
                continue
            # L2 distance -> similarity score 0-1
            sim = float(1.0 / (1.0 + dist))
            results.append((self._meta[idx]["entity_id"], sim))
        # Normalize
        if results:
            max_s = max(s for _, s in results)
            results = [(eid, s / max_s) for eid, s in results]
        return results


# ──────────────────────────────────────────────────────────────────────────────
# Hybrid Retrieval Service
# ──────────────────────────────────────────────────────────────────────────────

class HybridRetriever:
    def __init__(
        self,
        kb_entities: List[Dict[str, Any]],
        db_path: Path,
        index_path: Path,
        meta_path: Path,
        keyword_weight: float = 0.55,
        vector_weight: float = 0.45,
        top_k: int = 5,
    ):
        self.entities: Dict[str, Dict[str, Any]] = {e["entity_id"]: e for e in kb_entities}
        self.keyword = KeywordIndex(db_path)
        self.vector = VectorIndex(index_path, meta_path)
        self.kw_weight = keyword_weight
        self.vec_weight = vector_weight
        self.top_k = top_k
        self._vector_ready = self.vector.load()

    async def _embed_query(self, query: str, client: Any, model: str) -> Optional[np.ndarray]:
        try:
            resp = await client.embeddings.create(input=[query], model=model)
            vec = np.array(resp.data[0].embedding, dtype="float32")
            return vec
        except Exception as e:
            logger.warning("Embedding failed: %s", e)
            return None

    async def retrieve(
        self,
        query: str,
        client: Any,
        embed_model: str,
        project_filter: Optional[str] = None,
        region_filter: Optional[str] = None,
        unit_type_filter: Optional[str] = None,
        budget_filter: Optional[str] = None,
        timeline_filter: Optional[str] = None,
        purpose_filter: Optional[str] = None,
        top_k: Optional[int] = None,
    ) -> Tuple[List[Dict[str, Any]], Dict[str, int]]:
        """
        Returns (ranked_entities, stats_dict).
        Applies hard gating: project_filter > region_filter.
        Applies soft constraints reranking: budget, timeline, unit_type, answerability.
        """
        k = top_k or self.top_k

        # ── Keyword retrieval
        kw_results = self.keyword.search(query, top_k=k * 3)
        kw_map: Dict[str, float] = dict(kw_results)

        # ── Vector retrieval
        vec_map: Dict[str, float] = {}
        if self._vector_ready:
            query_vec = await self._embed_query(query, client, embed_model)
            if query_vec is not None:
                vec_results = self.vector.search(query_vec, top_k=k * 3)
                vec_map = dict(vec_results)

        # ── Blend scores
        all_ids = set(kw_map) | set(vec_map)
        blended: Dict[str, float] = {}
        for eid in all_ids:
            ks = kw_map.get(eid, 0.0)
            vs = vec_map.get(eid, 0.0)
            blended[eid] = self.kw_weight * ks + self.vec_weight * vs

        # ── Apply hard gating
        gated: List[Tuple[str, float]] = []
        for eid, score in blended.items():
            entity = self.entities.get(eid)
            if not entity:
                continue
            # Project hard filter (strictest)
            if project_filter and not _project_matches(entity, project_filter):
                continue
            # Region filter
            if region_filter and not _region_matches(entity.get("region"), region_filter):
                continue
            # Unit type (softer, but applied if requested)
            if unit_type_filter and not _unit_type_matches(entity.get("unit_types", []), unit_type_filter):
                continue
            gated.append((eid, score))

        # If gating returned nothing under a strict filter, DO NOT fall back.
        if not gated and (project_filter or region_filter):
            logger.info("Gating returned 0; maintaining strict zero-results for query: %s", query)

        # ── RapidFuzz Entity Matching on retrieved results ──
        # If user explicitly provided a project filter, promote those entities
        if project_filter:
            for i in range(len(gated)):
                eid, score = gated[i]
                entity = self.entities[eid]
                # Look at both entity ID and display name
                names_to_check = [entity.get("display_name", ""), entity.get("entity_id", ""), entity.get("parent_project", "")]
                names_to_check = [str(n) for n in names_to_check if n]
                
                # If rapidfuzz matches well, give it a massive promotion boost
                if names_to_check:
                    res = process.extractOne(project_filter, names_to_check, scorer=fuzz.partial_ratio)
                    if res and res[1] > 80:
                         gated[i] = (eid, score + 5.0)  # Pinned projects jump to the top

        # ── Metadata Constraint Reranking
        for i in range(len(gated)):
            eid, score = gated[i]
            entity = self.entities[eid]
            
            # Factual density base from ingestion
            ans = float(entity.get("answerability", 0.5))
            bonus = ans * 0.2  # Up to 20% bonus for highly answerable docs
            
            # Soft constraints correlation
            if budget_filter is not None:
                bf = str(budget_filter)
                if (bf in str(entity.get("downpayment_min", "")) or 
                    bf in str(entity.get("downpayment_max", "")) or
                    bf in str(entity.get("payment_plan", ""))):
                    bonus += 0.15
                
            if timeline_filter is not None:
                tf = str(timeline_filter)
                if (tf in str(entity.get("delivery_year_min", "")) or
                    tf in str(entity.get("delivery_year_max", "")) or
                    tf in str(entity.get("project_status", ""))):
                    bonus += 0.15
                
            gated[i] = (eid, score + bonus)

        # ── Sort + dedupe + pick top-k
        gated.sort(key=lambda x: x[1], reverse=True)
        seen: set = set()
        top: List[Dict[str, Any]] = []
        for eid, score in gated:
            if eid in seen:
                continue
            seen.add(eid)
            e = dict(self.entities[eid])
            e["blended_score"]  = round(score, 4)
            e["keyword_score"]  = round(kw_map.get(eid, 0.0), 4)
            e["vector_score"]   = round(vec_map.get(eid, 0.0), 4)
            top.append(e)
            if len(top) >= k:
                break

        stats = {
            "keyword_hits": len(kw_map),
            "vector_hits": len(vec_map),
            "blended_hits": len(blended),
            "gated_hits": len(top),
        }
        return top, stats
