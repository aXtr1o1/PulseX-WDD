#!/usr/bin/env python3
"""
PulseX-WDD Seed Lead Generator — PalmX-Grade Realism
Generates 473 deterministic synthetic leads for the WDD dashboard.

Usage:
    python3 scripts/seed_leads.py              # Template-based summaries (no API needed)
    python3 scripts/seed_leads.py --use-aoai   # Azure OpenAI enriched summaries

Output files (all under runtime/):
    runtime/leads/leads_seed.csv   — 473 leads with full schema
    runtime/leads/leads.csv        — Same data (dashboard default)
    runtime/sessions.csv           — 1:1 session data
    runtime/leads/audit.csv        — 1-4 audit events per lead
    engine-KB/derived/kb_digest.json — KB-derived project highlights
"""

import csv
import hashlib
import json
import os
import random
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

# --- Configuration & Paths ---
REPO_ROOT = Path(__file__).resolve().parent.parent
KB_PATH = REPO_ROOT / "engine-KB" / "PulseX-WDD_buyerKB.csv"
DIGEST_PATH = REPO_ROOT / "engine-KB" / "derived" / "kb_digest.json"
RUNTIME_DIR = REPO_ROOT / "runtime"
LEADS_DIR = RUNTIME_DIR / "leads"
CACHE_DIR = RUNTIME_DIR / "seed_cache"

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
    "Red Sea": 0.05,
}

# --- 1. Load KnowledgeBase ---
def load_kb_projects():
    """Load projects from the canonical WDD KB CSV, filtering to selling-only."""
    if not KB_PATH.is_file():
        print(f"[WARN] KB not found at {KB_PATH}. Using fallback project list.")
        return _fallback_projects()

    import csv as csvmod
    projects = []
    with open(KB_PATH, "r", encoding="utf-8") as f:
        reader = csvmod.DictReader(f)
        for row in reader:
            status = (row.get("current_sales_status") or "").lower().strip()
            # Only include projects that are actively selling
            drop = (row.get("drop_reason") or "").strip()
            alias = (row.get("is_alias_of") or "").strip()

            # Skip dropped, aliased, or explicitly not-selling projects
            if drop or alias:
                continue
            if status and status not in ("selling", "available", "unknown", ""):
                continue

            name = row.get("project_name", "").strip()
            if not name:
                continue

            region = row.get("region", "").strip()
            project_type = row.get("project_type", "residential").strip()

            # Parse unit types
            unit_types = []
            try:
                ut_raw = row.get("unit_types_offered_json", "[]")
                unit_types = json.loads(ut_raw) if ut_raw else []
            except (json.JSONDecodeError, TypeError):
                unit_types = ["apartment"]

            if not unit_types:
                unit_types = ["apartment", "chalet"] if project_type == "resort" else ["apartment"]

            # Parse amenities for digest
            amenities = []
            try:
                am_raw = row.get("key_amenities_json", "[]")
                amenities = json.loads(am_raw) if am_raw else []
            except (json.JSONDecodeError, TypeError):
                pass

            # Parse zones
            zones = []
            try:
                z_raw = row.get("zones_json", "[]")
                zones = json.loads(z_raw) if z_raw else []
            except (json.JSONDecodeError, TypeError):
                pass

            projects.append({
                "name": name,
                "project_id": row.get("project_id", name.lower()),
                "region": region or "Cairo",
                "type": project_type,
                "unit_types": unit_types,
                "status": status or "selling",
                "micro_location": row.get("micro_location", ""),
                "amenities": amenities[:6],
                "zones": [z.get("name", "") for z in zones if isinstance(z, dict)][:4],
                "beach_access": row.get("beach_access_flag", "false").lower() == "true",
                "golf": row.get("golf_flag", "false").lower() == "true",
                "pools": row.get("pools_flag", "false").lower() == "true",
                "price_status": row.get("price_status", "on_request"),
            })

    if not projects:
        return _fallback_projects()

    return projects


def _fallback_projects():
    return [
        {"name": "Murano", "project_id": "murano", "region": "Ain El Sokhna", "type": "resort",
         "unit_types": ["villa", "chalet", "duplex"], "status": "selling", "micro_location": "Ain Sokhna Road",
         "amenities": ["Swimming Pools", "Beach", "Restaurants"], "zones": ["Living Community", "Waterside"], "beach_access": True, "golf": False, "pools": True, "price_status": "on_request"},
        {"name": "ClubTown", "project_id": "clubtown", "region": "Cairo", "type": "residential",
         "unit_types": ["apartment", "duplex"], "status": "selling", "micro_location": "New Degla, Maadi",
         "amenities": ["Club House", "Padel Tennis", "Swimming Pools"], "zones": ["Breeze", "Horizon", "Edge"], "beach_access": False, "golf": False, "pools": True, "price_status": "on_request"},
        {"name": "Neo", "project_id": "neo", "region": "East Cairo", "type": "residential",
         "unit_types": ["apartment", "duplex"], "status": "selling", "micro_location": "Mostakbal City",
         "amenities": ["International School", "Green Areas", "Commercial Hub"], "zones": ["Neo Lakes", "Neo Gardens"], "beach_access": False, "golf": False, "pools": False, "price_status": "on_request"},
        {"name": "Vero", "project_id": "vero", "region": "North Coast", "type": "resort",
         "unit_types": ["apartment", "chalet"], "status": "selling", "micro_location": "Sidi Abd El Rahman",
         "amenities": ["Horizon Pool", "Beach Bar", "Fitness Center"], "zones": [], "beach_access": True, "golf": False, "pools": True, "price_status": "on_request"},
        {"name": "Promenade New Cairo", "project_id": "promenade_new_cairo", "region": "East Cairo", "type": "residential",
         "unit_types": ["apartment"], "status": "selling", "micro_location": "New Cairo",
         "amenities": ["Green Areas", "Commercial Area"], "zones": [], "beach_access": False, "golf": False, "pools": False, "price_status": "on_request"},
    ]


def build_kb_digest(projects):
    """Build a derived KB digest for seed + summary generation."""
    digest = {}
    for p in projects:
        highlights = []
        if p.get("micro_location"):
            highlights.append(f"Located in {p['micro_location']}")
        if p.get("beach_access"):
            highlights.append("Direct beach access")
        if p.get("pools"):
            highlights.append("Multiple swimming pools")
        if p.get("zones"):
            highlights.append(f"Phases: {', '.join(p['zones'][:3])}")
        if p.get("amenities"):
            highlights.append(f"Key amenities: {', '.join(p['amenities'][:3])}")
        if not highlights:
            highlights.append(f"{p['type'].title()} project by Wadi Degla Developments")

        digest[p["name"]] = {
            "region": p["region"],
            "type": p["type"],
            "unit_types": p["unit_types"],
            "status": p["status"],
            "highlights": highlights[:4],
            "price_status": p.get("price_status", "on_request"),
        }

    DIGEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(DIGEST_PATH, "w", encoding="utf-8") as f:
        json.dump(digest, f, indent=2, ensure_ascii=False)
    print(f"[OK] KB digest written: {DIGEST_PATH} ({len(digest)} projects)")
    return digest


# --- 2. Realism Helpers ---

NAME_POOL_ARABIC = [
    "Ahmed Hassan", "Mohamed Samir", "Yasmine Salem", "Nour El Din", "Hassan Radwan",
    "Sara El Masri", "Omar Khaled", "Layla Ibrahim", "Karim Youssef", "Dina Farouk",
    "Amr Tawfik", "Rania Hossam", "Tarek El Sayed", "Hana Mostafa", "Mostafa Gamal",
    "Fatma Abdel Rahman", "Mahmoud Ali", "Salma Ashraf", "Youssef Nabil", "Lina Mahmoud",
]
NAME_POOL_WESTERN = [
    "John Smith", "David Doe", "Sarah Emma", "Michael Johnson", "Emma Williams",
    "Robert Brown", "Linda Davis", "James Miller", "Mary Wilson", "Patricia Moore",
]


def get_realistic_name():
    if random.random() < 0.65:
        return random.choice(NAME_POOL_ARABIC)
    return random.choice(NAME_POOL_WESTERN)


def get_egyptian_phone():
    prefixes = ["010", "011", "012", "015"]
    return f"+20{random.choice(prefixes)}{random.randint(10000000, 99999999)}"


def get_realistic_timestamp(now):
    days_back = random.randint(0, 14)
    hour_weights = [1]*6 + [3]*4 + [5]*4 + [4]*4 + [2]*6  # Peak 10-18
    hour = random.choices(range(24), weights=hour_weights)[0]
    minute = random.randint(0, 59)
    second = random.randint(0, 59)
    dt = now - timedelta(days=days_back, hours=random.randint(0, 5))
    dt = dt.replace(hour=hour, minute=minute, second=second, microsecond=0)
    # Weekday bias (60% weekday)
    if dt.weekday() >= 5 and random.random() < 0.4:
        dt -= timedelta(days=random.randint(1, 2))
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


# --- 3. Template-based Summary Generator ---

def generate_template_summary(lead, kb_digest):
    """Generate a realistic customer summary using templates, no API needed."""
    name = lead["name"].split()[0]
    projects = json.loads(lead["interest_projects"])
    region = lead["preferred_region"]
    purpose = lead["purpose"]
    unit_type = lead["unit_type"]
    budget_band = lead["budget_band"]
    timeline = lead["timeline"]
    consent = lead["consent_contact"] == "true"
    confirmed = lead["confirmed_by_user"] == "true"

    # Build persona
    if purpose == "Invest":
        persona = f"{name} is an investor exploring real estate opportunities"
    elif purpose == "Weekend":
        persona = f"{name} is looking for a weekend/holiday retreat"
    elif purpose == "Rent":
        persona = f"{name} is exploring rental options"
    else:
        persona = f"{name} is a prospective homebuyer"

    if region in ("Ain El Sokhna", "North Coast"):
        persona += f" in {region}'s coastal market"
    else:
        persona += f" in the {region} residential market"

    # Build interest
    proj_names = ", ".join(projects[:2])
    proj_detail = ""
    for p in projects[:1]:
        info = kb_digest.get(p, {})
        if info.get("highlights"):
            proj_detail = f". {p} offers {info['highlights'][0].lower()}"

    interest = f"Showed strong interest in {proj_names}{proj_detail}"

    # Budget context
    budget_map = {"LOW": "entry-level budget range (1.5–3M EGP)", "MID": "mid-market budget (3–6M EGP)",
                  "HIGH": "premium budget segment (6–10M EGP)", "ULTRA": "ultra-premium tier (10M+ EGP)"}
    budget_ctx = budget_map.get(budget_band, "undisclosed budget")

    # Build asks
    asks = []
    if random.random() < 0.5:
        asks.append("requested brochure")
    if random.random() < 0.3:
        asks.append("asked about payment plans")
    if random.random() < 0.2:
        asks.append("inquired about site visit")
    if consent:
        asks.append("agreed to callback")
    if not asks:
        asks.append("browsed project details")

    # Timeline context
    timeline_map = {"Immediate": "ready to proceed immediately", "0-3 months": "planning within 3 months",
                    "3-6 months": "considering a 3-6 month timeline", "Exploring": "in early exploration stage"}
    timeline_ctx = timeline_map.get(timeline, "exploring options")

    # Customer summary (2-4 lines)
    customer_summary = f"{persona}. {interest}, specifically a {unit_type} within {budget_ctx}. " \
                       f"During the session, {name} {', '.join(asks)}. Currently {timeline_ctx}."

    # Executive summary (1-2 lines)
    temp = lead["lead_temperature"]
    exec_summary = f"{temp} lead — {purpose} intent for {proj_names} ({region}). " \
                   f"Budget: {budget_band}. Timeline: {timeline}."

    # Next action
    if temp == "Hot" and consent:
        next_action = f"Priority callback within 24h. Send {proj_names} brochure + payment plan."
    elif temp == "Warm":
        next_action = f"Schedule follow-up call. Share {proj_names} digital brochure."
    else:
        next_action = f"Add to nurture sequence. Email {proj_names} project highlights."

    return customer_summary, exec_summary, next_action


# --- 4. Lead Generation Logic ---

def generate_dataset(kb_digest):
    leads = []
    sessions = []
    audits = []

    now = datetime.now(timezone.utc)

    # Phone pool for dedupe realism (12-18% repeat)
    repeat_leads_count = int(TOTAL_LEADS * random.uniform(0.12, 0.18))
    contacts = []
    for _ in range(TOTAL_LEADS - repeat_leads_count):
        contacts.append({"name": get_realistic_name(), "phone": get_egyptian_phone()})

    # Fill the rest with repeats (different timestamp/intent)
    for _ in range(repeat_leads_count):
        contacts.append(random.choice(contacts[:int(len(contacts)*0.5)]))

    random.shuffle(contacts)

    selling_regions = list(set(p["region"] for p in PROJECTS))

    for i, contact in enumerate(contacts):
        ts = get_realistic_timestamp(now)
        session_id = str(uuid.uuid4())
        lead_id = f"WDDPX-{ts[2:4]}{ts[5:7]}{ts[8:10]}-{(i+1):04d}"

        # Region & Project (weighted)
        pref_region = random.choices(list(REGIONS_TARGET.keys()), weights=list(REGIONS_TARGET.values()))[0]
        if pref_region not in selling_regions:
            pref_region = random.choice(selling_regions)

        region_projects = [p for p in PROJECTS if p["region"] == pref_region]
        other_projects = [p for p in PROJECTS if p["region"] != pref_region]

        num_projs = random.choices([1, 2, 3], weights=[70, 20, 10])[0]
        interest_projs = []
        for _ in range(num_projs):
            if (random.random() < 0.8 or not other_projects) and region_projects:
                p = random.choice(region_projects)
            else:
                p = random.choice(other_projects)
            if p["name"] not in interest_projs:
                interest_projs.append(p["name"])

        # Attributes
        purpose = random.choices(["Buy", "Invest", "Weekend", "Rent"], weights=[40, 35, 20, 5])[0]
        if purpose == "Rent" and pref_region not in ["Cairo", "East Cairo", "North Coast"]:
            purpose = "Invest"

        unit_type = "apartment"
        for p in PROJECTS:
            if p["name"] == interest_projs[0]:
                u_types = p.get("unit_types", []) or ["apartment"]
                unit_type = random.choice(u_types)
                break

        timeline = random.choices(["Immediate", "0-3 months", "3-6 months", "Exploring"], weights=[15, 30, 25, 30])[0]

        band = random.choices(["LOW", "MID", "HIGH", "ULTRA"], weights=[30, 40, 20, 10])[0]
        if pref_region in ["Ain El Sokhna", "North Coast"] and band == "LOW":
            band = "MID"

        ranges = {"LOW": (1.5, 3), "MID": (3, 6), "HIGH": (6, 10), "ULTRA": (10, 18)}
        b_min_raw, b_max_raw = ranges[band]
        budget_min = int(b_min_raw * 1_000_000) + random.randint(0, 500_000)
        budget_max = budget_min + random.randint(500_000, 2_000_000)

        # Contact channel
        contact_channel = random.choices(["WhatsApp", "Phone"], weights=[70, 30])[0]

        # Gating
        consent = random.random() < 0.70
        confirmed = (random.random() < 0.75) if consent else False

        # Temperature & Reason Codes
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
        if band in ["HIGH", "ULTRA"]:
            tags.append("high_budget")
        if timeline == "Immediate":
            tags.append("urgent")
        if i % 8 == 0:
            tags.append("callback")

        # Email
        email_val = f"{contact['name'].lower().replace(' ', '.')}@example.com" if random.random() < 0.4 else ""

        lead_row = {
            "timestamp": ts,
            "lead_id": lead_id,
            "session_id": session_id,
            "name": contact["name"],
            "phone": contact["phone"],
            "email": email_val,
            "interest_projects": json.dumps(interest_projs),
            "interest_projects_display": "; ".join(interest_projs),
            "preferred_region": pref_region,
            "unit_type": unit_type,
            "budget_min": budget_min,
            "budget_max": budget_max,
            "budget_band": band,
            "purpose": purpose,
            "timeline": timeline,
            "contact_channel": contact_channel,
            "consent_contact": str(consent).lower(),
            "confirmed_by_user": str(confirmed).lower(),
            "lead_temperature": temp,
            "reason_codes": json.dumps(r_codes),
            "reason_codes_display": "; ".join(r_codes),
            "tags": json.dumps(tags),
            "tags_display": "; ".join(tags),
            "lead_summary": "",  # Will be filled by summary generator
            "customer_summary": "",
            "executive_summary": "",
            "next_action": "",
            "raw_json": "{}",
            "kb_version_hash": "v1.2-parity",
        }

        # Generate template summaries
        cs, es, na = generate_template_summary(lead_row, kb_digest)
        lead_row["customer_summary"] = cs
        lead_row["executive_summary"] = es
        lead_row["next_action"] = na
        lead_row["lead_summary"] = es  # backward compat

        # Build raw_json with all structured fields
        raw = {k: v for k, v in lead_row.items() if k != "raw_json"}
        lead_row["raw_json"] = json.dumps(raw, ensure_ascii=False)

        leads.append(lead_row)

        # Session Data
        sessions.append({
            "session_id": session_id,
            "started_at": ts,
            "last_seen_at": (datetime.fromisoformat(ts.replace("Z", "+00:00")) + timedelta(minutes=random.randint(2, 15))).isoformat().replace("+00:00", "Z"),
            "page_hint": "/concierge",
            "focused_project": interest_projs[0],
        })

        # Audit Data
        for _ in range(random.randint(1, 4)):
            audits.append({
                "timestamp": ts,
                "session_id": session_id,
                "intent": random.choices(["project_query", "list_projects", "compare", "pricing", "lead_capture", "support_contact"], weights=[35, 20, 15, 15, 10, 5])[0],
                "empty_retrieval": "false" if random.random() > 0.1 else "true",
                "top_entities_json": json.dumps(interest_projs),
                "latency_ms": random.randint(120, 2200),
                "status": "ok",
                "error_reason": "",
            })

    return leads, sessions, audits


# --- 5. Main Execution ---

def main():
    use_aoai = "--use-aoai" in sys.argv

    print(f"[SEED] PulseX-WDD Lead Seed Generator — PalmX Grade")
    print(f"[SEED] Total leads: {TOTAL_LEADS} | RNG seed: {RNG_SEED}")

    global PROJECTS
    PROJECTS = load_kb_projects()
    print(f"[KB] Loaded {len(PROJECTS)} selling projects: {', '.join(p['name'] for p in PROJECTS)}")

    kb_digest = build_kb_digest(PROJECTS)

    leads, sessions, audits = generate_dataset(kb_digest)

    # AOAI enrichment (if requested)
    if use_aoai:
        try:
            from scripts.enrich_lead_summaries import enrich_leads
            leads = enrich_leads(leads, kb_digest)
            print(f"[AOAI] Successfully enriched {len(leads)} leads")
        except Exception as e:
            print(f"[WARN] AOAI enrichment failed ({e}), using template summaries")

    def save_csv(path, data):
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=data[0].keys())
            writer.writeheader()
            writer.writerows(data)
        print(f"[OK] Wrote {path.name}: {len(data)} rows, {len(data[0].keys())} columns")

    # Write to both leads_seed.csv AND leads.csv (dashboard default)
    save_csv(LEADS_DIR / "leads_seed.csv", leads)
    save_csv(LEADS_DIR / "leads.csv", leads)
    save_csv(RUNTIME_DIR / "sessions.csv", sessions)
    save_csv(LEADS_DIR / "audit.csv", audits)

    # Print sample
    print(f"\n{'='*80}")
    print(f"SAMPLE — First 3 leads:")
    for l in leads[:3]:
        print(f"  {l['lead_id']} | {l['name']} | {l['phone']} | {l['preferred_region']} | {l['lead_temperature']}")
        print(f"    Summary: {l['customer_summary'][:120]}...")
    print(f"\nLast 2 leads:")
    for l in leads[-2:]:
        print(f"  {l['lead_id']} | {l['name']} | {l['phone']} | {l['preferred_region']} | {l['lead_temperature']}")

    # Verify
    phones = [l['phone'] for l in leads]
    unique_phones = len(set(phones))
    hot = sum(1 for l in leads if l['lead_temperature'] == 'Hot')
    warm = sum(1 for l in leads if l['lead_temperature'] == 'Warm')
    cold = sum(1 for l in leads if l['lead_temperature'] == 'Cold')
    print(f"\n[STATS] {len(leads)} leads | {unique_phones} unique phones | Hot: {hot} | Warm: {warm} | Cold: {cold}")
    print(f"[STATS] Repeat contact rate: {((len(leads) - unique_phones) / len(leads) * 100):.1f}%")
    print(f"[DONE] All files written to {RUNTIME_DIR}")


if __name__ == "__main__":
    main()
