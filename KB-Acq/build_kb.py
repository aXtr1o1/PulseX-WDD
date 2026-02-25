#!/usr/bin/env python3
"""
PulseX-WDD KB Builder — 28-row buyer KB CSV
"""
import csv, json, os

today = "2026-02-22"
contact = "https://wadidegladevelopments.com/contact-us/"
idx = "https://wadidegladevelopments.com/projects/"

def js(x): return json.dumps(x, ensure_ascii=False)

HEADER = [
  "project_id","project_name","brand_family","official_project_url","inquiry_form_url",
  "official_contact_page_url","region","city_area","micro_location","map_link",
  "project_type","project_status","current_sales_status","developer_inventory_status",
  "unit_types_offered_json","bedrooms_range_min","bedrooms_range_max",
  "bua_range_min_sqm","bua_range_max_sqm","starting_price_value","starting_price_currency",
  "price_range_min","price_range_max","price_status","pricing_date","pricing_disclaimer",
  "payment_plan_headline","downpayment_percent_min","downpayment_percent_max",
  "installment_years_min","installment_years_max","delivery_window",
  "delivery_year_min","delivery_year_max","finishing_levels_offered_json",
  "key_amenities_json","golf_flag","beach_access_flag","lagoons_flag","clubhouse_flag",
  "pools_flag","gym_flag","brochure_urls_json","gallery_urls_json","source_links_json",
  "screenshot_paths_json","last_verified_date","confidence_score","disclaimers_json",
  "zones_json","unit_templates_json","listings_json"
]

def base():
    """Return a blank row with all required keys."""
    return {k: "" for k in HEADER}

def setjson(row, col, val):
    row[col] = js(val)

def finalize(row):
    """Ensure all JSON cols are valid JSON."""
    JSON_COLS = [
        "unit_types_offered_json","finishing_levels_offered_json","key_amenities_json",
        "brochure_urls_json","gallery_urls_json","source_links_json","screenshot_paths_json",
        "disclaimers_json","zones_json","unit_templates_json","listings_json"
    ]
    for col in JSON_COLS:
        if not row.get(col):
            row[col] = "[]"
    return row

rows = []

# ══════════════════════════════════════════════════════════════════════
# 1  MURANO
r = base()
r.update({
    "project_id": "murano", "project_name": "Murano", "brand_family": "Second_Home",
    "official_project_url": "https://wadidegladevelopments.com/project-phases/murano/",
    "inquiry_form_url": contact, "official_contact_page_url": contact,
    "region": "Ain Sokhna", "city_area": "Ain Sokhna Road",
    "micro_location": "750 meters of beach, 50 minutes from Cairo",
    "project_type": "resort", "current_sales_status": "selling",
    "price_status": "on_request",
    "golf_flag": "false", "beach_access_flag": "true", "lagoons_flag": "true",
    "clubhouse_flag": "", "pools_flag": "true", "gym_flag": "",
    "last_verified_date": today, "confidence_score": "0.60",
})
setjson(r, "unit_types_offered_json", ["Villas","Attached Villas","Duplexes","Chalets"])
setjson(r, "finishing_levels_offered_json", [])
setjson(r, "key_amenities_json", ["Swimming Pools","Entertainment Area","Supermarket","Green Areas","Restaurants","750 metres of golden sandy beach"])
setjson(r, "brochure_urls_json", [
    "https://wadidegladevelopments.com/wp-content/uploads/2023/09/Waterside-Brochure.pdf",
    "https://wadidegladevelopments.com/wp-content/uploads/2025/09/WDD-Magazine-25-Digital.pdf"])
setjson(r, "gallery_urls_json", [])
setjson(r, "source_links_json", ["https://wadidegladevelopments.com/project-phases/murano/", idx])
setjson(r, "screenshot_paths_json", [
    "raw/screens/murano_top_1771723938584.png",
    "raw/screens/murano_middle_phases_1771723984094.png"])
setjson(r, "disclaimers_json", [
    "Pricing not published on official site; on request only.",
    "Brochures are image-based PDFs; specs not machine-readable."])
setjson(r, "zones_json", [
    {"name":"Living Community","url":"https://wadidegladevelopments.com/projects/murano/"},
    {"name":"Waterside","url":"https://wadidegladevelopments.com/projects/water-side/"},
    {"name":"Floating Islands","url":"https://wadidegladevelopments.com/projects/floating-islands/"},
    {"name":"Ojo","url":"https://wadidegladevelopments.com/projects/ojo-2/"}])
setjson(r, "unit_templates_json", [])
setjson(r, "listings_json", [])
rows.append(finalize(r))

# ══════════════════════════════════════════════════════════════════════
# 2  CLUBTOWN
r = base()
r.update({
    "project_id": "clubtown", "project_name": "ClubTown", "brand_family": "Residential",
    "official_project_url": "https://wadidegladevelopments.com/project-phases/clubtown/",
    "inquiry_form_url": contact, "official_contact_page_url": contact,
    "region": "Cairo", "city_area": "Maadi", "micro_location": "New Degla",
    "project_type": "residential", "project_status": "under_construction",
    "current_sales_status": "selling", "price_status": "on_request",
    "delivery_year_min": "2022",
    "golf_flag": "false", "beach_access_flag": "false", "lagoons_flag": "false",
    "clubhouse_flag": "true", "pools_flag": "true", "gym_flag": "true",
    "last_verified_date": today, "confidence_score": "0.60",
})
setjson(r, "unit_types_offered_json", ["Apartments","Duplexes"])
setjson(r, "finishing_levels_offered_json", [])
setjson(r, "key_amenities_json", ["Retail","Admin","Sports Courts","Outdoor Fitness Area",
    "Club House","Mosque","Food Court","Banks","Gym","Padel Tennis","Swimming Pools","Nurseries & Kids Gardens"])
setjson(r, "brochure_urls_json", ["https://wadidegladevelopments.com/wp-content/uploads/2025/09/WDD-Magazine-25-Digital.pdf"])
setjson(r, "gallery_urls_json", [
    "https://wadidegladevelopments.com/wp-content/uploads/2023/10/BreezeHorizon-M.-Plan-01-scaled.jpg",
    "https://wadidegladevelopments.com/wp-content/uploads/2023/10/CAM02-Frontyard-2-1-scaled-e1696240092640.jpg"])
setjson(r, "source_links_json", ["https://wadidegladevelopments.com/project-phases/clubtown/", idx])
setjson(r, "screenshot_paths_json", ["raw/screens/clubtown_top.png","raw/screens/clubtown_phases.png"])
setjson(r, "disclaimers_json", [
    "Pricing not published; on request only.",
    "Delivery year 2022 references earlier phases only; newer phases still under construction."])
setjson(r, "zones_json", [
    {"name":"Breeze","url":"https://wadidegladevelopments.com/projects/breeze/"},
    {"name":"Horizon","url":"https://wadidegladevelopments.com/projects/horizon/"},
    {"name":"Edge","url":"https://wadidegladevelopments.com/projects/edge/"}])
setjson(r, "unit_templates_json", [])
setjson(r, "listings_json", [])
rows.append(finalize(r))

# ══════════════════════════════════════════════════════════════════════
# 3  NEO
r = base()
r.update({
    "project_id": "neo", "project_name": "Neo", "brand_family": "Residential",
    "official_project_url": "https://wadidegladevelopments.com/project-phases/neo/",
    "inquiry_form_url": "https://wadidegladevelopments.com/projects/neo-gardens/#wpcf7-f5124-o1",
    "official_contact_page_url": contact,
    "region": "East Cairo", "city_area": "Mostakbal City",
    "micro_location": "Heart of Mostakbal City",
    "project_type": "residential", "project_status": "under_construction",
    "current_sales_status": "selling", "price_status": "on_request",
    "golf_flag": "false", "beach_access_flag": "false", "lagoons_flag": "false",
    "clubhouse_flag": "false", "pools_flag": "false", "gym_flag": "false",
    "last_verified_date": today, "confidence_score": "0.65",
})
setjson(r, "unit_types_offered_json", ["Apartments","Duplexes"])
setjson(r, "finishing_levels_offered_json", [])
setjson(r, "key_amenities_json", ["Green Areas","Parking","International School","Nursery",
    "Clinics","Mosque","Medical Services","Commercial & Entertainment Hub"])
setjson(r, "brochure_urls_json", [
    "https://wadidegladevelopments.com/wp-content/uploads/2023/09/Wadi-Degla-Development-Neopolis-Neo-Gardens.pdf"])
setjson(r, "gallery_urls_json", [
    "https://wadidegladevelopments.com/wp-content/uploads/2023/10/Untitled-2-01.jpg",
    "https://wadidegladevelopments.com/wp-content/uploads/2023/10/Untitled-2-02.jpg"])
setjson(r, "source_links_json", ["https://wadidegladevelopments.com/project-phases/neo/", idx])
setjson(r, "screenshot_paths_json", [
    "raw/screens/neo_hero_section_1771725070544.png",
    "raw/screens/neo_phases_section_1771725087443.png"])
setjson(r, "disclaimers_json", [
    "Pricing not published; on request only.",
    "Brochure Neopolis-Neo-Gardens.pdf is image-based; specs not machine-readable.",
    "Neopolis appears to be the master name for this Mostakbal City cluster."])
setjson(r, "zones_json", [
    {"name":"Neo Lakes","url":"https://wadidegladevelopments.com/projects/neo-lakes/"},
    {"name":"Neo Gardens","url":"https://wadidegladevelopments.com/projects/neo-gardens/"}])
setjson(r, "unit_templates_json", [])
setjson(r, "listings_json", [])
rows.append(finalize(r))

# ══════════════════════════════════════════════════════════════════════
# 4  VERO
r = base()
r.update({
    "project_id": "vero", "project_name": "Vero", "brand_family": "Second_Home",
    "official_project_url": "https://wadidegladevelopments.com/projects/vero/",
    "inquiry_form_url": contact, "official_contact_page_url": contact,
    "region": "North Coast", "city_area": "Sidi Abd El Rahman",
    "micro_location": "Sidi Abd El Rahman, elevated coastal retreat",
    "project_type": "resort", "current_sales_status": "selling",
    "price_status": "on_request",
    "beach_access_flag": "true", "pools_flag": "true", "gym_flag": "true",
    "last_verified_date": today, "confidence_score": "0.60",
})
setjson(r, "unit_types_offered_json", ["Serviced Apartments","Residential Apartments"])
setjson(r, "finishing_levels_offered_json", [])
setjson(r, "key_amenities_json", ["Horizon Pool","24/7 Lounge Reception & Concierge",
    "Housekeeping","Fitness Center","Pool Bar","Swimming Pool","Commercial Outlet","Vero Beach Bar"])
setjson(r, "brochure_urls_json", [
    "https://wadidegladevelopments.com/wp-content/uploads/2025/09/WDD-Magazine-25-Digital.pdf"])
setjson(r, "gallery_urls_json", [
    "https://wadidegladevelopments.com/wp-content/uploads/2026/02/Cam02-Beach-Club-scaled.jpg",
    "https://wadidegladevelopments.com/wp-content/uploads/2026/02/Cam-01.terrace-vero-no-ppl--scaled.jpg",
    "https://wadidegladevelopments.com/wp-content/uploads/2026/02/cam04-pool-scaled.jpg"])
setjson(r, "source_links_json", ["https://wadidegladevelopments.com/projects/vero/", idx])
setjson(r, "screenshot_paths_json", [
    "raw/screens/vero_top_1771726235415.png",
    "raw/screens/vero_mid_1771726253750.png",
    "raw/screens/vero_bottom_1771726273397.png"])
setjson(r, "disclaimers_json", [
    "Pricing not published; on request only.",
    "Project spans 34,000 sqm per page; individual unit BUA not published."])
setjson(r, "zones_json", [])
setjson(r, "unit_templates_json", [])
setjson(r, "listings_json", [])
rows.append(finalize(r))

# ══════════════════════════════════════════════════════════════════════
# 5  PROMENADE NEW CAIRO
r = base()
r.update({
    "project_id": "promenade_new_cairo", "project_name": "Promenade New Cairo",
    "brand_family": "Residential",
    "official_project_url": "https://wadidegladevelopments.com/projects/promnade-new-cairo/",
    "inquiry_form_url": "https://wadidegladevelopments.com/projects/promnade-new-cairo/",
    "official_contact_page_url": contact,
    "region": "East Cairo", "city_area": "New Cairo",
    "micro_location": "5 minutes from AUC and Road 90",
    "project_type": "residential", "current_sales_status": "selling",
    "price_status": "on_request",
    "pools_flag": "true", "gym_flag": "true",
    "last_verified_date": today, "confidence_score": "0.60",
})
setjson(r, "unit_types_offered_json", ["Apartments","Penthouses"])
setjson(r, "finishing_levels_offered_json", [])
setjson(r, "key_amenities_json", ["Walking Track","Gym","Swimming Pools","Secured Parking",
    "The Hub Waterway","Squash Court","Spa","360-degree view"])
setjson(r, "brochure_urls_json", [
    "https://wadidegladevelopments.com/wp-content/uploads/2025/09/WDD-Magazine-25-Digital.pdf"])
setjson(r, "gallery_urls_json", [
    "https://wadidegladevelopments.com/wp-content/uploads/2023/09/WhatsApp-Image-2024-02-28-at-2.49.17-PM-2.jpeg",
    "https://wadidegladevelopments.com/wp-content/uploads/2023/09/WhatsApp-Image-2024-02-28-at-2.49.18-PM.jpeg"])
setjson(r, "source_links_json", ["https://wadidegladevelopments.com/projects/promnade-new-cairo/", idx])
setjson(r, "screenshot_paths_json", [
    "raw/screens/promenade_top_1771726387275.png",
    "raw/screens/promenade_mid_1771726412577.png"])
setjson(r, "disclaimers_json", ["Pricing not published; on request only."])
setjson(r, "zones_json", [])
setjson(r, "unit_templates_json", [])
setjson(r, "listings_json", [])
rows.append(finalize(r))

# ══════════════════════════════════════════════════════════════════════
# SOLD-OUT PROJECTS 6–15
SOLD = [
    # (pid, name, brand, url, region, city, micro, ptype,
    #  units, amenities, beach, lagoons, club, pools, gym,
    #  brochures, confidence, disclaimers, screens)
    ("blumar_el_sokhna","Blumar El Sokhna","Second_Home",
     "https://wadidegladevelopments.com/projects/blumarelsokhna/",
     "Ain Sokhna","Suez Road","","resort",
     [],["Swimming Pools","Green Areas","Restaurants","Supermarket"],
     "true","","","true","false",
     ["https://wadidegladevelopments.com/wp-content/uploads/2025/09/WDD-Magazine-25-Digital.pdf"],
     "0.50",["Sold Out per official projects index."],
     ["raw/screens/index/blumar_el_sokhna_card.png","raw/screens/index/projects_index.png"]),

    ("blumar_hills","Blumar Hills","Second_Home",
     "https://wadidegladevelopments.com/projects/blumar-hills/",
     "Ain Sokhna","Zaafarana Road","","resort",
     ["Chalets"],["Swimming Pools"],
     "true","","","true","false",
     ["https://wadidegladevelopments.com/wp-content/uploads/2025/09/WDD-Magazine-25-Digital.pdf"],
     "0.50",["Sold Out per official projects index."],
     ["raw/screens/index/blumar_hills_card.png","raw/screens/index/projects_index.png"]),

    ("tijan_maadi","Tijan Maadi","Residential",
     "https://wadidegladevelopments.com/projects/tijan-maadi/",
     "Cairo","Maadi","New Degla","residential",
     ["Apartments"],["Green Areas","Secured Parking","Water Feature","Walking Track","Club House","Swimming Pools"],
     "false","false","true","true","false",
     [],"0.50",["Sold Out per official projects index."],
     ["raw/screens/index/tijan_maadi_card.png","raw/screens/index/projects_index.png"]),

    ("blumar_el_dome","Blumar El Dome","Second_Home",
     "https://wadidegladevelopments.com/projects/blumar-el-dome/",
     "Ain Sokhna","Zaafarana Road","","resort",
     ["Chalets"],["Restaurants","Hotel","Swimming Pools"],
     "true","false","false","true","false",
     [],"0.50",["Sold Out per official projects index."],
     ["raw/screens/index/blumar_el_dome_card.png","raw/screens/index/projects_index.png"]),

    ("pyramids_walk","Pyramids Walk","Residential",
     "https://wadidegladevelopments.com/projects/pyramids-walk/",
     "West Cairo","6th of October","","residential",
     ["Twin Houses","Town Houses"],["Swimming Pools","Green Areas","Secured Parking","360-degree view","Gym","Spa"],
     "false","false","false","true","true",
     [],"0.50",["Sold Out per official projects index.","Delivered 2016; 140,000 sqm in 6th of October."],
     ["raw/screens/pyramids_walk_project_1771728438187.png","raw/screens/index/projects_index.png"]),

    ("blumar_sidi_abd_el_rahman","Blumar Sidi Abd El Rahman","Second_Home",
     "https://wadidegladevelopments.com/projects/blumar-sidi-abdel-rahman-2/",
     "North Coast","Sidi Abdel Rahman","","resort",
     ["Chalets","Villas"],["Green Areas","Swimming Pools","Restaurants","Hotel"],
     "true","false","false","true","false",
     [],"0.50",["Sold Out per official projects index.","First North Coast resort; 270,000 sqm; since 2009."],
     ["raw/screens/blumar_sidi_abdel_rahman_1771728548479.png","raw/screens/index/projects_index.png"]),

    ("tijan_zahraa_el_maadi","Tijan Zahraa El Maadi","Residential",
     "https://wadidegladevelopments.com/projects/tijan-zahraa-maadi/",
     "Cairo","Zahraa El Maadi","","residential",
     ["Apartments"],["Green Areas","Secured Parking","Water Feature"],
     "false","false","false","false","false",
     [],"0.50",["Sold Out per official projects index."],
     ["raw/screens/tijan_zahraa_maadi_1771728598658.png","raw/screens/index/projects_index.png"]),

    ("canal_residence","Canal Residence","Residential",
     "https://wadidegladevelopments.com/projects/canal_residence/",
     "Cairo","Maadi","Sarayat el Maadi","residential",
     ["Apartments","Duplexes"],["Secured Parking","Swimming Pool"],
     "false","false","false","true","false",
     [],"0.50",["Sold Out per official projects index."],
     ["raw/screens/canal_residence_1771728668330.png","raw/screens/index/projects_index.png"]),

    ("river_walk","River Walk","Residential",
     "https://wadidegladevelopments.com/projects/river-walk/",
     "East Cairo","New Cairo","","residential",
     ["Villas","Attached Villas"],["Swimming Pools","Green Areas","Secured Parking","Commercial Area","360-degree view","River Walk Mall"],
     "false","false","false","true","false",
     [],"0.50",["Sold Out per official projects index.","Since 2012; 115,000 sqm; 98 families."],
     ["raw/screens/river_walk_1771728741501.png","raw/screens/index/projects_index.png"]),

    ("marina_wadi_degla","Marina Wadi Degla","Second_Home",
     "https://wadidegladevelopments.com/projects/blumar-marina-wadi-degla/",
     "Ain Sokhna","Suez Road","","resort",
     ["Villas","Attached Villas","Chalets"],
     ["Swimming Pools","Green Areas","Restaurants","Entertainment Area","Gym","Bakery","Hotel","360-degree view","Private beaches"],
     "true","false","false","true","true",
     [],"0.50",["Sold Out per official projects index.","Since 2007."],
     ["raw/screens/marina_wadi_degla_project_1771728818699.png","raw/screens/index/projects_index.png"]),
]

for s in SOLD:
    (pid, name, brand, url, region, city, micro, ptype,
     units, amenities, beach, lagoons, club, pools, gym,
     brochures, confidence, disclaimers, screens) = s
    r = base()
    r.update({
        "project_id": pid, "project_name": name, "brand_family": brand,
        "official_project_url": url,
        "inquiry_form_url": contact, "official_contact_page_url": contact,
        "region": region, "city_area": city, "micro_location": micro,
        "project_type": ptype, "project_status": "delivered",
        "current_sales_status": "not_selling", "developer_inventory_status": "sold_out",
        "golf_flag": "false",
        "beach_access_flag": beach, "lagoons_flag": lagoons,
        "clubhouse_flag": club, "pools_flag": pools, "gym_flag": gym,
        "last_verified_date": today, "confidence_score": confidence,
    })
    setjson(r, "unit_types_offered_json", units)
    setjson(r, "finishing_levels_offered_json", [])
    setjson(r, "key_amenities_json", amenities)
    setjson(r, "brochure_urls_json", brochures)
    setjson(r, "gallery_urls_json", [])
    setjson(r, "source_links_json", [url, idx])
    setjson(r, "screenshot_paths_json", screens)
    setjson(r, "disclaimers_json", disclaimers)
    setjson(r, "zones_json", [])
    setjson(r, "unit_templates_json", [])
    setjson(r, "listings_json", [])
    rows.append(finalize(r))

# ══════════════════════════════════════════════════════════════════════
# PHASE ENTITIES 16–25
PHASES = [
    # (pid, name, brand, url, region, city, micro, ptype,
    #  units, amenities, beach, lagoons, club, pools, gym,
    #  brochures, confidence, disclaimers, inquiry, screens, zones, gallery)
    ("living_community","Living Community","Second_Home",
     "https://wadidegladevelopments.com/projects/murano/",
     "Ain Sokhna","El Sokhna","Zaafarana Road","resort",
     ["Villas","Attached Villas","Duplexes","Chalets"],
     ["750-metre beachfront","Private beaches","Six pools","Green Areas","Entertainment Area","Restaurants","Supermarket"],
     "true","false","false","true","false",
     ["https://wadidegladevelopments.com/wp-content/uploads/2023/09/Waterside-Brochure.pdf"],
     "0.65",["Pricing not published; on request only.","Phase of Murano El Sokhna resort.","Brochure is image-based."],
     None,
     ["raw/screens/murano_top_1771729128709.png","raw/screens/murano_bottom_1771729130491.png"],
     [], []),

    ("waterside","Waterside","Second_Home",
     "https://wadidegladevelopments.com/projects/water-side/",
     "Ain Sokhna","Ain Sokhna","Murano","resort",
     ["Villas","Duplexes","Chalets"],
     ["Swimming Pools","Green Areas","Entertainment Area","Restaurants","Supermarket"],
     "true","false","false","true","false",
     ["https://wadidegladevelopments.com/wp-content/uploads/2023/09/Waterside-Brochure.pdf"],
     "0.65",["Pricing not published; on request only.","Phase of Murano; brochure downloaded (9.6MB) image-based."],
     None,
     ["raw/screens/waterside_top_1771728890379.png","raw/screens/waterside_bottom_1771728963344.png"],
     [], []),

    ("floating_islands","Floating Islands","Second_Home",
     "https://wadidegladevelopments.com/projects/floating-islands/",
     "Ain Sokhna","Ain Sokhna","Murano","resort",
     ["Duplexes","Chalets","Villas"],
     ["Entertainment Area","Green Areas","Swimming Pools","Restaurants","Supermarket"],
     "true","false","false","true","false",
     ["https://wadidegladevelopments.com/wp-content/uploads/2024/07/Floating-Islands-Brochure.pdf"],
     "0.65",["Pricing not published; on request only.","Phase of Murano; brochure downloaded (2.5MB) image-based."],
     None,
     ["raw/screens/floating_islands_top_1771729005634.png","raw/screens/floating_islands_bottom_1771729006586.png"],
     [], []),

    ("ojo","Ojo","Second_Home",
     "https://wadidegladevelopments.com/projects/ojo-2/",
     "Ain Sokhna","Ain Sokhna","Murano","resort",
     ["Standalone Villas","Town Houses","Chalets"],
     ["Serene lagoons and edge pools","Beach access","Commercial promenade","Casa Club","The Green Park (6-feddan landscaped sanctuary)"],
     "true","true","true","true","false",
     ["https://wadidegladevelopments.com/wp-content/uploads/2025/12/Ojo-Brochure.pdf"],
     "0.65",["Pricing not published; on request only.","Phase of Murano; brochure downloaded (73MB) image-based."],
     None,
     ["raw/screens/ojo_top_1771729061413.png","raw/screens/ojo_bottom_1771729062550.png"],
     [], []),

    ("neo_lakes","Neo Lakes","Residential",
     "https://wadidegladevelopments.com/projects/neo-lakes/",
     "East Cairo","Mostakbal City","Heart of Mostakbal City","residential",
     ["Apartments","Duplexes"],
     ["International School","Parking","Nursery","Green Areas","Clinics","Commercial and entertainment hub","24/7 security"],
     "false","true","false","false","false",
     ["https://wadidegladevelopments.com/wp-content/uploads/2023/10/Neo-Lakes.pdf"],
     "0.65",["Pricing not published; on request only.","Phase of Neo (Neopolis) Mostakbal City; brochure image-based."],
     None,
     ["raw/screens/neo_lakes_top_1771729210282.png","raw/screens/neo_lakes_bottom_1771729216623.png"],
     [], []),

    ("neo_gardens","Neo Gardens","Residential",
     "https://wadidegladevelopments.com/projects/neo-gardens/",
     "East Cairo","Mostakbal City","Heart of Mostakbal City","residential",
     ["Apartments"],
     ["Commercial Area","Green Areas","Mosque","Nursery","Medical Services","24/7 security","Parking"],
     "false","false","false","false","false",
     ["https://wadidegladevelopments.com/wp-content/uploads/2023/09/Wadi-Degla-Development-Neopolis-Neo-Gardens.pdf"],
     "0.65",["Pricing not published; on request only.","Phase of Neo (Neopolis) Mostakbal City; brochure image-based."],
     "https://wadidegladevelopments.com/projects/neo-gardens/#wpcf7-f5124-o1",
     ["raw/screens/neo_gardens_top_1771729801748.png","raw/screens/neo_gardens_bottom_1771729985232.png"],
     [], []),

    ("breeze","Breeze","Residential",
     "https://wadidegladevelopments.com/projects/breeze/",
     "Cairo","Maadi","New Degla","residential",
     ["Apartments","Duplexes"],
     ["Swimming Pools","Nurseries & Kids Gardens","Retail","Admin","Sports Courts",
      "Outdoor Fitness Area","Club House","Mosque","Food Court","Banks","Gym","Padel Tennis"],
     "false","false","true","true","true",
     ["https://wadidegladevelopments.com/wp-content/uploads/2023/10/CT-Breeze-Brochure.pdf"],
     "0.65",["Pricing not published; on request only.","Phase of ClubTown New Degla."],
     None, ["raw/screens/breeze_page.png","raw/screens/index/breeze_card.png"],
     [], []),

    ("horizon","Horizon","Residential",
     "https://wadidegladevelopments.com/projects/horizon/",
     "Cairo","Maadi","New Degla","residential",
     ["Apartments","Duplexes"],
     ["Swimming Pools","Nurseries & Kids Gardens","Retail","Admin","Sports Courts",
      "Outdoor Fitness Area","Club House","Mosque","Food Court","Banks","Gym","Padel Tennis"],
     "false","false","true","true","true",
     ["https://wadidegladevelopments.com/wp-content/uploads/2023/10/CT-Horizon-Brochure-Wadi-Degla-Developments_.pdf"],
     "0.65",["Pricing not published; on request only.","Phase of ClubTown New Degla."],
     None, ["raw/screens/horizon_page.png","raw/screens/index/horizon_card.png"],
     [], []),

    ("edge","Edge","Residential",
     "https://wadidegladevelopments.com/projects/edge/",
     "Cairo","Maadi","New Degla","residential",
     ["Apartments","Duplexes"],
     ["Swimming Pools","Gym","Mosque","Nurseries & Kids Gardens","Retail","Admin",
      "Sports Courts","Outdoor Fitness Area","Club House","Food Court","Banks","Padel Tennis"],
     "false","false","true","true","true",
     ["https://wadidegladevelopments.com/wp-content/uploads/2024/07/Edge-Brochure-2.pdf"],
     "0.65",["Pricing not published; on request only.","Phase of ClubTown New Degla."],
     None, ["raw/screens/edge_page.png","raw/screens/index/edge_card.png"],
     [], []),

    ("vyon","VYON","Residential",
     "https://wadidegladevelopments.com/projects/vyon/",
     "Cairo","Maadi","New Degla","residential",
     ["Lofts","Penthouses","Apartments","Duplexes"],
     ["Outdoor Dining & BBQ Area","Rooftop Cinema","Rooftop Social Lounges",
      "Co-Working & Meeting Pods","Roof plaza","Infinity-Edge Sky Pool",
      "Children's Play Zone","Outdoor Fitness Area","Outdoor Mini Gym",
      "Playing Yard","Pets' Friendly Zone","Water Feature & Landscape"],
     "false","false","false","true","false",
     ["https://wadidegladevelopments.com/wp-content/uploads/2025/07/VYON-Brochure.pdf"],
     "0.65",["Pricing not published; on request only.","Part of New Degla development cluster."],
     None, ["raw/screens/vyon_top.png","raw/screens/vyon_bottom.png"],
     [], []),
]

for s in PHASES:
    (pid, name, brand, url, region, city, micro, ptype,
     units, amenities, beach, lagoons, club, pools, gym,
     brochures, confidence, disclaimers, inquiry, screens, zones, gallery) = s
    r = base()
    r.update({
        "project_id": pid, "project_name": name, "brand_family": brand,
        "official_project_url": url,
        "inquiry_form_url": inquiry or contact,
        "official_contact_page_url": contact,
        "region": region, "city_area": city, "micro_location": micro,
        "project_type": ptype, "current_sales_status": "selling",
        "price_status": "on_request",
        "golf_flag": "false",
        "beach_access_flag": beach, "lagoons_flag": lagoons,
        "clubhouse_flag": club, "pools_flag": pools, "gym_flag": gym,
        "last_verified_date": today, "confidence_score": confidence,
    })
    setjson(r, "unit_types_offered_json", units)
    setjson(r, "finishing_levels_offered_json", [])
    setjson(r, "key_amenities_json", amenities)
    setjson(r, "brochure_urls_json", brochures)
    setjson(r, "gallery_urls_json", gallery)
    setjson(r, "source_links_json", [url, idx])
    setjson(r, "screenshot_paths_json", screens)
    setjson(r, "disclaimers_json", disclaimers)
    setjson(r, "zones_json", zones)
    setjson(r, "unit_templates_json", [])
    setjson(r, "listings_json", [])
    rows.append(finalize(r))

# ══════════════════════════════════════════════════════════════════════
# 26  NEOPOLIS
r = base()
r.update({
    "project_id": "neopolis", "project_name": "Neopolis", "brand_family": "Residential",
    "official_project_url": "https://wadidegladevelopments.com/projects/neo-gardens/",
    "inquiry_form_url": contact, "official_contact_page_url": contact,
    "region": "East Cairo", "city_area": "Mostakbal City",
    "project_type": "residential",
    "last_verified_date": today, "confidence_score": "0.35",
})
setjson(r, "unit_types_offered_json", [])
setjson(r, "finishing_levels_offered_json", [])
setjson(r, "key_amenities_json", [])
setjson(r, "brochure_urls_json", [
    "https://wadidegladevelopments.com/wp-content/uploads/2023/09/Wadi-Degla-Development-Neopolis-Neo-Gardens.pdf"])
setjson(r, "gallery_urls_json", [])
setjson(r, "source_links_json", [
    "https://wadidegladevelopments.com/projects/neo-gardens/",
    "https://wadidegladevelopments.com/wp-content/uploads/2023/09/Wadi-Degla-Development-Neopolis-Neo-Gardens.pdf"])
setjson(r, "screenshot_paths_json", ["raw/screens/neo_gardens_top_1771729801748.png"])
setjson(r, "disclaimers_json", [
    "Name referenced in official WDD brochure filename (Neopolis-Neo-Gardens.pdf).",
    "URL https://wadidegladevelopments.com/projects/neopolis/ redirects to Neo Gardens.",
    "Treated as alternate/master name for Mostakbal City cluster; no standalone page found in this run."])
setjson(r, "zones_json", [])
setjson(r, "unit_templates_json", [])
setjson(r, "listings_json", [])
rows.append(finalize(r))

# 27  MADA
r = base()
r.update({
    "project_id": "mada", "project_name": "Mada",
    "inquiry_form_url": contact, "official_contact_page_url": contact,
    "last_verified_date": today, "confidence_score": "0.30",
})
setjson(r, "unit_types_offered_json", [])
setjson(r, "finishing_levels_offered_json", [])
setjson(r, "key_amenities_json", [])
setjson(r, "brochure_urls_json", [])
setjson(r, "gallery_urls_json", [])
setjson(r, "source_links_json", ["https://wadidegladevelopments.com/", idx])
setjson(r, "screenshot_paths_json", ["raw/screens/index/projects_full_page_1771723527631.png"])
setjson(r, "disclaimers_json", [
    "Name referenced in official WDD form/PDF; no dedicated page discovered.",
    "https://wadidegladevelopments.com/projects/mada/ returns 404.",
    "Not found on projects index in this run."])
setjson(r, "zones_json", [])
setjson(r, "unit_templates_json", [])
setjson(r, "listings_json", [])
rows.append(finalize(r))

# 28  CAMUSE
r = base()
r.update({
    "project_id": "camuse", "project_name": "CAMUSE",
    "inquiry_form_url": contact, "official_contact_page_url": contact,
    "last_verified_date": today, "confidence_score": "0.30",
})
setjson(r, "unit_types_offered_json", [])
setjson(r, "finishing_levels_offered_json", [])
setjson(r, "key_amenities_json", [])
setjson(r, "brochure_urls_json", [])
setjson(r, "gallery_urls_json", [])
setjson(r, "source_links_json", ["https://wadidegladevelopments.com/", idx])
setjson(r, "screenshot_paths_json", ["raw/screens/index/projects_full_page_1771723527631.png"])
setjson(r, "disclaimers_json", [
    "Name referenced in official WDD form/PDF; no dedicated page discovered.",
    "https://wadidegladevelopments.com/projects/camuse/ returns 404.",
    "Not found on projects index or site search in this run."])
setjson(r, "zones_json", [])
setjson(r, "unit_templates_json", [])
setjson(r, "listings_json", [])
rows.append(finalize(r))

# ══════════════════════════════════════════════════════════════════════
# VALIDATION
assert len(rows) == 28, f"Expected 28 rows, got {len(rows)}"
ids = [r["project_id"] for r in rows]
assert len(set(ids)) == 28, f"Duplicate IDs found"
JSON_COLS = [
    "unit_types_offered_json","finishing_levels_offered_json","key_amenities_json",
    "brochure_urls_json","gallery_urls_json","source_links_json","screenshot_paths_json",
    "disclaimers_json","zones_json","unit_templates_json","listings_json"
]
for row in rows:
    for col in JSON_COLS:
        v = row.get(col, "")
        assert v, f"Empty JSON col {col} in {row['project_id']}"
        json.loads(v)  # must parse
    sl = json.loads(row["source_links_json"])
    assert sl, f"Empty source_links for {row['project_id']}"

# WRITE
out_paths = [
    "/Volumes/ReserveDisk/codeBase/PulseX-WDD/engine-KB/PulseX-WDD_buyerKB.csv",
    "/Volumes/ReserveDisk/codeBase/PulseX-WDD/KB-Acq/outputs/PulseX-WDD_buyerKB.csv",
]
for p in out_paths:
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=HEADER)
        w.writeheader()
        w.writerows(rows)

print("✓ VALIDATION PASSED")
print(f"  Rows: {len(rows)}")
print(f"  Unique IDs: {len(set(ids))}")
print(f"  JSON cols validated: {len(JSON_COLS)}")
print(f"  Written → {out_paths[0]}")
print(f"  Written → {out_paths[1]}")
