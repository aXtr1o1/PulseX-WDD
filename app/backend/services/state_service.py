"""
PulseX-WDD State Service — Session state persistence (CSV + state_json).
Persists per-session conversation state so slots survive page reloads.
"""

import csv
import json
import os
import logging
import portalocker
from datetime import datetime
from typing import Optional

from app.backend.config import Config
from app.backend.models import SessionState, Slots, Stage

logger = logging.getLogger("PulseX-WDD-State")

SESSIONS_PATH = os.path.join(Config.RUNTIME_DIR, "leads", "sessions_state.csv")

HEADERS = ["session_id", "started_at", "last_seen_at", "state_json"]


class StateService:
    def __init__(self):
        self._ensure_file()

    def _ensure_file(self):
        if not os.path.exists(SESSIONS_PATH):
            with open(SESSIONS_PATH, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(HEADERS)

    def load_state(self, session_id: str) -> SessionState:
        """Load session state from CSV. Returns fresh state if not found."""
        if os.path.exists(SESSIONS_PATH):
            try:
                with open(SESSIONS_PATH, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        if row.get("session_id") == session_id:
                            state_json = row.get("state_json", "{}")
                            try:
                                data = json.loads(state_json)
                                # Reconstruct SessionState
                                slots_data = data.get("slots", {})
                                slots = Slots(**slots_data)
                                return SessionState(
                                    session_id=session_id,
                                    greeted=data.get("greeted", False),
                                    stage=Stage(data.get("stage", "GREETING")),
                                    slots=slots,
                                    focused_project=data.get("focused_project"),
                                    turn_count=data.get("turn_count", 0),
                                )
                            except Exception as e:
                                logger.warning(f"Failed to parse state for {session_id}: {e}")
            except Exception as e:
                logger.error(f"Failed to read sessions CSV: {e}")

        # Return fresh state
        return SessionState(session_id=session_id)

    def save_state(self, state: SessionState):
        """Save session state to CSV (update existing or append new)."""
        now = datetime.utcnow().isoformat() + "Z"
        state_json = json.dumps({
            "greeted": state.greeted,
            "stage": state.stage.value,
            "slots": state.slots.model_dump(),
            "focused_project": state.focused_project,
            "turn_count": state.turn_count,
        })

        try:
            # Read all rows
            rows = []
            found = False
            if os.path.exists(SESSIONS_PATH):
                with open(SESSIONS_PATH, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        if row.get("session_id") == state.session_id:
                            row["last_seen_at"] = now
                            row["state_json"] = state_json
                            found = True
                        rows.append(row)

            if not found:
                rows.append({
                    "session_id": state.session_id,
                    "started_at": now,
                    "last_seen_at": now,
                    "state_json": state_json,
                })

            # Write back
            with open(SESSIONS_PATH, 'w', newline='', encoding='utf-8') as f:
                portalocker.lock(f, portalocker.LOCK_EX)
                writer = csv.DictWriter(f, fieldnames=HEADERS)
                writer.writeheader()
                writer.writerows(rows)
                portalocker.unlock(f)

        except Exception as e:
            logger.error(f"Failed to save state for {state.session_id}: {e}")


state_service = StateService()
