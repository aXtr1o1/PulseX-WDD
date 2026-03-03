from typing import Dict, Any, List, Optional
from app.schemas.models import EvidenceSnippet

def list_projects(kb_entities: List[Dict[str, Any]], include_not_selling: bool = False, region: Optional[str] = None) -> Dict[str, Any]:
    """
    Returns a structured grouping of portfolio projects directly from the KB.
    Guarantees no hallucination of statuses.
    """
    active_projects = []
    not_selling_projects = []
    
    for e in kb_entities:
        r = e.get("region", "").lower()
        if region and region.lower() not in r:
            continue
            
        status = str(e.get("sales_status") or e.get("project_status") or "unknown").lower()
        
        # If status is completely missing or unknown, treat as selling to be safe but don't explicitly claim status
        if status in ["sold out", "not selling", "inactive", "not available"]:
            not_selling_projects.append(e)
        else:
            active_projects.append(e)
            
    # Format for response
    def format_list(entities: List[Dict[str, Any]]) -> str:
        if not entities:
            return ""
        
        # Group by region
        by_region = {}
        for ent in entities:
            reg = ent.get("region") or "Other"
            if reg not in by_region:
                by_region[reg] = []
            name = ent.get("display_name") or ent.get("entity_id", "")
            unit_types = ", ".join(ent.get("unit_types", []))
            by_region[reg].append(f"- **{name}** ({unit_types})" if unit_types else f"- **{name}**")
            
        lines = []
        for reg, projs in by_region.items():
            lines.append(f"\n{reg}:")
            lines.extend(projs)
            
        return "\n".join(lines)

    answer_parts = []
    evidence = []
    
    if active_projects:
        answer_parts.append("Here are our currently available projects:")
        answer_parts.append(format_list(active_projects[:12]))
        if len(active_projects) > 12:
            answer_parts.append("\n*I can narrow this down if you specify a region or unit type.*")
            
        for e in active_projects[:5]:
            evidence.append(EvidenceSnippet(
                entity_id=e["entity_id"],
                display_name=e["display_name"],
                source_url=e.get("verified_url") or "",
                snippet=e.get("index_text", "")[:100],
                confidence=1.0
            ))
            
    if include_not_selling and not_selling_projects:
        answer_parts.append("\n\nNot Currently Selling:")
        answer_parts.append(format_list(not_selling_projects))
        
    if not answer_parts:
        return {
            "answer": "I couldn't find any projects matching those criteria right now.",
            "evidence": [],
            "shortlist": []
        }
        
    return {
        "answer": "\n".join(answer_parts),
        "evidence": evidence,
        "shortlist": [e.get("display_name", e.get("entity_id", "")) for e in active_projects[:5]]
    }
