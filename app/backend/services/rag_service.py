import os
import json
import hashlib
import logging
import numpy as np
import faiss
from rapidfuzz import process, fuzz
from typing import List, Dict, Any
from app.backend.config import Config
from app.backend.services.llm_service import llm_service
from app.backend.services.kb_service import kb_service
from app.backend.models import Project

logger = logging.getLogger(__name__)

class RAGService:
    def __init__(self):
        self.index = None
        self.metadata = [] # List of dicts matching index order
        self.is_ready = False
        self._load_index()

    def _compute_kb_hash(self) -> str:
        """SHA-256 of the KB CSV file — if this changes, the index is stale."""
        h = hashlib.sha256()
        try:
            with open(Config.KB_CSV_PATH, 'rb') as f:
                for chunk in iter(lambda: f.read(8192), b''):
                    h.update(chunk)
        except FileNotFoundError:
            return "no_kb_file"
        return h.hexdigest()[:16]

    def build_index_if_needed(self):
        """Only build if index is missing OR KB data changed. Saves API calls."""
        hash_path = os.path.join(os.path.dirname(Config.INDEX_PATH), "kb_hash.txt")
        current_hash = self._compute_kb_hash()

        # Check existing index + hash
        if (os.path.exists(Config.INDEX_PATH) and 
            os.path.exists(Config.META_PATH) and
            os.path.exists(hash_path)):
            with open(hash_path, 'r') as f:
                stored_hash = f.read().strip()
            if stored_hash == current_hash:
                logger.info(f"✅ Index up-to-date (hash={current_hash}). Skipping rebuild — zero API calls.")
                if not self.is_ready:
                    self._load_index()
                return

        # KB changed or first time → rebuild
        logger.info(f"🔨 KB changed or first run (hash={current_hash}). Building index...")
        self.build_index()

        # Persist the hash
        with open(hash_path, 'w') as f:
            f.write(current_hash)
        logger.info(f"✅ Index hash saved. Future restarts will skip rebuild.")

    def _load_index(self):
        if os.path.exists(Config.INDEX_PATH) and os.path.exists(Config.META_PATH):
            try:
                self.index = faiss.read_index(Config.INDEX_PATH)
                with open(Config.META_PATH, 'r') as f:
                    self.metadata = json.load(f)
                self.is_ready = True
                logger.info("RAG Index loaded successfully.")
            except Exception as e:
                logger.error(f"Failed to load index: {e}")
        else:
            logger.warning("RAG Index not found. Run build_index.py first.")

    def search(self, query: str, k: int = 3, filters: Dict = None) -> List[Dict[str, Any]]:
        """
        Hybrid search: FAISS embedding + RapidFuzz re-ranking/matching
        """
        if not self.is_ready:
            # Fallback to pure rapidfuzz on loaded KB if index missing
            return self._fallback_search(query, k)

        # 1. Embedding Search
        q_emb = llm_service.get_embedding(query)
        if not q_emb or len(q_emb) == 0:
            return self._fallback_search(query, k)

        D, I = self.index.search(np.array([q_emb], dtype=np.float32), k * 2) # Get more for filtering
        
        candidates = []
        seen_ids = set()
        
        # Collect FAISS candidates
        for idx in I[0]:
            if idx < 0 or idx >= len(self.metadata): continue
            meta = self.metadata[idx]
            pid = meta['project_id']
            if pid not in seen_ids:
                proj = kb_service.get_project(pid)
                if proj:
                    candidates.append({"project": proj, "score": 0.0, "source": "faiss"})
                    seen_ids.add(pid)

        # 2. RapidFuzz Search (Entity Matching)
        all_ids = list(kb_service.projects.keys())
        fuzzy_matches = process.extract(
            query, 
            all_ids, 
            scorer=fuzz.WRatio, 
            limit=k, 
            score_cutoff=60
        )
        for match in fuzzy_matches:
            # match is (match_string, score, index)
            pid = match[0]
            if pid not in seen_ids:
                proj = kb_service.get_project(pid)
                if proj:
                    candidates.append({"project": proj, "score": match[1]/100.0, "source": "fuzzy"})
                    seen_ids.add(pid)

        # 3. Apply Filters
        filtered = []
        for c in candidates:
            p = c['project']
            if filters:
                # Region Filter (Check both region and city_area)
                if filters.get('region'):
                    region_val = (p.region or '').lower()
                    city_val = (p.city_area or '').lower()
                    target_region = filters['region'].lower()
                    if target_region not in region_val and target_region not in city_val and region_val not in target_region:
                        continue
                
                # Project Type Filter
                if filters.get('project_type'):
                    p_type = (p.project_type or '').lower()
                    target_type = filters['project_type'].lower()
                    if target_type == 'commercial' and p_type != 'commercial':
                        continue
                    if target_type == 'residential' and p_type != 'residential':
                        continue

                # Project Status Filter
                if filters.get('project_status'):
                    status_val = (p.project_status or '').lower()
                    target_status = filters['project_status'].lower()
                    if target_status not in status_val:
                        continue

            filtered.append(c)

        # Return top k
        return filtered[:k]

    def _fallback_search(self, query: str, k: int) -> List[Dict[str, Any]]:
        # Simple name text search using kb_service
        matches = kb_service.search_projects(query)
        return [{"project": p, "score": 1.0, "source": "basic"} for p in matches[:k]]

    def build_index(self):
        """
        Generates embeddings for all projects and saves to disk.
        """
        logger.info("Building Index...")
        projects = list(kb_service.projects.values())
        if not projects:
            logger.error("No projects to index.")
            return

        embeddings = []
        meta = []

        for p in projects:
            card_text = kb_service.build_project_card(p)
            emb = llm_service.get_embedding(card_text)
            embeddings.append(emb)
            meta.append({
                "project_id": p.project_id,
                "project_name": p.project_name
            })
            print(f"Indexed {p.project_name}")

        dim = len(embeddings[0])
        index = faiss.IndexFlatL2(dim)
        index.add(np.array(embeddings, dtype=np.float32))

        # Save
        faiss.write_index(index, Config.INDEX_PATH)
        with open(Config.META_PATH, 'w') as f:
            json.dump(meta, f)
        
        logger.info(f"Index built with {len(projects)} items.")
        self._load_index()

rag_service = RAGService()
