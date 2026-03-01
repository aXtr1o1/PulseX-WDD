"""
PulseX-WDD – Answer Generation Service
Constrained LLM prompting with grounded-only policy.
Supports streaming (SSE) and non-streaming.
"""
from __future__ import annotations

import logging
from typing import Any, AsyncGenerator, Dict, List, Optional

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────────────────────
# System prompt factory
# ──────────────────────────────────────────────────────────────────────────────

def build_system_prompt(lang: str = "en") -> str:
    if lang == "ar":
        return """أنت "بولس إكس" — المساعد الرقمي لشركة وادي دجلة للتطوير العقاري.
قواعد صارمة:
1. أجب فقط بناءً على المعلومات الموثقة.
2. إذا كان السعر "على الطلب"، قل: "الأسعار متاحة عند الطلب — هل تريد أن نرتب لك مكالمة مع فريق المبيعات؟"
3. اذكر اسم المشروع في إجابتك.
4. الأسلوب: راقٍ، دافئ. لا تذكر كلمة الذكاء الاصطناعي.
5. في نهاية إجابتك، أضف دائمًا كتلة <payload>...</payload> تحتوي على JSON.
6. إذا كانت رسالة المستخدم مجرد تحية أو تصفح عام، يجب أن تكون الإجابة سطر ترحيب واحد مع سؤال توجيهي واحد (مثال: هل تبحث عن سكن أم استثمار؟).
مثال JSON:
<payload>
{"answer_line": "مرحبا بك...", "highlights": [], "next_question": "هل تبحث في منطقة معينة؟", "shortlist": [], "lead_suggestions": {}, "focused_project": "اسم المشروع"}
</payload>
"""
    return """You are "PulseX" — the digital concierge for Wadi Degla Developments.

STRICT RULES:
1. Answer ONLY from the evidence provided. Never invent prices or availability.
2. If price_status is "on_request": say "Pricing is available on request — shall I arrange a callback with our sales team?"
3. Tone: warm, reassuring, premium. Do NOT say "AI" or "model".
4. Max answer length: 4 sentences.
5. ALWAYS embed a JSON block at the very end of your response inside <payload>...</payload> tags.
6. If the user's message is a greeting or general browsing, reply with EXACTLY 1-line welcome + 1 qualifier question (e.g. region or residential vs commercial).
If you are suggesting projects, include them in the 'shortlist'. Include any extracted lead info in 'lead_suggestions' (e.g. budget_min). 
Example:
<payload>
{"answer_line": "Welcome to Wadi Degla. I can help you shortlist verified properties.", "highlights": [], "next_question": "Are you looking to invest or live?", "shortlist": [], "lead_suggestions": {}, "focused_project": null}
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
    lang: str = "en",
    session_history: Optional[List[Dict[str, str]]] = None,
) -> Dict[str, Any]:
    """
    Returns dict with keys: answer, tokens_in, tokens_out, model, payload.
    """
    import json
    import re
    system_prompt = build_system_prompt(lang)
    evidence_block = build_evidence_block(entities, lang)

    messages = [{"role": "system", "content": system_prompt}]
    if session_history:
        messages.extend(session_history[-6:])  # Last 3 turns
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

        return {
            "answer": answer_text,
            "payload": payload_data,
            "tokens_in": resp.usage.prompt_tokens,
            "tokens_out": resp.usage.completion_tokens,
            "model": model,
        }
    except Exception as e:
        logger.error("LLM answer generation failed: %s", e)
        fallback = (
            "يسعدني مساعدتك. يرجى التواصل مع فريق المبيعات عبر الرقم 16662."
            if lang == "ar"
            else "I'd be happy to help — please contact our sales team at 16662 or via our website."
        )
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
    lang: str = "en",
    session_history: Optional[List[Dict[str, str]]] = None,
) -> AsyncGenerator[str, None]:
    """Yields token strings for SSE streaming."""
    system_prompt = build_system_prompt(lang)
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
        yield (
            "يرجى التواصل مع فريق المبيعات عبر 16662."
            if lang == "ar"
            else "Please contact our sales team at 16662."
        )


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
