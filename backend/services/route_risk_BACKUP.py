from __future__ import annotations

import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests

from backend.services.incident_reports import list_reports


BASE_DIR = Path(__file__).resolve().parents[1]
RAW_DIR = BASE_DIR / "data" / "raw"
HAZARD_RADIUS_KM = 15.0
MAX_SEGMENTS = 24
ELEVATION_URL = "https://api.open-meteo.com/v1/elevation"


def _haversine_km(first: list[float], second: list[float]) -> float:
    latitude_one, longitude_one = math.radians(first[1]), math.radians(first[0])
    latitude_two, longitude_two = math.radians(second[1]), math.radians(second[0])
    delta_latitude = latitude_two - latitude_one
    delta_longitude = longitude_two - longitude_one
    value = (
        math.sin(delta_latitude / 2) ** 2
        + math.cos(latitude_one)
        * math.cos(latitude_two)
        * math.sin(delta_longitude / 2) ** 2
    )
    return 6371.0 * 2 * math.asin(math.sqrt(value))


def _load_observations(path: Path) -> list[dict[str, Any]]:
    try:
        with path.open("r", encoding="utf-8") as file:
            data = json.load(file)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return []

    observations = data.get("observations", []) if isinstance(data, dict) else data
    if not isinstance(observations, list):
        return []

    return [item for item in observations if isinstance(item, dict)]


def load_historical_hazards() -> list[dict[str, Any]]:
    hazards = []
    for hazard_type in ("flood", "landslide"):
        path = RAW_DIR / hazard_type / f"{hazard_type}_observations.json"
        for observation in _load_observations(path):
            latitude = observation.get("latitude")
            longitude = observation.get("longitude")
            try:
                latitude = float(latitude) if latitude is not None else None
                longitude = float(longitude) if longitude is not None else None
            except (TypeError, ValueError):
                latitude = None
                longitude = None
            if hazard_type == "landslide" and (latitude is None or longitude is None):
                continue
            hazards.append({
                "hazard_type": hazard_type,
                "latitude": latitude,
                "longitude": longitude,
                "event_date": observation.get("event_date"),
                "severity": observation.get("severity", 1),
                "district": observation.get("district"),
                "state": observation.get("state"),
                "resolution": "point",
            })
            if latitude is None or longitude is None:
                hazards[-1]["resolution"] = "district_or_state"
    return hazards


def load_current_incident_hazards() -> list[dict[str, Any]]:
    hazards = []
    severity_scores = {"low": 1, "moderate": 2, "high": 3, "critical": 4}
    for report in list_reports(500):
        try:
            latitude = float(report["latitude"])
            longitude = float(report["longitude"])
        except (KeyError, TypeError, ValueError):
            continue
        hazards.append({
            "hazard_type": report.get("incident_type", "other"),
            "latitude": latitude,
            "longitude": longitude,
            "event_date": report.get("reported_at"),
            "severity": severity_scores.get(report.get("severity"), 1),
            "is_current": True,
            "verification_status": report.get("status", "unverified"),
        })
    return hazards


def _sample_geometry(geometry: dict[str, Any]) -> list[list[float]]:
    coordinates = geometry.get("coordinates", []) if isinstance(geometry, dict) else []
    if geometry.get("type") != "LineString" or len(coordinates) < 2:
        return []

    step = max(1, math.ceil((len(coordinates) - 1) / MAX_SEGMENTS))
    sampled = coordinates[::step]
    if sampled[-1] != coordinates[-1]:
        sampled.append(coordinates[-1])
    return sampled


def _risk_level(score: float) -> str:
    if score >= 75:
        return "Very High"
    if score >= 50:
        return "High"
    if score >= 25:
        return "Moderate"
    return "Low"


def _fetch_elevations(points: list[list[float]]) -> list[float | None]:
    try:
        response = requests.get(
            ELEVATION_URL,
            params={
                "latitude": ",".join(str(point[1]) for point in points),
                "longitude": ",".join(str(point[0]) for point in points),
            },
            timeout=10,
            headers={"User-Agent": "Ner-logixAI-route-risk/1.0"},
        )
        response.raise_for_status()
        elevations = response.json().get("elevation", [])
        if not isinstance(elevations, list):
            return [None] * len(points)
        return [
            float(value) if value is not None else None
            for value in elevations[:len(points)]
        ] + [None] * max(0, len(points) - len(elevations))
    except (requests.RequestException, TypeError, ValueError, KeyError):
        return [None] * len(points)


def _terrain_score(elevation_one: float | None, elevation_two: float | None, distance_km: float) -> tuple[float, float | None]:
    if elevation_one is None or elevation_two is None or distance_km <= 0:
        return 0.0, None

    slope_percent = abs(elevation_two - elevation_one) / (distance_km * 1000) * 100
    if slope_percent >= 20:
        return 100.0, slope_percent
    if slope_percent >= 12:
        return 75.0, slope_percent
    if slope_percent >= 6:
        return 45.0, slope_percent
    if slope_percent >= 3:
        return 20.0, slope_percent
    return 0.0, slope_percent


def _local_terrain_profile(
    latitude: float,
    longitude: float,
) -> tuple[float | None, float | None, float | None]:
    """Estimate local relief from a small elevation neighborhood.

    Relief is a screening signal for steep terrain; it is not a geological
    diagnosis and cannot identify a loose individual boulder.
    """
    offsets = (-0.005, 0.0, 0.005)
    points = [
        [longitude + longitude_offset, latitude + latitude_offset]
        for latitude_offset in offsets
        for longitude_offset in offsets
    ]
    elevations = _fetch_elevations(points)
    usable = [value for value in elevations if value is not None]
    if not usable:
        return None, None, None

    center_index = 4
    center_elevation = elevations[center_index]
    relief = max(usable) - min(usable)
    if center_elevation is None:
        center_elevation = sum(usable) / len(usable)
    return center_elevation, relief, max(usable) - center_elevation


def _relief_score(relief_m: float | None) -> float:
    if relief_m is None:
        return 0.0
    if relief_m >= 250:
        return 100.0
    if relief_m >= 150:
        return 75.0
    if relief_m >= 75:
        return 50.0
    if relief_m >= 30:
        return 25.0
    return 0.0


def _event_weight(event_date: Any) -> float:
    if not isinstance(event_date, str):
        return 0.5
    for format_string in ("%Y-%m-%d", "%d-%m-%Y %H:%M", "%d-%m-%Y"):
        try:
            event = datetime.strptime(event_date[:16], format_string).replace(tzinfo=timezone.utc)
            age_years = max(0.0, (datetime.now(timezone.utc) - event).days / 365.25)
            return max(0.2, math.exp(-age_years / 18.0))
        except ValueError:
            continue
    return 0.5


def _matches_text(hazard: dict[str, Any], location_text: str) -> bool:
    normalized = " ".join(location_text.lower().replace(",", " ").split())
    values = [hazard.get("district"), hazard.get("state")]
    return any(
        isinstance(value, str)
        and " ".join(value.lower().replace(",", " ").split()) in normalized
        for value in values
        if value
    )


def _match_resolution(hazard: dict[str, Any], location_text: str) -> str | None:
    normalized = " ".join(location_text.lower().replace(",", " ").split())
    district = hazard.get("district")
    if isinstance(district, str) and district.strip().lower() in normalized:
        return "district"
    state = hazard.get("state")
    if isinstance(state, str) and state.strip().lower() in normalized:
        return "state"
    return None


def _coverage_summary(hazards: list[dict[str, Any]]) -> dict[str, Any]:
    dates = []
    for hazard in hazards:
        value = hazard.get("event_date")
        if isinstance(value, str) and value:
            dates.append(value)
    return {
        "catalog_record_count": len(hazards),
        "point_record_count": sum(
            1 for hazard in hazards if hazard.get("resolution") == "point"
        ),
        "district_or_state_record_count": sum(
            1 for hazard in hazards if hazard.get("resolution") == "district_or_state"
        ),
        "event_date_start": min(dates) if dates else None,
        "event_date_end": max(dates) if dates else None,
    }


def analyze_location(
    latitude: float,
    longitude: float,
    weather_safety_score: float,
    hazards: list[dict[str, Any]],
    location_text: str = "",
) -> dict[str, Any]:
    """Build an evidence-based risk profile for one map location.

    Boulder/rockfall is a terrain and nearby-hazard susceptibility proxy; it
    is not a confirmed object detection.
    """
    point = [longitude, latitude]
    nearby = [
        hazard for hazard in hazards
        if hazard.get("latitude") is not None
        and hazard.get("longitude") is not None
        and _haversine_km(point, [hazard["longitude"], hazard["latitude"]])
        <= HAZARD_RADIUS_KM
    ]
    district_matches = [
        hazard for hazard in hazards
        if hazard.get("resolution") == "district_or_state"
        and _matches_text(hazard, location_text)
    ]
    district_level_matches = [
        hazard for hazard in district_matches
        if _match_resolution(hazard, location_text) == "district"
    ]
    state_level_matches = [
        hazard for hazard in district_matches
        if _match_resolution(hazard, location_text) == "state"
    ]
    nearby.extend(district_matches)
    elevation, local_relief_m, upslope_relief_m = _local_terrain_profile(
        latitude,
        longitude,
    )
    current = [hazard for hazard in nearby if hazard.get("is_current")]
    historical = [hazard for hazard in nearby if not hazard.get("is_current")]
    landslide_records = [
        hazard for hazard in nearby
        if hazard.get("hazard_type") == "landslide"
    ]
    flood_records = [
        hazard for hazard in nearby if hazard.get("hazard_type") == "flood"
    ]
    rock_records = [
        hazard for hazard in nearby
        if hazard.get("hazard_type") in {"landslide", "rockfall", "boulder"}
    ]
    terrain_relief_score = _relief_score(local_relief_m)
    historical_rock_score = min(100.0, len(rock_records) * 15.0)
    landslide_score = min(
        100.0,
        sum(15.0 * _event_weight(record.get("event_date")) for record in landslide_records),
    )
    flood_score = min(
        100.0,
        sum(15.0 * _event_weight(record.get("event_date")) for record in flood_records),
    )
    incident_score = min(100.0, len(current) * 25.0)
    weather_score = max(0.0, min(100.0, 100.0 - weather_safety_score))
    boulder_score = min(
        100.0,
        terrain_relief_score * 0.45
        + historical_rock_score * 0.35
        + weather_score * 0.2,
    )
    overall_score = min(
        100.0,
        landslide_score * 0.3
        + flood_score * 0.2
        + boulder_score * 0.2
        + incident_score * 0.2
        + weather_score * 0.1,
    )
    evidence = []
    warnings = []
    if weather_score > 0:
        evidence.append("Current weather conditions")
    if landslide_records:
        evidence.append("Historical landslide evidence within 15 km")
    if flood_records:
        evidence.append("Historical flood evidence within 15 km")
    if district_level_matches:
        evidence.append("District-level historical flood evidence matched by place text")
    if state_level_matches:
        evidence.append("State-level historical flood evidence matched by place text")
    if current:
        evidence.append("Current field reports within 15 km")
    if elevation is not None:
        evidence.append("Open-Meteo local elevation neighborhood available")
    else:
        warnings.append("Elevation data unavailable; terrain confidence is reduced")
    if not landslide_records:
        warnings.append("No nearby historical landslide record was found")
    warnings.append(
        "Boulder risk is a terrain susceptibility estimate, not live object detection"
    )

    point_records = [r for r in nearby if r.get("resolution") == "point"]
    evidence_confidence = min(0.40, len(nearby) * 0.06)
    evidence_confidence += 0.10 if point_records else 0
    evidence_confidence += 0.05 if len(current) > 0 else 0

    screening_confidence = 0.0
    screening_confidence += 0.05 if elevation is not None else 0
    screening_confidence += 0.05 if weather_safety_score is not None else 0

    confidence = 0.03 + evidence_confidence + screening_confidence
    confidence = min(confidence, 0.90)


    return {
        "location": {"latitude": latitude, "longitude": longitude},
        "overall_score": round(overall_score, 1),
        "overall_risk": _risk_level(overall_score),
        "confidence": round(min(confidence, 0.95), 2),
        "elevation_m": round(elevation, 1) if elevation is not None else None,
        "terrain": {
            "local_relief_m": round(local_relief_m, 1) if local_relief_m is not None else None,
            "upslope_relief_m": round(upslope_relief_m, 1) if upslope_relief_m is not None else None,
            "screening_method": "3x3 elevation neighborhood",
        },
        "risks": {
            "landslide": {"score": round(landslide_score, 1), "risk": _risk_level(landslide_score)},
            "boulder_or_rockfall": {"score": round(boulder_score, 1), "risk": _risk_level(boulder_score)},
            "flood": {"score": round(flood_score, 1), "risk": _risk_level(flood_score)},
            "current_incident": {"score": round(incident_score, 1), "risk": _risk_level(incident_score)},
        },
        "nearby_evidence_count": len(nearby),
        "current_incident_count": len(current),
        "historical_evidence_count": len(historical),
        "district_level_evidence_count": len(district_matches),
        "district_match_count": len(district_level_matches),
        "state_match_count": len(state_level_matches),
        "data_coverage": _coverage_summary(hazards),
        "evidence": evidence,
        "warnings": warnings,
        "last_evaluated_at": datetime.now(timezone.utc).isoformat(),
    }


def analyze_route_geometry(
    geometry: dict[str, Any],
    weather_safety_score: float,
    hazards: list[dict[str, Any]],
) -> dict[str, Any]:
    points = _sample_geometry(geometry)
    if len(points) < 2:
        return {
            "available": False,
            "segments": [],
            "message": "Route geometry is unavailable for segment analysis.",
        }

    elevations = _fetch_elevations(points)
    segments = []
    for index in range(len(points) - 1):
        start = points[index]
        end = points[index + 1]
        midpoint = [(start[0] + end[0]) / 2, (start[1] + end[1]) / 2]
        nearby = [
            hazard for hazard in hazards
            if hazard.get("latitude") is not None
            and hazard.get("longitude") is not None
            and _haversine_km(midpoint, [hazard["longitude"], hazard["latitude"]])
            <= HAZARD_RADIUS_KM
        ]
        hazard_types = sorted({hazard["hazard_type"] for hazard in nearby})
        current_hazards = [
            hazard for hazard in nearby if hazard.get("is_current")
        ]
        current_count = len(current_hazards)
        verified_current_count = sum(
            1 for hazard in current_hazards
            if hazard.get("verification_status") == "verified"
        )
        historical_count = len(nearby) - current_count
        historical_score = min(60.0, historical_count * 10.0)
        current_score = min(
            80.0,
            sum(
                20.0
                if hazard.get("verification_status") == "verified"
                else 10.0
                for hazard in current_hazards
            ),
        )
        weather_score = max(0.0, min(100.0, 100.0 - weather_safety_score))
        distance_km = _haversine_km(start, end)
        terrain_score, slope_percent = _terrain_score(
            elevations[index], elevations[index + 1], distance_km
        )
        score = min(
            100.0,
            min(100.0, historical_score + current_score) * 0.5
            + weather_score * 0.3
            + terrain_score * 0.2,
        )
        evidence = ["Endpoint weather conditions applied"]
        if "flood" in hazard_types:
            evidence.append("Historical flood evidence within 15 km")
        if "landslide" in hazard_types:
            evidence.append("Historical landslide evidence within 15 km")
        if current_count:
            evidence.append("Current field incident report within 15 km")
        if any(
            hazard.get("verification_status") != "verified"
            for hazard in current_hazards
        ):
            evidence.append("Some field reports are unverified")
        if slope_percent is not None and slope_percent >= 6:
            evidence.append("Steep elevation change on segment")

        segments.append({
            "segment_number": index + 1,
            "start": {"longitude": start[0], "latitude": start[1]},
            "end": {"longitude": end[0], "latitude": end[1]},
            "distance_km": round(distance_km, 2),
            "risk_score": round(score, 1),
            "risk_level": _risk_level(score),
            "historical_hazard_count": len(nearby),
            "current_incident_count": current_count,
            "verified_current_incident_count": verified_current_count,
            "slope_percent": round(slope_percent, 2) if slope_percent is not None else None,
            "terrain_data_available": slope_percent is not None,
            "evidence": evidence,
        })

    highest_risk = max(segments, key=lambda segment: segment["risk_score"])
    return {
        "available": True,
        "segment_count": len(segments),
        "highest_risk": highest_risk,
        "segments": segments,
        "terrain_source": "Open-Meteo elevation",
        "evidence_summary": {
            "historical_hazard_count": sum(
                segment["historical_hazard_count"] for segment in segments
            ),
            "current_incident_count": sum(
                segment["current_incident_count"] for segment in segments
            ),
            "verified_current_incident_count": sum(
                segment["verified_current_incident_count"]
                for segment in segments
            ),
            "current_closure_confirmed": any(
                segment["verified_current_incident_count"] > 0
                for segment in segments
            ),
        },
        "data_note": (
            "Flood and landslide evidence is historical. It indicates "
            "susceptibility and does not confirm a current closure."
        ),
    }
