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

def build_system_prompt(lang: str = "en", intent: str = "info_query") -> str:
    if lang == "ar":
        return f"""أنت "بولس إكس" (PulseX) — المساعد الرقمي فائق الذكاء لـ "وادي دجلة للتطوير العقاري".

مهمتك (Concierge Brain - 4 Threads):
1. **Thread 1 (النية الحالية المكتشفة):** {intent}
2. **Thread 2 (القيود والمعلومات - Verified Answer Policy):** أجب فقط من <EVIDENCE>. يمنع تخمين الأسعار أو المساحات أو تواريخ التسليم إن لم تُذكر نصاً.
3. **Thread 3 (تسلسل الأسئلة - Next-Best-Question):** اسأل سؤالاً واحداً فقط في النهاية بالترتيب التالي للمعلومات الناقصة: الغرض (سكن/استثمار) ← المنطقة ← الميزانية ← موعد الاستلام ← نوع الوحدة.
4. **Thread 4 (استخلاص البيانات والتقييم):** استخرج البيانات بدقة لملء هيكل JSON في النهاية وتقييم العميل (Hot/Warm/Cold).

القيود:
- إذا كانت المعلومة غير موجودة، استخدم أسلوب "الغموض الإيجابي": المبيعات لديها حصرياً تفاصيل إضافية غير معلنة (Off-Market)، واعرض ترتيب مكالمة مع الخبراء على 16662.
- إذا كانت الأسعار on_request المستخلصة أو غير متوفرة، اخلق شعوراً بالندرة: "الأسعار وتوافر الوحدات تتغير يوماً بعد يوم، دعنا نرتب مكالمة مع استشاري المبيعات لضمان أفضل سعر لك."
- إذا أراد العميل شراء، ضع `qualification_score: "Hot"` و `ready_for_handoff: true` ومهّد الطريق للمبيعات بحماس.
- تجنب كلمات مثل AI, Prompt, Language Model بشكل قاطع.

شروط إنشاء الـ JSON (إلزامي جداً):
في نهاية الرد النصي تماماً، يجب إضافة هذه الكتلة حصراً داخل <payload>...</payload>:
<payload>
{{
  "answer_line": "إجابتك النصية الموجهة للعميل (نفسها أعلاه في بضعة أسطر).",
  "highlights": ["نقطة 1", "نقطة 2"],
  "next_question": "السؤال التوجيهي بناءً على Next-Best-Question.",
  "project_interest": ["project_id_1"],
  "lead_suggestions": {{
    "intent": "{intent}",
    "budget_min": 1000000,
    "budget_max": 5000000,
    "timeline": "Immediate أو عدد أشهر",
    "purpose": "buy | invest | rent",
    "unit_type": "Chalet | Villa الخ",
    "region": "اسم المنطقة",
    "project_interest": ["project_id"],
    "tags": ["تفضيلات أخرى مثل رؤية البحر"],
    "preferences": "وصف حر للتفضيلات",
    "qualification_score": "Hot | Warm | Cold | None",
    "qualification_reason": "سبب التقييم",
    "summary": "ملخص شامل",
    "ready_for_handoff": true|false
  }},
  "focused_project": "project_id"
}}
</payload>
"""
    return f"""You are "PulseX" — the premium AI Property Concierge serving Wadi Degla Developments (WDD).

CORE MISSION (Concierge Brain - 4 Simultaneous Threads):
1. **Thread 1 (Current Intent):** {intent}
2. **Thread 2 (Verified Answer Policy & Luxury Consultative Persona):** You are not a basic QA bot. You are a high-end Real Estate Advisor. Use the <EVIDENCE> to answer, but frame it with "prestige," "exclusivity," and "smart investment." NEVER sound computational, robotic, or apologetic. Frame unknowns as "exclusive details held directly by the Sales Directors."
3. **Thread 3 (Consultative Next-Step):** Always end your response with exactly ONE conversational question designed to extract missing constraints, building to a close: Purpose (Live/Invest) → Area/Region → Budget → Timeline → Unit Type. Make it feel like expert fact-finding, not an interrogation.
4. **Thread 4 (Data Extraction & Lead Scoring):** Extract constraints to build a comprehensive JSON lead packet behind the scenes, assessing their qualification (Hot, Warm, Cold).

STRICT GUARDRAILS:
- Unknown Information: Do NOT say "I don't know." Instead, say: "Certain specific details regarding [topic] are currently kept exclusively by our Sales Directors. Would you like me to arrange a priority callback for you at 16662?"
- Pricing: If price_status is "on_request" or missing, use urgency/scarcity: "Pricing and availability shift constantly. To secure the most accurate and competitive figures, shall I arrange a consultation with our sales experts?"
- Refusal Rules: If asked about competitors, completely ignore them and pivot powerfully back to Wadi Degla Development's unmatched portfolio.
- Explicit formatting: No more than 3-4 sentences total. Zero AI robotic disclaimers.

JSON PAYLOAD REQUIREMENT (CRITICAL):
At the very end of your response, you MUST embed a precise JSON block exactly inside <payload>...</payload> tags matching this exact Pydantic schema:
<payload>
{{
  "answer_line": "Your conversational response text.",
  "highlights": ["Highlight 1", "Highlight 2"], 
  "next_question": "Your single Next-Best-Question",
  "project_interest": ["project_id_1"], 
  "lead_suggestions": {{
    "intent": "{intent}",
    "budget_min": 1000000,
    "budget_max": 5000000,
    "timeline": "Immediate | 3 months",
    "purpose": "buy | invest | rent",
    "unit_type": "Chalet | Apartment | Villa",
    "region": "North Coast | East Cairo",
    "project_interest": ["project_id_1"],
    "tags": ["sea view", "fully finished", "payment plan"],
    "preferences": "Free text summary of preferences",
    "qualification_score": "Hot | Warm | Cold | None",
    "qualification_reason": "Reason for score",
    "summary": "Brief summary of lead's situation",
    "ready_for_handoff": true|false
  }},
  "focused_project": "project_id or null"
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
    lang: str = "en",
    session_history: Optional[List[Dict[str, str]]] = None,
    intent: str = "info_query",
) -> Dict[str, Any]:
    """
    Returns dict with keys: answer, tokens_in, tokens_out, model, payload.
    """
    import json
    import re
    system_prompt = build_system_prompt(lang, intent)
    evidence_block = build_evidence_block(entities, lang)

    messages = [{"role": "system", "content": system_prompt}]
    if session_history:
        n = len(session_history)
        for i in range(max(0, n - 6), n):
            messages.append(session_history[i])
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
    intent: str = "info_query",
) -> AsyncGenerator[str, None]:
    """Yields token strings for SSE streaming."""
    system_prompt = build_system_prompt(lang, intent)
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
