import sys
import os

# Set PYTHONPATH to include the project root
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.backend.services.llm_service import LLMService
from app.backend.models import Message

llm = LLMService()

msg = "I wnat in Cairo & east cairo"
history = [
    Message(role="assistant", content="We have several prime regions..."),
]

out = llm.router_completion(msg, history=history)

print("INTENT:", out.intent)
print("FILTERS:", out.filters)
print("TYPE OF REGION FILTER:", type(out.filters.get('region')))
