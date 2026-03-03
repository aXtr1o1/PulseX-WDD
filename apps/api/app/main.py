"""
PulseX-WDD – FastAPI App Factory
Initialises all services on startup.
"""
from __future__ import annotations

import logging
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .config import get_settings
from .routers import admin, chat, lead
from .services.retrieval import HybridRetriever
from .utils.csv_io import ensure_csv, LEADS_HEADERS, AUDIT_HEADERS, SESSIONS_HEADERS
from .utils.kb_loader import kb_file_hash, load_kb

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)


async def _init_openai_client(settings):
    """Return async OpenAI client depending on provider config."""
    from openai import AsyncAzureOpenAI, AsyncOpenAI

    if settings.azure_openai_api_key and settings.azure_openai_endpoint:
        logger.info("Using Azure OpenAI endpoint: %s", settings.azure_openai_endpoint)
        return AsyncAzureOpenAI(
            api_key=settings.azure_openai_api_key,
            azure_endpoint=settings.azure_openai_endpoint,
            api_version=settings.azure_openai_api_version,
        )
    elif settings.openai_api_key:
        logger.info("Using OpenAI API")
        kwargs = {"api_key": settings.openai_api_key}
        if settings.openai_base_url:
            kwargs["base_url"] = settings.openai_base_url
        return AsyncOpenAI(**kwargs)
    else:
        logger.warning("No LLM API key configured — LLM calls will fail gracefully.")
        return None


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    settings = get_settings()

    # Ensure runtime dirs + CSVs exist
    settings.leads_csv_path.parent.mkdir(parents=True, exist_ok=True)
    settings.audit_csv_path.parent.mkdir(parents=True, exist_ok=True)
    settings.keyword_index_path.parent.mkdir(parents=True, exist_ok=True)

    ensure_csv(settings.leads_csv_path, LEADS_HEADERS)
    ensure_csv(settings.audit_csv_path, AUDIT_HEADERS)
    ensure_csv(settings.sessions_csv_path, SESSIONS_HEADERS)

    # Load KB
    kb_entities = load_kb(settings.kb_csv_path)
    app.state.kb_entities = kb_entities
    app.state.kb_version_hash = (
        kb_file_hash(settings.kb_csv_path) if settings.kb_csv_path.exists() else "unknown"
    )

    # Build index if requested or missing
    if (
        settings.index_rebuild_on_start
        or not settings.keyword_index_path.exists()
        or not settings.vector_index_path.exists()
    ):
        logger.info("Building retrieval indices...")
        try:
            from scripts.build_index import build_all  # type: ignore
            build_all()
        except Exception as e:
            logger.warning("Auto-index build failed: %s (run `make build-index` manually)", e)

    # Init retriever
    app.state.retriever = HybridRetriever(
        kb_entities=kb_entities,
        db_path=settings.keyword_index_path,
        index_path=settings.vector_index_path,
        meta_path=settings.vector_meta_path,
        keyword_weight=settings.keyword_weight,
        vector_weight=settings.vector_weight,
        top_k=settings.kb_top_k,
    )

    # Init LLM client
    app.state.llm_client = await _init_openai_client(settings)

    logger.info(
        "PulseX-WDD API ready | KB: %d entities | Indices: keyword=%s vector=%s",
        len(kb_entities),
        settings.keyword_index_path.exists(),
        settings.vector_index_path.exists(),
    )

    yield

    # Cleanup (none needed currently)
    logger.info("PulseX-WDD API shutting down.")


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="PulseX-WDD Concierge API",
        description="Hybrid RAG-powered property concierge for Wadi Degla Developments.",
        version="1.0.0",
        lifespan=lifespan,
        docs_url="/api/docs" if settings.app_env == "dev" else None,
        redoc_url="/api/redoc" if settings.app_env == "dev" else None,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(chat.router)
    app.include_router(lead.router)
    app.include_router(admin.router)

    @app.get("/api/health")
    async def health():
        return {
            "status": "ok",
            "index_ready": getattr(app.state, "retriever", None) is not None and get_settings().keyword_index_path.exists(),
            "kb_entities": len(app.state.kb_entities) if hasattr(app.state, "kb_entities") else 0,
            "kb_hash": getattr(app.state, "kb_version_hash", ""),
        }

    return app


app = create_app()
