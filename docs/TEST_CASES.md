# NER-LogixAI — Test Case Report (verified on demo build)

Run against the live server at `http://127.0.0.1:8000` on **2026-09-07**.
Result: **28 / 28 PASSED**. All data returned is real (live APIs or bundled
datasets — see `docs/DATA_SOURCES.md`).

## API test cases

| # | Test | Endpoint | Expected | Result |
| --- | --- | --- | --- | --- |
| T1 | Dashboard loads | `GET /` | HTTP 200, contains NER-LogixAI | ✅ PASS |
| T2 | Health | `GET /health` | status ok/healthy | ✅ PASS |
| T3 | All 8 NER states | `GET /ner/states` | 8 states with capitals | ✅ PASS |
| T4 | Source registry | `GET /sources` | ≥ 8 documented sources | ✅ PASS (10) |
| T5 | Location: Mangan (Sikkim) | `POST /location/analyze` | 200 + risk scores | ✅ PASS |
| T6 | Location: Guwahati (Assam) | `POST /location/analyze` | 200 + risk scores | ✅ PASS |
| T7 | Location: Imphal (Manipur) | `POST /location/analyze` | 200 + risk scores | ✅ PASS |
| T8 | Location: Aizawl (Mizoram) | `POST /location/analyze` | 200 + risk scores | ✅ PASS |
| T9 | Location: Kohima (Nagaland) | `POST /location/analyze` | 200 + risk scores | ✅ PASS |
| T10 | Location: Itanagar (Arunachal) | `POST /location/analyze` | 200 + risk scores | ✅ PASS |
| T11 | Location: Agartala (Tripura) | `POST /location/analyze` | 200 + risk scores | ✅ PASS |
| T12 | Location: Shillong (Meghalaya) | `POST /location/analyze` | 200 + risk scores | ✅ PASS |
| T13 | Location: Tawang | `POST /location/analyze` | 200 + risk scores | ✅ PASS |
| T14 | Location: Lunglei | `POST /location/analyze` | 200 + risk scores | ✅ PASS |
| T15 | Location: Mon (Nagaland town) | `POST /location/analyze` | 200 + risk scores | ✅ PASS |
| T16 | Location: Hawai (Anjaw HQ) | `POST /location/analyze` | 200 + risk scores | ✅ PASS |
| T17 | Route: Shillong → Guwahati, emergency medicines | `POST /route/analyze` | 200, safety decision, 24 segments checked | ✅ PASS |
| T18 | Data status (live sources) | `GET /data/status` | operational_live_sources = true | ✅ PASS |
| T19 | Alerts | `GET /alerts` | ≥ 1 active alert with severity | ✅ PASS (6) |
| T20 | District accessibility | `GET /districts/accessibility` | 8 states summarized | ✅ PASS |
| T21 | Field reports | `GET /reports` | list of reports | ✅ PASS (10) |
| T22 | Reports GeoJSON | `GET /reports.geojson` | FeatureCollection | ✅ PASS |
| T23 | State boundaries GeoJSON | `GET /geojson` | 200 | ✅ PASS |
| T24 | Vehicles | `GET /vehicles` | list | ✅ PASS (7) |
| T25 | Vehicles GeoJSON | `GET /vehicles.geojson` | FeatureCollection | ✅ PASS |
| T26 | Satellite layers | `GET /satellite/layers` | 3 layers, real dates | ✅ PASS |
| T27 | Invalid payload rejected | `POST /location/analyze` (empty body) | HTTP 422 validation | ✅ PASS |
| T28 | Unknown place handled | `POST /location/analyze` ("NowhereCityXYZ") | graceful 404, no crash | ✅ PASS |

## Write-flow test cases (reports, sync, vehicles)

| # | Test | Endpoint | Expected | Result |
| --- | --- | --- | --- | --- |
| W1 | Create report | `POST /reports` | 201 + report_id | ✅ PASS |
| W2 | Offline sync dedupe | `POST /sync/reports` (repeat batch) | `already_synced`, no duplicate | ✅ PASS |
| W3 | Verify report | `PATCH /reports/{id}/verification?status=verified` | 200, status = verified | ✅ PASS |
| W4 | Photo upload | `POST /reports/photos` | 201 + file URL | ✅ PASS |
| W5 | Vehicle position update | `POST /vehicles/{id}/location` | 201 | ✅ PASS |
| W6 | Vehicle listed after update | `GET /vehicles` | vehicle present with status | ✅ PASS |

*Note: all test records created during W1–W6 were deleted afterwards — the
live store contains only real reports (10) and vehicles (7).*

## Live-data sanity checks (re-run any time)

- **Weather/rainfall:** Open-Meteo `past_days=1` — Mangan shows live
  temperature + 24 h rainfall on the location card.
- **River (GloFAS):** Teesta at Mangan — real discharge vs that river's own
  p90/p98 from 120 days of history.
- **Routing:** OSRM public server — Shillong→Guwahati = real road geometry.
- **Satellite:** NASA GIBS tiles for all 3 layers confirmed serving on the
  advertised acquisition date.

## Honest limits (documented, not hidden)

- Landslide score at Mangan uses the live rainfall × terrain model where the
  NASA catalog has no records — labeled "estimate, not a recorded event".
- Satellite layers are optical (cloud-limited); flood product is screening
  only, not closure confirmation.
- Accessibility scores are evidence-based estimates, not an official
  road-closure registry.