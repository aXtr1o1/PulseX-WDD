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

from ..schemas.models import LeadRequest
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

def save_lead(lead: LeadRequest, leads_path: Path) -> str:
    """
    Persist a validated lead to leads.csv.
    Returns the lead reference ID.
    """
    lead_id = generate_lead_id()
    ts = now_iso()
    consent_ts = ts if (lead.consent_callback or lead.consent_marketing) else None

    phone_norm = normalise_phone(lead.phone)
    budget_band = compute_budget_band(lead.budget_min, lead.budget_max)

    row: Dict[str, Any] = {
        "timestamp": ts,
        "session_id": lead.session_id,
        "lang": lead.lang,
        "name": lead.name or "",
        "phone": phone_norm or "",
        "email": lead.email or "",
        "interest_projects": json_dumps(lead.interest_projects),
        "preferred_region": lead.preferred_region or "",
        "unit_type": lead.unit_type or "",
        "budget_min": lead.budget_min if lead.budget_min is not None else "",
        "budget_max": lead.budget_max if lead.budget_max is not None else "",
        "budget_band": budget_band,
        "purpose": lead.purpose or "",
        "timeline": lead.timeline or "",
        "tags": json_dumps(lead.tags),
        "consent_callback": lead.consent_callback,
        "consent_marketing": lead.consent_marketing,
        "consent_timestamp": consent_ts or "",
        "source_url": lead.source_url or "",
        "page_title": lead.page_title or "",
        "summary": lead.summary or "",
        "raw_json": json_dumps(lead.model_dump()),
    }

    append_csv_row(leads_path, row, LEADS_HEADERS)
    logger.info("Lead saved: %s (session=%s)", lead_id, lead.session_id)
    return lead_id


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
