"""
PulseX-WDD – Lead Capture Service
Extraction, validation, budget banding, and CSV persistence.
"""
from __future__ import annotations

import json
import logging
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..schemas.models import SessionState
from ..utils.csv_io import append_csv_row, now_iso, json_dumps, LEADS_HEADERS

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────────────────────
# Budget banding
# ──────────────────────────────────────────────────────────────────────────────

def compute_budget_band(
    budget_min: Optional[float],
    budget_max: Optional[float],
) -> str:
    """
    Compute a budget band label.
    All EGP millions based on typical WDD price ranges.
    """
    mid: Optional[float] = None
    if budget_min is not None and budget_max is not None:
        mid = (budget_min + budget_max) / 2
    elif budget_min is not None:
        mid = budget_min
    elif budget_max is not None:
        mid = budget_max

    if mid is None:
        return "unknown"
    if mid < 3_000_000:
        return "low"
    if mid < 8_000_000:
        return "mid"
    if mid < 20_000_000:
        return "high"
    return "ultra_high"


# ──────────────────────────────────────────────────────────────────────────────
# Phone normalisation (best-effort E.164 for Egypt)
# ──────────────────────────────────────────────────────────────────────────────

def normalise_phone(phone: Optional[str]) -> Optional[str]:
    if not phone:
        return phone
    digits = re.sub(r"[^\d+]", "", phone)
    # Egyptian mobile: starts with 01 -> +2010...
    if digits.startswith("01") and len(digits) == 11:
        return "+2" + digits
    if digits.startswith("+"):
        return digits
    return phone  # leave as-is if uncertain


# ──────────────────────────────────────────────────────────────────────────────
# Lead ID
# ──────────────────────────────────────────────────────────────────────────────

def generate_lead_id() -> str:
    return "LID-" + str(uuid.uuid4())[:8].upper()


# ──────────────────────────────────────────────────────────────────────────────
# Save lead
# ──────────────────────────────────────────────────────────────────────────────

def save_lead_if_confirmed(state: SessionState, leads_path: Path) -> Optional[str]:
    """
    Persist a fully validated funnel session to leads.csv ONLY IF confirmed and consented.
    Returns the lead reference ID if saved.
    """
    fields = state.collected_fields
    
    if not fields.get("phone"):
        return None
    if not fields.get("confirmed_by_user"):
        return None
    if not fields.get("consent_contact"):
        return None

    lead_id = generate_lead_id()
    ts = now_iso()

    phone_norm = normalise_phone(fields.get("phone"))
    budget_min = fields.get("budget_min")
    budget_max = fields.get("budget_max")
    
    if isinstance(budget_min, str):
        try: budget_min = float(budget_min)
        except: budget_min = None
    if isinstance(budget_max, str):
        try: budget_max = float(budget_max)
        except: budget_max = None
        
    budget_band = compute_budget_band(budget_min, budget_max)

    row: Dict[str, Any] = {
        "timestamp": ts,
        "session_id": state.session_id,
        "lang": state.language,
        "name": fields.get("name") or "",
        "phone": phone_norm or "",
        "email": fields.get("email") or "",
        "interest_projects": json_dumps(fields.get("project_interest", [])),
        "preferred_region": fields.get("region") or "",
        "unit_type": fields.get("unit_type") or "",
        "budget_min": budget_min if budget_min is not None else "",
        "budget_max": budget_max if budget_max is not None else "",
        "budget_band": budget_band,
        "purpose": fields.get("purpose") or "",
        "timeline": fields.get("timeline") or "",
        "tags": json_dumps(fields.get("tags", [])),
        "consent_callback": True,
        "consent_marketing": True,
        "consent_timestamp": ts,
        "source_url": fields.get("source_url") or "",
        "page_title": fields.get("page_title") or "",
        "summary": fields.get("summary") or "",
        "raw_json": json_dumps(state.model_dump()),
    }

    append_csv_row(leads_path, row, LEADS_HEADERS)
    logger.info("Confirmed Lead saved: %s (session=%s)", lead_id, state.session_id)
    return lead_id

INTENT_HEADERS = [
    "timestamp", "session_id", "stage_reached", "language",
    "purpose", "unit_type", "region", "budget_band", "timeline"
]

def save_anonymous_intent(state: SessionState, intent_path: Path) -> None:
    """
    Log an unconverted session state to trace Funnel drop-offs.
    """
    fields = state.collected_fields
    
    budget_min = fields.get("budget_min")
    budget_max = fields.get("budget_max")
    if isinstance(budget_min, str):
        try: budget_min = float(budget_min)
        except: budget_min = None
    if isinstance(budget_max, str):
        try: budget_max = float(budget_max)
        except: budget_max = None
        
    budget_band = compute_budget_band(budget_min, budget_max)
    
    row: Dict[str, Any] = {
        "timestamp": now_iso(),
        "session_id": state.session_id,
        "stage_reached": state.stage,
        "language": state.language,
        "purpose": fields.get("purpose") or "",
        "unit_type": fields.get("unit_type") or "",
        "region": fields.get("region") or "",
        "budget_band": budget_band,
        "timeline": fields.get("timeline") or ""
    }
    
    append_csv_row(intent_path, row, INTENT_HEADERS)


# ──────────────────────────────────────────────────────────────────────────────
# Progressive profiling – next missing field
# ──────────────────────────────────────────────────────────────────────────────

LEAD_FIELD_ORDER = ["phone", "name", "interest_projects", "unit_type", "budget_min", "timeline", "consent_callback"]

LEAD_PROMPTS = {
    "phone": {
        "en": "Could you share your phone number so our team can reach you?",
        "ar": "هل يمكنك مشاركة رقم هاتفك حتى يتواصل معك فريقنا؟",
    },
    "name": {
        "en": "May I have your name?",
        "ar": "ما اسمك الكريم؟",
    },
    "interest_projects": {
        "en": "Which project(s) are you most interested in?",
        "ar": "ما المشاريع التي تهتم بها؟",
    },
    "unit_type": {
        "en": "What type of unit are you looking for? (apartment, villa, chalet, etc.)",
        "ar": "ما نوع الوحدة التي تبحث عنها؟ (شقة، فيلا، شاليه، إلخ)",
    },
    "budget_min": {
        "en": "Do you have a budget range in mind? (e.g. 5–10M EGP)",
        "ar": "هل لديك ميزانية تقريبية؟ (مثلاً 5–10 مليون جنيه)",
    },
    "timeline": {
        "en": "When are you looking to make a decision?",
        "ar": "متى تخطط لاتخاذ قرارك؟",
    },
    "consent_callback": {
        "en": "May I send you our latest project updates and have our team call you back? (yes/no)",
        "ar": "هل توافق على تلقي آخر تحديثات مشاريعنا والتواصل معك؟ (نعم/لا)",
    },
}


def get_next_lead_prompt(partial: Dict[str, Any], lang: str = "en") -> Optional[str]:
    """Return the next question to ask based on what's already collected."""
    for field in LEAD_FIELD_ORDER:
        val = partial.get(field)
        if val is None or val == "" or val == []:
            prompts = LEAD_PROMPTS.get(field, {})
            return prompts.get(lang, prompts.get("en"))
    return None  # All collected
