"""
PulseX-WDD – Audit Logging Service
Writes structured audit rows to audit.csv.
"""
from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..utils.csv_io import append_csv_row, now_iso, json_dumps, AUDIT_HEADERS

# GPT-4o approximate cost (USD per 1k tokens)
COST_PER_1K_IN  = 0.005
COST_PER_1K_OUT = 0.015


def new_request_id() -> str:
    return str(uuid.uuid4())[:8]


def write_audit(
    audit_path: Path,
    request_id: str,
    session_id: str,
    endpoint: str,
    intent: str,
    kb_version_hash: str,
    retrieval_stats: Dict[str, int],
    top_entities: List[str],
    model: str,
    tokens_in: int,
    tokens_out: int,
    latency_ms: int,
    status: str = "ok",
    error_reason: Optional[str] = None,
    message_hash: str = "",
) -> None:
    cost = ((tokens_in / 1000) * COST_PER_1K_IN) + ((tokens_out / 1000) * COST_PER_1K_OUT)

    row: Dict[str, Any] = {
        "timestamp":        now_iso(),
        "request_id":       request_id,
        "session_id":       session_id,
        "endpoint":         endpoint,
        "intent":           intent,
        "kb_version_hash":  kb_version_hash,
        "keyword_hits":     retrieval_stats.get("keyword_hits", 0),
        "vector_hits":      retrieval_stats.get("vector_hits", 0),
        "blended_hits":     retrieval_stats.get("blended_hits", 0),
        "top_entities_json": json_dumps(top_entities),
        "model":            model,
        "tokens_in":        tokens_in,
        "tokens_out":       tokens_out,
        "latency_ms":       latency_ms,
        "status":           status,
        "error_reason":     error_reason or "",
        "cost_estimate_usd": round(cost, 6),
        "message_hash":     message_hash,
    }
    append_csv_row(audit_path, row, AUDIT_HEADERS)
