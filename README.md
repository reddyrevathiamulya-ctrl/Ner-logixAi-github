# Ner-logixAi-github
AI-powered Smart Logistics and Accessibility Intelligence Platform for the North Eastern Region of India.
# NER-LogixAI

## AI-Powered Smart Logistics and Accessibility Intelligence Platform for North Eastern India

NER-LogixAI is an AI-powered logistics and accessibility intelligence platform designed to improve transportation planning, route safety, and emergency logistics across the North Eastern Region (NER) of India.

## SIH Problem Alignment

The North Eastern Region faces difficult terrain, extreme weather, limited
connectivity, and frequent disruptions from landslides, floods, bridge damage,
road damage, and infrastructure gaps. These disruptions delay medicines, food,
construction materials, agricultural produce, and other essential supplies,
increasing cost and interrupting public-service delivery.

NER-LogixAI addresses the SIH problem statement through one integrated logistics
intelligence platform for district officials, field teams, transport operators,
and essential-goods delivery users. It combines GIS, AI/ML-ready risk analytics,
weather and rainfall feeds, satellite layers, terrain data, GPS-ready logistics
interfaces, and geo-tagged field intelligence.

The intended platform outcomes are:

- Continuous visibility of road, bridge, route, and district accessibility
- Early warning of possible disruption from rainfall, floods, landslides,
	rockfall, road damage, and congestion
- Safer alternate routes with estimated delay and evidence-based explanations
- GPS tracking of vehicles carrying medicines, food, agricultural produce, and
	construction materials
- Automated alerts for blocked roads, inaccessible regions, delayed deliveries,
	and high-risk corridors
- Geo-tagged photographs and incident reports from officials and local users
- Centralized district connectivity, bottleneck, emergency-route, and delivery
	monitoring dashboards
- Multilingual notifications and offline synchronization for low-network areas

The platform combines Artificial Intelligence (AI), Machine Learning (ML), GIS mapping, weather intelligence, terrain analysis, GPS-based vehicle tracking, satellite observations, and real-time field reports.

---

## Problem

The North Eastern Region faces major logistics and accessibility challenges due to:

- Difficult mountainous terrain
- Heavy rainfall and extreme weather
- Landslides and floods
- Road and bridge disruptions
- Limited transport connectivity
- Poor network connectivity in remote locations

These disruptions can delay essential supplies such as medicines, food, agricultural produce, construction materials, and emergency materials.

---

## Our Solution

NER-LogixAI provides an intelligent platform that:

- Monitors road and transport accessibility
- Predicts possible route disruptions
- Calculates dynamic accessibility and risk scores
- Suggests safer and alternative transportation routes
- Tracks logistics vehicles using GPS
- Detects mobility anomalies and possible road disruptions
- Enables geo-tagged incident reporting
- Provides emergency accessibility intelligence
- Supports offline reporting and synchronization

The current prototype implements the GIS, weather, terrain, hazard-evidence,
route-ranking, alert, satellite-layer, and field-report foundations. Vehicle GPS,
offline mobile synchronization, multilingual notification delivery, and official
transport-system integrations remain planned production modules.

---

## Core Innovation

### Dynamic Accessibility Intelligence Score (DAIS)

Each road segment receives a continuously updated accessibility score based on:

- Rainfall and weather conditions
- Terrain and slope
- Historical landslide information
- Road and incident reports
- GPS vehicle movement patterns
- Satellite and remote sensing observations

---

## Technology Stack

### Mobile Application
- Flutter

### Web Dashboard
- React

### Backend
- Python
- FastAPI

### Database
- PostgreSQL
- PostGIS

### GIS and Maps
- OpenStreetMap
- MapLibre

### AI and Machine Learning
- Python
- Scikit-learn
- XGBoost
- GeoPandas
- Rasterio
- Other geospatial AI tools

---

## Project Modules

1. GIS Road Network
2. Weather Intelligence
3. Landslide Risk Prediction
4. Dynamic Accessibility Scoring
5. Safe Route Optimization
6. GPS Vehicle Tracking
7. GPS Anomaly Detection
8. Incident Reporting
9. Satellite Intelligence
10. Emergency Logistics Mode

---

## Project Status

🚧 Development in Progress

Currently building the project foundation and GIS-based prototype.

## Current Data Sources

The ingestion pipeline currently uses free, open or openly accessible sources:

- OpenStreetMap and OSRM for road and route data
- Open-Meteo for batched current weather and forecast data
- NASA GIBS for map-ready satellite imagery layers
- India Flood Inventory for historical flood evidence
- NASA Global Landslide Catalog for historical landslide evidence
- Curated NER district-headquarters coordinates for all 124 districts across
  the eight states (`backend/gis/ner_places.json`) for town-level geocoding and
  spatial anchoring of district-level records

Run the collector from the repository root:

```powershell
.\.venv\Scripts\python.exe -m backend.services.data_sources
```
### Endpoint data sources, update frequency, and license

| Endpoint | Real data source | Update frequency | License |
| --- | --- | --- | --- |
| `GET /` (dashboard) | Static GIS dashboard (`mobile/web/ml/gis/index.html`) | on deploy | project code |
| `GET /health`, `GET /ner/states` | no external data | - | project code |
| `GET /data/status` | freshness of the collected dataset files | live | - |
| `GET /sources` | static source registry (`backend/services/source_registry.py`) | on deploy | project code |
| `POST /location/analyze` | Open-Meteo forecast + elevation API; Open-Meteo Flood API (GloFAS river discharge); India Flood Inventory; NASA Global Landslide Catalog; field reports; NER district-HQ table (`backend/gis/ner_places.json`) | weather ~15 min; river discharge daily; inventories historical | Open-Meteo free non-commercial; CEMS/GloFAS open; NASA public domain; see notes below |
| `GET /satellite/layers` | NASA GIBS (VIIRS true color, MODIS true color, MODIS flood product) capabilities document + live tile probes | daily, acquisition and cloud dependent | NASA imagery public domain; acknowledgment requested |
| `GET /alerts` | local alert rules over current field reports and source freshness | live (on request) | project code |
| `POST /route/analyze` | OSRM public router over the OpenStreetMap road graph; Open-Meteo weather/rainfall; Open-Meteo elevation; hazard inventories; field reports | road graph updates with OSM; weather live; inventories historical | OSM data ODbL 1.0; OSRM open-source (BSD-2); Open-Meteo free non-commercial |
| `GET /districts/accessibility` | normalized flood/landslide inventories + field reports + source freshness | on request | project code over open datasets |
| `POST /reports` / `GET /reports` / `GET /reports.geojson` | first-party field reports (user-submitted, geo-tagged) | on submission | project data (first-party) |
| `POST /reports/photos` / `GET /reports/photos/{filename}` | uploaded field photographs | on submission | project data (first-party) |
| `PATCH /reports/{id}/verification` | field report store | on action | project data (first-party) |
| `POST /sync/reports` | queued offline reports (deduplicated by `offline_id`) | on submission | project data (first-party) |
| `POST /vehicles/{id}/location` / `GET /vehicles` / `GET /vehicles.geojson` | consented GPS positions of essential-goods vehicles | on report | project data (first-party) |
| `GET /geojson` | NER state-boundary geometry | on deploy | open geospatial data |

License notes: Open-Meteo APIs are free for non-commercial use
(https://open-meteo.com/en/terms). OpenStreetMap data is licensed ODbL 1.0
(© OpenStreetMap contributors). NASA GIBS imagery and the NASA Global
Landslide Catalog are public domain. GloFAS river-discharge data is provided
through the Open-Meteo Flood API under the Copernicus Emergency Management
Service data policy. The India Flood Inventory is an IMD-sourced research
dataset used as historical evidence only. Field reports and vehicle positions
are first-party data collected by this platform.

Demo materials: a 5-minute walkthrough is in `docs/DEMO_SCRIPT.md` and the
full source-by-source references and licenses are in `docs/DATA_SOURCES.md`.


The API endpoint `GET /data/status` reports source freshness. Weather and rainfall
are live inputs; flood and landslide inventories are intentionally marked as
historical evidence and must not be presented as live road closures. The
location risk scores additionally blend live rainfall and terrain into clearly
labeled susceptibility estimates, separate from recorded events.

`GET /alerts` provides actionable warnings for stale live sources and high-severity
field incidents. Alerts include severity, evidence, coordinates, timestamps, and
the verification status of field reports.

`GET /districts/accessibility` provides a centralized NER-8 state summary with
accessibility estimate, historical hazard count, current field-report count,
source freshness, and data-quality labeling. It is intended for district-wise
connectivity and bottleneck monitoring, not as an official closure register.

`POST /location/analyze` accepts a user-entered place and returns separate
landslide, boulder/rockfall susceptibility, flood, weather, and current-incident
results. Landslide risk blends recorded historical evidence with a live
rainfall-triggered susceptibility model driven by real Open-Meteo 24-hour
rainfall and terrain relief; flood risk anchors district-level India Flood
Inventory records to their district-HQ coordinates so documented events (e.g.
the 1983 Mangan flash flood) count as spatial evidence, and adds a live
river-discharge signal from the GloFAS model (Open-Meteo Flood API) that
compares today's discharge against the river's own 90th/98th percentiles. The
response exposes a `live_estimates` block that separates live rainfall and
river-based scores from observed historical evidence, plus confidence,
evidence, data timestamps, and warnings when the available data cannot support
a strong conclusion. `GET /reports.geojson` provides current field reports
directly to a GIS map.

Place resolution prefers populated-place results and falls back to a curated
district-headquarters reference table covering all 124 districts of the eight
NER states (see `backend/gis/ner_places.json`) so district-named places such as
Mangan, Anjaw, or North Tripura resolve to the actual HQ town instead of the
administrative centroid.

Route analysis accepts `cargo_type` and `priority`. This makes the recommendation
logistics-aware: emergency medicines and supplies favor safer corridors, while
perishable cargo gives more weight to travel time. The result includes the
optimization basis so the recommendation is explainable.

GPS-ready fleet endpoints are available for essential-goods operations:

```text
POST /vehicles/{vehicle_id}/location
GET  /vehicles
GET  /vehicles.geojson
```

These endpoints store the latest consented position per vehicle, cargo category,
delivery identifier, origin, destination, and delivery status. Production use
still requires authentication, driver consent, retention rules, and encrypted
storage.

Offline field devices can synchronize queued reports in one request:

```text
POST /sync/reports
```

Each queued report should include a device-generated `offline_id`. Repeating the
same batch after a network failure is safe: the server reports it as
`already_synced` instead of creating a duplicate incident.

## Product Differentiators

- Evidence-first risk explanations instead of one unexplained danger color
- Separate fast signals, historical evidence, and field-confirmed information
- Rockfall screening that separates terrain susceptibility from individual-boulder detection
- Segment-by-segment route risk, not only origin/destination weather
- Verification-aware field reports with photographs and offline IDs
- Source freshness and confidence visible to the user
- Offline-friendly reporting for low-connectivity districts
- Emergency logistics mode for essential deliveries
- Local-language alerts and low-bandwidth notification fallback

Run continuous monitoring with:

```powershell
.\.venv\Scripts\python.exe -m backend.services.monitor
```

For a one-time collection, use `--once`. The default check interval is 5 minutes; use
`--interval-minutes` to configure it for testing or deployment.

The monitor checks sources every 5 minutes by default, but checking more often
does not create newer satellite imagery. NASA optical products are daily or
near-daily and cloud dependent. The API endpoint `GET /satellite/layers` exposes
NASA GIBS tile templates and product limitations for the map. NASA GPM IMERG is
the next live rainfall adapter, subject to product access, latency, licensing,
and spatial aggregation tests.

---

## Project Goal

To improve regional logistics efficiency, reduce supply disruptions, strengthen emergency response, and provide intelligent accessibility planning across the North Eastern Region of India.

---

## Team

Smart India Hackathon Team — NER-LogixAI
