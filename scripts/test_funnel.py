import asyncio
import json
import uuid
import sys
import os

# Add parent directory to path so we can import app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.backend.models import ChatRequest, Message
from app.backend.services.llm_service import LLMService
from app.backend.services.rag_service import RAGService
from app.backend.services.kb_service import KBService
from app.backend.main import CONCIERGE_SYSTEM_PROMPT, TOOLS
from datetime import datetime

async def test_funnel():
    print("Initializing services...")
    kb = KBService()
    rag = RAGService()
    llm = LLMService()
    
    session_id = str(uuid.uuid4())
    history = []
    
    # Simulating a buyer flow
    # Turn 1: vague
    # Turn 2: answers qualification
    # Turn 3: likes a project, gives phone
    turns = [
        "I'm looking for a summer house, maybe a chalet.",
        "My budget is around 5 million EGP, I prefer the Red Sea area like Sokhna.",
        "Murano sounds great. Yes, please send the brochures to my WhatsApp. My name is Ahmed and number is 01012345678.",
        "Yes, please."
    ]
    
    print("\n--- Starting Conversation ---")
    for user_text in turns:
        print(f"\n[USER]: {user_text}")
        
        # 1. Routing
        router_out = llm.router_completion(user_text, history)
        print(f"  [Router Intent]: {router_out.intent}")
        print(f"  [Router Rewrite]: {router_out.query_rewrite}")
        
        # 2. Retrieval
        retrieved_docs = []
        if router_out.intent not in ("support_contact", "lead_capture"):
            results = rag.search(router_out.query_rewrite, k=3, filters=router_out.filters)
            retrieved_docs = [r['project'] for r in results]
            
        context_text = ""
        for p in retrieved_docs:
            context_text += f"---\n{kb.build_project_card(p)}\n"
            
        # 3. Prompting
        current_date = datetime.now().strftime("%B %d, %Y")
        system_msg = CONCIERGE_SYSTEM_PROMPT.format(current_date=current_date) + f"\n\nCONTEXT:\n{context_text}"
        
        messages = history + [Message(role="user", content=user_text)]
        
        # 4. LLM call
        response = llm.answer_completion(system_msg, messages, tools=TOOLS)
        
        if isinstance(response, list):
            # Tool call
            for t in response:
                if t.function.name == "save_lead":
                    print("\n🚨 [TOOL CALL TRIGGERED]: save_lead")
                    args = json.loads(t.function.arguments)
                    print(json.dumps(args, indent=2))
                    
                    # Verify our new fields exist
                    assert 'lead_temperature' in args, "Missing lead_temperature!"
                    assert 'consent_contact' in args, "Missing consent_contact!"
                    
                    history.append(Message(role="assistant", content=f"[Tool Call: save_lead with {args['name']}]"))
        else:
            print(f"\n[AI]: {response}")
            history.append(Message(role="user", content=user_text))
            history.append(Message(role="assistant", content=response))
            
if __name__ == "__main__":
    asyncio.run(test_funnel())
