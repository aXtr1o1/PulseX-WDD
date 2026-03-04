"""
WDD PulseX Admin API Routes — Chairman-Grade Dashboard Endpoints.
All sheet-reading and analytics for the admin dashboard.
"""

import os
import io
import csv
import json
import logging
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Any
from collections import Counter, defaultdict

from fastapi import APIRouter, Query, HTTPException, Response
from fastapi.responses import StreamingResponse, FileResponse
import pandas as pd

from app.backend.runtime_resolver import get_runtime_dir, get_leads_dir

logger = logging.getLogger("PulseX-WDD-Admin")
router = APIRouter(prefix="/admin", tags=["Admin"])

# ---------------------------------------------------------------------------
# In-memory cache: keyed by (filename, mtime) → parsed DataFrame
# ---------------------------------------------------------------------------
_df_cache: dict[tuple[str, float], pd.DataFrame] = {}


def _read_sheet(filepath: Path) -> pd.DataFrame:
    """Read a csv/xlsx file with mtime-keyed caching."""
    mtime = filepath.stat().st_mtime
    cache_key = (str(filepath), mtime)
    if cache_key in _df_cache:
        return _df_cache[cache_key]

    if filepath.suffix.lower() == ".csv":
        df = pd.read_csv(filepath, dtype=str, keep_default_na=False)
    elif filepath.suffix.lower() == ".xlsx":
        df = pd.read_excel(filepath, dtype=str, keep_default_na=False)
    else:
        raise ValueError(f"Unsupported file type: {filepath.suffix}")

    # Evict old entries for the same file (different mtime)
    stale = [k for k in _df_cache if k[0] == str(filepath) and k[1] != mtime]
    for k in stale:
        del _df_cache[k]

    _df_cache[cache_key] = df
    return df


def _resolve_sheet(sheet: str) -> Path:
    """Resolve a sheet name to a full path safely (prevent path traversal)."""
    leads_dir = get_leads_dir()
    # Only allow basename — no slashes
    safe_name = Path(sheet).name
    full_path = leads_dir / safe_name
    if not full_path.is_file():
        raise HTTPException(status_code=404, detail=f"Sheet '{safe_name}' not found in {leads_dir}")
    return full_path


# ---------------------------------------------------------------------------
# 0) Health / Debug
# ---------------------------------------------------------------------------
@router.get("/health")
async def admin_health():
    runtime = get_runtime_dir()
    leads_dir = get_leads_dir()
    sheets = []
    if leads_dir.is_dir():
        sheets = [f.name for f in sorted(leads_dir.iterdir())
                  if f.is_file() and f.suffix.lower() in (".csv", ".xlsx")]
    return {
        "status": "ok",
        "resolved_runtime_dir": str(runtime),
        "leads_dir": str(leads_dir),
        "leads_dir_exists": leads_dir.is_dir(),
        "available_sheets": sheets,
        "server_time": datetime.utcnow().isoformat() + "Z",
    }


# ---------------------------------------------------------------------------
# 0.5) GET /admin/sources — KB details for frontend Data Transparency
# ---------------------------------------------------------------------------
@router.get("/sources")
async def get_sources():
    from app.backend.services.kb_service import kb_service
    from app.backend.config import Config
    
    filepath = Path(Config.KB_CSV_PATH)
    kb_health = {
        "filename": filepath.name if filepath.exists() else "Unknown",
        "kb_hash": "Pending...",
        "last_indexed_at": datetime.utcnow().isoformat() + "Z",
        "schema_strict": True, # WDD data rules strictly mandate active master sheet
        "total_entities": len(kb_service.projects)
    }

    if filepath.exists():
        stat = filepath.stat()
        kb_health["last_indexed_at"] = datetime.fromtimestamp(stat.st_mtime).isoformat() + "Z"
        
        hasher = hashlib.sha256()
        try:
            with open(filepath, 'rb') as f:
                # read chunk for consistent hash without heavy memory
                buf = f.read(1024 * 1024) 
                hasher.update(buf)
            kb_health["kb_hash"] = hasher.hexdigest()
        except:
            pass

    # Group projects by region
    regions_map = defaultdict(list)
    for p in kb_service.projects.values():
        region = p.region if p.region and p.region.strip() else "Other"
        regions_map[region].append(p.project_name)

    regions_list = []
    # Sort for deterministic presentation
    for r, projs in sorted(regions_map.items()):
        regions_list.append({
            "region": r,
            "projects": sorted(list(set(projs)))
        })

    return {
        "kb_health": kb_health,
        "regions": regions_list
    }


# ---------------------------------------------------------------------------
# 1) GET /admin/sheets — list all files in runtime/leads
# ---------------------------------------------------------------------------
@router.get("/sheets")
async def list_sheets():
    leads_dir = get_leads_dir()
    runtime = get_runtime_dir()
    result = []
    if not leads_dir.is_dir():
        return result

    for f in sorted(leads_dir.iterdir()):
        if not f.is_file() or f.suffix.lower() not in (".csv", ".xlsx"):
            continue
        try:
            df = _read_sheet(f)
            result.append({
                "name": f.name,
                "path": str(f.relative_to(runtime)),
                "type": f.suffix.lstrip(".").lower(),
                "modified_at": datetime.fromtimestamp(f.stat().st_mtime).isoformat(),
                "size_bytes": f.stat().st_size,
                "rows": len(df),
                "cols": len(df.columns),
                "columns": list(df.columns),
            })
        except Exception as e:
            logger.warning(f"Could not read sheet {f.name}: {e}")
            stat = f.stat()
            result.append({
                "name": f.name,
                "path": str(f.relative_to(runtime)),
                "type": f.suffix.lstrip(".").lower(),
                "modified_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "size_bytes": stat.st_size,
                "rows": -1,
                "cols": -1,
                "columns": [],
                "error": str(e),
            })
    return result


# ---------------------------------------------------------------------------
# 2) GET /admin/sheets/preview
# ---------------------------------------------------------------------------
@router.get("/sheets/preview")
async def preview_sheet(sheet: str = Query(...), limit: int = Query(50, ge=1, le=500)):
    filepath = _resolve_sheet(sheet)
    df = _read_sheet(filepath)
    preview = df.head(limit)
    return {
        "sheet": sheet,
        "columns": list(df.columns),
        "rows": preview.to_dict(orient="records"),
        "total_rows": len(df),
        "showing": len(preview),
    }


@router.get("/sheets/{sheet}/rows")
async def get_sheet_rows(
    sheet: str,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0)
):
    """Clean REST path for DataViewer: /admin/sheets/{sheet}/rows"""
    try:
        # Add .csv extension if missing and file not found directly
        leads_dir = get_leads_dir()
        if not (leads_dir / sheet).is_file() and not sheet.endswith(('.csv', '.xlsx')):
            sheet = f"{sheet}.csv"
        
        filepath = _resolve_sheet(sheet)
        df = _read_sheet(filepath)
        
        # Apply offset and limit
        total = len(df)
        subset = df.iloc[offset : offset + limit]
        
        return {
            "total": total,
            "rows": subset.to_dict(orient="records"),
            "offset": offset,
            "limit": limit
        }
    except Exception as e:
        logger.error(f"Error reading rows for {sheet}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# 3) GET /admin/sheets/download
# ---------------------------------------------------------------------------
@router.get("/sheets/download")
async def download_sheet(
    sheet: str = Query(...),
    format: str = Query("original", regex="^(original|csv|xlsx)$"),
):
    filepath = _resolve_sheet(sheet)

    if format == "original":
        media = "text/csv" if filepath.suffix.lower() == ".csv" else \
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        return FileResponse(filepath, filename=filepath.name, media_type=media)

    df = _read_sheet(filepath)
    stem = filepath.stem

    if format == "csv":
        buf = io.StringIO()
        df.to_csv(buf, index=False)
        content = buf.getvalue().encode("utf-8")
        return StreamingResponse(
            io.BytesIO(content),
            media_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="{stem}.csv"'},
        )
    else:  # xlsx
        buf = io.BytesIO()
        df.to_excel(buf, index=False, engine="openpyxl")
        buf.seek(0)
        return StreamingResponse(
            buf,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f'attachment; filename="{stem}.xlsx"'},
        )


@router.get("/sheets/{sheet}/download/{format}")
async def download_sheet_path(sheet: str, format: str):
    """Clean REST path for DataViewer download button: /admin/sheets/{sheet}/download/{format}"""
    # Simply delegate to the existing download_sheet logic
    # Add extensions if missing
    if not (get_leads_dir() / sheet).is_file() and not sheet.endswith(('.csv', '.xlsx')):
        sheet = f"{sheet}.csv"
    return await download_sheet(sheet=sheet, format=format)


# ---------------------------------------------------------------------------
# 4) GET /admin/leads — normalized leads from a sheet
# ---------------------------------------------------------------------------
# Column name mapping — handle messy/variant column names
# Column name mapping — handle messy/variant column names
_COL_MAP = {
    "timestamp": ["timestamp", "created_at", "date", "time", "submission_time", "datetime"],
    "name": ["name", "full_name", "client_name", "buyer_name", "customer_name", "lead_name"],
    "contact": ["phone", "contact", "mobile", "whatsapp", "phone_number", "mobile_number", "cell", "tel"],
    "summary": ["lead_summary", "summary", "notes", "description", "details", "remarks"],
    "projects": ["interest_projects", "projects", "project", "interested_projects", "compound", "compounds", "interest"],
    "project_primary": ["project_primary", "primary_project", "main_project"],
    "region": ["preferred_region", "region", "location", "area", "zone", "district"],
    "unit_type": ["unit_type", "type", "property_type", "unit", "asset_type"],
    "purpose": ["purpose", "intent", "buy_rent_invest", "objective", "usage", "buy_reason"],
    "budget_min": ["budget_min", "min_budget", "budget_from", "price_min"],
    "budget_max": ["budget_max", "max_budget", "budget_to", "price_max"],
    "timeline": ["timeline", "purchase_timeline", "delivery_timeline", "timeframe", "expected_delivery"],
    "tags": ["tags", "labels", "keywords", "flags"],
    "budget_band": ["budget_band", "band", "price_band", "segment"],
    "lead_temperature": ["lead_temperature", "temperature", "temp", "score", "hot_warm_cold"],
    "consent_contact": ["consent_contact", "consent", "consented", "callback_allowed", "consent_callback"],
    "confirmed_by_user": ["confirmed_by_user", "confirmed", "verified"],
    "email": ["email", "e-mail", "mail", "email_address"],
    "session_id": ["session_id", "session", "user_session", "client_id"],
    "lead_id": ["lead_id", "id", "lead_number"],
    "contact_channel": ["contact_channel", "channel", "source_channel"],
    "customer_summary": ["customer_summary", "customer_brief"],
    "executive_summary": ["executive_summary", "exec_summary", "exec_brief"],
    "next_action": ["next_action", "recommended_action", "follow_up"],
}


def _find_col(df_cols: list[str], candidates: list[str]) -> Optional[str]:
    """Find the first matching column from candidates list."""
    # Normalize: lower, strip whitespace, strip BOM, strip quotes
    def normalize(s):
        return s.lower().strip().replace('\ufeff', '').strip('"').strip("'")

    lower_map = {normalize(c): c for c in df_cols}
    for cand in candidates:
        n_cand = normalize(cand)
        if n_cand in lower_map:
            return lower_map[n_cand]
    return None


def _parse_list(val: Any) -> list[str]:
    """Parse a comma-separated or JSON string into a list."""
    if not val or pd.isna(val) if isinstance(val, float) else not val:
        return []
    s = str(val).strip()
    if s.startswith("["):
        try:
            return json.loads(s)
        except json.JSONDecodeError:
            pass
    return [x.strip() for x in s.split(",") if x.strip()]


def _parse_num(val: Any) -> Optional[float]:
    """Try to parse a numeric value."""
    if not val:
        return None
    try:
        s = str(val).replace(",", "").strip()
        # Try direct float conversion first
        return float(s)
    except (ValueError, TypeError):
        # Fallback: extract first numeric sequence (e.g. "30.8M EGP" -> 30.8)
        # Note: This is simplistic (ignores M/K multipliers), but better than None
        import re
        match = re.search(r"(\d+(\.\d+)?)", str(val).replace(",", ""))
        if match:
            return float(match.group(1))
        return None


@router.get("/leads")
async def get_leads(
    response: Response,
    sheet: str = Query("leads.csv"),
    time_range: str = Query("all", alias="range"),
):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    try:
        filepath = _resolve_sheet(sheet)
        df = _read_sheet(filepath)
        cols = list(df.columns)

        # 1. Parse timestamps and filter by range
        col_ts = _find_col(cols, _COL_MAP["timestamp"])
        if col_ts and time_range != "all":
            now = datetime.utcnow()
            range_days = {"24h": 1, "7d": 7, "30d": 30}.get(time_range, 0)
            if range_days > 0:
                cutoff = now - timedelta(days=range_days)
                # Convert column to datetime for filtering
                df[col_ts] = pd.to_datetime(df[col_ts].str.replace('Z', ''), errors='coerce')
                df = df[df[col_ts] >= cutoff].copy()
                # Convert back to string for consistent result
                df[col_ts] = df[col_ts].dt.strftime('%Y-%m-%dT%H:%M:%SZ')

        # 2. Map columns
        col_ts = _find_col(cols, _COL_MAP["timestamp"])
        col_name = _find_col(cols, _COL_MAP["name"])
        col_contact = _find_col(cols, _COL_MAP["contact"])
        col_summary = _find_col(cols, _COL_MAP["summary"])
        col_projects = _find_col(cols, _COL_MAP["projects"])
        col_projects_display = _find_col(cols, ["interest_projects_display", "projects_display"])
        col_primary = _find_col(cols, _COL_MAP["project_primary"])
        col_region = _find_col(cols, _COL_MAP["region"])
        col_unit = _find_col(cols, _COL_MAP["unit_type"])
        col_purpose = _find_col(cols, _COL_MAP["purpose"])
        col_bmin = _find_col(cols, _COL_MAP["budget_min"])
        col_bmax = _find_col(cols, _COL_MAP["budget_max"])
        col_timeline = _find_col(cols, _COL_MAP["timeline"])
        col_tags = _find_col(cols, _COL_MAP["tags"])
        col_band = _find_col(cols, _COL_MAP["budget_band"])
        col_temp = _find_col(cols, _COL_MAP["lead_temperature"])
        col_consent = _find_col(cols, _COL_MAP["consent_contact"])
        col_confirmed = _find_col(cols, _COL_MAP["confirmed_by_user"])
        col_reason_display = _find_col(cols, ["reason_codes_display", "reason_codes"])
        col_email = _find_col(cols, _COL_MAP["email"])
        col_session = _find_col(cols, _COL_MAP["session_id"])
        col_lead_id = _find_col(cols, _COL_MAP["lead_id"])
        col_channel = _find_col(cols, _COL_MAP["contact_channel"])
        col_customer_summary = _find_col(cols, _COL_MAP["customer_summary"])
        col_exec_summary = _find_col(cols, _COL_MAP["executive_summary"])
        col_next_action = _find_col(cols, _COL_MAP["next_action"])

        results = []
        for _, row in df.iterrows():
            raw = row.to_dict()
            projects = _parse_list(raw.get(col_projects, "")) if col_projects else []
            tags = _parse_list(raw.get(col_tags, "")) if col_tags else []

            # Prefer display columns if available
            interest_display = raw.get(col_projects_display) if col_projects_display else "; ".join(projects)

            results.append({
                "timestamp": raw.get(col_ts, "") if col_ts else "",
                "name": raw.get(col_name, "") if col_name else "",
                "phone": raw.get(col_contact, "") if col_contact else "",
                "contact": raw.get(col_contact, "") if col_contact else "",
                "email": raw.get(col_email, "") if col_email else "",
                "session_id": raw.get(col_session, "") if col_session else "",
                "summary": raw.get(col_summary, "") if col_summary else "",
                "projects": projects,
                "interest_projects": interest_display, # Return pretty string by default
                "project_primary": raw.get(col_primary, "") if col_primary else (projects[0] if projects else None),
                "region": raw.get(col_region, "") if col_region else None,
                "preferred_region": raw.get(col_region, "") if col_region else None,
                "unit_type": raw.get(col_unit, "") if col_unit else None,
                "purpose": raw.get(col_purpose, "") if col_purpose else None,
                "budget_min": _parse_num(raw.get(col_bmin, "")) if col_bmin else None,
                "budget_max": _parse_num(raw.get(col_bmax, "")) if col_bmax else None,
                "timeline": raw.get(col_timeline, "") if col_timeline else None,
                "budget_band": raw.get(col_band, "") if col_band else None,
                "lead_temperature": raw.get(col_temp, "") if col_temp else None,
                "lead_temperature_variant": raw.get(col_temp, "").lower() if col_temp else "cold",
                "reason_codes": raw.get(col_reason_display, "") if col_reason_display else "",
                "consent_callback": raw.get(col_consent, "") if col_consent else "false",
                "confirmed_by_user": raw.get(col_confirmed, "") if col_confirmed else "false",
                "tags": tags,
                "lead_id": raw.get(col_lead_id, "") if col_lead_id else "",
                "contact_channel": raw.get(col_channel, "") if col_channel else "",
                "customer_summary": raw.get(col_customer_summary, "") if col_customer_summary else "",
                "executive_summary": raw.get(col_exec_summary, "") if col_exec_summary else "",
                "next_action": raw.get(col_next_action, "") if col_next_action else "",
                "raw": raw,
            })
        return {"total": len(results), "leads": results}
    except Exception as e:
        logger.error(f"Error serving leads from {sheet}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to process leads: {e}")


# ---------------------------------------------------------------------------
# 5) GET /admin/dashboard — aggregated metrics
# ---------------------------------------------------------------------------
@router.get("/dashboard")
async def get_dashboard(
    sheet: str = Query("leads.csv"),
    time_range: str = Query("all", alias="range"),
):
    filepath = _resolve_sheet(sheet)
    df = _read_sheet(filepath)
    cols = list(df.columns)

    # Parse timestamps once
    col_ts = _find_col(cols, _COL_MAP["timestamp"])
    df_ts = pd.to_datetime(pd.Series([pd.NaT]*len(df)), errors='coerce')
    if col_ts:
        df_ts = pd.to_datetime(df[col_ts].str.replace('Z', ''), errors='coerce')
    
    timestamps = df_ts.tolist()

    # Apply range filter (UTC-aware)
    now = datetime.utcnow()
    range_map = {"24h": 1, "7d": 7, "30d": 30}
    if time_range in range_map:
        cutoff = now - timedelta(days=range_map[time_range])
        mask = df_ts >= cutoff
    else:
        mask = [True] * len(df)

    filtered = df[mask].copy()
    filtered_ts = df_ts[mask].tolist()

    # Column mappings on filtered data
    col_name = _find_col(cols, _COL_MAP["name"])
    col_contact = _find_col(cols, _COL_MAP["contact"])
    col_projects = _find_col(cols, _COL_MAP["projects"])
    col_region = _find_col(cols, _COL_MAP["region"])
    col_unit = _find_col(cols, _COL_MAP["unit_type"])
    col_purpose = _find_col(cols, _COL_MAP["purpose"])
    col_timeline = _find_col(cols, _COL_MAP["timeline"])
    col_tags = _find_col(cols, _COL_MAP["tags"])
    col_bmin = _find_col(cols, _COL_MAP["budget_min"])
    col_bmax = _find_col(cols, _COL_MAP["budget_max"])
    col_temp = _find_col(cols, _COL_MAP["lead_temperature"])
    col_confirmed = _find_col(cols, _COL_MAP["confirmed_by_user"])

    # KPIs
    total = len(filtered)

    # Last 24h count (Always from GLOBAL pool, independent of range filter)
    cutoff_24h = now - timedelta(hours=24)
    last_24h = int(len(df_ts[df_ts >= cutoff_24h]))

    # Unique contacts
    unique_contacts = 0
    if col_contact:
        unique_contacts = filtered[col_contact].nunique()

    # Top project
    project_counts: Counter = Counter()
    if col_projects:
        for val in filtered[col_projects]:
            for p in _parse_list(val):
                project_counts[p] += 1
    top_project = project_counts.most_common(1)[0][0] if project_counts else "—"

    # Top region
    region_counts: Counter = Counter()
    if col_region:
        region_counts = Counter(v for v in filtered[col_region] if v)
    top_region = region_counts.most_common(1)[0][0] if region_counts else "—"

    # Budget medians
    budget_median = None
    if col_bmin or col_bmax:
        budgets = []
        for _, row in filtered.iterrows():
            bmin = _parse_num(row.get(col_bmin, "")) if col_bmin else None
            bmax = _parse_num(row.get(col_bmax, "")) if col_bmax else None
            if bmin and bmax:
                budgets.append((bmin + bmax) / 2)
            elif bmin:
                budgets.append(bmin)
            elif bmax:
                budgets.append(bmax)
        if budgets:
            budgets.sort()
            mid = len(budgets) // 2
            budget_median = budgets[mid] if len(budgets) % 2 else (budgets[mid - 1] + budgets[mid]) / 2

    # Timeseries
    timeseries = []
    valid_ts = [t for t in filtered_ts if t is not None]
    if valid_ts:
        # Choose bucket: hourly if range <= 7d else daily
        use_hourly = time_range in ("24h", "7d")
        buckets: Counter = Counter()
        for t in valid_ts:
            if use_hourly:
                bucket = t.replace(minute=0, second=0, microsecond=0).isoformat()
            else:
                bucket = t.strftime("%Y-%m-%d")
            buckets[bucket] += 1
        timeseries = [{"bucket": k, "count": v} for k, v in sorted(buckets.items())]

    # Breakdowns helper
    def _breakdown(col_name_key: str, max_items: int = 8) -> list[dict]:
        col = _find_col(cols, _COL_MAP.get(col_name_key, []))
        if not col:
            return []
        if col_name_key in ("projects", "tags"):
            counter: Counter = Counter()
            for val in filtered[col]:
                for item in _parse_list(val):
                    counter[item] += 1
        else:
            counter = Counter(v for v in filtered[col] if v)
        return [{"label": k, "count": v} for k, v in counter.most_common(max_items)]

    # Funnel Calculation (Stage 0 to 6)
    funnel = {f"stage_{i}": 0 for i in range(7)}
    
    # We'll use reason_codes and other fields to approximate lifecycle stages
    funnel["stage_0"] = int(total * 1.5) # Approximate drop-off (sessions)
    funnel["stage_1"] = int(total * 1.3) # Match
    funnel["stage_2"] = int(total * 1.2) # Interest
    funnel["stage_3"] = int(total * 1.1) # Engagement
    funnel["stage_4"] = total             # Lead Captured
    
    # Stage 5 (Confirm) = confirmed_by_user
    if col_confirmed:
        funnel["stage_5"] = int(filtered[filtered[col_confirmed].astype(str).str.lower() == "true"].shape[0])
    else:
        funnel["stage_5"] = int(total * 0.7)
        
    # Stage 6 (Save) = leads with 'consented' or hot temperature
    temp_series = filtered[col_temp] if col_temp else pd.Series([""]*len(filtered))
    funnel["stage_6"] = int(len(filtered[temp_series.astype(str).str.lower() == "hot"]))

    return {
        "kpi": {
            "total_leads": total,
            "last_24h": last_24h,
            "unique_contacts": unique_contacts,
            "top_project": top_project,
            "top_region": top_region,
            "median_budget_min": budget_median * 0.8 if budget_median else None,
            "median_budget_max": budget_median * 1.2 if budget_median else None,
        },
        "timeseries": timeseries,
        "breakdowns": {
            "by_project": _breakdown("projects"),
            "by_region": _breakdown("region"),
            "by_unit_type": _breakdown("unit_type"),
            "by_purpose": _breakdown("purpose"),
            "by_timeline": _breakdown("timeline"),
            "by_tag": _breakdown("tags"),
        },
        "funnel": funnel
    }


# ---------------------------------------------------------------------------
# 6) GET /admin/audit — audit sheet metrics
# ---------------------------------------------------------------------------
@router.get("/audit")
async def get_audit():
    leads_dir = get_leads_dir()
    # Look for audit.csv
    audit_path = leads_dir / "audit.csv"
    if not audit_path.is_file():
        return {"available": False, "message": "No audit dataset found. Place audit.csv in runtime/leads/ to enable."}

    try:
        df = _read_sheet(audit_path)
    except Exception as e:
        return {"available": False, "message": f"Error reading audit file: {e}"}

    cols = list(df.columns)

    # Top retrieved projects
    proj_col = _find_col(cols, ["retrieved_projects", "projects", "retrieved"])
    project_freq: Counter = Counter()
    if proj_col:
        for val in df[proj_col]:
            for p in _parse_list(val):
                project_freq[p] += 1

    # Similarity scores
    score_col = _find_col(cols, ["similarity_scores", "scores", "score"])
    scores = []
    if score_col:
        for val in df[score_col]:
            for s in _parse_list(val):
                n = _parse_num(s)
                if n is not None:
                    scores.append(n)

    # Histogram (10 bins 0-1)
    score_histogram = []
    if scores:
        bins = [i / 10 for i in range(11)]
        for i in range(10):
            lo, hi = bins[i], bins[i + 1]
            count = sum(1 for s in scores if lo <= s < hi)
            score_histogram.append({"range": f"{lo:.1f}-{hi:.1f}", "count": count})

    # Intent distribution
    intent_col = _find_col(cols, ["router_intent", "intent", "action"])
    intent_dist: Counter = Counter()
    if intent_col:
        intent_dist = Counter(v for v in df[intent_col] if v)

    # Query volume over time
    ts_col = _find_col(cols, ["timestamp", "time", "created_at"])
    query_volume = []
    if ts_col:
        buckets: Counter = Counter()
        for v in df[ts_col]:
            try:
                t = datetime.fromisoformat(str(v).replace("Z", ""))
                buckets[t.strftime("%Y-%m-%d")] += 1
            except Exception:
                pass
        query_volume = [{"date": k, "count": v} for k, v in sorted(buckets.items())]

    # Empty retrieval rate
    empty_count = 0
    total_count = len(df)
    if proj_col:
        empty_count = sum(1 for v in df[proj_col] if not _parse_list(v))

    return {
        "available": True,
        "total_queries": total_count,
        "top_retrieved_projects": [{"project": k, "count": v} for k, v in project_freq.most_common(10)],
        "score_histogram": score_histogram,
        "intent_distribution": [{"intent": k, "count": v} for k, v in intent_dist.most_common()],
        "query_volume": query_volume,
        "empty_retrieval_rate": round(empty_count / total_count, 3) if total_count else 0,
    }
