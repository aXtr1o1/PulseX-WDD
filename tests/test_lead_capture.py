"""
Test Lead Capture constraints and DB (CSV) writing integrity.
"""
from pathlib import Path
from apps.api.app.config import get_settings
from apps.api.app.utils.csv_io import read_csv_rows

def test_lead_capture_validation(client):
    # Missing required phone & consent
    res = client.post(
        "/api/lead",
        json={
            "session_id": "test_sess_4",
            "lang": "en",
            "name": "Testing Valid"
        }
    )
    # Should fail validation (assuming phone / consent required)
    # FastAPI gives 422 if Pydantic model enforces it, or customized logic returns 400.
    assert res.status_code in [400, 422]

def test_lead_capture_valid(client):
    settings = get_settings()
    leads_path = settings.leads_csv_path
    
    # Count rows before
    rows_before = len(read_csv_rows(leads_path)) if leads_path.exists() else 0
    
    # Missing optional but satisfying requirements
    res = client.post(
        "/api/lead",
        json={
            "session_id": "test_sess_5",
            "lang": "en",
            "phone": "+201012345678",
            "name": "Valid Test Lead",
            "consent_callback": True,
            "consent_marketing": False
        }
    )
    
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert "lead_id" in data
    
    # Count rows after
    rows_after = len(read_csv_rows(leads_path))
    assert rows_after == rows_before + 1
