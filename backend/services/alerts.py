from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from backend.services.data_status import get_data_status
from backend.services.incident_reports import list_reports


def _alert(
    alert_type: str,
    severity: str,
    title: str,
    message: str,
    evidence: list[str],
    latitude: float | None = None,
    longitude: float | None = None,
) -> dict[str, Any]:
    return {
        "alert_id": f"{alert_type}-{int(datetime.now(timezone.utc).timestamp())}",
        "alert_type": alert_type,
        "severity": severity,
        "title": title,
        "message": message,
        "evidence": evidence,
        "latitude": latitude,
        "longitude": longitude,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": "active",
    }


def get_active_alerts() -> dict[str, Any]:
    alerts: list[dict[str, Any]] = []
    status = get_data_status()

    for source_name, source in status["sources"].items():
        if source["freshness"] == "stale" and source["live_capable"]:
            alerts.append(_alert(
                "stale_source",
                "moderate",
                f"{source_name.title()} data is stale",
                f"The latest {source_name} data is older than its configured freshness window.",
                [
                    f"Last update age: {source['age_minutes']} minutes",
                    f"Allowed age: {source['max_age_minutes']} minutes",
                ],
            ))

    for report in list_reports(500):
        if report.get("status") == "rejected":
            continue
        severity = report.get("severity", "moderate")
        if severity not in {"high", "critical"}:
            continue
        verification = report.get("status", "unverified")
        alerts.append(_alert(
            "field_incident",
            severity,
            f"{report.get('incident_type', 'Incident').replace('_', ' ').title()} reported",
            report.get("description") or "A high-severity field incident was reported nearby.",
            [
                f"Field report status: {verification}",
                f"Reported at: {report.get('reported_at')}",
            ],
            report.get("latitude"),
            report.get("longitude"),
        ))

    severity_order = {"critical": 4, "high": 3, "moderate": 2, "low": 1}
    alerts.sort(key=lambda item: severity_order.get(item["severity"], 0), reverse=True)
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "count": len(alerts),
        "alerts": alerts,
    }
