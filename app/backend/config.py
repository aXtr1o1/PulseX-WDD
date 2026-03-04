import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from repo root
load_dotenv()

# Import runtime resolver for robust path resolution
from app.backend.runtime_resolver import get_runtime_dir

class Config:
    # Azure OpenAI
    AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
    AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
    AZURE_OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview")
    AZURE_OPENAI_CHAT_DEPLOYMENT = os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT", "gpt-4")
    AZURE_OPENAI_EMBED_DEPLOYMENT = os.getenv("AZURE_OPENAI_EMBED_DEPLOYMENT", "text-embedding-ada-002")

    # OpenAI Fallback
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    OPENAI_EMBED_MODEL = os.getenv("OPENAI_EMBED_MODEL", "text-embedding-3-small")

    # Paths — use runtime_resolver for robust path resolution
    _runtime = get_runtime_dir()
    RUNTIME_DIR = str(_runtime)

    # KB path: resolve relative to repo root (parent of runtime/)
    _repo_root = _runtime.parent
    KB_CSV_PATH = str(_repo_root / os.getenv("KB_CSV_PATH", "engine-KB/PulseX-WDD_buyerKB.csv"))

    INDEX_PATH = str(_runtime / "index" / "faiss.index")
    META_PATH = str(_runtime / "index" / "meta.json")
    LEADS_PATH = str(_runtime / "leads" / "leads.csv")
    AUDIT_PATH = str(_runtime / "leads" / "audit.csv")

    # Admin
    ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin")

    # Ensure runtime dirs exist
    os.makedirs(os.path.dirname(INDEX_PATH), exist_ok=True)
    os.makedirs(os.path.dirname(LEADS_PATH), exist_ok=True)
    os.makedirs(str(_runtime / "exports"), exist_ok=True)

import logging as _logging
_cfg_logger = _logging.getLogger("PulseX-WDD-Config")
_cfg_logger.info(f"KB path resolved to: {Config.KB_CSV_PATH}")
