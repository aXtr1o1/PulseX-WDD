"""
PulseX-WDD Scoring Service — Deterministic lead scoring (Hot/Warm/Cold).
Zero LLM involvement. Pure rule-based.
"""

import logging
from typing import Tuple, List
from app.backend.models import Slots

logger = logging.getLogger("PulseX-WDD-Scoring")


def score_lead(slots: Slots) -> Tuple[str, List[str]]:
    """
    Score a lead based on captured slots.
    Returns (temperature, reason_codes[]).
    
    Hot:  purpose + timeline∈{Immediate,0-3} + budget + project + confirmed + consent
    Warm: purpose present but missing 1-2 qualifiers
    Cold: browsing_only / low_signal / consent_declined
    """
    reasons = []
    score = 0

    # Purpose present
    if slots.purpose:
        score += 1
        reasons.append("purpose_present")
    else:
        reasons.append("purpose_missing")

    # Short timeline
    if slots.timeline and slots.timeline.lower() in ("immediate", "0-3 months"):
        score += 1
        reasons.append("short_timeline")
    elif slots.timeline:
        reasons.append("timeline_long")
    else:
        reasons.append("timeline_missing")

    # Budget present
    if slots.budget_min or slots.budget_max:
        score += 1
        reasons.append("budget_present")
    else:
        reasons.append("budget_missing")

    # Project selected
    if slots.interest_projects and len(slots.interest_projects) > 0:
        score += 1
        reasons.append("project_selected")
    else:
        reasons.append("project_missing")

    # Confirmed
    if slots.confirmed_by_user:
        score += 1
        reasons.append("confirmed")
    else:
        reasons.append("not_confirmed")

    # Consent
    if slots.consent_contact:
        score += 1
        reasons.append("consented")
    else:
        reasons.append("consent_pending")

    # Scoring rules
    if slots.consent_contact is False and slots.confirmed_by_user:
        # Explicit consent decline
        return "Cold", ["consent_declined"]

    if score >= 5:
        return "Hot", [r for r in reasons if not r.endswith("_missing") and r != "consent_pending" and r != "not_confirmed"]
    elif score >= 3:
        return "Warm", reasons
    else:
        return "Cold", ["browsing_only", "low_signal"] + [r for r in reasons if r.endswith("_missing")]


def compute_budget_band(budget_min: str = None, budget_max: str = None) -> str:
    """Compute budget band from min/max EGP values."""
    try:
        vals = []
        if budget_min:
            vals.append(float(str(budget_min).replace(",", "")))
        if budget_max:
            vals.append(float(str(budget_max).replace(",", "")))
        if not vals:
            return ""
        avg = sum(vals) / len(vals)
        if avg < 3_000_000:
            return "LOW"
        elif avg < 6_000_000:
            return "MID"
        elif avg < 10_000_000:
            return "HIGH"
        else:
            return "ULTRA"
    except (ValueError, TypeError):
        return ""
