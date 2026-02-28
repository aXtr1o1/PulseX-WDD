"""
PulseX-WDD – Concurrency-Safe CSV I/O Utilities
All CSV writes are protected by file-level locks via portalocker.
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import portalocker


# ──────────────────────────────────────────────────────────────────────────────
# Atomic / locked CSV append
# ──────────────────────────────────────────────────────────────────────────────

def ensure_csv(path: Path, headers: List[str]) -> None:
    """Create a CSV file with headers if it does not already exist."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists() or path.stat().st_size == 0:
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()


def append_csv_row(path: Path, row: Dict[str, Any], headers: List[str]) -> None:
    """Append a single row to a CSV file with exclusive file lock."""
    ensure_csv(path, headers)
    with portalocker.Lock(str(path) + ".lock", timeout=10):
        with open(path, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=headers, extrasaction="ignore")
            writer.writerow(row)


def read_csv_rows(path: Path) -> List[Dict[str, Any]]:
    """Read all rows from a CSV, returning list of dicts."""
    if not path.exists():
        return []
    with open(path, "r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return [dict(row) for row in reader]


def csv_to_xlsx_bytes(path: Path) -> bytes:
    """Convert a CSV to xlsx bytes using openpyxl (for download)."""
    import openpyxl

    wb = openpyxl.Workbook()
    ws = wb.active
    rows = read_csv_rows(path)
    if not rows:
        ws.append(["(empty)"])
    else:
        ws.append(list(rows[0].keys()))
        for row in rows:
            ws.append(list(row.values()))

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf.read()


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────

def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def hash_message(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()[:16]


def json_dumps(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, default=str)


# ──────────────────────────────────────────────────────────────────────────────
# Column headers (single source of truth)
# ──────────────────────────────────────────────────────────────────────────────

LEADS_HEADERS = [
    "timestamp", "session_id", "lang", "name", "phone", "email",
    "interest_projects", "preferred_region", "unit_type",
    "budget_min", "budget_max", "budget_band",
    "purpose", "timeline", "tags",
    "consent_callback", "consent_marketing", "consent_timestamp",
    "source_url", "page_title",
    "summary", "raw_json",
]

AUDIT_HEADERS = [
    "timestamp", "request_id", "session_id", "endpoint", "intent",
    "kb_version_hash", "keyword_hits", "vector_hits", "blended_hits",
    "top_entities_json", "model", "tokens_in", "tokens_out", "latency_ms",
    "status", "error_reason", "cost_estimate_usd", "message_hash",
]

SESSIONS_HEADERS = [
    "session_id", "created_at", "last_seen", "turn_count", "lang",
    "last_intent", "page_url", "ip_hash", "user_agent",
]
