"""
PulseX-WDD Intent Router — Pattern-based deterministic routing.
NO LLM calls. Uses regex + fuzzy matching against KB project names.
"""

import re
import logging
from typing import List, Optional
from rapidfuzz import process, fuzz

from app.backend.models import IntentType, RoutedIntent

logger = logging.getLogger("PulseX-WDD-Router")

# --- Pattern banks ---

_GREETING_PATTERNS = re.compile(
    r"^(hi|hello|hey|good\s*(morning|afternoon|evening)|assalamu|salam|marhaba|greetings|howdy|what'?s up|sup)\b",
    re.IGNORECASE
)

_HIGH_INTENT_PATTERNS = re.compile(
    r"\b(price|pricing|cost|how\s+much|payment\s*plan|installment|down\s*payment|brochure|"
    r"availab|viewing|site\s*visit|book|schedule|callback|call\s*back|call\s*me|"
    r"whatsapp|send\s*(me|details|prices|info)|interested|want\s*to\s*(buy|rent|invest|book)|"
    r"i\s*want|sign\s*me\s*up|reserve|deposit)\b",
    re.IGNORECASE
)

_LIST_PATTERNS = re.compile(
    r"\b(list\s*(all)?|show\s*(me\s*)?(all|every|properties|projects|portfolio)|"
    r"what\s*(properties|projects|do\s*you\s*have)|all\s*(properties|projects)|"
    r"portfolio|everything\s*you\s*(have|offer))\b",
    re.IGNORECASE
)

_NON_SALES_PATTERNS = re.compile(
    r"\b(complaint|complain|refund|maintenance|repair|broken|customer\s*service|"
    r"finance\s*department|accounting|legal|existing\s*owner|already\s*(bought|own)|"
    r"after\s*sales|warranty|defect)\b",
    re.IGNORECASE
)

_YES_PATTERNS = re.compile(
    r"^(yes|yeah|yep|yup|correct|confirmed?|that'?s?\s*(right|correct)|absolutely|sure|go\s*ahead|ok|okay|proceed|approve|lgtm)\s*[.!]?$",
    re.IGNORECASE
)

_NO_PATTERNS = re.compile(
    r"^(no|nope|nah|not?\s*(correct|right|yet)|wrong|incorrect|cancel|stop|don'?t|decline)\s*[.!]?$",
    re.IGNORECASE
)

# --- Region extraction ---

_REGION_MAP = {
    "ain el sokhna": "Ain El Sokhna",
    "sokhna": "Ain El Sokhna",
    "el sokhna": "Ain El Sokhna",
    "north coast": "North Coast",
    "sahel": "North Coast",
    "east cairo": "East Cairo",
    "new cairo": "East Cairo",
    "mostakbal": "East Cairo",
    "mostakbal city": "East Cairo",
    "cairo": "Cairo",
    "maadi": "Cairo",
    "zahraa": "Cairo",
    "west cairo": "West Cairo",
    "6th of october": "West Cairo",
    "october": "West Cairo",
    "sheikh zayed": "West Cairo",
    "coast": "North Coast",
    "red sea": "Ain El Sokhna",
    "sidi abd el rahman": "North Coast",
}

# --- Unit type extraction ---

_UNIT_TYPES = [
    "apartment", "villa", "chalet", "townhouse", "twinhouse",
    "duplex", "penthouse", "loft", "retail", "office", "commercial",
    "studio", "flat",
]


class IntentRouter:
    def __init__(self):
        self._project_names: List[str] = []
        self._project_slugs: List[str] = []

    def set_kb_projects(self, names: List[str], slugs: List[str]):
        """Called once at startup after KB loads."""
        self._project_names = names
        self._project_slugs = slugs
        logger.info(f"IntentRouter loaded {len(names)} project names for matching")

    def route(self, message: str, turn_count: int = 0, stage: str = "GREETING") -> RoutedIntent:
        """Deterministic intent routing — zero LLM calls."""
        msg = message.strip()
        msg_lower = msg.lower()

        # 1. Confirmation gates (only when stage expects them)
        if stage in ("RECAP_PENDING", "CONSENT_PENDING", "CAPTURE_PHONE"):
            if _YES_PATTERNS.match(msg):
                return RoutedIntent(
                    intent=IntentType.CONFIRMATION_YES,
                    raw_query=msg,
                )
            if _NO_PATTERNS.match(msg):
                return RoutedIntent(
                    intent=IntentType.CONFIRMATION_NO,
                    raw_query=msg,
                )
            # If in capture_phone stage, treat any input as potential phone
            if stage == "CAPTURE_PHONE":
                # Check if this looks like a phone number
                phone_match = re.search(r'[\+]?\d[\d\s\-]{7,}', msg)
                if phone_match:
                    return RoutedIntent(
                        intent=IntentType.CONFIRMATION_YES,
                        raw_query=msg,
                    )

        # 2. Extract entities from message
        matched_projects = self._match_projects(msg_lower)
        extracted_region = self._extract_region(msg_lower)
        extracted_unit_type = self._extract_unit_type(msg_lower)

        # 3. High-intent check (overrides everything except confirmation gates)
        if _HIGH_INTENT_PATTERNS.search(msg):
            return RoutedIntent(
                intent=IntentType.HIGH_INTENT,
                matched_projects=matched_projects,
                extracted_region=extracted_region,
                extracted_unit_type=extracted_unit_type,
                is_high_intent=True,
                raw_query=msg,
            )

        # 4. Non-sales
        if _NON_SALES_PATTERNS.search(msg):
            return RoutedIntent(
                intent=IntentType.NON_SALES,
                raw_query=msg,
            )

        # 5. List portfolio
        if _LIST_PATTERNS.search(msg):
            return RoutedIntent(
                intent=IntentType.LIST_PORTFOLIO,
                extracted_region=extracted_region,
                extracted_unit_type=extracted_unit_type,
                raw_query=msg,
            )

        # 6. Greeting (first turn or explicit greeting with no other content)
        if turn_count == 0 and (len(msg_lower.split()) <= 5 or _GREETING_PATTERNS.match(msg)):
            return RoutedIntent(
                intent=IntentType.GREETING,
                matched_projects=matched_projects,
                extracted_region=extracted_region,
                extracted_unit_type=extracted_unit_type,
                raw_query=msg,
            )
        if _GREETING_PATTERNS.match(msg) and len(msg_lower.split()) <= 3:
            return RoutedIntent(
                intent=IntentType.GREETING,
                raw_query=msg,
            )

        # 7. Project discovery (mentioned a specific project name)
        if matched_projects:
            return RoutedIntent(
                intent=IntentType.PROJECT_DISCOVERY,
                matched_projects=matched_projects,
                extracted_region=extracted_region,
                extracted_unit_type=extracted_unit_type,
                raw_query=msg,
            )

        # 8. General QA (default)
        return RoutedIntent(
            intent=IntentType.GENERAL_QA,
            extracted_region=extracted_region,
            extracted_unit_type=extracted_unit_type,
            raw_query=msg,
        )

    def _match_projects(self, msg_lower: str) -> List[str]:
        """Fuzzy-match user message against KB project names."""
        if not self._project_names:
            return []

        matched = []
        # Direct substring check first
        for name in self._project_names:
            if name.lower() in msg_lower:
                matched.append(name)

        if matched:
            return matched[:3]

        # Fuzzy match on individual words/phrases
        words = msg_lower.split()
        for i in range(len(words)):
            for j in range(i + 1, min(i + 4, len(words) + 1)):
                phrase = " ".join(words[i:j])
                if len(phrase) < 3:
                    continue
                results = process.extract(
                    phrase,
                    self._project_names,
                    scorer=fuzz.WRatio,
                    limit=2,
                    score_cutoff=75,
                )
                for match_str, score, _ in results:
                    if match_str not in matched:
                        matched.append(match_str)

        return matched[:3]

    def _extract_region(self, msg_lower: str) -> Optional[str]:
        """Extract region from message text."""
        for keyword, region in _REGION_MAP.items():
            if keyword in msg_lower:
                return region
        return None

    def _extract_unit_type(self, msg_lower: str) -> Optional[str]:
        """Extract unit type from message."""
        for ut in _UNIT_TYPES:
            pattern = r'\b' + re.escape(ut) + r's?\b'
            if re.search(pattern, msg_lower):
                return ut
        return None


intent_router = IntentRouter()
