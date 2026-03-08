import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.backend.services.rag_service import rag_service

try:
    results = rag_service.search("I wnat in Cairo & east cairo", k=3, filters={'region': 'Cairo & East Cairo'})
    print("SUCCESS, found", len(results))
except Exception as e:
    import traceback
    traceback.print_exc()
