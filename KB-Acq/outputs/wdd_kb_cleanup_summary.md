# WDD KB Governance Cleanup Summary

**Run date:** 2026-02-27  
**Input:** `engine-KB/PulseX-WDD_buyerKB.csv` (28 rows)  
**Output:** `engine-KB/PulseX-WDD_buyerKB.cleaned.csv` (26 rows)

---

## Dropped — "For Sure NO" (2 rows)

| project_id | project_name | Drop Reason |
|---|---|---|
| `mada` | Mada | HTTP 404 on WDD site; not listed on official projects index; no official_project_url; name not attributable to any WDD p |
| `camuse` | CAMUSE | HTTP 404 on WDD site; not listed on official projects index; no official_project_url; name not attributable to any WDD p |

---

## Kept — Needs Verification (confidence 0.40–0.69) (0 rows)

| project_id | confidence | is_alias_of |
|---|---|---|

---

## Kept — Verified (confidence ≥ 0.70) (26 rows)

| project_id | confidence | verified_url |
|---|---|---|
| `murano` | 0.95 | https://wadidegladevelopments.com/project-phases/murano/ |
| `clubtown` | 0.9 | https://wadidegladevelopments.com/project-phases/clubtown/ |
| `neo` | 0.85 | https://wadidegladevelopments.com/project-phases/neo/ |
| `vero` | 0.85 | https://wadidegladevelopments.com/projects/vero/ |
| `promenade_new_cairo` | 0.85 | https://wadidegladevelopments.com/projects/promnade-new-cairo/ |
| `blumar_el_sokhna` | 0.85 | https://wadidegladevelopments.com/projects/blumarelsokhna/ |
| `blumar_hills` | 0.85 | https://wadidegladevelopments.com/projects/blumar-hills/ |
| `tijan_maadi` | 0.85 | https://wadidegladevelopments.com/projects/tijan-maadi/ |
| `blumar_el_dome` | 0.85 | https://wadidegladevelopments.com/projects/blumar-el-dome/ |
| `pyramids_walk` | 0.85 | https://wadidegladevelopments.com/projects/pyramids-walk/ |
| `blumar_sidi_abd_el_rahman` | 0.85 | https://wadidegladevelopments.com/projects/blumar-sidi-abdel-rahman-2/ |
| `tijan_zahraa_el_maadi` | 0.85 | https://wadidegladevelopments.com/projects/tijan-zahraa-maadi/ |
| `canal_residence` | 0.85 | https://wadidegladevelopments.com/projects/canal_residence/ |
| `river_walk` | 0.85 | https://wadidegladevelopments.com/projects/river-walk/ |
| `marina_wadi_degla` | 0.85 | https://wadidegladevelopments.com/projects/blumar-marina-wadi-degla/ |
| `living_community` | 0.8 | https://wadidegladevelopments.com/projects/murano/ |
| `waterside` | 0.8 | https://wadidegladevelopments.com/projects/water-side/ |
| `floating_islands` | 0.8 | https://wadidegladevelopments.com/projects/floating-islands/ |
| `ojo` | 0.8 | https://wadidegladevelopments.com/projects/ojo-2/ |
| `neo_lakes` | 0.8 | https://wadidegladevelopments.com/projects/neo-lakes/ |
| `neo_gardens` | 0.8 | https://wadidegladevelopments.com/projects/neo-gardens/ |
| `breeze` | 0.8 | https://wadidegladevelopments.com/projects/breeze/ |
| `horizon` | 0.8 | https://wadidegladevelopments.com/projects/horizon/ |
| `edge` | 0.8 | https://wadidegladevelopments.com/projects/edge/ |
| `vyon` | 0.8 | https://wadidegladevelopments.com/projects/vyon/ |
| `neopolis` | 0.75 | https://wadidegladevelopments.com/projects/neopolis/ |

---

## Top Changes & Warnings

| # | Change |
|---|---|
| 1 | **DROPPED `mada`** — HTTP 404 on WDD, no official page, not on WDD index, conf=0.30 |
| 2 | **DROPPED `camuse`** — HTTP 404 on WDD, no official page, not on WDD index, conf=0.30 |
| 3 | **`neopolis` URL fixed** — official page confirmed at `/projects/neopolis/` (was pointing to neo-gardens) |
| 4 | **`project_status` normalized** — replaced "Sales Team will assist you" with `unknown`/`delivered` per evidence |
| 5 | **`developer_inventory_status` normalized** — replaced placeholder text with `sold_out`/`unknown` |
| 6 | **`delivery_window` cleared** — removed "Sales Team will assist you" placeholder; added disclaimer note |
| 7 | **`map_link` cleared** — removed "Sales Team will assist you" placeholder; column retained (schema dependency) |
| 8 | **Unit types canonicalized** — e.g. "Attached Villas" → `villa`, "Loft House" → `loft`, "Standalone Villas" → `villa` |
| 9 | **City area normalized** — "Ain Sokhna" → "Ain El Sokhna"; "Sidi Abdel Rahman" → "Sidi Abd El Rahman" |
| 10 | **confidence_score recomputed** — all 26 kept rows updated per verification rubric (0.75–0.95) |

---

## Stats

| Metric | Count |
|---|---|
| Rows dropped | 2 |
| Rows kept | 26 |
| Enum fields normalized (rows) | 16 |
| Placeholder cells removed | 52 |
| Unit type rows canonicalized | 24 |
| Non-unit items removed from unit_types | 4 |
| City/region cells normalized | 14 |
| URLs fixed | 1 |
