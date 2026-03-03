"""
PulseX-WDD – Lead Router
Explicit lead submission endpoint.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Request, status

from ..config import get_settings
from ..schemas.models import LeadRequest, LeadResponse
from ..services.lead import save_lead_if_confirmed, get_next_lead_prompt
from ..services.session import get_session

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["lead"])


@router.post("/lead", response_model=LeadResponse)
async def submit_lead(lead: LeadRequest, req: Request) -> LeadResponse:
    """
    Accept a manually submitted form lead (fallback).
    Maps into SessionState and saves to leads.csv.
    """
    settings = get_settings()
    if not lead.phone and not lead.email:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="At least one of phone or email is required.",
        )

    state = get_session(lead.session_id)
    fields = lead.model_dump(exclude={"session_id", "lang"})
    state.collected_fields.update(fields)
    state.collected_fields["confirmed_by_user"] = True
    state.collected_fields["consent_contact"] = lead.consent_callback or lead.consent_marketing
    
    lead_id = save_lead_if_confirmed(state, settings.leads_csv_path)
    if not lead_id:
        raise HTTPException(
            status_code=400,
            detail="Lead rejected by Funnel constraint verification.",
        )
    msg_en = f"Thank you! We've recorded your request (Ref: {lead_id}). Our team will be in touch shortly."
    msg_ar = f"شكرًا! تم تسجيل طلبك (رقم المرجع: {lead_id}). سيتواصل معك فريقنا قريبًا."
    message = msg_ar if lead.lang == "ar" else msg_en

    return LeadResponse(success=True, lead_id=lead_id, message=message)


@router.get("/lead/next-prompt")
async def lead_next_prompt(session_id: str, lang: str = "en", req: Request = None):
    """
    Helper endpoint: given what's collected so far (query params), return next prompt.
    Used by the widget for progressive profiling.
    """
    # Parse partial lead from query params
    if req is None:
        return {"prompt": None}
    params = dict(req.query_params)
    params.pop("session_id", None)
    params.pop("lang", None)
    prompt = get_next_lead_prompt(params, lang)
    return {"prompt": prompt}
