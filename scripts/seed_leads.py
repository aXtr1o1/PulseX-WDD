import csv
import json
import os
import random
import uuid
from datetime import datetime, timedelta
from pathlib import Path

# --- Configuration & Paths ---
REPO_ROOT = Path("/Volumes/ReserveDisk/codeBase/PulseX-WDD")
KB_PATH = REPO_ROOT / "engine-KB/PulseX-WDD_buyerKB.csv"
RUNTIME_LEADS_DIR = REPO_ROOT / "runtime/leads"
EXPORT_DIR = RUNTIME_LEADS_DIR / "exports"

LEADS_FILE = RUNTIME_LEADS_DIR / "leads.csv"
LEADS_SEED_FILE = RUNTIME_LEADS_DIR / "leads_seed.csv"
AUDIT_FILE = RUNTIME_LEADS_DIR / "audit.csv"
SESSIONS_FILE = RUNTIME_LEADS_DIR / "sessions.csv"

# Deterministic Seed
random.seed(42)

# --- Data Rules ---
TOTAL_LEADS = 473
AUDIT_RATIO = 2.5 # ~2.5 audit rows per lead
DAYS_BACK = 30

H_DIST = {
    "12-22": 0.75, # 75% of traffic
    "07-11": 0.20, # 20% of traffic
    "00-06": 0.05  # 5% of traffic
}

# --- 1. Read KB & Portfolio ---
def load_portfolio():
    projects = []
    regions = set()
    with open(KB_PATH, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row['current_sales_status'] == 'selling':
                p_name = row['project_name'].strip()
                region = row['region'].strip()
                projects.append({"name": p_name, "region": region, "id": row['project_id']})
                regions.add(region)
    return projects, sorted(list(regions))

PROJECTS, REGIONS = load_portfolio()

# --- 2. Generation Helpers ---
def get_random_timestamp():
    # Last 30 days distribution
    r = random.random()
    if r < 0.60: # 60% in last 7 days
        days = random.randint(0, 7)
    elif r < 0.85: # 25% in days 8-15
        days = random.randint(8, 15)
    else: # 15% in days 16-30
        days = random.randint(16, 30)
    
    # Hour distribution
    hr_r = random.random()
    if hr_r < H_DIST["12-22"]:
        hour = random.randint(12, 22)
    elif hr_r < H_DIST["12-22"] + H_DIST["07-11"]:
        hour = random.randint(7, 11)
    else:
        hour = random.randint(0, 6)
        
    ts = datetime.now() - timedelta(days=days, hours=hour, minutes=random.randint(0, 59))
    return ts.isoformat()

def generate_phone():
    return f"+201{random.randint(0, 2)}{random.randint(1000000, 9999999)}"

NAME_START = ["Ahmed", "Mohamed", "Tarek", "Yasmine", "Laila", "Sherif", "Omar", "Hassan", "Mona", "Sara", "John", "David", "Sarah", "Emma", "Michael"]
NAME_END = ["Mansour", "Zaki", "Ebeid", "Salem", "Smith", "Doe", "Johnson", "Williams", "Brown"]

def generate_name():
    return f"{random.choice(NAME_START)} {random.choice(NAME_END)}"

BUDGET_BANDS = {
    "low": (1500000, 3000000),
    "mid": (3000000, 6000000),
    "high": (6000000, 10000000),
    "ultra": (10000000, 18000000)
}

# --- 3. Generate Leads ---
leads = []
sessions = []
audit_logs = []

# For repeat leads simulation
phone_pool = []

for i in range(TOTAL_LEADS):
    is_repeat = random.random() < 0.15 and len(phone_pool) > 10
    if is_repeat:
        base_lead = random.choice(phone_pool)
        phone = base_lead['phone']
        name = base_lead['name']
    else:
        phone = generate_phone()
        name = generate_name()
    
    ts = get_random_timestamp()
    session_id = str(uuid.uuid4())
    lead_id = f"WDDPX-{ts[:10].replace('-', '')}-{i:04d}"
    
    # Portfolio selection
    proj = random.choice(PROJECTS)
    region = proj['region']
    
    purpose = random.choices(["Buy", "Invest", "Weekend", "Rent"], weights=[40, 35, 20, 5])[0]
    unit_type = random.choices(["apartment", "villa", "chalet", "townhouse", "duplex"], weights=[35, 20, 20, 15, 10])[0]
    
    # Budget logic
    if "Coast" in region or "Sokhna" in region:
        band = random.choices(["mid", "high", "ultra"], weights=[40, 40, 20])[0]
    else:
        band = random.choices(["low", "mid", "high"], weights=[30, 50, 20])[0]
    
    bmin, bmax = BUDGET_BANDS[band]
    budget_min = random.randint(bmin, bmax - 500000)
    budget_max = budget_min + random.randint(500000, 2000000)
    
    timeline = random.choices(["Immediate", "0-3 months", "3-6 months", "Exploring"], weights=[15, 30, 25, 30])[0]
    
    consent = random.random() < 0.70
    confirmed = random.random() < 0.75 if consent else False
    
    # Temperature Logic
    temp = "Cold"
    reason_codes = ["low_signal"]
    tags = []
    
    if consent and confirmed:
        if timeline in ["Immediate", "0-3 months"]:
            temp = "Hot"
            reason_codes = ["high_intent", "short_timeline", "consented", "confirmed"]
            tags.append("urgent")
        else:
            temp = "Warm"
            reason_codes = ["consent_pending", "timeline_6mo"]
    
    if budget_max > 10000000:
        tags.append("high_budget")
    if random.random() < 0.10:
        tags.append("international")
    
    summary = f"Interested in {proj['name']} ({unit_type}) for {purpose.lower()}. Timeline: {timeline}."
    
    lead_row = {
        "timestamp": ts,
        "lead_id": lead_id,
        "session_id": session_id,
        "name": name,
        "phone": phone,
        "email": f"{name.lower().replace(' ', '.')}@example.com",
        "interest_projects": json.dumps([proj['name']]),
        "preferred_region": region,
        "unit_type": unit_type,
        "budget_min": budget_min,
        "budget_max": budget_max,
        "budget_band": band,
        "purpose": purpose,
        "timeline": timeline,
        "contact_channel": "WhatsApp" if random.random() > 0.3 else "Phone",
        "consent_contact": str(consent).lower(),
        "confirmed_by_user": str(confirmed).lower(),
        "lead_temperature": temp,
        "reason_codes": json.dumps(reason_codes),
        "tags": json.dumps(tags),
        "lead_summary": summary,
        "raw_json": json.dumps({"source": "seed_v1", "agent": "Gemini-3-Flash"}),
        "kb_version_hash": "v1.0"
    }
    
    leads.append(lead_row)
    if not is_repeat:
        phone_pool.append({"phone": phone, "name": name})
        
    # Sessions
    sessions.append({
        "session_id": session_id,
        "started_at": ts,
        "last_seen_at": (datetime.fromisoformat(ts) + timedelta(minutes=random.randint(5, 20))).isoformat(),
        "entry_page": random.choice(["/", "/widget", "/concierge"]),
        "locale": "en"
    })
    
    # Audit Logs (multiple per session)
    num_audits = random.randint(2, 4)
    for _ in range(num_audits):
        audit_logs.append({
            "timestamp": (datetime.fromisoformat(ts) + timedelta(minutes=random.randint(1, 10))).isoformat(),
            "session_id": session_id,
            "user_message": "Interested in WDD projects",
            "router_intent": random.choices(["discovery", "sales", "brochure_request"], weights=[45, 45, 10])[0],
            "retrieved_projects": json.dumps([p['name'] for p in random.sample(PROJECTS, k=random.randint(1, 3))]),
            "similarity_scores": json.dumps([round(random.uniform(0.7, 0.95), 3) for _ in range(3)]),
            "kb_version": "v1.0",
            "fields_used": "all"
        })

# --- 4. Write Files ---
def write_csv(path, data, headers):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(data)

# Backup existing if any
if LEADS_FILE.exists():
    os.makedirs(EXPORT_DIR, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    os.rename(LEADS_FILE, EXPORT_DIR / f"leads_backup_{stamp}.csv")

write_csv(LEADS_SEED_FILE, leads, list(leads[0].keys()))
write_csv(LEADS_FILE, leads, list(leads[0].keys()))
write_csv(SESSIONS_FILE, sessions, list(sessions[0].keys()))
write_csv(AUDIT_FILE, audit_logs, list(audit_logs[0].keys()))

print(f"Generated {len(leads)} leads, {len(sessions)} sessions, and {len(audit_logs)} audit rows.")
print(f"Files saved to: {RUNTIME_LEADS_DIR}")
