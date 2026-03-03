from fastapi import APIRouter
from app.services.session import get_session

router = APIRouter(prefix="/api/debug", tags=["debug"])

@router.get("/session/{session_id}")
async def get_debug_session(session_id: str):
    """
    Returns the current state of a session. If it doesn't exist,
    returns a fresh initialised stage 0 session.
    """
    state = get_session(session_id)
    return {
        "session_id": state.session_id,
        "stage": state.stage,
        "collected_fields": state.collected_fields,
        "last_updated": state.last_updated,
        "created_at": getattr(state, "created_at", None),
    }
