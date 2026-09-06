from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4


BASE_DIR = Path(__file__).resolve().parents[1]
REPORTS_PATH = BASE_DIR / "data" / "processed" / "field_reports.json"
PHOTO_DIR = BASE_DIR / "data" / "processed" / "field_report_photos"
MAX_PHOTO_BYTES = 8 * 1024 * 1024
ALLOWED_PHOTO_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}
VALID_INCIDENT_TYPES = {
    "blocked_road",
    "landslide",
    "rockfall",
    "boulder",
    "rock_debris",
    "flood",
    "bridge_damage",
    "road_damage",
    "traffic",
    "other",
}
VALID_SEVERITIES = {"low", "moderate", "high", "critical"}


def _load_reports() -> list[dict[str, Any]]:
    if not REPORTS_PATH.exists():
        return []
    try:
        with REPORTS_PATH.open("r", encoding="utf-8") as file:
            data = json.load(file)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return []
    return data if isinstance(data, list) else []


def _save_reports(reports: list[dict[str, Any]]) -> None:
    REPORTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = REPORTS_PATH.with_suffix(".tmp")
    with temporary_path.open("w", encoding="utf-8") as file:
        json.dump(reports, file, indent=2, ensure_ascii=False)
    temporary_path.replace(REPORTS_PATH)


def create_report(report: dict[str, Any]) -> dict[str, Any]:
    incident_type = str(report.get("incident_type", "")).strip().lower()
    severity = str(report.get("severity", "")).strip().lower()
    latitude = float(report["latitude"])
    longitude = float(report["longitude"])

    if incident_type not in VALID_INCIDENT_TYPES:
        raise ValueError(f"Unsupported incident type: {incident_type}")
    if severity not in VALID_SEVERITIES:
        raise ValueError(f"Unsupported severity: {severity}")
    if not -90 <= latitude <= 90 or not -180 <= longitude <= 180:
        raise ValueError("Latitude or longitude is outside valid bounds")

    now = datetime.now(timezone.utc).isoformat()
    normalized = {
        "report_id": str(uuid4()),
        "offline_id": report.get("offline_id"),
        "incident_type": incident_type,
        "severity": severity,
        "latitude": latitude,
        "longitude": longitude,
        "description": str(report.get("description", "")).strip(),
        "photo_url": report.get("photo_url"),
        "reported_at": report.get("reported_at") or now,
        "received_at": now,
        "source": report.get("source", "field_app"),
        "status": "unverified",
    }
    reports = _load_reports()
    offline_id = report.get("offline_id")
    if offline_id:
        for existing in reports:
            if existing.get("offline_id") == offline_id:
                return existing
    reports.append(normalized)
    _save_reports(reports)
    return normalized


def list_reports(limit: int = 100) -> list[dict[str, Any]]:
    reports = _load_reports()
    return reports[-max(1, min(limit, 500)):][::-1]


def save_photo(content: bytes, content_type: str | None) -> str:
    suffix = ALLOWED_PHOTO_TYPES.get(content_type or "")
    if suffix is None:
        raise ValueError("Only JPEG, PNG, and WebP photos are supported")
    if len(content) > MAX_PHOTO_BYTES:
        raise ValueError("Photo must be 8 MB or smaller")
    if not content:
        raise ValueError("Photo cannot be empty")

    PHOTO_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"{uuid4()}{suffix}"
    path = PHOTO_DIR / filename
    with path.open("wb") as file:
        file.write(content)
    return filename


def verify_report(report_id: str, status: str) -> dict[str, Any]:
    if status not in {"verified", "rejected"}:
        raise ValueError("Status must be verified or rejected")

    reports = _load_reports()
    for report in reports:
        if report.get("report_id") == report_id:
            report["status"] = status
            report["reviewed_at"] = datetime.now(timezone.utc).isoformat()
            _save_reports(reports)
            return report

    raise LookupError("Incident report not found")
