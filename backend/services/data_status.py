from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parents[1]
RAW_DIR = BASE_DIR / "data" / "raw"

SOURCE_RULES = {
    "weather": {
        "directory": RAW_DIR / "weather",
        "max_age_minutes": 90,
        "live_capable": True,
    },
    "rainfall": {
        "directory": RAW_DIR / "rainfall",
        "max_age_minutes": 90,
        "live_capable": True,
    },
    "flood": {
        "directory": RAW_DIR / "flood",
        "max_age_minutes": 24 * 60,
        "live_capable": False,
    },
    "landslide": {
        "directory": RAW_DIR / "landslide",
        "max_age_minutes": 24 * 60,
        "live_capable": False,
    },
}


def _parse_timestamp(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None

    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None

    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)

    return parsed.astimezone(timezone.utc)


def _file_timestamp(path: Path) -> datetime | None:
    try:
        with path.open("r", encoding="utf-8") as file:
            data = json.load(file)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None

    if isinstance(data, dict):
        for key in ("observed_at", "collected_at", "updated_at", "timestamp"):
            timestamp = _parse_timestamp(data.get(key))
            if timestamp:
                return timestamp

    try:
        return datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
    except OSError:
        return None


def _source_status(name: str, rule: dict[str, Any], now: datetime) -> dict[str, Any]:
    directory = rule["directory"]
    files = sorted(directory.glob("*.json")) if directory.exists() else []
    timestamps = [timestamp for path in files if (timestamp := _file_timestamp(path))]
    latest = max(timestamps) if timestamps else None
    age_minutes = None

    if latest:
        age_minutes = max(0.0, (now - latest).total_seconds() / 60)

    if not files:
        freshness = "missing"
    elif not rule["live_capable"]:
        freshness = "historical"
    elif latest is None:
        freshness = "unknown"
    elif age_minutes <= rule["max_age_minutes"]:
        freshness = "fresh"
    else:
        freshness = "stale"

    return {
        "name": name,
        "file_count": len(files),
        "latest_timestamp": latest.isoformat() if latest else None,
        "age_minutes": round(age_minutes, 1) if age_minutes is not None else None,
        "freshness": freshness,
        "live_capable": rule["live_capable"],
        "max_age_minutes": rule["max_age_minutes"],
    }


def get_data_status() -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    sources = {
        name: _source_status(name, rule, now)
        for name, rule in SOURCE_RULES.items()
    }

    live_sources = [
        source for source in sources.values() if source["live_capable"]
    ]

    return {
        "generated_at": now.isoformat(),
        "monitoring_interval_minutes": 5,
        "operational_live_sources": all(
            source["freshness"] == "fresh" for source in live_sources
        ),
        "sources": sources,
        "warning": (
            "Historical flood and landslide inventories are evidence, not "
            "live confirmations."
        ),
    }