#!/usr/bin/env python3
"""
kb_post_patch.py
----------------
Buyer-facing null fallback patch for PulseX-WDD KB.
Idempotent. Safe to rerun.

Step 1: map_link dependency check → RETAIN (referenced in build_kb.py HEADER line 15)
Step 2: Fallback text for approved string fields only
Step 3: Append standard note to disclaimers_json if not present
Step 4: Validate
Step 5: Backup + write both output paths
"""

import csv, json, os, shutil, datetime

ROOT    = '/Volumes/ReserveDisk/codeBase/PulseX-WDD'
KB_IN   = os.path.join(ROOT, 'KB-Acq/outputs/PulseX-WDD_buyerKB.csv')
KB_ENG  = os.path.join(ROOT, 'engine-KB/PulseX-WDD_buyerKB.csv')
BACKUP_DIR = os.path.join(ROOT, 'engine-KB/backups')
TIMESTAMP = datetime.datetime.now().strftime('%Y-%m-%d_%H%M')
TODAY   = '2026-02-25'

os.makedirs(BACKUP_DIR, exist_ok=True)

# ── Field classification (from build_kb.py authoritative HEADER) ──────────────
NUMERIC_COLS = {
    'bedrooms_range_min', 'bedrooms_range_max',
    'bua_range_min_sqm', 'bua_range_max_sqm',
    'starting_price_value', 'starting_price_currency',
    'price_range_min', 'price_range_max',
    'pricing_date',
    'downpayment_percent_min', 'downpayment_percent_max',
    'installment_years_min', 'installment_years_max',
    'delivery_year_min', 'delivery_year_max',
    'confidence_score',
}

BOOLEAN_COLS = {
    'golf_flag', 'beach_access_flag', 'lagoons_flag',
    'clubhouse_flag', 'pools_flag', 'gym_flag',
}

JSON_COLS = {
    'unit_types_offered_json', 'finishing_levels_offered_json',
    'key_amenities_json', 'brochure_urls_json', 'gallery_urls_json',
    'source_links_json', 'screenshot_paths_json', 'disclaimers_json',
    'zones_json', 'unit_templates_json', 'listings_json',
}

# ── Approved string fallbacks ─────────────────────────────────────────────────
FALLBACK_GENERIC = 'Sales Team will assist you'
FALLBACK_PRICING = 'Pricing is available on request. Sales Team will assist you.'
STANDARD_DISCLAIMER = 'Some project details are not publicly disclosed by WDD; Sales Team will assist you.'

# Map: field → fallback text (ONLY if currently empty)
STRING_FALLBACKS = {
    'micro_location':             FALLBACK_GENERIC,
    'project_status':             FALLBACK_GENERIC,
    'developer_inventory_status': FALLBACK_GENERIC,
    'delivery_window':            FALLBACK_GENERIC,
    'map_link':                   FALLBACK_GENERIC,  # retained per dependency check
    'pricing_disclaimer':         FALLBACK_PRICING,  # only fills if empty; existing kept
}

# ── Load ──────────────────────────────────────────────────────────────────────
with open(KB_IN, newline='', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    fieldnames = reader.fieldnames
    rows = list(reader)

n = len(rows)
print(f'Loaded {n} rows, {len(fieldnames)} columns')
print(f'Timestamp: {TIMESTAMP}')

# ── Backup ────────────────────────────────────────────────────────────────────
backup_path = os.path.join(BACKUP_DIR, f'PulseX-WDD_buyerKB_{TIMESTAMP}.csv')
shutil.copy2(KB_IN, backup_path)
print(f'Backup: {backup_path}')

# ── Patch counters ────────────────────────────────────────────────────────────
patch_counts = {f: 0 for f in STRING_FALLBACKS}
disclaimer_appended = 0

# ── Apply patches ─────────────────────────────────────────────────────────────
for row in rows:
    # Step 2: String fallbacks
    for field, fallback in STRING_FALLBACKS.items():
        if field not in row:
            continue
        val = row[field].strip()
        if not val:
            row[field] = fallback
            patch_counts[field] += 1

    # Step 3: disclaimers_json — append standard note if not already present
    disc_raw = row.get('disclaimers_json', '[]').strip()
    try:
        disc_list = json.loads(disc_raw) if disc_raw else []
        if not isinstance(disc_list, list):
            disc_list = [str(disc_list)]
    except:
        disc_list = []

    if STANDARD_DISCLAIMER not in disc_list:
        disc_list.append(STANDARD_DISCLAIMER)
        row['disclaimers_json'] = json.dumps(disc_list, ensure_ascii=False)
        disclaimer_appended += 1

    # last_verified_date touch
    row['last_verified_date'] = TODAY

# ── Step 4: Validate ──────────────────────────────────────────────────────────
errors = []

# Row count
if len(rows) != 28:
    errors.append(f'Row count changed: {len(rows)} (expected 28)')

# Unique project_ids
pids = [r['project_id'] for r in rows]
if len(set(pids)) != 28:
    errors.append(f'Duplicate project_ids detected')

# JSON cols parse
for r in rows:
    for col in JSON_COLS:
        v = r.get(col, '').strip()
        if v and v not in ('null', ''):
            try:
                json.loads(v)
            except Exception as e:
                errors.append(f"{r['project_id']}:{col} INVALID JSON: {e}")

# Numeric cols are still numeric/empty only
for r in rows:
    for col in NUMERIC_COLS:
        v = r.get(col, '').strip()
        if v:
            try:
                float(v)
            except ValueError:
                errors.append(f"{r['project_id']}:{col} CORRUPTED — non-numeric value: '{v}'")

# Boolean cols are still bool/empty only
for r in rows:
    for col in BOOLEAN_COLS:
        v = r.get(col, '').strip().lower()
        if v and v not in ('true', 'false', ''):
            errors.append(f"{r['project_id']}:{col} CORRUPTED — invalid bool value: '{v}'")

if errors:
    print(f'\n❌ VALIDATION FAILED ({len(errors)} errors):')
    for e in errors:
        print(f'  {e}')
    raise SystemExit(1)

print('\n✅ Validation passed')

# ── Step 5: Write ─────────────────────────────────────────────────────────────
for dest in [KB_IN, KB_ENG]:
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    with open(dest, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

# ── Summary ───────────────────────────────────────────────────────────────────
print()
print('=== PATCH SUMMARY ===')
print()
print('Step 1 — map_link: RETAINED')
print('  Reason: referenced in KB-Acq/build_kb.py HEADER line 15 (authoritative schema)')
print('  Action: fallback text "Sales Team will assist you" applied to empty cells')
print()
print('Step 2 — String fallback patches applied:')
for field, count in patch_counts.items():
    if count > 0:
        text = STRING_FALLBACKS[field]
        print(f'  {field:<35} {count:>2} cells patched → "{text}"')
    else:
        print(f'  {field:<35}  0 cells (already populated)')
print()
print(f'Step 3 — disclaimers_json: {disclaimer_appended}/{n} rows had standard note appended')
print()
print('Step 4 — Validation: ✅ PASSED')
print(f'  Rows: {len(rows)}/28')
print(f'  Unique project_ids: {len(set(pids))}/28')
print(f'  JSON cols: all valid')
print(f'  Numeric cols: all numeric/empty')
print(f'  Boolean cols: all true/false/empty')
print()
print('Step 5 — Files written:')
print(f'  ✅ {KB_IN}')
print(f'  ✅ {KB_ENG}')
print(f'  ✅ Backup: {backup_path}')
