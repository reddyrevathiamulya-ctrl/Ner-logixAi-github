# NER-LogixAI — Data Sources, References & Licensing

Every integration below is **real and tested** (verified with live API calls
on the demo day build). For each source: what it feeds, where it comes from,
how often it updates, and its license.

---

## Live APIs (called at runtime)

### 1. Open-Meteo — Weather, 24-hour rainfall, elevation
- **Feeds:** live weather block, rainfall-triggered landslide model, flood
  rainfall component, weather safety score, route weather.
- **Endpoint used:** `https://api.open-meteo.com/v1/forecast` (current +
  `past_days=1` precipitation), `https://api.open-meteo.com/v1/elevation`.
- **Update frequency:** forecast model, refreshed continuously (~15 min–1 h).
- **License:** free for non-commercial use — https://open-meteo.com/en/terms
- **Verified:** HTTP 200; Mangan 27.8 °C, 24 h rainfall, 792 m elevation.

### 2. Open-Meteo Flood API (GloFAS river discharge)
- **Feeds:** live river-flood signal — today's discharge vs the river's own
  p90/p98 from the last 120 days; shown on the location result card.
- **Endpoint used:** `https://flood-api.open-meteo.com/v1/flood`
  (daily `river_discharge`, `past_days=120`).
- **Underlying data:** GloFAS — Copernicus Emergency Management Service
  global flood awareness model (ECMWF).
- **Update frequency:** daily.
- **License:** free/open under CEMS data policy; Open-Meteo terms apply to
  the API access layer.
- **Verified:** HTTP 200 with 125 days of history at Mangan (Teesta),
  Guwahati, Dibrugarh.

### 3. OSRM — Real road routing
- **Feeds:** route geometry, distance, duration; every analyzed segment.
- **Endpoint used:** `https://router.project-osrm.org/route/v1/driving/...`
- **Underlying data:** OpenStreetMap road graph (public OSRM server).
- **Update frequency:** road-graph dependent (updates as OSM data updates).
- **License:** OSM data © OpenStreetMap contributors, ODbL 1.0; OSRM
  open-source (BSD-2).
- **Verified:** Shillong→Guwahati = 101.1 km real geometry.

### 4. NASA GIBS — Satellite imagery layers
- **Feeds:** map overlays — VIIRS true color, MODIS true color, MODIS flood
  product — with real acquisition dates (validated by tile probes).
- **Endpoint used:** `https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/...`
- **Update frequency:** daily, acquisition- and cloud-dependent.
- **License:** NASA imagery public domain; acknowledgment requested.
- **Verified:** all 3 layers serve real 2026-09-06 tiles.

### 5. Nominatim / OpenStreetMap — Geocoding
- **Feeds:** place → coordinates, with fallback to the curated district table.
- **Endpoint used:** `https://nominatim.openstreetmap.org/search`
- **License:** OSM data ODbL 1.0; Nominatim usage policy applies
  (https://operations.osmfoundation.org/policies/nominatim/).

---

## Historical datasets (bundled in the app, clearly labeled "historical")

### 6. India Flood Inventory
- **Feeds:** flood risk evidence; district records anchored to real
  district-HQ coordinates (e.g. the 1983 Mangan flash flood — 113 deaths,
  27 landslides that marooned Mangan town; 1980 & 1990 Mangan events).
- **Contents in app:** 1,305 records with IMD `UEI-*` event identifiers.
- **Origin:** IMD (India Meteorological Department) data, compiled as the
  India Flood Inventory (IIT Gandhinagar research dataset).
- **License:** open research/IMD-sourced dataset; used as historical evidence
  only — never presented as a live closure.
- **Reference:** the dataset's UEI scheme and IMD gridded data
  (https://www.imdpune.gov.in) form the source lineage.

### 7. NASA Global Landslide Catalog (GLC)
- **Feeds:** landslide susceptibility evidence with real coordinates.
- **Contents in app:** 351 records across the 8 NER states (e.g. 2010
  Manipur downpour event).
- **Origin:** NASA GLC — https://data.nasa.gov/Earth-Science/Global-Landslide-Catalog-Export/dd9e-wu2v
- **License:** public domain (NASA).
- **Note:** the catalog has no records within 100 km of Mangan — the app is
  honest about this and the landslide score there comes from the live
  rainfall × terrain model, labeled "estimate, not a recorded event".

### 8. NER district-HQ reference table (curated, first-party)
- **Feeds:** town-level geocoding for all 124 districts across the 8 states
  + spatial anchoring of district-level flood records.
- **Origin:** state-government district lists; coordinates resolved via
  OpenStreetMap with state disambiguation; manual overrides where Nominatim
  returns a district centroid instead of the town (Mangan 27.5167, 88.5333 —
  sourced from the Sikkim State Disaster Management Authority report; Mon
  26.7253, 95.0304 — OSM town node).
- **License:** project data over ODbL/OSM coordinates.
- **Verified:** 23/23 test locations across all 8 states resolve correctly.

---

## First-party data (collected by the platform)

### 9. Field reports & photos
- **Feeds:** current ground truth — blocked roads, damage, floods;
  verification status tracked end-to-end; offline sync via `offline_id`
  deduplication.
- **Origin:** field officials / app users; 10 reports currently in store.
- **License:** project data.

### 10. Vehicle GPS positions
- **Feeds:** live fleet tracking endpoints (`/vehicles`,
  `/vehicles.geojson`).
- **Origin:** consented GPS device reports; 7 vehicles in store.
- **License:** project data; production use requires auth + retention rules
  (documented in README).

---

## Where to look for the code

- Backend: `backend/main.py` (endpoints), `backend/services/route_risk.py`
  (risk engine), `backend/services/satellite_layers.py` (GIBS),
  `backend/services/data_sources.py` (collector).
- Data: `backend/data/raw/` (flood, landslide, weather, rainfall),
  `backend/gis/ner_places.json` (district table).
- Frontend: `mobile/web/ml/gis/index.html`.

## Verification record (this build)

All endpoints tested with real data: 10/10 location analyses across 8
states, route analysis with 24 checked segments, report create → sync
idempotency → verification, vehicle position → list → GeoJSON, alerts,
district accessibility, satellite layers, data status — all HTTP 200/201.
Test records were created then removed; the live store contains only real
reports and vehicles.