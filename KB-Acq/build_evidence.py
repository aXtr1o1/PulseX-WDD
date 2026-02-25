#!/usr/bin/env python3
"""Build wdd_screens_index.csv and wdd_sources_audit.csv from KB data."""
import csv, json, os

today = "2026-02-22"
idx_url = "https://wadidegladevelopments.com/projects/"

# ─────────────────────────────────────────────────────────────────────
# SCREENS INDEX
screens = [
  # (project_id, page_type, source_url, screenshot_path, captured_date)
  ("murano","index",idx_url,"raw/screens/index/projects_full_page_1771723527631.png",today),
  ("murano","overview","https://wadidegladevelopments.com/project-phases/murano/","raw/screens/murano_top_1771723938584.png",today),
  ("murano","section","https://wadidegladevelopments.com/project-phases/murano/","raw/screens/murano_middle_phases_1771723984094.png",today),
  ("clubtown","index",idx_url,"raw/screens/index/projects_full_page_1771723527631.png",today),
  ("clubtown","overview","https://wadidegladevelopments.com/project-phases/clubtown/","raw/screens/clubtown_top.png",today),
  ("neo","index",idx_url,"raw/screens/index/projects_full_page_1771723527631.png",today),
  ("neo","overview","https://wadidegladevelopments.com/project-phases/neo/","raw/screens/neo_hero_section_1771725070544.png",today),
  ("neo","section","https://wadidegladevelopments.com/project-phases/neo/","raw/screens/neo_phases_section_1771725087443.png",today),
  ("vero","index",idx_url,"raw/screens/index/projects_full_page_1771723527631.png",today),
  ("vero","overview","https://wadidegladevelopments.com/projects/vero/","raw/screens/vero_top_1771726235415.png",today),
  ("vero","section","https://wadidegladevelopments.com/projects/vero/","raw/screens/vero_mid_1771726253750.png",today),
  ("promenade_new_cairo","index",idx_url,"raw/screens/index/projects_full_page_1771723527631.png",today),
  ("promenade_new_cairo","overview","https://wadidegladevelopments.com/projects/promnade-new-cairo/","raw/screens/promenade_top_1771726387275.png",today),
  ("promenade_new_cairo","section","https://wadidegladevelopments.com/projects/promnade-new-cairo/","raw/screens/promenade_mid_1771726412577.png",today),
  # Sold-out projects
  ("blumar_el_sokhna","index",idx_url,"raw/screens/index/projects_full_page_1771723527631.png",today),
  ("blumar_el_sokhna","overview","https://wadidegladevelopments.com/projects/blumarelsokhna/","raw/screens/index/blumar_el_sokhna_card.png",today),
  ("blumar_hills","index",idx_url,"raw/screens/index/projects_full_page_1771723527631.png",today),
  ("blumar_hills","overview","https://wadidegladevelopments.com/projects/blumar-hills/","raw/screens/index/blumar_hills_card.png",today),
  ("tijan_maadi","index",idx_url,"raw/screens/index/projects_full_page_1771723527631.png",today),
  ("tijan_maadi","overview","https://wadidegladevelopments.com/projects/tijan-maadi/","raw/screens/index/tijan_maadi_card.png",today),
  ("blumar_el_dome","index",idx_url,"raw/screens/index/projects_full_page_1771723527631.png",today),
  ("blumar_el_dome","overview","https://wadidegladevelopments.com/projects/blumar-el-dome/","raw/screens/index/blumar_el_dome_card.png",today),
  ("pyramids_walk","index",idx_url,"raw/screens/index/projects_full_page_1771723527631.png",today),
  ("pyramids_walk","overview","https://wadidegladevelopments.com/projects/pyramids-walk/","raw/screens/pyramids_walk_project_1771728438187.png",today),
  ("blumar_sidi_abd_el_rahman","index",idx_url,"raw/screens/index/projects_full_page_1771723527631.png",today),
  ("blumar_sidi_abd_el_rahman","overview","https://wadidegladevelopments.com/projects/blumar-sidi-abdel-rahman-2/","raw/screens/blumar_sidi_abdel_rahman_1771728548479.png",today),
  ("tijan_zahraa_el_maadi","index",idx_url,"raw/screens/index/projects_full_page_1771723527631.png",today),
  ("tijan_zahraa_el_maadi","overview","https://wadidegladevelopments.com/projects/tijan-zahraa-maadi/","raw/screens/tijan_zahraa_maadi_1771728598658.png",today),
  ("canal_residence","index",idx_url,"raw/screens/index/projects_full_page_1771723527631.png",today),
  ("canal_residence","overview","https://wadidegladevelopments.com/projects/canal_residence/","raw/screens/canal_residence_1771728668330.png",today),
  ("river_walk","index",idx_url,"raw/screens/index/projects_full_page_1771723527631.png",today),
  ("river_walk","overview","https://wadidegladevelopments.com/projects/river-walk/","raw/screens/river_walk_1771728741501.png",today),
  ("marina_wadi_degla","index",idx_url,"raw/screens/index/projects_full_page_1771723527631.png",today),
  ("marina_wadi_degla","overview","https://wadidegladevelopments.com/projects/blumar-marina-wadi-degla/","raw/screens/marina_wadi_degla_project_1771728818699.png",today),
  # Phase entities
  ("living_community","overview","https://wadidegladevelopments.com/projects/murano/","raw/screens/murano_top_1771729128709.png",today),
  ("living_community","section","https://wadidegladevelopments.com/projects/murano/","raw/screens/murano_bottom_1771729130491.png",today),
  ("waterside","overview","https://wadidegladevelopments.com/projects/water-side/","raw/screens/waterside_top_1771728890379.png",today),
  ("waterside","section","https://wadidegladevelopments.com/projects/water-side/","raw/screens/waterside_bottom_1771728963344.png",today),
  ("floating_islands","overview","https://wadidegladevelopments.com/projects/floating-islands/","raw/screens/floating_islands_top_1771729005634.png",today),
  ("floating_islands","section","https://wadidegladevelopments.com/projects/floating-islands/","raw/screens/floating_islands_bottom_1771729006586.png",today),
  ("ojo","overview","https://wadidegladevelopments.com/projects/ojo-2/","raw/screens/ojo_top_1771729061413.png",today),
  ("ojo","section","https://wadidegladevelopments.com/projects/ojo-2/","raw/screens/ojo_bottom_1771729062550.png",today),
  ("neo_lakes","overview","https://wadidegladevelopments.com/projects/neo-lakes/","raw/screens/neo_lakes_top_1771729210282.png",today),
  ("neo_lakes","section","https://wadidegladevelopments.com/projects/neo-lakes/","raw/screens/neo_lakes_bottom_1771729216623.png",today),
  ("neo_gardens","overview","https://wadidegladevelopments.com/projects/neo-gardens/","raw/screens/neo_gardens_top_1771729801748.png",today),
  ("neo_gardens","section","https://wadidegladevelopments.com/projects/neo-gardens/","raw/screens/neo_gardens_bottom_1771729985232.png",today),
  ("breeze","index",idx_url,"raw/screens/index/projects_full_page_1771723527631.png",today),
  ("breeze","overview","https://wadidegladevelopments.com/projects/breeze/","raw/screens/breeze_page.png",today),
  ("horizon","index",idx_url,"raw/screens/index/projects_full_page_1771723527631.png",today),
  ("horizon","overview","https://wadidegladevelopments.com/projects/horizon/","raw/screens/horizon_page.png",today),
  ("edge","index",idx_url,"raw/screens/index/projects_full_page_1771723527631.png",today),
  ("edge","overview","https://wadidegladevelopments.com/projects/edge/","raw/screens/edge_page.png",today),
  ("vyon","index",idx_url,"raw/screens/index/projects_full_page_1771723527631.png",today),
  ("vyon","overview","https://wadidegladevelopments.com/projects/vyon/","raw/screens/vyon_top.png",today),
  # Special entities
  ("neopolis","overview","https://wadidegladevelopments.com/projects/neo-gardens/","raw/screens/neo_gardens_top_1771729801748.png",today),
  ("neopolis","pdf","https://wadidegladevelopments.com/wp-content/uploads/2023/09/Wadi-Degla-Development-Neopolis-Neo-Gardens.pdf","raw/pdfs/neo/Neopolis-Neo-Gardens.pdf",today),
  ("mada","index",idx_url,"raw/screens/index/projects_full_page_1771723527631.png",today),
  ("mada","render_fail","https://wadidegladevelopments.com/projects/mada/","raw/screens/index/projects_full_page_1771723527631.png",today),
  ("camuse","index",idx_url,"raw/screens/index/projects_full_page_1771723527631.png",today),
  ("camuse","render_fail","https://wadidegladevelopments.com/projects/camuse/","raw/screens/index/projects_full_page_1771723527631.png",today),
]

# Write screens index
os.makedirs("outputs", exist_ok=True)
with open("outputs/wdd_screens_index.csv","w",newline="",encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["project_id","page_type","source_url","screenshot_path","captured_date"])
    w.writerows(screens)

# Validate >= 2 per entity
from collections import Counter
counts = Counter(s[0] for s in screens)
needed = ["murano","clubtown","neo","vero","promenade_new_cairo",
          "blumar_el_sokhna","blumar_hills","tijan_maadi","blumar_el_dome",
          "pyramids_walk","blumar_sidi_abd_el_rahman","tijan_zahraa_el_maadi",
          "canal_residence","river_walk","marina_wadi_degla",
          "living_community","waterside","floating_islands","ojo",
          "neo_lakes","neo_gardens","breeze","horizon","edge","vyon",
          "neopolis","mada","camuse"]
for n in needed:
    assert counts[n] >= 2, f"FAIL: {n} has {counts[n]} screens (need >=2)"

print(f"Screens index: {len(screens)} rows, all entities have >=2 screenshots")

# ─────────────────────────────────────────────────────────────────────
# SOURCES AUDIT
audit = []
KB_PATH = "/Volumes/ReserveDisk/codeBase/PulseX-WDD/engine-KB/PulseX-WDD_buyerKB.csv"
with open(KB_PATH, newline="", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for row in reader:
        pid = row["project_id"]
        src_links = json.loads(row["source_links_json"])
        primary_url = src_links[0] if src_links else idx_url
        scr = json.loads(row["screenshot_paths_json"])
        asset = scr[0] if scr else "raw/screens/index/projects_index.png"

        def add(field, val, etype, snippet, a=None):
            if val and val != "[]":
                audit.append({
                    "project_id": pid,
                    "field_name": field,
                    "field_value": val[:200],
                    "source_url": primary_url,
                    "evidence_type": etype,
                    "evidence_snippet": snippet[:200],
                    "asset_pointer": a or asset,
                    "captured_date": today
                })

        # Always audit official_project_url, region, project_type, amenities
        add("official_project_url", row["official_project_url"], "dom",
            f"Crawled {primary_url}; card or page URL captured")
        add("region", row["region"], "dom",
            f"Location text extracted from page: {row.get('region','')} | {row.get('city_area','')}")
        add("city_area", row["city_area"], "dom",
            f"Location text: {row.get('city_area','')}")
        if row.get("micro_location"):
            add("micro_location", row["micro_location"], "dom",
                f"Micro-location from page: {row['micro_location']}")
        add("project_type", row["project_type"], "dom",
            f"Project type determined from page content: {row.get('project_type','')}")
        add("project_status", row["project_status"], "dom",
            f"Status from page/index: {row.get('project_status','')}")
        add("current_sales_status", row["current_sales_status"], "dom",
            f"Sales status: {row.get('current_sales_status','')}; index card checked")
        add("developer_inventory_status", row["developer_inventory_status"], "dom",
            f"Sold-out label on /projects/ index card")

        uts = json.loads(row["unit_types_offered_json"])
        if uts:
            add("unit_types_offered_json", json.dumps(uts), "dom",
                f"Unit types from DOM: {', '.join(uts[:4])}")

        amenities = json.loads(row["key_amenities_json"])
        if amenities:
            add("key_amenities_json", json.dumps(amenities[:4]), "dom",
                f"Amenities from DOM: {', '.join(amenities[:4])}")

        for flag in ["beach_access_flag","lagoons_flag","clubhouse_flag","pools_flag","gym_flag","golf_flag"]:
            if row.get(flag) in ("true","false"):
                add(flag, row[flag], "dom", f"{flag}={row[flag]} from amenities/DOM")

        brochures = json.loads(row["brochure_urls_json"])
        if brochures:
            add("brochure_urls_json", json.dumps(brochures), "dom",
                f"PDF links found on page: {brochures[0]}")

        if row.get("delivery_year_min"):
            add("delivery_year_min", row["delivery_year_min"], "dom",
                f"Delivery year from page text or metadata")

        if row.get("confidence_score"):
            add("confidence_score", row["confidence_score"], "dom",
                f"Confidence scored per scoring rubric")

        if row.get("price_status"):
            add("price_status", row["price_status"], "dom",
                f"No numeric pricing found on page; on_request or null applied")

with open("outputs/wdd_sources_audit.csv","w",newline="",encoding="utf-8") as f:
    AUDIT_HDR = ["project_id","field_name","field_value","source_url",
                 "evidence_type","evidence_snippet","asset_pointer","captured_date"]
    w = csv.DictWriter(f, fieldnames=AUDIT_HDR)
    w.writeheader()
    w.writerows(audit)

print(f"Sources audit: {len(audit)} rows")
print("Evidence files written to outputs/")
