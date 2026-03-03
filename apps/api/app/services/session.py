"""
PulseX-WDD – Session Management Service
Persists the 6-Stage Concierge State Machine via JSON.
"""
import json
import portalocker
from pathlib import Path
from datetime import datetime, timezone
from app.schemas.models import SessionState

SESSION_FILE = Path("runtime/session_state.json")
LOCK_FILE = Path("runtime/session_state.json.lock")

def _ensure_file():
    SESSION_FILE.parent.mkdir(parents=True, exist_ok=True)
    if not SESSION_FILE.exists():
        with open(SESSION_FILE, "w", encoding="utf-8") as f:
            json.dump({}, f)

def get_session(session_id: str) -> SessionState:
    """Retrieve an existing session or start a fresh one."""
    _ensure_file()
    
    with portalocker.Lock(str(LOCK_FILE), mode="w", timeout=10):
        with open(SESSION_FILE, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)
                if session_id in data:
                    return SessionState(**data[session_id])
            except Exception:
                pass
                
    # Return fresh state initialized to Stage 0
    return SessionState(
        session_id=session_id,
        stage=0,
        last_updated=datetime.now(timezone.utc).timestamp()
    )


def save_session(state: SessionState) -> None:
    """Persist the session state back to the store."""
    _ensure_file()
    state.last_updated = datetime.now(timezone.utc).timestamp()
    
    with portalocker.Lock(str(LOCK_FILE), mode="w", timeout=10):
        with open(SESSION_FILE, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)
            except Exception:
                data = {}
                
        data[state.session_id] = state.model_dump()
        
        with open(SESSION_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
