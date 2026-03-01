"""
Test readiness checks and index absence detection.
"""
import os
import shutil
from pathlib import Path
from apps.api.app.config import REPO_ROOT

def test_health_with_indices(client):
    # Depending on how the repository is structured, indices might be built.
    # Assuming indices exist for the test:
    res = client.get("/api/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    
def test_health_missing_indices(client):
    # Temporarily hide indices dir
    indices_dir = REPO_ROOT / "indices"
    backup_dir = REPO_ROOT / "indices_backup_temp"
    
    if indices_dir.exists():
        shutil.move(str(indices_dir), str(backup_dir))
    
    try:
        res = client.get("/api/health")
        data = res.json()
        
        # It should show index_ready == false
        assert data["index_ready"] is False
        
    finally:
        # Restore indices
        if backup_dir.exists():
            if indices_dir.exists():
                shutil.rmtree(indices_dir)
            shutil.move(str(backup_dir), str(indices_dir))
