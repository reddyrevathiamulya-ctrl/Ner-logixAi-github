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
    notify_new_high_severity_alerts(alerts)
 
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "count": len(alerts),
        "alerts": alerts,
    }
# ============================================================
# PUSH NOTIFICATION LAYER — ADDED
# ============================================================
import smtplib
import os
import logging
from email.mime.text import MIMEText

logger = logging.getLogger(__name__)

_already_notified_ids = set()


def send_alert_notification(alert: dict) -> bool:
    smtp_server = os.environ.get("ALERT_SMTP_SERVER")
    smtp_port = os.environ.get("ALERT_SMTP_PORT")
    sender_email = os.environ.get("ALERT_SENDER_EMAIL")
    sender_password = os.environ.get("ALERT_SENDER_PASSWORD")
    recipient_email = os.environ.get("ALERT_RECIPIENT_EMAIL")

    if not all([smtp_server, smtp_port, sender_email, sender_password, recipient_email]):
        logger.warning(
            "Alert email skipped: ALERT_SMTP_* environment variables not set."
        )
        return False

    severity = alert.get("severity", "unknown")
    title = alert.get("title", "NER-LogixAI Alert")
    subject = f"[NER-LogixAI Alert] {severity.upper()}: {title}"

    body_lines = [
        f"Severity: {severity}",
        f"Title: {title}",
        f"Message: {alert.get('message', '')}",
    ]
    if alert.get("evidence"):
        body_lines.append("Evidence:")
        for item in alert["evidence"]:
            body_lines.append(f"  - {item}")
    if alert.get("latitude") is not None and alert.get("longitude") is not None:
        body_lines.append(f"Location: {alert['latitude']}, {alert['longitude']}")
    body_lines.append(f"Created at: {alert.get('created_at', '')}")
    body = "\n".join(body_lines)

    message = MIMEText(body)
    message["Subject"] = subject
    message["From"] = sender_email
    message["To"] = recipient_email

    try:
        with smtplib.SMTP(smtp_server, int(smtp_port)) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, [recipient_email], message.as_string())
        logger.info(f"Alert email sent: {subject}")
        return True
    except Exception as exc:
        logger.error(f"Failed to send alert email: {exc}")
        return False


def notify_new_high_severity_alerts(alerts: list[dict]) -> int:
    sent_count = 0
    for alert in alerts:
        alert_id = alert.get("alert_id")
        severity = (alert.get("severity") or "").lower()

        if alert_id in _already_notified_ids:
            continue
        if severity not in ("high", "critical"):
            continue

        if send_alert_notification(alert):
            _already_notified_ids.add(alert_id)
            sent_count += 1

    return sent_count