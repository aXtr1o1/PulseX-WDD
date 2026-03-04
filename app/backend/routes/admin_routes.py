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
async def get_leads(response: Response, sheet: str = Query("leads.csv")):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    try:
        filepath = _resolve_sheet(sheet)
        logger.info(f"Reading leads from: {filepath}")
        
        df = _read_sheet(filepath)
        cols = list(df.columns)
        logger.info(f"Columns found in {sheet}: {cols}")

        # Map columns
        col_ts = _find_col(cols, _COL_MAP["timestamp"])
        col_name = _find_col(cols, _COL_MAP["name"])
        col_contact = _find_col(cols, _COL_MAP["contact"])
        col_summary = _find_col(cols, _COL_MAP["summary"])
        col_projects = _find_col(cols, _COL_MAP["projects"])
        col_primary = _find_col(cols, _COL_MAP["project_primary"])
        col_region = _find_col(cols, _COL_MAP["region"])
        col_unit = _find_col(cols, _COL_MAP["unit_type"])
        col_purpose = _find_col(cols, _COL_MAP["purpose"])
        col_bmin = _find_col(cols, _COL_MAP["budget_min"])
        col_bmax = _find_col(cols, _COL_MAP["budget_max"])
        col_timeline = _find_col(cols, _COL_MAP["timeline"])
        col_tags = _find_col(cols, _COL_MAP["tags"])

        logger.info(f"Mapping results for {sheet}: Contact='{col_contact}', Projects='{col_projects}', Summary='{col_summary}'")

        results = []
        for _, row in df.iterrows():
            raw = row.to_dict()
            projects = _parse_list(raw.get(col_projects, "")) if col_projects else []
            tags = _parse_list(raw.get(col_tags, "")) if col_tags else []

            results.append({
                "timestamp": raw.get(col_ts, "") if col_ts else "",
                "name": raw.get(col_name, "") if col_name else "",
                "contact": raw.get(col_contact, "") if col_contact else "",
                "summary": raw.get(col_summary, "") if col_summary else "",
                "projects": projects,
                "project_primary": raw.get(col_primary, "") if col_primary else (projects[0] if projects else None),
                "region": raw.get(col_region, "") if col_region else None,
                "unit_type": raw.get(col_unit, "") if col_unit else None,
                "purpose": raw.get(col_purpose, "") if col_purpose else None,
                "budget_min": _parse_num(raw.get(col_bmin, "")) if col_bmin else None,
                "budget_max": _parse_num(raw.get(col_bmax, "")) if col_bmax else None,
                "timeline": raw.get(col_timeline, "") if col_timeline else None,
                "tags": tags,
                "raw": raw,
            })
        return results
    except Exception as e:
        logger.error(f"Error serving leads from {sheet}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to process leads: {e}")


# ---------------------------------------------------------------------------
# 5) GET /admin/analytics — aggregated metrics
# ---------------------------------------------------------------------------
@router.get("/analytics")
async def get_analytics(
    sheet: str = Query("leads.csv"),
    range: str = Query("all", alias="range"),
):
    filepath = _resolve_sheet(sheet)
    df = _read_sheet(filepath)
    cols = list(df.columns)

    # Parse timestamps
    col_ts = _find_col(cols, _COL_MAP["timestamp"])
    timestamps = []
    if col_ts:
        for v in df[col_ts]:
            try:
                timestamps.append(datetime.fromisoformat(str(v).replace("Z", "+00:00").replace("Z", "")))
            except Exception:
                timestamps.append(None)
    else:
        timestamps = [None] * len(df)

    # Apply range filter
    now = datetime.now()
    range_map = {"24h": 1, "7d": 7, "30d": 30}
    if range in range_map:
        cutoff = now - timedelta(days=range_map[range])
        mask = [t is not None and t.replace(tzinfo=None) >= cutoff for t in timestamps]
    else:
        mask = [True] * len(df)

    filtered = df[mask].copy()
    filtered_ts = [t for t, m in zip(timestamps, mask) if m]

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

    # KPIs
    total = len(filtered)

    # Last 24h count
    cutoff_24h = now - timedelta(hours=24)
    last_24h = sum(1 for t in filtered_ts if t and t.replace(tzinfo=None) >= cutoff_24h)

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
        use_hourly = range in ("24h", "7d")
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

    return {
        "kpis": {
            "total": total,
            "last_24h": last_24h,
            "unique_contacts": unique_contacts,
            "top_project": top_project,
            "top_region": top_region,
            "budget_median": budget_median,
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
