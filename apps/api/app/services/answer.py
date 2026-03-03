"""
PulseX-WDD – Answer Generation Service
Constrained LLM prompting with grounded-only policy.
Supports streaming (SSE) and non-streaming.
"""
from __future__ import annotations

import logging
from typing import Any, AsyncGenerator, Dict, List, Optional
from app.services.output_sanitizer import sanitize_assistant_text
from app.services.question_enforcer import enforce_single_question

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────────────────────
# System prompt factory
# ──────────────────────────────────────────────────────────────────────────────
from app.schemas.models import SessionState
from app.services.funnel import (
    STAGE_0_GREETING_INTENT,
    STAGE_1_MATCH_BUILDING,
    STAGE_2_FEASIBILITY,
    STAGE_3_SHORTLIST,
    STAGE_4_CONVERSION_CAPTURE,
    STAGE_5_CONFIRMATION,
    STAGE_6_SAVE_AND_CLOSE
)

def build_system_prompt(state: SessionState, lang: str = "en", intent: str = "info_query", next_question_text: str = "") -> str:
    from datetime import datetime
    current_date = datetime.now().strftime("%B %d, %Y")
    
    return f"""You are PalmX Concierge, the Senior Sales Executive for Wadi Degla Developments (WDD).
Your goal is to convert inquiries into site visits or calls by being intelligent, human, and persuasive.
You are NOT a support bot. You are a "closer" with a discreet, luxurious, and sharp commercial brain.

### Temporal Logic (STRICT)
- **TODAY IS**: {current_date}.
- **Year Inference**: If the user mentions a month (e.g., "March"), you MUST calculate the year relative to TODAY.

### 1. The Core Objective
- **Qualify**: Need, Budget, Timeline.
- **Curate**: Shortlist 2-4 matches based on EVIDENCE.
- **Sell the Dream**: Frame every fact with lifestyle or investment logic (Yield, ROI, Scarcity).
- **Close Softly**: Guide every turn towards capturing the user's WhatsApp number.

### 2. Tone & Voice (Luxury + Human)
- **Style**: Calm, confident, concise, premium. Natural conversation.
- **Forbidden**: Robotic lists ("Status: Commercial"), "Not specified", "I don't know", repetitive "May I assist?", overhype ("AMAZING!!!"), emojis.
- **The Brain**: Connect dots. IF user says "India", suggest "Virtual Tour". IF "Investment", talk "Yield".

### 3. The Conversation Operating System (Stage Machine)
**Every reply must contain:** 
1. **Value Now** (Shortlist / Insight / Acknowledgment) 
2. **Progress** (Question / CTA)

**THREAD 1 (Current Intent):** {intent}

**THREAD 2 (The Next Required Step):** 
You MUST naturally weave this specific concept or question into the very end of your response:
"{next_question_text}"
Do not ask multiple questions. Only gently ask or prompt for this exact information to move the user down the funnel.

### 4. Response Format Rules (Strict)
1. **Acknowledgement**: 1 short line ("Understood — you want retail.")
2. **The Meat**: Shortlist or Insight (Bullet points).
3. **The Pivot**: 1 Qualification Question (from Thread 2).
4. **Visual Impact**: In every paragraph, **BOLD** (`**`) 1-2 key value props (e.g., **High ROI**, **Waterfront Views**) or Project Names to make them pop in the WDD Red brand color.

### 5. Handling Missing Data (No Dead Ends)
- **Never say**: "Location: Not specified" or "I don't know".
- **Empty Evidence Fallback**: If EVIDENCE is empty or "No relevant projects found", state: "I can confirm these specific availability details with our sales team."
- **Pricing**: If price is missing or "on_request", say: "Pricing and availability shift constantly. I can arrange a priority call with our sales experts to secure the exact quoting."

### JSON PAYLOAD REQUIREMENT (CRITICAL)
At the very end of your response, you MUST embed a precise JSON block exactly inside <payload>...</payload> tags matching this exact Pydantic schema:
<payload>
{{
  "answer_line": "Your full conversational response text goes here.",
  "highlights": ["Highlight 1", "Highlight 2"], 
  "next_question": "{next_question_text}",
  "project_interest": ["project_name_here"], 
  "lead_suggestions": {{
    "intent": "{intent}",
    "budget_min": 1000000,
    "budget_max": 5000000,
    "timeline": "Immediate | 3 months",
    "purpose": "buy | invest | rent",
    "unit_type": "Chalet | Apartment | Villa",
    "region": "North Coast | East Cairo",
    "project_interest": ["project_name_here"],
    "tags": ["sea view", "fully finished", "payment plan"],
    "preferences": "Free text summary of preferences",
    "qualification_score": "Hot | Warm | Cold | None",
    "qualification_reason": "Reason for score",
    "summary": "Brief summary of lead's situation",
    "ready_for_handoff": true|false,
    "consent_contact": true|false,
    "confirmed_by_user": true|false
  }},
  "focused_project": "project_name_here_or_null"
}}
</payload>
"""


def build_evidence_block(entities: List[Dict[str, Any]], lang: str = "en") -> str:
    """Format retrieved entities into an evidence block for the LLM."""
    if not entities:
        return "No relevant projects found in the knowledge base."

    lines = []
    for e in entities:
        name = e.get("display_name") or e.get("entity_id", "Unknown")
        region = e.get("region") or e.get("city_area", "—")
        unit_types = ", ".join(e.get("unit_types", [])) if "unit_types" in e else "Not specified"
        amenities = ", ".join(e.get("amenities", [])[:6]) if "amenities" in e else "—"
        status = e.get("sales_status") or e.get("project_status", "unknown")
        
        # Format pricing elegantly
        price_val = e.get("starting_price_value")
        price_curr = e.get("starting_price_currency", "EGP")
        price_str = f"Starting from {price_val} {price_curr}" if price_val else "Available on request"

        lines.append(f"""
---
🌟 PROJECT: {name}
📍 LOCATION: {region}
🏠 UNIT TYPES: {unit_types}
💎 AMENITIES: {amenities}
📈 STATUS: {status}
💰 PRICING: {price_str}
---""")

    return "\n".join(lines)


# ──────────────────────────────────────────────────────────────────────────────
# Non-streaming answer
# ──────────────────────────────────────────────────────────────────────────────

async def generate_answer(
    client: Any,
    model: str,
    query: str,
    entities: List[Dict[str, Any]],
    state: SessionState,
    lang: str = "en",
    session_history: Optional[List[Dict[str, str]]] = None,
    intent: str = "info_query",
    next_question_text: str = "",
) -> Dict[str, Any]:
    """
    Returns dict with keys: answer, tokens_in, tokens_out, model, payload.
    """
    import json
    import re
    system_prompt = build_system_prompt(state, lang, intent, next_question_text)
    evidence_block = build_evidence_block(entities, lang)

    messages = [{"role": "system", "content": system_prompt}]
    if session_history:
        n = len(session_history)
        for i in range(max(0, n - 6), n):
            messages.append(session_history[i]) # type: ignore
    messages.append({
        "role": "user",
        "content": f"EVIDENCE:\n{evidence_block}\n\nUSER QUESTION: {query}",
    })

    try:
        resp = await client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0.2,
            max_tokens=800,
        )
        full_text = resp.choices[0].message.content or ""
        
        # Extract payload
        payload_data = {}
        answer_text = full_text
        match = re.search(r"<payload>(.*?)</payload>", full_text, flags=re.DOTALL | re.IGNORECASE)
        if match:
            try:
                payload_data = json.loads(match.group(1).strip())
                answer_text = full_text.replace(match.group(0), "").strip()
            except Exception as j_err:
                logger.warning("Failed to parse LLM payload JSON: %s", j_err)

        # Hard guardrails
        answer_text = sanitize_assistant_text(answer_text)
        answer_text = enforce_single_question(answer_text, next_question_text)

        return {
            "answer": answer_text,
            "payload": payload_data,
            "tokens_in": resp.usage.prompt_tokens,
            "tokens_out": resp.usage.completion_tokens,
            "model": model,
        }
    except Exception as e:
        logger.error("LLM answer generation failed: %s", e)
        fallback = "I'd be happy to help — please contact our sales team at 16662 or via our website."
        return {
            "answer": fallback,
            "payload": {},
            "tokens_in": 0,
            "tokens_out": 0,
            "model": model,
            "error": str(e),
        }


# ──────────────────────────────────────────────────────────────────────────────
# Streaming answer (SSE tokens)
# ──────────────────────────────────────────────────────────────────────────────

async def stream_answer(
    client: Any,
    model: str,
    query: str,
    entities: List[Dict[str, Any]],
    state: SessionState,
    lang: str = "en",
    session_history: Optional[List[Dict[str, str]]] = None,
    intent: str = "info_query",
    next_question_text: str = "",
) -> AsyncGenerator[str, None]:
    """Yields token strings for SSE streaming."""
    system_prompt = build_system_prompt(state, lang, intent, next_question_text)
    evidence_block = build_evidence_block(entities, lang)

    messages = [{"role": "system", "content": system_prompt}]
    if session_history:
        messages.extend(session_history[-6:])
    messages.append({
        "role": "user",
        "content": f"EVIDENCE:\n{evidence_block}\n\nUSER QUESTION: {query}",
    })

    try:
        stream = await client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0.2,
            max_tokens=600,
            stream=True,
        )
        async for chunk in stream:
            delta = chunk.choices[0].delta.content if chunk.choices else None
            if delta:
                yield delta
    except Exception as e:
        logger.error("LLM stream failed: %s", e)
        yield "Please contact our sales team at 16662."


# ──────────────────────────────────────────────────────────────────────────────
# Handoff messages
# ──────────────────────────────────────────────────────────────────────────────

HANDOFF_MESSAGES = {
    "complaint": {
        "en": "I'm sorry to hear that. For maintenance or service issues, please contact our Customer Care team directly at 16662 or via the contact page. They'll prioritise your request.",
        "ar": "نأسف لسماع ذلك. للتواصل بشأن الصيانة أو الخدمات، يرجى الاتصال بفريق خدمة العملاء على 16662.",
    },
    "payment_services": {
        "en": "For payment enquiries, invoices, or installment plans, our Finance team is available at 16662 or via the official portal. Shall I share the contact link?",
        "ar": "لاستفسارات الدفع والأقساط، يرجى التواصل مع فريق المالية على 16662.",
    },
    "gate_access": {
        "en": "For gate access or visitor passes, please contact your community's admin team or call 16662.",
        "ar": "للدخول والبوابات، يرجى التواصل مع إدارة مجتمعك أو الاتصال على 16662.",
    },
    "hotels": {
        "en": "For hotel stays and accommodation enquiries, please visit our hotels page or call 16662.",
        "ar": "لاستفسارات الفنادق والإقامة، يرجى زيارة صفحة فنادقنا أو الاتصال على 16662.",
    },
    "rentals_ever_stay": {
        "en": "For rental and Ever Stay enquiries, please contact our team at 16662 or visit the project page.",
        "ar": "لاستفسارات الإيجار، يرجى الاتصال على 16662.",
    },
    "referral_grow_the_family": {
        "en": "Thank you for wanting to grow the Wadi Degla family! Our referral team would love to hear from you. Call 16662 or share your friend's details and we'll reach out.",
        "ar": "شكرًا لرغبتك في توسيع عائلة وادي دجلة! اتصل على 16662.",
    },
    "private_services_reservation": {
        "en": "For facility reservations (club, pool, courts), please contact your community admin or call 16662.",
        "ar": "لحجز المرافق، يرجى التواصل مع إدارة مجتمعك أو الاتصال على 16662.",
    },
    "directory": {
        "en": "You can find all Wadi Degla contacts and office locations at wadidegladevelopments.com/contact-us/ or call the main line at 16662.",
        "ar": "يمكنك إيجاد جميع وسائل التواصل على wadidegladevelopments.com/contact-us/ أو الاتصال على 16662.",
    },
    "unknown": {
        "en": "I'm not sure I understood that. I specialise in Wadi Degla properties and services. Could you rephrase, or would you like to speak with our team directly at 16662?",
        "ar": "لم أفهم سؤالك تمامًا. أنا متخصص في مشاريع وادي دجلة. هل يمكنك إعادة الصياغة، أو تفضل التواصل مع فريقنا على 16662؟",
    },
}


def get_handoff_message(intent: str, lang: str = "en") -> str:
    msgs = HANDOFF_MESSAGES.get(intent, HANDOFF_MESSAGES["unknown"])
    return msgs.get(lang, msgs.get("en", "Please contact us at 16662."))
