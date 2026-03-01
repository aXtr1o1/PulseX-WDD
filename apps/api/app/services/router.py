"""
PulseX-WDD – Intent Router
Classifies user messages into WDD intents.
"""
from __future__ import annotations

import re
from typing import Dict, List, Optional, Tuple

# Intent names
PROPERTY_QUESTION    = "property_question"
SALES_INTENT         = "sales_intent"
COMPLAINT            = "complaint"
PAYMENT_SERVICES     = "payment_services"
DIRECTORY            = "directory"
PRIVATE_SERVICES     = "private_services_reservation"
GATE_ACCESS          = "gate_access"
HOTELS               = "hotels"
RENTALS              = "rentals_ever_stay"
REFERRAL             = "referral_grow_the_family"
UNKNOWN              = "unknown"

GREETING             = "greeting"

# ── Keyword patterns per intent (order matters – checked top-down) ──────────
PATTERNS: List[Tuple[str, List[str]]] = [
    (GREETING, [
        r"\b(hi|hello|hey|good morning|good afternoon|good evening|مرحبا|اهلا|صباح الخير|مساء الخير)\b",
    ]),
    (SALES_INTENT, [
        r"\b(buy|book|purchase|reserve|invest|interested in|interested to|callback|call me|call back|"
        r"contact sale|speak to|talk to sales|visit|schedule|arrange|set up.*(meeting|call|visit)|"
        r"payment plan|send brochure|brochure|أريد.*(شراء|حجز|استثمار|زيارة)|اتصل|أتصل|كتيب|تفاصيل الدفع)\b",
    ]),
    (COMPLAINT, [
        r"\b(complain|problem|issue|broken|maintenance|repair|damage|شكوى|مشكلة|عطل)\b",
    ]),
    (PAYMENT_SERVICES, [
        r"\b(pay|payment|invoice|receipt|overdue|installment|قسط|دفع|فاتورة)\b",
    ]),
    (GATE_ACCESS, [
        r"\b(gate|access|entry|visitor pass|id|identification|بوابة|دخول)\b",
    ]),
    (HOTELS, [
        r"\b(hotel|stay|night|accommodation|فندق|إقامة)\b",
    ]),
    (RENTALS, [
        r"\b(rent|rental|ever.?stay|للإيجار|إيجار)\b",
    ]),
    (REFERRAL, [
        r"\b(refer|referral|grow the family|introduce|friend|family member|توصية|ترشيح)\b",
    ]),
    (PRIVATE_SERVICES, [
        r"\b(reservation|book.*(facility|court|pool|club)|reserve a|حجز.*(ملعب|مسبح|نادي))\b",
    ]),
    (DIRECTORY, [
        r"\b(directory|find|where is|contact|phone number|email|address|location|دليل|مكان|عنوان)\b",
    ]),
    (PROPERTY_QUESTION, [
        r"\b(project|property|apartment|villa|chalet|duplex|penthouse|townhouse|loft|"
        r"unit|bedroom|sqm|meter|area|region|north coast|ain sokhna|new cairo|maadi|"
        r"mostakbal|6th october|amenities|pool|gym|delivery|handover|status|available|"
        r"finishing|furnished|مشروع|شقة|فيلا|شاليه|غرفة|متر|منطقة|تسليم|وحدة)\b",
    ]),
]


def detect_intent(message: str, lang: str = "en") -> str:
    """Rule-based intent classification. Returns one of the INTENT constants."""
    text = message.lower()
    for intent, patterns in PATTERNS:
        for pattern in patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return intent
    return UNKNOWN


def extract_project_hint(message: str, entity_names: List[str]) -> Optional[str]:
    """
    Try to find a project name mentioned in the message.
    Returns the entity_id of the matched project, or None.
    """
    text = message.lower()
    # Exact + partial match — longest match wins
    best: Optional[Tuple[int, str]] = None
    for name in entity_names:
        if name.lower() in text:
            if best is None or len(name) > best[0]:
                best = (len(name), name)
    return best[1] if best else None


def extract_region_hint(message: str) -> Optional[str]:
    """Extract region keyword from message."""
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
    """Extract unit type from message."""
    types = ["villa", "apartment", "chalet", "duplex", "penthouse", "townhouse", "loft", "twinhouse","فيلا","شقة","شاليه"]
    text = message.lower()
    for t in types:
        if t in text:
            return t
    return None
