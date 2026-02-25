#!/usr/bin/env python3
"""
enrich_from_brochures.py
PulseX-WDD — Brochure-First KB Enrichment Pipeline (Azure Document Intelligence)

Passes:
  A) Gap analysis — identify missing fields per entity
  B) DocIntel extraction — submit brochures to Azure DI, cache responses
  C) Field normalization + parsing — extract structured fields from DI output
  D) Merge into KB — update only evidence-backed fields, log everything
  E) Validation — structural + data hygiene
  F) Final write — both KB paths

Uses:
  - /Volumes/ReserveDisk/codeBase/PulseX-WDD/.env  for Azure credentials
  - KB-Acq/projectBrochures/<project_id>/*.pdf      for brochures
  - KB-Acq/outputs/wdd_brochures_manifest.csv       for brochure registry
  - engine-KB/PulseX-WDD_buyerKB.csv               for current KB

Outputs:
  - engine-KB/PulseX-WDD_buyerKB.csv               (enriched)
  - KB-Acq/outputs/PulseX-WDD_buyerKB.csv          (archive copy)
  - KB-Acq/raw/docintel/<project_id>/<hash>.json   (DocIntel cache)
  - KB-Acq/outputs/intermediate/wdd_gap_report.csv
  - KB-Acq/outputs/intermediate/wdd_gap_summary.json
  - KB-Acq/outputs/intermediate/wdd_merge_report.csv
  - KB-Acq/outputs/wdd_sources_audit.csv           (appended)
  - KB-Acq/logs/wdd_enrich_run.log

Zero hallucination — all updated fields must have evidence rows.
"""

import os, sys, csv, json, re, time, hashlib, shutil, logging, traceback
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional

# ──────────────────────────────────────────────────────────────────────────────
# 0) BOOTSTRAP — load .env, set up paths + logging
# ──────────────────────────────────────────────────────────────────────────────

REPO_ROOT   = Path("/Volumes/ReserveDisk/codeBase/PulseX-WDD")
KB_ACQ      = REPO_ROOT / "KB-Acq"
ENGINE_KB   = REPO_ROOT / "engine-KB"
OUTPUTS     = KB_ACQ / "outputs"
INTER       = OUTPUTS / "intermediate"
DOCINTEL_C  = KB_ACQ / "raw" / "docintel"
BROCHURES   = KB_ACQ / "projectBrochures"
LOGS        = KB_ACQ / "logs"

for d in [OUTPUTS, INTER, DOCINTEL_C, LOGS,
          KB_ACQ/"raw"/"pdf_ocr_pages", KB_ACQ/"raw"/"html",
          KB_ACQ/"raw"/"net", KB_ACQ/"raw"/"screens"]:
    d.mkdir(parents=True, exist_ok=True)

LOG_PATH = LOGS / "wdd_enrich_run.log"
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%SZ",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(LOG_PATH, encoding="utf-8"),
    ],
)
log = logging.getLogger("enrich")

TODAY = datetime.now(timezone.utc).strftime("%Y-%m-%d")

# ── load .env (never print values)
def load_env(path: Path):
    """Load key=value pairs from .env file into os.environ."""
    if not path.exists():
        log.warning(f".env not found at {path}")
        return
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                k, _, v = line.partition("=")
                os.environ.setdefault(k.strip(), v.strip())

load_env(REPO_ROOT / ".env")

DOCINTEL_ENDPOINT = os.environ.get("AZURE_DOCINTEL_ENDPOINT", "")
DOCINTEL_KEY      = os.environ.get("AZURE_DOCINTEL_KEY", "")
DOCINTEL_VERSION  = os.environ.get("AZURE_DOCINTEL_API_VERSION", "2024-11-30")

if not DOCINTEL_ENDPOINT or not DOCINTEL_KEY:
    log.error("Azure DocIntel credentials not found in .env — aborting.")
    sys.exit(1)
else:
    log.info("Azure DocIntel credentials loaded (endpoint masked for security).")

# ──────────────────────────────────────────────────────────────────────────────
# 1) CSV HELPERS
# ──────────────────────────────────────────────────────────────────────────────

KB_PATH_ENGINE = ENGINE_KB / "PulseX-WDD_buyerKB.csv"
KB_PATH_ACQ    = OUTPUTS   / "PulseX-WDD_buyerKB.csv"
AUDIT_PATH     = OUTPUTS   / "wdd_sources_audit.csv"
SCREENS_PATH   = OUTPUTS   / "wdd_screens_index.csv"

AUDIT_HEADER = [
    "project_id","field_name","field_value","source_url","evidence_type",
    "evidence_snippet","asset_path_or_pdf_page","captured_date",
    "parser_confidence","overwrite_flag","notes",
]
MERGE_HEADER = [
    "project_id","field_name","old_value","new_value","source_used",
    "evidence_type","updated_flag","reason",
]

TARGET_FIELDS = [
    "bedrooms_range_min","bedrooms_range_max",
    "bua_range_min_sqm","bua_range_max_sqm",
    "starting_price_value","price_range_min","price_range_max","price_status",
    "pricing_date","pricing_disclaimer",
    "payment_plan_headline","downpayment_percent_min","downpayment_percent_max",
    "installment_years_min","installment_years_max",
    "delivery_window","delivery_year_min","delivery_year_max",
    "unit_templates_json","listings_json","finishing_levels_offered_json",
]

JSON_COLS = [
    "unit_types_offered_json","finishing_levels_offered_json","key_amenities_json",
    "brochure_urls_json","gallery_urls_json","source_links_json",
    "screenshot_paths_json","disclaimers_json","zones_json",
    "unit_templates_json","listings_json",
]

def load_kb() -> tuple[list[dict], list[str]]:
    with open(KB_PATH_ENGINE, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        return rows, reader.fieldnames

def save_kb(rows: list[dict], fieldnames: list[str]):
    """Write to both engine-KB and outputs archive."""
    for path in [KB_PATH_ENGINE, KB_PATH_ACQ]:
        with open(path, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=fieldnames)
            w.writeheader()
            w.writerows(rows)
    log.info(f"KB written to engine-KB + outputs ({len(rows)} rows)")

def load_audit_rows() -> list[dict]:
    if not AUDIT_PATH.exists():
        return []
    with open(AUDIT_PATH, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))

def append_audit(new_rows: list[dict]):
    existing = load_audit_rows()
    existing.extend(new_rows)
    with open(AUDIT_PATH, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=AUDIT_HEADER, extrasaction="ignore")
        w.writeheader()
        w.writerows(existing)

def backup_engine_kb():
    ts = datetime.now().strftime("%Y-%m-%d_%H%M")
    bk = ENGINE_KB / "backups" / f"PulseX-WDD_buyerKB_{ts}.csv"
    bk.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(KB_PATH_ENGINE, bk)
    log.info(f"Backup saved: {bk}")

# ──────────────────────────────────────────────────────────────────────────────
# 2) PASS A — GAP ANALYSIS
# ──────────────────────────────────────────────────────────────────────────────

def pass_a_gap_analysis(rows: list[dict], fieldnames: list[str]):
    log.info("═" * 60)
    log.info("PASS A — Gap Analysis")
    log.info("═" * 60)

    gap_rows = []
    for row in rows:
        pid = row["project_id"]
        missing = [f for f in TARGET_FIELDS if not row.get(f, "").strip()]
        present = [f for f in TARGET_FIELDS if row.get(f, "").strip()]
        severity = (
            "A" if len(missing) >= 12 else
            "B" if len(missing) >= 6 else
            "C"
        )
        gap_rows.append({
            "project_id": pid,
            "project_name": row["project_name"],
            "missing_count": len(missing),
            "present_count": len(present),
            "severity_tier": severity,
            "missing_fields": "|".join(missing),
            "brochure_available": "yes" if (BROCHURES / pid).exists() and any((BROCHURES/pid).glob("*.pdf")) else "no",
        })
        log.info(f"  [{severity}] {pid}: {len(missing)}/{len(TARGET_FIELDS)} missing")

    gap_report_path = INTER / "wdd_gap_report.csv"
    with open(gap_report_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(gap_rows[0].keys()))
        w.writeheader()
        w.writerows(gap_rows)

    summary = {
        "run_date": TODAY,
        "total_entities": len(rows),
        "tier_A": sum(1 for r in gap_rows if r["severity_tier"] == "A"),
        "tier_B": sum(1 for r in gap_rows if r["severity_tier"] == "B"),
        "tier_C": sum(1 for r in gap_rows if r["severity_tier"] == "C"),
        "entities_with_brochures": sum(1 for r in gap_rows if r["brochure_available"] == "yes"),
        "per_field_fill_rate": {
            f: sum(1 for row in rows if row.get(f,"").strip())
            for f in TARGET_FIELDS
        },
    }
    gap_summary_path = INTER / "wdd_gap_summary.json"
    with open(gap_summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    log.info(f"Gap report: {gap_report_path}")
    log.info(f"Gap summary: {gap_summary_path}")
    log.info(f"Tier A (most gaps): {summary['tier_A']}  B: {summary['tier_B']}  C: {summary['tier_C']}")
    return gap_rows

# ──────────────────────────────────────────────────────────────────────────────
# 3) PASS B/C — Azure Document Intelligence Extraction
# ──────────────────────────────────────────────────────────────────────────────

def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()

DOCINTEL_MAX_BYTES = 1_900_000  # 1.9MB safe limit — high-DPI image pages are 1–3MB each


def _split_pdf_to_page_chunks(pdf_path: Path, max_bytes: int) -> list[bytes]:
    """Split a PDF into chunks small enough for DocIntel using pypdf."""
    import io
    from pypdf import PdfReader, PdfWriter

    reader = PdfReader(str(pdf_path))
    total_pages = len(reader.pages)
    log.info(f"  Splitting {total_pages}-page PDF into chunks (max {max_bytes//1024}KB each)")

    chunks = []
    current_pages = []
    current_writer = PdfWriter()

    for i, page in enumerate(reader.pages):
        current_writer.add_page(page)
        current_pages.append(i)

        # Test current size
        buf = io.BytesIO()
        current_writer.write(buf)
        size = buf.tell()

        if size >= max_bytes or i == total_pages - 1:
            buf.seek(0)
            chunk_bytes = buf.read()
            chunks.append(chunk_bytes)
            log.info(f"  Chunk {len(chunks)}: pages {current_pages[0]+1}–{current_pages[-1]+1} ({len(chunk_bytes)//1024}KB)")
            # Reset for next chunk
            current_pages = []
            current_writer = PdfWriter()

    return chunks


def _docintel_submit_bytes(pdf_bytes: bytes, label: str) -> Optional[dict]:
    """Submit raw PDF bytes to Azure DocIntel. Returns polled result or None."""
    import urllib.request, urllib.error

    endpoint = DOCINTEL_ENDPOINT.rstrip("/")
    submit_url = (
        f"{endpoint}/documentintelligence/documentModels/prebuilt-layout:analyze"
        f"?api-version={DOCINTEL_VERSION}&outputContentFormat=markdown"
    )

    req = urllib.request.Request(
        submit_url,
        data=pdf_bytes,
        method="POST",
        headers={
            "Ocp-Apim-Subscription-Key": DOCINTEL_KEY,
            "Content-Type": "application/octet-stream",
        },
    )
    try:
        resp = urllib.request.urlopen(req, timeout=120)
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")[:400]
        log.error(f"  DocIntel submit error {e.code} for {label}: {body}")
        return None

    op_location = resp.headers.get("Operation-Location", "")
    if not op_location:
        log.error("  No Operation-Location header returned")
        return None

    for attempt in range(60):
        time.sleep(3)
        poll_req = urllib.request.Request(
            op_location,
            headers={"Ocp-Apim-Subscription-Key": DOCINTEL_KEY},
        )
        try:
            poll_resp = urllib.request.urlopen(poll_req, timeout=60)
            result = json.loads(poll_resp.read())
        except Exception as ex:
            log.warning(f"  Poll attempt {attempt+1} failed: {ex}")
            continue

        status = result.get("status", "")
        if status == "succeeded":
            return result
        elif status in ("failed", "canceled"):
            log.error(f"  DocIntel failed: {result.get('error', {})}")
            return None
        elif attempt % 5 == 0:
            log.info(f"  ... polling {label} ({attempt*3}s, status={status})")

    log.error(f"  DocIntel timed out after 180s for {label}")
    return None


def _build_url_map() -> dict[str, str]:
    """Build map: file_path -> source_url from brochure manifest."""
    url_map = {}
    manifest_path = OUTPUTS / "wdd_brochures_manifest.csv"
    if manifest_path.exists():
        with open(manifest_path) as f:
            for row in csv.DictReader(f):
                fp = row.get("file_path", "").strip()
                su = row.get("source_url", "").strip()
                if fp and su:
                    url_map[fp] = su
    return url_map


_BROCHURE_URL_MAP: dict[str, str] = {}  # populated on first use


def docintel_analyze(pdf_path: Path, project_id: str) -> Optional[dict]:
    """Submit PDF to Azure DocIntel. Uses URL-source for large PDFs via WDD CDN. Caches results."""
    import urllib.request, urllib.error

    global _BROCHURE_URL_MAP
    if not _BROCHURE_URL_MAP:
        _BROCHURE_URL_MAP = _build_url_map()

    pdf_hash = sha256_file(pdf_path)[:12]
    cache_dir = DOCINTEL_C / project_id
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_path = cache_dir / f"{pdf_hash}.json"

    if cache_path.exists():
        log.info(f"  [CACHE HIT] DocIntel cache: {cache_path.name}")
        with open(cache_path, encoding="utf-8") as f:
            return json.load(f)

    pdf_bytes = pdf_path.read_bytes()
    pdf_size = len(pdf_bytes)
    log.info(f"  PDF size: {pdf_size//1024}KB — limit: {DOCINTEL_MAX_BYTES//1024}KB")

    endpoint = DOCINTEL_ENDPOINT.rstrip("/")
    submit_url = (
        f"{endpoint}/documentintelligence/documentModels/prebuilt-layout:analyze"
        f"?api-version={DOCINTEL_VERSION}&outputContentFormat=markdown"
    )

    if pdf_size > DOCINTEL_MAX_BYTES:
        # Try URL-based submission first (no file-size limit)
        cdn_url = _BROCHURE_URL_MAP.get(str(pdf_path), "")
        if cdn_url and cdn_url.startswith("https://wadidegladevelopments.com"):
            log.info(f"  Large PDF — submitting via CDN URL: {cdn_url}")
            body_json = json.dumps({"urlSource": cdn_url}).encode("utf-8")
            req = urllib.request.Request(
                submit_url,
                data=body_json,
                method="POST",
                headers={
                    "Ocp-Apim-Subscription-Key": DOCINTEL_KEY,
                    "Content-Type": "application/json",
                },
            )
            try:
                resp = urllib.request.urlopen(req, timeout=120)
                op_location = resp.headers.get("Operation-Location", "")
                if op_location:
                    result = _poll_docintel(op_location, f"{pdf_path.name} (URL)")
                    if result:
                        with open(cache_path, "w", encoding="utf-8") as fc:
                            json.dump(result, fc, ensure_ascii=False)
                        log.info(f"  DocIntel URL-mode succeeded — cached to {cache_path.name}")
                        return result
            except urllib.error.HTTPError as e:
                body = e.read().decode("utf-8", errors="replace")[:400]
                log.warning(f"  URL-mode failed ({e.code}): {body} — falling back to page chunks")
            except Exception as ex:
                log.warning(f"  URL-mode error: {ex} — falling back to page chunks")

        # Fallback: page-by-page chunk submission
        log.info(f"  PDF too large ({pdf_size//1024}KB) — splitting into 1.9MB page chunks...")
        try:
            chunks = _split_pdf_to_page_chunks(pdf_path, DOCINTEL_MAX_BYTES)
        except Exception as ex:
            log.error(f"  Failed to split PDF: {ex}")
            return None

        if not chunks:
            log.error("  No chunks produced from split")
            return None

        all_texts = []
        for idx, chunk_bytes in enumerate(chunks):
            label = f"{pdf_path.name} chunk {idx+1}/{len(chunks)}"
            log.info(f"  Submitting {label} ({len(chunk_bytes)//1024}KB)...")
            chunk_result = _docintel_submit_bytes(chunk_bytes, label)
            if chunk_result:
                chunk_text = chunk_result.get("analyzeResult", {}).get("content", "")
                if chunk_text:
                    all_texts.append(chunk_text)
                    log.info(f"  Chunk {idx+1}: {len(chunk_text)} chars extracted")
            else:
                log.warning(f"  Chunk {idx+1} failed — continuing")

        if not all_texts:
            log.error(f"  All chunks failed for {pdf_path.name}")
            return None

        merged_text = "\n\n".join(all_texts)
        merged_result = {
            "status": "succeeded",
            "_chunked": True,
            "_chunk_count": len(chunks),
            "analyzeResult": {"content": merged_text, "pages": []},
        }
        with open(cache_path, "w", encoding="utf-8") as fc:
            json.dump(merged_result, fc, ensure_ascii=False)
        log.info(f"  DocIntel chunked succeeded — {len(merged_text)} chars total, cached to {cache_path.name}")
        return merged_result

    else:
        # Small enough — submit directly as bytes
        log.info(f"  Submitting {pdf_path.name} directly to DocIntel...")
        result = _docintel_submit_bytes(pdf_bytes, pdf_path.name)
        if result:
            with open(cache_path, "w", encoding="utf-8") as fc:
                json.dump(result, fc, ensure_ascii=False)
            log.info(f"  DocIntel succeeded — cached to {cache_path.name}")
        return result


def _poll_docintel(op_location: str, label: str) -> Optional[dict]:
    """Poll an operation URL until succeeded/failed."""
    import urllib.request
    for attempt in range(90):
        time.sleep(3)
        poll_req = urllib.request.Request(
            op_location,
            headers={"Ocp-Apim-Subscription-Key": DOCINTEL_KEY},
        )
        try:
            poll_resp = urllib.request.urlopen(poll_req, timeout=60)
            result = json.loads(poll_resp.read())
        except Exception as ex:
            log.warning(f"  Poll attempt {attempt+1} failed: {ex}")
            continue
        status = result.get("status", "")
        if status == "succeeded":
            return result
        elif status in ("failed", "canceled"):
            log.error(f"  DocIntel failed for {label}: {result.get('error', {})}")
            return None
        elif attempt % 5 == 0:
            log.info(f"  ... polling {label} ({attempt*3}s, status={status})")
    log.error(f"  DocIntel timed out after 270s for {label}")
    return None



def extract_markdown_text(di_result: dict) -> str:
    """Extract the markdown content from DocIntel result."""
    try:
        return di_result.get("analyzeResult", {}).get("content", "")
    except Exception:
        return ""

def extract_all_page_texts(di_result: dict) -> list[str]:
    """Return list of per-page text strings."""
    pages = di_result.get("analyzeResult", {}).get("pages", [])
    page_texts = []
    for p in pages:
        lines = []
        for line in p.get("lines", []):
            lines.append(line.get("content", ""))
        page_texts.append("\n".join(lines))
    return page_texts

# ──────────────────────────────────────────────────────────────────────────────
# 4) FIELD EXTRACTION — parse DocIntel markdown/text for buyer-critical values
# ──────────────────────────────────────────────────────────────────────────────

# Regex patterns for extraction
RE_BEDROOM = re.compile(
    r'(\d+)\s*(?:bed(?:room)?s?|BR|Bed)',
    re.IGNORECASE
)
RE_BUA = re.compile(
    r'(\d[\d,\.]*)\s*(?:sqm|m²|m2|sq\.?\s*m)',
    re.IGNORECASE
)
RE_PRICE_EGP = re.compile(
    r'(?:EGP|LE|جنيه)?\s*([\d,\.]+)\s*(?:EGP|LE|M|million|مليون)?',
    re.IGNORECASE
)
RE_STARTING_PRICE = re.compile(
    r'(?:starting\s+(?:from|at|price)|starts?\s+(?:from|at)|price\s+starts?\s+(?:from|at))\s*:?\s*'
    r'(?:EGP|LE)?\s*([\d,\.]+\s*(?:M|million|مليون)?)',
    re.IGNORECASE
)
RE_DOWNPAYMENT = re.compile(
    r'(?:down\s*pay(?:ment)?|deposit|مقدم)\s*:?\s*([\d\.]+)\s*%',
    re.IGNORECASE
)
RE_INSTALLMENT_YEARS = re.compile(
    r'(?:over|installment|payment plan|spread over|يساوي|على)\s*:?\s*(\d+)\s*(?:years?|سنة|سنوات)',
    re.IGNORECASE
)
RE_DELIVERY = re.compile(
    r'(?:delivery|handover|تسليم)\s*:?\s*(?:Q\d\s*)?(\d{4})',
    re.IGNORECASE
)
RE_FINISHING = re.compile(
    r'(fully?\s*finished|semi[\s-]?finished|core\s*(?:and|&)\s*shell|لتشطيب التام|لتشطيب نصف)',
    re.IGNORECASE
)
RE_UNIT_TYPE = re.compile(
    r'\b(apartment|duplex|townhouse|twin[\s-]?house|villa|penthouse|chalet|studio|loft|office|clinic|retail)\b',
    re.IGNORECASE
)


def normalize_price(raw: str) -> Optional[str]:
    """Convert price string to numeric. Returns None if ambiguous."""
    raw = raw.strip().replace(",", "")
    # Handle "1.5M" style
    m = re.match(r'^([\d\.]+)\s*[Mm](?:illion)?$', raw)
    if m:
        val = float(m.group(1)) * 1_000_000
        return str(int(val))
    # Pure numeric
    m = re.match(r'^([\d\.]+)$', raw)
    if m:
        val_s = m.group(1)
        if "." in val_s and len(val_s.replace(".", "")) > 10:
            return None  # too ambiguous
        return str(int(float(val_s))) if "." in val_s else val_s
    return None


def extract_fields_from_text(text: str, project_id: str, pdf_path: Path) -> dict:
    """
    Parse DocIntel markdown text for buyer-critical fields.
    Returns dict of field_name -> list of (value, snippet, page_hint) tuples.
    """
    hits = {
        "bedrooms": [],
        "bua_sqm": [],
        "starting_price": [],
        "prices": [],
        "downpayment_pct": [],
        "installment_years": [],
        "delivery_year": [],
        "finishing": [],
        "unit_types": set(),
    }

    lines = text.split("\n")
    for i, line in enumerate(lines):
        context = " ".join(lines[max(0, i-1):i+2])

        # Bedrooms
        for m in RE_BEDROOM.finditer(line):
            hits["bedrooms"].append((int(m.group(1)), line.strip(), f"line:{i+1}"))

        # BUA
        for m in RE_BUA.finditer(line):
            raw = m.group(1).replace(",", "")
            try:
                val = float(raw)
                if 20 <= val <= 5000:  # sanity range for real estate sqm
                    hits["bua_sqm"].append((val, line.strip(), f"line:{i+1}"))
            except ValueError:
                pass

        # Starting price
        for m in RE_STARTING_PRICE.finditer(context):
            raw = m.group(1)
            norm = normalize_price(raw)
            if norm:
                hits["starting_price"].append((norm, context.strip()[:120], f"line:{i+1}"))

        # General EGP prices (for range computation)
        if re.search(r'\bEGP\b|\bLE\b', line, re.IGNORECASE):
            for m in RE_PRICE_EGP.finditer(line):
                raw = m.group(1).replace(",", "")
                norm = normalize_price(raw)
                if norm and int(norm) > 100000:  # floor: prices above 100K EGP
                    hits["prices"].append((norm, line.strip(), f"line:{i+1}"))

        # Downpayment
        for m in RE_DOWNPAYMENT.finditer(line):
            val = float(m.group(1))
            if 0 < val <= 100:
                hits["downpayment_pct"].append((val, line.strip(), f"line:{i+1}"))

        # Installment years
        for m in RE_INSTALLMENT_YEARS.finditer(line):
            val = int(m.group(1))
            if 1 <= val <= 30:
                hits["installment_years"].append((val, line.strip(), f"line:{i+1}"))

        # Delivery year
        for m in RE_DELIVERY.finditer(line):
            yr = int(m.group(1))
            if 2020 <= yr <= 2035:
                hits["delivery_year"].append((yr, line.strip(), f"line:{i+1}"))

        # Finishing
        for m in RE_FINISHING.finditer(line):
            hits["finishing"].append((m.group(1).lower(), line.strip(), f"line:{i+1}"))

        # Unit types
        for m in RE_UNIT_TYPE.finditer(line):
            hits["unit_types"].add(m.group(1).lower().replace(" ", "_").replace("-", "_"))

    return hits


def synthesize_fields(hits: dict, project_id: str, pdf_path: Path,
                      di_result: dict) -> tuple[dict, list[dict]]:
    """
    Turn raw hits dict into KB field updates + audit rows.
    Returns (updates_dict, audit_rows)
    """
    updates = {}
    audit = []
    pdf_name = pdf_path.name
    source_url = f"file://{pdf_path}"

    def make_audit(field, val, snippet, page_hint, confidence="medium", overwrite=False):
        return {
            "project_id": project_id,
            "field_name": field,
            "field_value": str(val),
            "source_url": source_url,
            "evidence_type": "docintel",
            "evidence_snippet": snippet[:200],
            "asset_path_or_pdf_page": f"{pdf_name}::{page_hint}",
            "captured_date": TODAY,
            "parser_confidence": confidence,
            "overwrite_flag": "true" if overwrite else "false",
            "notes": "",
        }

    # Bedrooms
    if hits["bedrooms"]:
        vals = [v for v, _, _ in hits["bedrooms"]]
        mn, mx = min(vals), max(vals)
        snippet = hits["bedrooms"][0][1]
        page = hits["bedrooms"][0][2]
        updates["bedrooms_range_min"] = str(mn)
        updates["bedrooms_range_max"] = str(mx)
        audit.append(make_audit("bedrooms_range_min", mn, snippet, page))
        audit.append(make_audit("bedrooms_range_max", mx, snippet, page))
        log.info(f"    bedrooms: {mn}–{mx} BR")

    # BUA
    if hits["bua_sqm"]:
        vals = [v for v, _, _ in hits["bua_sqm"]]
        mn, mx = min(vals), max(vals)
        if mn != mx or len(vals) >= 2:
            snippet = hits["bua_sqm"][0][1]
            page = hits["bua_sqm"][0][2]
            updates["bua_range_min_sqm"] = str(int(mn))
            updates["bua_range_max_sqm"] = str(int(mx))
            audit.append(make_audit("bua_range_min_sqm", int(mn), snippet, page))
            audit.append(make_audit("bua_range_max_sqm", int(mx), snippet, page))
            log.info(f"    BUA: {int(mn)}–{int(mx)} sqm")

    # Starting price
    if hits["starting_price"]:
        val, snippet, page = hits["starting_price"][0]
        updates["starting_price_value"] = val
        updates["price_status"] = "official"
        updates["pricing_date"] = TODAY
        updates["pricing_disclaimer"] = f"Official starting price from brochure {pdf_name}."
        audit.append(make_audit("starting_price_value", val, snippet, page, confidence="high"))
        audit.append(make_audit("price_status", "official", snippet, page, confidence="high"))
        log.info(f"    starting_price: {val} EGP")

    # Price range from observed prices
    if hits["prices"] and len(hits["prices"]) >= 2:
        price_vals = sorted(set(int(v) for v, _, _ in hits["prices"]))
        pmn, pmx = price_vals[0], price_vals[-1]
        snippet = hits["prices"][0][1]
        page = hits["prices"][0][2]
        updates["price_range_min"] = str(pmn)
        updates["price_range_max"] = str(pmx)
        if "price_status" not in updates:
            updates["price_status"] = "official"
            updates["pricing_date"] = TODAY
            updates["pricing_disclaimer"] = f"Observed official price range from brochure {pdf_name}. Not exhaustive inventory."
        audit.append(make_audit("price_range_min", pmn, snippet, page))
        audit.append(make_audit("price_range_max", pmx, snippet, page))
        log.info(f"    price_range: {pmn:,}–{pmx:,} EGP")

    # Downpayment
    if hits["downpayment_pct"]:
        vals = [v for v, _, _ in hits["downpayment_pct"]]
        mn, mx = min(vals), max(vals)
        snippet = hits["downpayment_pct"][0][1]
        page = hits["downpayment_pct"][0][2]
        updates["downpayment_percent_min"] = str(int(mn))
        updates["downpayment_percent_max"] = str(int(mx))
        audit.append(make_audit("downpayment_percent_min", int(mn), snippet, page))
        audit.append(make_audit("downpayment_percent_max", int(mx), snippet, page))
        # Build payment plan headline
        if hits["installment_years"]:
            yr_vals = [v for v, _, _ in hits["installment_years"]]
            yr_mn, yr_mx = min(yr_vals), max(yr_vals)
            headline = f"{int(mn)}% downpayment, up to {yr_mx} years installments"
            updates["payment_plan_headline"] = headline
            audit.append(make_audit("payment_plan_headline", headline, snippet, page))
            log.info(f"    payment: {headline}")

    # Installment years
    if hits["installment_years"]:
        vals = [v for v, _, _ in hits["installment_years"]]
        mn, mx = min(vals), max(vals)
        snippet = hits["installment_years"][0][1]
        page = hits["installment_years"][0][2]
        updates["installment_years_min"] = str(mn)
        updates["installment_years_max"] = str(mx)
        audit.append(make_audit("installment_years_min", mn, snippet, page))
        audit.append(make_audit("installment_years_max", mx, snippet, page))
        log.info(f"    installment_years: {mn}–{mx}")

    # Delivery
    if hits["delivery_year"]:
        vals = [v for v, _, _ in hits["delivery_year"]]
        mn, mx = min(vals), max(vals)
        snippet = hits["delivery_year"][0][1]
        page = hits["delivery_year"][0][2]
        updates["delivery_year_min"] = str(mn)
        updates["delivery_year_max"] = str(mx)
        updates["delivery_window"] = f"{mn}–{mx}" if mn != mx else str(mn)
        audit.append(make_audit("delivery_year_min", mn, snippet, page))
        audit.append(make_audit("delivery_year_max", mx, snippet, page))
        audit.append(make_audit("delivery_window", updates["delivery_window"], snippet, page))
        log.info(f"    delivery: {updates['delivery_window']}")

    # Finishing
    if hits["finishing"]:
        levels = list({v for v, _, _ in hits["finishing"]})
        snippet = hits["finishing"][0][1]
        page = hits["finishing"][0][2]
        updates["finishing_levels_offered_json"] = json.dumps(levels)
        audit.append(make_audit("finishing_levels_offered_json", json.dumps(levels), snippet, page))
        log.info(f"    finishing: {levels}")

    # Unit types — merge into existing
    if hits["unit_types"]:
        types = sorted(hits["unit_types"])
        log.info(f"    unit_types: {types}")
        # Will be merged in merge pass using existing + new
        updates["_unit_types_new"] = types  # private key for merge pass

    return updates, audit


# ──────────────────────────────────────────────────────────────────────────────
# 5) PASS B+C — Run DocIntel on all brochures
# ──────────────────────────────────────────────────────────────────────────────

def pass_bc_docintel(rows: list[dict]) -> dict:
    """
    For each entity with brochures, run DocIntel.
    Returns dict: project_id -> (updates_dict, audit_rows)
    """
    log.info("═" * 60)
    log.info("PASS B/C — Brochure DocIntel Extraction")
    log.info("═" * 60)

    all_updates = {}  # project_id -> {field: value}
    all_audit   = []  # flat list of audit rows

    # Build brochure map: project_id -> list of unique pdf paths (dedupe by inode/hash)
    seen_hashes = {}
    brochure_map = {}  # project_id -> list of (path, is_primary)

    # Load manifest to understand which entities share brochures
    manifest_path = OUTPUTS / "wdd_brochures_manifest.csv"
    manifest_by_pid = {}
    if manifest_path.exists():
        with open(manifest_path) as f:
            for mr in csv.DictReader(f):
                pid = mr["project_id"]
                mp = Path(mr.get("file_path", ""))
                if mp.exists():
                    manifest_by_pid.setdefault(pid, []).append(mp)

    # Walk projectBrochures directory
    for pid_dir in sorted(BROCHURES.iterdir()):
        if not pid_dir.is_dir():
            continue
        pid = pid_dir.name
        pdfs = list(pid_dir.glob("*.pdf"))
        if not pdfs:
            continue
        brochure_map[pid] = pdfs

    log.info(f"Entities with brochures: {len(brochure_map)}")

    for pid, pdfs in brochure_map.items():
        log.info(f"\n── Entity: {pid} ({len(pdfs)} PDFs)")
        entity_updates = {}
        entity_audit = []

        for pdf_path in pdfs:
            file_hash = sha256_file(pdf_path)[:12]

            # Skip WDD magazine for field extraction (not project-specific enough)
            if "unknown_pdf" in pdf_path.name or "WDD-Magazine" in pdf_path.name:
                log.info(f"  ⊘  Skipping generic magazine: {pdf_path.name}")
                continue

            log.info(f"  PDF: {pdf_path.name}")

            # Check if this exact hash was already processed for ANOTHER entity
            # (shared brochures — still extract, share evidence via audit
            canonical_pid = seen_hashes.get(file_hash, pid)
            if file_hash in seen_hashes and canonical_pid != pid:
                log.info(f"  ↔  Shared brochure (same as {canonical_pid}) — using cached extraction")
                # Copy updates from canonical entity
                if canonical_pid in all_updates:
                    for k, v in all_updates[canonical_pid].items():
                        if k not in entity_updates:
                            entity_updates[k] = v
                # Add audit rows pointing to the shared pdf
                for ar in all_audit:
                    if ar["project_id"] == canonical_pid:
                        shared_ar = dict(ar)
                        shared_ar["project_id"] = pid
                        shared_ar["notes"] = f"Shared brochure from {canonical_pid}"
                        entity_audit.append(shared_ar)
                continue

            seen_hashes[file_hash] = pid

            # Submit to DocIntel
            di_result = docintel_analyze(pdf_path, pid)
            if not di_result:
                log.warning(f"  ✗ DocIntel failed for {pdf_path.name}")
                continue

            # Extract markdown text
            full_text = extract_markdown_text(di_result)
            if not full_text:
                log.warning(f"  ✗ No text extracted from DocIntel result")
                continue

            log.info(f"  ✓ Got {len(full_text)} chars of text from DocIntel")

            # Save normalized text
            norm_path = INTER / f"{pid}__docintel_normalized.json"
            with open(norm_path, "w", encoding="utf-8") as nf:
                json.dump({
                    "project_id": pid,
                    "pdf": pdf_path.name,
                    "hash": file_hash,
                    "extracted_date": TODAY,
                    "text_length": len(full_text),
                    "text_preview": full_text[:2000],
                    "full_text": full_text,
                }, nf, ensure_ascii=False, indent=2)

            # Extract fields
            hits = extract_fields_from_text(full_text, pid, pdf_path)
            updates, audit_rows = synthesize_fields(hits, pid, pdf_path, di_result)

            for k, v in updates.items():
                if not k.startswith("_"):
                    entity_updates[k] = v
            entity_audit.extend(audit_rows)

            # Handle private unit_types_new
            if "_unit_types_new" in updates:
                entity_updates["_unit_types_new"] = updates["_unit_types_new"]

        all_updates[pid] = entity_updates
        all_audit.extend(entity_audit)

    log.info(f"\nDocIntel pass complete. Entities with extracted data: {sum(1 for u in all_updates.values() if u)}")
    return all_updates, all_audit


# ──────────────────────────────────────────────────────────────────────────────
# 6) PASS D — Merge into KB
# ──────────────────────────────────────────────────────────────────────────────

def pass_d_merge(rows: list[dict], fieldnames: list[str],
                 all_updates: dict, all_audit: list[dict]) -> tuple[list[dict], list[dict]]:
    log.info("═" * 60)
    log.info("PASS D — Merge extracted fields into KB")
    log.info("═" * 60)

    merge_report = []

    for row in rows:
        pid = row["project_id"]
        updates = all_updates.get(pid, {})
        if not updates:
            continue

        for field, new_val in updates.items():
            if field.startswith("_"):
                continue  # private keys handled separately

            old_val = row.get(field, "")
            updated = False

            if not old_val.strip():
                # Field was empty — fill it
                row[field] = new_val
                updated = True
                log.info(f"  {pid}.{field}: (empty) → {new_val!r:.60s}")
            elif old_val.strip() != str(new_val).strip():
                # Field already has a value — compare confidence
                # For now, only allow overwrites for confirmed official sources
                # (price_status, pricing fields) and if new value has more evidence
                # Don't overwrite existing good data blindly
                if field in ("price_status",) and new_val == "official":
                    row[field] = new_val
                    updated = True
                    log.info(f"  {pid}.{field}: {old_val!r} → {new_val!r} (upgraded)")
                else:
                    log.info(f"  {pid}.{field}: keeping existing {old_val!r:.40s}")

            merge_report.append({
                "project_id": pid,
                "field_name": field,
                "old_value": old_val,
                "new_value": str(new_val),
                "source_used": "docintel",
                "evidence_type": "docintel",
                "updated_flag": "true" if updated else "false",
                "reason": "field_was_empty" if updated and not old_val.strip() else
                          ("value_upgraded" if updated else "kept_existing"),
            })

        # Handle unit_types_new — merge into existing JSON list
        if "_unit_types_new" in updates:
            new_types = updates["_unit_types_new"]
            existing_json_str = row.get("unit_types_offered_json", "[]") or "[]"
            try:
                existing = json.loads(existing_json_str)
            except Exception:
                existing = []
            merged = sorted(set(existing) | set(new_types))
            row["unit_types_offered_json"] = json.dumps(merged)
            merge_report.append({
                "project_id": pid,
                "field_name": "unit_types_offered_json",
                "old_value": existing_json_str,
                "new_value": json.dumps(merged),
                "source_used": "docintel",
                "evidence_type": "docintel",
                "updated_flag": "true",
                "reason": "merged_unit_types_from_brochure",
            })

        # Recompute confidence score
        row["confidence_score"] = str(compute_confidence(row))
        row["last_verified_date"] = TODAY

    return rows, merge_report


def compute_confidence(row: dict) -> float:
    score = 0.30
    if row.get("official_project_url", "").strip():
        score += 0.15
    if row.get("brochure_urls_json", "[]").strip() not in ("[]", ""):
        try:
            if json.loads(row["brochure_urls_json"]):
                score += 0.15
        except Exception:
            pass
    if row.get("unit_types_offered_json", "[]").strip() not in ("[]", ""):
        try:
            if json.loads(row["unit_types_offered_json"]):
                score += 0.15
        except Exception:
            pass
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


# ──────────────────────────────────────────────────────────────────────────────
# 7) PASS E — Validation
# ──────────────────────────────────────────────────────────────────────────────

def pass_e_validate(rows: list[dict], fieldnames: list[str]) -> bool:
    log.info("═" * 60)
    log.info("PASS E — Validation")
    log.info("═" * 60)

    errors = []

    # Structural
    assert len(rows) == 28, f"Row count mismatch: {len(rows)} != 28"
    pids = [r["project_id"] for r in rows]
    assert len(set(pids)) == 28, f"Duplicate project_ids detected"
    assert list(rows[0].keys()) == list(fieldnames), "Fieldnames mismatch"

    # JSON columns
    for row in rows:
        for col in JSON_COLS:
            val = row.get(col, "[]") or "[]"
            try:
                json.loads(val)
            except json.JSONDecodeError as e:
                errors.append(f"{row['project_id']}.{col}: invalid JSON — {e}")

    # Numeric ordering constraints
    for row in rows:
        pid = row["project_id"]
        def num(f): return float(row[f]) if row.get(f, "").strip() else None

        br_mn, br_mx = num("bedrooms_range_min"), num("bedrooms_range_max")
        if br_mn is not None and br_mx is not None and br_mn > br_mx:
            errors.append(f"{pid}: bedrooms_range_min > bedrooms_range_max")

        bua_mn, bua_mx = num("bua_range_min_sqm"), num("bua_range_max_sqm")
        if bua_mn is not None and bua_mx is not None and bua_mn > bua_mx:
            errors.append(f"{pid}: bua_range_min > bua_range_max")

        pr_mn, pr_mx = num("price_range_min"), num("price_range_max")
        if pr_mn is not None and pr_mx is not None and pr_mn > pr_mx:
            errors.append(f"{pid}: price_range_min > price_range_max")

    if errors:
        for e in errors:
            log.error(f"  VALIDATION ERROR: {e}")
        return False

    log.info(f"  ✓ All {len(rows)} rows valid")
    return True


# ──────────────────────────────────────────────────────────────────────────────
# 8) COVERAGE REPORT
# ──────────────────────────────────────────────────────────────────────────────

def coverage_report(rows: list[dict]):
    log.info("═" * 60)
    log.info("COVERAGE REPORT")
    log.info("═" * 60)

    n = len(rows)
    def pct(f): return sum(1 for r in rows if r.get(f,"").strip())

    report = {
        "total_rows": n,
        "with_official_url": pct("official_project_url"),
        "with_brochure_urls": sum(1 for r in rows if r.get("brochure_urls_json","[]") not in ("[]","")),
        "with_bedrooms": pct("bedrooms_range_min"),
        "with_bua": pct("bua_range_min_sqm"),
        "with_starting_price": pct("starting_price_value"),
        "with_price_range": pct("price_range_min"),
        "with_payment_plan": pct("payment_plan_headline"),
        "with_delivery": pct("delivery_window"),
        "with_finishing": pct("finishing_levels_offered_json"),
        "price_status_official": sum(1 for r in rows if r.get("price_status","") == "official"),
        "price_status_on_request": sum(1 for r in rows if r.get("price_status","") == "on_request"),
        "still_all_missing_specs": sum(1 for r in rows
            if not any(r.get(f,"").strip() for f in ["bedrooms_range_min","bua_range_min_sqm","starting_price_value"])),
    }

    for k, v in report.items():
        log.info(f"  {k}: {v}/{n}" if k != "total_rows" else f"  {k}: {v}")

    with open(INTER / "wdd_coverage_report.json", "w") as f:
        json.dump(report, f, indent=2)

    return report


# ──────────────────────────────────────────────────────────────────────────────
# 9) MAIN ORCHESTRATION
# ──────────────────────────────────────────────────────────────────────────────

def main():
    log.info("=" * 70)
    log.info("PulseX-WDD — Brochure Enrichment Pipeline")
    log.info(f"Run date: {TODAY}")
    log.info("=" * 70)

    # Load KB
    rows, fieldnames = load_kb()
    log.info(f"Loaded KB: {len(rows)} rows × {len(fieldnames)} columns")

    # Backup
    backup_engine_kb()

    # PASS A — Gap analysis
    gap_rows = pass_a_gap_analysis(rows, fieldnames)

    # PASS B/C — DocIntel extraction
    all_updates, all_audit = pass_bc_docintel(rows)

    # PASS D — Merge into KB
    rows, merge_report = pass_d_merge(rows, fieldnames, all_updates, all_audit)

    # Write merge report
    merge_path = INTER / "wdd_merge_report.csv"
    with open(merge_path, "w", newline="", encoding="utf-8") as f:
        if merge_report:
            w = csv.DictWriter(f, fieldnames=MERGE_HEADER, extrasaction="ignore")
            w.writeheader()
            w.writerows(merge_report)
    log.info(f"Merge report: {merge_path} ({len(merge_report)} rows)")

    # Append audit rows
    if all_audit:
        append_audit(all_audit)
        log.info(f"Audit: {len(all_audit)} new rows appended to {AUDIT_PATH}")

    # PASS E — Validate
    valid = pass_e_validate(rows, fieldnames)
    if not valid:
        log.error("Validation FAILED — not writing KB. Fix errors above.")
        sys.exit(1)

    # Write KB
    save_kb(rows, fieldnames)

    # Coverage report
    report = coverage_report(rows)

    log.info("=" * 70)
    log.info("ENRICHMENT COMPLETE")
    log.info("=" * 70)

    return report


if __name__ == "__main__":
    report = main()
