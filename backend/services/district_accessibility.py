from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from typing import Any

from backend.gis.ner_states import NER_STATES
from backend.services.data_status import get_data_status
from backend.services.incident_reports import list_reports
from backend.services.route_risk import load_historical_hazards


def _risk_level(score: float) -> str:
    if score >= 75:
        return "Very High"
    if score >= 50:
        return "High"
    if score >= 25:
        return "Moderate"
    return "Low"


def _state_for_report(report: dict[str, Any], hazards: list[dict[str, Any]]) -> str | None:
    state = report.get("state")
    if state in {item["name"] for item in NER_STATES}:
        return state

    try:
        latitude = float(report["latitude"])
        longitude = float(report["longitude"])
    except (KeyError, TypeError, ValueError):
        return None

    nearest = None
    nearest_distance = float("inf")
    for hazard in hazards:
        if hazard.get("state") is None or hazard.get("latitude") is None:
            continue
        distance = (latitude - hazard["latitude"]) ** 2 + (longitude - hazard["longitude"]) ** 2
        if distance < nearest_distance:
            nearest = hazard["state"]
            nearest_distance = distance
    return nearest


def get_district_accessibility() -> dict[str, Any]:
    hazards = load_historical_hazards()
    reports = list_reports(500)
    historical_counts = Counter(hazard.get("state") for hazard in hazards if hazard.get("state"))
    current_counts = Counter(_state_for_report(report, hazards) for report in reports)
    source_status = get_data_status()["sources"]
    maximum_historical_count = max(historical_counts.values(), default=1)
    results = []

    for state in NER_STATES:
        name = state["name"]
        historical_count = historical_counts.get(name, 0)
        current_count = current_counts.get(name, 0)
        historical_score = min(
            60.0,
            historical_count / maximum_historical_count * 60.0,
        )
        current_score = min(40.0, current_count * 20.0)
        score = min(100.0, historical_score + current_score)
        evidence = []
        if historical_count:
            evidence.append(f"{historical_count} historical hazard records")
        if current_count:
            evidence.append(f"{current_count} current field reports")
        if not evidence:
            evidence.append("No matched hazard or field-report evidence")

        results.append({
            "state": name,
            "state_id": state["id"],
            "accessibility_score": round(max(0.0, 100.0 - score), 1),
            "risk_level": _risk_level(score),
            "historical_hazard_count": historical_count,
            "current_field_report_count": current_count,
            "evidence": evidence,
            "data_quality": "limited" if historical_count == 0 and current_count == 0 else "evidence_available",
            "historical_evidence_only": current_count == 0 and historical_count > 0,
        })

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "region": "North Eastern Region of India",
        "state_count": len(results),
        "sources": {
            "weather": source_status["weather"]["freshness"],
            "rainfall": source_status["rainfall"]["freshness"],
            "flood": source_status["flood"]["freshness"],
            "landslide": source_status["landslide"]["freshness"],
        },
        "warning": "Accessibility is a normalized evidence-based estimate, not an official road-closure registry.",
        "states": results,
    }
