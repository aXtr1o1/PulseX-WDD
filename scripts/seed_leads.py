import csv
import json
import os
import random
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

# --- Configuration & Paths ---
REPO_ROOT = Path("/Volumes/ReserveDisk/codeBase/PulseX-WDD")
KB_PATH = REPO_ROOT / "engine-KB/PulseX-WDD_buyerKB.csv"
RUNTIME_DIR = REPO_ROOT / "runtime"
RUNTIME_LEADS_DIR = RUNTIME_DIR / "leads"

LEADS_SEED_FILE = RUNTIME_LEADS_DIR / "leads_seed.csv"
LEADS_LIVE_FILE = RUNTIME_LEADS_DIR / "leads.csv"
AUDIT_FILE = RUNTIME_LEADS_DIR / "audit.csv"
SESSIONS_FILE = RUNTIME_DIR / "sessions.csv"

# --- Constants & Rules ---
TOTAL_LEADS = 473
RNG_SEED = 42
random.seed(RNG_SEED)

# Distribution targets
REGIONS_TARGET = {
    "East Cairo": 0.35,
    "Cairo": 0.20,
    "Ain El Sokhna": 0.20,
    "North Coast": 0.15,
    "West Cairo": 0.05,
    "Red Sea": 0.05
}

# --- 1. Load KnowledgeBase ---
def load_kb_projects():
    projects = []
    with open(KB_PATH, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row['current_sales_status'] == 'selling':
                projects.append({
                    "id": row['project_id'],
                    "name": row['project_name'].strip(),
                    "region": row['region'].strip(),
                    "unit_types": json.loads(row['unit_types_offered_json']) if row['unit_types_offered_json'] else ["apartment"]
                })
    return projects

PROJECTS = load_kb_projects()
SELLING_REGIONS = list(set(p['region'] for p in PROJECTS))

# --- 2. Realism Helpers ---

# Transliterated Arabic/Egyptian names + common Western/English names
NAME_POOL_ARABIC = [
    "Ahmed Mansour", "Mohamed Zaki", "Tarek Ebeid", "Yasmine Salem", "Laila Mahmoud",
    "Sherif Hassan", "Omar Fayed", "Mona Kamel", "Sara El-Ghazaly", "Hassan Radwan",
    "Nour El-Din", "Dina Hegazi", "Khaled Abbas", "Amira Soliman", "Bassem Youssef",
    "Rania El-Sayed", "Mostafa Ghandour", "Hend Sabry", "Adel Imam", "Maha Ahmed"
]
NAME_POOL_WESTERN = [
    "John Smith", "David Doe", "Sarah Emma", "Michael Johnson", "Emma Williams",
    "Robert Brown", "Linda Davis", "James Miller", "Mary Wilson", "Patricia Moore"
]

def get_realistic_name():
    if random.random() < 0.25: # 25% Arabic mix
        return random.choice(NAME_POOL_ARABIC)
    return random.choice(NAME_POOL_WESTERN)

def get_egyptian_phone():
    prefix = random.choice(["10", "11", "12", "15"])
    num = "".join([str(random.randint(0, 9)) for _ in range(8)])
    return f"+20{prefix}{num}"

def get_realistic_timestamp(now):
    # 60% in last 7 days, 25% in 8-15, 15% in 16-30
    r = random.random()
    if r < 0.60: days = random.randint(0, 7)
    elif r < 0.85: days = random.randint(8, 15)
    else: days = random.randint(16, 30)
    
    # Hour distribution: 12:00-22:00 weighted
    hr_r = random.random()
    if hr_r < 0.70: hour = random.randint(12, 21)
    elif hr_r < 0.90: hour = random.randint(7, 11)
    else: hour = random.choice([0,1,2,3,4,5,6,22,23])
    
    ts = now - timedelta(days=days, hours=hour, minutes=random.randint(0, 59), seconds=random.randint(0, 59))
    return ts.replace(microsecond=0, tzinfo=timezone.utc).isoformat().replace('+00:00', 'Z')

# --- 3. Lead Generation Logic ---

def generate_dataset():
    leads = []
    sessions = []
    audits = []
    
    now = datetime.now(timezone.utc)
    
    # Phone pool for dedupe realism (12-18% repeat)
    repeat_leads_count = int(TOTAL_LEADS * random.uniform(0.12, 0.18))
    contacts = []
    for _ in range(TOTAL_LEADS - repeat_leads_count):
        contacts.append({"name": get_realistic_name(), "phone": get_egyptian_phone()})
    
    # Fill the rest with repeats
    for _ in range(repeat_leads_count):
        contacts.append(random.choice(contacts[:int(len(contacts)*0.5)]))
    
    random.shuffle(contacts)
    
    for i, contact in enumerate(contacts):
        # 1. Basics
        ts = get_realistic_timestamp(now)
        session_id = str(uuid.uuid4())
        lead_id = f"WDDPX-{ts[2:4]}{ts[5:7]}{ts[8:10]}-{(i+1):04d}"
        
        # 2. Region & Project (80/20 rule)
        # Select region based on weighted target
        pref_region = random.choices(
            list(REGIONS_TARGET.keys()), 
            weights=list(REGIONS_TARGET.values())
        )[0]
        # Adjust if region not in KB
        if pref_region not in SELLING_REGIONS:
            pref_region = random.choice(SELLING_REGIONS)
            
        region_projects = [p for p in PROJECTS if p['region'] == pref_region]
        other_projects = [p for p in PROJECTS if p['region'] != pref_region]
        
        # 1-3 interest projects
        num_projs = random.choices([1, 2, 3], weights=[70, 20, 10])[0]
        interest_projs = []
        for _ in range(num_projs):
            if (random.random() < 0.8 or not other_projects) and region_projects:
                p = random.choice(region_projects)
            else:
                p = random.choice(other_projects)
            if p['name'] not in interest_projs:
                interest_projs.append(p['name'])
        
        # 3. Attributes
        purpose = random.choices(["Buy", "Invest", "Weekend", "Rent"], weights=[40, 35, 20, 5])[0]
        # Restrict Rent if not coastal/residential
        if purpose == "Rent" and pref_region not in ["Cairo", "East Cairo", "North Coast"]:
            purpose = "Invest"
            
        # Match unit type to first project if possible
        unit_type = "apartment" # Global fallback
        for p in PROJECTS:
            if p['name'] == interest_projs[0]:
                u_types = p.get('unit_types', [])
                if not u_types: u_types = ["apartment", "chalet"]
                unit_type = random.choice(u_types)
                break
        
        # Timeline
        timeline = random.choices(["Immediate", "0-3 months", "3-6 months", "Exploring"], weights=[15, 30, 25, 30])[0]
        
        # Budget
        band = random.choices(["LOW", "MID", "HIGH", "ULTRA"], weights=[30, 40, 20, 10])[0]
        # Coastal spikes budgets
        if pref_region in ["Ain El Sokhna", "North Coast"] and band == "LOW":
            band = "MID"
            
        ranges = {"LOW": (1.5, 3), "MID": (3, 6), "HIGH": (6, 10), "ULTRA": (10, 18)}
        b_min_raw, b_max_raw = ranges[band]
        pixel_budget_min = int(b_min_raw * 1_000_000)
        pixel_budget_max = int(b_max_raw * 1_000_000)
        
        budget_min = random.randint(pixel_budget_min, pixel_budget_max - 500_000)
        budget_max = budget_min + random.randint(500_000, 2_000_000)
        
        # 4. Gating (Consent/Confirm)
        consent = random.random() < 0.70
        confirmed = (random.random() < 0.75) if consent else False
        
        # 5. Temperature & Reason Codes
        is_hot = (purpose in ["Buy", "Invest", "Weekend"]) and (timeline in ["Immediate", "0-3 months"]) and consent and confirmed
        
        if is_hot:
            temp = "Hot"
            r_codes = ["high_intent", "short_timeline", "budget_present", "project_selected", "consented"]
        elif consent and (not confirmed or timeline == "Exploring"):
            temp = "Warm"
            r_codes = ["budget_missing"] if random.random() > 0.5 else ["timeline_long"]
        else:
            temp = "Cold"
            r_codes = ["browsing_only", "low_signal"] if not consent else ["consent_declined"]
            
        tags = []
        if band in ["HIGH", "ULTRA"]: tags.append("high_budget")
        if timeline == "Immediate": tags.append("urgent")
        if i % 8 == 0: tags.append("callback")
        
        # 6. Display Columns (The Dashboard Polish)
        lead_row = {
            "timestamp": ts,
            "lead_id": lead_id,
            "session_id": session_id,
            "name": contact['name'],
            "phone": contact['phone'],
            "email": f"{contact['name'].lower().replace(' ', '.')}@example.com" if random.random() < 0.4 else "None",
            "interest_projects": json.dumps(interest_projs),
            "interest_projects_display": "; ".join(interest_projs),
            "preferred_region": pref_region,
            "unit_type": unit_type,
            "budget_min": budget_min,
            "budget_max": budget_max,
            "budget_band": band,
            "purpose": purpose,
            "timeline": timeline,
            "contact_channel": random.choice(["WhatsApp", "WhatsApp", "Phone"]),
            "consent_contact": str(consent).lower(),
            "confirmed_by_user": str(confirmed).lower(),
            "lead_temperature": temp,
            "reason_codes": json.dumps(r_codes),
            "reason_codes_display": "; ".join(r_codes),
            "tags": json.dumps(tags),
            "tags_display": "; ".join(tags),
            "lead_summary": f"Concierge identified interest in {', '.join(interest_projs)}. Intent: {purpose}. Budget: {band}.",
            "raw_json": "{}",
            "kb_version_hash": "v1.1-palmx"
        }
        leads.append(lead_row)
        
        # Session Data
        sessions.append({
            "session_id": session_id,
            "started_at": ts,
            "last_seen_at": (datetime.fromisoformat(ts.replace('Z', '+00:00')) + timedelta(minutes=random.randint(2, 15))).isoformat().replace('+00:00', 'Z'),
            "page_hint": "/concierge",
            "focused_project": interest_projs[0]
        })
        
        # Audit Data (2x ratio)
        for _ in range(random.randint(1, 4)):
            audits.append({
                "timestamp": ts,
                "session_id": session_id,
                "intent": random.choices(["discovery", "sales", "brochure_request", "other"], weights=[45, 35, 15, 5])[0],
                "empty_retrieval": "false" if random.random() > 0.1 else "true",
                "top_entities_json": json.dumps(interest_projs),
                "latency_ms": random.randint(120, 2200),
                "status": "ok",
                "error_reason": "None"
            })

    return leads, sessions, audits

# --- 4. Main Execution ---
def main():
    print(f"--- WDD PulseX Seeding (PalmX-Grade) ---")
    leads, sessions, audits = generate_dataset()
    
    # Save Files
    def save_csv(path, data):
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=data[0].keys())
            writer.writeheader()
            writer.writerows(data)
        print(f"Saved {len(data)} rows to {path}")

    save_csv(LEADS_SEED_FILE, leads)
    save_csv(LEADS_LIVE_FILE, leads)
    save_csv(SESSIONS_FILE, sessions)
    save_csv(AUDIT_FILE, audits)
    
    print("\nVerification Stats:")
    print(f"Total Leads: {len(leads)}")
    unique_phones = len(set(l['phone'] for l in leads))
    print(f"Unique Contacts: {unique_phones} ({round(100 - (unique_phones/len(leads)*100), 1)}% repeat)")
    print(f"Regions Coverage: {set(l['preferred_region'] for l in leads)}")
    print("Done.")

if __name__ == "__main__":
    main()
