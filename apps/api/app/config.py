"""
PulseX-WDD – Configuration
Reads all settings from environment / .env file.
"""
from __future__ import annotations

import os
from pathlib import Path
from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

# Repo root is always two levels up from apps/api
REPO_ROOT = Path(__file__).parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(REPO_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ── LLM ────────────────────────────────────────────────────────────────
    llm_provider: str = Field("azure_openai", alias="LLM_PROVIDER")

    # Azure OpenAI
    azure_openai_endpoint: str = Field("", alias="AZURE_OPENAI_ENDPOINT")
    azure_openai_api_key: str = Field("", alias="AZURE_OPENAI_API_KEY")
    azure_openai_api_version: str = Field(
        "2025-01-01-preview", alias="AZURE_OPENAI_API_VERSION"
    )
    azure_openai_chat_deployment: str = Field("gpt-4o", alias="AZURE_OPENAI_CHAT_DEPLOYMENT")
    azure_openai_embed_deployment: str = Field(
        "text-embedding-ada-002", alias="AZURE_OPENAI_EMBED_DEPLOYMENT"
    )

    # Standard OpenAI (fallback)
    openai_api_key: str = Field("", alias="OPENAI_API_KEY")
    openai_base_url: str = Field("", alias="OPENAI_BASE_URL")
    openai_chat_model: str = Field("gpt-4o", alias="OPENAI_CHAT_MODEL")
    openai_embedding_model: str = Field(
        "text-embedding-ada-002", alias="OPENAI_EMBEDDING_MODEL"
    )

    # ── KB / RAG ────────────────────────────────────────────────────────────
    kb_base_path: str = Field("engine-KB", alias="KB_BASE_PATH")
    kb_top_k: int = Field(5, alias="KB_TOP_K")
    kb_similarity_threshold: float = Field(0.72, alias="KB_SIMILARITY_THRESHOLD")
    keyword_weight: float = 0.55
    vector_weight: float = 0.45
    index_rebuild_on_start: bool = Field(False, alias="INDEX_REBUILD_ON_START")

    # ── Runtime data ────────────────────────────────────────────────────────
    runtime_dir: str = Field("runtime", alias="RUNTIME_DIR")

    # ── Admin ────────────────────────────────────────────────────────────────
    admin_password: str = Field("changeme", alias="ADMIN_PASSWORD")
    admin_auth_mode: str = Field("off", alias="ADMIN_AUTH_MODE")
    admin_session_ttl: int = 3600  # seconds

    # ── App ─────────────────────────────────────────────────────────────────
    app_env: str = Field("dev", alias="APP_ENV")
    log_level: str = Field("INFO", alias="LOG_LEVEL")
    cors_origins: str = Field("http://localhost:3000", alias="CORS_ORIGINS")

    # ── Brand ────────────────────────────────────────────────────────────────
    wdd_brand_primary: str = Field("#CB2030", alias="WDD_BRAND_PRIMARY")

    # ── Cost / guardrails ────────────────────────────────────────────────────
    token_budget_per_session: int = Field(8000, alias="TOKEN_BUDGET_PER_SESSION")
    enable_guardrails: bool = Field(True, alias="ENABLE_GUARDRAILS")

    # ── Derived paths (always relative to repo root) ─────────────────────────
    @property
    def kb_csv_path(self) -> Path:
        return REPO_ROOT / "engine-KB" / "PulseX-WDD_buyerKB.csv"

    @property
    def keyword_index_path(self) -> Path:
        return REPO_ROOT / "indices" / "keyword_index.db"

    @property
    def vector_index_path(self) -> Path:
        return REPO_ROOT / "indices" / "vector_index.faiss"

    @property
    def vector_meta_path(self) -> Path:
        return REPO_ROOT / "indices" / "vector_metadata.json"

    @property
    def leads_csv_path(self) -> Path:
        return REPO_ROOT / "runtime" / "leads.csv"

    @property
    def audit_csv_path(self) -> Path:
        return REPO_ROOT / "runtime" / "audit.csv"

    @property
    def sessions_csv_path(self) -> Path:
        return REPO_ROOT / "runtime" / "sessions.csv"

    @property
    def cors_origins_list(self) -> List[str]:
        return [o.strip() for o in self.cors_origins.split(",")]


@lru_cache
def get_settings() -> Settings:
    return Settings()
