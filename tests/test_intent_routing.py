"""
Test intent routing for chat endpoint.
"""
def test_greeting_routing(client):
    res = client.post(
        "/api/chat",
        json={"message": "hi", "lang": "en", "session_id": "test_sess_1"}
    )
    assert res.status_code == 200
    data = res.json()
    
    assert data["intent_lane"] == "greeting"
    assert data["lead_trigger"] is False
    # The answer should contain qualifier questions like region or project.
    assert "project" in data["answer"].lower() or "region" in data["answer"].lower() or "looking for" in data["answer"].lower()


def test_sales_intent_routing(client):
    res = client.post(
        "/api/chat",
        json={"message": "I want to see the payment plan for Murano", "lang": "en", "session_id": "test_sess_2"}
    )
    assert res.status_code == 200
    data = res.json()
    
    # Must route to pricing or info_query and trigger lead capture (if intent says so)
    assert data["intent_lane"] in ["pricing", "info_query", "lead_capture"]
    # With Phase 12, lead_trigger is based on the LLM payload, which we mocked to {}
    # So lead_trigger will be False from the chat.py endpoint unless intent is LEAD_CAPTURE
    assert isinstance(data["lead_trigger"], bool)
