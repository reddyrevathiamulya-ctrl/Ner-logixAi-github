# NER-LogixAI — 5-Minute Internal Hackathon Demo Script

Total time: 5:00. Every number shown comes from a live API or a real dataset —
if a judge asks "where is this from?", each slide has the answer prepped below.

---

## 0:00 – Opening (30 sec) — the problem, one sentence

> "North East India's logistics break down when landslides and floods cut the
> roads. This platform tells you — before you dispatch a truck — which routes
> are risky, why they're risky, and what the river and rain are doing right now."

**On screen:** the dashboard with the red "Active high-severity alert" pill.
That pill is driven by real field reports in the system.

---

## 0:30 – Location check (90 sec) — the money feature

1. In **CHECK A LOCATION**, type `Mangan` → click **Assess location risk**.
2. Watch the map pin land on **Mangan town** (not the district centroid).
3. Read the verdict banner: **"Moderate risk · 45.6 / 100"**.
4. Point at the two live numbers:

> "This landslide score is High because of real terrain + live rainfall
> (9.6 mm in the last 24 hours). This flood line is the river itself: the
> Teesta is flowing at **718.5 m³/s right now**, against its own 90-day
> normal of 711.9 — that's GloFAS satellite river data. Nothing here is
> made up."

5. Optionally click `हिं` / `অস` (top-right) to show multilingual support.

**If asked "is this real?":** re-click the button — the numbers refresh from
the live APIs (Open-Meteo + GloFAS). Say: *"Every number on this card either
comes from a live API I can re-run right now, or a documented historical
record — the 1983 Mangan flash flood that marooned this town is in our
flood inventory."*

---

## 2:00 – Route analysis (90 sec) — mission-aware routing

1. In **ANALYZE A DELIVERY ROUTE**: From `Shillong` → To `Guwahati`.
2. Set Cargo type = **Medicines**, Priority = **Emergency response**.
3. Click **Analyze route**.
4. Read the verdict: **"No verified closure found"** + the stats
   (distance, travel time, danger segments).

> "The route engine checked 24 real road segments from OSRM. For emergency
> medicines it weights safety at 85% and speed at 15% — so it would pick a
> longer but safer corridor if the highway were at risk. Notice it says
> 'no **verified** closure' — we never claim a road is safe; we claim no
> confirmed blockage exists in the data."

**If asked about alternates:** the API returns `alternative_routes` with
per-route risk; mention the engine explains its choice ("lowest combined
route-risk + travel-time score").

---

## 3:30 – Live operations + district watch (45 sec)

1. Scroll to **LIVE OPERATIONS** — the 6 active alerts (Blocked Road NH-6,
   Bridge Damage Imphal, Flooding Agartala, landslides on Aizawl-Silchar and
   Shillong-Guwahati). Note the source-freshness line: *weather: fresh ·
   rainfall: fresh · flood: historical · landslide: historical*.

> "This line is our honesty policy. Weather and rainfall are live. Flood and
   landslide inventories are historical evidence — we never dress history up
   as a current closure."

2. **DISTRICT WATCH** — Assam shows "Very High · accessibility 20".

---

## 4:15 – Satellite + GPS tracking (30 sec) — supporting detail

1. Open the map **Layers** control (top-right) → enable **MODIS flood product**
   (labeled with its real acquisition date).

> "Satellite layers are visual screening from NASA GIBS — a helper, not the
   prediction engine. The risk engine runs on the hazard database, live
   rainfall, and river discharge."

2. Mention GPS tracking exists: `POST /vehicles/{id}/location`, live
   positions in GeoJSON (`/vehicles.geojson`).

---

## 4:45 – Close (15 sec)

> "One platform: live river + rainfall data, evidence-based risk scoring on
> every district, mission-aware route advice, field reporting with offline
> sync, and honest labels on every number. Thank you."

---

## Judge Q&A cheat sheet

| Question | Answer |
| --- | --- |
| Where does the data come from? | Open-Meteo (weather/rain, live), GloFAS (river discharge, live), OSRM/OpenStreetMap (roads), NASA GIBS (satellite), India Flood Inventory + NASA Landslide Catalog (history), field reports (first-party). Full table in README + `docs/DATA_SOURCES.md`. |
| Is the landslide score real? | Real records where they exist + live rainfall × terrain model, **explicitly labeled** "estimate, not a recorded event" when it's the model. |
| Why is Assam "Very High"? | 986 historical flood/landslide records in the inventory anchor there — real IMD data. |
| Can the demo break? | No external call is required for the page to load; if a live API hiccups the app shows a graceful fallback, never a crash. |
| What's NOT real? | Nothing is fabricated. Satellite is optical (cloud-limited), history ≠ current closure, and field reports are "verified/unverified" — we say so in the UI. |

## Key places to demo (all verified working)

Mangan (Sikkim) · Guwahati (Assam) · Imphal (Manipur) · Aizawl (Mizoram) ·
Kohima (Nagaland) · Itanagar (Arunachal) · Agartala (Tripura) · Shillong
(Meghalaya) · plus all 124 district HQs (e.g. "Anjaw" → Hawai, "Mon").