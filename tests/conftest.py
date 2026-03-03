"""
PulseX-WDD – Pytest Configuration
"""
import os
import pytest
from fastapi.testclient import TestClient

os.environ["APP_ENV"] = "test"
os.environ["ADMIN_AUTH_MODE"] = "cookie"

from apps.api.app.main import app
from apps.api.app.config import get_settings

@pytest.fixture(autouse=True)
def clear_settings_cache():
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()

@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client

@pytest.fixture
def set_admin_bypass():
    def _set(mode: str):
        os.environ["ADMIN_AUTH_MODE"] = mode
        get_settings.cache_clear()
    return _set

@pytest.fixture(autouse=True)
def mock_openai(monkeypatch):
    """Mock LLM calls to make tests fast, deterministic and offline-capable without 404s."""
    
    async def mock_generate_answer(client, model, query, entities, lang="en", session_history=None, intent="info_query"):
        ans = "I'd be happy to help. What specific region are you looking for?"
        intent_lane = "unknown"
        
        # Determine strict fallback responses
        q = query.lower()
        if "murano" in q and "club town" in q:
            ans = "I do not have cross-project information or Club Town details available."
        elif "club town" in q and not entities: # gated away
            ans = "I don't have information about Club Town matching your context."
        elif "hi" in q:
            ans = "Hello! Which project or region are you interested in?"
        elif "payment plan" in q:
            ans = "Our payment plans are flexible. Shall I have a sales representative call you?"
            
        return {
            "answer": ans,
            "model": model,
            "tokens_in": 10,
            "tokens_out": 20,
            "payload": {}
        }
        
    def mock_embed_query(*args, **kwargs):
        import numpy as np
        return np.zeros(1536, dtype="float32")
        
    monkeypatch.setattr("apps.api.app.routers.chat.generate_answer", mock_generate_answer)
    monkeypatch.setattr("apps.api.app.services.retrieval.HybridRetriever._embed_query", mock_embed_query)
