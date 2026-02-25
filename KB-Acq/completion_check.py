import csv, json
from pathlib import Path

KB_PATH = Path('/Volumes/ReserveDisk/codeBase/PulseX-WDD/KB-Acq/outputs/PulseX-WDD_buyerKB.csv')
OUTPUT_METRICS = Path('/Volumes/ReserveDisk/codeBase/PulseX-WDD/KB-Acq/outputs/intermediate/wdd_completion_check.json')
OUTPUT_GAP = Path('/Volumes/ReserveDisk/codeBase/PulseX-WDD/KB-Acq/outputs/intermediate/wdd_gap_report.csv')

OUTPUT_METRICS.parent.mkdir(parents=True, exist_ok=True)

if not KB_PATH.exists():
    print("KB not found.")
    exit(1)

with open(KB_PATH, 'r', encoding='utf-8') as f:
    rows = list(csv.DictReader(f))

# A1 checks
row_count = len(rows)
project_ids = set(r['project_id'] for r in rows)
struct_valid = (row_count == 28 and len(project_ids) == 28)

# JSON checks
json_cols = [c for c in rows[0].keys() if c.endswith('_json')]
json_ok = True
for r in rows:
    for c in json_cols:
        val = r[c].strip()
        if val:
            try:
                json.loads(val)
            except:
                json_ok = False
                break

struct_valid = struct_valid and json_ok

# Coverage checks
target_fields = [
    'unit_types_offered_json',
    'bedrooms_range_min', 'bedrooms_range_max',
    'bua_range_min_sqm', 'bua_range_max_sqm',
    'starting_price_value',
    'price_range_min', 'price_range_max',
    'price_status',
    'payment_plan_headline',
    'downpayment_percent_min', 'downpayment_percent_max',
    'installment_years_min', 'installment_years_max',
    'delivery_window', 'delivery_year_min', 'delivery_year_max',
    'brochure_urls_json', 'unit_templates_json', 'listings_json'
]

coverage = {f: 0 for f in target_fields}
incompletes = []

for r in rows:
    missing_all_critical = True
    for f in target_fields:
        val = r.get(f, '').strip()
        if val and val != '[]':
            coverage[f] += 1
            if f in ['bedrooms_range_min', 'bua_range_min_sqm', 'starting_price_value', 'price_range_min']:
                missing_all_critical = False
    
    if missing_all_critical:
        incompletes.append(r['project_id'])

metrics = {
    'structurally_valid': struct_valid,
    'total_rows': row_count,
    'unique_project_ids': len(project_ids),
    'json_columns_valid': json_ok,
    'coverage': coverage,
    'incomplete_rows': incompletes,
    'is_complete': struct_valid and len(incompletes) == 0
}

with open(OUTPUT_METRICS, 'w') as f:
    json.dump(metrics, f, indent=2)

with open(OUTPUT_GAP, 'w', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(['project_id', 'missing_critical'])
    for pid in incompletes:
        writer.writerow([pid, True])

print(json.dumps(metrics, indent=2))
