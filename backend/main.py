from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from pathlib import Path
import requests
import math


# =========================================================
# APP SETUP
# =========================================================

app = FastAPI(title="NER-LogixAI API")
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


# =========================================================
# BASIC ENDPOINTS
# =========================================================

@app.get("/")
def home():
    index_file = BASE_DIR / "index.html"

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


@app.get("/geojson")
def geojson():
    if not GEOJSON_FILE.exists():
        raise HTTPException(
            status_code=404,
            detail="India states GeoJSON file not found."
        )

    return FileResponse(GEOJSON_FILE)


# =========================================================
# ROUTE REQUEST MODEL
# =========================================================

class RouteRequest(BaseModel):
    start: str
    destination: str


# =========================================================
# GEOCODING
# =========================================================

def geocode_place(place: str):

    url = "https://nominatim.openstreetmap.org/search"

    params = {
        "q": f"{place}, India",
        "format": "jsonv2",
        "limit": 1,
        "countrycodes": "in"
    }

    headers = {
        "User-Agent": "NER-LogixAI/1.0"
    }

    try:
        response = requests.get(
            url,
            params=params,
            headers=headers,
            timeout=15
        )

        response.raise_for_status()

    except requests.RequestException as error:
        raise HTTPException(
            status_code=502,
            detail=f"Location service unavailable: {error}"
        )

    results = response.json()

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

    # -----------------------------------------------------
    # 9. FINAL RESPONSE
    # -----------------------------------------------------

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

        "route": route_results[0],

        "alternative_routes": route_results[1:],

        "safety_score": safety_score,

        "risk_level": risk_level,

        "hazards": hazards,

        "weather": {
            "start": start_weather,
            "destination": destination_weather
        },

        "message": (
            "Route analyzed using real road routing "
            "and current weather data."
        )
    }