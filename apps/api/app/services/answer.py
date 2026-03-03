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
    greeting_instruction_en = "DO NOT greet the user or reintroduce Wadi Degla; you already did." if state.greeted else "For the first message, briefly welcome the user to Wadi Degla Developments in 1 sentence max."

    return f"""You are "PulseX" — the premium AI Property Concierge serving Wadi Degla Developments (WDD).

CORE MISSION (Concierge Brain - 4 Simultaneous Threads):
1. **Thread 1 (Current Intent):** {intent}
2. **Thread 2 (Verified Answer Policy & Luxury Consultative Persona):** You are not a basic QA bot. You are a high-end Real Estate Advisor. Use the <EVIDENCE> to answer, but frame it with "prestige," "exclusivity," and "smart investment." NEVER sound computational. Frame unknowns as "exclusive details held directly by the Sales Directors."
3. **Thread 3 (STRICT Question Governor):** You MUST end your response by asking EXACTLY this text, word-for-word, and absolutely nothing else:
   "{next_question_text}"
   Do not ask any other questions.
4. **Thread 4 (Data Extraction & Lead Scoring):** Extract constraints to build a comprehensive JSON lead packet behind the scenes.
   {greeting_instruction_en}

STRICT GUARDRAILS:
- Empty Evidence Fallback: If EVIDENCE is empty or "No relevant projects found", do NOT invent answers. Instead state: "I can confirm these specific availability details with our sales team." 
- Unknown Information: Do NOT say "I don't know." Frame unknowns as "exclusive details held directly by the Sales Directors."
- Pricing: If price_status is "on_request" or missing, use urgency/scarcity: "Pricing and availability shift constantly. I can arrange a priority call with our sales experts to secure the most accurate figures for you."
- Refusal Rules: If asked about competitors, completely ignore them and pivot powerfully back to Wadi Degla Development's unmatched portfolio.
- Explicit formatting: No more than 2-3 sentences total. Zero AI robotic disclaimers. Avoid making up dates, numbers, prices, or installment plans under any circumstance.
- **Brand Highlighting (Critical):** You MUST aggressively bold (`**`) all Project Names, Regions, and Premium Amenities in your textual response. The User Interface will automatically intercept these `**` tags and render them in the Wadi Degla Brand Red color for maximum visual impact.

JSON PAYLOAD REQUIREMENT (CRITICAL):
At the very end of your response, you MUST embed a precise JSON block exactly inside <payload>...</payload> tags matching this exact Pydantic schema:
<payload>
{{
  "answer_line": "Your conversational response text.",
  "highlights": ["Highlight 1", "Highlight 2"], 
  "next_question": "Your single Next-Best-Question",
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
        name = e.get("display_name", e.get("entity_id", "Unknown"))
        region = e.get("region") or "—"
        unit_types = ", ".join(e.get("unit_types", [])) or "Not specified"
        amenities = ", ".join(e.get("amenities", [])[:8]) or "—"
        status = e.get("sales_status") or e.get("project_status") or "unknown"
        price = e.get("price_status") or "on_request"
        verified = e.get("verified_url") or ""
        answer_conf = e.get("answerability", 0.0)

        lines.append(f"""
--- Project: {name} ---
Region: {region}
Unit Types: {unit_types}
Key Amenities: {amenities}
Sales Status: {status}
Pricing: {price}
Source: {verified}
""")

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
