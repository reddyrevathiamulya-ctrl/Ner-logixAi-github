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

Run the collector from the repository root:

```powershell
.\.venv\Scripts\python.exe -m backend.services.data_sources
```

The API endpoint `GET /data/status` reports source freshness. Weather and rainfall
are live-capable inputs; flood and landslide inventories are intentionally marked
as historical evidence and must not be presented as live road closures.

`GET /alerts` provides actionable warnings for stale live sources and high-severity
field incidents. Alerts include severity, evidence, coordinates, timestamps, and
the verification status of field reports.

`GET /districts/accessibility` provides a centralized NER-8 state summary with
accessibility estimate, historical hazard count, current field-report count,
source freshness, and data-quality labeling. It is intended for district-wise
connectivity and bottleneck monitoring, not as an official closure register.

`POST /location/analyze` accepts a user-entered place and returns separate
landslide, boulder/rockfall susceptibility, flood, weather, and current-incident
results. It also returns confidence, evidence, data timestamps, and warnings when
the available data cannot support a strong conclusion. `GET /reports.geojson`
provides current field reports directly to a GIS map.

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
