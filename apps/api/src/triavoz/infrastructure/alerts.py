"""Alert delivery hooks. Logging is always on; e-mail is opt-in via SMTP settings."""

from __future__ import annotations

import asyncio
import json
import logging
import smtplib
from email.message import EmailMessage
from typing import Any
from uuid import UUID

from triavoz.application.abuse.alerts import AlertService
from triavoz.config import Settings, get_settings
from triavoz.infrastructure.rate_limit.gate_store import get_gate_store

log = logging.getLogger("triavoz.alerts")


class LoggingAlertNotifier:
    async def notify(self, kind: str, clinic_id: UUID, payload: dict[str, Any]) -> None:
        # Never include caller numbers: only clinic + counters.
        log.warning("abuse_alert kind=%s clinic=%s payload=%s", kind, clinic_id, payload)


class EmailAlertNotifier:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    async def notify(self, kind: str, clinic_id: UUID, payload: dict[str, Any]) -> None:
        if not (self._settings.smtp_host and self._settings.alerts_email):
            return
        await asyncio.to_thread(self._send, kind, clinic_id, payload)

    def _send(self, kind: str, clinic_id: UUID, payload: dict[str, Any]) -> None:
        s = self._settings
        message = EmailMessage()
        message["Subject"] = f"[TriaVoz] {kind} spike alert"
        message["From"] = s.smtp_from or s.smtp_username or "alerts@triavoz.local"
        message["To"] = s.alerts_email or ""
        message.set_content(
            json.dumps({"clinic_id": str(clinic_id), **payload}, ensure_ascii=False, indent=2)
        )
        try:
            with smtplib.SMTP(s.smtp_host or "", s.smtp_port, timeout=10) as smtp:
                if s.smtp_starttls:
                    smtp.starttls()
                if s.smtp_username and s.smtp_password:
                    smtp.login(s.smtp_username, s.smtp_password.get_secret_value())
                smtp.send_message(message)
        except (OSError, smtplib.SMTPException):
            log.exception("alert e-mail could not be sent kind=%s clinic=%s", kind, clinic_id)


class CompositeAlertNotifier:
    def __init__(self, *notifiers: Any) -> None:
        self._notifiers = notifiers

    async def notify(self, kind: str, clinic_id: UUID, payload: dict[str, Any]) -> None:
        for notifier in self._notifiers:
            await notifier.notify(kind, clinic_id, payload)


def build_alert_service(settings: Settings | None = None) -> AlertService:
    s = settings or get_settings()
    return AlertService(
        get_gate_store(),
        CompositeAlertNotifier(LoggingAlertNotifier(), EmailAlertNotifier(s)),
        calls_per_hour=s.alert_calls_per_hour,
        cost_cents_per_hour=s.alert_cost_cents_per_hour,
        prank_flags_per_hour=s.alert_prank_flags_per_hour,
    )
