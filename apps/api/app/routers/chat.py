"""
PulseX-WDD – Chat Router
Main /api/chat endpoint with streaming SSE support.
"""
from __future__ import annotations

import logging
import time
from typing import AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException, Request, BackgroundTasks
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
    extract_budget_hint,
    extract_timeline_hint,
    extract_purpose_hint,
    INFO_QUERY,
    SHORTLIST,
    PRICING,
    HANDOFF,
    LEAD_CAPTURE,
    GREETING,
)
from ..utils.csv_io import hash_message

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["chat"])

# Intents that require full RAG via the Concierge Brain
RAG_INTENTS = {INFO_QUERY, SHORTLIST, PRICING, LEAD_CAPTURE, GREETING}
HANDOFF_INTENTS = {HANDOFF}


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

    # Extract dynamic constraint filters
    entity_names = [e["display_name"] for e in state.kb_entities]
    project_filter = (
        request.page_context.project_slug if request.page_context and request.page_context.project_slug
        else extract_project_hint(request.message, entity_names)
    )
    region_filter    = extract_region_hint(request.message)
    unit_type_filter = extract_unit_type_hint(request.message)
    budget_filter    = extract_budget_hint(request.message)
    timeline_filter  = extract_timeline_hint(request.message)
    purpose_filter   = extract_purpose_hint(request.message)

    # Determine dynamic Top-K based on constraint exactness
    is_vague = not any([project_filter, region_filter, unit_type_filter, budget_filter])
    top_k = 16 if is_vague else 6

    # Hybrid retrieval with metadata reranking parameters
    top_entities, stats = await state.retriever.retrieve(
        query=request.message,
        client=state.llm_client,
        embed_model=settings.azure_openai_embed_deployment,
        project_filter=project_filter,
        region_filter=region_filter,
        unit_type_filter=unit_type_filter,
        budget_filter=budget_filter,
        timeline_filter=timeline_filter,
        purpose_filter=purpose_filter,
        top_k=top_k,
    )

    # Output strictly Top-4 UI evidence cards based on Reranker
    evidence_entities = top_entities[:4]

    # Answer generation with 4-Thread Concierge Brain
    result = await generate_answer(
        client=state.llm_client,
        model=settings.azure_openai_chat_deployment,
        query=request.message,
        entities=evidence_entities,
        lang=request.lang,
        intent=intent,
    )

    latency_ms = int((time.monotonic() - t0) * 1000)

    _write_audit_safe(
        state, request_id, request.session_id, "/api/chat",
        intent, stats,
        [e["entity_id"] for e in evidence_entities],
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
        for e in evidence_entities
    ]

    payload = result.get("payload") or {}
    
    # Lead trigger check from dynamic payload
    is_trigger = (intent == LEAD_CAPTURE) or payload.get("ready_for_handoff", False)

    return ChatResponse(
        session_id=request.session_id,
        request_id=request_id,
        intent=intent,
        answer=result["answer"],
        evidence=evidence,
        shortlist=payload.get("project_interest"),
        lead_suggestions=payload,
        focused_project=project_filter,
        intent_lane=intent,
        lead_trigger=is_trigger,
        lang=request.lang,
        latency_ms=latency_ms,
    )


@router.post("/chat/stream")
async def chat_stream(request: ChatRequest, req: Request) -> StreamingResponse:
    """Streaming SSE chat endpoint."""
    import json
    import time
    from ..services.pubsub import publish_to_redis, stream_redis_sse

    settings = get_settings()
    t0 = time.monotonic()
    request_id = new_request_id()
    state = req.app.state
    intent = detect_intent(request.message, request.lang)

    if intent in HANDOFF_INTENTS:
        msg = get_handoff_message(intent, request.lang)
        async def _simple():
            meta = {"intent": intent, "handoff_cta": True, "lead_trigger": False, "evidence": []}
            yield f"data: [METADATA] {json.dumps(meta)}\n\n"
            yield f"data: {json.dumps({'t': msg})}\n\n"
            yield "data: [DONE]\n\n"
        return StreamingResponse(_simple(), media_type="text/event-stream")

    entity_names = [e["display_name"] for e in state.kb_entities]
    project_filter = (
        request.page_context.project_slug if request.page_context and request.page_context.project_slug
        else extract_project_hint(request.message, entity_names)
    )
    region_filter    = extract_region_hint(request.message)
    unit_type_filter = extract_unit_type_hint(request.message)
    budget_filter    = extract_budget_hint(request.message)
    timeline_filter  = extract_timeline_hint(request.message)
    purpose_filter   = extract_purpose_hint(request.message)

    is_vague = not any([project_filter, region_filter, unit_type_filter, budget_filter])
    top_k = 16 if is_vague else 6

    top_entities, stats = await state.retriever.retrieve(
        query=request.message,
        client=state.llm_client,
        embed_model=settings.azure_openai_embed_deployment,
        project_filter=project_filter,
        region_filter=region_filter,
        unit_type_filter=unit_type_filter,
        budget_filter=budget_filter,
        timeline_filter=timeline_filter,
        purpose_filter=purpose_filter,
        top_k=top_k,
    )
    
    evidence_entities = top_entities[:4]

    evidence = [
        EvidenceSnippet(
            entity_id=e["entity_id"],
            display_name=e["display_name"],
            source_url=e.get("verified_url") or (e.get("sources") or [None])[0],
            snippet=e.get("index_text", "")[:200],
            confidence=e.get("confidence", 0.7),
        ).model_dump()
        for e in evidence_entities
    ]

    async def gen() -> AsyncGenerator[str, None]:
        meta = {
            "intent": intent,
            "handoff_cta": False,
            "lead_trigger": (intent == LEAD_CAPTURE),
            "evidence": evidence
        }
        yield f"data: [METADATA] {json.dumps(meta)}\n\n"
        
        full_text = ""
        async for token in stream_answer(
            client=state.llm_client,
            model=settings.azure_openai_chat_deployment,
            query=request.message,
            entities=evidence_entities,
            lang=request.lang,
            intent=intent,
        ):
            full_text += token
            # Stream as json object to safely handle newlines natively
            yield f"data: {json.dumps({'t': token})}\n\n"
            
        latency_ms = int((time.monotonic() - t0) * 1000)
        _write_audit_safe(
            state, request_id, request.session_id, "/api/chat/stream",
            intent, stats, [e["entity_id"] for e in evidence_entities],
            settings.azure_openai_chat_deployment,
            0, 0, latency_ms, request.message,
        )
        yield "data: [DONE]\n\n"

    # ──────────────────────────────────────────────────────────────────
    # [PHASE 13] - Serverless Redis Pub/Sub Streaming
    # ──────────────────────────────────────────────────────────────────
    
    # If Upstash is configured, offload the Heavy LLM generator to the background 
    # and return the fast Redis stream to the client. Otherwise fallback to local.
    channel_id = f"chat_sse_{request.session_id}_{request_id}"
    
    if settings.upstash_redis_rest_url:
        import asyncio
        asyncio.create_task(
            publish_to_redis(
                settings.upstash_redis_rest_url,
                settings.upstash_redis_rest_token,
                channel_id,
                gen()
            )
        )
        return StreamingResponse(
            stream_redis_sse(
                settings.upstash_redis_rest_url, 
                settings.upstash_redis_rest_token, 
                channel_id
            ), 
            media_type="text/event-stream"
        )
        
    # Local memory fallback (FastAPI standard)
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
