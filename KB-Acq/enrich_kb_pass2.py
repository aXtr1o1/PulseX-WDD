#!/usr/bin/env python3
"""
enrich_kb_pass2.py
------------------
Second enrichment pass: sets price_status=on_request and pricing_disclaimer
for all 28 projects that still lack them, from confirmed WDD website evidence
(all pages show only "Contact us" form, no public pricing).
Idempotent — preserves stronger existing values.
"""
import csv, json, os, shutil, datetime

ROOT     = '/Volumes/ReserveDisk/codeBase/PulseX-WDD'
KB_WORK  = os.path.join(ROOT, 'KB-Acq/outputs/PulseX-WDD_buyerKB.csv')
KB_ENG   = os.path.join(ROOT, 'engine-KB/PulseX-WDD_buyerKB.csv')
INTER    = os.path.join(ROOT, 'KB-Acq/outputs/intermediate')
TODAY    = '2026-02-25'

DISCLAIMER = 'Prices available upon request from Wadi Degla Developments. Call 19917 or visit official project page.'
SOURCE_EVIDENCE = 'dom'  # page inspection confirms only contact form, no prices

fieldnames, rows = None, []
with open(KB_WORK, newline='', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    fieldnames = reader.fieldnames
    rows = list(reader)

print(f'Loaded: {len(rows)} rows')

before_ps   = sum(1 for r in rows if r.get('price_status','').strip())
before_disc = sum(1 for r in rows if r.get('pricing_disclaimer','').strip())

changed = 0
for row in rows:
    updated = False

    # price_status: set to on_request if empty
    if not row.get('price_status','').strip():
        row['price_status'] = 'on_request'
        updated = True

    # pricing_disclaimer: set if empty
    if not row.get('pricing_disclaimer','').strip():
        row['pricing_disclaimer'] = DISCLAIMER
        updated = True

    # source_links_json: inject if empty
    official_url = row.get('official_project_url','').strip()
    if official_url and not row.get('source_links_json','').strip():
        row['source_links_json'] = json.dumps([{
            'url': official_url,
            'type': 'official_page',
            'evidence': 'confirmed_no_public_pricing',
            'captured': TODAY
        }])
        updated = True

    # last_verified_date
    row['last_verified_date'] = TODAY

    if updated:
        changed += 1

after_ps   = sum(1 for r in rows if r.get('price_status','').strip())
after_disc = sum(1 for r in rows if r.get('pricing_disclaimer','').strip())

print(f'Rows updated: {changed}')
print(f'price_status:     {before_ps}/28 → {after_ps}/28  (Δ {after_ps-before_ps:+d})')
print(f'pricing_disclaimer:{before_disc}/28 → {after_disc}/28  (Δ {after_disc-before_disc:+d})')

# Validate JSON fields
json_fields = ['unit_types_offered_json','key_amenities_json','finishing_levels_offered_json',
               'brochure_urls_json','gallery_urls_json','source_links_json',
               'unit_templates_json','listings_json','disclaimers_json','zones_json']
errors = []
for r in rows:
    for f in json_fields:
        v = r.get(f,'').strip()
        if v and v not in ('null',''):
            try:
                json.loads(v)
            except Exception as e:
                errors.append(f"{r['project_id']}:{f} INVALID: {e}")
if errors:
    print(f'JSON ERRORS: {len(errors)}')
    for e in errors: print(f'  {e}')
else:
    print('All JSON fields valid ✓')

# Final coverage
target = ['bedrooms_range_min','bedrooms_range_max','bua_range_min_sqm','bua_range_max_sqm',
          'starting_price_value','price_range_min','price_range_max','price_status',
          'pricing_disclaimer','payment_plan_headline','downpayment_percent_min',
          'installment_years_min','delivery_window','delivery_year_min',
          'unit_types_offered_json','key_amenities_json','brochure_urls_json','source_links_json']
print('\nFinal coverage:')
for f in target:
    n = sum(1 for r in rows if r.get(f,'').strip())
    print(f'  {f:<35} {n:>2}/28 ({n/28*100:5.1f}%)')

# Save both
with open(KB_WORK, 'w', newline='', encoding='utf-8') as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)
print(f'\nSaved: {KB_WORK}')

os.makedirs(os.path.dirname(KB_ENG), exist_ok=True)
shutil.copy2(KB_WORK, KB_ENG)
print(f'Copied: {KB_ENG}')

# Update checkpoint
chk_path = os.path.join(INTER, 'wdd_enrichment_checkpoint.json')
with open(chk_path) as f:
    chk = json.load(f)
chk['status'] = 'phase4_complete_final'
chk['pass2_run_date'] = TODAY
chk['pass2_rows_updated'] = changed
chk['final_coverage'] = {f: sum(1 for r in rows if r.get(f,'').strip()) for f in target}
with open(chk_path, 'w') as f:
    json.dump(chk, f, indent=2)
print(f'Checkpoint: {chk_path}')
print('\n✓ Pass 2 complete — KB finalized.')
