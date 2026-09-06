from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parents[1]
POSITIONS_PATH = BASE_DIR / "data" / "processed" / "vehicle_positions.json"
VALID_CARGO_TYPES = {
    "medicine",
    "food",
    "agricultural_produce",
    "construction_material",
    "emergency_supply",
    "other",
}
VALID_STATUSES = {"en_route", "delayed", "delivered", "stopped", "unknown"}


def _load_positions() -> dict[str, dict[str, Any]]:
    if not POSITIONS_PATH.exists():
        return {}
    try:
        with POSITIONS_PATH.open("r", encoding="utf-8") as file:
            data = json.load(file)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def _save_positions(positions: dict[str, dict[str, Any]]) -> None:
    POSITIONS_PATH.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = POSITIONS_PATH.with_suffix(".tmp")
    with temporary_path.open("w", encoding="utf-8") as file:
        json.dump(positions, file, indent=2, ensure_ascii=False)
    temporary_path.replace(POSITIONS_PATH)


def update_vehicle_position(vehicle_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    vehicle_id = vehicle_id.strip()
    if not vehicle_id:
        raise ValueError("vehicle_id is required")

    try:
        latitude = float(payload["latitude"])
        longitude = float(payload["longitude"])
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError("Valid latitude and longitude are required") from error
    if not -90 <= latitude <= 90 or not -180 <= longitude <= 180:
        raise ValueError("Latitude or longitude is outside valid bounds")

    cargo_type = str(payload.get("cargo_type", "other")).strip().lower()
    status = str(payload.get("status", "unknown")).strip().lower()
    if cargo_type not in VALID_CARGO_TYPES:
        raise ValueError(f"Unsupported cargo type: {cargo_type}")
    if status not in VALID_STATUSES:
        raise ValueError(f"Unsupported vehicle status: {status}")

    position = {
        "vehicle_id": vehicle_id,
        "latitude": latitude,
        "longitude": longitude,
        "cargo_type": cargo_type,
        "cargo_description": str(payload.get("cargo_description", "")).strip(),
        "origin": str(payload.get("origin", "")).strip(),
        "destination": str(payload.get("destination", "")).strip(),
        "status": status,
        "delivery_id": payload.get("delivery_id"),
        "observed_at": payload.get("observed_at") or datetime.now(timezone.utc).isoformat(),
        "received_at": datetime.now(timezone.utc).isoformat(),
        "source": payload.get("source", "gps_device"),
    }
    positions = _load_positions()
    positions[vehicle_id] = position
    _save_positions(positions)
    return position


def list_vehicle_positions() -> list[dict[str, Any]]:
    return list(_load_positions().values())
