import pytest
from app.schemas.models import SessionState
from app.services.funnel_policy import get_next_question

def test_funnel_policy_progression():
    state = SessionState(session_id="test", stage=0, collected_fields={}, last_updated=0.0, created_at=0.0)
    
    # 1. Ask Purpose
    slot_key, prompt, options = get_next_question(state, "info_query", {})
    assert slot_key == "purpose"
    
    # User provides purpose
    state.collected_fields["purpose"] = "invest"
    
    # 2. Ask Region
    slot_key, prompt, options = get_next_question(state, "info_query", {"purpose": "invest"})
    assert slot_key == "region"
    
    # User provides region and unit type at once (bypassing unit type question)
    state.collected_fields["region"] = "east cairo"
    state.collected_fields["unit_type"] = "villa"
    
    # 3. Ask Budget (Because Unit Type was provided)
    slot_key, prompt, options = get_next_question(state, "info_query", {})
    assert slot_key == "budget_min"

def test_funnel_policy_pinned_project():
    state = SessionState(session_id="test", stage=0, collected_fields={
        "project_interest": ["Il Bosco"]
    }, last_updated=0.0, created_at=0.0)
    
    # Pinned project should skip region/unit and go straight to budget or timeline
    slot_key, prompt, options = get_next_question(state, "info_query", {})
    assert slot_key == "budget_min"
    
def test_funnel_policy_capture_intent_override():
    state = SessionState(session_id="test", stage=3, collected_fields={
        "purpose": "buy",
        "region": "east cairo"
    }, last_updated=0.0, created_at=0.0)
    
    # User explicitly asks for pricing - trigger capture flow regardless of missing slots
    slot_key, prompt, options = get_next_question(state, "pricing", {})
    assert slot_key == "phone"
    
def test_funnel_policy_completion():
    state = SessionState(session_id="test", stage=6, collected_fields={
        "purpose": "buy",
        "region": "east cairo",
        "unit_type": "villa",
        "budget_min": "10M",
        "timeline": "Immediate",
        "phone": "+20123456789",
        "confirmed_by_user": True,
        "consent_contact": False
    }, last_updated=0.0, created_at=0.0)
    
    # Waiting on consent
    slot_key, prompt, options = get_next_question(state, "info_query", {})
    assert slot_key == "consent"
