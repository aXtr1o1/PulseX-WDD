import csv
import os
import logging
import portalocker
from datetime import datetime
from openpyxl import Workbook
from app.backend.config import Config
from app.backend.models import Lead

logger = logging.getLogger(__name__)

class LeadsService:
    def __init__(self):
        self._init_files()

    def _init_files(self):
        # Leads CSV
        expected_headers = [
            "timestamp", "session_id", "name", "phone", 
            "interest_projects", "preferred_region", "unit_type", 
            "budget_min", "budget_max", "purpose", "timeline", 
            "next_step", "lead_summary", "tags", "kb_version_hash"
        ]
        
        if not os.path.exists(Config.LEADS_PATH):
            with open(Config.LEADS_PATH, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(expected_headers)
        else:
            # Check if header is missing in existing file
            try:
                with open(Config.LEADS_PATH, 'r', encoding='utf-8') as f:
                    first_line = f.readline().strip()
                    if first_line and "timestamp" not in first_line:
                        # Header likely missing (row starts with data), fix by prepending
                        content = f.read()
                        logger.info("Restoring missing headers to leads.csv")
                        with open(Config.LEADS_PATH, 'w', newline='', encoding='utf-8') as f2:
                            writer = csv.writer(f2)
                            writer.writerow(expected_headers)
                            f2.write(first_line + "\n" + content)
            except Exception as e:
                logger.error(f"Failed to verify/fix headers: {e}")
        
        # Audit CSV
        if not os.path.exists(Config.AUDIT_PATH):
            with open(Config.AUDIT_PATH, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([
                    "timestamp", "session_id", "user_message", "router_intent", 
                    "retrieved_projects", "similarity_scores", "kb_version", "fields_used"
                ])

    def save_lead(self, lead: Lead):
        row = [
            datetime.now().isoformat(),
            lead.session_id,
            lead.name,
            lead.phone,
            ",".join(lead.interest_projects),
            lead.preferred_region or "",
            lead.unit_type or "",
            lead.budget_min or "",
            lead.budget_max or "",
            lead.purpose or "",
            lead.timeline or "",
            lead.next_step or "",
            lead.lead_summary or "",
            ",".join(lead.tags),
            lead.kb_version_hash or "v1.0"
        ]
        
        try:
            with open(Config.LEADS_PATH, 'a', newline='', encoding='utf-8') as f:
                portalocker.lock(f, portalocker.LOCK_EX)
                writer = csv.writer(f)
                writer.writerow(row)
                portalocker.unlock(f)
            return True
        except Exception as e:
            logger.error(f"Failed to save lead: {e}")
            return False

    def log_audit(self, session_id: str, user_msg: str, intent: str, retrieved: list, scores: list):
        row = [
            datetime.now().isoformat(),
            session_id,
            user_msg,
            intent,
            json.dumps(retrieved),
            json.dumps(scores),
            "v1.0", # KB Version placeholder
            "all" # Fields used placeholder
        ]
        
        try:
            with open(Config.AUDIT_PATH, 'a', newline='', encoding='utf-8') as f:
                portalocker.lock(f, portalocker.LOCK_EX)
                writer = csv.writer(f)
                writer.writerow(row)
                portalocker.unlock(f)
        except Exception as e:
            logger.error(f"Failed to log audit: {e}")

    def get_leads(self) -> list[dict]:
        leads = []
        if os.path.exists(Config.LEADS_PATH):
            with open(Config.LEADS_PATH, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                leads = list(reader)
        return leads

    def export_excel(self) -> str:
        wb = Workbook()
        ws = wb.active
        ws.title = "WDD PulseX Leads"
        
        leads = self.get_leads()
        if not leads:
            return None
            
        # Headers
        headers = list(leads[0].keys())
        ws.append(headers)
        
        for lead in leads:
            ws.append(list(lead.values()))
            
        # Save to exports dir
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"leads_export_{timestamp}.xlsx"
        path = os.path.join(Config.RUNTIME_DIR, "exports", filename)
        wb.save(path)
        return path

import json
leads_service = LeadsService()
