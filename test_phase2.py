import sys
import asyncio
from app.schemas.models import SessionState
from app.services.slot_extractor import extract_slots
from app.services.funnel_policy import get_next_question

def run_test_1():
    print("--- Test 1 (no repeats) ---")
    state = SessionState(session_id="test1", collected_fields={"purpose": "invest"})
    # Let's say user said "I want to invest"
    msg = "I want to invest"
    kb_names = ["ClubTown", "Neo Lakes"]
    slots = extract_slots(msg, kb_names)
    state.collected_fields.update(slots)
    
    q_key, text, options = get_next_question(state, "info_query", slots)
    print(f"Next question key: {q_key}")
    print(f"Next question text: {text}")
    assert q_key in ["region", "unit_type"], f"Expected region or unit_type, got {q_key}"

def run_test_2():
    print("\n--- Test 2 (project pin with typo) ---")
    state = SessionState(session_id="test2", collected_fields={})
    msg = "Neo laks and clubtwn"
    kb_names = ["ClubTown", "Neo Lakes", "Other Project"]
    slots = extract_slots(msg, kb_names)
    state.collected_fields.update(slots)
    
    print(f"Extracted slots: {slots}")
    assert "project_interest" in slots, "Fuzzy match failed to find projects"
    
    q_key, text, options = get_next_question(state, "info_query", slots)
    print(f"Next question key: {q_key}")
    print(f"Next question text: {text}")
    assert q_key == "budget_min", f"Expected budget_min due to pinned projects, got {q_key}"

def run_test_3():
    print("\n--- Test 3 (International Flow) ---")
    state = SessionState(session_id="test3", collected_fields={})
    msg = "I am moving to Egypt soon."
    slots = extract_slots(msg, [])
    state.collected_fields.update(slots)
    
    print(f"Extracted slots: {slots}")
    assert slots.get("is_international") == True
    
    q_key, text, options = get_next_question(state, "info_query", slots)
    print(f"Next question key: {q_key}")
    print(f"Next question text: {text}")
    assert q_key == "region" and "virtual walkthrough" in text.lower()

if __name__ == "__main__":
    run_test_1()
    run_test_2()
    run_test_3()
    print("\nALL OFFLINE POLICY TESTS PASSED.")
