"""Validated Odoo client configuration.

Wraps app.core.config.Settings' ODOO_* fields into an OdooConfig that has already
been checked for internal consistency — a client is never constructed from an
incomplete/invalid configuration; it fails fast at OdooConfig.from_settings(),
not on the first API call.
"""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlparse

from app.core.config import Settings
from app.integrations.odoo.exceptions import OdooConfigurationError

SUPPORTED_PROTOCOLS = frozenset({"jsonrpc"})


@dataclass(frozen=True)
class OdooConfig:
    base_url: str
    database: str
    username: str
    password: str | None
    api_key: str | None
    timeout_seconds: float
    verify_ssl: bool
    max_retries: int
    retry_backoff_seconds: float
    read_batch_size: int
    protocol: str
    company_id: int | None
    default_pricelist_id: int | None
    default_warehouse_id: int | None

    @property
    def credential(self) -> str:
        """The value used as the `password` argument in Odoo's authenticate/login
        call — Odoo's external API accepts an API key interchangeably with the
        account password there, so API-key auth and password auth share one
        transport-level login call.
        """
        assert self.api_key or self.password
        return self.api_key or self.password or ""

    @property
    def jsonrpc_endpoint(self) -> str:
        return f"{self.base_url.rstrip('/')}/jsonrpc"

    def masked_dict(self) -> dict[str, object]:
        """Config snapshot safe to log — mirrors Settings.masked_dict()."""
        return {
            "base_url": self.base_url,
            "database": self.database,
            "username": self.username,
            "password": "***REDACTED***" if self.password else None,
            "api_key": "***REDACTED***" if self.api_key else None,
            "timeout_seconds": self.timeout_seconds,
            "verify_ssl": self.verify_ssl,
            "max_retries": self.max_retries,
            "retry_backoff_seconds": self.retry_backoff_seconds,
            "read_batch_size": self.read_batch_size,
            "protocol": self.protocol,
            "company_id": self.company_id,
            "default_pricelist_id": self.default_pricelist_id,
            "default_warehouse_id": self.default_warehouse_id,
        }

    @classmethod
    def from_settings(cls, settings: Settings) -> OdooConfig:
        issues: list[str] = []

        base_url = settings.odoo_base_url.strip()
        database = settings.odoo_database.strip()
        username = settings.odoo_username.strip()
        password = settings.odoo_password.strip() or None
        api_key = settings.odoo_api_key.strip() or None

        if not base_url:
            issues.append("ODOO_BASE_URL is not set")
        else:
            parsed = urlparse(base_url)
            if parsed.scheme not in ("http", "https") or not parsed.netloc:
                issues.append(f"ODOO_BASE_URL is not a valid absolute http(s) URL: {base_url!r}")

        if not database:
            issues.append("ODOO_DATABASE is not set")
        if not username:
            issues.append("ODOO_USERNAME is not set")
        if not password and not api_key:
            issues.append("Neither ODOO_PASSWORD nor ODOO_API_KEY is set")
        if password and api_key:
            issues.append("Both ODOO_PASSWORD and ODOO_API_KEY are set — configure exactly one")

        if settings.odoo_timeout_seconds <= 0:
            issues.append(
                f"ODOO_TIMEOUT_SECONDS must be positive, got {settings.odoo_timeout_seconds}"
            )
        if settings.odoo_max_retries < 0:
            issues.append(f"ODOO_MAX_RETRIES must be >= 0, got {settings.odoo_max_retries}")
        if settings.odoo_retry_backoff_seconds < 0:
            issues.append(
                "ODOO_RETRY_BACKOFF_SECONDS must be >= 0, "
                f"got {settings.odoo_retry_backoff_seconds}"
            )
        if settings.odoo_read_batch_size <= 0:
            issues.append(
                f"ODOO_READ_BATCH_SIZE must be positive, got {settings.odoo_read_batch_size}"
            )

        protocol = settings.odoo_protocol.strip().lower()
        if protocol not in SUPPORTED_PROTOCOLS:
            issues.append(
                f"ODOO_PROTOCOL {protocol!r} is not supported — must be one of "
                f"{sorted(SUPPORTED_PROTOCOLS)} (see docs/integrations/odoo-client.md "
                "for the protocol decision)"
            )

        if issues:
            raise OdooConfigurationError(
                "Invalid Odoo configuration: " + "; ".join(issues),
                context={"issue_count": len(issues)},
            )

        return cls(
            base_url=base_url,
            database=database,
            username=username,
            password=password,
            api_key=api_key,
            timeout_seconds=float(settings.odoo_timeout_seconds),
            verify_ssl=settings.odoo_verify_ssl,
            max_retries=settings.odoo_max_retries,
            retry_backoff_seconds=settings.odoo_retry_backoff_seconds,
            read_batch_size=settings.odoo_read_batch_size,
            protocol=protocol,
            company_id=settings.odoo_company_id,
            default_pricelist_id=settings.odoo_default_pricelist_id,
            default_warehouse_id=settings.odoo_default_warehouse_id,
        )

    @classmethod
    def is_configured(cls, settings: Settings) -> bool:
        """True if enough ODOO_* settings are present to attempt from_settings() —
        used by the verification CLI to distinguish "not configured" (expected, quiet)
        from "configured but invalid" (a real problem worth a loud error).
        """
        return bool(
            settings.odoo_base_url.strip()
            or settings.odoo_database.strip()
            or settings.odoo_username.strip()
        )
