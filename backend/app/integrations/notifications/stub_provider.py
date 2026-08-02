"""Stub notification provider — Launch Sprint default, per explicit decision to stub
email/SMS for this launch. Never contacts a real email or SMS provider; every send
succeeds immediately. Swap via NOTIFICATION_PROVIDER in settings once real credentials
(e.g. SendGrid/SES for email, Twilio/Unifonic for SMS) exist.
"""

from __future__ import annotations

import uuid

from app.integrations.notifications.base import NotificationResult


class StubNotificationProvider:
    name = "stub"

    def send_email(self, *, to: str, subject: str, body: str) -> NotificationResult:
        return NotificationResult(
            success=True,
            status="sent",
            provider_reference=f"stub_email_{uuid.uuid4().hex[:16]}",
            raw={
                "provider": self.name,
                "note": "Stub provider — no real email was sent.",
                "to": to,
                "subject": subject,
            },
        )

    def send_sms(self, *, to: str, body: str) -> NotificationResult:
        return NotificationResult(
            success=True,
            status="sent",
            provider_reference=f"stub_sms_{uuid.uuid4().hex[:16]}",
            raw={
                "provider": self.name,
                "note": "Stub provider — no real SMS was sent.",
                "to": to,
                "body_length": len(body),
            },
        )
