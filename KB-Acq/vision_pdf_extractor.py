#!/usr/bin/env python3
"""
vision_pdf_extractor.py
PulseX-WDD — Vision-Mode PDF Full-Text Extractor

Strategy:
  1. Render every PDF page to JPEG at 100 DPI via PyMuPDF (fitz) → ~150-400KB each
     → No poppler/system dependency required
  2. Submit each page image to Azure DocIntel (prebuilt-layout) as raw bytes
     → Bypasses the PDF size limit entirely (images pass easily)
     → DocIntel's Read/Layout model handles image-embedded text well
  3. If DocIntel returns < 30 chars for a page → fallback to Azure OpenAI GPT-4o Vision
     → Sends page as base64 image, asks for full text transcription
  4. Concatenate all page texts → full document text
  5. Write to:
     - KB-Acq/raw/pdf_text/<project_id>/<pdf_hash>.txt   (full raw text)
     - KB-Acq/outputs/intermediate/<project_id>__vision_text.txt  (combined per project)
  6. Dedup by PDF SHA256 — shared brochures processed once

Zero hallucination. All text output is directly from DocIntel/AOAI OCR.
Rendering: PyMuPDF (fitz) — pip install pymupdf

Usage:
  python3 KB-Acq/vision_pdf_extractor.py
"""

import os, sys, json, csv, logging, hashlib, time, base64, io, shutil
from pathlib import Path
from datetime import datetime, timezone

# ─── PATHS ────────────────────────────────────────────────────────────────────
REPO_ROOT  = Path("/Volumes/ReserveDisk/codeBase/PulseX-WDD")
KB_ACQ     = REPO_ROOT / "KB-Acq"
BROCHURES  = KB_ACQ / "projectBrochures"
OUTPUTS    = KB_ACQ / "outputs"
INTER      = OUTPUTS / "intermediate"
PDF_TEXT   = KB_ACQ / "raw" / "pdf_text"   # NEW — raw OCR text per PDF
PAGE_IMGS  = KB_ACQ / "raw" / "pdf_pages"  # NEW — rendered JPEG pages (temp cache)
LOGS       = KB_ACQ / "logs"

for d in [INTER, PDF_TEXT, PAGE_IMGS, LOGS]:
    d.mkdir(parents=True, exist_ok=True)

LOG_PATH = LOGS / "wdd_vision_extract.log"
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%SZ",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(LOG_PATH, encoding="utf-8"),
    ],
)
log = logging.getLogger("vision")
TODAY = datetime.now(timezone.utc).strftime("%Y-%m-%d")

# ─── ENV + CREDENTIALS ────────────────────────────────────────────────────────
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

DI_ENDPOINT = os.environ.get("AZURE_DOCINTEL_ENDPOINT", "").rstrip("/")
DI_KEY      = os.environ.get("AZURE_DOCINTEL_KEY", "")
DI_VERSION  = os.environ.get("AZURE_DOCINTEL_API_VERSION", "2024-11-30")

AOAI_ENDPOINT   = os.environ.get("AZURE_OPENAI_ENDPOINT", "").rstrip("/")
AOAI_KEY        = os.environ.get("AZURE_OPENAI_API_KEY", "")
AOAI_VERSION    = os.environ.get("AZURE_OPENAI_API_VERSION", "2025-01-01-preview")
AOAI_DEPLOYMENT = os.environ.get("AZURE_OPENAI_CHAT_DEPLOYMENT", "gpt-4o")

if not DI_ENDPOINT or not DI_KEY:
    log.error("Azure DocIntel credentials missing — aborting")
    sys.exit(1)
if not AOAI_ENDPOINT or not AOAI_KEY:
    log.warning("Azure OpenAI credentials missing — GPT-4o vision fallback disabled")

log.info("Azure credentials loaded (masked for security)")

# ─── HELPERS ──────────────────────────────────────────────────────────────────
def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()

def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

# ─── PDF → JPEG PAGES (PyMuPDF / fitz) ───────────────────────────────────────
RENDER_DPI   = 100   # 100 DPI → typical page: 794×1123 px → ~150-400KB JPEG
JPEG_QUALITY = 70    # JPEG quality — lower = smaller file for DocIntel
# PyMuPDF matrix: 100 DPI / 72 base DPI ≈ 1.389
_FITZ_MATRIX = None  # lazily initialised

def _get_fitz_matrix():
    global _FITZ_MATRIX
    if _FITZ_MATRIX is None:
        import fitz
        scale = RENDER_DPI / 72.0
        _FITZ_MATRIX = fitz.Matrix(scale, scale)
    return _FITZ_MATRIX

def render_pdf_pages(pdf_path: Path, pdf_hash: str) -> list[Path]:
    """
    Render PDF pages to JPEG at RENDER_DPI using PyMuPDF (fitz).
    Returns list of rendered JPEG paths in page order.
    Cache: skip if already rendered.
    No poppler/system dependency required.
    """
    import fitz
    from PIL import Image
    import io as _io

    page_dir = PAGE_IMGS / pdf_hash
    page_dir.mkdir(parents=True, exist_ok=True)

    # Check if already rendered
    existing = sorted(page_dir.glob("page_*.jpg"))
    if existing:
        log.info(f"  [CACHE] {len(existing)} rendered pages already exist for {pdf_hash[:8]}")
        return existing

    log.info(f"  Rendering PDF pages at {RENDER_DPI} DPI via PyMuPDF: {pdf_path.name}")
    try:
        doc = fitz.open(str(pdf_path))
    except Exception as ex:
        log.error(f"  fitz.open failed: {ex}")
        return []

    matrix = _get_fitz_matrix()
    paths = []
    total = len(doc)
    for i, page in enumerate(doc):
        try:
            pix = page.get_pixmap(matrix=matrix, alpha=False)
            # Convert fitz Pixmap → PIL Image → JPEG bytes
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            out_path = page_dir / f"page_{i+1:04d}.jpg"
            img.save(str(out_path), "JPEG", quality=JPEG_QUALITY)
            size_kb = out_path.stat().st_size // 1024
            paths.append(out_path)
            log.info(f"  Page {i+1}/{total}: {pix.width}x{pix.height}px {size_kb}KB → {out_path.name}")
        except Exception as ex:
            log.warning(f"  Page {i+1} render error: {ex}")

    doc.close()
    log.info(f"  Rendered {len(paths)}/{total} pages for {pdf_path.name}")
    return paths

# ─── AZURE DOCINTEL — IMAGE READ ──────────────────────────────────────────────
import urllib.request, urllib.error

def docintel_read_image(img_bytes: bytes, label: str, retries: int = 2) -> str:
    """
    Submit a single JPEG image to Azure DocIntel prebuilt-read model.
    Returns extracted text string (may be empty for fully graphic pages).
    Supports retries for transient errors.
    """
    # Try 2024-11-30 first with markdown output, fall back to older version
    versions_to_try = [
        (DI_VERSION, "prebuilt-layout", "markdown"),
        ("2023-10-31-preview", "prebuilt-read", None),
    ]

    for api_ver, model, fmt_param in versions_to_try:
        submit_url = (
            f"{DI_ENDPOINT}/documentintelligence/documentModels/{model}:analyze"
            f"?api-version={api_ver}"
        )
        if fmt_param:
            submit_url += f"&outputContentFormat={fmt_param}"

        for attempt in range(retries + 1):
            try:
                req = urllib.request.Request(
                    submit_url,
                    data=img_bytes,
                    method="POST",
                    headers={
                        "Ocp-Apim-Subscription-Key": DI_KEY,
                        "Content-Type": "image/jpeg",
                    },
                )
                resp = urllib.request.urlopen(req, timeout=60)
                op_loc = resp.headers.get("Operation-Location", "")
                if not op_loc:
                    break

                # Poll
                text = _poll_di_text(op_loc, label)
                if text is not None:
                    return text
            except urllib.error.HTTPError as e:
                body = e.read().decode("utf-8", errors="replace")[:300]
                if e.code == 400 and "InvalidContentLength" in body:
                    log.warning(f"  DocIntel: image too large for {label} — trying lower quality")
                    # Compress further
                    from PIL import Image
                    img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
                    buf = io.BytesIO()
                    img.save(buf, "JPEG", quality=40)
                    img_bytes = buf.getvalue()
                    continue
                log.warning(f"  DocIntel HTTP {e.code} for {label}: {body[:100]}")
                break
            except Exception as ex:
                log.warning(f"  DocIntel error for {label}: {ex}")
                break

    return ""  # No text extracted


def _poll_di_text(op_location: str, label: str) -> str | None:
    """Poll DocIntel operation. Returns text string on success, None on failure."""
    for attempt in range(60):
        time.sleep(3)
        try:
            poll_req = urllib.request.Request(
                op_location,
                headers={"Ocp-Apim-Subscription-Key": DI_KEY},
            )
            resp = urllib.request.urlopen(poll_req, timeout=60)
            result = json.loads(resp.read())
        except Exception as ex:
            log.warning(f"  Poll {attempt+1} failed: {ex}")
            continue

        status = result.get("status", "")
        if status == "succeeded":
            # Try markdown content first (layout model)
            content = result.get("analyzeResult", {}).get("content", "")
            if not content:
                # Try read model page lines
                pages = result.get("analyzeResult", {}).get("pages", [])
                lines = []
                for pg in pages:
                    for line in pg.get("lines", []):
                        lines.append(line.get("content", ""))
                content = "\n".join(lines)
            return content
        elif status in ("failed", "canceled"):
            log.warning(f"  DocIntel {status} for {label}: {result.get('error', {})}")
            return None
        elif attempt % 5 == 0:
            log.info(f"  ... polling {label} ({attempt*3}s, status={status})")

    log.warning(f"  DocIntel timed out for {label}")
    return None

# ─── AZURE OPENAI — GPT-4o VISION FALLBACK ────────────────────────────────────
def aoai_vision_transcribe(img_bytes: bytes, label: str, page_num: int, pdf_name: str) -> str:
    """
    Use GPT-4o vision to transcribe text from a page image.
    Only called as fallback when DocIntel returns < 30 chars.
    """
    if not AOAI_ENDPOINT or not AOAI_KEY:
        return ""

    b64_img = base64.b64encode(img_bytes).decode("utf-8")

    url = (
        f"{AOAI_ENDPOINT}/openai/deployments/{AOAI_DEPLOYMENT}/chat/completions"
        f"?api-version={AOAI_VERSION}"
    )

    prompt = (
        f"This is page {page_num} of a real estate brochure for '{pdf_name}'.\n"
        "TASK: Extract and transcribe ALL visible text from this page EXACTLY as it appears.\n"
        "Include:\n"
        "- All headings, body text, captions, labels, callouts\n"
        "- All numbers, measurements (sqm, m2, BR, bedrooms, EGP, %, years)\n"
        "- All table content (row by row)\n"
        "- Payment plan details if visible\n"
        "- Delivery/handover dates if visible\n"
        "- Unit type names and specifications\n"
        "- Amenity lists\n"
        "- Contact info\n\n"
        "RULES:\n"
        "- DO NOT summarize, interpret, or add any information not on the page\n"
        "- DO NOT invent numbers or specs\n"
        "- If a section is unclear, transcribe as-is with [unclear] marker\n"
        "- If there is literally no readable text (purely decorative), respond with: [NO TEXT]\n\n"
        "Respond with ONLY the transcribed text, nothing else."
    )

    payload = json.dumps({
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{b64_img}",
                            "detail": "high"
                        }
                    }
                ]
            }
        ],
        "max_tokens": 2000,
        "temperature": 0,
    }).encode("utf-8")

    try:
        req = urllib.request.Request(
            url, data=payload, method="POST",
            headers={
                "api-key": AOAI_KEY,
                "Content-Type": "application/json",
            }
        )
        resp = urllib.request.urlopen(req, timeout=90)
        result = json.loads(resp.read())
        text = result["choices"][0]["message"]["content"].strip()
        if text == "[NO TEXT]":
            return ""
        log.info(f"  GPT-4o vision: {len(text)} chars for {label}")
        return text
    except Exception as ex:
        log.warning(f"  GPT-4o vision failed for {label}: {ex}")
        return ""

# ─── PROCESS SINGLE PDF ───────────────────────────────────────────────────────
DOCINTEL_MIN_CHARS = 30  # If DocIntel gets fewer than this, use vision fallback
MAGAZINE_SHA256    = "48944a0807f98a08329b36de54001e59e8e54d5995918912823658517a7f58a8"

def process_pdf(pdf_path: Path, project_id: str, source_url: str = "") -> dict:
    """
    Full extraction pipeline for one PDF.
    Returns: {project_id, pdf_name, pdf_hash, page_count, full_text, page_texts, pages_via_docintel, pages_via_aoai}
    """
    pdf_name = pdf_path.name
    pdf_hash = sha256_file(pdf_path)[:16]
    pdf_hash_full = sha256_file(pdf_path)

    # Check if this is the generic WDD Magazine
    if pdf_hash_full == MAGAZINE_SHA256:
        log.info(f"  ⊘ Skipping WDD Magazine (generic, project-non-specific)")
        return {"skipped": True, "reason": "generic_magazine"}

    # Output text file path
    text_dir = PDF_TEXT / project_id
    text_dir.mkdir(parents=True, exist_ok=True)
    text_file = text_dir / f"{pdf_hash}.txt"
    manifest_file = text_dir / f"{pdf_hash}_manifest.json"

    # Check if already fully processed
    if text_file.exists() and manifest_file.exists():
        with open(manifest_file) as f:
            existing = json.load(f)
        log.info(f"  [CACHE HIT] Already processed: {pdf_name} ({existing.get('page_count', '?')} pages, {existing.get('total_chars', '?')} chars)")
        with open(text_file, encoding="utf-8") as f:
            full_text = f.read()
        existing["full_text"] = full_text
        return existing

    log.info(f"\n  ══ Processing: {pdf_name} ({pdf_path.stat().st_size // 1024}KB) ══")
    log.info(f"  SHA256: {pdf_hash_full[:32]}...")

    # Step 1: Render pages
    page_paths = render_pdf_pages(pdf_path, pdf_hash_full[:16])
    if not page_paths:
        log.error(f"  Failed to render pages for {pdf_name}")
        return {"skipped": True, "reason": "render_failed"}

    # Step 2: Extract text per page
    page_texts = []
    pages_via_di = 0
    pages_via_aoai = 0
    pages_no_text = 0

    for i, page_path in enumerate(page_paths):
        page_num = i + 1
        label = f"{pdf_name} p{page_num}/{len(page_paths)}"
        log.info(f"  Page {page_num}/{len(page_paths)}...")

        # Read JPEG bytes
        img_bytes = page_path.read_bytes()
        img_size_kb = len(img_bytes) // 1024

        # DocIntel read
        di_text = docintel_read_image(img_bytes, label)
        di_chars = len(di_text.strip())

        if di_chars >= DOCINTEL_MIN_CHARS:
            page_texts.append(f"--- PAGE {page_num} [DocIntel] ---\n{di_text.strip()}")
            pages_via_di += 1
            log.info(f"  ✓ DocIntel: {di_chars} chars")
        else:
            # GPT-4o vision fallback
            log.info(f"  DocIntel returned {di_chars} chars → GPT-4o vision fallback")
            # Compress image for GPT-4o (high detail mode needs reasonable size)
            from PIL import Image
            img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
            buf = io.BytesIO()
            img.save(buf, "JPEG", quality=75)
            compressed = buf.getvalue()

            gpt_text = aoai_vision_transcribe(compressed, label, page_num, pdf_name)
            gpt_chars = len(gpt_text.strip())

            if gpt_chars > 0:
                page_texts.append(f"--- PAGE {page_num} [AOAI-Vision] ---\n{gpt_text.strip()}")
                pages_via_aoai += 1
                log.info(f"  ✓ GPT-4o vision: {gpt_chars} chars")
            else:
                page_texts.append(f"--- PAGE {page_num} [NO TEXT EXTRACTED] ---")
                pages_no_text += 1
                log.info(f"  ○ No text on page {page_num}")

        # Small delay to avoid rate limiting
        time.sleep(0.5)

    # Step 3: Combine into full document text
    full_text = "\n\n".join(page_texts)
    total_chars = len(full_text)

    # Step 4: Write outputs
    with open(text_file, "w", encoding="utf-8") as f:
        f.write(f"# PulseX-WDD Vision Extraction\n")
        f.write(f"# Project: {project_id}\n")
        f.write(f"# PDF: {pdf_name}\n")
        f.write(f"# Pages: {len(page_paths)}\n")
        f.write(f"# Extracted: {TODAY}\n")
        f.write(f"# Source URL: {source_url}\n")
        f.write(f"# DocIntel pages: {pages_via_di} | GPT-4o pages: {pages_via_aoai} | No-text: {pages_no_text}\n")
        f.write(f"# Total chars: {total_chars}\n")
        f.write("=" * 80 + "\n\n")
        f.write(full_text)

    manifest = {
        "project_id": project_id,
        "pdf_name": pdf_name,
        "pdf_hash": pdf_hash,
        "pdf_hash_full": pdf_hash_full,
        "source_url": source_url,
        "page_count": len(page_paths),
        "pages_via_docintel": pages_via_di,
        "pages_via_aoai": pages_via_aoai,
        "pages_no_text": pages_no_text,
        "total_chars": total_chars,
        "text_file": str(text_file),
        "extracted_date": TODAY,
    }
    with open(manifest_file, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    manifest["full_text"] = full_text
    log.info(f"  ✔ Done: {len(page_paths)} pages, {total_chars} chars saved → {text_file.name}")
    log.info(f"  (DocIntel: {pages_via_di}, GPT-4o: {pages_via_aoai}, No-text: {pages_no_text})")

    return manifest

# ─── WRITE COMBINED TEXT PER PROJECT ─────────────────────────────────────────
def write_combined_project_text(project_id: str, pdf_results: list[dict]):
    """Write combined text from all PDFs for a project to intermediate/."""
    combined_parts = []
    for res in pdf_results:
        if res.get("skipped"):
            continue
        combined_parts.append(
            f"{'='*60}\n"
            f"PDF: {res.get('pdf_name', 'unknown')}\n"
            f"Pages: {res.get('page_count', '?')} | Chars: {res.get('total_chars', '?')}\n"
            f"{'='*60}\n\n"
            f"{res.get('full_text', '')}"
        )

    if not combined_parts:
        return None

    out_path = INTER / f"{project_id}__vision_text.txt"
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(f"# PulseX-WDD Combined Vision Text\n")
        f.write(f"# Project: {project_id}\n")
        f.write(f"# Generated: {TODAY}\n")
        f.write(f"# PDF count: {len(combined_parts)}\n\n")
        f.write("\n\n".join(combined_parts))

    log.info(f"  Combined text written: {out_path.name} ({out_path.stat().st_size // 1024}KB)")
    return str(out_path)

# ─── MAIN: PROCESS ALL PROJECTS ──────────────────────────────────────────────
def main():
    log.info("=" * 70)
    log.info("PulseX-WDD — Vision PDF Full-Text Extractor")
    log.info(f"Run date: {TODAY}")
    log.info("=" * 70)

    # Load brochure manifest
    manifest_path = OUTPUTS / "wdd_brochures_manifest.csv"
    if not manifest_path.exists():
        log.error(f"Manifest not found: {manifest_path}")
        sys.exit(1)

    with open(manifest_path, newline="", encoding="utf-8") as f:
        manifest_rows = list(csv.DictReader(f))

    # Group by project_id, deduplicate PDFs by sha256
    projects: dict[str, list[dict]] = {}
    seen_hashes: set[str] = set()
    dedup_map: dict[str, str] = {}  # sha256 → project_id that processed it

    for row in manifest_rows:
        pid = row["project_id"]
        sha = row.get("sha256", "")
        pdf_path = Path(row.get("file_path", ""))
        is_dupe = bool(row.get("notes", "").startswith("Duplicate"))

        if pid not in projects:
            projects[pid] = []

        projects[pid].append({
            "pdf_path": pdf_path,
            "sha256": sha,
            "source_url": row.get("source_url", ""),
            "doc_type": row.get("doc_type", ""),
            "is_dupe": is_dupe,
        })

    log.info(f"Found {len(projects)} projects in manifest")

    # Process each project
    all_results = {}
    processed_sha = {}  # sha256 → result (for dedup)

    for project_id in sorted(projects.keys()):
        pdfs = projects[project_id]
        log.info(f"\n{'─'*60}")
        log.info(f"── PROJECT: {project_id} ({len(pdfs)} PDFs)")

        project_results = []

        for pdf_info in pdfs:
            pdf_path = pdf_info["pdf_path"]
            sha      = pdf_info["sha256"]
            src_url  = pdf_info["source_url"]

            if not pdf_path.exists():
                log.warning(f"  PDF not found: {pdf_path}")
                project_results.append({"skipped": True, "reason": "file_not_found"})
                continue

            # Dedup: if this SHA was processed for another project, reuse text
            if sha in processed_sha:
                log.info(f"  ↔  Shared PDF (SHA={sha[:8]}) — copying text from {processed_sha[sha]['project_id']}")
                # Copy text file to this project's dir
                src_text = Path(processed_sha[sha].get("text_file", ""))
                if src_text.exists():
                    dst_dir = PDF_TEXT / project_id
                    dst_dir.mkdir(parents=True, exist_ok=True)
                    dst_text = dst_dir / src_text.name
                    if not dst_text.exists():
                        shutil.copy2(src_text, dst_text)
                    cached = dict(processed_sha[sha])
                    cached["project_id"] = project_id
                    with open(src_text, encoding="utf-8") as f:
                        cached["full_text"] = f.read()
                    project_results.append(cached)
                else:
                    project_results.append({"skipped": True, "reason": "shared_source_missing"})
                continue

            # Check magazine
            if sha == MAGAZINE_SHA256:
                log.info(f"  ⊘ Skipping WDD Magazine")
                project_results.append({"skipped": True, "reason": "generic_magazine"})
                continue

            # Process this PDF
            result = process_pdf(pdf_path, project_id, src_url)

            if not result.get("skipped"):
                processed_sha[sha] = result

            project_results.append(result)

        # Write combined text for this project
        combined_path = write_combined_project_text(project_id, project_results)
        all_results[project_id] = {
            "pdfs": project_results,
            "combined_text_path": combined_path,
        }

    # Summary
    log.info("\n" + "=" * 70)
    log.info("EXTRACTION SUMMARY")
    log.info("=" * 70)
    processed_count = sum(
        1 for pid, r in all_results.items()
        if any(not p.get("skipped") for p in r["pdfs"])
    )
    total_chars = sum(
        p.get("total_chars", 0)
        for r in all_results.values()
        for p in r["pdfs"]
        if not p.get("skipped")
    )
    log.info(f"Projects with extracted text: {processed_count}/{len(all_results)}")
    log.info(f"Total characters extracted:   {total_chars:,}")

    for pid, r in sorted(all_results.items()):
        pdfs = r["pdfs"]
        success = [p for p in pdfs if not p.get("skipped")]
        skip = [p for p in pdfs if p.get("skipped")]
        chars = sum(p.get("total_chars", 0) for p in success)
        log.info(f"  {pid}: {len(success)} PDFs → {chars:,} chars  (skipped: {len(skip)})")

    # Write session manifest
    session = {
        "run_date": TODAY,
        "projects_processed": processed_count,
        "total_chars": total_chars,
        "per_project": {
            pid: {
                "combined_text_path": r["combined_text_path"],
                "pdf_count": len([p for p in r["pdfs"] if not p.get("skipped")]),
                "total_chars": sum(p.get("total_chars", 0) for p in r["pdfs"] if not p.get("skipped")),
            }
            for pid, r in all_results.items()
        }
    }
    session_path = INTER / "wdd_vision_session.json"
    with open(session_path, "w", encoding="utf-8") as f:
        json.dump(session, f, indent=2)
    log.info(f"\nSession manifest: {session_path}")
    log.info("Vision extraction complete. Next: run aoai_field_mapper.py")

if __name__ == "__main__":
    main()
