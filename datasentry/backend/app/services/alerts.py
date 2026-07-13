from __future__ import annotations

import json
import smtplib
import ssl
import urllib.request
from email.message import EmailMessage
from typing import Any

from app.core.config import settings
from app.db.models import AlertEvent, AlertRule
from app.services import webhooks as webhook_svc


def evaluate(metric_value: float, operator: str, threshold: str) -> bool:
    try:
        t = float(threshold)
    except (TypeError, ValueError):
        return False
    if metric_value is None:
        return False
    if operator == ">=":
        return metric_value >= t
    if operator == "<=":
        return metric_value <= t
    if operator == ">":
        return metric_value > t
    if operator == "<":
        return metric_value < t
    if operator == "==":
        return metric_value == t
    return False


def _send_slack(message: str) -> bool:
    if not settings.SLACK_WEBHOOK_URL:
        return False
    payload = json.dumps({"text": message}).encode("utf-8")
    req = urllib.request.Request(
        settings.SLACK_WEBHOOK_URL, data=payload, headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status == 200
    except Exception:
        return False


def _send_email(message: str, to: str) -> bool:
    if not settings.SMTP_HOST:
        return False
    msg = EmailMessage()
    msg["Subject"] = "DataSentry alert"
    msg["From"] = settings.SMTP_FROM
    msg["To"] = to
    msg.set_content(message)
    ctx = ssl.create_default_context()
    try:
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            server.starttls(context=ctx)
            if settings.SMTP_USER:
                server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.send_message(msg)
        return True
    except Exception:
        return False


def dispatch(rule: AlertRule, message: str, channels: list[str]) -> bool:
    ok = False
    for ch in channels:
        if ch == "slack":
            ok = _send_slack(message) or ok
        elif ch == "email":
            ok = _send_email(message, settings.SMTP_USER or "ops@localhost") or ok
    return ok


def process_scope(db, scope_type: str, scope_id: str, metrics: dict[str, Any]) -> list[AlertEvent]:
    """Evaluate all enabled rules for a scope and fire events that trigger."""
    rules = (
        db.query(AlertRule)
        .filter(
            AlertRule.scope_type == scope_type,
            AlertRule.scope_id == scope_id,
            AlertRule.enabled == "true",
        )
        .all()
    )
    events: list[AlertEvent] = []
    for rule in rules:
        value = metrics.get(rule.metric)
        if value is None:
            continue
        if not evaluate(float(value), rule.operator, rule.threshold):
            continue
        channels = json.loads(rule.channels_json or '["slack"]')
        message = (
            f"[DataSentry] Alert '{rule.name}' ({scope_type}:{scope_id}): "
            f"{rule.metric} = {value} {rule.operator} {rule.threshold}"
        )
        delivered = dispatch(rule, message, channels)
        ev = AlertEvent(
            rule_id=rule.id,
            owner_id=rule.owner_id,
            message=message,
            payload_json=json.dumps(metrics),
            delivered="true" if delivered else "false",
        )
        db.add(ev)
        events.append(ev)
        webhook_svc.fire_event(
            db,
            "alert.triggered",
            {"rule": rule.name, "scope_type": scope_type, "scope_id": scope_id, "message": message, "metrics": metrics},
            owner_id=rule.owner_id,
        )
    db.commit()
    return events
