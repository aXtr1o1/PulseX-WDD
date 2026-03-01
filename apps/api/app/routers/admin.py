"""
PulseX-WDD – Admin Router
Protected endpoints for dashboard data, CSV viewer, and XLSX export.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import JSONResponse, StreamingResponse

from ..config import get_settings
from ..middleware.auth import create_admin_token, require_admin, verify_admin_token
from ..schemas.models import (
    AdminDashboardResponse,
    AdminLoginRequest,
    AdminLoginResponse,
    DailyCount,
    KPISummary,
    ProjectCount,
    RegionCount,
)
from ..utils.csv_io import csv_to_xlsx_bytes, read_csv_rows

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/admin", tags=["admin"])


# ──────────────────────────────────────────────────────────────────────────────
# Auth
# ──────────────────────────────────────────────────────────────────────────────

@router.post("/login", response_model=AdminLoginResponse)
async def admin_login(body: AdminLoginRequest, response: Response) -> AdminLoginResponse:
    settings = get_settings()
    if body.password != settings.admin_password:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid password.")
    token = create_admin_token()
    response.set_cookie(
        key="pulsex_admin",
        value=token,
        httponly=True,
        max_age=settings.admin_session_ttl,
        samesite="lax",
        secure=(settings.app_env == "prod"),
    )
    return AdminLoginResponse(success=True, message="Authenticated.")


@router.post("/logout")
async def admin_logout(response: Response):
    response.delete_cookie("pulsex_admin")
    return {"success": True}


# ──────────────────────────────────────────────────────────────────────────────
# Dashboard
# ──────────────────────────────────────────────────────────────────────────────

@router.get("/dashboard", response_model=AdminDashboardResponse)
async def dashboard(request: Request, _: None = Depends(require_admin)) -> AdminDashboardResponse:
    settings = get_settings()
    rows = read_csv_rows(settings.leads_csv_path)

    now_utc = datetime.now(timezone.utc)
    cutoff_24h = now_utc - timedelta(hours=24)

    total = len(rows)
    last_24h = 0
    phones: set = set()
    emails: set = set()
    project_counts: Dict[str, int] = {}
    region_counts: Dict[str, int] = {}
    daily_counts: Dict[str, int] = {}
    budget_mins: List[float] = []
    budget_maxs: List[float] = []

    for row in rows:
        ts_str = row.get("timestamp", "")
        try:
            ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            if ts >= cutoff_24h:
                last_24h += 1
            day = ts.strftime("%Y-%m-%d")
            daily_counts[day] = daily_counts.get(day, 0) + 1
        except Exception:
            pass

        if row.get("phone"):
            phones.add(row["phone"])
        if row.get("email"):
            emails.add(row["email"].lower())

        # Projects
        import json as _json
        try:
            projects = _json.loads(row.get("interest_projects", "[]"))
            for p in projects:
                project_counts[p] = project_counts.get(p, 0) + 1
        except Exception:
            pass

        # Region
        reg = row.get("preferred_region", "")
        if reg:
            region_counts[reg] = region_counts.get(reg, 0) + 1

        # Budget
        try:
            bmin = row.get("budget_min")
            if bmin:
                budget_mins.append(float(bmin))
        except Exception:
            pass
        try:
            bmax = row.get("budget_max")
            if bmax:
                budget_maxs.append(float(bmax))
        except Exception:
            pass

    unique_contacts = len(phones | emails)
    top_project = max(project_counts, key=project_counts.get) if project_counts else None
    top_region  = max(region_counts, key=region_counts.get) if region_counts else None

    def median(lst: List[float]) -> Optional[float]:
        if not lst:
            return None
        s = sorted(lst)
        mid = len(s) // 2
        return (s[mid] + s[~mid]) / 2

    # Sort daily
    sorted_daily = sorted(daily_counts.items())
    daily_series = [DailyCount(date=d, count=c) for d, c in sorted_daily[-30:]]

    top_projects_list = sorted(project_counts.items(), key=lambda x: x[1], reverse=True)[:5]
    top_regions_list  = sorted(region_counts.items(), key=lambda x: x[1], reverse=True)[:5]

    return AdminDashboardResponse(
        kpi=KPISummary(
            total_leads=total,
            last_24h=last_24h,
            unique_contacts=unique_contacts,
            top_project=top_project,
            top_region=top_region,
            median_budget_min=median(budget_mins),
            median_budget_max=median(budget_maxs),
        ),
        daily_leads=daily_series,
        top_projects=[ProjectCount(project=p, count=c) for p, c in top_projects_list],
        top_regions=[RegionCount(region=r, count=c) for r, c in top_regions_list],
    )


# ──────────────────────────────────────────────────────────────────────────────
# CSV viewer / download
# ──────────────────────────────────────────────────────────────────────────────

ALLOWED_SHEETS = {"leads", "audit", "leads_seed", "sessions"}


def _resolve_sheet(sheet: str, settings) -> Path:
    mapping = {
        "leads":      settings.leads_csv_path,
        "audit":      settings.audit_csv_path,
        "leads_seed": settings.leads_csv_path.parent / "leads_seed.csv",
        "sessions":   settings.sessions_csv_path,
    }
    return mapping[sheet]


@router.get("/sheets/{sheet}/rows")
async def sheet_rows(
    sheet: str,
    limit: int = 200,
    offset: int = 0,
    _: None = Depends(require_admin),
):
    if sheet not in ALLOWED_SHEETS:
        raise HTTPException(status_code=400, detail=f"Unknown sheet: {sheet}")
    settings = get_settings()
    path = _resolve_sheet(sheet, settings)
    rows = read_csv_rows(path)
    total = len(rows)
    return {"total": total, "offset": offset, "limit": limit, "rows": rows[offset:offset+limit]}


@router.get("/sheets/{sheet}/download/csv")
async def download_csv(sheet: str, _: None = Depends(require_admin)):
    if sheet not in ALLOWED_SHEETS:
        raise HTTPException(status_code=400, detail=f"Unknown sheet: {sheet}")
    settings = get_settings()
    path = _resolve_sheet(sheet, settings)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Sheet not found.")
    data = path.read_bytes()
    return Response(
        content=data,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{sheet}.csv"'},
    )


@router.get("/sheets/{sheet}/download/xlsx")
async def download_xlsx(sheet: str, _: None = Depends(require_admin)):
    if sheet not in ALLOWED_SHEETS:
        raise HTTPException(status_code=400, detail=f"Unknown sheet: {sheet}")
    settings = get_settings()
    path = _resolve_sheet(sheet, settings)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Sheet not found.")
    xlsx_bytes = csv_to_xlsx_bytes(path)
    return Response(
        content=xlsx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{sheet}.xlsx"'},
    )


# ──────────────────────────────────────────────────────────────────────────────
# Lead details
# ──────────────────────────────────────────────────────────────────────────────

@router.get("/leads")
async def list_leads(
    time_filter: str = "all",
    source: Optional[str] = None,
    project: Optional[str] = None,
    region: Optional[str] = None,
    unit_type: Optional[str] = None,
    purpose: Optional[str] = None,
    _: None = Depends(require_admin),
):
    settings = get_settings()
    rows = read_csv_rows(settings.leads_csv_path)
    now_utc = datetime.now(timezone.utc)

    def ts_cutoff(hours: int) -> datetime:
        return now_utc - timedelta(hours=hours)

    cutoff = None
    if time_filter == "24h":
        cutoff = ts_cutoff(24)
    elif time_filter == "7d":
        cutoff = ts_cutoff(7 * 24)
    elif time_filter == "30d":
        cutoff = ts_cutoff(30 * 24)

    filtered = []
    for r in rows:
        if cutoff:
            try:
                ts = datetime.fromisoformat(r.get("timestamp", "").replace("Z", "+00:00"))
                if ts.tzinfo is None:
                    ts = ts.replace(tzinfo=timezone.utc)
                if ts < cutoff:
                    continue
            except Exception:
                pass
        if source and source.lower() not in (r.get("source_url") or "").lower():
            continue
        if project and project.lower() not in (r.get("interest_projects") or "").lower():
            continue
        if region and region.lower() not in (r.get("preferred_region") or "").lower():
            continue
        if unit_type and unit_type.lower() not in (r.get("unit_type") or "").lower():
            continue
        if purpose and purpose.lower() != (r.get("purpose") or "").lower():
            continue
        filtered.append(r)

    return {"total": len(filtered), "leads": filtered}


# ──────────────────────────────────────────────────────────────────────────────
# Trust Layer: Sources & Quality
# ──────────────────────────────────────────────────────────────────────────────

@router.get("/sources")
async def get_sources(request: Request, _: None = Depends(require_admin)):
    import json
    state = request.app.state
    settings = get_settings()
    
    entities = getattr(state, "kb_entities", [])
    regions_map: Dict[str, set] = {}
    
    for e in entities:
        reg = e.get("region") or "Unspecified"
        proj = e.get("parent_project") or e.get("display_name")
        if reg not in regions_map:
            regions_map[reg] = set()
        if proj:
            regions_map[reg].add(proj)
            
    regions = [
        {"region": r, "projects": sorted(list(p))} 
        for r, p in regions_map.items()
    ]
    regions.sort(key=lambda x: x["region"])
    
    kb_health = {
        "filename": settings.kb_csv_path.name,
        "kb_hash": getattr(state, "kb_version_hash", "unknown"),
        "last_indexed_at": getattr(state, "kb_timestamp", datetime.now(timezone.utc).isoformat()),
        "schema_strict": True,
        "total_entities": len(entities)
    }
    
    return {"kb_health": kb_health, "regions": regions}


@router.get("/quality")
async def get_quality(request: Request, _: None = Depends(require_admin)):
    import json
    settings = get_settings()
    rows = read_csv_rows(settings.audit_csv_path)
    
    total = len(rows)
    if total == 0:
        return {
            "total_queries": 0, "empty_retrieval_pct": 0,
            "top_retrieved_entities": [], "intent_distribution": [], "content_gaps": []
        }
    
    empty_hits = 0
    intents: Dict[str, int] = {}
    entities_count: Dict[str, int] = {}
    content_gaps = []
    
    for row in rows:
        intent = row.get("intent", "unknown")
        intents[intent] = intents.get(intent, 0) + 1
        
        try:
            blended = int(row.get("blended_hits", 0))
            if blended == 0 and intent in {"property_question", "sales_intent"}:
                empty_hits += 1
                msg_hash = row.get("message_hash", "unknown_query")
                content_gaps.append({"query": f"Query Hash {msg_hash[:8]}", "reason": "Zero Hits"})
        except Exception:
            pass
            
        try:
            ents = json.loads(row.get("top_entities_json", "[]"))
            for e in ents:
                entities_count[e] = entities_count.get(e, 0) + 1
        except Exception:
            pass
            
    empty_pct = (empty_hits / total) * 100 if total > 0 else 0
    
    top_ents = [{"name": k, "count": v} for k, v in sorted(entities_count.items(), key=lambda x: x[1], reverse=True)[:10]]
    intent_dist = [{"intent": k, "count": v} for k, v in sorted(intents.items(), key=lambda x: x[1], reverse=True)]
    
    return {
        "total_queries": total,
        "empty_retrieval_pct": empty_pct,
        "top_retrieved_entities": top_ents,
        "intent_distribution": intent_dist,
        "content_gaps": content_gaps[:10]
    }
