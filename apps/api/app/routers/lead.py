"""
PulseX-WDD – Lead Router
Explicit lead submission endpoint.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Request, status

from ..config import get_settings
from ..schemas.models import LeadRequest, LeadResponse
from ..services.lead import save_lead, get_next_lead_prompt

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["lead"])


@router.post("/lead", response_model=LeadResponse)
async def submit_lead(lead: LeadRequest, req: Request) -> LeadResponse:
    """
    Accept a fully or partially populated lead.
    Saves to leads.csv and returns reference ID.
    """
    settings = get_settings()
    # Require at least phone OR email
    if not lead.phone and not lead.email:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="At least one of phone or email is required.",
        )

    lead_id = save_lead(lead, settings.leads_csv_path)
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
