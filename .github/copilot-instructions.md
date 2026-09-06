# NER-LogixAI Copilot Instructions

## Product and architecture
- NER-LogixAI is a logistics accessibility and emergency-response platform for North Eastern India. The primary user flow is origin/destination route planning with safety and accessibility evidence, not ordinary fastest-route navigation.
- `backend/main.py` owns the FastAPI application and registers the HTTP surface. Keep domain logic in `backend/services/` rather than adding large handlers to `main.py`.
- `backend/services/route_risk.py` is the central route-analysis boundary. It evaluates route segments and combines weather/rainfall, terrain slope and relief, historical flood/landslide evidence, rockfall susceptibility, and current field reports before producing route comparisons and recommendations.
- The frontend is the browser GIS dashboard in `mobile/web/ml/gis/index.html`. When an API response changes, update the dashboard rendering and user-facing explanation in the same change.
- The backend exposes map-oriented GeoJSON where appropriate. Preserve coordinate order and feature properties because the dashboard consumes them directly.

## Evidence and safety semantics
- Keep historical evidence, current reports, verified incidents, danger segments, and recommendation reasoning separate in API responses and UI copy.
- A missing verified closure means "no verified current blockage in available data", not "safe". Do not turn absence of data into a safety guarantee.
- Rockfall is currently susceptibility screening, not direct boulder-movement detection. Use cautious wording such as "high susceptibility" unless a current sensor, camera, or verified field report confirms an incident.
- Route scoring is mission-aware. Cargo and priority affect the balance between safety and travel time; emergency delivery prioritizes route safety more strongly than standard delivery.
- Do not leave synthetic incidents, vehicles, or validation records in the live data store. Empty feeds should remain empty.

## Service patterns
- Add focused modules under `backend/services/` for new domain behavior, then expose them through a small endpoint in `backend/main.py`.
- Existing modules include `incident_reports.py`, `vehicle_tracking.py`, `district_accessibility.py`, `source_registry.py`, and `route_risk.py`; follow their validation and response shapes before inventing new ones.
- Field reports support offline synchronization through `POST /sync/reports`; retries are expected, so preserve `offline_id` duplicate protection and return accepted, already-synchronized, and invalid results separately.
- Vehicle tracking endpoints (`POST /vehicles/{vehicle_id}/location`, `GET /vehicles`, and `GET /vehicles.geojson`) represent live operational data. Preserve status, cargo, timestamp, and source metadata.
- External integrations include OpenStreetMap Nominatim for geocoding, OSRM for driving routes, and public weather/terrain/hazard sources. Treat remote data as fallible and retain source/freshness information where the existing model provides it.

## Development workflow
- From the repository root on Windows, start the API with `.\backend\venv\Scripts\python.exe -m uvicorn backend.main:app --reload` (the intended local URL is `http://127.0.0.1:8000`).
- Before running API checks, ensure the backend virtual environment and its dependencies are available. Use the project's existing dependency files rather than installing ad hoc packages.
- For a quick syntax check, run `.\backend\venv\Scripts\python.exe -m compileall backend`.
- Exercise changed endpoints against the running API, especially route analysis, report sync/idempotency, accessibility, and GeoJSON output. Confirm the frontend still renders the returned properties.
- Keep README/API descriptions aligned with implemented endpoints; distinguish implemented modules from production-planned integrations.

## Editing guidance
- Prefer small, focused changes and preserve existing response contracts because the map frontend consumes them directly.
- Do not claim official closures, guaranteed safety, live GPS monitoring, or direct hazard detection without corresponding verified data and integrations.
- When changing risk logic, update the explanation shown to users and add or run a focused validation for the affected service.