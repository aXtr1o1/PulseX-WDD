#!/usr/bin/env python3
"""
PulseX-WDD AOAI Lead Summary Enrichment
Enriches lead summaries using Azure OpenAI GPT-4o with KB grounding.
Deterministic (temperature=0), cached to runtime/seed_cache/.

Usage:
    Called by seed_leads.py --use-aoai, or standalone:
    python3 scripts/enrich_lead_summaries.py
"""

import hashlib
import json
import os
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CACHE_DIR = REPO_ROOT / "runtime" / "seed_cache"
DIGEST_PATH = REPO_ROOT / "engine-KB" / "derived" / "kb_digest.json"


def _get_aoai_client():
    """Initialize Azure OpenAI client from env vars."""
    try:
        from openai import AzureOpenAI
    except ImportError:
        raise ImportError("openai package not installed. Run: pip install openai")

    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    api_key = os.getenv("AZURE_OPENAI_API_KEY")
    deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o")
    api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-12-01-preview")

    if not endpoint or not api_key:
        raise ValueError("AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_API_KEY must be set")

    return AzureOpenAI(
        azure_endpoint=endpoint,
        api_key=api_key,
        api_version=api_version,
    ), deployment


def _cache_key(lead: dict) -> str:
    """Deterministic cache key from lead attributes."""
    significant = json.dumps({
        "name": lead.get("name", ""),
        "phone": lead.get("phone", ""),
        "interest_projects": lead.get("interest_projects", "[]"),
        "preferred_region": lead.get("preferred_region", ""),
        "purpose": lead.get("purpose", ""),
        "unit_type": lead.get("unit_type", ""),
        "budget_band": lead.get("budget_band", ""),
        "timeline": lead.get("timeline", ""),
        "lead_temperature": lead.get("lead_temperature", ""),
        "consent_contact": lead.get("consent_contact", ""),
    }, sort_keys=True)
    return hashlib.sha256(significant.encode()).hexdigest()[:16]


def _read_cache(key: str) -> dict | None:
    """Read cached enrichment result."""
    cache_file = CACHE_DIR / f"{key}.json"
    if cache_file.is_file():
        try:
            return json.loads(cache_file.read_text())
        except (json.JSONDecodeError, OSError):
            pass
    return None


def _write_cache(key: str, data: dict):
    """Write enrichment result to cache."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    (CACHE_DIR / f"{key}.json").write_text(json.dumps(data, ensure_ascii=False))


def _build_prompt(lead: dict, kb_digest: dict) -> str:
    """Build the AOAI prompt for a single lead."""
    name = lead.get("name", "Unknown")
    projects_raw = lead.get("interest_projects", "[]")
    try:
        projects = json.loads(projects_raw)
    except (json.JSONDecodeError, TypeError):
        projects = []

    # Gather KB context for each project
    project_context = []
    for p in projects:
        info = kb_digest.get(p, {})
        if info:
            highlights = "; ".join(info.get("highlights", []))
            project_context.append(f"  - {p} ({info.get('region', '?')}): {info.get('type', '?')}, {highlights}")

    kb_section = "\n".join(project_context) if project_context else "  No KB data available."

    return f"""You are a senior real estate CRM analyst for Wadi Degla Developments (WDD), Egypt's premier developer.

Generate a structured JSON response for this lead. Be specific, professional, and grounded in the project data provided.

LEAD DATA:
- Name: {name}
- Region: {lead.get('preferred_region', '?')}
- Projects: {', '.join(projects)}
- Unit Type: {lead.get('unit_type', '?')}
- Purpose: {lead.get('purpose', '?')}
- Budget Band: {lead.get('budget_band', '?')} (MIN: {lead.get('budget_min', '?')}, MAX: {lead.get('budget_max', '?')})
- Timeline: {lead.get('timeline', '?')}
- Temperature: {lead.get('lead_temperature', '?')}
- Consent to callback: {lead.get('consent_contact', '?')}
- Confirmed: {lead.get('confirmed_by_user', '?')}

PROJECT KNOWLEDGE BASE:
{kb_section}

OUTPUT (JSON only, no markdown):
{{
  "customer_summary": "2-4 sentence natural language summary of this customer's profile, needs, and engagement level. Mention specific projects and their features.",
  "executive_summary": "1-2 sentence executive brief: temperature, intent, key project, budget tier, timeline.",
  "next_action": "Single actionable next step for the sales team."
}}"""


def enrich_leads(leads: list[dict], kb_digest: dict, batch_size: int = 5) -> list[dict]:
    """Enrich leads with AOAI-generated summaries, with caching."""
    try:
        client, deployment = _get_aoai_client()
    except (ImportError, ValueError) as e:
        print(f"[AOAI] Skipping enrichment: {e}")
        return leads

    enriched = 0
    cached = 0
    failed = 0

    for i, lead in enumerate(leads):
        key = _cache_key(lead)

        # Check cache first
        cached_result = _read_cache(key)
        if cached_result:
            lead["customer_summary"] = cached_result.get("customer_summary", lead["customer_summary"])
            lead["executive_summary"] = cached_result.get("executive_summary", lead["executive_summary"])
            lead["next_action"] = cached_result.get("next_action", lead["next_action"])
            lead["lead_summary"] = lead["executive_summary"]
            cached += 1
            continue

        # Call AOAI
        prompt = _build_prompt(lead, kb_digest)
        try:
            response = client.chat.completions.create(
                model=deployment,
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
                max_tokens=500,
                response_format={"type": "json_object"},
            )
            result = json.loads(response.choices[0].message.content)

            lead["customer_summary"] = result.get("customer_summary", lead["customer_summary"])
            lead["executive_summary"] = result.get("executive_summary", lead["executive_summary"])
            lead["next_action"] = result.get("next_action", lead["next_action"])
            lead["lead_summary"] = lead["executive_summary"]

            _write_cache(key, result)
            enriched += 1

            if (i + 1) % 10 == 0:
                print(f"[AOAI] Enriched {enriched}/{i+1} leads (cached: {cached})")

        except Exception as e:
            failed += 1
            if failed <= 3:
                print(f"[AOAI] Error on lead {i}: {e}")
            # Keep template summary as fallback

        # Rate limiting
        if enriched % batch_size == 0 and enriched > 0:
            time.sleep(0.5)

    print(f"[AOAI] Done: {enriched} enriched, {cached} cached, {failed} failed")
    return leads


def main():
    """Standalone enrichment of existing leads_seed.csv."""
    import csv

    leads_path = REPO_ROOT / "runtime" / "leads" / "leads_seed.csv"
    if not leads_path.is_file():
        print(f"[ERROR] {leads_path} not found. Run seed_leads.py first.")
        sys.exit(1)

    # Load KB digest
    if DIGEST_PATH.is_file():
        kb_digest = json.loads(DIGEST_PATH.read_text())
    else:
        print("[WARN] No KB digest found. Run seed_leads.py to create it.")
        kb_digest = {}

    # Load leads
    with open(leads_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        leads = list(reader)

    print(f"[ENRICH] Loaded {len(leads)} leads from {leads_path}")

    # Enrich
    enriched = enrich_leads(leads, kb_digest)

    # Write back
    with open(leads_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=enriched[0].keys())
        writer.writeheader()
        writer.writerows(enriched)

    # Also update leads.csv
    leads_csv = REPO_ROOT / "runtime" / "leads" / "leads.csv"
    with open(leads_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=enriched[0].keys())
        writer.writeheader()
        writer.writerows(enriched)

    print(f"[DONE] Enriched leads written to {leads_path} and {leads_csv}")


if __name__ == "__main__":
    main()
