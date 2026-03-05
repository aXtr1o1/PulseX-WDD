from typing import List, Optional, Any, Dict
from pydantic import BaseModel, Field
from enum import Enum

# --- Enums ---
class Stage(str, Enum):
    GREETING = "GREETING"
    DISCOVERY = "DISCOVERY"
    SHORTLISTED = "SHORTLISTED"
    CAPTURE_PHONE = "CAPTURE_PHONE"
    RECAP_PENDING = "RECAP_PENDING"
    CONSENT_PENDING = "CONSENT_PENDING"
    SAVED = "SAVED"

class IntentType(str, Enum):
    GREETING = "GREETING"
    LIST_PORTFOLIO = "LIST_PORTFOLIO"
    PROJECT_DISCOVERY = "PROJECT_DISCOVERY"
    HIGH_INTENT = "HIGH_INTENT"
    GENERAL_QA = "GENERAL_QA"
    NON_SALES = "NON_SALES"
    CONFIRMATION_YES = "CONFIRMATION_YES"
    CONFIRMATION_NO = "CONFIRMATION_NO"

# --- KB Models ---
class Project(BaseModel):
    project_id: str
    project_name: str
    brand_family: Optional[str] = None
    official_project_url: Optional[str] = None
    region: Optional[str] = None
    city_area: Optional[str] = None
    project_type: Optional[str] = None
    project_status: Optional[str] = None
    current_sales_status: Optional[str] = None
    starting_price_value: Optional[int] = None
    price_status: Optional[str] = None
    key_amenities: List[str] = []
    unit_types: List[str] = []
    has_brochure: bool = False
    raw_data: dict = {}

# --- Session State ---
class Slots(BaseModel):
    purpose: Optional[str] = None          # Live / Invest / Weekend
    region: Optional[str] = None           # Ain El Sokhna / North Coast / East Cairo / Cairo / West Cairo
    unit_type: Optional[str] = None        # apartment / villa / chalet / townhouse / duplex / penthouse / loft / commercial
    budget_min: Optional[str] = None       # EGP string
    budget_max: Optional[str] = None
    budget_band: Optional[str] = None      # LOW / MID / HIGH / ULTRA
    timeline: Optional[str] = None         # Immediate / 0-3 months / 3-6 months / Exploring
    interest_projects: List[str] = Field(default_factory=list)  # 1-3 KB project names
    name: Optional[str] = None
    phone: Optional[str] = None            # Normalized +20...
    confirmed_by_user: bool = False
    consent_contact: bool = False

class SessionState(BaseModel):
    session_id: str
    greeted: bool = False
    stage: Stage = Stage.GREETING
    slots: Slots = Field(default_factory=Slots)
    focused_project: Optional[str] = None
    turn_count: int = 0

# --- Router Output ---
class RoutedIntent(BaseModel):
    intent: IntentType
    matched_projects: List[str] = Field(default_factory=list)
    extracted_region: Optional[str] = None
    extracted_unit_type: Optional[str] = None
    is_high_intent: bool = False
    raw_query: str = ""

# --- Evidence Pack (for frontend chips) ---
class EvidencePack(BaseModel):
    project_id: str
    project_name: str
    region: Optional[str] = None
    city_area: Optional[str] = None
    url: Optional[str] = None
    has_brochure: bool = False
    price_status: Optional[str] = None
    unit_types: List[str] = []
    amenities_short: List[str] = []    # Top 4 amenities
    source: str = "faiss"               # faiss / fuzzy / basic

# --- Chat Models ---
class Message(BaseModel):
    role: str  # user | assistant | system
    content: str

class ChatRequest(BaseModel):
    session_id: str
    messages: List[Message]
    locale: str = "en"

class ChatResponse(BaseModel):
    message: str
    next_action: Optional[str] = None
    retrieved_projects: List[str] = []
    evidence: List[dict] = Field(default_factory=list)
    mode: str = "concierge"  # concierge | lead_capture
    stage: Optional[str] = None

# --- Lead Models ---
class Lead(BaseModel):
    lead_id: Optional[str] = None
    session_id: str
    name: str
    phone: str
    email: Optional[str] = None
    interest_projects: List[str] = Field(default_factory=list)
    preferred_region: Optional[str] = None
    unit_type: Optional[str] = None
    budget_min: Optional[str] = None
    budget_max: Optional[str] = None
    budget_band: Optional[str] = None
    purpose: Optional[str] = None
    timeline: Optional[str] = None
    contact_channel: Optional[str] = "whatsapp"
    consent_contact: bool = True
    confirmed_by_user: bool = True
    lead_temperature: Optional[str] = None    # Hot / Warm / Cold
    reason_codes: List[str] = Field(default_factory=list)
    next_step: Optional[str] = None
    lead_summary: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    kb_version_hash: Optional[str] = "v1.0"

# --- Legacy Router (kept for backward compat with admin) ---
class RouterOutput(BaseModel):
    intent: str = Field(..., description="project_query | list_projects | compare | pricing | amenity_check | lead_capture | support_contact")
    entities: List[str] = Field(default_factory=list)
    region: Optional[str] = None
    filters: dict = Field(default_factory=dict)
    needs: List[str] = Field(default_factory=list)
    query_rewrite: str = Field(default="")
    ambiguous: bool = False
    clarification_question: Optional[str] = None
