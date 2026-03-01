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
    
    # Must route to sales intent and trigger lead capture
    assert data["intent_lane"] == "sales_intent"
    assert data["lead_trigger"] is True
