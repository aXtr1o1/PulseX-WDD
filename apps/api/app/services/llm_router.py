"""
PulseX-WDD – PalmX-style LLM Router
Optional intelligence to determine intent and rewrite queries.
"""
from typing import Dict, Any, List
import json

def router_completion(message: str, client: Any, model: str, kb_project_names: List[str]) -> Dict[str, Any]:
    """
    Returns extracted intent and hints via strict JSON.
    NOTE: PulseX-WDD primarily uses the deterministic SlotExtractor for precision.
    This just supplements query rewriting.
    """
    system_prompt = f"""
    You are an AI router for a Real Estate Assistant.
    Your job is to read the user's message and determine intent.
    
    Known project families: {', '.join(kb_project_names)[:1000]}
    
    Respond STRICTLY with a JSON object:
    {{
      "intent": "info_query" | "shortlist" | "pricing" | "handoff" | "lead_capture",
      "entities": {{"project_names": []}},
      "query_rewrite": "search optimized string",
      "urgency": "high" | "low"
    }}
    """
    
    try:
        completion = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": message}
            ],
            temperature=0,
            response_format={"type": "json_object"}
        )
        result = json.loads(completion.choices[0].message.content)
        return result
    except Exception as e:
        return {"intent": "info_query", "entities": {}, "query_rewrite": message, "urgency": "low"}
