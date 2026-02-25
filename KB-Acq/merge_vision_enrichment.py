#!/usr/bin/env python3
"""
merge_vision_enrichment.py
PulseX-WDD — Vision Enrichment Merge + Validation + Final KB Write

Reads AOAI candidate JSONs (from aoai_field_mapper.py),
merges evidence-backed values into the buyer KB (non-destructively),
runs validation gates, writes final KB to both paths, 
and updates the sources audit + merge report.

Usage:
  /tmp/pulsex_venv/bin/python3 KB-Acq/merge_vision_enrichment.py
"""

import os, sys, json, csv, logging, shutil
from pathlib import Path
from datetime import datetime, timezone

REPO_ROOT = Path("/Volumes/ReserveDisk/codeBase/PulseX-WDD")
KB_ACQ    = REPO_ROOT / "KB-Acq"
OUTPUTS   = KB_ACQ / "outputs"
INTER     = OUTPUTS / "intermediate"
LOGS      = KB_ACQ / "logs"
ENGINE_KB = REPO_ROOT / "engine-KB"

LOGS.mkdir(parents=True, exist_ok=True)

LOG_PATH = LOGS / "wdd_vision_merge.log"
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%SZ",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(LOG_PATH, encoding="utf-8"),
    ],
)
log = logging.getLogger("merge")
TODAY = datetime.now(timezone.utc).strftime("%Y-%m-%d")

KB_ENGINE_PATH = ENGINE_KB / "PulseX-WDD_buyerKB.csv"
KB_ACQ_PATH    = OUTPUTS / "PulseX-WDD_buyerKB.csv"
AUDIT_PATH     = OUTPUTS / "wdd_sources_audit.csv"
SCREENS_PATH   = OUTPUTS / "wdd_screens_index.csv"
MERGE_REPORT   = INTER / "wdd_vision_merge_report.csv"

AUDIT_HEADER = [
    "project_id","field_name","field_value","source_url","evidence_type",
    "evidence_snippet","asset_path_or_pdf_page","captured_date",
    "parser_confidence","overwrite_flag","notes",
]
MERGE_HEADER = [
    "project_id","field_name","old_value","new_value","source_used",
    "evidence_type","updated_flag","reason",
]

# JSON columns that must always be valid JSON
JSON_COLS = [
    "unit_types_offered_json","finishing_levels_offered_json","key_amenities_json",
    "brochure_urls_json","gallery_urls_json","source_links_json",
    "screenshot_paths_json","disclaimers_json","zones_json",
    "unit_templates_json","listings_json",
]

# ─── KB LOAD / SAVE ───────────────────────────────────────────────────────────
def load_kb() -> tuple[list[dict], list[str]]:
    with open(KB_ENGINE_PATH, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        return rows, list(reader.fieldnames)

def save_kb(rows: list[dict], fieldnames: list[str]):
    for path in [KB_ENGINE_PATH, KB_ACQ_PATH]:
        with open(path, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=fieldnames)
            w.writeheader()
            w.writerows(rows)
    log.info(f"KB written to engine-KB + outputs ({len(rows)} rows)")

def backup_kb():
    ts = datetime.now().strftime("%Y-%m-%d_%H%M")
    bk_dir = ENGINE_KB / "backups"
    bk_dir.mkdir(parents=True, exist_ok=True)
    bk = bk_dir / f"PulseX-WDD_buyerKB_{ts}.csv"
    shutil.copy2(KB_ENGINE_PATH, bk)
    log.info(f"Backup saved: {bk}")

def load_audit() -> list[dict]:
    if not AUDIT_PATH.exists():
        return []
    with open(AUDIT_PATH, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))

def save_audit(rows: list[dict]):
    with open(AUDIT_PATH, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=AUDIT_HEADER, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)

# ─── JSON FIELD HELPERS ───────────────────────────────────────────────────────
def parse_json_safe(val: str) -> list | dict | None:
    if not val or not val.strip():
        return None
    try:
        return json.loads(val)
    except Exception:
        return None

def merge_json_lists(existing_str: str, new_items: list[str]) -> str:
    """Merge new items into an existing JSON list, deduplicating."""
    existing = parse_json_safe(existing_str) or []
    existing_lower = {str(x).lower() for x in existing}
    merged = list(existing)
    for item in (new_items or []):
        if str(item).lower() not in existing_lower:
            merged.append(item)
            existing_lower.add(str(item).lower())
    return json.dumps(merged, ensure_ascii=False)

def normalize_numeric(val) -> str | None:
    """Normalize a value to clean numeric string."""
    if val is None:
        return None
    s = str(val).strip().replace(",", "").replace(" ", "")
    # Handle shorthand: 4.5M → 4500000
    import re
    m = re.match(r'^([\d\.]+)[Mm](?:illion)?$', s)
    if m:
        return str(int(float(m.group(1)) * 1_000_000))
    # Must be numeric
    if re.match(r'^[\d\.]+$', s):
        return str(int(float(s))) if '.' in s else s
    return None  # Not cleanly numeric — reject

# ─── FIELD MERGE RULES ────────────────────────────────────────────────────────
# Map from candidate key → KB column name (and merge strategy)
FIELD_MAP = {
    # Direct numeric fields (only set if currently empty)
    "bedrooms_range_min": ("bedrooms_range_min", "numeric"),
    "bedrooms_range_max": ("bedrooms_range_max", "numeric"),
    "bua_range_min_sqm":  ("bua_range_min_sqm", "numeric"),
    "bua_range_max_sqm":  ("bua_range_max_sqm", "numeric"),
    "starting_price_value": ("starting_price_value", "numeric"),
    "price_range_min":    ("price_range_min", "numeric"),
    "price_range_max":    ("price_range_max", "numeric"),
    "downpayment_percent_min": ("downpayment_percent_min", "numeric"),
    "downpayment_percent_max": ("downpayment_percent_max", "numeric"),
    "installment_years_min": ("installment_years_min", "numeric"),
    "installment_years_max": ("installment_years_max", "numeric"),
    "delivery_year_min":  ("delivery_year_min", "numeric"),
    "delivery_year_max":  ("delivery_year_max", "numeric"),
    # String fields (only set if currently empty)
    "price_status":       ("price_status", "string"),
    "pricing_disclaimer": ("pricing_disclaimer", "string"),
    "payment_plan_headline": ("payment_plan_headline", "string"),
    "delivery_window":    ("delivery_window", "string"),
    # JSON list fields (always merge/extend)
    "unit_types_offered_json": ("unit_types_offered_json", "json_list"),
    "key_amenities_json":      ("key_amenities_json", "json_list"),
    "finishing_levels_offered_json": ("finishing_levels_offered_json", "json_list"),
    # Nested JSON fields (set if currently empty/[])
    "unit_templates_json": ("unit_templates_json", "json_nested"),
    "listings_json":       ("listings_json", "json_nested"),
}

ALLOWED_PRICE_STATUS = {"official", "on_request", "unknown"}

def apply_candidates_to_row(
    row: dict,
    candidates: dict,
    project_id: str,
) -> tuple[dict, list[dict], list[dict]]:
    """
    Apply AOAI candidate fields to a KB row (non-destructively).
    Returns (updated_row, audit_rows, merge_report_rows)
    """
    audit_rows = []
    merge_rows = []

    evidence = candidates.get("_evidence", {})

    # Source reference for audit
    # Try to find the vision text file path
    vision_txt = INTER / f"{project_id}__vision_text.txt"
    source_ref = str(vision_txt) if vision_txt.exists() else f"vision/{project_id}"

    def make_audit(field, val, snippet, confidence="medium", overwrite=False):
        return {
            "project_id": project_id,
            "field_name": field,
            "field_value": str(val)[:500],
            "source_url": f"vision_extraction:{project_id}",
            "evidence_type": "docintel+aoai_vision",
            "evidence_snippet": str(snippet or "")[:300],
            "asset_path_or_pdf_page": source_ref,
            "captured_date": TODAY,
            "parser_confidence": confidence,
            "overwrite_flag": "true" if overwrite else "false",
            "notes": "Vision pipeline: pdf2image → DocIntel/GPT-4o → GPT-4o structured extraction",
        }

    def make_merge(field, old, new, updated, reason):
        return {
            "project_id": project_id,
            "field_name": field,
            "old_value": str(old)[:200],
            "new_value": str(new)[:200],
            "source_used": "vision_pipeline",
            "evidence_type": "docintel+aoai_vision",
            "updated_flag": "true" if updated else "false",
            "reason": reason,
        }

    for cand_key, (kb_col, strategy) in FIELD_MAP.items():
        if kb_col not in row:
            continue

        candidate_val = candidates.get(cand_key)
        old_val = row.get(kb_col, "").strip()
        snippet = evidence.get(cand_key.split("_")[0], "") or ""

        if strategy == "numeric":
            if candidate_val is None:
                continue
            norm = normalize_numeric(candidate_val)
            if norm is None:
                log.debug(f"  {project_id}.{kb_col}: couldn't normalize '{candidate_val}' → skip")
                continue
            if not old_val:
                # Set new value
                row[kb_col] = norm
                audit_rows.append(make_audit(kb_col, norm, snippet))
                merge_rows.append(make_merge(kb_col, old_val, norm, True, "field_was_empty"))
                log.info(f"  {project_id}.{kb_col}: → '{norm}'")
            else:
                merge_rows.append(make_merge(kb_col, old_val, norm, False, "field_already_populated"))

        elif strategy == "string":
            if not candidate_val:
                continue
            val_str = str(candidate_val).strip()
            if not val_str:
                continue

            # Special validation for price_status
            if kb_col == "price_status" and val_str not in ALLOWED_PRICE_STATUS:
                log.warning(f"  {project_id}.{kb_col}: invalid value '{val_str}' — skip")
                continue

            if not old_val:
                row[kb_col] = val_str
                audit_rows.append(make_audit(kb_col, val_str, snippet))
                merge_rows.append(make_merge(kb_col, old_val, val_str, True, "field_was_empty"))
                log.info(f"  {project_id}.{kb_col}: → '{val_str[:60]}'")
            elif kb_col == "price_status":
                # price_status: upgrade from "unknown" to more specific
                if old_val == "unknown" and val_str in ("official", "on_request"):
                    row[kb_col] = val_str
                    audit_rows.append(make_audit(kb_col, val_str, snippet))
                    merge_rows.append(make_merge(kb_col, old_val, val_str, True, "upgraded_from_unknown"))
                    log.info(f"  {project_id}.{kb_col}: '{old_val}' → '{val_str}' (upgrade)")
                else:
                    merge_rows.append(make_merge(kb_col, old_val, val_str, False, "field_already_populated"))
            else:
                merge_rows.append(make_merge(kb_col, old_val, val_str, False, "field_already_populated"))

        elif strategy == "json_list":
            new_items = candidate_val
            if not isinstance(new_items, list) or not new_items:
                continue
            old_json = parse_json_safe(old_val) if old_val else []
            merged = merge_json_lists(old_val, new_items)
            if parse_json_safe(merged) != (old_json or []):
                row[kb_col] = merged
                added = [x for x in (parse_json_safe(merged) or []) if x not in (old_json or [])]
                audit_rows.append(make_audit(kb_col, merged[:200], snippet))
                merge_rows.append(make_merge(
                    kb_col, old_val[:100] if old_val else "[]",
                    merged[:100], True,
                    f"merged_from_vision: added {added}"
                ))
                log.info(f"  {project_id}.{kb_col}: merged {len(added)} new items")
            else:
                merge_rows.append(make_merge(kb_col, old_val, merged, False, "no_new_items"))

        elif strategy == "json_nested":
            if not candidate_val:
                continue
            if isinstance(candidate_val, list) and len(candidate_val) > 0:
                old_parsed = parse_json_safe(old_val)
                # Only set if currently empty or empty list
                if not old_parsed:
                    new_json = json.dumps(candidate_val, ensure_ascii=False)
                    row[kb_col] = new_json
                    audit_rows.append(make_audit(kb_col, new_json[:200], snippet, confidence="medium"))
                    merge_rows.append(make_merge(kb_col, "[]", new_json[:100], True, "set_from_vision"))
                    log.info(f"  {project_id}.{kb_col}: set {len(candidate_val)} items from vision")

    # Handle pricing_date — set if starting_price or price_range was just set
    if "starting_price_value" in candidates and candidates["starting_price_value"]:
        if not row.get("pricing_date", "").strip():
            row["pricing_date"] = TODAY
            audit_rows.append(make_audit("pricing_date", TODAY, "auto-set on price extraction"))
            merge_rows.append(make_merge("pricing_date", "", TODAY, True, "auto_set_with_price"))

    # Handle last_verified_date — update to today
    row["last_verified_date"] = TODAY

    # Handle confidence_score — recompute based on populated fields
    row["confidence_score"] = str(compute_confidence(row))

    return row, audit_rows, merge_rows


def compute_confidence(row: dict) -> float:
    """Recompute confidence score based on evidence coverage."""
    score = 0.30
    if row.get("official_project_url", "").strip():
        score += 0.15
    if parse_json_safe(row.get("brochure_urls_json", "")) not in (None, []):
        score += 0.15
    if parse_json_safe(row.get("unit_types_offered_json", "")) not in (None, []):
        score += 0.15
    if row.get("bedrooms_range_min", "").strip():
        score += 0.10
    if row.get("bua_range_min_sqm", "").strip():
        score += 0.10
    if row.get("starting_price_value", "").strip():
        score += 0.10
    if row.get("price_range_min", "").strip():
        score += 0.10
    if row.get("payment_plan_headline", "").strip():
        score += 0.05
    if row.get("delivery_window", "").strip():
        score += 0.05
    return min(round(score, 2), 1.00)


# ─── VALIDATION GATES ─────────────────────────────────────────────────────────
def validate_kb(rows: list[dict], fieldnames: list[str], canonical_count: int) -> tuple[bool, list[str]]:
    errors = []

    # Row count
    if len(rows) != canonical_count:
        errors.append(f"Row count {len(rows)} ≠ canonical {canonical_count}")

    # Unique project_ids
    pids = [r.get("project_id", "") for r in rows]
    if len(pids) != len(set(pids)):
        errors.append("Duplicate project_ids found")

    # JSON columns valid
    for row in rows:
        pid = row.get("project_id", "?")
        for col in JSON_COLS:
            val = row.get(col, "").strip()
            if not val:
                continue
            try:
                json.loads(val)
            except Exception as ex:
                errors.append(f"{pid}.{col}: invalid JSON: {ex}")

    # Numeric range sanity
    for row in rows:
        pid = row.get("project_id", "?")
        def check_range(mn_col, mx_col):
            mn_s = row.get(mn_col, "").strip()
            mx_s = row.get(mx_col, "").strip()
            if mn_s and mx_s:
                try:
                    mn, mx = float(mn_s), float(mx_s)
                    if mn > mx:
                        errors.append(f"{pid}: {mn_col}={mn} > {mx_col}={mx}")
                except ValueError:
                    errors.append(f"{pid}: non-numeric in {mn_col}/{mx_col}")

        check_range("price_range_min", "price_range_max")
        check_range("bedrooms_range_min", "bedrooms_range_max")
        check_range("bua_range_min_sqm", "bua_range_max_sqm")
        check_range("delivery_year_min", "delivery_year_max")

    return (len(errors) == 0), errors


# ─── COVERAGE REPORT ──────────────────────────────────────────────────────────
def print_coverage_report(rows: list[dict]):
    total = len(rows)
    log.info("\n" + "═" * 60)
    log.info("FINAL COVERAGE REPORT")
    log.info("═" * 60)

    def count_field(col):
        return sum(1 for r in rows if r.get(col, "").strip())

    def count_json_nonempty(col):
        return sum(1 for r in rows if parse_json_safe(r.get(col, "")) not in (None, [], {}))

    log.info(f"  Total rows: {total}")
    log.info(f"  with official_project_url: {count_field('official_project_url')}/{total}")
    log.info(f"  with brochure_urls: {count_json_nonempty('brochure_urls_json')}/{total}")
    log.info(f"  with unit_types: {count_json_nonempty('unit_types_offered_json')}/{total}")
    log.info(f"  with bedrooms range: {count_field('bedrooms_range_min')}/{total}")
    log.info(f"  with BUA range: {count_field('bua_range_min_sqm')}/{total}")
    log.info(f"  with starting_price: {count_field('starting_price_value')}/{total}")
    log.info(f"  with price_range_min/max: {count_field('price_range_min')}/{total}")
    log.info(f"  with payment_plan: {count_field('payment_plan_headline')}/{total}")
    log.info(f"  with delivery_window: {count_field('delivery_window')}/{total}")
    log.info(f"  with unit_templates: {count_json_nonempty('unit_templates_json')}/{total}")
    log.info(f"  with key_amenities: {count_json_nonempty('key_amenities_json')}/{total}")
    log.info(f"  price_status=official: {sum(1 for r in rows if r.get('price_status','').strip()=='official')}/{total}")
    log.info(f"  price_status=on_request: {sum(1 for r in rows if r.get('price_status','').strip()=='on_request')}/{total}")

    # Still incomplete rows
    target_fields = ["bedrooms_range_min", "bua_range_min_sqm", "starting_price_value",
                     "payment_plan_headline", "delivery_window"]
    incomplete = [
        (r["project_id"], [f for f in target_fields if not r.get(f, "").strip()])
        for r in rows
        if any(not r.get(f, "").strip() for f in target_fields)
    ]
    if incomplete:
        log.info(f"\n  Rows still missing buyer-critical fields: {len(incomplete)}")
        for pid, missing in incomplete[:10]:
            log.info(f"    {pid}: missing {', '.join(missing)}")
        if len(incomplete) > 10:
            log.info(f"    ... and {len(incomplete)-10} more")

    # Write coverage JSON
    coverage = {
        "run_date": TODAY,
        "total_rows": total,
        "with_official_url": count_field("official_project_url"),
        "with_brochures": count_json_nonempty("brochure_urls_json"),
        "with_unit_types": count_json_nonempty("unit_types_offered_json"),
        "with_bedrooms": count_field("bedrooms_range_min"),
        "with_bua": count_field("bua_range_min_sqm"),
        "with_starting_price": count_field("starting_price_value"),
        "with_price_range": count_field("price_range_min"),
        "with_payment_plan": count_field("payment_plan_headline"),
        "with_delivery": count_field("delivery_window"),
        "with_unit_templates": count_json_nonempty("unit_templates_json"),
        "with_amenities": count_json_nonempty("key_amenities_json"),
        "price_official": sum(1 for r in rows if r.get("price_status","").strip()=="official"),
        "price_on_request": sum(1 for r in rows if r.get("price_status","").strip()=="on_request"),
        "incomplete_rows": [pid for pid, missing in incomplete],
    }
    with open(INTER / "wdd_final_coverage.json", "w", encoding="utf-8") as f:
        json.dump(coverage, f, indent=2)

    return coverage


# ─── MAIN ─────────────────────────────────────────────────────────────────────
def main():
    log.info("=" * 70)
    log.info("PulseX-WDD — Vision Enrichment Merge")
    log.info(f"Run date: {TODAY}")
    log.info("=" * 70)

    # Load KB
    rows, fieldnames = load_kb()
    canonical_count = len(rows)
    log.info(f"Loaded KB: {canonical_count} rows × {len(fieldnames)} columns")
    backup_kb()

    # Find all AOAI candidate files
    candidate_files = sorted(INTER.glob("*__aoai_candidates.json"))
    log.info(f"Found {len(candidate_files)} AOAI candidate files")

    if not candidate_files:
        log.error("No candidate files found. Run aoai_field_mapper.py first.")
        sys.exit(1)

    # Load all candidates
    all_candidates = {}
    for cf in candidate_files:
        pid = cf.name.replace("__aoai_candidates.json", "")
        with open(cf, encoding="utf-8") as f:
            all_candidates[pid] = json.load(f)

    # Build project_id → row index map
    pid_to_idx = {r["project_id"]: i for i, r in enumerate(rows)}

    all_audit    = load_audit()
    all_merge    = []
    total_updates = 0

    # Apply each candidate to its KB row
    for pid, candidates in sorted(all_candidates.items()):
        if candidates.get("_status") not in ("extracted", None):
            log.info(f"  ⊘ {pid}: status={candidates.get('_status')} — skip")
            continue

        idx = pid_to_idx.get(pid)
        if idx is None:
            log.warning(f"  ⚠ {pid}: not found in KB — skip (row-lock must be preserved)")
            continue

        log.info(f"\n── {pid}")
        row = dict(rows[idx])
        updated_row, audit_rows, merge_rows = apply_candidates_to_row(row, candidates, pid)

        rows[idx] = updated_row
        all_audit.extend(audit_rows)
        all_merge.extend(merge_rows)

        n_updated = sum(1 for mr in merge_rows if mr.get("updated_flag") == "true")
        total_updates += n_updated
        if n_updated:
            log.info(f"  Updated {n_updated} fields")

    log.info(f"\nTotal field updates: {total_updates}")

    # Validate
    log.info("\n" + "─" * 60)
    log.info("VALIDATION")
    valid, errors = validate_kb(rows, fieldnames, canonical_count)
    if valid:
        log.info("  ✓ All validation gates passed")
    else:
        log.error(f"  ✗ Validation errors ({len(errors)}):")
        for e in errors:
            log.error(f"    {e}")
        # Don't abort — log and continue but note errors
        log.warning("  Continuing despite errors (check errors before using KB)")

    # Save outputs
    save_kb(rows, fieldnames)

    # Save audit
    save_audit(all_audit)
    log.info(f"Audit: {AUDIT_PATH} ({len(all_audit)} rows total)")

    # Save merge report
    with open(MERGE_REPORT, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=MERGE_HEADER, extrasaction="ignore")
        w.writeheader()
        w.writerows(all_merge)
    log.info(f"Merge report: {MERGE_REPORT} ({len(all_merge)} rows)")

    # Coverage report
    coverage = print_coverage_report(rows)

    # Update completion check
    completion = {
        "structurally_valid": valid,
        "validation_errors": errors,
        "total_rows": canonical_count,
        "unique_project_ids": len(set(r["project_id"] for r in rows)),
        "coverage": {k: v for k, v in coverage.items() if k.startswith("with_") or k.startswith("price_")},
        "total_field_updates_this_run": total_updates,
        "is_complete": valid and coverage["with_bedrooms"] > 0 and coverage["with_bua"] > 0,
        "run_date": TODAY,
    }
    with open(INTER / "wdd_completion_check.json", "w", encoding="utf-8") as f:
        json.dump(completion, f, indent=2)

    log.info("\n" + "=" * 70)
    log.info("MERGE COMPLETE")
    log.info(f"KB written: {KB_ENGINE_PATH}")
    log.info(f"KB backup:  engine-KB/backups/")
    log.info("=" * 70)


if __name__ == "__main__":
    main()
