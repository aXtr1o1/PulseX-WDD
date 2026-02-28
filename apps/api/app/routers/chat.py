"""
PulseX-WDD – Chat Router
Main /api/chat endpoint with streaming SSE support.
"""
from __future__ import annotations

import logging
import time
from typing import AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse

from ..config import get_settings
from ..schemas.models import ChatRequest, ChatResponse, EvidenceSnippet
from ..services.answer import generate_answer, stream_answer, get_handoff_message
from ..services.audit import write_audit, new_request_id
from ..services.lead import get_next_lead_prompt
from ..services.router import (
    detect_intent,
    extract_project_hint,
    extract_region_hint,
    extract_unit_type_hint,
    PROPERTY_QUESTION,
    SALES_INTENT,
)
from ..utils.csv_io import hash_message

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["chat"])

# Intents that require full RAG
RAG_INTENTS = {PROPERTY_QUESTION, SALES_INTENT}
# Intents that route to handoff
HANDOFF_INTENTS = {
    "complaint", "payment_services", "gate_access", "hotels",
    "rentals_ever_stay", "referral_grow_the_family",
    "private_services_reservation", "directory", "unknown",
}


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest, req: Request) -> ChatResponse:
    """Non-streaming chat endpoint."""
    settings = get_settings()
    t0 = time.monotonic()
    request_id = new_request_id()
    state = req.app.state

    intent = detect_intent(request.message, request.lang)

    # Handoff for non-RAG intents
    if intent in HANDOFF_INTENTS:
        answer = get_handoff_message(intent, request.lang)
        _write_audit_safe(
            state, request_id, request.session_id, "/api/chat",
            intent, {}, [], settings.azure_openai_chat_deployment,
            0, 0, int((time.monotonic() - t0)*1000), request.message,
        )
        return ChatResponse(
            session_id=request.session_id,
            request_id=request_id,
            intent=intent,
            answer=answer,
            handoff_cta=True,
            lang=request.lang,
        )

    # Extract filters
    entity_names = [e["display_name"] for e in state.kb_entities]
    project_filter = (
        request.page_context.project_slug if request.page_context and request.page_context.project_slug
        else extract_project_hint(request.message, entity_names)
    )
    region_filter   = extract_region_hint(request.message)
    unit_type_filter = extract_unit_type_hint(request.message)

    # Hybrid retrieval
    top_entities, stats = state.retriever.retrieve(
        query=request.message,
        client=state.llm_client,
        embed_model=settings.azure_openai_embed_deployment,
        project_filter=project_filter,
        region_filter=region_filter,
        unit_type_filter=unit_type_filter,
    )

    # Answer generation
    result = await generate_answer(
        client=state.llm_client,
        model=settings.azure_openai_chat_deployment,
        query=request.message,
        entities=top_entities,
        lang=request.lang,
    )

    latency_ms = int((time.monotonic() - t0) * 1000)

    _write_audit_safe(
        state, request_id, request.session_id, "/api/chat",
        intent, stats,
        [e["entity_id"] for e in top_entities],
        result.get("model", settings.azure_openai_chat_deployment),
        result.get("tokens_in", 0), result.get("tokens_out", 0),
        latency_ms, request.message,
    )

    evidence = [
        EvidenceSnippet(
            entity_id=e["entity_id"],
            display_name=e["display_name"],
            source_url=e.get("verified_url") or (e.get("sources") or [None])[0],
            snippet=e.get("index_text", "")[:200],
            confidence=e.get("confidence", 0.7),
        )
        for e in top_entities[:4]
    ]

    return ChatResponse(
        session_id=request.session_id,
        request_id=request_id,
        intent=intent,
        answer=result["answer"],
        evidence=evidence,
        lead_trigger=(intent == SALES_INTENT),
        lang=request.lang,
        latency_ms=latency_ms,
    )


@router.post("/chat/stream")
async def chat_stream(request: ChatRequest, req: Request) -> StreamingResponse:
    """Streaming SSE chat endpoint."""
    settings = get_settings()
    state = req.app.state
    intent = detect_intent(request.message, request.lang)

    if intent in HANDOFF_INTENTS:
        msg = get_handoff_message(intent, request.lang)
        async def _simple():
            yield f"data: {msg}\n\n"
            yield "data: [DONE]\n\n"
        return StreamingResponse(_simple(), media_type="text/event-stream")

    entity_names = [e["display_name"] for e in state.kb_entities]
    project_filter = (
        request.page_context.project_slug if request.page_context and request.page_context.project_slug
        else extract_project_hint(request.message, entity_names)
    )
    region_filter    = extract_region_hint(request.message)
    unit_type_filter = extract_unit_type_hint(request.message)

    top_entities, _ = state.retriever.retrieve(
        query=request.message,
        client=state.llm_client,
        embed_model=settings.azure_openai_embed_deployment,
        project_filter=project_filter,
        region_filter=region_filter,
        unit_type_filter=unit_type_filter,
    )

    async def gen() -> AsyncGenerator[str, None]:
        async for token in stream_answer(
            client=state.llm_client,
            model=settings.azure_openai_chat_deployment,
            query=request.message,
            entities=top_entities,
            lang=request.lang,
        ):
            yield f"data: {token}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(gen(), media_type="text/event-stream")


def _write_audit_safe(
    state, request_id, session_id, endpoint, intent,
    stats, entities, model, tok_in, tok_out, latency, msg,
) -> None:
    try:
        settings = get_settings()
        write_audit(
            audit_path=settings.audit_csv_path,
            request_id=request_id,
            session_id=session_id,
            endpoint=endpoint,
            intent=intent,
            kb_version_hash=getattr(state, "kb_version_hash", ""),
            retrieval_stats=stats,
            top_entities=entities,
            model=model,
            tokens_in=tok_in,
            tokens_out=tok_out,
            latency_ms=latency,
            message_hash=hash_message(msg),
        )
    except Exception as e:
        logger.warning("Audit write failed: %s", e)
