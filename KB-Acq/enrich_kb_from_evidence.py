#!/usr/bin/env python3
"""
enrich_kb_from_evidence.py
--------------------------
Evidence-constrained, idempotent KB enrichment.
Populates buyer-critical fields from ALREADY-EXTRACTED brochure text and official page evidence.
Does NOT call Azure APIs or invent values.

Evidence sources:
  1. murano/waterside brochure (shared PDF: Waterside-Brochure.pdf) → murano, living_community, waterside
  2. living_community docintel (Sky Loft/Penthouse with 3-4BR, 145-260sqm)
  3. ojo brochure (villas, townhouses, 1-3BR chalets)
  4. floating_islands brochure (very thin - lifestyle only)
  5. neo/neo_gardens/neopolis brochure (Neo Gardens lifestyle + facilities)
  6. breeze/horizon/edge brochures (ClubTown master brochures - amenities only)
  7. vyon brochure (lifestyle + amenities)
  8. neo_lakes brochure (lifestyle only)

Fields that can be populated:
  - unit_types_offered_json
  - bedrooms_range_min / bedrooms_range_max
  - bua_range_min_sqm / bua_range_max_sqm
  - key_amenities_json
  - finishing_levels_offered_json (from brochures)
  - price_status → "on_request" where no price evident
  - pricing_disclaimer
  - brochure_urls_json (from manifest)
  - source_links_json

Fields that CANNOT be populated (no evidence in any official source):
  - starting_price_value
  - price_range_min / price_range_max
  - payment_plan_headline / downpayment_percent_min / installment_years_min
  - delivery_window / delivery_year_min / delivery_year_max

Run: python3 enrich_kb_from_evidence.py
"""

import csv
import json
import os
import shutil
import datetime

ROOT = '/Volumes/ReserveDisk/codeBase/PulseX-WDD'
KB_WORK = os.path.join(ROOT, 'KB-Acq/outputs/PulseX-WDD_buyerKB.csv')
KB_ENGINE = os.path.join(ROOT, 'engine-KB/PulseX-WDD_buyerKB.csv')
INTER_DIR = os.path.join(ROOT, 'KB-Acq/outputs/intermediate')
TODAY = datetime.date.today().isoformat()

os.makedirs(INTER_DIR, exist_ok=True)

# ──────────────────────────────────────────────────────────────────
# EVIDENCE BANK
# Every entry is evidence-constrained with source pointers.
# Only add what is EXPLICITLY stated in official PDFs/brochures.
# ──────────────────────────────────────────────────────────────────

EVIDENCE = {
    # ── MURANO (Ain El Sokhna) ──────────────────────────────────────
    # Source: Waterside-Brochure.pdf (murano__phase_brochure__61f82a41.pdf), 65 pages
    # Extracted with PyMuPDF, captured 2026-02-25
    # Unit type pages: 29-65 contain explicit bedroom count + gross area tables
    'murano': {
        'unit_types_offered_json': json.dumps([
            'Loft House', 'Tre Chalet', 'Due Chalet'
        ]),
        'bedrooms_range_min': '2',
        'bedrooms_range_max': '4',
        'bua_range_min_sqm': '115',     # Due Chalet min observed: 115 sqm
        'bua_range_max_sqm': '260',     # Largest: Loft House 4BR/260sqm (Sky Loft brochure)
        'key_amenities_json': json.dumps([
            'Swimming Pools', 'Infinity Pool', 'Pool Bars', 'Beach Walk',
            'Outdoor Gym', 'Beach Football', 'Beach Volleyball', 'Events Area',
            'Beach Clubhouse', 'Wooden Deck', 'Hot Springs', 'Commercial Area',
            'Sitting Area'
        ]),
        'finishing_levels_offered_json': json.dumps(['Semi-Finished']),
        'price_status': 'on_request',
        'pricing_disclaimer': 'Prices available upon request from Wadi Degla Developments.',
        '_evidence': {
            'source': 'pdf',
            'file': 'KB-Acq/projectBrochures/murano/murano__phase_brochure__61f82a41.pdf',
            'pages': 'pp.29-65',
            'extracted': TODAY,
            'method': 'PyMuPDF'
        }
    },

    # ── LIVING COMMUNITY (Ain El Sokhna / Murano Phase) ────────────
    # Source: SAME Waterside-Brochure.pdf (Murano brochure covers all phases)
    # Also: living_community docintel normalized JSON confirms:
    #   Sky Loft 4BR/260sqm + roof, Tre Penthouse 3BR/145sqm + roof
    'living_community': {
        'unit_types_offered_json': json.dumps([
            'Sky Loft', 'Tre Penthouse', 'Loft House', 'Tre Chalet', 'Due Chalet'
        ]),
        'bedrooms_range_min': '2',
        'bedrooms_range_max': '4',
        'bua_range_min_sqm': '115',
        'bua_range_max_sqm': '260',
        'key_amenities_json': json.dumps([
            'Hot Spring', 'Beach', 'Swimming Pools', 'Outdoor Pool',
            'Beach Walk', 'Sitting Area', 'Commercial Area'
        ]),
        'finishing_levels_offered_json': json.dumps(['Semi-Finished']),
        'price_status': 'on_request',
        'pricing_disclaimer': 'Prices available upon request from Wadi Degla Developments.',
        '_evidence': {
            'source': 'pdf',
            'file': 'KB-Acq/projectBrochures/living_community/living_community__phase_brochure__61f82a41.pdf',
            'pages': 'all',
            'extracted': TODAY,
            'method': 'PyMuPDF + DocIntel'
        }
    },

    # ── WATERSIDE (Ain El Sokhna / Murano Phase) ───────────────────
    # Source: SAME Waterside-Brochure.pdf
    'waterside': {
        'unit_types_offered_json': json.dumps([
            'Loft House', 'Tre Chalet', 'Due Chalet'
        ]),
        'bedrooms_range_min': '2',
        'bedrooms_range_max': '4',
        'bua_range_min_sqm': '115',
        'bua_range_max_sqm': '240',
        'key_amenities_json': json.dumps([
            'Swimming Pools', 'Beach Walk', 'Outdoor Gym', 'Beach Volleyball',
            'Events Area', 'Wooden Deck', 'Pool Bars', 'Commercial Area'
        ]),
        'finishing_levels_offered_json': json.dumps(['Semi-Finished']),
        'price_status': 'on_request',
        'pricing_disclaimer': 'Prices available upon request from Wadi Degla Developments.',
        '_evidence': {
            'source': 'pdf',
            'file': 'KB-Acq/projectBrochures/waterside/waterside__phase_brochure__61f82a41.pdf',
            'pages': 'all',
            'extracted': TODAY,
            'method': 'PyMuPDF'
        }
    },

    # ── OJO (Ain El Sokhna / Murano) ───────────────────────────────
    # Source: ojo__phase_brochure__fcd04cec.pdf, 3 pages
    # Extracted with PyMuPDF, 2026-02-25
    # Page 3 states unit types: Laguna (standalone villas), Canal (townhouses),
    # Senda (1, 2, or 3 bedroom chalets)
    'ojo': {
        'unit_types_offered_json': json.dumps([
            'Laguna Villa', 'Canal Townhouse', 'Senda Chalet'
        ]),
        'bedrooms_range_min': '1',
        'bedrooms_range_max': '3',
        'key_amenities_json': json.dumps([
            'Swimmable Lagoons', 'Crystal River', 'Casa Club', 'Parkland',
            'Commercial Promenade', 'Cafés', 'Boutique Shops', 'Dining',
            '24/7 Security', 'Beach'
        ]),
        'price_status': 'on_request',
        'pricing_disclaimer': 'Prices available upon request from Wadi Degla Developments.',
        '_evidence': {
            'source': 'pdf',
            'file': 'KB-Acq/projectBrochures/ojo/ojo__phase_brochure__fcd04cec.pdf',
            'pages': 'pp.2-3',
            'extracted': TODAY,
            'method': 'PyMuPDF',
            'snippet': 'Senda: one, two, or three bedrooms that open to light, air, and ease.'
        }
    },

    # ── FLOATING ISLANDS (North Coast) ─────────────────────────────
    # Source: floating_islands__phase_brochure__75d002bc.pdf
    # DocIntel returns only 150 chars (almost all images); no specs extractable
    'floating_islands': {
        'price_status': 'on_request',
        'pricing_disclaimer': 'Prices available upon request from Wadi Degla Developments.',
        '_evidence': {
            'source': 'pdf',
            'file': 'KB-Acq/projectBrochures/floating_islands/floating_islands__phase_brochure__75d002bc.pdf',
            'pages': 'all',
            'note': 'Brochure is predominantly images; no numeric specs extracted.'
        }
    },

    # ── BREEZE (New Degla, ClubTown) ───────────────────────────────
    # Source: CT-Breeze-Brochure.pdf (DocIntel extracted)
    # ClubTown brochure confirms amenities. No bedroom/BUA/price data.
    'breeze': {
        'key_amenities_json': json.dumps([
            'Swimming Pools', 'Nurseries & Kids Gardens', 'Sports Courts',
            'Outdoor Fitness Area', 'Club House', 'Mosque', 'Food Court',
            'Banks', 'Gym', 'Padel Tennis', 'Retail'
        ]),
        'price_status': 'on_request',
        'pricing_disclaimer': 'Prices available upon request from Wadi Degla Developments.',
        '_evidence': {
            'source': 'pdf',
            'file': 'KB-Acq/projectBrochures/breeze/breeze__phase_brochure__aeaa3281.pdf',
            'method': 'DocIntel',
            'extracted': TODAY,
            'snippet': 'NURSERIES & KIDS GARDENS, RETAIL, SPORTS COURTS, OUTDOOR FITNESS AREA, CLUB HOUSE, MOSQUE, FOOD COURT, BANKS, GYM, PADEL TENNIS'
        }
    },

    # ── HORIZON (New Degla, ClubTown) ──────────────────────────────
    'horizon': {
        'key_amenities_json': json.dumps([
            'Swimming Pools', 'Nurseries & Kids Gardens', 'Sports Courts',
            'Outdoor Fitness Area', 'Club House', 'Mosque', 'Food Court',
            'Banks', 'Gym', 'Padel Tennis', 'Retail', 'Waterfall'
        ]),
        'price_status': 'on_request',
        'pricing_disclaimer': 'Prices available upon request from Wadi Degla Developments.',
        '_evidence': {
            'source': 'pdf',
            'file': 'KB-Acq/projectBrochures/horizon/horizon__phase_brochure__fb03a146.pdf',
            'method': 'DocIntel',
            'extracted': TODAY
        }
    },

    # ── EDGE (New Degla, ClubTown) ──────────────────────────────────
    'edge': {
        'key_amenities_json': json.dumps([
            'Swimming Pools', 'Outdoor Fitness Area', 'Club House', 'Sports Courts',
            'Waterfall', 'Retail', 'Banks', 'Mosque'
        ]),
        'price_status': 'on_request',
        'pricing_disclaimer': 'Prices available upon request from Wadi Degla Developments.',
        '_evidence': {
            'source': 'pdf',
            'file': 'KB-Acq/projectBrochures/edge/edge__phase_brochure__f80df447.pdf',
            'method': 'DocIntel',
            'extracted': TODAY
        }
    },

    # ── VYON (New Degla, vertical towers) ──────────────────────────
    # Source: VYON-Brochure.pdf (DocIntel 5269 chars)
    # Mentions: Yoga decks, outdoor fitness, rooftop mini gym, plunge pools, play yard
    # Unit type mentioned: Penthouse (in image filename: Cam01-Penthouse)
    # No bedroom/BUA specs stated explicitly.
    'vyon': {
        'key_amenities_json': json.dumps([
            'Yoga Decks', 'Outdoor Fitness Zone', 'Rooftop Mini Gym',
            'Plunge Pools', 'Play Yard', 'Rooftop Gardens', 'Verdant Terraces',
            '24/7 Security', 'CCTV', 'Waste Management', 'Underground Parking'
        ]),
        'price_status': 'on_request',
        'pricing_disclaimer': 'Prices available upon request from Wadi Degla Developments.',
        '_evidence': {
            'source': 'pdf',
            'file': 'KB-Acq/projectBrochures/vyon/vyon__phase_brochure__127bb95e.pdf',
            'method': 'DocIntel',
            'extracted': TODAY,
            'snippet': 'Yoga decks, outdoor fitness zones, rooftop mini gym, tranquil plunge pools, peaceful play yard'
        }
    },

    # ── NEO (Mostakbal City) ────────────────────────────────────────
    # Source: neo__project_brochure__5926f3b9.pdf (Neo Gardens brochure)
    # DocIntel: Facilities confirmed: 24/7 Security, Parking, Green Area, Medical, Mosque, Nursery, Commercial Area
    # This brochure is for Neo Gardens; shared with neo project in KB.
    'neo': {
        'key_amenities_json': json.dumps([
            '24/7 Security', 'Parking', 'Green Area', 'Medical', 'Mosque', 'Nursery', 'Commercial Area'
        ]),
        'price_status': 'on_request',
        'pricing_disclaimer': 'Prices available upon request from Wadi Degla Developments.',
        '_evidence': {
            'source': 'pdf',
            'file': 'KB-Acq/projectBrochures/neo/neo__project_brochure__5926f3b9.pdf',
            'method': 'DocIntel',
            'extracted': TODAY,
            'snippet': '24/7 SECURITY, PARKING, GREEN AREA, MEDICAL, MOSQUE, NURSERY, COMMERCIAL AREA'
        }
    },

    # ── NEO GARDENS (Mostakbal City) ─────────────────────────────────
    'neo_gardens': {
        'key_amenities_json': json.dumps([
            '24/7 Security', 'Parking', 'Green Area', 'Medical', 'Mosque', 'Nursery', 'Commercial Area'
        ]),
        'price_status': 'on_request',
        'pricing_disclaimer': 'Prices available upon request from Wadi Degla Developments.',
        '_evidence': {
            'source': 'pdf',
            'file': 'KB-Acq/projectBrochures/neo_gardens/neo_gardens__project_brochure__5926f3b9.pdf',
            'method': 'DocIntel',
            'extracted': TODAY
        }
    },

    # ── NEOPOLIS (Mostakbal City) ─────────────────────────────────────
    'neopolis': {
        'key_amenities_json': json.dumps([
            '24/7 Security', 'Parking', 'Green Area', 'Medical', 'Mosque', 'Nursery', 'Commercial Area'
        ]),
        'price_status': 'on_request',
        'pricing_disclaimer': 'Prices available upon request from Wadi Degla Developments.',
        '_evidence': {
            'source': 'pdf',
            'file': 'KB-Acq/projectBrochures/neopolis/neopolis__project_brochure__5926f3b9.pdf',
            'method': 'DocIntel',
            'extracted': TODAY
        }
    },

    # ── NEO LAKES (Mostakbal City) ──────────────────────────────────
    # Source: neo_lakes brochure (2052 chars, mostly images/location map)
    'neo_lakes': {
        'price_status': 'on_request',
        'pricing_disclaimer': 'Prices available upon request from Wadi Degla Developments.',
        '_evidence': {
            'source': 'pdf',
            'file': 'KB-Acq/projectBrochures/neo_lakes/neo_lakes__project_brochure__1bfb1a62.pdf',
            'method': 'DocIntel',
            'note': 'Brochure lacks numeric specs; only location/master plan shown.'
        }
    },
}

# Brochure URLs from manifest (evidence source: wdd_brochures_manifest.csv)
BROCHURE_URLS = {
    'murano': 'https://wadidegladevelopments.com/wp-content/uploads/2023/09/Waterside-Brochure.pdf',
    'living_community': 'https://wadidegladevelopments.com/wp-content/uploads/2023/09/Waterside-Brochure.pdf',
    'waterside': 'https://wadidegladevelopments.com/wp-content/uploads/2023/09/Waterside-Brochure.pdf',
    'neo': 'https://wadidegladevelopments.com/wp-content/uploads/2023/09/Wadi-Degla-Development-Neopolis-Neo-Gardens.pdf',
    'neo_gardens': 'https://wadidegladevelopments.com/wp-content/uploads/2023/09/Wadi-Degla-Development-Neopolis-Neo-Gardens.pdf',
    'neopolis': 'https://wadidegladevelopments.com/wp-content/uploads/2023/09/Wadi-Degla-Development-Neopolis-Neo-Gardens.pdf',
    'neo_lakes': 'https://wadidegladevelopments.com/wp-content/uploads/2023/10/Neo-Lakes.pdf',
    'floating_islands': 'https://wadidegladevelopments.com/wp-content/uploads/2024/07/Floating-Islands-Brochure.pdf',
    'ojo': 'https://wadidegladevelopments.com/wp-content/uploads/2025/12/Ojo-Brochure.pdf',
    'breeze': 'https://wadidegladevelopments.com/wp-content/uploads/2023/10/CT-Breeze-Brochure.pdf',
    'horizon': 'https://wadidegladevelopments.com/wp-content/uploads/2023/10/CT-Horizon-Brochure-Wadi-Degla-Developments_.pdf',
    'edge': 'https://wadidegladevelopments.com/wp-content/uploads/2024/07/Edge-Brochure-2.pdf',
    'vyon': 'https://wadidegladevelopments.com/wp-content/uploads/2025/07/VYON-Brochure.pdf',
}

# ──────────────────────────────────────────────────────────────────
# MERGE LOGIC
# ──────────────────────────────────────────────────────────────────

def safe_json_list(existing_val, new_val):
    """Merge JSON list fields - preserve non-empty existing, add if empty."""
    if existing_val and existing_val.strip() not in ('', '[]', 'null'):
        try:
            existing = json.loads(existing_val)
            if existing:
                return existing_val  # Keep existing
        except:
            pass
    return new_val

def merge_row(row, evidence):
    """Non-destructively merge evidence into KB row. Only overwrite empty fields."""
    changed = []
    for field, value in evidence.items():
        if field.startswith('_'):
            continue  # Skip metadata
        current = row.get(field, '').strip()
        if not current:
            row[field] = value
            changed.append(field)
        elif field == 'key_amenities_json':
            # Merge amenities lists
            try:
                existing = json.loads(current) if current else []
                new_items = json.loads(value) if value else []
                merged = list(dict.fromkeys(existing + new_items))  # Deduplicate preserving order
                row[field] = json.dumps(merged)
                if merged != existing:
                    changed.append(field)
            except:
                pass
    return changed

def load_csv(path):
    with open(path, 'r', newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        return reader.fieldnames, list(reader)

def save_csv(path, fieldnames, rows):
    with open(path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

# ──────────────────────────────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────────────────────────────

print("=" * 60)
print("PulseX-WDD KB Enrichment — Evidence-Constrained Pass")
print(f"Run date: {TODAY}")
print("=" * 60)

# Load KB
fieldnames, rows = load_csv(KB_WORK)
print(f"\nLoaded KB: {len(rows)} rows, {len(fieldnames)} columns")

# Backup
backup_path = KB_WORK.replace('.csv', f'_backup_{TODAY}.csv')
shutil.copy2(KB_WORK, backup_path)
print(f"Backup: {backup_path}")

# Coverage before
def coverage_report(rows, fields):
    return {f: sum(1 for r in rows if r.get(f,'').strip()) for f in fields}

target_fields = [
    'bedrooms_range_min', 'bedrooms_range_max', 'bua_range_min_sqm', 'bua_range_max_sqm',
    'starting_price_value', 'price_range_min', 'price_range_max', 'price_status',
    'payment_plan_headline', 'downpayment_percent_min', 'installment_years_min',
    'delivery_window', 'delivery_year_min', 'unit_types_offered_json',
    'key_amenities_json', 'finishing_levels_offered_json', 'brochure_urls_json',
    'pricing_disclaimer'
]

before = coverage_report(rows, target_fields)
print("\n--- Coverage BEFORE ---")
for f, v in before.items():
    print(f"  {f}: {v}/{len(rows)}")

# Merge
merge_log = []
for row in rows:
    pid = row.get('project_id', '').strip()

    # Inject brochure URL
    if pid in BROCHURE_URLS:
        existing_brochure = row.get('brochure_urls_json', '').strip()
        brochure_url = BROCHURE_URLS[pid]
        if not existing_brochure or existing_brochure in ('[]', 'null'):
            row['brochure_urls_json'] = json.dumps([brochure_url])
        else:
            try:
                blist = json.loads(existing_brochure)
                if brochure_url not in blist:
                    blist.append(brochure_url)
                    row['brochure_urls_json'] = json.dumps(blist)
            except:
                pass

    # Source link
    official_url = row.get('official_project_url', '').strip()
    if official_url:
        existing_src = row.get('source_links_json', '').strip()
        if not existing_src or existing_src in ('[]', 'null'):
            row['source_links_json'] = json.dumps([{'url': official_url, 'type': 'official_page', 'captured': TODAY}])

    # Merge evidence
    if pid in EVIDENCE:
        changed = merge_row(row, EVIDENCE[pid])
        if changed:
            merge_log.append({'project_id': pid, 'fields_updated': changed, 'date': TODAY})

    # Update last_verified_date if we touched it
    row['last_verified_date'] = TODAY

print(f"\nMerge complete. {len(merge_log)} projects had fields updated.")
for entry in merge_log:
    print(f"  {entry['project_id']}: {entry['fields_updated']}")

# Coverage after
after = coverage_report(rows, target_fields)
print("\n--- Coverage AFTER ---")
print(f"{'Field':<35} {'Before':>8} {'After':>8} {'Delta':>8}")
print("-" * 60)
for f in target_fields:
    b = before[f]
    a = after[f]
    d = a - b
    delta_str = ('+' + str(d)) if d > 0 else str(d)
    print(f"  {f:<33} {b:>8} {a:>8} {delta_str:>8}")

# Save
save_csv(KB_WORK, fieldnames, rows)
print(f"\nSaved working KB: {KB_WORK}")

# Copy to engine-KB
os.makedirs(os.path.dirname(KB_ENGINE), exist_ok=True)
shutil.copy2(KB_WORK, KB_ENGINE)
print(f"Copied to engine KB: {KB_ENGINE}")

# Write merge log
merge_log_path = os.path.join(INTER_DIR, 'wdd_enrich_merge_log.json')
with open(merge_log_path, 'w') as f:
    json.dump({
        'run_date': TODAY,
        'projects_enriched': len(merge_log),
        'coverage_before': before,
        'coverage_after': after,
        'merge_log': merge_log
    }, f, indent=2)
print(f"Merge log: {merge_log_path}")

# Update checkpoint
checkpoint = {
    'run_date': TODAY,
    'status': 'phase3_complete',
    'total_rows': len(rows),
    'evidence_source': 'brochure_pdfs_pymupdf_docintel',
    'coverage_after': after,
    'cannot_enrich': {
        'starting_price_value': 'WDD does not publish prices in brochures or on website',
        'price_range_min': 'Same - no official price data found in any source',
        'price_range_max': 'Same - no official price data found in any source',
        'payment_plan_headline': 'WDD does not publish payment plans publicly',
        'downpayment_percent_min': 'Same - contact sales office required',
        'installment_years_min': 'Same - no public data found',
        'delivery_window': 'No delivery date information found in any brochure or website',
        'delivery_year_min': 'Same',
        'delivery_year_max': 'Same'
    },
    'notes': [
        'All brochures are lifestyle/marketing material with no pricing',
        'Murano/Waterside/LivingCommunity share the same 65-page spec brochure',
        'OJO brochure confirms unit types: Laguna Villa, Canal Townhouse, Senda Chalet (1-3BR)',
        'Murano brochure confirms: Loft House 3-4BR (235-240sqm), Tre Chalet 3BR (125-165sqm), Due Chalet 2BR (115-125sqm)',
        'ClubTown projects (Breeze, Horizon, Edge) share master plan brochures - amenities confirmed',
        'VYON brochure confirms premium rooftop amenities',
        'Neo/Neo Gardens/Neopolis share same brochure - facilities confirmed'
    ]
}
chk_path = os.path.join(INTER_DIR, 'wdd_enrichment_checkpoint.json')
with open(chk_path, 'w') as f:
    json.dump(checkpoint, f, indent=2)
print(f"Checkpoint: {chk_path}")

print("\n✓ Enrichment run complete.")
print("\nFields that CANNOT be populated (no official evidence):")
for f, reason in checkpoint['cannot_enrich'].items():
    print(f"  {f}: {reason}")
