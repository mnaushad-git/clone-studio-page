"""Notification provider contract. Every provider (stub or real, e.g. SendGrid/SES for
email, Twilio/Unifonic for SMS) implements this Protocol.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(frozen=True)
class NotificationResult:
    success: bool
    status: str  # "sent" | "failed"
    provider_reference: str
    raw: dict[str, Any]


class NotificationProvider(Protocol):
    name: str

    def send_email(self, *, to: str, subject: str, body: str) -> NotificationResult:
        """Must never raise for a normal send failure — that's
        NotificationResult(success=False, ...); only truly exceptional conditions
        (provider unreachable, invalid config) should raise."""
        ...

    def send_sms(self, *, to: str, body: str) -> NotificationResult:
        """Same non-raising contract as send_email."""
        ...
