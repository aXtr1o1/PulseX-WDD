"""
PulseX-WDD – Deterministic Slot Extractor
Rule-based + Fuzzy slot extraction pipeline.
"""
from __future__ import annotations

import re
import logging
from typing import Dict, Any, List
from rapidfuzz import process, fuzz

logger = logging.getLogger(__name__)

# Basic currencies logic
def parse_budget(text: str) -> Dict[str, Any]:
    text = text.lower()
    res = {}
    
    # Very basic heuristics (could be expanded)
    match = re.search(r"\b(\d+(?:\.\d+)?)\s*(million|m|k|thousand|مليون|الف)\b", text)
    if match:
        res["budget_band"] = match.group(0)
        
    return res

def extract_slots(message: str, kb_project_names: List[str]) -> Dict[str, Any]:
    """
    Extracts slots strictly from the user's raw message. Returns a dictionary of updates.
    """
    text = message.lower()
    updates: Dict[str, Any] = {}
    
    # 1. Purpose
    if re.search(r"\b(invest|investment|roi|استثمار)\b", text):
        updates["purpose"] = "invest"
    elif re.search(r"\b(rent|rental|ايجار)\b", text):
        updates["purpose"] = "rent"
    elif re.search(r"\b(buy|purchase|live|شراء|اسكن)\b", text):
        updates["purpose"] = "buy"

    # 2. Region
    regions = {
        "east cairo": ["east cairo", "new cairo", "mostakbal", "التجمع"],
        "west cairo": ["west cairo", "6th october"],
        "north coast": ["north coast", "الساحل"],
        "ain el sokhna": ["ain sokhna", "sokhna", "red sea", "العين السخنة"],
        "cairo": ["maadi", "zaraa", "zahraa", "القاهرة"],
    }
    for region_name, keywords in regions.items():
        if any(kw in text for kw in keywords):
            updates["region"] = region_name
            break

    # 3. Unit Type
    types = ["villa", "apartment", "chalet", "duplex", "penthouse", "townhouse", "loft", "twinhouse", "فيلا", "شقة", "شاليه"]
    for t in types:
        if t in text:
            updates["unit_type"] = t
            break

    # 4. Timeline
    if re.search(r"\b(immediate|now|ready|جاهز|فوري|الآن)\b", text):
        updates["timeline"] = "Immediate"
    else:
        match = re.search(r"\b(\d+)\s*(months?|years?|شهر|سنة|سنين)\b", text)
        if match:
            updates["timeline"] = match.group(0)
            
    # 5. Budget
    budget_data = parse_budget(message)
    if "budget_band" in budget_data:
        # Just store as string for now based on PalmX minimum
        updates["budget_min"] = budget_data["budget_band"] 
        
    # 6. Phone
    phone_match = re.search(r"\+?[0-9\s\-().]{7,20}", text)
    if phone_match and len(re.sub(r"\D", "", phone_match.group(0))) >= 7:
        updates["phone"] = phone_match.group(0).strip()

    # 7. Project Interest (Fuzzy Match against KB Projects)
    if kb_project_names:
        # We need to be careful not to match random words. 
        # Only extract if score is very high > 85
        # Splitting message to look for phrases
        
        extracted_projects = []
        # RapidFuzz extract against the original message to preserve casing just in case (though we lowercased our text)
        res = process.extract(text, kb_project_names, scorer=fuzz.WRatio, limit=3)
        for name, score, _ in res:
            if score >= 60: # Threshold for WRatio fuzzy match
                extracted_projects.append(name)
                
        if extracted_projects:
            updates["project_interest"] = list(set(extracted_projects))

    # 8. International / Relocating Flow
    if re.search(r"\b(from \w+|new to egypt|moving to egypt|outside egypt|international)\b", text):
        updates["is_international"] = True
        updates["contact_channel"] = "whatsapp"

    # 9. High-Intent Capture Trigger (E4)
    if re.search(r"\b(price|pricing|installment|payment plan|availability|brochure|pdf|book|visit|viewing|tour|call me|whatsapp|contact)\b", text):
        updates["lead_capture_trigger"] = True

    # 10. Salvage Trigger (Confusion)
    if re.search(r"\b(i told you already|new to egypt|i have no idea|am new|don't know|not sure)\b", text):
        updates["salvage_trigger"] = True

    return updates
