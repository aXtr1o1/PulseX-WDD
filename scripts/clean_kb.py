import pandas as pd
import json
import os
import re
from datetime import datetime

# Paths
KB_ROOT = "/Volumes/ReserveDisk/codeBase/PulseX-WDD/engine-KB"
INPUT_CSV = os.path.join(KB_ROOT, "PulseX-WDD_buyerKB.csv")
PROCESSED_DIR = os.path.join(KB_ROOT, "processed")
CLEANED_CSV = os.path.join(PROCESSED_DIR, "PulseX-WDD_buyerKB.cleaned.csv")
DROP_CSV = os.path.join(PROCESSED_DIR, "PulseX-WDD_buyerKB.drop.csv")
REPORT_JSON = os.path.join(PROCESSED_DIR, "wdd_kb_cleanup_report.json")
SUMMARY_MD = os.path.join(PROCESSED_DIR, "wdd_kb_cleanup_summary.md")

os.makedirs(PROCESSED_DIR, exist_ok=True)

# Normalization Maps
REGION_MAP = {
    "ain sokhna": "Ain El Sokhna",
    "ain sokhna road": "Ain El Sokhna",
    "el sokhna": "Ain El Sokhna",
    "north coast": "North Coast",
    "cairo": "Cairo",
    "east cairo": "East Cairo",
    "west cairo": "West Cairo",
}

UNIT_TYPE_ENUM = [
    "apartment", "villa", "chalet", "townhouse", "duplex", 
    "penthouse", "loft", "studio", "retail", "office", "commercial", "unknown"
]

UNIT_TYPE_VARIANTS = {
    "town houses": "townhouse",
    "town house": "townhouse",
    "apartments": "apartment",
    "retail": "retail",
    "villas": "villa",
    "chalets": "chalet",
}

def normalize_slug(name):
    if not isinstance(name, str): return "unknown"
    s = name.lower()
    s = re.sub(r'[^a-z0-0\s_]', '', s)
    s = re.sub(r'[\s\-]+', '_', s)
    return s.strip('_')

def parse_unit_types(val):
    results = set()
    if not val or pd.isna(val):
        return ["unknown"]
    
    try:
        # Try raw JSON
        if isinstance(val, str) and (val.startswith('[') or val.startswith('{')):
            data = json.loads(val)
            if isinstance(data, list):
                for item in data:
                    item_low = str(item).lower().strip()
                    results.add(UNIT_TYPE_VARIANTS.get(item_low, item_low))
    except:
        pass

    # Fallback to string splitting if JSON fails or is just a string
    if not results and isinstance(val, str):
        parts = re.split(r'[,|;]', val)
        for p in parts:
            p_low = p.lower().strip()
            results.add(UNIT_TYPE_VARIANTS.get(p_low, p_low))

    # Filter by enum
    final = [r for r in results if r in UNIT_TYPE_ENUM]
    return final if final else ["unknown"]

def clean_kb():
    print(f"Loading KB from {INPUT_CSV}...")
    df = pd.read_csv(INPUT_CSV, encoding='utf-8-sig')
    
    report = {
        "input_row_count": len(df),
        "cleaned_row_count": 0,
        "dropped_row_count": 0,
        "dropped_details": [],
        "placeholder_status_count": 0,
        "quality_stats": {
            "missing_unit_types": 0,
            "missing_urls": 0
        }
    }

    cleaned_rows = []
    dropped_rows = []
    slug_counts = {}

    for idx, row in df.iterrows():
        p_name = str(row.get('project_name', '')).strip()
        region = str(row.get('region', '')).strip()
        city_area = str(row.get('city_area', '')).strip()
        
        # New canon fields
        canon = {k: v for k, v in row.to_dict().items()}
        canon['canon_quality_flags'] = []
        canon['canon_notes'] = ""
        canon['canon_row_action'] = "keep"
        canon['canon_drop_reason'] = ""

        # 1. DROP RULES
        drop_reason = []
        if not p_name or len(p_name) < 3 or p_name.lower() == 'nan':
            drop_reason.append("missing_project_name")
        
        if (not region or region.lower() == 'nan') and (not city_area or city_area.lower() == 'nan'):
            drop_reason.append("missing_location")
            
        urls = [row.get('official_project_url'), row.get('contact_page_url'), row.get('inquiry_form_url')]
        if not any(isinstance(u, str) and len(str(u)) > 10 for u in urls):
            drop_reason.append("no_routing_urls")
            report["quality_stats"]["missing_urls"] += 1

        if drop_reason:
            canon['canon_row_action'] = "drop"
            canon['canon_drop_reason'] = ", ".join(drop_reason)
            report["dropped_details"].append({"project": p_name, "reason": canon['canon_drop_reason']})
            dropped_rows.append(canon)
            continue

        # 2. NORMALIZATION
        # Project Name & Slug
        canon['canon_project_name'] = p_name.title()
        slug = normalize_slug(p_name)
        if slug in slug_counts:
            slug_counts[slug] += 1
            slug = f"{slug}_{slug_counts[slug]}"
        else:
            slug_counts[slug] = 1
        canon['canon_project_slug'] = slug

        # Region
        r_low = region.lower()
        canon['canon_region'] = REGION_MAP.get(r_low, "Unknown")
        if canon['canon_region'] == "Unknown":
            canon['canon_quality_flags'].append("missing_region")

        # City Area
        canon['canon_city_area'] = city_area.title() if city_area and city_area.lower() != 'nan' else "Unknown"

        # Unit Types
        raw_units = row.get('unit_types_offered_json')
        canon_units = parse_unit_types(raw_units)
        if "unknown" in canon_units:
            report["quality_stats"]["missing_unit_types"] += 1
            canon['canon_quality_flags'].append("missing_unit_types")
        canon['canon_unit_types'] = json.dumps(canon_units)

        # Project Type
        if any(u in ["retail", "office", "commercial"] for u in canon_units):
            canon['canon_project_type'] = "mixed" if any(u in ["apartment", "villa", "chalet"] for u in canon_units) else "commercial"
        elif "unknown" in canon_units:
            canon['canon_project_type'] = "unknown"
        else:
            canon['canon_project_type'] = "residential"

        # Sales Status
        val_sales = str(row.get('current_sales_status', '')).lower()
        if val_sales in ["selling", "not_selling"]:
            canon['canon_sales_status'] = val_sales
        else:
            canon['canon_sales_status'] = "unknown"

        # Project Status & Placeholder Cleanup
        p_status = str(row.get('project_status', '')).strip()
        if "team will assist" in p_status.lower() or "sales team" in p_status.lower():
            canon['canon_notes'] = p_status
            canon['canon_project_status'] = "unknown"
            canon['canon_quality_flags'].append("placeholder_project_status")
            report["placeholder_status_count"] += 1
        else:
            # Only accept real status if it looks like one
            if p_status.lower() in ["delivered", "under_construction", "launched"]:
                canon['canon_project_status'] = p_status.lower()
            else:
                canon['canon_project_status'] = "unknown"

        # Brand Family
        canon['brand_family'] = str(row.get('brand_family', '')).strip() or "Wadi Degla"
        canon['canon_brand_family'] = canon['brand_family'].title()

        # Primary URL
        u_official = row.get('official_project_url')
        u_inquiry = row.get('inquiry_form_url')
        u_contact = row.get('contact_page_url')
        canon['canon_primary_url'] = u_official if pd.notna(u_official) else (u_inquiry if pd.notna(u_inquiry) else (u_contact if pd.notna(u_contact) else None))

        # Brochure
        b_json = row.get('brochure_urls_json')
        try:
            b_list = json.loads(b_json) if isinstance(b_json, str) and b_json.startswith('[') else []
            canon['canon_has_brochure'] = len(b_list) > 0
        except:
            canon['canon_has_brochure'] = False

        # Final packaging
        canon['canon_quality_flags'] = json.dumps(canon['canon_quality_flags'])
        cleaned_rows.append(canon)

    # Output DataFrames
    df_clean = pd.DataFrame(cleaned_rows)
    df_drop = pd.DataFrame(dropped_rows)

    df_clean.to_csv(CLEANED_CSV, index=False, encoding='utf-8-sig')
    df_drop.to_csv(DROP_CSV, index=False, encoding='utf-8-sig')

    # Report Stats
    report["cleaned_row_count"] = len(df_clean)
    report["dropped_row_count"] = len(df_drop)
    report["selling_count"] = int(df_clean[df_clean['canon_sales_status'] == 'selling'].shape[0])
    report["not_selling_count"] = int(df_clean[df_clean['canon_sales_status'] == 'not_selling'].shape[0])
    report["unknown_sales_count"] = int(df_clean[df_clean['canon_sales_status'] == 'unknown'].shape[0])
    report["region_distribution"] = df_clean['canon_region'].value_counts().to_dict()
    
    # Top incomplete
    df_clean['missing_count'] = df_clean.apply(lambda r: json.loads(r['canon_quality_flags']), axis=1).apply(len)
    report["top_incomplete"] = df_clean.sort_values('missing_count', ascending=False).head(10)[['canon_project_name', 'missing_count']].to_dict('records')

    with open(REPORT_JSON, 'w') as f:
        json.dump(report, f, indent=4)

    # Markdown Summary
    with open(SUMMARY_MD, 'w') as f:
        f.write(f"# KB Cleanup Summary - {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n")
        f.write(f"### Overall Stats\n")
        f.write(f"- **Input Rows**: {report['input_row_count']}\n")
        f.write(f"- **Cleaned Rows**: {report['cleaned_row_count']}\n")
        f.write(f"- **Dropped Rows**: {report['dropped_row_count']}\n\n")
        f.write(f"### Distribution\n")
        for reg, count in report['region_distribution'].items():
            f.write(f"- {reg}: {count}\n")
        f.write(f"\n### Drop Reasons\n")
        reasons = {}
        for d in report["dropped_details"]:
            r = d['reason']
            reasons[r] = reasons.get(r, 0) + 1
        for r, count in reasons.items():
            f.write(f"- {r}: {count}\n")
    
    print(f"Cleanup complete. Generated {CLEANED_CSV}")

if __name__ == "__main__":
    clean_kb()
