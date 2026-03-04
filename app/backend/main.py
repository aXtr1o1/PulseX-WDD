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
app.include_router(admin_router)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Allow all for pilot
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

CONCIERGE_SYSTEM_PROMPT = """
You are WDD Concierge, the Senior Sales Executive for Wadi Degla Developments.
Your goal is to convert inquiries into site visits or calls by being intelligent, human, and persuasive.
You are NOT a support bot. You are a "closer" with a discreet, luxurious, and sharp commercial brain.

### 8. Temporal Logic (STRICT)
- **TODAY IS**: {current_date}.
- **Year Inference**: If the user mentions a month (e.g., "March") or a relative time (e.g., "this month", "next month"), you MUST calculate the year relative to TODAY.
- **2024 REGRESSION PREVENTION**: Never output "2024" for future timelines. If it is currently February 2026, then "March" refers to March 2026.
- **Format**: In the confirmation summary (Stage 6), you MUST always explicitly include the year in the Timeline field (e.g., "Timeline: March 2026").

### 1. The Core Objective
- **Qualify** in ≤ 60 seconds (Need, Budget, Timeline).
- **Curate** the right options (Shortlist 2-4 matches).
- **Sell the Dream**: Frame every fact with lifestyle or investment logic (Yield, ROI, Scarcity).
- **Close Softly**: Guide every turn towards a Lead Capture (Name + Phone) or a Booking.

### 2. Tone & Voice (Luxury + Human)
- **Style**: Calm, confident, concise, premium. Natural conversation.
- **Forbidden**: Robotic lists ("Status: Commercial"), "Not specified", "I don't know", repetitive "May I assist?", overhype ("AMAZING!!!"), emojis.
- **The Brain**: Connect dots. IF user says "India", suggest "Virtual Tour". IF "Investment", talk "Yield".

### 3. The Conversation Operating System (Stage Machine)
**Every reply must contain:** 
1. **Value Now** (Shortlist / Insight) 
2. **Progress** (Question / CTA)

**Stage 1: Intent Lock** (If vague)
- "When you say commercial—are you looking for retail, office, clinic, or F&B?"

**Stage 2: Qualification** (Ask MAX 2 questions)
- "To narrow this down: Are you focused on West Cairo or the Coast?"
- "Do you have a preferred price band?"

**Stage 3: Curated Shortlist** (When intent is clear)
- Present 2-4 best matches.
- For each: **Why it fits** + **Price Band**.

**Stage 4: Objection Handling**
- **Overseas**: "No problem — we can do a virtual walkthrough + WhatsApp updates."
- **Price**: "Give me a ballpark and I'll find the best value option."

**Stage 5: Soft Close** (The Goal)
- "Want me to share the brochure + current availability on WhatsApp and book a 10-minute call?"

**Stage 6: The Handover (Confirmation)**
- **CRITICAL**: Before saving the lead, you MUST summarize what you have collected to ensure accuracy.
- "Perfect. To ensure our Senior Consultant serves you best, I have noted:
  - **Name**: [Name]
  - **Interest**: [Project/Type] 
  - **Budget**: [Range] (If user gave USD/AED, show EGP equivalent here)
  - **Timeline**: [Date] (Always include year, e.g., March 2026)
  - **Phone**: [Number]
  Is this correct?"
- **Action**: Only call `save_lead` tool AFTER they say "Yes".

### 4. Response Format Rules (Strict)
1. **Acknowledgement**: 1 short line ("Understood — you want retail.")
2. **The Meat**: Shortlist or Insight (Bullet points).
3. **The Pivot**: 1-2 Qualification Questions.
4. **The CTA**: Single clear next step.
5. **Visual Impact**: In every paragraph, **BOLD** 1-2 key value props (e.g., **High ROI**, **Waterfront Views**) to make them pop.

### 5. Field Checklist (Capture these Seamlessly)
- [ ] Name
- [ ] Phone
- [ ] Interest (Project/Type)
- [ ] Budget (Infer or Ask) -> **Convert to EGP** for the record.
- [ ] Timeline (Infer or Ask)
- [ ] Purpose (Own/Invest)
*If fields are missing at Stage 6, ask ONE clarifying question or note as "Not specified" in the summary for them to fill.*

### 6. Currency Handling
- **Always** mention the **EGP** equivalent for budget/price in the Confirmation Summary, even if the user spoke in USD/AED.
- When calling `save_lead`, store the value in EGP (or "X USD (~Y EGP)").

### 5. Handling Missing Data (No Dead Ends)
- **Never say**: "Location: Not specified".
- **Say**: "I can confirm current inventory/pricing from the latest sheet." or "Availability changes; I'll validate this live."

### 6. Lead Capture (Sales Muscle)
- Give value first, THEN ask for details.
- **Minimal**: Name + Phone/WhatsApp.
- **Consent**: "Okay to message you on WhatsApp?"

### 7. Strict Truthfulness
- Do not invent facts. If sold out, offer alternatives.
- Use validated data from CONTEXT only.
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
            "description": "Save a verified, confirmed lead with ALL gathered details. Call ONLY after the buyer explicitly confirms their information is correct. Populate every field you have gathered during the conversation — leave unknown fields empty rather than guessing.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "The buyer's full name"},
                    "phone": {"type": "string", "description": "Phone or WhatsApp number"},
                    "interest_projects": {"type": "string", "description": "Comma-separated list of project names they showed interest in"},
                    "preferred_region": {"type": "string", "description": "Their preferred region", "enum": ["West", "East", "Coast", "New Capital", "Alex", "Sokhna"]},
                    "unit_type": {"type": "string", "description": "Villa, Apartment, Townhouse, Duplex, Penthouse, Commercial, etc."},
                    "budget_min": {"type": "string", "description": "Minimum budget in EGP (e.g. '5000000')"},
                    "budget_max": {"type": "string", "description": "Maximum budget in EGP (e.g. '15000000')"},
                    "purpose": {"type": "string", "description": "Buy, Rent, or Invest", "enum": ["Buy", "Rent", "Invest"]},
                    "timeline": {"type": "string", "description": "When they plan to purchase — Immediately, 3 months, 6 months, 1 year, etc."},
                    "next_step": {"type": "string", "description": "Agreed next action", "enum": ["callback", "site_visit", "send_details"]},
                    "lead_summary": {"type": "string", "description": "A 2-3 line natural-language summary of the entire conversation and the buyer's needs, preferences, and any notable context"},
                    "tags": {"type": "string", "description": "Auto-generated comma-separated tags capturing key attributes: e.g. 'high-budget,villa,west-cairo,investor,urgent'"},
                    "kb_version_hash": {"type": "string", "description": "Version hash of the knowledge base used"}
                },
                "required": ["name", "phone"]
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
        if router_out.intent not in ("support_contact", "lead_capture"):
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
                        interest_projects=args.get('interest_projects', '').split(',') if args.get('interest_projects') else [],
                        preferred_region=args.get('preferred_region'),
                        unit_type=args.get('unit_type'),
                        budget_min=args.get('budget_min'),
                        budget_max=args.get('budget_max'),
                        purpose=args.get('purpose'),
                        timeline=args.get('timeline'),
                        next_step=args.get('next_step'),
                        lead_summary=args.get('lead_summary'),
                        tags=args.get('tags', '').split(',') if args.get('tags') else [],
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
        
        # 1. Router
        history = request.messages[:-1]
        router_out = llm_service.router_completion(user_msg, history=history)
        logger.info(f"[Stream] Router intent: {router_out.intent}")

        # 2. Retrieval
        retrieved_docs = []
        if router_out.intent not in ("support_contact", "lead_capture"):
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
                                interest_projects=args.get('interest_projects', '').split(',') if args.get('interest_projects') else [],
                                preferred_region=args.get('preferred_region'),
                                unit_type=args.get('unit_type'),
                                budget_min=args.get('budget_min'),
                                budget_max=args.get('budget_max'),
                                purpose=args.get('purpose'),
                                timeline=args.get('timeline'),
                                next_step=args.get('next_step'),
                                lead_summary=args.get('lead_summary'),
                                tags=args.get('tags', '').split(',') if args.get('tags') else [],
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

@app.get("/admin/leads")
async def get_leads(password: str = Header(None)):
    if password != Config.ADMIN_PASSWORD:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return leads_service.get_leads()

@app.get("/admin/leads/export.xlsx")
async def export_leads(password: str = Header(None, alias="x-admin-password")):
    if password != Config.ADMIN_PASSWORD:
        raise HTTPException(status_code=401, detail="Unauthorized")
        
    path = leads_service.export_excel()
    if not path:
        raise HTTPException(status_code=404, detail="No leads to export")
        
    return FileResponse(
        path, 
        filename=os.path.basename(path), 
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

@app.get("/health")
async def health():
    return {"status": "ok", "rag_ready": rag_service.is_ready}
