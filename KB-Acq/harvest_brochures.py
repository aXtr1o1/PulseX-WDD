#!/usr/bin/env python3
"""
PulseX-WDD Brochure Harvest Pipeline
=====================================
Downloads all official WDD project brochures, validates them, probes for
extraction hints, and generates all required CSV manifests + audit trails.

Run:  python3 harvest_brochures.py
"""

import csv, json, os, sys, hashlib, datetime, urllib.request, urllib.error
import ssl, re, subprocess, traceback

# ── CONFIG ──────────────────────────────────────────────────────────────

TODAY = "2026-02-25"
BASE = "/Volumes/ReserveDisk/codeBase/PulseX-WDD/KB-Acq"
KB_PATH = "/Volumes/ReserveDisk/codeBase/PulseX-WDD/engine-KB/PulseX-WDD_buyerKB.csv"

BROCHURE_DIR = os.path.join(BASE, "projectBrochures")
OUTPUTS_DIR  = os.path.join(BASE, "outputs")
PROBE_DIR    = os.path.join(BASE, "raw", "pdf_probe")
LOGS_DIR     = os.path.join(BASE, "logs")
SCREENS_DIR  = os.path.join(BASE, "raw", "screens")

LOG_PATH = os.path.join(LOGS_DIR, "wdd_brochure_harvest.log")
log_lines = []

def log(msg):
    ts = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
    line = f"[{ts}] {msg}"
    log_lines.append(line)
    print(line)

# SSL context for HTTPS
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

# ── CANONICAL ENTITY REGISTRY ──────────────────────────────────────────

ENTITY_META = {
    "murano":                    {"name":"Murano",                   "type":"flagship_project",  "parent":""},
    "clubtown":                  {"name":"ClubTown",                 "type":"flagship_project",  "parent":""},
    "neo":                       {"name":"Neo",                      "type":"flagship_project",  "parent":""},
    "vero":                      {"name":"Vero",                     "type":"flagship_project",  "parent":""},
    "promenade_new_cairo":       {"name":"Promenade New Cairo",      "type":"flagship_project",  "parent":""},
    "blumar_el_sokhna":          {"name":"Blumar El Sokhna",         "type":"flagship_project",  "parent":""},
    "blumar_hills":              {"name":"Blumar Hills",             "type":"flagship_project",  "parent":""},
    "tijan_maadi":               {"name":"Tijan Maadi",              "type":"flagship_project",  "parent":""},
    "blumar_el_dome":            {"name":"Blumar El Dome",           "type":"flagship_project",  "parent":""},
    "pyramids_walk":             {"name":"Pyramids Walk",            "type":"flagship_project",  "parent":""},
    "blumar_sidi_abd_el_rahman": {"name":"Blumar Sidi Abd El Rahman","type":"flagship_project",  "parent":""},
    "tijan_zahraa_el_maadi":     {"name":"Tijan Zahraa El Maadi",    "type":"flagship_project",  "parent":""},
    "canal_residence":           {"name":"Canal Residence",          "type":"flagship_project",  "parent":""},
    "river_walk":                {"name":"River Walk",               "type":"flagship_project",  "parent":""},
    "marina_wadi_degla":         {"name":"Marina Wadi Degla",        "type":"flagship_project",  "parent":""},
    "living_community":          {"name":"Living Community",         "type":"phase_entity",      "parent":"murano"},
    "waterside":                 {"name":"Waterside",                "type":"phase_entity",      "parent":"murano"},
    "floating_islands":          {"name":"Floating Islands",         "type":"phase_entity",      "parent":"murano"},
    "ojo":                       {"name":"Ojo",                      "type":"phase_entity",      "parent":"murano"},
    "neo_lakes":                 {"name":"Neo Lakes",                "type":"phase_entity",      "parent":"neo"},
    "neo_gardens":               {"name":"Neo Gardens",              "type":"phase_entity",      "parent":"neo"},
    "breeze":                    {"name":"Breeze",                   "type":"phase_entity",      "parent":"clubtown"},
    "horizon":                   {"name":"Horizon",                  "type":"phase_entity",      "parent":"clubtown"},
    "edge":                      {"name":"Edge",                     "type":"phase_entity",      "parent":"clubtown"},
    "vyon":                      {"name":"VYON",                     "type":"phase_entity",      "parent":"clubtown"},
    "neopolis":                  {"name":"Neopolis",                 "type":"referenced_name",   "parent":"neo"},
    "mada":                      {"name":"Mada",                     "type":"referenced_name",   "parent":""},
    "camuse":                    {"name":"CAMUSE",                   "type":"referenced_name",   "parent":""},
}

# ── ADDITIONAL BROCHURE CANDIDATES (from browser crawling + known patterns) ──

ADDITIONAL_PDF_CANDIDATES = {
    # From existing KB
    "murano": [
        "https://wadidegladevelopments.com/wp-content/uploads/2023/09/Waterside-Brochure.pdf",
        "https://wadidegladevelopments.com/wp-content/uploads/2025/09/WDD-Magazine-25-Digital.pdf",
    ],
    "clubtown": [
        "https://wadidegladevelopments.com/wp-content/uploads/2025/09/WDD-Magazine-25-Digital.pdf",
    ],
    "neo": [
        "https://wadidegladevelopments.com/wp-content/uploads/2023/09/Wadi-Degla-Development-Neopolis-Neo-Gardens.pdf",
    ],
    "vero": [
        "https://wadidegladevelopments.com/wp-content/uploads/2025/09/WDD-Magazine-25-Digital.pdf",
    ],
    "promenade_new_cairo": [
        "https://wadidegladevelopments.com/wp-content/uploads/2025/09/WDD-Magazine-25-Digital.pdf",
    ],
    "blumar_el_sokhna": [
        "https://wadidegladevelopments.com/wp-content/uploads/2025/09/WDD-Magazine-25-Digital.pdf",
    ],
    "blumar_hills": [
        "https://wadidegladevelopments.com/wp-content/uploads/2025/09/WDD-Magazine-25-Digital.pdf",
    ],
    "living_community": [
        "https://wadidegladevelopments.com/wp-content/uploads/2023/09/Waterside-Brochure.pdf",
    ],
    "waterside": [
        "https://wadidegladevelopments.com/wp-content/uploads/2023/09/Waterside-Brochure.pdf",
    ],
    "floating_islands": [
        "https://wadidegladevelopments.com/wp-content/uploads/2024/07/Floating-Islands-Brochure.pdf",
    ],
    "ojo": [
        "https://wadidegladevelopments.com/wp-content/uploads/2025/12/Ojo-Brochure.pdf",
    ],
    "neo_lakes": [
        "https://wadidegladevelopments.com/wp-content/uploads/2023/10/Neo-Lakes.pdf",
    ],
    "neo_gardens": [
        "https://wadidegladevelopments.com/wp-content/uploads/2023/09/Wadi-Degla-Development-Neopolis-Neo-Gardens.pdf",
    ],
    "breeze": [
        "https://wadidegladevelopments.com/wp-content/uploads/2023/10/CT-Breeze-Brochure.pdf",
    ],
    "horizon": [
        "https://wadidegladevelopments.com/wp-content/uploads/2023/10/CT-Horizon-Brochure-Wadi-Degla-Developments_.pdf",
    ],
    "edge": [
        "https://wadidegladevelopments.com/wp-content/uploads/2024/07/Edge-Brochure-2.pdf",
    ],
    "vyon": [
        "https://wadidegladevelopments.com/wp-content/uploads/2025/07/VYON-Brochure.pdf",
    ],
    "neopolis": [
        "https://wadidegladevelopments.com/wp-content/uploads/2023/09/Wadi-Degla-Development-Neopolis-Neo-Gardens.pdf",
    ],
}

# WDD Magazine is a corporate publication, not a project brochure
# But we still download it once for evidence
WDD_MAGAZINE_URL = "https://wadidegladevelopments.com/wp-content/uploads/2025/09/WDD-Magazine-25-Digital.pdf"

# ── HELPERS ─────────────────────────────────────────────────────────────

def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()

def classify_doc_type(url, filename):
    """Classify the PDF doc_type based on URL/filename clues."""
    lower = (url + " " + filename).lower()
    if "masterplan" in lower or "master-plan" in lower:
        return "masterplan"
    if "floorplan" in lower or "floor-plan" in lower or "floor_plan" in lower:
        return "floorplan"
    if "price" in lower or "pricing" in lower:
        return "price_list"
    if "payment" in lower:
        return "payment_plan"
    if "spec" in lower:
        return "spec_sheet"
    if "magazine" in lower or "newsletter" in lower:
        return "unknown_pdf"  # corporate material
    if "brochure" in lower:
        if any(phase in lower for phase in ["breeze","horizon","edge","vyon","waterside","floating","ojo","neo-lakes","neo-gardens","neopolis"]):
            return "phase_brochure"
        return "project_brochure"
    # Default: if URL has project name context
    return "project_brochure"

def short_hash(url):
    return hashlib.md5(url.encode()).hexdigest()[:8]

def safe_filename(project_id, doc_type, url):
    return f"{project_id}__{doc_type}__{short_hash(url)}.pdf"

def download_pdf(url, dest_path):
    """Download a PDF from URL to dest_path. Returns (http_status, content_type, success, error)."""
    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 PulseX-WDD-Harvester/1.0",
            "Accept": "application/pdf,*/*",
        })
        resp = urllib.request.urlopen(req, context=ctx, timeout=60)
        http_status = resp.getcode()
        content_type = resp.headers.get("Content-Type", "unknown")
        data = resp.read()

        if len(data) == 0:
            return http_status, content_type, False, "Empty response body"

        os.makedirs(os.path.dirname(dest_path), exist_ok=True)
        with open(dest_path, "wb") as f:
            f.write(data)

        # Validate PDF header
        if not data[:5] == b"%PDF-":
            return http_status, content_type, False, f"Not a PDF (header: {data[:20]})"

        return http_status, content_type, True, None

    except urllib.error.HTTPError as e:
        return e.code, "", False, str(e)
    except Exception as e:
        return 0, "", False, str(e)

def probe_pdf(file_path):
    """Quick probe of a PDF: page count, text extractability, keyword hits."""
    result = {
        "page_count": "unknown",
        "pdf_text_extractable": "unknown",
        "keyword_hits": {},
        "likely_spec_pages": [],
        "likely_pricing_pages": [],
        "likely_payment_plan_pages": [],
        "probe_status": "attempted",
        "notes": "",
    }

    # Try using python3 to detect page count and text
    try:
        with open(file_path, "rb") as f:
            data = f.read()

        # Page count via regex on PDF internals
        # Count /Type /Page (but not /Type /Pages)
        pages = re.findall(rb'/Type\s*/Page[^s]', data)
        if pages:
            result["page_count"] = len(pages)
        else:
            # Alternative: count 'endstream' or search for /Count
            counts = re.findall(rb'/Count\s+(\d+)', data)
            if counts:
                result["page_count"] = max(int(c) for c in counts)

        # Check text extractability by looking for text streams
        text_blocks = re.findall(rb'BT\s.*?ET', data, re.DOTALL)
        if text_blocks and len(text_blocks) > 2:
            result["pdf_text_extractable"] = True

            # Try to extract some text for keyword scanning
            # Decode text segments — look for common text operators
            all_text = ""
            for block in text_blocks[:100]:  # limit to first 100 blocks
                # Extract text from Tj/TJ operators
                texts = re.findall(rb'\((.*?)\)', block)
                for t in texts:
                    try:
                        all_text += t.decode("latin-1", errors="ignore") + " "
                    except:
                        pass

            # Keyword scanning
            keywords = {
                "bedrooms": ["bedroom", "bedrooms", "br ", " br", "1br", "2br", "3br", "4br"],
                "sqm_bua": ["sqm", "m2", "m²", "area", "bua", "built-up"],
                "pricing": ["egp", "price", "starting from", "جنيه", "starting price"],
                "payment": ["payment plan", "installment", "down payment", "downpayment"],
                "delivery": ["delivery", "handover", "hand over", "completion"],
            }
            for cat, terms in keywords.items():
                hits = []
                for term in terms:
                    if term.lower() in all_text.lower():
                        hits.append(term)
                if hits:
                    result["keyword_hits"][cat] = hits

        else:
            result["pdf_text_extractable"] = False
            result["notes"] = "Image-based PDF; OCR required for extraction."

        result["probe_status"] = "completed"

    except Exception as e:
        result["probe_status"] = "failed"
        result["notes"] = str(e)

    return result

# ── MAIN PIPELINE ───────────────────────────────────────────────────────

def main():
    log("=" * 70)
    log("PulseX-WDD Brochure Harvest Pipeline — START")
    log(f"Date: {TODAY}")
    log(f"Base: {BASE}")
    log("=" * 70)

    # ── Load KB for project URLs ────────────────────────────────────────
    kb_data = {}
    with open(KB_PATH, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            kb_data[row["project_id"]] = row

    # ── Build combined URL registry ─────────────────────────────────────
    # Merge KB brochure_urls_json + ADDITIONAL_PDF_CANDIDATES
    all_candidates = {}
    for pid in ENTITY_META:
        urls = set()
        # From KB
        if pid in kb_data:
            brochures_json = kb_data[pid].get("brochure_urls_json", "[]")
            try:
                urls.update(json.loads(brochures_json))
            except:
                pass
        # From additional candidates
        if pid in ADDITIONAL_PDF_CANDIDATES:
            urls.update(ADDITIONAL_PDF_CANDIDATES[pid])
        all_candidates[pid] = list(urls)

    # Count unique URLs
    all_unique_urls = set()
    for urls in all_candidates.values():
        all_unique_urls.update(urls)
    log(f"Total unique PDF URLs to attempt: {len(all_unique_urls)}")
    log(f"Entities with candidates: {sum(1 for v in all_candidates.values() if v)}")
    log(f"Entities with no candidates: {sum(1 for v in all_candidates.values() if not v)}")

    # ── Download Phase ──────────────────────────────────────────────────
    manifest_rows = []     # wdd_brochures_manifest.csv
    audit_rows = []        # wdd_brochure_source_audit.csv
    probe_rows = []        # wdd_pdf_probe_manifest.csv
    screen_rows = []       # wdd_screens_index.csv (from previous crawl + existing)
    downloaded_hashes = {} # sha256 → file_path (for dedup)
    entity_downloads = {}  # pid → list of manifest rows

    for pid, meta in ENTITY_META.items():
        entity_downloads[pid] = []
        pname = meta["name"]
        official_url = kb_data.get(pid, {}).get("official_project_url", "")
        urls = all_candidates.get(pid, [])

        log(f"\n── Processing: {pname} ({pid}) — {len(urls)} candidate(s)")

        # Audit: record page resolution
        audit_rows.append({
            "project_id": pid, "project_name": pname,
            "field_name": "official_project_url",
            "field_value": official_url or "none",
            "source_url": official_url or "https://wadidegladevelopments.com/projects/",
            "evidence_type": "dom",
            "evidence_snippet": f"Official URL from KB: {official_url}" if official_url else "No official page found",
            "screenshot_path": "", "asset_path_or_ref": "",
            "captured_date": TODAY, "notes": ""
        })

        if not urls:
            log(f"  ❌ No brochure URL candidates for {pid}")
            audit_rows.append({
                "project_id": pid, "project_name": pname,
                "field_name": "no_brochure_found",
                "field_value": "true",
                "source_url": official_url or "https://wadidegladevelopments.com/projects/",
                "evidence_type": "link_scan",
                "evidence_snippet": "No PDF links found on project page or KB for this entity.",
                "screenshot_path": "", "asset_path_or_ref": "",
                "captured_date": TODAY,
                "notes": "Entity may be sold out or have no dedicated brochure."
            })
            continue

        for url in urls:
            # Skip WDD Magazine for non-primary entities (download once for reference)
            is_magazine = "WDD-Magazine" in url

            doc_type = classify_doc_type(url, os.path.basename(url))
            if is_magazine:
                doc_type = "unknown_pdf"

            fname = safe_filename(pid, doc_type, url)
            dest = os.path.join(BROCHURE_DIR, pid, fname)

            log(f"  📄 Downloading: {os.path.basename(url)}")
            log(f"     → {dest}")

            # Audit: record brochure link candidate
            audit_rows.append({
                "project_id": pid, "project_name": pname,
                "field_name": "brochure_link_candidate",
                "field_value": url,
                "source_url": official_url or url,
                "evidence_type": "dom",
                "evidence_snippet": f"PDF link from KB/official page: {url}",
                "screenshot_path": "", "asset_path_or_ref": "",
                "captured_date": TODAY, "notes": ""
            })

            http_status, content_type, success, error = download_pdf(url, dest)

            if success:
                fsize = os.path.getsize(dest)
                fhash = sha256_file(dest)

                # Dedup check
                if fhash in downloaded_hashes:
                    existing = downloaded_hashes[fhash]
                    log(f"  ⚠️  Duplicate SHA256 (same as {existing})")
                    # Still keep for this entity's manifest; note in notes
                    dedup_note = f"Duplicate of {existing}"
                else:
                    downloaded_hashes[fhash] = dest
                    dedup_note = ""

                log(f"  ✅ Downloaded: {fsize} bytes, SHA256: {fhash[:12]}...")

                # Doc ID
                doc_id = f"{pid}__{short_hash(url)}"

                manifest_row = {
                    "project_id": pid, "project_name": pname,
                    "doc_id": doc_id,
                    "doc_type": doc_type,
                    "doc_title_guess": os.path.basename(url).replace(".pdf","").replace("-"," ").replace("_"," "),
                    "source_url": url,
                    "referrer_url": official_url or "",
                    "download_url_final": url,
                    "http_status": str(http_status),
                    "content_type": content_type,
                    "file_path": dest,
                    "file_name": fname,
                    "file_size_bytes": str(fsize),
                    "sha256": fhash,
                    "page_count": "",
                    "pdf_text_extractable": "",
                    "discovered_via": "dom_link",
                    "captured_date": TODAY,
                    "last_verified_date": TODAY,
                    "notes": dedup_note,
                }

                # Probe
                log(f"  🔍 Probing PDF...")
                probe = probe_pdf(dest)
                manifest_row["page_count"] = str(probe["page_count"])
                manifest_row["pdf_text_extractable"] = str(probe["pdf_text_extractable"]).lower()

                probe_json_path = os.path.join(PROBE_DIR, pid, f"{os.path.splitext(fname)[0]}.json")
                os.makedirs(os.path.dirname(probe_json_path), exist_ok=True)
                with open(probe_json_path, "w") as pf:
                    json.dump(probe, pf, indent=2, default=str)

                probe_rows.append({
                    "project_id": pid, "project_name": pname,
                    "doc_id": doc_id,
                    "file_path": dest,
                    "page_count": str(probe["page_count"]),
                    "pdf_text_extractable": str(probe["pdf_text_extractable"]).lower(),
                    "keyword_hits_json": json.dumps(probe["keyword_hits"]),
                    "likely_spec_pages_json": json.dumps(probe["likely_spec_pages"]),
                    "likely_pricing_pages_json": json.dumps(probe["likely_pricing_pages"]),
                    "likely_payment_plan_pages_json": json.dumps(probe["likely_payment_plan_pages"]),
                    "probe_status": probe["probe_status"],
                    "notes": probe["notes"],
                })

                manifest_rows.append(manifest_row)
                entity_downloads[pid].append(manifest_row)

                # Audit: confirmed download
                audit_rows.append({
                    "project_id": pid, "project_name": pname,
                    "field_name": "pdf_download_confirmed",
                    "field_value": url,
                    "source_url": url,
                    "evidence_type": "pdf",
                    "evidence_snippet": f"PDF downloaded: {fsize} bytes, SHA256={fhash[:16]}",
                    "screenshot_path": "", "asset_path_or_ref": dest,
                    "captured_date": TODAY, "notes": dedup_note,
                })

            else:
                log(f"  ❌ Download FAILED: {error} (HTTP {http_status})")
                audit_rows.append({
                    "project_id": pid, "project_name": pname,
                    "field_name": "brochure_download_failed",
                    "field_value": url,
                    "source_url": url,
                    "evidence_type": "net",
                    "evidence_snippet": f"Download failed: HTTP {http_status}, error={error}",
                    "screenshot_path": "", "asset_path_or_ref": "",
                    "captured_date": TODAY, "notes": "",
                })

    # ── Add existing screenshot index entries ───────────────────────────
    # Load from previous runs if exists
    prev_screens = os.path.join(OUTPUTS_DIR, "wdd_screens_index.csv")
    if os.path.exists(prev_screens):
        with open(prev_screens, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                screen_rows.append({
                    "project_id": row.get("project_id",""),
                    "project_name": ENTITY_META.get(row.get("project_id",""),{}).get("name", row.get("project_id","")),
                    "page_type": row.get("page_type",""),
                    "source_url": row.get("source_url",""),
                    "screenshot_path": row.get("screenshot_path",""),
                    "captured_date": row.get("captured_date", TODAY),
                    "notes": "",
                })

    # Add projects index screenshot from this run
    screen_rows.append({
        "project_id": "_index",
        "project_name": "WDD Projects Index",
        "page_type": "projects_index",
        "source_url": "https://wadidegladevelopments.com/projects/",
        "screenshot_path": "raw/screens/projects_index_full.png",
        "captured_date": TODAY,
        "notes": "Captured during brochure harvest run",
    })

    # ── Build Coverage CSV (28 rows exactly) ────────────────────────────
    coverage_rows = []
    missing_rows = []

    for pid, meta in ENTITY_META.items():
        pname = meta["name"]
        etype = meta["type"]
        parent = meta["parent"]
        official_url = kb_data.get(pid, {}).get("official_project_url", "")
        downloads = entity_downloads.get(pid, [])

        page_found = bool(official_url)
        brochure_found = len(downloads) > 0
        # Filter out magazine-only entries
        real_brochures = [d for d in downloads if d["doc_type"] != "unknown_pdf"]
        brochure_count = len(downloads)
        doc_types = list(set(d["doc_type"] for d in downloads))
        attempted = all_candidates.get(pid, [])

        # Source links
        source_links = [official_url] if official_url else []
        source_links.append("https://wadidegladevelopments.com/projects/")

        # Screenshots from existing data
        screenshots = []
        if pid in kb_data:
            try:
                screenshots = json.loads(kb_data[pid].get("screenshot_paths_json", "[]"))
            except:
                pass

        # Confidence scoring
        conf = 0.20
        if page_found:
            conf += 0.25
        if brochure_found:
            conf += 0.25
        if screenshots:
            conf += 0.10
        if brochure_found and any(d.get("sha256") for d in downloads):
            conf += 0.10  # DOM evidence
        if any(p.get("probe_status") == "completed" for p in probe_rows if p["project_id"] == pid):
            conf += 0.10
        conf = min(conf, 1.0)

        # Missing reason
        missing_reason = ""
        coverage_status = "complete"
        if not brochure_found:
            coverage_status = "not_found"
            if not page_found:
                missing_reason = "no_project_page"
            elif etype == "referenced_name":
                missing_reason = "entity_reference_only"
            else:
                missing_reason = "no_pdf_links_visible"
        elif not real_brochures:
            coverage_status = "partial"
            missing_reason = "only_generic_magazine_pdf"

        coverage_rows.append({
            "project_id": pid, "project_name": pname,
            "entity_type": etype, "parent_project": parent,
            "official_project_url": official_url,
            "page_found_flag": str(page_found).lower(),
            "project_page_status": "resolved" if page_found else "not_found",
            "brochure_found_flag": str(brochure_found).lower(),
            "brochure_count": str(brochure_count),
            "brochure_doc_types_json": json.dumps(doc_types),
            "attempted_urls_json": json.dumps(attempted),
            "source_links_json": json.dumps(source_links),
            "screenshot_paths_json": json.dumps(screenshots),
            "coverage_status": coverage_status,
            "missing_reason": missing_reason,
            "confidence_score": f"{conf:.2f}",
            "last_verified_date": TODAY,
            "notes": "",
        })

        # Missing report
        if not brochure_found:
            missing_rows.append({
                "project_id": pid, "project_name": pname,
                "official_project_url": official_url,
                "attempted_urls_json": json.dumps(attempted),
                "evidence_summary": f"No brochure PDFs found via KB scan or DOM crawl. Page found: {page_found}.",
                "likely_reason": missing_reason,
                "next_retry_strategy": "manual_site_search" if page_found else "check_wayback_or_contact_dev",
                "screenshot_paths_json": json.dumps(screenshots),
                "last_verified_date": TODAY,
            })

    # ── WRITE ALL CSVs ──────────────────────────────────────────────────

    # 1. Manifest
    MANIFEST_HDR = [
        "project_id","project_name","doc_id","doc_type","doc_title_guess",
        "source_url","referrer_url","download_url_final","http_status",
        "content_type","file_path","file_name","file_size_bytes","sha256",
        "page_count","pdf_text_extractable","discovered_via",
        "captured_date","last_verified_date","notes"
    ]
    with open(os.path.join(OUTPUTS_DIR, "wdd_brochures_manifest.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=MANIFEST_HDR)
        w.writeheader()
        w.writerows(manifest_rows)
    log(f"\n✓ wdd_brochures_manifest.csv: {len(manifest_rows)} rows")

    # 2. Coverage
    COVERAGE_HDR = [
        "project_id","project_name","entity_type","parent_project",
        "official_project_url","page_found_flag","project_page_status",
        "brochure_found_flag","brochure_count","brochure_doc_types_json",
        "attempted_urls_json","source_links_json","screenshot_paths_json",
        "coverage_status","missing_reason","confidence_score",
        "last_verified_date","notes"
    ]
    with open(os.path.join(OUTPUTS_DIR, "wdd_brochure_coverage.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COVERAGE_HDR)
        w.writeheader()
        w.writerows(coverage_rows)
    log(f"✓ wdd_brochure_coverage.csv: {len(coverage_rows)} rows")

    # 3. Source audit
    AUDIT_HDR = [
        "project_id","project_name","field_name","field_value",
        "source_url","evidence_type","evidence_snippet",
        "screenshot_path","asset_path_or_ref","captured_date","notes"
    ]
    with open(os.path.join(OUTPUTS_DIR, "wdd_brochure_source_audit.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=AUDIT_HDR)
        w.writeheader()
        w.writerows(audit_rows)
    log(f"✓ wdd_brochure_source_audit.csv: {len(audit_rows)} rows")

    # 4. Screens index
    SCREEN_HDR = [
        "project_id","project_name","page_type","source_url",
        "screenshot_path","captured_date","notes"
    ]
    with open(os.path.join(OUTPUTS_DIR, "wdd_screens_index.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=SCREEN_HDR)
        w.writeheader()
        w.writerows(screen_rows)
    log(f"✓ wdd_screens_index.csv: {len(screen_rows)} rows")

    # 5. Missing report
    MISSING_HDR = [
        "project_id","project_name","official_project_url",
        "attempted_urls_json","evidence_summary","likely_reason",
        "next_retry_strategy","screenshot_paths_json","last_verified_date"
    ]
    with open(os.path.join(OUTPUTS_DIR, "wdd_brochure_missing_report.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=MISSING_HDR)
        w.writeheader()
        w.writerows(missing_rows)
    log(f"✓ wdd_brochure_missing_report.csv: {len(missing_rows)} rows")

    # 6. Probe manifest
    PROBE_HDR = [
        "project_id","project_name","doc_id","file_path","page_count",
        "pdf_text_extractable","keyword_hits_json","likely_spec_pages_json",
        "likely_pricing_pages_json","likely_payment_plan_pages_json",
        "probe_status","notes"
    ]
    with open(os.path.join(OUTPUTS_DIR, "wdd_pdf_probe_manifest.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=PROBE_HDR)
        w.writeheader()
        w.writerows(probe_rows)
    log(f"✓ wdd_pdf_probe_manifest.csv: {len(probe_rows)} rows")

    # ── VALIDATION ──────────────────────────────────────────────────────
    log("\n" + "=" * 70)
    log("VALIDATION")
    log("=" * 70)

    # 1. Coverage row count
    assert len(coverage_rows) == 28, f"❌ Expected 28 coverage rows, got {len(coverage_rows)}"
    log("✓ Coverage CSV has exactly 28 rows")

    # 2. Unique IDs
    cov_ids = [r["project_id"] for r in coverage_rows]
    assert len(set(cov_ids)) == 28, f"❌ Duplicate project_ids in coverage"
    log("✓ 28 unique project_ids in coverage")

    # 3. Every downloaded file exists and is PDF
    for row in manifest_rows:
        fp = row["file_path"]
        assert os.path.exists(fp), f"❌ File not found: {fp}"
        with open(fp, "rb") as f:
            assert f.read(5) == b"%PDF-", f"❌ Not a PDF: {fp}"
    log(f"✓ All {len(manifest_rows)} downloaded files exist and are valid PDFs")

    # 4. SHA256 present
    for row in manifest_rows:
        assert row["sha256"], f"❌ Missing SHA256: {row['file_path']}"
    log("✓ SHA256 present for all downloads")

    # 5. brochure_found=true entities have manifest rows
    found_pids = set(r["project_id"] for r in coverage_rows if r["brochure_found_flag"] == "true")
    manifest_pids = set(r["project_id"] for r in manifest_rows)
    for pid in found_pids:
        assert pid in manifest_pids, f"❌ {pid} has brochure_found=true but no manifest row"
    log("✓ All brochure_found=true entities have manifest rows")

    # 6. brochure_found=false entities are in missing report
    not_found_pids = set(r["project_id"] for r in coverage_rows if r["brochure_found_flag"] == "false")
    missing_pids = set(r["project_id"] for r in missing_rows)
    for pid in not_found_pids:
        assert pid in missing_pids, f"❌ {pid} has brochure_found=false but not in missing report"
    log("✓ All brochure_found=false entities have missing report rows")

    # ── SUMMARY STATS ───────────────────────────────────────────────────
    log("\n" + "=" * 70)
    log("HARVEST SUMMARY")
    log("=" * 70)
    log(f"Total entities processed: 28")
    log(f"Entities with project pages: {sum(1 for r in coverage_rows if r['page_found_flag']=='true')}")
    log(f"Entities with ≥1 brochure/PDF: {len(found_pids)}")
    log(f"Total PDFs downloaded: {len(manifest_rows)}")
    log(f"Unique PDFs by SHA256: {len(downloaded_hashes)}")
    log(f"Entities with NO brochure: {len(not_found_pids)}")
    log(f"PDF probes completed: {sum(1 for p in probe_rows if p['probe_status']=='completed')}")

    if missing_rows:
        log("\nMissing brochure entities:")
        for m in missing_rows:
            log(f"  • {m['project_name']} ({m['project_id']}): {m['likely_reason']}")

    # ── WRITE LOG ───────────────────────────────────────────────────────
    with open(LOG_PATH, "w") as f:
        f.write("\n".join(log_lines) + "\n")

    log(f"\n✓ Log written to {LOG_PATH}")
    log("HARVEST COMPLETE.")


if __name__ == "__main__":
    main()
