"""
PulseX-WDD – Concierge Funnel Engine
Implements the 0-6 Stage State Machine for Progressive Profiling.
"""
from typing import Any, Dict
from app.schemas.models import SessionState

STAGE_0_GREETING_INTENT = 0
STAGE_1_MATCH_BUILDING = 1
STAGE_2_FEASIBILITY = 2
STAGE_3_SHORTLIST = 3
STAGE_4_CONVERSION_CAPTURE = 4
STAGE_5_CONFIRMATION = 5
STAGE_6_SAVE_AND_CLOSE = 6

def advance_funnel_stage(state: SessionState, payload_suggestions: Dict[str, Any], user_message: str) -> None:
    """
    Evaluates newly extracted fields from the LLM payload, updates the state,
    and calculates the deterministic next Stage.
    """
    fields = state.collected_fields
    
    # Merge new payload fields into state
    for k in ["purpose", "unit_type", "region", "budget_min", "budget_max", 
              "timeline", "project_interest", "phone", "consent_contact", "confirmed_by_user"]:
        v = payload_suggestions.get(k)
        if v and v != "Unknown":
            fields[k] = v

    # Handoff explicit signal pushes directly to capture
    if payload_suggestions.get("ready_for_handoff") and state.stage < STAGE_4_CONVERSION_CAPTURE:
        state.stage = STAGE_4_CONVERSION_CAPTURE

    # Progression Rules
    if state.stage == STAGE_0_GREETING_INTENT:
        # Move to 1 after ANY domain extraction
        if any(k in fields for k in ["purpose", "unit_type", "region", "project_interest"]):
            state.stage = STAGE_1_MATCH_BUILDING

    if state.stage == STAGE_1_MATCH_BUILDING:
        # Move to 2 once purpose + region OR purpose + unit_type
        p = fields.get("purpose")
        r = fields.get("region")
        u = fields.get("unit_type")
        if p and (r or u):
            state.stage = STAGE_2_FEASIBILITY

    if state.stage == STAGE_2_FEASIBILITY:
        # Move to 3 once budget OR timeline is collected
        if fields.get("budget_min") or fields.get("timeline"):
            state.stage = STAGE_3_SHORTLIST

    if state.stage == STAGE_3_SHORTLIST:
        # Move to 4 if asking price/avail/visit or selection
        # (This is partly handled by ready_for_handoff, but we can also infer)
        intent = payload_suggestions.get("intent")
        if intent in ["handoff", "lead_capture", "pricing"]:
            state.stage = STAGE_4_CONVERSION_CAPTURE
        elif fields.get("project_interest"):
             state.stage = STAGE_4_CONVERSION_CAPTURE

    if state.stage == STAGE_4_CONVERSION_CAPTURE:
        # Move to 5 once phone is collected and consent is requested
        if fields.get("phone"):
            state.stage = STAGE_5_CONFIRMATION

    if state.stage == STAGE_5_CONFIRMATION:
        # Move to 6 if user confirms recap AND gives consent
        if fields.get("confirmed_by_user") and fields.get("consent_contact"):
            state.stage = STAGE_6_SAVE_AND_CLOSE

    state.collected_fields = fields
