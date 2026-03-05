"""
PulseX-WDD KB Service — Knowledge Base loader with selling-only default,
evidence pack generation, and portfolio listing.
"""

import csv
import json
import logging
import os
from typing import List, Dict, Any, Optional
from app.backend.config import Config
from app.backend.models import Project, EvidencePack

logger = logging.getLogger(__name__)


class KBService:
    def __init__(self):
        self.projects: Dict[str, Project] = {}
        self.raw_rows: List[Dict[str, Any]] = []
        self._load_kb()

    def _load_kb(self):
        if not os.path.exists(Config.KB_CSV_PATH):
            logger.error(f"KB CSV not found at {Config.KB_CSV_PATH}")
            return

        logger.info(f"Loading finalized KB from: {Config.KB_CSV_PATH}")

        with open(Config.KB_CSV_PATH, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                clean_row = {k: self._clean_val(v) for k, v in row.items()}

                # Parse JSON fields
                for k, v in clean_row.items():
                    if k.endswith('_json') or k in ['canon_unit_types', 'canon_quality_flags']:
                        clean_row[k] = self._parse_json(v)

                try:
                    pid = clean_row.get('canon_project_slug', clean_row.get('project_id'))
                    if not pid:
                        continue

                    p_name = clean_row.get('canon_project_name', clean_row.get('project_name', 'Unknown'))
                    region = clean_row.get('canon_region', clean_row.get('region'))
                    p_type = clean_row.get('canon_project_type', clean_row.get('project_type'))
                    p_status = clean_row.get('canon_project_status', clean_row.get('project_status'))
                    sales_status = clean_row.get('canon_sales_status', clean_row.get('current_sales_status'))

                    # Amenities: JSON + flag enrichment
                    amenities = clean_row.get('key_amenities_json', [])
                    if not isinstance(amenities, list):
                        amenities = []
                    flags = ['golf', 'beach_access', 'lagoons', 'clubhouse', 'pools', 'gym']
                    for flag in flags:
                        val = clean_row.get(f'{flag}_flag')
                        if val and str(val).lower() == 'true':
                            name = flag.replace('_', ' ').replace('flag', '').strip().title()
                            if name not in amenities:
                                amenities.append(name)

                    # Unit types
                    unit_types = clean_row.get('canon_unit_types', [])
                    if not isinstance(unit_types, list):
                        unit_types = self._parse_json(clean_row.get('unit_types_offered_json'))
                    if not isinstance(unit_types, list):
                        unit_types = []

                    # Pricing
                    price_val = clean_row.get('starting_price_value')
                    price_int = None
                    try:
                        if price_val and str(price_val).replace('.', '').replace('0', '') != '':
                            price_int = int(float(price_val))
                    except:
                        pass

                    price_status = clean_row.get('price_status')
                    if price_status:
                        price_status = price_status.lower()

                    # Brochure
                    has_brochure = str(clean_row.get('canon_has_brochure', 'false')).lower() == 'true'

                    proj = Project(
                        project_id=pid,
                        project_name=p_name or 'Unknown',
                        brand_family=clean_row.get('canon_brand_family', clean_row.get('brand_family')),
                        official_project_url=clean_row.get('canon_primary_url', clean_row.get('official_project_url')),
                        region=region,
                        city_area=clean_row.get('canon_city_area', clean_row.get('city_area')),
                        project_type=p_type,
                        project_status=p_status,
                        current_sales_status=sales_status,
                        starting_price_value=price_int,
                        price_status=price_status,
                        key_amenities=amenities,
                        unit_types=unit_types,
                        has_brochure=has_brochure,
                        raw_data=clean_row,
                    )

                    self.projects[pid] = proj
                    self.raw_rows.append(clean_row)

                except Exception as e:
                    logger.warning(f"Failed to parse row {row.get('project_id')}: {e}")

        logger.info(f"KB loaded: {len(self.projects)} projects "
                     f"({len(self.get_selling_projects())} selling)")

    def _clean_val(self, val: Any) -> Optional[str]:
        if val is None:
            return None
        s = str(val).strip()
        if s.lower() in ['unknown', 'null', '', 'none']:
            return None
        return s

    def _parse_json(self, val: Optional[str]) -> Any:
        if not val:
            return []
        try:
            return json.loads(val)
        except:
            return []

    # --- Public API ---

    def get_project(self, project_id: str) -> Optional[Project]:
        return self.projects.get(project_id)

    def get_selling_projects(self) -> List[Project]:
        """Returns only projects with current_sales_status == 'selling'."""
        return [p for p in self.projects.values()
                if p.current_sales_status and p.current_sales_status.lower() == 'selling']

    def get_all_projects(self) -> List[Project]:
        return list(self.projects.values())

    def get_portfolio_by_region(self, selling_only: bool = True) -> Dict[str, List[Project]]:
        """Group projects by region. Selling-only by default."""
        projects = self.get_selling_projects() if selling_only else self.get_all_projects()
        grouped: Dict[str, List[Project]] = {}
        for p in projects:
            region = p.region or "Other"
            if region not in grouped:
                grouped[region] = []
            grouped[region].append(p)
        return grouped

    def get_all_project_names(self) -> List[str]:
        """For intent router fuzzy matching."""
        return [p.project_name for p in self.projects.values()]

    def get_all_project_slugs(self) -> List[str]:
        return list(self.projects.keys())

    def search_projects(self, query: str) -> List[Project]:
        """Basic name substring search (fallback/utility)."""
        q = query.lower()
        return [p for p in self.projects.values()
                if q in p.project_name.lower() or q in p.project_id.lower()]

    def build_project_card(self, project: Project) -> str:
        """Creates the normalized text chunk for embedding. Strict governance."""
        raw = project.raw_data
        lines = [f"Project: {project.project_name}"]

        # Location
        loc_parts = filter(None, [raw.get('region'), raw.get('city_area'), raw.get('micro_location')])
        lines.append(f"Location: {', '.join(loc_parts)}")

        # Status/Type
        stats = filter(None, [raw.get('project_type'), raw.get('project_status'), raw.get('current_sales_status')])
        lines.append(f"Status: {', '.join(stats)}")

        # Pricing — STRICT
        p_status = raw.get('price_status')
        if p_status and p_status.lower() == 'official':
            start_p = raw.get('starting_price_value')
            curr = raw.get('starting_price_currency', 'EGP')
            if start_p:
                lines.append(f"Starting Price: {start_p} {curr}")
            min_p = raw.get('price_range_min')
            max_p = raw.get('price_range_max')
            if min_p and max_p and min_p != start_p:
                lines.append(f"Price Range: {min_p} - {max_p} {curr}")
        elif p_status and p_status.lower() == 'on_request':
            lines.append("Pricing: On Request only")

        # Units
        if project.unit_types:
            lines.append(f"Units: {', '.join(project.unit_types)}")

        # Amenities
        if project.key_amenities:
            lines.append(f"Amenities: {', '.join(project.key_amenities[:8])}")

        # Zones
        zones = raw.get('zones_json', [])
        if zones and isinstance(zones, list):
            z_names = [z.get('zone_name') for z in zones if isinstance(z, dict) and z.get('zone_name')]
            if z_names:
                lines.append(f"Zones: {', '.join(z_names)}")

        return "\n".join(lines)

    def build_evidence_pack(self, project: Project) -> dict:
        """Structured metadata for frontend chips — no free text."""
        return EvidencePack(
            project_id=project.project_id,
            project_name=project.project_name,
            region=project.region,
            city_area=project.city_area,
            url=project.official_project_url,
            has_brochure=project.has_brochure,
            price_status=project.price_status,
            unit_types=project.unit_types[:5],
            amenities_short=project.key_amenities[:4],
            source="kb",
        ).model_dump()

    def format_portfolio_listing(self) -> str:
        """Format the selling portfolio grouped by region for chat display."""
        portfolio = self.get_portfolio_by_region(selling_only=True)
        if not portfolio:
            return "No actively selling projects found."

        lines = ["Here is our current portfolio of available projects:\n"]
        for region, projects in sorted(portfolio.items()):
            lines.append(f"**{region}**")
            for p in projects:
                unit_str = ", ".join(p.unit_types[:3]) if p.unit_types else "various units"
                lines.append(f"- **{p.project_name}** — {unit_str}")
            lines.append("")

        return "\n".join(lines)


kb_service = KBService()
