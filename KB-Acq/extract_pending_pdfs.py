#!/usr/bin/env python3
"""
extract_pending_pdfs.py
Runs PyMuPDF extraction on all pending brochure PDFs not yet extracted.
Skips already-done projects. Idempotent.
"""
import fitz
import os
import json

BROCHURE_BASE = '/Volumes/ReserveDisk/codeBase/PulseX-WDD/KB-Acq/projectBrochures'
PDF_TEXT_BASE = '/Volumes/ReserveDisk/codeBase/PulseX-WDD/KB-Acq/raw/pdf_text'
INTER_DIR = '/Volumes/ReserveDisk/codeBase/PulseX-WDD/KB-Acq/outputs/intermediate'

pending = [
    ('neo',             'neo/neo__project_brochure__5926f3b9.pdf'),
    ('floating_islands','floating_islands/floating_islands__phase_brochure__75d002bc.pdf'),
    ('neo_lakes',       'neo_lakes/neo_lakes__project_brochure__1bfb1a62.pdf'),
    ('breeze',          'breeze/breeze__phase_brochure__aeaa3281.pdf'),
    ('horizon',         'horizon/horizon__phase_brochure__fb03a146.pdf'),
    ('edge',            'edge/edge__phase_brochure__f80df447.pdf'),
    ('vyon',            'vyon/vyon__phase_brochure__127bb95e.pdf'),
]

results = {}

for proj_id, rel_pdf in pending:
    pdf_path = os.path.join(BROCHURE_BASE, rel_pdf)
    if not os.path.exists(pdf_path):
        print(f'MISSING: {pdf_path}')
        results[proj_id] = {'status': 'missing'}
        continue

    out_dir = os.path.join(PDF_TEXT_BASE, proj_id)
    os.makedirs(out_dir, exist_ok=True)
    out_file = os.path.join(out_dir, 'combined_text.txt')

    if os.path.exists(out_file) and os.path.getsize(out_file) > 100:
        size = os.path.getsize(out_file)
        print(f'SKIP {proj_id} (already done, {size:,} bytes)')
        results[proj_id] = {'status': 'skipped', 'chars': size}
        continue

    doc = fitz.open(pdf_path)
    page_count = doc.page_count
    all_text = []
    for pg in range(page_count):
        page = doc.load_page(pg)
        txt = page.get_text('text')
        if txt.strip():
            all_text.append(f'=== PAGE {pg+1} ===')
            all_text.append(txt)
    doc.close()

    full = '\n'.join(all_text)
    with open(out_file, 'w', encoding='utf-8') as f:
        f.write(full)

    results[proj_id] = {'status': 'done', 'pages': page_count, 'chars': len(full)}
    print(f'DONE {proj_id}: {page_count} pages, {len(full):,} chars -> {out_file}')

# Update checkpoint
chk_path = os.path.join(INTER_DIR, 'wdd_enrichment_checkpoint.json')
with open(chk_path) as f:
    chk = json.load(f)
chk['phase2_pymupdf_pass2'] = results
chk['phase2_pass2_date'] = '2026-02-25'
chk['status'] = 'phase2_pass2_complete'
with open(chk_path, 'w') as f:
    json.dump(chk, f, indent=2)
print(f'\nCheckpoint updated: {chk_path}')
print('\nSummary:')
for pid, r in results.items():
    print(f'  {pid}: {r}')
