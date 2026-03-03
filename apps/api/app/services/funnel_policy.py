"""
PulseX-WDD – Funnel Policy & Question Governor
Enforces the 1-Question-Per-Turn rule deterministically.
"""
from typing import Dict, Any, Tuple
from app.schemas.models import SessionState

# Ordered fields for progressive profiling
FUNNEL_ORDER = [
    ("purpose", "Are you looking to live or invest?", ["Live", "Invest"]),
    ("region", "Which region are you interested in? (e.g. New Cairo, North Coast, Sokhna)", ["East Cairo", "North Coast", "Ain Sokhna"]),
    ("unit_type", "What type of unit do you prefer? (Villa, Apartment, Chalet)", ["Villa", "Apartment", "Chalet"]),
    ("budget_min", "What is your approximate budget range?", []),
    ("timeline", "When are you looking to move in or invest?", ["Immediate", "Within 1 year", "Exploring"]),
]

def get_next_question(state: SessionState, router_intent: str, extracted_slots: Dict[str, Any]) -> Tuple[str, str, list]:
    """
    Returns (slot_key, exact_prompt_string, [options])
    Guarantees no repeats by looking purely at state.collected_fields.
    """
    fields = state.collected_fields
    
    # 1. Lead Capture Triggers (Overrides normal flow)
    # If the user asked for pricing/avail/handoff or explicitly wants a call
    is_capture_intent = router_intent in ["lead_capture", "pricing", "handoff", "availability", "brochure", "visit_request", "request_sales_call"]
    ready_for_handoff = fields.get("ready_for_handoff", False)
    
    if is_capture_intent or ready_for_handoff or fields.get("lead_capture_trigger") or fields.get("salvage_trigger"):
        if not fields.get("phone"):
            return "phone", "I can share the brochure and confirm availability on WhatsApp. What WhatsApp number should I use?", []
            
        if not fields.get("confirmed_by_user"):
            return "confirm_recap", "Great. Please confirm the details in the recap card below to proceed.", []
            
        if not fields.get("consent_contact"):
            return "consent", "Do we have your consent to contact you?", ["Yes", "No"]
            
        return "done", "Thank you, a Senior Consultant will be in touch shortly.", []

    # 2. If we have project_interest pinned, we skip some vague questions (region, etc.) 
    # and go straight to budget/timeline if missing.
    has_pinned_project = "project_interest" in fields and len(fields["project_interest"]) > 0
    
    if has_pinned_project:
        if not fields.get("budget_min"):
             return "budget_min", f"You have great taste considering {', '.join(fields['project_interest'])}. What is your approximate budget range?", []
        if not fields.get("timeline"):
             return "timeline", "When were you looking to take delivery or move in?", ["Immediate", "Exploring"]
             
        # If we have basic project info + budget, transition to capture
        if not fields.get("phone"):
            return "phone", "To provide the exact availability for that project, what's your WhatsApp number?", []

    # 2.5 International / New to Egypt Flow (P4)
    is_intl = state.is_international or fields.get("is_international")
    if is_intl:
        if not fields.get("region"):
            return "region", "Since you're joining us from abroad, we can arrange a virtual walkthrough. Which region in Egypt are you focused on?", ["East Cairo", "North Coast"]
        if not fields.get("budget_min"):
            return "budget_min", "To find the perfect match for your virtual tour, what is your approximate budget range?", []
        if not fields.get("timeline"):
            return "timeline", "When are you looking to invest or move?", ["Immediate", "Exploring"]
        if not fields.get("phone"):
            return "phone", "To send you the virtual walkthrough links and keep you updated, what is your WhatsApp number?", []

    # 3. Standard Progressive Profiling (Order of Operations)
    # We walk down the FUNNEL_ORDER. The first one missing in `fields` is what we ask.
    for slot_key, prompt_text, options in FUNNEL_ORDER:
        if not fields.get(slot_key):
            # E.g. If we haven't asked purpose, ask it.
            return slot_key, prompt_text, options

    # 4. Reached end of standard slots without triggering capture?
    # Default to capture if we have enough info.
    if not fields.get("phone"):
        return "phone", "We've found excellent matches. To share the brochures, what's your phone number?", []
        
    if not fields.get("confirmed_by_user"):
        return "confirm_recap", "Please confirm the details below.", []

    return "consent", "Do we have your consent to contact you?", ["Yes"]

