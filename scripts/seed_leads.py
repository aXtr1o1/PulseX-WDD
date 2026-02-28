#!/usr/bin/env python3
"""
PulseX-WDD – Seed Leads
Seeds runtime/leads.csv from runtime/leads_seed.csv.

Usage:
    python scripts/seed_leads.py
    # or: make seed
"""
from __future__ import annotations

import csv
import shutil
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT / "apps" / "api"))

from app.config import get_settings
from app.utils.csv_io import ensure_csv, LEADS_HEADERS


def seed_leads() -> None:
    settings = get_settings()
    seed_path = settings.leads_csv_path.parent / "leads_seed.csv"
    target_path = settings.leads_csv_path

    if not seed_path.exists():
        print(f"Seed file not found: {seed_path}")
        sys.exit(1)

    ensure_csv(target_path, LEADS_HEADERS)

    with open(seed_path, "r", encoding="utf-8") as sf:
        reader = csv.DictReader(sf)
        rows = list(reader)

    with open(target_path, "a", newline="", encoding="utf-8") as tf:
        writer = csv.DictWriter(tf, fieldnames=LEADS_HEADERS, extrasaction="ignore")
        for row in rows:
            writer.writerow(row)

    print(f"Seeded {len(rows)} rows from {seed_path} -> {target_path}")


if __name__ == "__main__":
    seed_leads()
