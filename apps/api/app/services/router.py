"""
PulseX-WDD – Intent Router & Constraint Extraction
Classifies user messages into precise Concierge Brain intents and extracts constraints.
"""
from __future__ import annotations

import re
from typing import Dict, List, Optional, Tuple

# Intent names mapped to Phase 12 Concierge Brain
INFO_QUERY    = "info_query"
SHORTLIST     = "shortlist"
PRICING       = "pricing"
HANDOFF       = "handoff"
LEAD_CAPTURE  = "lead_capture"
GREETING      = "greeting"
UNKNOWN       = "info_query"  # Vague queries fall back to info_query to allow RAG to attempt resolving

# ── Keyword patterns per intent (order matters – checked top-down) ──────────
PATTERNS: List[Tuple[str, List[str]]] = [
    (GREETING, [
        r"^\s*(hi|hello|hey|good morning|good afternoon|good evening|مرحبا|اهلا|صباح الخير|مساء الخير)\s*$",
    ]),
    (LEAD_CAPTURE, [
        r"\b(callback|call me|call back|contact sale|speak to|talk to sales|visit|schedule|arrange|set up.*(meeting|call|visit)|contact me|اتصل|أتصل)\b",
    ]),
    (HANDOFF, [
        r"\b(complain|problem|issue|broken|maintenance|repair|damage|شكوى|مشكلة|عطل|"
        r"pay|invoice|receipt|overdue|فاتورة|"
        r"gate|access|entry|visitor pass|id|identification|بوابة|دخول|"
        r"hotel|stay|night|accommodation|فندق|إقامة|"
        r"rent|rental|ever.?stay|للإيجار|إيجار|"
        r"refer|referral|grow the family|introduce|friend|family member|توصية|ترشيح|"
        r"reservation|book.*(facility|court|pool|club)|reserve a|حجز.*(ملعب|مسبح|نادي)|"
        r"directory|find|where is|phone number|email|address|location|دليل|مكان|عنوان)\b",
    ]),
    (PRICING, [
        r"\b(price|cost|how much|budget|downpayment|down payment|installments|سعر|تكلفة|بكم|مقدم|أقساط)\b",
    ]),
    (SHORTLIST, [
        r"\b(list|show me|options|recommend|what do you have|available|متاح|خيارات|عرض|مشاريع)\b",
    ]),
    (INFO_QUERY, [
        r"\b(project|property|apartment|villa|chalet|duplex|penthouse|townhouse|loft|"
        r"unit|bedroom|sqm|meter|area|region|north coast|ain sokhna|new cairo|maadi|"
        r"mostakbal|6th october|amenities|pool|gym|delivery|handover|status|"
        r"finishing|furnished|مشروع|شقة|فيلا|شاليه|غرفة|متر|منطقة|تسليم|وحدة)\b",
    ]),
]


def detect_intent(message: str, lang: str = "en") -> str:
    """Rule-based intent classification for the Concierge Brain."""
    text = message.lower()
    for intent, patterns in PATTERNS:
        for pattern in patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return intent
    return UNKNOWN


# ── Constraint Extractors ───────────────────────────────────────────────────

def extract_project_hint(message: str, entity_names: List[str]) -> Optional[str]:
    text = message.lower()
    best_len = 0
    best_name: Optional[str] = None
    for name in entity_names:
        if name.lower() in text:
            if len(name) > best_len:
                best_len = len(name)
                best_name = name
    return best_name


def extract_region_hint(message: str) -> Optional[str]:
    regions = {
        "east cairo": "East Cairo",
        "new cairo": "East Cairo",
        "mostakbal": "East Cairo",
        "west cairo": "West Cairo",
        "6th october": "West Cairo",
        "north coast": "North Coast",
        "ain sokhna": "Ain El Sokhna",
        "sokhna": "Ain El Sokhna",
        "maadi": "Cairo",
        "zaraa": "Cairo",
        "zahraa": "Cairo",
        "red sea": "Ain El Sokhna",
        "الساحل": "North Coast",
        "التجمع": "East Cairo",
        "العين السخنة": "Ain El Sokhna",
        "القاهرة": "Cairo",
    }
    text = message.lower()
    for kw, region in regions.items():
        if kw in text:
            return region
    return None


def extract_unit_type_hint(message: str) -> Optional[str]:
    types = ["villa", "apartment", "chalet", "duplex", "penthouse", "townhouse", "loft", "twinhouse","فيلا","شقة","شاليه"]
    text = message.lower()
    for t in types:
        if t in text:
            return t
    return None


def extract_budget_hint(message: str) -> Optional[str]:
    text = message.lower()
    match = re.search(r"\b(\d+(?:\.\d+)?)\s*(million|m|k|thousand|مليون|الف)\b", text)
    if match:
        return match.group(0)
    return None


def extract_timeline_hint(message: str) -> Optional[str]:
    text = message.lower()
    if re.search(r"\b(immediate|now|ready|جاهز|فوري|الآن)\b", text):
        return "Immediate"
    match = re.search(r"\b(\d+)\s*(months?|years?|شهر|سنة|سنين)\b", text)
    if match:
        return match.group(0)
    return None


def extract_purpose_hint(message: str) -> Optional[str]:
    text = message.lower()
    if re.search(r"\b(invest|investment|roi|استثمار)\b", text):
        return "invest"
    # Note: 'rent' is generally a handoff intent at WDD, but logged as purpose
    if re.search(r"\b(rent|rental|ايجار)\b", text):
        return "rent"
    if re.search(r"\b(buy|purchase|live|شراء|اسكن)\b", text):
        return "buy"
    return None

