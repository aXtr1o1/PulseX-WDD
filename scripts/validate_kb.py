#!/usr/bin/env python3
"""
PulseX-WDD – KB Validator
Sanity-checks buyerKB.csv for common issues.
Critical: Detects "installment years" false positives (years of experience
mistaken as payment plan years).

Usage:
    python scripts/validate_kb.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT / "apps" / "api"))

from app.config import get_settings
from app.utils.kb_loader import load_kb

# Keywords that MUST appear near an installment year number to be valid
INSTALLMENT_CONTEXT_PATTERNS = [
    r"\binstallment", r"\bpayment plan", r"\bpay\b", r"\bdownpayment",
    r"\bmonthly", r"\bquart", r"\bsemi.?annual", r"\byears to pay",
]

# Suspicious "years" context that suggests experience, not installments
FALSE_POSITIVE_CONTEXT_PATTERNS = [
    r"\bexperience\b", r"\boperat", r"\bfound", r"\bestablish",
    r"\byears? of", r"\bsince \d{4}", r"\bcelebrat",
]


def _looks_like_installment_context(text: str) -> bool:
    """Return True if text has installment-related keywords."""
    t = text.lower()
    return any(re.search(p, t) for p in INSTALLMENT_CONTEXT_PATTERNS)


def _looks_like_false_positive(text: str) -> bool:
    """Return True if text suggests company age / experience context."""
    t = text.lower()
    return any(re.search(p, t) for p in FALSE_POSITIVE_CONTEXT_PATTERNS)


def validate_kb() -> None:
    settings = get_settings()
    entities = load_kb(settings.kb_csv_path)

    errors = 0
    warnings = 0

    print(f"\nValidating {len(entities)} KB entities...\n")

    for e in entities:
        eid = e["entity_id"]

        # ── Required fields
        if not e.get("display_name"):
            print(f"[ERROR] {eid}: missing display_name")
            errors += 1
        if not e.get("region"):
            print(f"[WARN ] {eid}: missing region")
            warnings += 1
        if not e.get("verified_url") and not e.get("official_url"):
            print(f"[WARN ] {eid}: no verified or official URL")
            warnings += 1

        # ── Installment years false-positive guard
        inst_min = e.get("installment_min")
        inst_max = e.get("installment_max")
        if inst_min or inst_max:
            # Check index_text for suspicious context
            text = e.get("index_text", "")
            if _looks_like_false_positive(text) and not _looks_like_installment_context(text):
                print(
                    f"[CRITICAL] {eid}: installment_years ({inst_min}-{inst_max}) "
                    f"may be a FALSE POSITIVE. Text snippet: '{text[:120]}'"
                )
                errors += 1
            else:
                # Validate range is reasonable (1-30 years)
                try:
                    mn = float(inst_min) if inst_min else None
                    mx = float(inst_max) if inst_max else None
                    if mn and (mn < 1 or mn > 30):
                        print(f"[WARN ] {eid}: installment_min={mn} out of range 1-30")
                        warnings += 1
                    if mx and (mx < 1 or mx > 30):
                        print(f"[WARN ] {eid}: installment_max={mx} out of range 1-30")
                        warnings += 1
                except ValueError:
                    print(f"[ERROR] {eid}: non-numeric installment years: {inst_min}/{inst_max}")
                    errors += 1

        # ── Confidence score
        conf = e.get("confidence", 0)
        if float(conf) < 0.5:
            print(f"[WARN ] {eid}: low confidence_score={conf}")
            warnings += 1

        # ── Unit types should be a list
        if not isinstance(e.get("unit_types"), list):
            print(f"[ERROR] {eid}: unit_types is not a list")
            errors += 1

    print(f"\n{'─'*50}")
    print(f"Result: {errors} errors, {warnings} warnings across {len(entities)} entities.")
    if errors:
        print("❌ KB validation FAILED — review errors above.")
        sys.exit(1)
    else:
        print("✅ KB validation passed.")


if __name__ == "__main__":
    validate_kb()
