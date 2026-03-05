"""
PulseX-WDD — FastAPI Application Entry Point.
PalmX-Grade Intelligence Layer: Stateful concierge with deterministic routing,
strict RAG gating, hard lead-capture gates, and zero hallucinations.
"""

import json
import re
import logging
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from app.backend.models import (
    ChatRequest, ChatResponse, Lead, Message,
    Stage, IntentType, Slots,
)
from app.backend.services.kb_service import kb_service
from app.backend.services.rag_service import rag_service
from app.backend.services.llm_service import llm_service
from app.backend.services.leads_service import leads_service
from app.backend.services.state_service import state_service
from app.backend.services.intent_router import intent_router
from app.backend.services.scoring_service import score_lead, compute_budget_band
from app.backend.routes.admin_routes import router as admin_router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("PulseX-WDD")

app = FastAPI(title="PulseX-WDD API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(admin_router, prefix="/api")

# --- Initialize on startup ---
@app.on_event("startup")
async def startup():
    # Wire intent router with KB project names
    intent_router.set_kb_projects(
        kb_service.get_all_project_names(),
        kb_service.get_all_project_slugs(),
    )
    # Build FAISS index if needed
    rag_service.build_index_if_needed()
    logger.info("✅ PulseX-WDD PalmX-Grade Intelligence started")

# ─────────────────────────────────────────────────────────────────────
# SYSTEM PROMPT — PalmX Output Grammar
# ─────────────────────────────────────────────────────────────────────

CONCIERGE_SYSTEM_PROMPT = """\
You are WDD Concierge, the Senior Sales Consultant for Wadi Degla Developments.
You convert inquiries into site visits or calls by being knowledgeable, concise, and conversion-focused.
You are NOT a chatbot. You are a sales closer.

### TODAY IS: {current_date}

### OUTPUT GRAMMAR (STRICT — follow exactly):
1. **Answer**: 1–4 lines MAX, grounded in CONTEXT only. No invented facts.
2. **Highlights** (optional): 2–4 bullets of key selling points from CONTEXT.
3. **Question**: Exactly ONE next question — either a slot-fill question or a commitment question.
4. NEVER repeat the greeting after the first turn.
5. NEVER use fluff like "Great taste!", "Excellent choice!", "Amazing!".
6. NEVER dump huge lists — max 4 items in any list.
7. NEVER invent prices, payment plans, or availability if not in CONTEXT.

### PRICING RULE (CRITICAL):
- If CONTEXT says "Pricing: On Request only" → you MUST say "Pricing is available on request — I can arrange for our team to share the latest pricing sheet."
- NEVER invent prices. NEVER guess payment plans.

### FIELD COLLECTION (seamless):
Collect these naturally in conversation — NEVER ask all at once:
- Purpose: Live / Invest / Weekend
- Region preference
- Unit type
- Budget range (in EGP)
- Timeline: Immediate / 0-3 months / 3-6 months / Exploring
- Name (optional)
- WhatsApp/Phone (REQUIRED for lead save)

### CAPTURE RULES:
- When the user shows HIGH INTENT (asks about price/brochure/availability/viewing/callback), pivot to asking for their WhatsApp number with: "I'd love to send you the details — may I have your WhatsApp number?"
- After phone is captured, ask ONLY remaining missing slots (one at a time).
- Before saving, ALWAYS present a recap and ask "Is this correct?"
- After confirmation, ask "May we contact you on WhatsApp?" (consent gate).
- ONLY after "Yes" to consent: the lead is ready to save.

### SOLD OUT RULE:
- Only present projects that are currently selling.
- If user asks about a sold-out project, say "That project is currently sold out" and suggest selling alternatives.

### NON-SALES RULE:
- For complaints, maintenance, after-sales: direct to 19917 or wadidegladevelopments.com/contact-us/
"""

# ─────────────────────────────────────────────────────────────────────
# TOOL DEFINITION (save_lead)
# ─────────────────────────────────────────────────────────────────────

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "save_lead",
            "description": "Save a confirmed, consented lead. Call ONLY after user confirms recap AND gives contact consent.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Buyer's full name"},
                    "phone": {"type": "string", "description": "WhatsApp/phone number"},
                    "interest_projects": {"type": "string", "description": "Comma-separated project names"},
                    "preferred_region": {"type": "string", "description": "Preferred region"},
                    "unit_type": {"type": "string", "description": "Unit type preference"},
                    "budget_min": {"type": "string", "description": "Min budget in EGP"},
                    "budget_max": {"type": "string", "description": "Max budget in EGP"},
                    "purpose": {"type": "string", "description": "Live, Invest, or Weekend"},
                    "timeline": {"type": "string", "description": "Purchase timeline"},
                    "lead_summary": {"type": "string", "description": "2-line conversation summary"},
                },
                "required": ["name", "phone"]
            }
        }
    }
]

# ─────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────

def _normalize_phone(raw: str) -> Optional[str]:
    """Normalize Egyptian phone to +20... format."""
    digits = re.sub(r'[^\d+]', '', raw.strip())
    if digits.startswith('+20') and len(digits) >= 13:
        return digits[:13]
    if digits.startswith('20') and len(digits) >= 12:
        return '+' + digits[:12]
    if digits.startswith('0') and len(digits) >= 11:
        return '+20' + digits[1:11]
    if len(digits) >= 10 and not digits.startswith('+'):
        return '+20' + digits[-10:]
    return raw.strip() if raw.strip() else None


def _build_system_msg(context_text: str) -> str:
    current_date = datetime.utcnow().strftime("%B %d, %Y")
    return CONCIERGE_SYSTEM_PROMPT.format(current_date=current_date) + f"\n\nCONTEXT:\n{context_text}"


def _build_recap(slots: Slots) -> str:
    """Build a compact recap card."""
    lines = ["Here's what I have noted:"]
    if slots.name:
        lines.append(f"- **Name**: {slots.name}")
    if slots.interest_projects:
        lines.append(f"- **Interest**: {', '.join(slots.interest_projects)}")
    if slots.region:
        lines.append(f"- **Region**: {slots.region}")
    if slots.unit_type:
        lines.append(f"- **Unit type**: {slots.unit_type}")
    if slots.purpose:
        lines.append(f"- **Purpose**: {slots.purpose}")
    if slots.budget_min or slots.budget_max:
        budget = f"{slots.budget_min or '?'} – {slots.budget_max or '?'} EGP"
        lines.append(f"- **Budget**: {budget}")
    if slots.timeline:
        lines.append(f"- **Timeline**: {slots.timeline}")
    if slots.phone:
        lines.append(f"- **WhatsApp**: {slots.phone}")
    lines.append("\nIs this correct?")
    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────
# HEALTH
# ─────────────────────────────────────────────────────────────────────

@app.get("/api/health")
async def health_check():
    return {"status": "ready", "rag_ready": rag_service.is_ready}

@app.get("/health")
async def health():
    return {"status": "ok", "rag_ready": rag_service.is_ready}


# ─────────────────────────────────────────────────────────────────────
# CHAT PIPELINE — The Intelligence Layer
# ─────────────────────────────────────────────────────────────────────

def _process_chat(session_id: str, messages: list[Message]) -> dict:
    """
    Core chat pipeline:
    1. Load state
    2. Deterministic intent route
    3. Stage-aware action
    4. Build LLM context (if needed)
    5. Generate answer
    6. Update state
    7. Audit log
    Returns dict with {message, evidence, mode, stage, retrieved_projects}
    """
    user_msg = messages[-1].content
    state = state_service.load_state(session_id)
    routed = intent_router.route(user_msg, state.turn_count, state.stage.value)

    # Update slots from extracted entities
    if routed.extracted_region and not state.slots.region:
        state.slots.region = routed.extracted_region
    if routed.extracted_unit_type and not state.slots.unit_type:
        state.slots.unit_type = routed.extracted_unit_type
    if routed.matched_projects:
        for p in routed.matched_projects:
            if p not in state.slots.interest_projects:
                state.slots.interest_projects.append(p)
        if not state.focused_project:
            state.focused_project = routed.matched_projects[0]

    retrieved_projects = []
    evidence = []
    response_text = ""
    error_reason = ""

    try:
        # ─── STAGE-AWARE ACTIONS ──────────────────────────────────────

        # A) CONFIRMATION GATES (highest priority)
        if state.stage == Stage.RECAP_PENDING:
            if routed.intent == IntentType.CONFIRMATION_YES:
                state.slots.confirmed_by_user = True
                state.stage = Stage.CONSENT_PENDING
                response_text = "Thank you for confirming. May we contact you on WhatsApp to share details and schedule a call?"
            elif routed.intent == IntentType.CONFIRMATION_NO:
                state.stage = Stage.DISCOVERY
                response_text = "No problem — let me know what needs to be corrected and I'll update your details."
            else:
                response_text = "Just to confirm — is the information I summarized correct? Please reply **Yes** or **No**."

        elif state.stage == Stage.CONSENT_PENDING:
            if routed.intent == IntentType.CONFIRMATION_YES:
                state.slots.consent_contact = True
                state.stage = Stage.SAVED
                # Score and save lead
                temp, reasons = score_lead(state.slots)
                band = compute_budget_band(state.slots.budget_min, state.slots.budget_max)
                lead = Lead(
                    session_id=session_id,
                    name=state.slots.name or "",
                    phone=state.slots.phone or "",
                    interest_projects=state.slots.interest_projects,
                    preferred_region=state.slots.region,
                    unit_type=state.slots.unit_type,
                    budget_min=state.slots.budget_min,
                    budget_max=state.slots.budget_max,
                    budget_band=band,
                    purpose=state.slots.purpose,
                    timeline=state.slots.timeline,
                    lead_temperature=temp,
                    reason_codes=reasons,
                    confirmed_by_user=True,
                    consent_contact=True,
                    lead_summary=f"{state.slots.name or 'Buyer'} interested in {', '.join(state.slots.interest_projects) or 'WDD projects'}. "
                                 f"Purpose: {state.slots.purpose or 'Not specified'}. Timeline: {state.slots.timeline or 'Exploring'}.",
                    tags=[t for t in [temp.lower(), state.slots.purpose, state.slots.region] if t],
                )
                saved = leads_service.save_lead(lead)
                if saved:
                    response_text = (f"Thank you, {state.slots.name or 'there'}. Your details have been saved. "
                                     f"A senior consultant will contact you at {state.slots.phone} shortly to assist you further.")
                else:
                    response_text = "I encountered an issue saving your details. Please try again."
                    error_reason = "save_failed"
            elif routed.intent == IntentType.CONFIRMATION_NO:
                state.slots.consent_contact = False
                state.stage = Stage.DISCOVERY
                response_text = ("Understood — I won't share your contact details. "
                                 "Feel free to continue exploring our projects. How can I help?")
            else:
                response_text = "May we contact you on WhatsApp to share details? Please reply **Yes** or **No**."

        elif state.stage == Stage.CAPTURE_PHONE:
            # Try to extract phone from user message
            phone = _normalize_phone(user_msg)
            if phone and len(re.sub(r'[^\d]', '', phone)) >= 10:
                state.slots.phone = phone
                state.stage = Stage.RECAP_PENDING
                response_text = _build_recap(state.slots)
            else:
                response_text = "I didn't catch a valid phone number. Could you share your WhatsApp number? (e.g., +20 101 234 5678)"

        # B) NON-SALES
        elif routed.intent == IntentType.NON_SALES:
            response_text = ("For customer service, complaints, or after-sales support, "
                             "please contact Wadi Degla directly at **19917** or visit "
                             "[wadidegladevelopments.com/contact-us](https://wadidegladevelopments.com/contact-us/).")

        # C) LIST PORTFOLIO
        elif routed.intent == IntentType.LIST_PORTFOLIO:
            listing = kb_service.format_portfolio_listing()
            selling = kb_service.get_selling_projects()
            evidence = [kb_service.build_evidence_pack(p) for p in selling]
            retrieved_projects = [p.project_name for p in selling]
            response_text = listing + "\nWhich region or project type interests you most?"

        # D) HIGH INTENT — pivot to capture
        elif routed.intent == IntentType.HIGH_INTENT:
            if not state.slots.phone:
                # Need phone first
                # But first, answer their question using RAG
                results = rag_service.search(
                    user_msg, k=3,
                    filters={"region": state.slots.region} if state.slots.region else None,
                    selling_only=True,
                    focused_project=state.focused_project,
                )
                retrieved_projects = [r['project'].project_name for r in results]
                evidence = [kb_service.build_evidence_pack(r['project']) for r in results]

                # Build context for LLM
                context_text = ""
                for r in results:
                    context_text += f"---\n{kb_service.build_project_card(r['project'])}\n"

                if not context_text:
                    error_reason = "strict_gating_empty"

                system_msg = _build_system_msg(context_text)
                # Add instruction to pivot to phone capture
                pivot_instruction = ("\n\nIMPORTANT: The user has shown high intent. "
                                     "After answering briefly, ask for their WhatsApp number with: "
                                     "\"I'd love to send you the details — may I have your WhatsApp number?\"")
                system_msg += pivot_instruction

                result = llm_service.answer_completion(system_msg, messages)
                if isinstance(result, str):
                    response_text = result
                else:
                    response_text = "I'd love to help with that. May I have your WhatsApp number so I can send you the latest details?"

                state.stage = Stage.CAPTURE_PHONE
            else:
                # Phone already captured — check what's missing
                if not state.slots.confirmed_by_user:
                    state.stage = Stage.RECAP_PENDING
                    response_text = _build_recap(state.slots)
                else:
                    state.stage = Stage.CONSENT_PENDING
                    response_text = "May we contact you on WhatsApp to share details?"

        # E) GREETING
        elif routed.intent == IntentType.GREETING:
            if not state.greeted:
                state.greeted = True
                state.stage = Stage.DISCOVERY
                response_text = ("Welcome to Wadi Degla Developments. "
                                 "I'm here to help you find the right property — whether for living, investment, or a weekend retreat.\n\n"
                                 "Are you looking to **live**, **invest**, or find a **weekend home**?")
            else:
                response_text = "How can I help you today? Are you interested in any specific project or region?"

        # F) PROJECT DISCOVERY / GENERAL QA
        else:
            # RAG search
            filters = {}
            if state.slots.region:
                filters["region"] = state.slots.region

            results = rag_service.search(
                routed.raw_query or user_msg,
                k=3,
                filters=filters if filters else None,
                selling_only=True,
                focused_project=state.focused_project,
            )

            # Check for focused project switch
            if (state.focused_project and
                routed.matched_projects and
                routed.matched_projects[0].lower() != state.focused_project.lower()):
                # User asking about different project
                new_proj = routed.matched_projects[0]
                response_text = (f"You're currently exploring **{state.focused_project}**. "
                                 f"Would you like to switch to **{new_proj}** instead?")
                # Don't switch yet — wait for confirmation
            else:
                retrieved_projects = [r['project'].project_name for r in results]
                evidence = [kb_service.build_evidence_pack(r['project']) for r in results]

                context_text = ""
                for r in results:
                    context_text += f"---\n{kb_service.build_project_card(r['project'])}\n"

                if not context_text:
                    error_reason = "strict_gating_empty"
                    context_text = "No matching projects found for this query."

                system_msg = _build_system_msg(context_text)

                # Slot-fill instruction
                missing_slots = []
                if not state.slots.purpose:
                    missing_slots.append("purpose (Live/Invest/Weekend)")
                if not state.slots.region:
                    missing_slots.append("region preference")
                if not state.slots.budget_min and not state.slots.budget_max:
                    missing_slots.append("budget range")

                if missing_slots:
                    system_msg += f"\n\nIMPORTANT: Your ONE question at the end should ask about: {missing_slots[0]}"

                result = llm_service.answer_completion(system_msg, messages)
                if isinstance(result, str):
                    response_text = result
                else:
                    response_text = "I'd be happy to help. Could you tell me more about what you're looking for?"

                # If user mentioned a project, set as focused
                if routed.matched_projects and not state.focused_project:
                    state.focused_project = routed.matched_projects[0]

                state.stage = Stage.DISCOVERY

        # ─── SLOT EXTRACTION from LLM response (for user messages) ────
        _extract_slots_from_message(user_msg, state.slots)

    except Exception as e:
        logger.error(f"Chat pipeline error: {e}", exc_info=True)
        response_text = "I apologize, but I'm encountering a temporary issue. Please try again."
        error_reason = f"exception: {str(e)[:100]}"

    # ─── UPDATE STATE ─────────────────────────────────────────────────
    state.turn_count += 1
    state_service.save_state(state)

    # ─── AUDIT ────────────────────────────────────────────────────────
    leads_service.log_audit(
        session_id=session_id,
        stage=state.stage.value,
        intent=routed.intent.value,
        high_intent=routed.is_high_intent,
        user_message=user_msg,
        focused_project=state.focused_project,
        retrieved_projects=[p for p in retrieved_projects],
        empty_retrieval=len(retrieved_projects) == 0,
        error_reason=error_reason,
    )

    return {
        "message": response_text,
        "retrieved_projects": retrieved_projects,
        "evidence": evidence,
        "mode": "lead_capture" if state.stage in (Stage.CAPTURE_PHONE, Stage.RECAP_PENDING, Stage.CONSENT_PENDING, Stage.SAVED) else "concierge",
        "stage": state.stage.value,
    }


def _extract_slots_from_message(msg: str, slots: Slots):
    """Try to extract slot values from user message text."""
    msg_lower = msg.lower().strip()

    # Purpose
    if not slots.purpose:
        if any(w in msg_lower for w in ["invest", "investment", "roi", "rental income"]):
            slots.purpose = "Invest"
        elif any(w in msg_lower for w in ["live", "living", "primary home", "move in", "residence"]):
            slots.purpose = "Live"
        elif any(w in msg_lower for w in ["weekend", "vacation", "holiday", "getaway", "second home"]):
            slots.purpose = "Weekend"

    # Timeline
    if not slots.timeline:
        if any(w in msg_lower for w in ["immediately", "asap", "right away", "urgent"]):
            slots.timeline = "Immediate"
        elif any(w in msg_lower for w in ["3 month", "three month", "soon", "next quarter"]):
            slots.timeline = "0-3 months"
        elif any(w in msg_lower for w in ["6 month", "six month", "half year"]):
            slots.timeline = "3-6 months"
        elif any(w in msg_lower for w in ["exploring", "just looking", "browsing", "no rush"]):
            slots.timeline = "Exploring"

    # Budget (simple extraction)
    if not slots.budget_min and not slots.budget_max:
        budget_match = re.findall(r'(\d+(?:\.\d+)?)\s*(?:m|million|mil)', msg_lower)
        if len(budget_match) >= 2:
            vals = sorted([float(v) for v in budget_match[:2]])
            slots.budget_min = str(int(vals[0] * 1_000_000))
            slots.budget_max = str(int(vals[1] * 1_000_000))
        elif len(budget_match) == 1:
            val = float(budget_match[0])
            slots.budget_min = str(int(val * 0.8 * 1_000_000))
            slots.budget_max = str(int(val * 1_000_000))

    # Name (only if short, proper-cased response and we don't have one)
    if not slots.name and len(msg.split()) <= 3:
        words = msg.strip().split()
        if all(w[0].isupper() and w.isalpha() for w in words if len(w) > 1):
            if not any(w.lower() in ["yes", "no", "hi", "hello", "hey", "ok", "sure", "thanks"] for w in words):
                slots.name = msg.strip()


# ─────────────────────────────────────────────────────────────────────
# ENDPOINTS
# ─────────────────────────────────────────────────────────────────────

@app.post("/api/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    try:
        result = _process_chat(request.session_id, request.messages)
        return ChatResponse(**result)
    except Exception as e:
        logger.error(f"Chat error: {e}", exc_info=True)
        return ChatResponse(
            message="I apologize, but I'm encountering a temporary issue. Please try again.",
            retrieved_projects=[],
            mode="concierge"
        )


@app.post("/api/chat/stream")
async def chat_stream_endpoint(request: ChatRequest):
    """SSE streaming endpoint. For non-LLM responses, sends immediately."""
    try:
        user_msg = request.messages[-1].content
        session_id = request.session_id
        state = state_service.load_state(session_id)
        routed = intent_router.route(user_msg, state.turn_count, state.stage.value)

        # Check if this route needs LLM (only PROJECT_DISCOVERY, GENERAL_QA, HIGH_INTENT with context)
        needs_llm = routed.intent in (IntentType.PROJECT_DISCOVERY, IntentType.GENERAL_QA, IntentType.HIGH_INTENT)
        is_gate_stage = state.stage in (Stage.RECAP_PENDING, Stage.CONSENT_PENDING, Stage.CAPTURE_PHONE)

        if not needs_llm or is_gate_stage:
            # Process synchronously and stream the result as a single chunk
            result = _process_chat(session_id, request.messages)

            def generate_sync():
                yield f"data: {json.dumps({'token': result['message']})}\n\n"
                yield f"data: {json.dumps({'done': True, 'retrieved_projects': result.get('retrieved_projects', []), 'evidence': result.get('evidence', []), 'mode': result.get('mode', 'concierge'), 'stage': result.get('stage', '')})}\n\n"

            return StreamingResponse(
                generate_sync(),
                media_type="text/event-stream",
                headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"}
            )

        # LLM-required path: stream tokens
        # Update slots
        if routed.extracted_region and not state.slots.region:
            state.slots.region = routed.extracted_region
        if routed.extracted_unit_type and not state.slots.unit_type:
            state.slots.unit_type = routed.extracted_unit_type
        if routed.matched_projects:
            for p in routed.matched_projects:
                if p not in state.slots.interest_projects:
                    state.slots.interest_projects.append(p)
            if not state.focused_project:
                state.focused_project = routed.matched_projects[0]

        # RAG search
        filters = {}
        if state.slots.region:
            filters["region"] = state.slots.region

        results = rag_service.search(
            routed.raw_query or user_msg,
            k=3,
            filters=filters if filters else None,
            selling_only=True,
            focused_project=state.focused_project,
        )

        retrieved_projects = [r['project'].project_name for r in results]
        evidence = [kb_service.build_evidence_pack(r['project']) for r in results]

        context_text = ""
        for r in results:
            context_text += f"---\n{kb_service.build_project_card(r['project'])}\n"

        if not context_text:
            context_text = "No matching projects found."

        system_msg = _build_system_msg(context_text)

        # Add high-intent pivot if needed
        if routed.is_high_intent and not state.slots.phone:
            system_msg += ("\n\nIMPORTANT: The user has shown high intent. "
                           "After answering briefly, ask for their WhatsApp number.")
            state.stage = Stage.CAPTURE_PHONE
        else:
            state.stage = Stage.DISCOVERY

        # Slot-fill instruction
        missing = []
        if not state.slots.purpose:
            missing.append("purpose (Live/Invest/Weekend)")
        if not state.slots.region:
            missing.append("region preference")
        if missing:
            system_msg += f"\n\nYour ONE question should ask about: {missing[0]}"

        _extract_slots_from_message(user_msg, state.slots)
        state.turn_count += 1
        state_service.save_state(state)

        def generate():
            for chunk in llm_service.stream_answer_completion(system_msg, request.messages):
                if "__TOOL_CALLS__" in chunk:
                    # Tool calls in streaming mode — handle save_lead
                    tc_json = chunk.split("__TOOL_CALLS__")[1]
                    tool_calls = json.loads(tc_json)
                    for tc in tool_calls:
                        if tc["function"]["name"] == "save_lead":
                            args = json.loads(tc["function"]["arguments"])
                            # Don't auto-save here — gates must pass through state machine
                            confirm_msg = "I'd love to help finalize your inquiry. May I have your WhatsApp number?"
                            yield f"data: {json.dumps({'token': confirm_msg})}\n\n"
                else:
                    yield f"data: {json.dumps({'token': chunk})}\n\n"

            yield f"data: {json.dumps({'done': True, 'retrieved_projects': retrieved_projects, 'evidence': evidence, 'mode': 'lead_capture' if routed.is_high_intent else 'concierge', 'stage': state.stage.value})}\n\n"

            leads_service.log_audit(
                session_id=session_id,
                stage=state.stage.value,
                intent=routed.intent.value,
                high_intent=routed.is_high_intent,
                user_message=user_msg,
                focused_project=state.focused_project,
                retrieved_projects=retrieved_projects,
                empty_retrieval=len(retrieved_projects) == 0,
            )

        return StreamingResponse(
            generate(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"}
        )

    except Exception as e:
        logger.error(f"Stream chat error: {e}", exc_info=True)
        return StreamingResponse(
            iter([f"data: {json.dumps({'token': 'I apologize, but I encountered a temporary issue. Please try again.', 'done': True})}\n\n"]),
            media_type="text/event-stream"
        )


@app.post("/api/lead")
async def create_lead(lead: Lead):
    if not leads_service.can_save(lead):
        raise HTTPException(status_code=400, detail="Lead gates not met: phone, confirmation, and consent required.")
    success = leads_service.save_lead(lead)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to save lead")
    return {"status": "success", "message": "Lead captured"}
