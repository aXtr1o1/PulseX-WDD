#!/usr/bin/env python3
"""
PulseX-WDD – Seed Leads Data Generator
Generates realistic, deterministic lead data to populate the Admin Dashboard.

Usage:
    python scripts/seed_leads.py
    # or: make seed
"""
from __future__ import annotations

import csv
import json
import random
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT / "apps" / "api"))

from app.config import get_settings
from app.utils.csv_io import ensure_csv, LEADS_HEADERS

# ── Deterministic Seed ──────────────────────────────────────────────────────────
random.seed(42)

NAMES_EN = ["Ahmed Hassan", "Nour El Din", "Youssef Ali", "Sara Tarek", "Mahmoud Gamal", "Omar Farouk", "Salma Reda", "Karim Mostafa", "Hoda Samir", "Tarek Mansour", "Layla Kamel", "Mona Zaki", "Khaled Youssef", "Amr Diab", "Sherine Abdel", "Hamed Saeed", "Nadia Lotfy", "Rami Malek", "Dina El Sherbiny", "Tamer Hosny"]
NAMES_AR = ["أحمد حسن", "نور الدين", "يوسف علي", "سارة طارق", "محمود جمال", "عمر فاروق", "سلمى رضا", "كريم مصطفى", "هدى سمير", "طارق منصور", "ليلى كامل", "منى زكي", "خالد يوسف", "عمرو دياب", "شيرين عبد الوهاب", "حامد سعيد", "نادية لطفي", "رامي مالك", "دينا الشربيني", "تامر حسني"]

PROJECTS = ["Murano", "Neopolis", "Club Town", "Promenade New Cairo", "Blumar Sokhna", "Blumar Hills", "Marina Wadi Degla", "Tijan", "Canal Residence", "Pyramids Walk"]
REGIONS = ["Ain El Sokhna", "East Cairo", "East Cairo", "East Cairo", "Ain El Sokhna", "Ain El Sokhna", "Ain El Sokhna", "Cairo", "Cairo", "West Cairo"]
UNIT_TYPES = ["Chalet", "Apartment", "Duplex", "Villa", "Townhouse", "Penthouse"]
PURPOSES = ["buy", "invest", "buy", "buy", "rent", "invest"]
TIMELINES = ["Within 1-2 months", "Within 3-6 months", "Looking around", "Just exploring", "Immediate"]

def random_phone() -> str:
    return f"+201{random.randint(0,2)}{random.randint(1000000, 9999999)}"

def random_timestamp() -> str:
    now = datetime.now(timezone.utc)
    days_ago = random.randint(0, 30)
    hours_ago = random.randint(0, 23)
    mins_ago = random.randint(0, 59)
    dt = now - timedelta(days=days_ago, hours=hours_ago, minutes=mins_ago)
    return dt.isoformat()

def generate_row() -> dict:
    lang = random.choice(["en", "en", "en", "ar"])
    name = random.choice(NAMES_AR) if lang == "ar" else random.choice(NAMES_EN)
    phone = random.choice([random_phone(), random_phone(), ""]) # Some explicit phones, some blank if they only explored
    email = f"{name.split()[0].lower()}{random.randint(10,99)}@gmail.com" if random.random() > 0.4 else ""
    
    proj_idx = random.randint(0, len(PROJECTS)-1)
    project = PROJECTS[proj_idx]
    region = REGIONS[proj_idx]
    unit = random.choice(UNIT_TYPES)
    
    # Budgets
    b_min = random.choice([3000000, 5000000, 8000000, 10000000, 15000000])
    b_max = b_min + random.choice([2000000, 5000000, 10000000])
    
    # 20% chance they don't leave phone -> just an anonymous session tag
    if random.random() < 0.2:
        name = ""
        phone = ""
        email = ""
        consent = "false"
    else:
        consent = "true"

    return {
        "timestamp": random_timestamp(),
        "session_id": f"sess_{uuid.uuid4().hex[:12]}",
        "lang": lang,
        "name": name,
        "phone": phone,
        "email": email,
        "interest_projects": json.dumps([project]),
        "preferred_region": region,
        "unit_type": unit,
        "budget_min": str(b_min),
        "budget_max": str(b_max),
        "budget_band": f"EGP {b_min/1000000:.1f}M - {b_max/1000000:.1f}M",
        "purpose": random.choice(PURPOSES),
        "timeline": random.choice(TIMELINES),
        "tags": random.choice(["high_budget", "whatsapp_pref", "family", ""]),
        "consent_callback": consent,
        "consent_marketing": "false",
        "consent_timestamp": random_timestamp() if consent == "true" else "",
        "source_url": "https://wadidegladevelopments.com",
        "page_title": f"Wadi Degla | {project}",
        "summary": "Auto-generated seed lead",
        "raw_json": "{}",
    }

def seed_leads() -> None:
    settings = get_settings()
    seed_path = settings.leads_csv_path.parent / "leads_seed.csv"
    target_path = settings.leads_csv_path

    import json # ensure local import

    print(f"Generating deterministic database of 150 leads...")
    rows = []
    # Force 3 duplicate rows to test deduplication logic on frontend
    dup = generate_row()
    dup["timestamp"] = datetime.now(timezone.utc).isoformat()
    rows.append(dup)
    rows.append(dup)
    rows.append(dup)

    for _ in range(147):
        rows.append(generate_row())

    # Sort generated rows by timestamp descending so they appear chronologically in Dashboard
    rows.sort(key=lambda x: x["timestamp"], reverse=True)

    # Write to seed file first
    ensure_csv(seed_path, LEADS_HEADERS)
    with open(seed_path, "w", newline="", encoding="utf-8") as sf:
        writer = csv.DictWriter(sf, fieldnames=LEADS_HEADERS)
        writer.writeheader()
        writer.writerows(rows)

    # Overwrite the actual runtime file for a fresh start whenever seed is run
    ensure_csv(target_path, LEADS_HEADERS)
    with open(target_path, "w", newline="", encoding="utf-8") as tf:
        writer = csv.DictWriter(tf, fieldnames=LEADS_HEADERS)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Seeded {len(rows)} varied leads into {target_path}")

if __name__ == "__main__":
    seed_leads()
