"""
PulseX-WDD – Lead Capture Pipeline
Strict gating for confirmation and consent.
"""
from pathlib import Path
from typing import Dict, Any, Optional
import time
from app.schemas.models import SessionState
from app.utils.csv_io import append_csv_row, LEADS_HEADERS, SESSIONS_HEADERS

def build_recap(slots: Dict[str, Any]) -> Dict[str, Any]:
    """Builds a structured recap for the UI ConsentBlock to render."""
    return {
        "project": ", ".join(slots.get("project_interest", [])) or "Any",
        "region": slots.get("region", "Any"),
        "budget": slots.get("budget_min", "TBD"),
        "phone": slots.get("phone", "Missing")
    }

def save_lead_if_confirmed(state: SessionState, slots: Dict[str, Any], leads_path: Path) -> Optional[str]:
    """Only saves lead if the user has confirmed recap AND given consent."""
    if not slots.get("confirmed_by_user") or not slots.get("consent_contact"):
        return None
        
    if not slots.get("phone"):
        return None # Critical failure
        
    from app.services.lead import generate_lead_id
    lead_id = generate_lead_id()
    
    # Save to CSV
    row = {
        "timestamp": time.time(),
        "session_id": state.session_id,
        "lang": state.language,
        "name": slots.get("name", ""),
        "phone": slots.get("phone"),
        "email": slots.get("email", ""),
        "interest_projects": "|".join(slots.get("project_interest", [])),
        "preferred_region": slots.get("region", ""),
        "unit_type": slots.get("unit_type", ""),
        "budget_min": slots.get("budget_min", ""),
        "budget_max": slots.get("budget_max", ""),
        "budget_band": slots.get("budget_min", ""),
        "purpose": slots.get("purpose", ""),
        "timeline": slots.get("timeline", ""),
        "tags": "|".join(slots.get("tags", [])),
        "consent_callback": slots.get("consent_contact", False),
        "consent_marketing": False,
        "consent_timestamp": time.time(),
        "source_url": "",
        "page_title": "",
        "summary": slots.get("summary", ""),
        "raw_json": "{}"
    }
    
    try:
        append_csv_row(leads_path, row, LEADS_HEADERS)
        return lead_id
    except Exception:
        return None
        
def save_anonymous_intent(state: SessionState, slots: Dict[str, Any], intent_path: Path) -> None:
    """Save drop-offs for analytics."""
    row = {
         "timestamp": time.time(),
         "session_id": state.session_id,
         "stage_reached": state.stage,
         "language": state.language,
         "purpose": slots.get("purpose", ""),
         "unit_type": slots.get("unit_type", ""),
         "region": slots.get("region", ""),
         "budget_band": slots.get("budget_min", ""),
         "timeline": slots.get("timeline", "")
    }
    try:
        # Simplified intent schema tracking using SESSIONS_HEADERS format logic if available or general append
        append_csv_row(intent_path, row, ["timestamp", "session_id", "stage_reached", "language", "purpose", "unit_type", "region", "budget_band", "timeline"])
    except Exception:
        pass
