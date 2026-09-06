from __future__ import annotations

import csv
import json
import logging
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parents[1]
RAW_DIR = BASE_DIR / "data" / "raw"
GIS_DIR = BASE_DIR / "gis"
GEOJSON_PATH = GIS_DIR / "india_states.geojson"

FLOOD_DIR = RAW_DIR / "flood"
LANDSLIDE_DIR = RAW_DIR / "landslide"
WEATHER_DIR = RAW_DIR / "weather"
RAINFALL_DIR = RAW_DIR / "rainfall"

FLOOD_DIR.mkdir(parents=True, exist_ok=True)
LANDSLIDE_DIR.mkdir(parents=True, exist_ok=True)
WEATHER_DIR.mkdir(parents=True, exist_ok=True)
RAINFALL_DIR.mkdir(parents=True, exist_ok=True)

NORTH_EAST_STATES = [
    "Arunachal Pradesh",
    "Assam",
    "Manipur",
    "Meghalaya",
    "Mizoram",
    "Nagaland",
    "Sikkim",
    "Tripura",
]

INDIAN_STATES = NORTH_EAST_STATES

STATE_CENTERS: dict[str, tuple[float, float]] = {
    "Arunachal Pradesh": (28.2180, 94.7278),
    "Assam": (26.2006, 92.9376),
    "Manipur": (24.6637, 93.9063),
    "Meghalaya": (25.4670, 91.3662),
    "Mizoram": (23.1645, 92.9376),
    "Nagaland": (26.1584, 94.5624),
    "Sikkim": (27.5330, 88.5122),
    "Tripura": (23.9408, 91.9882),
}

STATE_SLUGS: dict[str, str] = {
    "Arunachal Pradesh": "arunachal_pradesh",
    "Assam": "assam",
    "Manipur": "manipur",
    "Meghalaya": "meghalaya",
    "Mizoram": "mizoram",
    "Nagaland": "nagaland",
    "Sikkim": "sikkim",
    "Tripura": "tripura",
}

HTTP_SESSION = requests.Session()
HTTP_SESSION.headers.update({
    "User-Agent": "Ner-logixAI-hazard-ingestion/1.0"
})
HTTP_SESSION.mount(
    "https://",
    HTTPAdapter(
        max_retries=Retry(
            total=2,
            connect=2,
            read=2,
            backoff_factor=0.5,
            status_forcelist=(429, 500, 502, 503, 504),
            allowed_methods=frozenset({"GET"}),
        )
    ),
)
CACHE_MAX_AGE_MINUTES = 25


def _save_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    logger.info("Saved %s", path)


def _load_json(path: Path) -> Any:
    if not path.exists():
        return None
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as exc:
        logger.error("Could not read %s: %s", path, exc)
        return None


def _request_json(url: str, params: dict | None = None) -> Any:
    response = HTTP_SESSION.get(
        url,
        params=params,
        timeout=30,
    )
    response.raise_for_status()
    return response.json()


def _load_cached_observations(path: Path) -> list[dict[str, Any]]:
    data = _load_json(path)
    if isinstance(data, dict) and isinstance(data.get("observations"), list):
        return [item for item in data["observations"] if isinstance(item, dict)]
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    return []


def _load_fresh_open_meteo_cache() -> dict[str, list[dict[str, Any]]] | None:
    weather_data = _load_json(WEATHER_DIR / "open_meteo.json")
    rainfall_data = _load_json(RAINFALL_DIR / "open_meteo.json")

    if not isinstance(weather_data, dict) or not isinstance(rainfall_data, dict):
        return None

    collected_at = weather_data.get("collected_at")
    if not isinstance(collected_at, str):
        return None

    try:
        timestamp = datetime.fromisoformat(collected_at.replace("Z", "+00:00"))
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=timezone.utc)
        age_minutes = (
            datetime.now(timezone.utc) - timestamp.astimezone(timezone.utc)
        ).total_seconds() / 60
    except ValueError:
        return None

    if age_minutes < 0 or age_minutes > CACHE_MAX_AGE_MINUTES:
        return None

    return {
        "weather": _load_cached_observations(WEATHER_DIR / "open_meteo.json"),
        "rainfall": _load_cached_observations(RAINFALL_DIR / "open_meteo.json"),
    }

def fetch_open_meteo_data() -> dict[str, list[dict[str, Any]]]:
    """Fetch one batched weather request for all NER state centers."""
    cached = _load_fresh_open_meteo_cache()
    if cached is not None:
        logger.info("Using Open-Meteo cache younger than %d minutes", CACHE_MAX_AGE_MINUTES)
        return cached

    states = list(NORTH_EAST_STATES)
    latitudes = [STATE_CENTERS[state][0] for state in states]
    longitudes = [STATE_CENTERS[state][1] for state in states]

    try:
        data = _request_json(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": ",".join(str(value) for value in latitudes),
                "longitude": ",".join(str(value) for value in longitudes),
                "current": (
                    "temperature_2m,relative_humidity_2m,precipitation,rain,"
                    "weather_code,wind_speed_10m"
                ),
                "hourly": "precipitation,rain,precipitation_probability,weather_code",
                "forecast_days": 2,
                "timezone": "UTC",
            },
        )
    except requests.RequestException as error:
        logger.warning("Open-Meteo unavailable; using cached data: %s", error)
        return {
            "weather": _load_cached_observations(WEATHER_DIR / "open_meteo.json"),
            "rainfall": _load_cached_observations(RAINFALL_DIR / "open_meteo.json"),
        }

    responses = data if isinstance(data, list) else [data]
    collected_at = datetime.now(timezone.utc).isoformat()
    weather_records: list[dict[str, Any]] = []
    rainfall_records: list[dict[str, Any]] = []

    for state, response in zip(states, responses):
        if not isinstance(response, dict):
            continue

        current = response.get("current", {})
        hourly = response.get("hourly", {})
        weather_record = {
            "state": state,
            "source": "Open-Meteo",
            "collected_at": collected_at,
            "observed_at": current.get("time"),
            "latitude": STATE_CENTERS[state][0],
            "longitude": STATE_CENTERS[state][1],
            "current": current,
            "hourly": hourly,
        }
        weather_records.append(weather_record)
        rainfall_records.append({
            "state": state,
            "source": "Open-Meteo",
            "collected_at": collected_at,
            "observed_at": current.get("time"),
            "rainfall": current.get("rain", current.get("precipitation")),
            "hourly": {
                "time": hourly.get("time", []),
                "rain": hourly.get("rain", []),
                "precipitation": hourly.get("precipitation", []),
                "precipitation_probability": hourly.get(
                    "precipitation_probability", []
                ),
            },
        })

    weather_output = {
        "source": "Open-Meteo",
        "collected_at": collected_at,
        "observation_count": len(weather_records),
        "observations": weather_records,
    }
    rainfall_output = {
        "source": "Open-Meteo",
        "collected_at": collected_at,
        "observation_count": len(rainfall_records),
        "observations": rainfall_records,
    }

    _save_json(WEATHER_DIR / "open_meteo.json", weather_output)
    _save_json(RAINFALL_DIR / "open_meteo.json", rainfall_output)

    return {"weather": weather_records, "rainfall": rainfall_records}


def _point_in_poly(x: float, y: float, poly: list[list[float]]) -> bool:
    """Ray casting algorithm to check if point (x=lon, y=lat) is in polygon."""
    n = len(poly)
    inside = False
    if n < 3:
        return False
    p1x, p1y = poly[0]
    for i in range(n + 1):
        p2x, p2y = poly[i % n]
        if y > min(p1y, p2y):
            if y <= max(p1y, p2y):
                if x <= max(p1x, p2x):
                    if p1y != p2y:
                        xinters = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                    if p1x == p2x or x <= xinters:
                        inside = not inside
        p1x, p1y = p2x, p2y
    return inside


def map_coordinates_to_ner_state(lat: float, lon: float) -> str:
    """
    Map latitude and longitude coordinates to an NER state using
    india_states.geojson polygons, falling back to nearest state centroid.
    """
    if GEOJSON_PATH.exists():
        try:
            with open(GEOJSON_PATH, "r", encoding="utf-8") as f:
                geojson = json.load(f)
            for feat in geojson.get("features", []):
                st = feat.get("properties", {}).get("ST_NM")
                if st in NORTH_EAST_STATES:
                    geom = feat.get("geometry", {})
                    gtype = geom.get("type")
                    coords = geom.get("coordinates", [])
                    if gtype == "Polygon":
                        for ring in coords:
                            if _point_in_poly(lon, lat, ring):
                                return st
                    elif gtype == "MultiPolygon":
                        for poly in coords:
                            for ring in poly:
                                if _point_in_poly(lon, lat, ring):
                                    return st
        except Exception as exc:
            logger.warning("Error reading geojson for coordinate mapping: %s", exc)

    # Fallback to nearest Northeast state centroid
    nearest_state = "Assam"
    min_dist = float("inf")
    for state, (c_lat, c_lon) in STATE_CENTERS.items():
        dist = (lat - c_lat) ** 2 + (lon - c_lon) ** 2
        if dist < min_dist:
            min_dist = dist
            nearest_state = state
    return nearest_state


# ============================================================
# FLOOD DATA INGESTION
# ============================================================

def fetch_flood_data() -> list[dict]:
    """
    Ingest flood observations from India_Flood_Inventory_v3.csv,
    filter and attribute records to the 8 North-Eastern states,
    and save both master and per-state observation JSON files.
    """
    csv_path = FLOOD_DIR / "India_Flood_Inventory_v3.csv"
    normalized: list[dict] = []

    if csv_path.exists():
        try:
            with open(csv_path, "r", encoding="utf-8-sig", newline="") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    state_raw = row.get("State", "")
                    if not state_raw:
                        continue

                    # Check for matching NER states in the row
                    matched_states = []
                    for ner_state in NORTH_EAST_STATES:
                        if ner_state.lower() in state_raw.lower():
                            matched_states.append(ner_state)

                    if not matched_states:
                        continue

                    # Parse numerical fields
                    fatalities = 0.0
                    try:
                        fat_val = row.get("Human fatality", "")
                        if fat_val and fat_val.strip():
                            fatalities = float(fat_val.strip().replace(",", ""))
                    except (ValueError, TypeError):
                        pass

                    duration = 0.0
                    try:
                        dur_val = row.get("Duration(Days)", "")
                        if dur_val and dur_val.strip():
                            duration = float(dur_val.strip().replace(",", ""))
                    except (ValueError, TypeError):
                        pass

                    # Compute transparent hazard severity (scale 1.0 - 4.0)
                    if fatalities >= 10:
                        severity = 4.0
                    elif fatalities >= 1:
                        severity = 3.0
                    elif duration >= 7:
                        severity = 2.0
                    else:
                        severity = 1.0

                    flood_score = min(severity * 25.0, 100.0)

                    lat = None
                    lon = None
                    try:
                        if row.get("Latitude"):
                            lat = float(row["Latitude"])
                        if row.get("Longitude"):
                            lon = float(row["Longitude"])
                    except (ValueError, TypeError):
                        pass

                    for st in matched_states:
                        record = {
                            "hazard_type": "flood",
                            "source": "India Flood Inventory",
                            "event_id": row.get("UEI"),
                            "event_date": row.get("Start Date"),
                            "end_date": row.get("End Date"),
                            "duration_days": duration,
                            "state": st,
                            "district": row.get("Districts"),
                            "location": row.get("Location"),
                            "severity": severity,
                            "flood_score": flood_score,
                            "fatalities": fatalities,
                            "human_fatality": fatalities,
                            "area_affected": row.get("Area Affected"),
                            "damage": row.get("Extent of damage "),
                            "description": row.get("Description of Casualties/injured"),
                            "latitude": lat,
                            "longitude": lon,
                            "coordinate_available": lat is not None and lon is not None,
                            "raw": {k: v for k, v in row.items() if v},
                        }
                        normalized.append(record)

            logger.info("Parsed %d flood records from CSV", len(normalized))
        except Exception as exc:
            logger.error("Error parsing flood CSV: %s", exc)

    # Fallback to existing JSON if CSV not found or returned empty
    if not normalized:
        json_path = FLOOD_DIR / "flood_observations.json"
        data = _load_json(json_path)
        if isinstance(data, dict):
            normalized = data.get("observations", [])
        elif isinstance(data, list):
            normalized = data

    # Save master observation JSON
    now = datetime.now(timezone.utc).isoformat()
    master_output = {
        "hazard_type": "flood",
        "source": "India Flood Inventory",
        "collected_at": now,
        "observation_count": len(normalized),
        "observations": normalized,
    }
    _save_json(FLOOD_DIR / "flood_observations.json", master_output)
    _save_json(FLOOD_DIR / "flood_normalized.json", master_output)

    # Also save per-state JSON files to mirror rainfall/ structure
    for st in NORTH_EAST_STATES:
        slug = STATE_SLUGS.get(st, st.lower().replace(" ", "_"))
        st_records = [r for r in normalized if r.get("state") == st]
        state_output = {
            "hazard_type": "flood",
            "source": "India Flood Inventory",
            "state": st,
            "observation_count": len(st_records),
            "observations": st_records,
            "average_severity": round(sum(r["severity"] for r in st_records) / len(st_records), 2) if st_records else 0.0,
            "total_fatalities": sum(r["fatalities"] for r in st_records),
        }
        _save_json(FLOOD_DIR / f"{slug}.json", state_output)

    return normalized


# ============================================================
# LANDSLIDE DATA INGESTION
# ============================================================

def fetch_landslide_data() -> list[dict]:
    """
    Ingest landslide observations from nasa_landslide_catalog.csv,
    spatially map coordinates to North-Eastern states,
    and save both master and per-state observation JSON files.
    """
    csv_path = LANDSLIDE_DIR / "nasa_landslide_catalog.csv"
    normalized: list[dict] = []

    size_map = {
        "small": 1.0,
        "medium": 2.0,
        "large": 3.0,
        "very_large": 4.0,
        "very large": 4.0,
    }

    if csv_path.exists():
        try:
            with open(csv_path, "r", encoding="utf-8-sig", newline="") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    lat_raw = row.get("latitude")
                    lon_raw = row.get("longitude")
                    if not lat_raw or not lon_raw:
                        continue

                    lat = float(lat_raw)
                    lon = float(lon_raw)
                    state = map_coordinates_to_ner_state(lat, lon)

                    size_str = (row.get("landslide_size") or "").strip().lower()
                    base_severity = size_map.get(size_str, 2.0)

                    fatalities = 0.0
                    try:
                        fat_val = row.get("fatality_count", "0")
                        if fat_val and fat_val.strip():
                            fatalities = float(fat_val.strip())
                    except (ValueError, TypeError):
                        pass

                    # Severity adjusted by fatality impact (scale 1.0 - 4.0)
                    severity = min(base_severity + (1.0 if fatalities > 0 else 0.0), 4.0)
                    landslide_score = min(severity * 25.0, 100.0)

                    record = {
                        "hazard_type": "landslide",
                        "source": "NASA Global Landslide Catalog",
                        "event_id": row.get("event_id"),
                        "event_date": row.get("event_date"),
                        "state": state,
                        "latitude": lat,
                        "longitude": lon,
                        "landslide_size": size_str,
                        "severity": severity,
                        "landslide_score": landslide_score,
                        "trigger": row.get("landslide_trigger"),
                        "fatalities": fatalities,
                        "fatality_count": fatalities,
                        "raw": row,
                    }
                    normalized.append(record)

            logger.info("Parsed %d landslide records from CSV", len(normalized))
        except Exception as exc:
            logger.error("Error parsing landslide CSV: %s", exc)

    # Fallback to existing JSON if CSV not found or empty
    if not normalized:
        json_path = LANDSLIDE_DIR / "landslide_observations.json"
        data = _load_json(json_path)
        if isinstance(data, dict):
            normalized = data.get("observations", [])
        elif isinstance(data, list):
            normalized = data

    # Save master observation JSON
    now = datetime.now(timezone.utc).isoformat()
    master_output = {
        "hazard_type": "landslide",
        "source": "NASA Global Landslide Catalog",
        "collected_at": now,
        "observation_count": len(normalized),
        "observations": normalized,
    }
    _save_json(LANDSLIDE_DIR / "landslide_observations.json", master_output)
    _save_json(LANDSLIDE_DIR / "landslide_normalized.json", master_output)

    # Also save per-state JSON files to mirror rainfall/ structure
    for st in NORTH_EAST_STATES:
        slug = STATE_SLUGS.get(st, st.lower().replace(" ", "_"))
        st_records = [r for r in normalized if r.get("state") == st]
        state_output = {
            "hazard_type": "landslide",
            "source": "NASA Global Landslide Catalog",
            "state": st,
            "observation_count": len(st_records),
            "observations": st_records,
            "average_severity": round(sum(r["severity"] for r in st_records) / len(st_records), 2) if st_records else 0.0,
            "total_fatalities": sum(r["fatalities"] for r in st_records),
        }
        _save_json(LANDSLIDE_DIR / f"{slug}.json", state_output)

    return normalized


# ============================================================
# MAIN HAZARD COLLECTION
# ============================================================

def collect_hazard_data() -> dict[str, Any]:
    """
    Collect flood and landslide data from local datasets.
    """
    now = datetime.now(timezone.utc).isoformat()

    flood = fetch_flood_data()
    landslide = fetch_landslide_data()
    weather_data = fetch_open_meteo_data()

    flood_output = {
        "hazard_type": "flood",
        "source": "India Flood Inventory",
        "collected_at": now,
        "observation_count": len(flood),
        "observations": flood,
    }

    landslide_output = {
        "hazard_type": "landslide",
        "source": "NASA Global Landslide Catalog",
        "collected_at": now,
        "observation_count": len(landslide),
        "observations": landslide,
    }

    return {
        "flood": flood_output,
        "landslide": landslide_output,
        "weather": weather_data["weather"],
        "rainfall": weather_data["rainfall"],
    }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    result = collect_hazard_data()

    print()
    print("=" * 70)
    print("LOCAL HAZARD DATA INTEGRATION")
    print("=" * 70)

    print("Flood records:", result["flood"]["observation_count"])
    print("Landslide records:", result["landslide"]["observation_count"])
    print("=" * 70)
