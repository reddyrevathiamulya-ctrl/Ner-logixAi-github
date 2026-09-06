from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from pathlib import Path
from datetime import datetime, timedelta, timezone
import requests
import ollama
import math
import os
# ============================================================
# LIVE ROAD DATA - OPENSTREETMAP
# ============================================================

OVERPASS_URL = "https://overpass-api.de/api/interpreter"


def get_live_road_data(lat: float, lon: float):
    query = f"""
    [out:json][timeout:8];
    way(around:1000,{lat},{lon})["highway"];
    out tags center;
    """

    try:
        response = requests.post(
            OVERPASS_URL,
            data=query,
            timeout=10,
            headers={"User-Agent": "NER-LogixAI/1.0"}
        )

        response.raise_for_status()

        elements = response.json().get("elements", [])

        roads = []

        for road in elements:
            tags = road.get("tags", {})

            roads.append({
                "name": tags.get("name", "Unnamed road"),
                "highway": tags.get("highway", "unknown"),
                "surface": tags.get("surface", "unknown"),
                "lanes": tags.get("lanes", "unknown"),
                "maxspeed": tags.get("maxspeed", "unknown"),
                "lit": tags.get("lit", "unknown"),
                "smoothness": tags.get("smoothness", "unknown")
            })

        return {
            "source": "OpenStreetMap",
            "road_count": len(roads),
            "roads": roads[:20]
        }

    except requests.RequestException as error:
        return {
            "source": "OpenStreetMap",
            "road_count": 0,
            "roads": [],
            "error": str(error)
        }


# =========================================================
# APP SETUP
# =========================================================

app = FastAPI(
    title="NER-LogixAI Logistics Accessibility Intelligence API",
    description=(
        "SIH-aligned decision support for essential-goods logistics, route "
        "accessibility, hazard evidence, field reports, and emergency response "
        "across North Eastern India."
    ),
)
ENABLE_AI_EXPLANATION = os.getenv("NER_LOGIX_ENABLE_AI", "false").lower() == "true"
@app.get("/health")
def health():
    return {"status": "ok"}

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =========================================================
# PATHS
# =========================================================

BASE_DIR = Path(__file__).resolve().parent.parent
BACKEND_DIR = Path(__file__).resolve().parent
GEOJSON_FILE = BACKEND_DIR / "gis" / "india_states.geojson"


# =========================================================
# EXISTING NER DATA
# =========================================================

from backend.gis.ner_states import NER_STATES
from backend.services.data_status import get_data_status
from backend.services.route_risk import (
    analyze_route_geometry,
    analyze_location,
    load_current_incident_hazards,
    load_historical_hazards,
)
from backend.services.incident_reports import (
    PHOTO_DIR,
    create_report,
    list_reports,
    save_photo,
    verify_report,
)
from backend.services.satellite_layers import get_satellite_layers
from backend.services.alerts import get_active_alerts
from backend.services.source_registry import get_source_registry
from backend.services.vehicle_tracking import (
    list_vehicle_positions,
    update_vehicle_position,
)
from backend.services.district_accessibility import get_district_accessibility


class IncidentReportRequest(BaseModel):
    incident_type: str
    severity: str
    latitude: float
    longitude: float
    description: str = ""
    photo_url: str | None = None
    reported_at: str | None = None
    offline_id: str | None = None
    source: str = "field_app"


class VehiclePositionRequest(BaseModel):
    latitude: float
    longitude: float
    cargo_type: str = "other"
    cargo_description: str = ""
    origin: str = ""
    destination: str = ""
    status: str = "unknown"
    delivery_id: str | None = None
    observed_at: str | None = None
    source: str = "gps_device"


class LocationRiskRequest(BaseModel):
    location: str


# =========================================================
# BASIC ENDPOINTS
# =========================================================

@app.get("/")
def home():
    index_file = BASE_DIR / "mobile" / "web" / "ml" / "gis" / "index.html"

    if not index_file.exists():
        raise HTTPException(
            status_code=404,
            detail=f"index.html not found at {index_file}"
        )

    return FileResponse(index_file)


@app.get("/health")
def health():
    return {
        "status": "healthy"
    }


@app.get("/ner/states")
def get_ner_states():
    return {
        "region": "North Eastern Region of India",
        "count": len(NER_STATES),
        "states": NER_STATES
    }


@app.get("/data/status")
def data_status():
    return get_data_status()


@app.post("/location/analyze")
def analyze_location_risk(request: LocationRiskRequest):
    if not request.location.strip():
        raise HTTPException(status_code=400, detail="Location is required")

    place = geocode_place(request.location.strip())
    weather = get_weather(place["lat"], place["lon"])
    weather_score, weather_risk, weather_hazards = calculate_weather_risk(weather)
    hazards = load_historical_hazards() + load_current_incident_hazards()
    result = analyze_location(
        place["lat"],
        place["lon"],
        weather_score,
        hazards,
        f"{request.location} {place['name']}",
    )
    result["place"] = place
    result["weather"] = {
        "score": weather_score,
        "risk": weather_risk,
        "hazards": weather_hazards,
        "observed_at": weather.get("time"),
    }
    return result


@app.get("/satellite/layers")
def satellite_layers():
    return get_satellite_layers()


@app.get("/alerts")
def alerts():
    return get_active_alerts()


@app.get("/sources")
def sources():
    return get_source_registry()


@app.post("/vehicles/{vehicle_id}/location", status_code=201)
def update_vehicle(vehicle_id: str, request: VehiclePositionRequest):
    try:
        return update_vehicle_position(vehicle_id, request.model_dump())
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@app.get("/vehicles")
def vehicles():
    positions = list_vehicle_positions()
    return {"count": len(positions), "vehicles": positions}


@app.get("/vehicles.geojson")
def vehicles_geojson():
    return {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [position["longitude"], position["latitude"]],
                },
                "properties": {
                    key: value
                    for key, value in position.items()
                    if key not in {"latitude", "longitude"}
                },
            }
            for position in list_vehicle_positions()
        ],
    }


@app.get("/geojson")
def geojson():
    if not GEOJSON_FILE.exists():
        raise HTTPException(
            status_code=404,
            detail="India states GeoJSON file not found."
        )

    return FileResponse(GEOJSON_FILE)


@app.post("/reports", status_code=201)
def submit_incident_report(request: IncidentReportRequest):
    try:
        return create_report(request.model_dump())
    except (TypeError, ValueError) as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@app.post("/sync/reports")
def sync_incident_reports(requests: list[IncidentReportRequest]):
    created = []
    already_synced = []
    rejected = []
    for request in requests[:200]:
        try:
            was_synced = bool(
                request.offline_id
                and any(
                    item.get("offline_id") == request.offline_id
                    for item in list_reports(500)
                )
            )
            report = create_report(request.model_dump())
            if was_synced:
                already_synced.append(report)
            else:
                created.append(report)
        except (TypeError, ValueError) as error:
            rejected.append({"offline_id": request.offline_id, "error": str(error)})
    return {
        "accepted_count": len(created),
        "already_synced_count": len(already_synced),
        "rejected_count": len(rejected),
        "created": created,
        "already_synced": already_synced,
        "rejected": rejected,
    }


@app.get("/reports")
def get_incident_reports(limit: int = 100):
    reports = list_reports(limit)
    return {
        "count": len(reports),
        "reports": reports,
    }


@app.get("/reports.geojson")
def incident_reports_geojson(limit: int = 500):
    reports = list_reports(limit)
    return {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [report["longitude"], report["latitude"]],
                },
                "properties": {
                    key: value
                    for key, value in report.items()
                    if key not in {"latitude", "longitude"}
                },
            }
            for report in reports
        ],
    }


@app.post("/reports/photos", status_code=201)
async def upload_incident_photo(file: UploadFile = File(...)):
    try:
        content = await file.read()
        filename = save_photo(content, file.content_type)
        return {
            "filename": filename,
            "url": f"/reports/photos/{filename}",
        }
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@app.get("/reports/photos/{filename}")
def get_incident_photo(filename: str):
    if Path(filename).name != filename:
        raise HTTPException(status_code=400, detail="Invalid photo filename")
    photo_path = PHOTO_DIR / filename
    if not photo_path.is_file():
        raise HTTPException(status_code=404, detail="Photo not found")
    return FileResponse(photo_path)


@app.patch("/reports/{report_id}/verification")
def review_incident_report(report_id: str, status: str):
    try:
        return verify_report(report_id, status.strip().lower())
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


# =========================================================
# ROUTE REQUEST MODEL
# =========================================================

class RouteRequest(BaseModel):
    start: str
    destination: str
    cargo_type: str = "other"
    priority: str = "standard"


# =========================================================
# GEOCODING
# =========================================================

def geocode_place(place: str):

    url = "https://nominatim.openstreetmap.org/search"

    headers = {
        "User-Agent": "NER-LogixAI/1.0"
    }

    queries = [place]
    if "," in place:
        queries.append(place.split(",", 1)[0].strip())
    first_phrase = " ".join(place.split()[:2]).strip()
    if first_phrase and first_phrase not in queries:
        queries.append(first_phrase)
    first_token = place.split()[0].strip() if place.split() else ""
    if first_token and first_token not in queries:
        queries.append(first_token)

    results = []
    for query in queries:
        try:
            response = requests.get(
                url,
                params={
                    "q": f"{query}, India",
                    "format": "jsonv2",
                    "limit": 1,
                    "countrycodes": "in"
                },
                headers=headers,
                timeout=15
            )
            response.raise_for_status()
            results = response.json()
        except requests.RequestException as error:
            raise HTTPException(
                status_code=502,
                detail=f"Location service unavailable: {error}"
            ) from error
        if results:
            break

    if not results:
        raise HTTPException(
            status_code=404,
            detail=f"Location not found: {place}"
        )

    return {
        "name": results[0]["display_name"],
        "lat": float(results[0]["lat"]),
        "lon": float(results[0]["lon"])
    }


# =========================================================
# WEATHER
# =========================================================

def get_weather(lat: float, lon: float):

    url = "https://api.open-meteo.com/v1/forecast"

    params = {
        "latitude": lat,
        "longitude": lon,
        "current": (
            "temperature_2m,"
            "relative_humidity_2m,"
            "precipitation,"
            "rain,"
            "weather_code,"
            "wind_speed_10m"
        ),
        "hourly": (
            "temperature_2m,"
            "precipitation_probability,"
            "precipitation,"
            "rain,"
            "weather_code,"
            "wind_speed_10m"
        ),
        "forecast_days": 1,
        "timezone": "auto"
    }

    try:
        response = requests.get(
            url,
            params=params,
            timeout=15
        )

        response.raise_for_status()

    except requests.RequestException as error:
        raise HTTPException(
            status_code=502,
            detail=f"Weather service unavailable: {error}"
        )

    data = response.json()

    current = data.get("current", {})

    return {
        "temperature": current.get("temperature_2m"),
        "humidity": current.get("relative_humidity_2m"),
        "precipitation": current.get("precipitation"),
        "rain": current.get("rain"),
        "weather_code": current.get("weather_code"),
        "wind_speed": current.get("wind_speed_10m"),
        "time": current.get("time")
    }


# =========================================================
# WEATHER RISK
# =========================================================

def calculate_weather_risk(weather):

    score = 100
    hazards = []

    precipitation = weather.get("precipitation") or 0
    rain = weather.get("rain") or 0
    wind = weather.get("wind_speed") or 0
    weather_code = weather.get("weather_code")

    # -----------------------------------------------------
    # Rain risk
    # -----------------------------------------------------

    if rain >= 10 or precipitation >= 10:
        score -= 35
        hazards.append("Heavy rainfall")

    elif rain >= 5 or precipitation >= 5:
        score -= 20
        hazards.append("Moderate rainfall")

    elif rain > 0 or precipitation > 0:
        score -= 8
        hazards.append("Rain")

    # -----------------------------------------------------
    # Wind risk
    # -----------------------------------------------------

    if wind >= 60:
        score -= 30
        hazards.append("Very strong winds")

    elif wind >= 40:
        score -= 20
        hazards.append("Strong winds")

    elif wind >= 25:
        score -= 8
        hazards.append("Moderate winds")

    # -----------------------------------------------------
    # Weather-code risk
    # -----------------------------------------------------

    dangerous_codes = {
        65: "Heavy rain",
        67: "Heavy freezing rain",
        75: "Heavy snow",
        82: "Heavy rain showers",
        95: "Thunderstorm",
        96: "Thunderstorm with hail",
        99: "Thunderstorm with hail"
    }

    if weather_code in dangerous_codes:

        score -= 25

        hazard = dangerous_codes[weather_code]

        if hazard not in hazards:
            hazards.append(hazard)

    score = max(0, min(100, score))

    if score >= 80:
        risk_level = "Low"

    elif score >= 60:
        risk_level = "Moderate"

    elif score >= 40:
        risk_level = "High"

    else:
        risk_level = "Very High"

    return score, risk_level, hazards

# ============================================================
# SAR / SEARCH AND RESCUE
# ============================================================

def get_sar_data(lat: float, lon: float):
    return {
        "available": True,
        "status": "SAR assessment available",
        "risk_level": "moderate",
        "latitude": lat,
        "longitude": lon,
        "recommendation": (
            "Maintain emergency communication and use verified "
            "local rescue services when required."
        )
    }
# =========================================================
# ROAD ROUTING
# =========================================================

def get_routes(start, destination):

    coordinates = (
        f"{start['lon']},{start['lat']};"
        f"{destination['lon']},{destination['lat']}"
    )

    url = (
        "https://router.project-osrm.org/"
        f"route/v1/driving/{coordinates}"
    )

    params = {
        "overview": "full",
        "geometries": "geojson",
        "alternatives": "true",
        "steps": "false"
    }

    try:
        response = requests.get(
            url,
            params=params,
            timeout=20
        )

        response.raise_for_status()

    except requests.RequestException as error:
        raise HTTPException(
            status_code=502,
            detail=f"Routing service unavailable: {error}"
        )

    data = response.json()

    if data.get("code") != "Ok":
        raise HTTPException(
            status_code=400,
            detail="No road route could be found."
        )

    return data.get("routes", [])


# =========================================================
# DISTANCE / TIME FORMATTERS
# =========================================================

def format_distance(meters):

    kilometers = meters / 1000

    if kilometers < 1:
        return f"{round(meters)} m"

    return f"{kilometers:.1f} km"


def format_duration(seconds):

    minutes = round(seconds / 60)

    hours = minutes // 60
    remaining_minutes = minutes % 60

    if hours > 0:
        return f"{hours} hr {remaining_minutes} min"

    return f"{remaining_minutes} min"


# =========================================================
# ROUTE ANALYSIS
# =========================================================
# ============================================================
# SAR DATA
# ============================================================

import os
import json


SAR_DATA_PATH = os.path.join(
    os.path.dirname(__file__),
    "gis",
    "data",
    "sar_data.json"
)


def get_sar_data(lat: float, lon: float):
    """
    Retrieve SAR observation data relevant to the requested location.
    Uses the local SAR dataset downloaded for the project.
    """

    try:
        if not os.path.exists(SAR_DATA_PATH):
            return {
                "source": "SAR dataset",
                "available": False,
                "observations": [],
                "message": "SAR data file not found."
            }

        with open(SAR_DATA_PATH, "r", encoding="utf-8") as file:
            sar_data = json.load(file)

        # Support either a list directly or {"observations": [...]}
        observations = (
            sar_data
            if isinstance(sar_data, list)
            else sar_data.get("observations", [])
        )

        # Return nearby observations.
        # If the downloaded dataset contains coordinates, use them.
        nearby = []

        for observation in observations:
            obs_lat = observation.get("latitude", observation.get("lat"))
            obs_lon = observation.get("longitude", observation.get("lon"))

            if obs_lat is None or obs_lon is None:
                continue

            try:
                distance = (
                    (float(obs_lat) - lat) ** 2
                    + (float(obs_lon) - lon) ** 2
                ) ** 0.5

                if distance <= 1.0:
                    nearby.append(observation)

            except (TypeError, ValueError):
                continue

        return {
            "source": "SAR dataset",
            "available": True,
            "observation_count": len(nearby),
            "observations": nearby[:20]
        }

    except Exception as error:
        return {
            "source": "SAR dataset",
            "available": False,
            "observations": [],
            "error": str(error)
        }


@app.post("/route/analyze")
def analyze_route(request: RouteRequest):

    # -----------------------------------------------------
    # INPUT VALIDATION
    # -----------------------------------------------------

    if not request.start.strip():
        raise HTTPException(
            status_code=400,
            detail="Starting location is required."
        )

    if not request.destination.strip():
        raise HTTPException(
            status_code=400,
            detail="Destination is required."
        )

    if request.start.strip().lower() == request.destination.strip().lower():
        raise HTTPException(
            status_code=400,
            detail="Starting location and destination cannot be the same."
        )

    valid_cargo_types = {
        "medicine", "food", "agricultural_produce",
        "construction_material", "emergency_supply", "other",
    }
    valid_priorities = {"standard", "urgent", "emergency", "perishable"}
    cargo_type = request.cargo_type.strip().lower()
    priority = request.priority.strip().lower()
    if cargo_type not in valid_cargo_types:
        raise HTTPException(status_code=400, detail="Unsupported cargo type.")
    if priority not in valid_priorities:
        raise HTTPException(status_code=400, detail="Unsupported delivery priority.")

    # -----------------------------------------------------
    # 1. FIND START LOCATION
    # -----------------------------------------------------

    start = geocode_place(
        request.start.strip()
    )

    # -----------------------------------------------------
    # 2. FIND DESTINATION
    # -----------------------------------------------------

    destination = geocode_place(
        request.destination.strip()
    )

    # -----------------------------------------------------
    # 3. GET REAL ROAD ROUTES
    # -----------------------------------------------------

    routes = get_routes(
        start,
        destination
    )

    if not routes:
        raise HTTPException(
            status_code=400,
            detail="No route found."
        )

    # -----------------------------------------------------
    # 4. WEATHER AT START
    # -----------------------------------------------------

    start_weather = get_weather(
        start["lat"],
        start["lon"]
    )

    # -----------------------------------------------------
    # 5. WEATHER AT DESTINATION
    # -----------------------------------------------------

    destination_weather = get_weather(
        destination["lat"],
        destination["lon"]
    )

    # -----------------------------------------------------
    # 6. CALCULATE WEATHER SAFETY
    # -----------------------------------------------------

    start_score, start_risk, start_hazards = (
        calculate_weather_risk(start_weather)
    )

    destination_score, destination_risk, destination_hazards = (
        calculate_weather_risk(destination_weather)
    )

    # Conservative route score:
    # use the lower of the two endpoint scores.

    safety_score = min(
        start_score,
        destination_score
    )

    # Combine hazards

    hazards = list(
        dict.fromkeys(
            start_hazards + destination_hazards
        )
    )

    # -----------------------------------------------------
    # 7. ROUTE RISK LEVEL
    # -----------------------------------------------------

    if safety_score >= 80:
        risk_level = "Low"

    elif safety_score >= 60:
        risk_level = "Moderate"

    elif safety_score >= 40:
        risk_level = "High"

    else:
        risk_level = "Very High"

    # -----------------------------------------------------
    # 8. BUILD ROUTE RESPONSE
    # -----------------------------------------------------

    route_results = []

    for index, route in enumerate(routes):

        route_results.append({
            "route_number": index + 1,

            "distance": route.get(
                "distance"
            ),

            "distance_text": format_distance(
                route.get("distance", 0)
            ),

            "duration": route.get(
                "duration"
            ),

            "duration_text": format_duration(
                route.get("duration", 0)
            ),

            "geometry": route.get(
                "geometry"
            )
        })

    historical_hazards = load_historical_hazards()
    current_incidents = load_current_incident_hazards()
    route_hazards = historical_hazards + current_incidents
    for route_result in route_results:
        route_result["segment_risk"] = analyze_route_geometry(
            route_result.get("geometry", {}),
            safety_score,
            route_hazards,
        )

    fastest_duration = min(
        (route.get("duration") or 0 for route in route_results),
        default=0,
    )
    for route_result in route_results:
        segments = route_result.get("segment_risk", {}).get("segments", [])
        highest_segment_score = max(
            (segment.get("risk_score", 50) for segment in segments),
            default=50,
        )
        duration = route_result.get("duration") or fastest_duration or 1
        time_penalty = max(0.0, (duration - fastest_duration) / duration) * 30
        route_result["route_risk_score"] = round(highest_segment_score, 1)
        risk_weight = {
            "standard": 0.7,
            "urgent": 0.75,
            "emergency": 0.85,
            "perishable": 0.55,
        }[priority]
        time_weight = 1.0 - risk_weight
        route_result["optimization_score"] = round(
            highest_segment_score * risk_weight + time_penalty * (time_weight / 0.3),
            1,
        )
        route_result["optimization_basis"] = (
            f"{round(risk_weight * 100)}% route risk, "
            f"{round(time_weight * 100)}% travel-time preference for {priority} delivery"
        )

    route_results.sort(key=lambda route: route["optimization_score"])
    recommended_route = route_results[0]
    recommended_segments = recommended_route.get("segment_risk", {}).get("segments", [])
    danger_segments = [
        segment for segment in recommended_segments
        if segment.get("risk_score", 0) >= 50
    ]
    evidence_summary = recommended_route.get("segment_risk", {}).get(
        "evidence_summary", {}
    )
    if evidence_summary.get("current_closure_confirmed"):
        safety_decision = "avoid_verified_incident"
        safety_decision_text = "Avoid this route until the verified incident is cleared."
    elif safety_score < 40 or danger_segments:
        safety_decision = "high_caution"
        safety_decision_text = "Use caution and verify local road conditions before departure."
    else:
        safety_decision = "no_verified_closure"
        safety_decision_text = "No verified closure was found; this is not a guarantee of safe travel."
    recommendation_reason = (
        "Recommended because it has the lowest combined route-risk and "
        "travel-time score among available alternatives."
    )

    ai_message = "Deterministic route analysis returned."
    if ENABLE_AI_EXPLANATION:
        try:
            ai_response = ollama.chat(
                model="qwen2.5:7b",
                messages=[
                    {
                        "role": "user",
                        "content": f"""
You are a route safety assistant.

Start: {request.start}
Destination: {request.destination}

Route information:
{route_results}

Weather:
Start weather: {start_weather}
Destination weather: {destination_weather}

Hazards:
{hazards}

Safety score: {safety_score}
Risk level: {risk_level}

Explain the route safety in simple language.
Mention important hazards, weather concerns, and whether the route is safe.
Give practical advice to the traveller.
"""
                    }
                ]
            )
            ai_message = ai_response["message"]["content"]
        except Exception:
            ai_message = "AI explanation unavailable; deterministic analysis is shown."

    # --------------------------------------------------
    # 9. FINAL RESPONSE
    # --------------------------------------------------

    return {

        "start": {
            "query": request.start,
            "name": start["name"],
            "lat": start["lat"],
            "lon": start["lon"]
        },

        "destination": {
            "query": request.destination,
            "name": destination["name"],
            "lat": destination["lat"],
            "lon": destination["lon"]
        },

        "route": recommended_route,

        "alternative_routes": route_results[1:],

        "route_recommendation": {
            "route_number": recommended_route["route_number"],
            "reason": recommendation_reason,
            "optimization_basis": recommended_route["optimization_basis"],
            "alternatives_considered": len(route_results),
            "cargo_type": cargo_type,
            "priority": priority,
        },
        "safety_decision": {
            "status": safety_decision,
            "message": safety_decision_text,
            "danger_segment_count": len(danger_segments),
            "verified_incident_count": evidence_summary.get(
                "verified_current_incident_count", 0
            ),
            "checked_route_segments": len(recommended_segments),
        },

        "safety_score": safety_score,

        "risk_level": risk_level,

        "hazards": hazards,

        "weather": {
            "start": start_weather,
            "destination": destination_weather
        },

        "ai_explanation": ai_message,

        "message": (
            "Route analyzed using real road routing "
            "and current weather data."
        )
    }


@app.get("/districts/accessibility")
def district_accessibility():
    return get_district_accessibility()