"""
PulseX-WDD Leads Service — Lead persistence with hard gates and schema alignment.
Writes ONLY when phone + confirmed + consent gates pass.
"""

import csv
import json
import os
import hashlib
import logging
import portalocker
from datetime import datetime
from typing import Optional
from openpyxl import Workbook
from app.backend.config import Config
from app.backend.models import Lead

logger = logging.getLogger(__name__)

LEAD_HEADERS = [
    "timestamp", "lead_id", "session_id", "name", "phone", "email",
    "interest_projects", "preferred_region", "unit_type",
    "budget_min", "budget_max", "budget_band", "purpose", "timeline",
    "contact_channel", "consent_contact", "confirmed_by_user",
    "lead_temperature", "reason_codes", "tags", "lead_summary",
    "raw_json", "kb_version_hash"
]

AUDIT_HEADERS = [
    "timestamp", "session_id", "stage", "intent", "high_intent",
    "user_message", "focused_project", "retrieved_projects",
    "empty_retrieval", "error_reason", "status"
]


class LeadsService:
    def __init__(self):
        self._init_files()

    def _init_files(self):
        """Ensure leads.csv and audit.csv exist with correct headers."""
        if not os.path.exists(Config.LEADS_PATH):
            with open(Config.LEADS_PATH, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(LEAD_HEADERS)
        else:
            # Verify header
            try:
                with open(Config.LEADS_PATH, 'r', encoding='utf-8') as f:
                    first_line = f.readline().strip()
                    if first_line and "lead_id" not in first_line and "timestamp" not in first_line:
                        content = f.read()
                        logger.info("Restoring missing headers to leads.csv")
                        with open(Config.LEADS_PATH, 'w', newline='', encoding='utf-8') as f2:
                            writer = csv.writer(f2)
                            writer.writerow(LEAD_HEADERS)
                            f2.write(first_line + "\n" + content)
            except Exception as e:
                logger.error(f"Failed to verify/fix headers: {e}")

        if not os.path.exists(Config.AUDIT_PATH):
            with open(Config.AUDIT_PATH, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(AUDIT_HEADERS)

    @staticmethod
    def generate_lead_id() -> str:
        """Generate a unique lead ID: WDDPX-{hash}"""
        ts = datetime.utcnow().isoformat()
        h = hashlib.sha256(ts.encode()).hexdigest()[:8].upper()
        return f"WDDPX-{h}"

    @staticmethod
    def can_save(lead: Lead) -> bool:
        """Hard gate: phone + confirmed + consent required."""
        has_phone = bool(lead.phone and lead.phone.strip())
        confirmed = lead.confirmed_by_user
        consented = lead.consent_contact
        return has_phone and confirmed and consented

    def save_lead(self, lead: Lead) -> bool:
        """Save a fully-gated lead to CSV. Returns False if gates fail."""
        if not self.can_save(lead):
            logger.warning(f"Lead gate failed for session {lead.session_id}: "
                           f"phone={bool(lead.phone)}, confirmed={lead.confirmed_by_user}, "
                           f"consent={lead.consent_contact}")
            return False

        # Generate lead_id if missing
        if not lead.lead_id:
            lead.lead_id = self.generate_lead_id()

        row = [
            datetime.utcnow().isoformat() + "Z",               # timestamp
            lead.lead_id,                                        # lead_id
            lead.session_id,                                     # session_id
            lead.name or "",                                     # name
            lead.phone or "",                                    # phone
            lead.email or "",                                    # email
            ",".join(lead.interest_projects),                    # interest_projects
            lead.preferred_region or "",                         # preferred_region
            lead.unit_type or "",                                # unit_type
            lead.budget_min or "",                               # budget_min
            lead.budget_max or "",                               # budget_max
            lead.budget_band or "",                              # budget_band
            lead.purpose or "",                                  # purpose
            lead.timeline or "",                                 # timeline
            lead.contact_channel or "whatsapp",                  # contact_channel
            str(lead.consent_contact).lower(),                   # consent_contact
            str(lead.confirmed_by_user).lower(),                 # confirmed_by_user
            lead.lead_temperature or "",                         # lead_temperature
            ",".join(lead.reason_codes),                         # reason_codes
            ",".join(lead.tags),                                 # tags
            lead.lead_summary or "",                             # lead_summary
            "",                                                  # raw_json (reserved)
            lead.kb_version_hash or "v1.0",                     # kb_version_hash
        ]

        try:
            with open(Config.LEADS_PATH, 'a', newline='', encoding='utf-8') as f:
                portalocker.lock(f, portalocker.LOCK_EX)
                writer = csv.writer(f)
                writer.writerow(row)
                portalocker.unlock(f)
            logger.info(f"✅ Lead saved: {lead.lead_id} | {lead.name} | {lead.phone}")
            return True
        except Exception as e:
            logger.error(f"Failed to save lead: {e}")
            return False

    def log_audit(
        self,
        session_id: str,
        stage: str,
        intent: str,
        high_intent: bool,
        user_message: str,
        focused_project: Optional[str],
        retrieved_projects: list,
        empty_retrieval: bool,
        error_reason: str = "",
        status: str = "ok",
    ):
        """Log every turn for quality telemetry."""
        row = [
            datetime.utcnow().isoformat() + "Z",
            session_id,
            stage,
            intent,
            str(high_intent).lower(),
            user_message[:200],  # Truncate to prevent huge rows
            focused_project or "",
            json.dumps(retrieved_projects),
            str(empty_retrieval).lower(),
            error_reason,
            status,
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

    def export_excel(self) -> Optional[str]:
        wb = Workbook()
        ws = wb.active
        ws.title = "WDD PulseX Leads"
        leads = self.get_leads()
        if not leads:
            return None
        headers = list(leads[0].keys())
        ws.append(headers)
        for lead in leads:
            ws.append(list(lead.values()))
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"leads_export_{timestamp}.xlsx"
        path = os.path.join(Config.RUNTIME_DIR, "exports", filename)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        wb.save(path)
        return path


leads_service = LeadsService()
