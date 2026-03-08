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
            "timestamp", "lead_id", "session_id", "name", "phone", "email",
            "interest_projects", "interest_projects_display", "preferred_region", "unit_type", 
            "budget_min", "budget_max", "budget_band", "purpose", "timeline", 
            "contact_channel", "consent_contact", "confirmed_by_user",
            "lead_temperature", "reason_codes", "reason_codes_display", "tags", "tags_display", "lead_summary", 
            "customer_summary", "executive_summary", "next_action", "raw_json", "kb_version_hash"
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
        import uuid
        lead_id = f"WDDPX-{uuid.uuid4().hex[:8].upper()}"
        
        new_row = [
            datetime.now().isoformat(),
            lead_id,
            lead.session_id,
            lead.name,
            lead.phone,
            lead.email or "",
            ",".join(lead.interest_projects),
            ", ".join(lead.interest_projects),
            lead.preferred_region or "",
            lead.unit_type or "",
            lead.budget_min or "",
            lead.budget_max or "",
            "",
            lead.purpose or "",
            lead.timeline or "",
            "AI Concierge",
            str(lead.consent_contact).lower() if lead.consent_contact is not None else "false",
            "true",
            lead.lead_temperature or "Warm",
            ",".join(lead.reason_codes) if hasattr(lead, 'reason_codes') else "",
            ", ".join(lead.reason_codes) if hasattr(lead, 'reason_codes') else "",
            ",".join(lead.tags) if hasattr(lead, 'tags') else "",
            ", ".join(lead.tags) if hasattr(lead, 'tags') else "",
            lead.lead_summary or "",
            lead.customer_summary or "",
            lead.executive_summary or "",
            lead.next_action or lead.next_step or "Sales Call",
            "",
            lead.kb_version_hash or "v1.0"
        ]
        
        try:
            rows = []
            updated = False
            
            # Read existing rows
            if os.path.exists(Config.LEADS_PATH):
                with open(Config.LEADS_PATH, 'r', newline='', encoding='utf-8') as f:
                    portalocker.lock(f, portalocker.LOCK_SH)
                    reader = csv.reader(f)
                    header = next(reader, None)
                    if header:
                        rows.append(header)
                        # Find session_id column index
                        try:
                            sid_idx = header.index("session_id")
                        except ValueError:
                            sid_idx = 2 # Best guess if index fails
                        
                        for r in reader:
                            if len(r) > sid_idx and r[sid_idx] == lead.session_id:
                                # Preserve lead_id and original timestamp if updating
                                new_row[1] = r[1] if len(r) > 1 else lead_id
                                new_row[0] = r[0] if len(r) > 0 else new_row[0]
                                rows.append(new_row)
                                updated = True
                            else:
                                rows.append(r)
                    portalocker.unlock(f)

            if not updated:
                rows.append(new_row)

            # Write back
            with open(Config.LEADS_PATH, 'w', newline='', encoding='utf-8') as f:
                portalocker.lock(f, portalocker.LOCK_EX)
                writer = csv.writer(f)
                writer.writerows(rows)
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
