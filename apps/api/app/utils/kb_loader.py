"""
PulseX-WDD – KB Loader
Robustly reads buyerKB.csv with dynamic column mapping.
Produces canonical fields regardless of exact CSV column names.
"""
from __future__ import annotations

import csv
import hashlib
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# ── Canonical field -> possible CSV column name aliases ─────────────────────
COLUMN_MAP: Dict[str, List[str]] = {
    "entity_id":        ["entity_id", "project_id", "id"],
    "display_name":     ["display_name", "project_name", "name"],
    "parent_project":   ["parent_project", "parent"],
    "is_alias_of":      ["is_alias_of", "alias_of"],
    "region":           ["region"],
    "city_area":        ["city_area", "city"],
    "micro_location":   ["micro_location", "location_text", "location"],
    "project_type":     ["project_type", "type"],
    "project_status":   ["project_status", "status"],
    "sales_status":     ["current_sales_status", "sales_status"],
    "inventory_status": ["developer_inventory_status", "inventory_status"],
    "unit_types_raw":   ["unit_types_offered_json", "unit_types_json", "unit_types"],
    "price_status":     ["price_status"],
    "payment_plan":     ["payment_plan_headline", "payment_plan"],
    "downpayment_min":  ["downpayment_percent_min", "downpayment_min"],
    "downpayment_max":  ["downpayment_percent_max", "downpayment_max"],
    "installment_min":  ["installment_years_min"],
    "installment_max":  ["installment_years_max"],
    "delivery_year_min": ["delivery_year_min"],
    "delivery_year_max": ["delivery_year_max"],
    "amenities_raw":    ["key_amenities_json", "amenities_json", "amenities"],
    "sources_raw":      ["source_links_json", "sources_json", "sources"],
    "brochure_raw":     ["brochure_urls_json", "brochure_urls"],
    "verified_url":     ["verified_url"],
    "confidence_score": ["confidence_score", "truth_confidence"],
    "verified_on_wdd":  ["verified_on_wdd_site", "verified"],
    "disclaimers_raw":  ["disclaimers_json", "disclaimers"],
    "zones_raw":        ["zones_json", "zones"],
    "last_verified_date": ["last_verified_date", "freshness_date"],
    "official_url":     ["official_project_url", "project_url", "url"],
    "inquiry_url":      ["inquiry_form_url", "inquiry_url"],
    "beach_flag":       ["beach_access_flag", "beach_access"],
    "golf_flag":        ["golf_flag", "golf"],
    "lagoons_flag":     ["lagoons_flag", "lagoons"],
    "brand_family":     ["brand_family", "brand"],
}


def _pick(row: Dict[str, Any], canonical: str) -> Optional[str]:
    """Return first matching column value for canonical key."""
    for col in COLUMN_MAP.get(canonical, [canonical]):
        if col in row and row[col] not in (None, "", "nan"):
            return str(row[col]).strip()
    return None


def _parse_json_list(raw: Optional[str]) -> List[str]:
    """Parse JSON array string -> Python list of strings."""
    if not raw:
        return []
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, list):
            return [str(i) for i in parsed]
    except Exception:
        pass
    # Fallback: comma-split
    return [s.strip() for s in raw.split(",") if s.strip()]


def _compute_answerability(row_canonical: Dict[str, Any]) -> float:
    """
    Score 0-1 based on how much useful info we have.
    Penalised if price_status is on_request and no brochure.
    """
    score = 0.0
    if row_canonical.get("verified_url"):
        score += 0.3
    if row_canonical.get("unit_types"):
        score += 0.2
    if row_canonical.get("brochures"):
        score += 0.2
    if row_canonical.get("amenities"):
        score += 0.1
    if row_canonical.get("confidence"):
        score += float(row_canonical["confidence"]) * 0.2
    return round(min(score, 1.0), 3)


def load_kb(csv_path: Path) -> List[Dict[str, Any]]:
    """
    Load buyerKB.csv and return a list of canonical entity dicts.
    Robust to column name variations.
    """
    if not csv_path.exists():
        logger.error("KB CSV not found: %s", csv_path)
        return []

    rows: List[Dict[str, Any]] = []
    with open(csv_path, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for i, raw in enumerate(reader):
            if not any(v.strip() for v in raw.values()):
                continue  # skip blank rows

            c: Dict[str, Any] = {}
            c["entity_id"]        = _pick(raw, "entity_id") or f"entity_{i}"
            c["display_name"]     = _pick(raw, "display_name") or c["entity_id"]
            c["parent_project"]   = _pick(raw, "parent_project")
            c["is_alias_of"]      = _pick(raw, "is_alias_of")
            c["region"]           = _pick(raw, "region")
            
            if not c["region"]:
                logger.warning("Skipping project row %s due to missing region metadata.", c["entity_id"])
                continue

            c["city_area"]        = _pick(raw, "city_area")
            c["location_text"]    = _pick(raw, "micro_location")
            c["brand_family"]     = _pick(raw, "brand_family")
            c["project_type"]     = _pick(raw, "project_type")
            c["project_status"]   = _pick(raw, "project_status")
            c["sales_status"]     = _pick(raw, "sales_status")
            c["inventory_status"] = _pick(raw, "inventory_status")
            c["price_status"]     = _pick(raw, "price_status")
            c["payment_plan"]     = _pick(raw, "payment_plan")
            c["downpayment_min"]  = _pick(raw, "downpayment_min")
            c["downpayment_max"]  = _pick(raw, "downpayment_max")
            # Installment years - only numeric, only from specific columns
            c["installment_min"]  = _pick(raw, "installment_min")
            c["installment_max"]  = _pick(raw, "installment_max")
            c["delivery_year_min"] = _pick(raw, "delivery_year_min")
            c["delivery_year_max"] = _pick(raw, "delivery_year_max")
            c["verified_url"]     = _pick(raw, "verified_url")
            c["official_url"]     = _pick(raw, "official_url")
            c["inquiry_url"]      = _pick(raw, "inquiry_url")
            c["last_verified_date"] = _pick(raw, "last_verified_date")

            confidence_raw = _pick(raw, "confidence_score")
            try:
                c["confidence"] = float(confidence_raw) if confidence_raw else 0.7
            except ValueError:
                c["confidence"] = 0.7

            # Lists
            c["unit_types"] = _parse_json_list(_pick(raw, "unit_types_raw"))
            c["amenities"]  = _parse_json_list(_pick(raw, "amenities_raw"))
            c["sources"]    = _parse_json_list(_pick(raw, "sources_raw"))
            c["brochures"]  = _parse_json_list(_pick(raw, "brochure_raw"))
            c["disclaimers"] = _parse_json_list(_pick(raw, "disclaimers_raw"))
            zones_raw = _pick(raw, "zones_raw")
            if zones_raw:
                try:
                    zones_parsed = json.loads(zones_raw)
                    c["zones"] = [z.get("name", str(z)) for z in zones_parsed if isinstance(z, dict)]
                except Exception:
                    c["zones"] = []
            else:
                c["zones"] = []

            c["answerability"] = _compute_answerability(c)

            # Text blob for indexing
            c["index_text"] = " | ".join(filter(None, [
                c["display_name"],
                " ".join(c["zones"]),
                c["region"] or "",
                c["city_area"] or "",
                c["location_text"] or "",
                " ".join(c["unit_types"]),
                " ".join(c["amenities"][:10]),
                c["project_type"] or "",
                c["brand_family"] or "",
            ]))

            rows.append(c)

    logger.info("Loaded %d entities from KB: %s", len(rows), csv_path)
    return rows


def kb_file_hash(csv_path: Path) -> str:
    """Return short SHA256 of KB file for audit versioning."""
    h = hashlib.sha256()
    with open(csv_path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()[:12]
