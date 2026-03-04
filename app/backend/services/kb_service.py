import csv
import json
import logging
import os
from typing import List, Dict, Any, Optional
from app.backend.config import Config
from app.backend.models import Project

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

        with open(Config.KB_CSV_PATH, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Clean row
                clean_row = {k: self._clean_val(v) for k, v in row.items()}
                
                # Parse JSON fields
                for k, v in clean_row.items():
                    if k.endswith('_json'):
                        clean_row[k] = self._parse_json(v)

                # Create Project object
                try:
                    pid = clean_row.get('project_id')
                    if not pid: continue
                    
                    # Manual mapping for key amenities from json + flags
                    amenities = clean_row.get('key_amenities_json', [])
                    if isinstance(amenities, list):
                        amenities = [a for a in amenities if isinstance(a, str)]
                    else:
                        amenities = []
                        
                    # Add flag-based amenities
                    flags = ['golf', 'beach_access', 'lagoons', 'clubhouse', 'pools', 'gym']
                    for flag in flags:
                        val = clean_row.get(f'{flag}_flag')
                        if val and str(val).lower() == 'true':
                            # capitalize nicely
                            name = flag.replace('_', ' ').replace('flag', '').strip().title()
                            if name not in amenities:
                                amenities.append(name)

                    # Pricing integer conversion
                    price_val = clean_row.get('starting_price_value')
                    price_int = None
                    try:
                        if price_val and str(price_val).isdigit():
                            price_int = int(price_val)
                    except: pass

                    # Normalizing status for safer checks
                    p_status = clean_row.get('price_status')
                    if p_status: p_status = p_status.lower()

                    proj = Project(
                        project_id=pid,
                        project_name=clean_row.get('project_name', 'Unknown'),
                        brand_family=clean_row.get('brand_family'),
                        official_project_url=clean_row.get('official_project_url'),
                        region=clean_row.get('region'),
                        city_area=clean_row.get('city_area'),
                        project_type=clean_row.get('project_type'),
                        project_status=clean_row.get('project_status'),
                        starting_price_value=price_int,
                        price_status=clean_row.get('price_status'),
                        key_amenities=amenities,
                        raw_data=clean_row
                    )
                    
                    self.projects[pid] = proj
                    self.raw_rows.append(clean_row)
                    
                except Exception as e:
                    logger.warning(f"Failed to parse row {row.get('project_id')}: {e}")

    def _clean_val(self, val: Any) -> Optional[str]:
        if val is None: return None
        s = str(val).strip()
        if s.lower() in ['unknown', 'null', '', 'none']:
            return None
        return s

    def _parse_json(self, val: Optional[str]) -> Any:
        if not val: return []
        try:
            return json.loads(val)
        except:
            return []

    def get_project(self, project_id: str) -> Optional[Project]:
        return self.projects.get(project_id)

    def search_projects(self, query: str) -> List[Project]:
        # Basic name substring search (fallback/utility)
        q = query.lower()
        results = []
        for p in self.projects.values():
            if q in p.project_name.lower() or q in p.project_id.lower():
                results.append(p)
        return results

    def build_project_card(self, project: Project) -> str:
        """
        Creates the normalized text chunk for embedding.
        Strict governance: only verified fields.
        """
        raw = project.raw_data
        
        lines = [f"Project: {project.project_name}"]
        
        # Location
        loc_parts = filter(None, [raw.get('region'), raw.get('city_area'), raw.get('micro_location')])
        lines.append(f"Location: {', '.join(loc_parts)}")
        
        # Status/Type
        stats = filter(None, [raw.get('project_type'), raw.get('project_status'), raw.get('current_sales_status')])
        lines.append(f"Status: {', '.join(stats)}")
        
        # Pricing - STRICT RULE
        p_status = raw.get('price_status')
        if p_status and p_status.lower() == 'official':
            start_p = raw.get('starting_price_value')
            curr = raw.get('starting_price_currency', 'EGP')
            if start_p:
                lines.append(f"Starting Price: {start_p} {curr}")
            
            # Ranges
            min_p = raw.get('price_range_min')
            max_p = raw.get('price_range_max')
            if min_p and max_p and min_p != start_p:
                lines.append(f"Price Range: {min_p} - {max_p} {curr}")
        elif p_status and p_status.lower() == 'on_request':
            lines.append("Pricing: On Request only")
        
        # Units
        units = raw.get('unit_types_offered_json', [])
        if units:
            lines.append(f"Units: {', '.join(units)}")
            
        # Amenities
        if project.key_amenities:
            lines.append(f"Amenities: {', '.join(project.key_amenities)}")
            
        # Zones
        zones = raw.get('zones_json', [])
        if zones:
            z_names = [z.get('zone_name') for z in zones if z.get('zone_name')]
            if z_names:
                lines.append(f"Zones: {', '.join(z_names)}")
                
        return "\n".join(lines)

kb_service = KBService()
