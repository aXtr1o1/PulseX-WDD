"""
PulseX-WDD – Pydantic v2 Schemas
All request/response models and data structures.
"""
from __future__ import annotations

import re
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator, model_validator


# ──────────────────────────────────────────────────────────────────────────────
# Chat / Session
# ──────────────────────────────────────────────────────────────────────────────

class PageContext(BaseModel):
    url: Optional[str] = None
    project_slug: Optional[str] = None
    page_title: Optional[str] = None


class ChatRequest(BaseModel):
    session_id: str = Field(..., min_length=8, max_length=64)
    lang: str = Field("en", pattern=r"^(en|ar)$")
    message: str = Field(..., min_length=1, max_length=2000)
    page_context: Optional[PageContext] = None


class EvidenceSnippet(BaseModel):
    entity_id: str
    display_name: str
    source_url: Optional[str] = None
    snippet: str
    confidence: float = Field(0.0, ge=0.0, le=1.0)


class ChatResponse(BaseModel):
    session_id: str
    request_id: str
    intent: str
    answer: str
    evidence: List[EvidenceSnippet] = []
    shortlist: Optional[List[Dict[str, Any]]] = None
    lead_suggestions: Optional[Dict[str, Any]] = None
    focused_project: Optional[str] = None
    intent_lane: Optional[str] = None
    lead_trigger: bool = False
    handoff_cta: bool = False
    lang: str = "en"
    latency_ms: Optional[int] = None


# ──────────────────────────────────────────────────────────────────────────────
# Lead
# ──────────────────────────────────────────────────────────────────────────────

PHONE_PATTERN = re.compile(r"^\+?[0-9\s\-().]{7,20}$")
EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class LeadRequest(BaseModel):
    session_id: str
    lang: str = "en"
    name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    interest_projects: List[str] = []
    preferred_region: Optional[str] = None
    unit_type: Optional[str] = None
    budget_min: Optional[float] = None
    budget_max: Optional[float] = None
    purpose: Optional[str] = None  # buy / rent / invest
    timeline: Optional[str] = None
    consent_callback: bool = False
    consent_marketing: bool = False
    source_url: Optional[str] = None
    page_title: Optional[str] = None
    tags: List[str] = []
    summary: Optional[str] = None

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        v = v.strip()
        if not PHONE_PATTERN.match(v):
            raise ValueError(f"Invalid phone number: {v}")
        return v

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        v = v.strip().lower()
        if not EMAIL_PATTERN.match(v):
            raise ValueError(f"Invalid email: {v}")
        return v

    @field_validator("purpose")
    @classmethod
    def validate_purpose(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        allowed = {"buy", "rent", "invest"}
        if v.lower() not in allowed:
            raise ValueError(f"purpose must be one of {allowed}")
        return v.lower()


class LeadRow(BaseModel):
    """Internal row model for leads.csv"""
    timestamp: str
    session_id: str
    lang: str
    name: Optional[str]
    phone: Optional[str]
    email: Optional[str]
    interest_projects: str  # JSON
    preferred_region: Optional[str]
    unit_type: Optional[str]
    budget_min: Optional[float]
    budget_max: Optional[float]
    budget_band: str
    purpose: Optional[str]
    timeline: Optional[str]
    tags: str  # JSON
    consent_callback: bool
    consent_marketing: bool
    consent_timestamp: Optional[str]
    source_url: Optional[str]
    page_title: Optional[str]
    summary: Optional[str]
    raw_json: str


class LeadResponse(BaseModel):
    success: bool
    lead_id: str
    message: str


# ──────────────────────────────────────────────────────────────────────────────
# Admin
# ──────────────────────────────────────────────────────────────────────────────

class AdminLoginRequest(BaseModel):
    password: str


class AdminLoginResponse(BaseModel):
    success: bool
    message: str


class KPISummary(BaseModel):
    total_leads: int
    last_24h: int
    unique_contacts: int
    top_project: Optional[str]
    top_region: Optional[str]
    median_budget_min: Optional[float]
    median_budget_max: Optional[float]


class DailyCount(BaseModel):
    date: str
    count: int


class ProjectCount(BaseModel):
    project: str
    count: int


class RegionCount(BaseModel):
    region: str
    count: int


class AdminDashboardResponse(BaseModel):
    kpi: KPISummary
    daily_leads: List[DailyCount]
    top_projects: List[ProjectCount]
    top_regions: List[RegionCount]


# ──────────────────────────────────────────────────────────────────────────────
# Retrieval internal
# ──────────────────────────────────────────────────────────────────────────────

class RetrievalResult(BaseModel):
    entity_id: str
    display_name: str
    region: Optional[str]
    unit_types: List[str] = []
    amenities: List[str] = []
    project_status: Optional[str]
    sales_status: Optional[str]
    price_status: Optional[str]
    sources: List[str] = []
    verified_url: Optional[str]
    confidence: float
    answerability: float
    blended_score: float
    keyword_score: float
    vector_score: float
    parent_project: Optional[str]
    is_alias_of: Optional[str]
    snippet: str


class AuditRow(BaseModel):
    timestamp: str
    request_id: str
    session_id: str
    endpoint: str
    intent: str
    kb_version_hash: str
    keyword_hits: int
    vector_hits: int
    blended_hits: int
    top_entities_json: str
    model: str
    tokens_in: int
    tokens_out: int
    latency_ms: int
    status: str
    error_reason: Optional[str]
    cost_estimate_usd: float
    message_hash: str
