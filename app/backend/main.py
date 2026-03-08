from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import json
import logging
import os
from datetime import datetime

from app.backend.config import Config
from app.backend.models import ChatRequest, ChatResponse, Lead, Message
from app.backend.services.llm_service import llm_service
from app.backend.services.rag_service import rag_service
from app.backend.services.leads_service import leads_service
from app.backend.services.kb_service import kb_service
from app.backend.routes.admin_routes import router as admin_router

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("PulseX-WDD-API")

app = FastAPI(title="PulseX-WDD API", version="1.0.0")

# Mount admin routes
app.include_router(admin_router, prefix="/api")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Allow all for pilot
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

CONCIERGE_SYSTEM_PROMPT = """
You are Wadi Degla Developments (WDD) Concierge, but under the hood, you are a Top Notch, State-of-the-Art (SOTA), PRO, Robust, and Resilient Senior Sales Executive.
Your ultimate goal is to convert inquiries into site visits or calls by being highly intelligent, organically human, and persuasively guiding the buyer through our funnel. 
You are NOT just a support bot. You are a resilient "closer" with a discreet, luxurious, PalmX-grade commercial brain that never drops a lead.

### 1. The Core Objective (Sleek, Seamless & Very Organic Lead Capture)
- **Understand Instantly**: Use the provided CONTEXT to immediately impress the user with accurate WDD project knowledge.
- **Deeply Qualify (Organically)**: Never rush to a close. Conversationally and seamlessly extract their **Budget Range**, **Preferred Region**, **Unit Type** (Villa/Chalet/Apartment), **Purpose** (Investment vs Personal), and **Timeline**. Make it feel like a sleek luxury consultation, not a form.
- **Curate**: Shortlist 2-3 perfect matches (e.g., Murano for Sokhna, ClubTown for Maadi, Neo for Mostakbal City) based on their exact profile.
- **The WhatsApp Pivot (Sleek Close)**: Once you've earned trust and enriched the profile, gracefully offer value: *"Would you like me to share the official brochures, floor plans, and current availability for these on WhatsApp? If so, please share your **Name** and **WhatsApp Number**."*
- **Capture & Score**: Upon gaining consent, summarize the rich profile internally, score them, and capture the lead using the `save_lead` tool. The capture must be absolutely seamless.

### 2. Tone & Voice (Luxury + Human + Trust)
- **Style**: Warm, reassuring, premium but readable. Minimal jargon, non-technical. Talk *through* the customer organically without sounding robotic or like an interrogator. Ask 1-2 questions max per turn.
- **Brand Essence**: You represent Egypt's most trusted real estate developer with over 20 years of expertise. When pitching, emphasize "family comfort", "belonging", and an "integrated community lifestyle".
- **Highlighting**: You MUST use Markdown bolding (`**keyword**`) to highlight important terms (e.g., project names, regions, unit types, budget numbers) so the UI can style them dynamically. Example: "I highly recommend **Murano** for an **Investment** in **Ain El Sokhna**."
- **Forbidden**: Robotic lists ("Status: Commercial"), repetitive "May I assist?", overhype ("AMAZING!!!"), emojis, or acting "dumb" when queried about facts in the CONTEXT.
- **The Brain**: Connect dots seamlessly. If they mention "ROI" or "Investment", pivot to high-yield projects. Wait to gather all details before jumping to the WhatsApp Pivot.

### 3. SOTA SCENARIO PITCHING (The Pro Salesman Reflex)
- **Broad/International Scenarios**: If a user introduces a broad scenario (e.g., "I'm an investor from India", "I'm looking for a second home but don't know Egypt"), DO NOT just ask clinical questions.
- **The Value Proposition Pivot**: First, act like a world-class salesman. Pitch Egypt's booming real estate ROI, WDD's 20-year proven legacy of delivering world-class communities, and the security of investing with a trusted developer. 
- *Example Pitch*: "Egypt's real estate market is currently one of the highest-yield investment hubs globally. With over 20 years of legacy, Wadi Degla Developments offers secure, highly liquid assets with exceptional capital appreciation. I'd love to curate a high-yield portfolio for you. Are you leaning towards a commercial asset, or a premium residential property?"
- After pitching the undeniable value of WDD, smoothly transition back to Stage 2 (Organically gathering Region, Budget, Unit Type).

### 4. STRICT GUARDRAILS (Out-of-Domain Block)
- **Zero Hallucination / Scope Lock**: You are a real estate Senior Executive for Wadi Degla Developments. If the user asks you about topics outside of this domain (e.g., geography, history, recipes, other developers, coding, general knowledge), you MUST POLITELY DECLINE.
- **Refusal Formula**: Acknowledge the question lightly, state your boundary, and pivot back to their property search.
- *Example Refusal*: "I’m afraid my expertise is entirely dedicated to Wadi Degla's real estate portfolio. However, if you're looking for a new home or investment opportunity, I’d be delighted to assist you with that. Are you currently exploring properties in Cairo or the coast?"

### 5. The Conversation Operating System (6-Stage Funnel)
**Every reply must organically progress the buyer through this funnel:**

**Stage 1: The Brand Welcome & Intent Lock**
- **CRITICAL ON FIRST TURN**: If this is the very first message or the user simply says "Hi", you MUST introduce the brand with prestige and trust.
- *Example Welcome*: "Welcome to **Wadi Degla Developments**, Egypt's trusted real estate leader for over 20 years. I am your Senior Concierge. Whether you are looking for a luxurious coastal retreat or a premium family residence in **Cairo**, I am here to assist."
- Immediately demonstrate you understand their specific need if they provided one, using the CONTEXT.

**Stage 2: Structured Organic Qualification**
- You must organically guide the conversation layer by layer: **1. Cover City/Region** -> **2. Cover Project** -> **3. Cover Property / Unit Type** (Villa/Chalet/Apartment) -> **4. Clarify Budget & Timeline & Purpose**.
- **CRITICAL DEFINITION**: "Region" refers ONLY to broad areas (e.g. Cairo, East Cairo, West Cairo, North Coast, Red Sea, Ain El Sokhna). "Project" refers to specific developments (e.g. Vyon, Clubtown, Murano). 
- **AUTO-INFERENCE OVERRIDE**: If a user mentions a known Project (like "Vyon") and the knowledge base CONTEXT provides its Region (e.g., "East Cairo"), you MUST auto-fill your internal Region requirement. **DO NOT** ask the user "What is your preferred Region?" if you already know it from the project context.
- Ask 1-2 natural, luxurious questions per turn to build this profile without overwhelming them.
- **Verbosity Rule**: Keep things CRISP and concise when asking qualification questions.

**Stage 3: Curated Value (The Pitch Phase)**
- Present 1-3 tailored matches from the CONTEXT that fit the gathered profile. 
- **Verbosity Rule**: ELABORATE and ENLIGHTEN beautifully here. Describe the lifestyle, the landscapes, and why it fits them perfectly. Make the property sound irresistible..
- *Example*: "Are you looking for an **Investment** property or a personal weekend retreat? And do you have a specific **Budget Range** in mind so I can curate the perfect options?"
- **STRICT FORBIDDEN RULE**: You MUST NEVER list or recommend a project if its Status is "Delivered, not selling" or "Not Selling". Only pitch actively "Selling" projects.
- Highlight **Why it fits** + provide the **Starting Price** (if available) or note pricing is "On Request".

**Stage 4: The WhatsApp Pivot (The Sleek Soft Close)**
- **STRICT FORBIDDEN RULE**: NEVER offer the WhatsApp pivot until Stage 2 is 100% complete (you know their Budget, Timeline, Purpose, Region, and Unit Type). Once you have EVERYTHING, gracefully pivot.
- **SOTA Salesman Rule**: Make it irresistible and organic. Don't sound automated.
- *Example*: "These exclusive units are in extremely high demand right now. I'd love to shoot over the official floor plans, current availability, and the digital brochure directly to your **WhatsApp** so you can review them with your family. If that sounds good, what's your **Name** and **WhatsApp Number**?" 

**Stage 5: Data Capture & Confirmation (The Sleek Summary & Consent Gate)**
- Once they say yes to WhatsApp and provide a number/name, summarize elegantly. You MUST summarize ALL fields captured (including **Email** if provided organically). Make it sound like a high-end service, not a receipt.
- **CRITICAL**: You MUST end this summary by explicitly asking for their final confirmation. Do NOT call `save_lead` yet.
- *Example*: "Perfect, **[Name]**. I've got you covered. Just to make sure my senior team sends you the exact right portfolio, I've noted you are looking for a **[Unit Type]** in **[Region]**, specifically keeping an eye on **[Project]**, for **[Purpose]**, with a budget around **[Budget in EGP]**, looking to move forward by **[Timeline]**. I've got your number down as **[Number]**. Does this look correct? Shall I go ahead and have them release the brochures to you?"

**Stage 6: The Execution (Resilient Lock)**
- **Action**: ONLY call the `save_lead` tool AFTER they explicitly reply "Yes" or confirm the summary presented in Stage 5. If they hesitate, gently reassure them. If they say no to WhatsApp but give an email, pivot smoothly and capture that instead. Be a robust, resilient closer.

### 4. Special WDD Mechanics & Temporal Logic (STRICT)
- **TODAY IS**: {current_date}.
- **Year Inference**: Never output "2024" for future timelines. If it's 2026, "March" means March 2026.
- **Currency Handling**: Always state values in **EGP**. If the user says USD/AED, instantly convert and show the EGP equivalent. When storing in `save_lead`, use the string value (e.g. "5000000").
- **Pricing Authority**: 100% of WDD pricing is currently "On Request". If asked about price, say: "Pricing is currently on request; I can have our team share the exact sheet with you."

### 5. Progressive Scoring (Internal thought before capture)
When calling `save_lead`, you must accurately set the `lead_temperature`:
- **Hot**: Ready to buy immediately (0-3 months), clear budget, highly engaged.
- **Warm**: Exploring (3-6 months), needs more info, somewhat engaged.
- **Cold**: Just browsing, very vague, or unresponsive.

### 6. Strict Truthfulness
- **NEVER hallucinate projects**. Only recommend what is in the CONTEXT.
- If a project is sold out (e.g., Blumar El Sokhna), pivot elegantly to active projects like Murano.
"""

@app.get("/api/health")
async def health_check():
    """Simple health check for frontend to poll during startup."""
    return {"status": "ready", "rag_ready": rag_service.is_ready}

# --- Tools ---
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "save_lead",
            "description": "Save a verified, highly-qualified lead. Call ONLY after the buyer explicitly confirms their summarized information is correct and consents to being contacted. Populate every field accurately from the conversation.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "The buyer's full name."},
                    "phone": {"type": "string", "description": "The buyer's correct phone or WhatsApp number."},
                    "email": {"type": "string", "description": "The buyer's email address, if they naturally provided it."},
                    "interest_projects": {"type": "string", "description": "Comma-separated list of exact WDD project names discussed."},
                    "preferred_region": {"type": "string", "description": "Their preferred WDD region.", "enum": ["East Cairo", "West Cairo", "North Coast", "Ain El Sokhna", "Cairo", "Red Sea", "Unknown"]},
                    "unit_type": {"type": "string", "description": "Villa, Apartment, Townhouse, Duplex, Penthouse, Commercial, etc."},
                    "budget_min": {"type": "string", "description": "Minimum budget in EGP as a string (e.g., '5000000')."},
                    "budget_max": {"type": "string", "description": "Maximum budget in EGP as a string (e.g., '15000000')."},
                    "purpose": {"type": "string", "description": "Buy, Rent, or Invest", "enum": ["Buy", "Rent", "Invest"]},
                    "timeline": {"type": "string", "description": "When they plan to purchase (e.g., Immediate, 3 months, 6 months, Exploring)."},
                    "next_step": {"type": "string", "description": "Agreed next action.", "enum": ["callback", "site_visit", "send_details"]},
                    "next_action": {"type": "string", "description": "Specific next action to be taken by sales.", "enum": ["callback", "site_visit", "send_details"]},
                    "lead_summary": {"type": "string", "description": "A sharp, 2-3 line natural-language executive summary of the buyer's exact needs, context, and intent."},
                    "customer_summary": {"type": "string", "description": "A polite, customer-facing summary of the requirements."},
                    "executive_summary": {"type": "string", "description": "An internal, concise summary of the lead for the sales executives."},
                    "reason_codes": {"type": "string", "description": "Comma-separated list of reasons for their intent (e.g., 'investment_roi, primary_home, upgrade')."},
                    "tags": {"type": "string", "description": "Auto-generated comma-separated tags capturing key attributes: e.g. 'high_budget,villa,investor,urgent'"},
                    "lead_temperature": {"type": "string", "description": "Progressive score of the buyer's intent.", "enum": ["Hot", "Warm", "Cold"]},
                    "consent_contact": {"type": "boolean", "description": "True if the user explicitly agreed to be contacted via WhatsApp/Phone."},
                    "kb_version_hash": {"type": "string", "description": "Leave as default unless known."}
                },
                "required": ["name", "phone", "lead_temperature", "consent_contact"]
            }
        }
    }
]

# --- Endpoints ---

@app.post("/api/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    try:
        user_msg = request.messages[-1].content
        session_id = request.session_id
        
        # 1. Router
        history = request.messages[:-1]
        router_out = llm_service.router_completion(user_msg, history=history)
        logger.info(f"Router intent: {router_out.intent} | Filters: {router_out.filters}")

        # 2. Retrieval
        retrieved_docs = []
        if router_out.intent not in ("support_contact", "lead_capture", "out_of_domain"):
            results = rag_service.search(
                router_out.query_rewrite, 
                k=3, 
                filters=router_out.filters
            )
            retrieved_docs = [r['project'] for r in results]

        # 3. Context Construction
        context_text = ""
        for p in retrieved_docs:
            context_text += f"---\n{kb_service.build_project_card(p)}\n"
            
        current_date = datetime.now().strftime("%B %d, %Y")
        full_system_msg = CONCIERGE_SYSTEM_PROMPT.format(current_date=current_date) + f"\n\nCONTEXT:\n{context_text}"
        
        # 4. Answer Generation
        response_data = llm_service.answer_completion(
            full_system_msg, 
            request.messages,
            tools=TOOLS
        )
        
        final_text = ""
        
        # 5. Handle Tool Calls
        if isinstance(response_data, list):
            for tool_call in response_data:
                if tool_call.function.name == "save_lead":
                    args = json.loads(tool_call.function.arguments)
                    logger.info(f"Tool Call 'save_lead' Args: {args}")
                    
                    lead = Lead(
                        session_id=session_id,
                        name=args.get('name'),
                        phone=args.get('phone'),
                        email=args.get('email'),
                        interest_projects=args.get('interest_projects', '').split(',') if args.get('interest_projects') else [],
                        preferred_region=args.get('preferred_region'),
                        unit_type=args.get('unit_type'),
                        budget_min=args.get('budget_min'),
                        budget_max=args.get('budget_max'),
                        purpose=args.get('purpose'),
                        timeline=args.get('timeline'),
                        next_step=args.get('next_step'),
                        next_action=args.get('next_action'),
                        lead_summary=args.get('lead_summary'),
                        customer_summary=args.get('customer_summary'),
                        executive_summary=args.get('executive_summary'),
                        reason_codes=args.get('reason_codes', '').split(',') if args.get('reason_codes') else [],
                        tags=args.get('tags', '').split(',') if args.get('tags') else [],
                        lead_temperature=args.get('lead_temperature'),
                        consent_contact=args.get('consent_contact'),
                        kb_version_hash=args.get('kb_version_hash', 'v1.0')
                    )
                    leads_service.save_lead(lead)
                    final_text = f"Thank you {lead.name}. Your details have been saved. A sales representative will contact you at {lead.phone} shortly."
        else:
            final_text = response_data

        # 6. Audit
        leads_service.log_audit(
            session_id, 
            user_msg, 
            router_out.intent, 
            [p.project_id for p in retrieved_docs], 
            [] 
        )
        
        return ChatResponse(
            message=final_text,
            retrieved_projects=[p.project_name for p in retrieved_docs],
            mode="lead_capture" if router_out.intent == "lead_capture" else "concierge"
        )

    except Exception as e:
        logger.error(f"Chat error: {e}")
        return ChatResponse(
            message="I apologize, but I'm encountering a temporary issue. Please try again.",
            retrieved_projects=[],
            mode="concierge"
        )

@app.post("/api/chat/stream")
async def chat_stream_endpoint(request: ChatRequest):
    try:
        user_msg = request.messages[-1].content
        session_id = request.session_id
        
        # 0. Empty Message Defense
        if not user_msg or not str(user_msg).strip():
            logger.warning("[Stream] Received empty message, aborting.")
            def empty_fallback():
                fallback_msg = "I didn't quite catch that. How can I help you regarding Wadi Degla properties?"
                yield f"data: {json.dumps({'token': fallback_msg})}\n\n"
                yield f"data: {json.dumps({'done': True, 'retrieved_projects': [], 'mode': 'concierge'})}\n\n"
            return StreamingResponse(empty_fallback(), media_type="text/event-stream")

        # 1. Router
        history = request.messages[:-1]
        router_out = llm_service.router_completion(user_msg, history=history)
        logger.info(f"[Stream] Router intent: {router_out.intent}")

        # 2. Retrieval
        retrieved_docs = []
        if router_out.intent not in ("support_contact", "lead_capture", "out_of_domain"):
            results = rag_service.search(
                router_out.query_rewrite, k=3, filters=router_out.filters
            )
            retrieved_docs = [r['project'] for r in results]

        # 3. Context
        context_text = ""
        for p in retrieved_docs:
            context_text += f"---\n{kb_service.build_project_card(p)}\n"
        
        current_date = datetime.now().strftime("%B %d, %Y")
        full_system_msg = CONCIERGE_SYSTEM_PROMPT.format(current_date=current_date) + f"\n\nCONTEXT:\n{context_text}"

        # 4. Stream tokens
        def generate():
            full_response = ""
            for chunk in llm_service.stream_answer_completion(
                full_system_msg, request.messages, tools=TOOLS
            ):
                if "__TOOL_CALLS__" in chunk:
                    tc_json = chunk.split("__TOOL_CALLS__")[1]
                    tool_calls = json.loads(tc_json)
                    for tc in tool_calls:
                        if tc["function"]["name"] == "save_lead":
                            args = json.loads(tc["function"]["arguments"])
                            lead = Lead(
                                session_id=session_id,
                                name=args.get('name'),
                                phone=args.get('phone'),
                                email=args.get('email'),
                                interest_projects=args.get('interest_projects', '').split(',') if args.get('interest_projects') else [],
                                preferred_region=args.get('preferred_region'),
                                unit_type=args.get('unit_type'),
                                budget_min=args.get('budget_min'),
                                budget_max=args.get('budget_max'),
                                purpose=args.get('purpose'),
                                timeline=args.get('timeline'),
                                next_step=args.get('next_step'),
                                next_action=args.get('next_action'),
                                lead_summary=args.get('lead_summary'),
                                customer_summary=args.get('customer_summary'),
                                executive_summary=args.get('executive_summary'),
                                reason_codes=args.get('reason_codes', '').split(',') if args.get('reason_codes') else [],
                                tags=args.get('tags', '').split(',') if args.get('tags') else [],
                                lead_temperature=args.get('lead_temperature'),
                                consent_contact=args.get('consent_contact'),
                                kb_version_hash=args.get('kb_version_hash', 'v1.0')
                            )
                            leads_service.save_lead(lead)
                            confirm_msg = f"Thank you {lead.name}. Your details have been saved. A sales representative will contact you at {lead.phone} shortly."
                            yield f"data: {json.dumps({'token': confirm_msg})}\n\n"
                else:
                    full_response += chunk
                    yield f"data: {json.dumps({'token': chunk})}\n\n"
            
            yield f"data: {json.dumps({'done': True, 'retrieved_projects': [p.project_name for p in retrieved_docs], 'mode': 'lead_capture' if router_out.intent == 'lead_capture' else 'concierge'})}\n\n"
            
            leads_service.log_audit(
                session_id, user_msg, router_out.intent,
                [p.project_id for p in retrieved_docs], []
            )

        return StreamingResponse(
            generate(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"
            }
        )
    except Exception as e:
        logger.error(f"Stream chat error: {e}")
        return StreamingResponse(
            iter([f"data: {json.dumps({'token': 'I apologize, but I encountered a temporary issue. Please try again.', 'done': True})}\n\n"]),
            media_type="text/event-stream"
        )

@app.post("/api/lead")
async def create_lead(lead: Lead):
    success = leads_service.save_lead(lead)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to save lead")
    return {"status": "success", "message": "Lead captured"}


@app.get("/health")
async def health():
    return {"status": "ok", "rag_ready": rag_service.is_ready}
