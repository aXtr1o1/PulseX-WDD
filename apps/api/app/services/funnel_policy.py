"""
PulseX-WDD – Funnel Policy & Question Governor
Enforces the 1-Question-Per-Turn rule deterministically.
"""
from typing import Dict, Any, Tuple
from app.schemas.models import SessionState

# Ordered fields for progressive profiling
# Returning: (slot_key, llm_instruction_concept, [options])
FUNNEL_ORDER = [
    ("purpose", "Ask if they are looking to buy for living or for investment.", ["Live", "Invest"]),
    ("region", "Ask which region or specific area they are focused on (e.g. New Cairo, North Coast).", ["East Cairo", "North Coast", "Ain Sokhna"]),
    ("unit_type", "Ask what property type they prefer (e.g. Villa, Chalet, Apartment).", ["Villa", "Apartment", "Chalet"]),
    ("budget_min", "Gently ask for their approximate budget range or price expectation.", []),
    ("timeline", "Ask when they are looking to take delivery or move in.", ["Immediate", "Within 1 year", "Exploring"]),
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
            return "phone", "Offer to share the official brochure and exact availability on WhatsApp, and ask what WhatsApp number you should use.", []
            
        if not fields.get("confirmed_by_user"):
            return "confirm_recap", "Ask the user to confirm if the details in the summary are correct.", []
            
        if not fields.get("consent_contact"):
            return "consent", "Politely ask for their consent to be contacted by a Senior Consultant.", ["Yes", "No"]
            
        return "done", "Thank the user and notify them that a Senior Consultant will be in touch shortly.", []

    # 2. If we have project_interest pinned, we skip some vague questions (region, etc.) 
    # and go straight to budget/timeline if missing.
    has_pinned_project = "project_interest" in fields and len(fields["project_interest"]) > 0
    
    if has_pinned_project:
        if not fields.get("budget_min"):
             return "budget_min", f"Praise their interest in {', '.join(fields['project_interest'])} and ask for their approximate budget range.", []
        if not fields.get("timeline"):
             return "timeline", "Ask when they were hoping to take delivery or move in.", ["Immediate", "Exploring"]
             
        # If we have basic project info + budget, transition to capture
        if not fields.get("phone"):
            return "phone", "Offer to confirm the exact availability and pricing for their selected project on WhatsApp, and ask for their number.", []

    # 2.5 International / New to Egypt Flow (P4)
    is_intl = state.is_international or fields.get("is_international")
    if is_intl:
        if not fields.get("region"):
            return "region", "Note that since they are abroad, we can arrange a virtual walkthrough. Ask which region in Egypt they are focused on.", ["East Cairo", "North Coast"]
        if not fields.get("budget_min"):
            return "budget_min", "Ask what their budget range is to find the perfect match for a virtual tour.", []
        if not fields.get("timeline"):
            return "timeline", "Ask when they are looking to invest or move.", ["Immediate", "Exploring"]
        if not fields.get("phone"):
            return "phone", "Offer to send them the virtual walkthrough links on WhatsApp and ask for their number.", []

    # 3. Standard Progressive Profiling (Order of Operations)
    for slot_key, prompt_text, options in FUNNEL_ORDER:
        if not fields.get(slot_key):
            return slot_key, prompt_text, options

    # 4. Reached end of standard slots without triggering capture?
    # Default to capture if we have enough info.
    if not fields.get("phone"):
        return "phone", "Mention we process excellent matches. Offer to share brochures and ask for their WhatsApp number.", []
        
    if not fields.get("confirmed_by_user"):
        return "confirm_recap", "Ask the user to confirm the details below.", []

    return "consent", "Do we have your consent to contact you?", ["Yes"]

