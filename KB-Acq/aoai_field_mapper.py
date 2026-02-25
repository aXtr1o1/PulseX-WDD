#!/usr/bin/env python3
"""
aoai_field_mapper.py
PulseX-WDD — Azure OpenAI Structured Field Extractor

Reads per-project vision text files (from vision_pdf_extractor.py output),
then uses GPT-4o to extract structured buyer KB fields with evidence citations.

Input:  KB-Acq/outputs/intermediate/<project_id>__vision_text.txt
Output: KB-Acq/outputs/intermediate/<project_id>__aoai_candidates.json
        KB-Acq/outputs/intermediate/wdd_aoai_extraction_summary.json

Zero hallucination: AOAI maps ONLY from provided text snippets.
All candidates include evidence_snippet pointing back to source text.

Usage:
  /tmp/pulsex_venv/bin/python3 KB-Acq/aoai_field_mapper.py
"""

import os, sys, json, csv, logging, time
from pathlib import Path
from datetime import datetime, timezone
import urllib.request, urllib.error

REPO_ROOT = Path("/Volumes/ReserveDisk/codeBase/PulseX-WDD")
KB_ACQ    = REPO_ROOT / "KB-Acq"
OUTPUTS   = KB_ACQ / "outputs"
INTER     = OUTPUTS / "intermediate"
LOGS      = KB_ACQ / "logs"
ENGINE_KB = REPO_ROOT / "engine-KB"

LOGS.mkdir(parents=True, exist_ok=True)
INTER.mkdir(parents=True, exist_ok=True)

LOG_PATH = LOGS / "wdd_aoai_mapping.log"
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%SZ",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(LOG_PATH, encoding="utf-8"),
    ],
)
log = logging.getLogger("aoai_mapper")
TODAY = datetime.now(timezone.utc).strftime("%Y-%m-%d")

# ─── ENV ──────────────────────────────────────────────────────────────────────
def load_env(path: Path):
    if not path.exists():
        return
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            os.environ.setdefault(k.strip(), v.strip())

load_env(REPO_ROOT / ".env")

AOAI_ENDPOINT   = os.environ.get("AZURE_OPENAI_ENDPOINT", "").rstrip("/")
AOAI_KEY        = os.environ.get("AZURE_OPENAI_API_KEY", "")
AOAI_VERSION    = os.environ.get("AZURE_OPENAI_API_VERSION", "2025-01-01-preview")
AOAI_DEPLOYMENT = os.environ.get("AZURE_OPENAI_CHAT_DEPLOYMENT", "gpt-4o")

if not AOAI_ENDPOINT or not AOAI_KEY:
    log.error("Azure OpenAI credentials missing — aborting")
    sys.exit(1)

log.info("Azure OpenAI credentials loaded (masked for security)")

# ─── EXTRACTION SCHEMA PROMPT ─────────────────────────────────────────────────
SYSTEM_PROMPT = """You are a structured data extraction agent for a real estate knowledge base.
You will receive text extracted from official WDD (Wadi Degla Developments) brochures.
Your job is to extract specific buyer-critical fields ONLY from the provided text.

CRITICAL RULES:
1. NEVER invent, estimate, or assume values not explicitly in the provided text
2. For any field not found in the text, use null
3. For every extracted value, provide an evidence_snippet (exact quoted text from input)
4. Normalize prices: remove commas, no currency symbols, no "M" shorthand (expand to full number)
5. Normalize areas to numbers only (no "sqm" suffix in value, just the number)
6. If you see conflicting values for the same field, pick the most specific/explicit one
7. price_status must be ONLY: "official" (if explicit EGP price found) OR "on_request" (if inquiry CTA) OR "unknown"
8. Return ONLY valid JSON, no commentary, no markdown blocks"""

def make_extraction_prompt(project_id: str, project_name: str, text: str) -> str:
    # Truncate text to fit context window leaving room for response
    # GPT-4o has 128K context; we use up to 80K chars of text
    max_text = 80000
    if len(text) > max_text:
        text = text[:max_text] + "\n\n[TEXT TRUNCATED — FIRST 80,000 CHARS SHOWN]"

    return f"""PROJECT: {project_id} / {project_name}

BROCHURE TEXT (extracted via OCR/Vision from official WDD brochure):
---
{text}
---

Extract the following fields from the text above. Return a JSON object with these EXACT keys:

{{
  "bedrooms_range_min": <integer or null>,
  "bedrooms_range_max": <integer or null>,
  "bua_range_min_sqm": <integer or null>,
  "bua_range_max_sqm": <integer or null>,
  "land_area_min_sqm": <integer or null>,
  "land_area_max_sqm": <integer or null>,
  "starting_price_value": <numeric string like "4500000" or null>,
  "price_range_min": <numeric string or null>,
  "price_range_max": <numeric string or null>,
  "price_status": "official" | "on_request" | "unknown",
  "pricing_disclaimer": <string or null>,
  "payment_plan_headline": <string summary of plan, e.g. "10% downpayment, 8 years installments" or null>,
  "downpayment_percent_min": <integer or null>,
  "downpayment_percent_max": <integer or null>,
  "installment_years_min": <integer or null>,
  "installment_years_max": <integer or null>,
  "delivery_window": <string like "Q4 2026" or "2026-2027" or null>,
  "delivery_year_min": <integer or null>,
  "delivery_year_max": <integer or null>,
  "finishing_levels_offered_json": <list of strings from: ["fully_finished", "semi_finished", "core_shell"] or []>,
  "unit_types_offered_json": <list of unit type strings actually mentioned in text, or []>,
  "key_amenities_json": <list of amenity strings from text, or []>,
  "unit_templates_json": <list of unit template objects (see below), or []>,
  "listings_json": <list of specific unit listing objects (see below), or []>,
  "contact_phone": <phone number string or null>,
  "contact_email": <email string or null>,
  "sales_office_locations": <list of sales office location strings or []>,
  "_evidence": {{
    "bedrooms": <exact quote from text or null>,
    "bua": <exact quote from text or null>,
    "price": <exact quote from text or null>,
    "payment": <exact quote from text or null>,
    "delivery": <exact quote from text or null>,
    "finishing": <exact quote from text or null>,
    "unit_types": <exact quote from text or null>
  }}
}}

Unit template object format (use for each distinct unit spec row found in a table):
{{
  "unit_type": "apartment",
  "bedrooms": 2,
  "bua_min": 100,
  "bua_max": 120,
  "price_min": null,
  "price_max": null,
  "finishing": null,
  "delivery": null,
  "evidence_snippet": "exact text snippet"
}}

Listing object format (for individual priced units/offers found in text):
{{
  "unit_type": "apartment",
  "bedrooms": 2,
  "bua": 110,
  "price": "4500000",
  "payment_plan": null,
  "evidence_snippet": "exact text snippet"
}}

IMPORTANT NOTES:
- For bedrooms: look for "2BR", "3 bedrooms", "2-bed", etc.
- For BUA: look for sqm, m2, m², square meters
- For price: look for EGP, LE, prices in millions (expand: "4.5M" → "4500000")
- For payment: look for downpayment %, installment years, monthly payment info
- For delivery: look for "delivery", "handover", "Q1/Q2/Q3/Q4 20XX", year mentions
- For finishing: look for "fully finished", "semi finished", "core & shell"
- phone numbers like 19917 are WDD's hotline — include in contact_phone
- If WDD only says "contact us for pricing" or shows a form — set price_status to "on_request"
- If no pricing info at all — set price_status to "unknown"

Return ONLY the JSON object, no other text."""


# ─── AOAI CALL ────────────────────────────────────────────────────────────────
def call_aoai(prompt: str, system: str = SYSTEM_PROMPT, max_tokens: int = 4000) -> dict | None:
    """Call Azure OpenAI GPT-4o with JSON extraction prompt."""
    url = (
        f"{AOAI_ENDPOINT}/openai/deployments/{AOAI_DEPLOYMENT}/chat/completions"
        f"?api-version={AOAI_VERSION}"
    )

    payload = json.dumps({
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
        "max_tokens": max_tokens,
        "temperature": 0,
        "response_format": {"type": "json_object"},
    }).encode("utf-8")

    for attempt in range(3):
        try:
            req = urllib.request.Request(
                url, data=payload, method="POST",
                headers={
                    "api-key": AOAI_KEY,
                    "Content-Type": "application/json",
                }
            )
            resp = urllib.request.urlopen(req, timeout=120)
            result = json.loads(resp.read())
            content = result["choices"][0]["message"]["content"].strip()
            # Parse the JSON response
            return json.loads(content)
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="replace")
            if e.code == 429:
                wait = 30 * (attempt + 1)
                log.warning(f"  Rate limited — waiting {wait}s... (attempt {attempt+1})")
                time.sleep(wait)
                continue
            log.error(f"  AOAI HTTP {e.code}: {body[:200]}")
            return None
        except json.JSONDecodeError as ex:
            log.error(f"  JSON decode error: {ex}")
            return None
        except Exception as ex:
            log.error(f"  AOAI error: {ex}")
            if attempt < 2:
                time.sleep(5)

    return None


# ─── LOAD KB FOR PROJECT NAME LOOKUP ─────────────────────────────────────────
def load_kb_project_names() -> dict[str, str]:
    """Return dict of project_id -> project_name."""
    kb_path = ENGINE_KB / "PulseX-WDD_buyerKB.csv"
    if not kb_path.exists():
        return {}
    with open(kb_path, newline="", encoding="utf-8") as f:
        return {r["project_id"]: r["project_name"] for r in csv.DictReader(f)}


# ─── MAIN ─────────────────────────────────────────────────────────────────────
def main():
    log.info("=" * 70)
    log.info("PulseX-WDD — Azure OpenAI Structured Field Mapper")
    log.info(f"Run date: {TODAY}")
    log.info("=" * 70)

    project_names = load_kb_project_names()

    # Find all vision text files
    text_files = sorted(INTER.glob("*__vision_text.txt"))
    if not text_files:
        # Also check if session manifest exists
        session = INTER / "wdd_vision_session.json"
        if session.exists():
            log.info("Vision session found but no text files in intermediate/ — checking pdf_text/")
            # Find all combined text files
            pdf_text_dir = KB_ACQ / "raw" / "pdf_text"
            if pdf_text_dir.exists():
                for pid_dir in sorted(pdf_text_dir.iterdir()):
                    if pid_dir.is_dir():
                        combined = INTER / f"{pid_dir.name}__vision_text.txt"
                        if not combined.exists():
                            # Aggregate all txt files for this project
                            parts = []
                            for txt in sorted(pid_dir.glob("*.txt")):
                                parts.append(txt.read_text(encoding="utf-8"))
                            if parts:
                                combined.write_text("\n\n".join(parts), encoding="utf-8")
                                log.info(f"  Created combined text for {pid_dir.name}")

        text_files = sorted(INTER.glob("*__vision_text.txt"))

    if not text_files:
        log.error("No vision text files found. Run vision_pdf_extractor.py first.")
        sys.exit(1)

    log.info(f"Found {len(text_files)} vision text files to process")

    all_candidates = {}
    failed = []

    for txt_path in text_files:
        # Parse project_id from filename
        project_id = txt_path.name.replace("__vision_text.txt", "")
        project_name = project_names.get(project_id, project_id)
        candidates_path = INTER / f"{project_id}__aoai_candidates.json"

        # Check if already done
        if candidates_path.exists():
            log.info(f"  [CACHE] {project_id} — candidates already extracted")
            with open(candidates_path, encoding="utf-8") as f:
                all_candidates[project_id] = json.load(f)
            continue

        log.info(f"\n── {project_id} / {project_name}")

        # Read vision text
        text = txt_path.read_text(encoding="utf-8")
        text_len = len(text)
        log.info(f"  Text length: {text_len:,} chars")

        if text_len < 100:
            log.warning(f"  Text too short ({text_len} chars) — skipping")
            candidates = {"_status": "insufficient_text", "text_length": text_len}
            all_candidates[project_id] = candidates
            with open(candidates_path, "w", encoding="utf-8") as f:
                json.dump(candidates, f, indent=2)
            continue

        # Build prompt and call AOAI
        prompt = make_extraction_prompt(project_id, project_name, text)
        log.info(f"  Calling GPT-4o for field extraction...")

        candidates = call_aoai(prompt)

        if candidates is None:
            log.error(f"  AOAI extraction failed for {project_id}")
            failed.append(project_id)
            candidates = {"_status": "aoai_failed"}
        else:
            # Add metadata
            candidates["_status"] = "extracted"
            candidates["_project_id"] = project_id
            candidates["_project_name"] = project_name
            candidates["_extracted_date"] = TODAY
            candidates["_text_length"] = text_len

            log.info(f"  ✓ Extraction complete")
            log.info(f"    bedrooms: {candidates.get('bedrooms_range_min')}–{candidates.get('bedrooms_range_max')}")
            log.info(f"    BUA: {candidates.get('bua_range_min_sqm')}–{candidates.get('bua_range_max_sqm')} sqm")
            log.info(f"    starting_price: {candidates.get('starting_price_value')}")
            log.info(f"    price_status: {candidates.get('price_status')}")
            log.info(f"    payment: {candidates.get('payment_plan_headline')}")
            log.info(f"    delivery: {candidates.get('delivery_window')}")
            log.info(f"    unit_types: {candidates.get('unit_types_offered_json')}")
            log.info(f"    amenities: {len(candidates.get('key_amenities_json') or [])} items")
            log.info(f"    unit_templates: {len(candidates.get('unit_templates_json') or [])} rows")

        all_candidates[project_id] = candidates
        with open(candidates_path, "w", encoding="utf-8") as f:
            json.dump(candidates, f, indent=2, ensure_ascii=False)

        log.info(f"  Saved → {candidates_path.name}")

        # Rate limit courtesy delay
        time.sleep(2)

    # Write summary
    summary = {
        "run_date": TODAY,
        "total_projects": len(all_candidates),
        "successful": len([v for v in all_candidates.values() if v.get("_status") == "extracted"]),
        "failed": failed,
        "per_project_summary": {}
    }

    for pid, cands in all_candidates.items():
        if cands.get("_status") != "extracted":
            continue
        summary["per_project_summary"][pid] = {
            "bedrooms_range": f"{cands.get('bedrooms_range_min')}–{cands.get('bedrooms_range_max')}",
            "bua_range": f"{cands.get('bua_range_min_sqm')}–{cands.get('bua_range_max_sqm')}",
            "starting_price": cands.get("starting_price_value"),
            "price_status": cands.get("price_status"),
            "payment_plan": cands.get("payment_plan_headline"),
            "delivery": cands.get("delivery_window"),
            "unit_types_count": len(cands.get("unit_types_offered_json") or []),
            "amenities_count": len(cands.get("key_amenities_json") or []),
            "unit_templates_count": len(cands.get("unit_templates_json") or []),
        }

    summary_path = INTER / "wdd_aoai_extraction_summary.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    log.info("\n" + "=" * 70)
    log.info("AOAI MAPPING SUMMARY")
    log.info("=" * 70)
    log.info(f"Projects processed: {summary['total_projects']}")
    log.info(f"Successful extractions: {summary['successful']}")
    if failed:
        log.warning(f"Failed projects: {failed}")
    log.info(f"Summary saved: {summary_path}")
    log.info("Next: run merge_vision_enrichment.py")


if __name__ == "__main__":
    main()
