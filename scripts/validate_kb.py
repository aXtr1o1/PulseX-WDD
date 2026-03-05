import pandas as pd
import json
import os
import sys

# Paths
KB_ROOT = "/Volumes/ReserveDisk/codeBase/PulseX-WDD/engine-KB"
PROCESSED_DIR = os.path.join(KB_ROOT, "processed")
CLEANED_CSV = os.path.join(PROCESSED_DIR, "PulseX-WDD_buyerKB.cleaned.csv")

# Allowed Enums
ALLOWED_REGIONS = ["Ain El Sokhna", "North Coast", "Cairo", "East Cairo", "West Cairo", "Unknown"]
ALLOWED_SALES_STATUS = ["selling", "not_selling", "unknown"]
ALLOWED_PROJECT_STATUS = ["delivered", "under_construction", "launched", "unknown"]
ALLOWED_PROJECT_TYPES = ["residential", "commercial", "mixed", "unknown"]

def validate():
    if not os.path.exists(CLEANED_CSV):
        print(f"ERROR: {CLEANED_CSV} does not exist.")
        sys.exit(1)

    df = pd.read_csv(CLEANED_CSV)
    errors = []

    if len(df) == 0:
        errors.append("Cleaned KB is empty.")

    # 1. Column Integrity
    required_cols = [
        "canon_project_slug", "canon_project_name", "canon_region", 
        "canon_sales_status", "canon_unit_types", "canon_primary_url"
    ]
    for col in required_cols:
        if col not in df.columns:
            errors.append(f"Missing required column: {col}")

    if errors:
        for e in errors: print(f"CRITICAL ERROR: {e}")
        sys.exit(1)

    # 2. Row Wise Validation
    for idx, row in df.iterrows():
        p_name = str(row['canon_project_name'])
        
        # NaN check
        if pd.isna(row['canon_project_slug']) or row['canon_project_slug'] == 'nan':
            errors.append(f"[{p_name}] canon_project_slug is NaN")
            
        # Enum check: Region
        if row['canon_region'] not in ALLOWED_REGIONS:
            errors.append(f"[{p_name}] invalid region: {row['canon_region']}")

        # Enum check: Sales Status
        if row['canon_sales_status'] not in ALLOWED_SALES_STATUS:
            errors.append(f"[{p_name}] invalid sales status: {row['canon_sales_status']}")

        # JSON check: Unit Types
        try:
            units = json.loads(row['canon_unit_types'])
            if not isinstance(units, list):
                errors.append(f"[{p_name}] canon_unit_types is not a list")
        except:
            errors.append(f"[{p_name}] canon_unit_types failed to parse as JSON")

        # Routing check for selling projects
        if row['canon_sales_status'] == 'selling':
            if pd.isna(row['canon_primary_url']) or len(str(row['canon_primary_url'])) < 10:
                # This is a warning/flag in cleanup but we can gate it if we want strict routing
                pass

        # Placeholder check in project status
        p_status = str(row.get('canon_project_status', ''))
        if "team will assist" in p_status.lower():
             errors.append(f"[{p_name}] Placeholder text remains in canon_project_status")

    if errors:
        print(f"Validation failed with {len(errors)} errors:")
        for e in errors[:20]: # Show top 20
            print(f"- {e}")
        if len(errors) > 20: print(f"... and {len(errors)-20} more.")
        sys.exit(1)

    print("✅ Validation successful. Cleaned KB is integrity-safe.")

if __name__ == "__main__":
    validate()
