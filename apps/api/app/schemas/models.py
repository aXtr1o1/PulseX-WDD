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


class LeadSuggestions(BaseModel):
    intent: Optional[str] = None
    budget_min: Optional[int] = None
    budget_max: Optional[int] = None
    timeline: Optional[str] = None
    purpose: Optional[str] = None
    unit_type: Optional[str] = None
    region: Optional[str] = None
    project_interest: Optional[List[str]] = Field(default_factory=list)
    tags: Optional[List[str]] = Field(default_factory=list)
    preferences: Optional[str] = None
    qualification_score: Optional[str] = None
    qualification_reason: Optional[str] = None
    summary: Optional[str] = None
    ready_for_handoff: bool = False
    
    # Concierge Intelligence Validation
    consent_contact: bool = False
    confirmed_by_user: bool = False
    
    class Config:
        extra = "allow"


class SessionState(BaseModel):
    """6-Stage Funnel State Machine in-memory/csv structure"""
    session_id: str
    stage: int = 0
    collected_fields: Dict[str, Any] = Field(default_factory=dict)
    language: str = "en"
    greeted: bool = False
    is_international: bool = False
    last_updated: float


class AnonymousIntent(BaseModel):
    """Unconverted sessions capturing partial intent without PII"""
    session_id: str
    language: str = "en"
    stage_reached: int
    purpose: Optional[str] = None
    unit_type: Optional[str] = None
    location_preference: Optional[str] = None
    budget_band: Optional[str] = None
    timeline: Optional[str] = None
    created_at: float


class LeadPacket(BaseModel):
    """Fully confirmed lead ready for CRM/Admin consumption"""
    lead_id: str
    name: Optional[str] = None
    phone: str
    contact_channel: Optional[str] = None
    preferred_callback_time: Optional[str] = None
    language: str = "en"
    source_page: Optional[str] = None
    project_interest: List[str] = Field(default_factory=list)
    purpose: Optional[str] = None
    unit_type: Optional[str] = None
    location_preference: Optional[str] = None
    budget_band: Optional[str] = None
    timeline: Optional[str] = None
    must_haves: List[str] = Field(default_factory=list)
    key_driver: Optional[str] = None
    lead_temperature: str = "Cold" # Hot/Warm/Cold
    reason_codes: List[str] = Field(default_factory=list)
    consent_contact: bool = False
    confirmed_by_user: bool = False
    confirmed_at: float
    created_at: float
    session_id: str

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        v = v.strip()
        if not PHONE_PATTERN.match(v):
            raise ValueError(f"Invalid phone number: {v}")
        return v


class LeadResponse(BaseModel):
    success: bool
    lead_id: str
    message: str


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
    purpose: Optional[str] = None
    timeline: Optional[str] = None
    consent_callback: bool = False
    consent_marketing: bool = False
    source_url: Optional[str] = None
    page_title: Optional[str] = None
    tags: List[str] = []
    summary: Optional[str] = None


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


class FunnelMetrics(BaseModel):
    stage_0: int
    stage_1: int
    stage_2: int
    stage_3: int
    stage_4: int
    stage_5: int
    stage_6: int


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
