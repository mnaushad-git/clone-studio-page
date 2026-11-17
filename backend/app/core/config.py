"""Environment-based application configuration.

Odoo settings (Phase 4) are read by app/integrations/odoo/config.py, which builds a
validated OdooConfig from this Settings instance and fails fast on incomplete/invalid
configuration. Settings itself stays a plain, permissive pydantic-settings model — it
does not validate Odoo-specific invariants (e.g. "password or api key, not neither"),
so the app can still start with Odoo entirely unconfigured (placeholder/local-dev case).
"""

from __future__ import annotations

from functools import lru_cache
from typing import Annotated
from urllib.parse import urlsplit

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

# Field names whose values must never be written to logs verbatim.
INSECURE_ADMIN_JWT_SECRET = "dev-insecure-admin-jwt-secret-change-me"
MIN_PRODUCTION_JWT_SECRET_LENGTH = 32
_LOCAL_HOST_MARKERS = ("localhost", "127.0.0.1", "0.0.0.0", "[::1]")
DEPLOYMENT_STAGES = ("development", "demo", "local_integration", "staging", "live")
# The hosts a local_integration deployment may push real sale orders to.
LOCAL_ODOO_HOSTS = ("localhost", "127.0.0.1", "terrific-odoo")
ODOO_CREDENTIAL_FREE_ROLES = ("api", "beat", "migrate")
# The only Odoo a staging deployment may contact: the Compose project's own `odoo` service on
# its internal network, and its one database. Fixed in code, so that no environment value can
# point staging at an external or production Odoo.
STAGING_ODOO_BASE_URL = "http://odoo:8069"
STAGING_ODOO_DATABASE = "terrific_odoo"
STAGING_ODOO_WRITE_TARGET = f"{STAGING_ODOO_BASE_URL}#{STAGING_ODOO_DATABASE}"
# The services allowed to hold an Odoo login on staging, and the login each must use. These
# are the restricted integration users created by deploy/odoo/bootstrap.py.
STAGING_ODOO_LOGINS = {
    "worker": "terrific-order-sync",
    "catalogue_import": "terrific-catalogue-import",
}

SECRET_FIELD_NAMES: frozenset[str] = frozenset(
    {
        "database_url",
        "redis_url",
        "celery_broker_url",
        "celery_result_backend",
        "odoo_password",
        "odoo_api_key",
        "admin_jwt_secret",
    }
)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application identity
    app_name: str = "Terrific Bites API"
    app_version: str = "0.1.0"
    app_env: str = "development"
    debug: bool = False
    # development: local work. demo: Stage A, every external provider must be a stub and
    # every order is permanently marked is_demo. local_integration: real sale orders into
    # an isolated local Odoo, payments and notifications stubbed, never on production.
    # staging: the client UAT site; payments and notifications stubbed, sale orders only into
    # the deployment's own staging Odoo (STAGING_ODOO_*). live: Stage B, every provider must
    # be real. See docs/deployment/production-runbook.md.
    deployment_stage: str = "development"
    # Which process this is, so that _refuse_odoo_credentials_outside_workers can hold each
    # one to the credentials its job needs. Blank is local development and tests.
    service_role: str = ""

    # API
    api_v1_prefix: str = "/api/v1"
    host: str = "0.0.0.0"
    port: int = 8000

    # Logging
    log_level: str = "INFO"

    # PostgreSQL
    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/terrific_bites"
    database_pool_size: int = 5
    database_max_overflow: int = 10

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Celery
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"

    # CORS / trusted hosts — comma-separated lists in the environment. NoDecode stops
    # pydantic-settings from JSON-decoding the raw env string before our validator runs.
    cors_allowed_origins: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["http://localhost:3000"]
    )
    trusted_hosts: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["localhost", "127.0.0.1"]
    )

    # Odoo — read by app/integrations/odoo/config.py (Phase 4). Empty by default: the
    # app and its non-Odoo tests must keep working with Odoo entirely unconfigured.
    odoo_base_url: str = ""
    odoo_database: str = ""
    odoo_username: str = ""
    odoo_password: str = ""
    odoo_api_key: str = ""
    odoo_timeout_seconds: int = 30
    odoo_verify_ssl: bool = True
    odoo_max_retries: int = 3
    odoo_retry_backoff_seconds: float = 1.0
    odoo_read_batch_size: int = 200
    odoo_protocol: str = "jsonrpc"
    odoo_company_id: int | None = None
    odoo_default_pricelist_id: int | None = None
    odoo_default_warehouse_id: int | None = None
    # Which stock.location counts as "available for the storefront" when summing
    # stock.quant rows. None means "sum every internal-usage location" — the sync
    # degrades gracefully (see app/services/catalogue/odoo_catalogue_sync_service.py)
    # when the Inventory app isn't installed at all, so this stays optional.
    odoo_stock_location_id: int | None = None

    # Odoo -> PostgreSQL catalogue pull sync (the reverse of the import service above).
    # max_records bounds every bulk Odoo read per entity type per run (required by
    # OdooClient.iter_search_read — no "fetch everything" convenience by design).
    odoo_catalogue_sync_max_records: int = 5000
    odoo_catalogue_sync_interval_seconds: float = 300.0

    # Local-disk media storage for images pulled from Odoo (image_1920 base64 payloads
    # have nowhere else to land — see MediaStorageService). Deliberately not object
    # storage yet: no existing storage/credential story in this app to build on, and
    # CLAUDE.md says not to introduce infrastructure without a demonstrated need.
    media_root: str = "media"
    media_base_url: str = "http://localhost:8020/media"

    # Checkout pricing — mirrors the Admin Portal's current localStorage-only defaults
    # (src/lib/admin-store.ts SiteSettings) since admin settings aren't backend-owned
    # yet (Launch Sprint scope). Server-authoritative regardless: checkout always
    # recomputes from these, never from a client-submitted tax/delivery/total value.
    # 15% Saudi VAT, with every price (and, below, the delivery fee) VAT-inclusive. Proposed
    # rules awaiting client finance approval, see docs/integrations/odoo-order-financials.md.
    checkout_tax_rate_percent: float = 15.0
    checkout_delivery_vat_applies: bool = True
    checkout_default_delivery_fee: float = 15.0
    checkout_free_delivery_threshold: float = 0.0
    checkout_min_order_amount: float = 30.0

    # "stub" (Launch Sprint default) never contacts a real gateway. See
    # app/integrations/payments/factory.py for the swap point.
    payment_provider: str = "stub"

    # "stub" (Launch Sprint default, explicit decision) never contacts Odoo; "live"
    # creates a real sale.order (see LiveOdooOrderPusher). See
    # app/integrations/odoo/order_push_factory.py for the swap point.
    odoo_order_push_provider: str = "stub"
    # Every Odoo write is refused unless this is exactly <ODOO_BASE_URL>#<ODOO_DATABASE>.
    # See app/integrations/odoo/write_target_guard.py.
    odoo_write_approved_target: str = ""

    # Set only once the client's finance team has approved the VAT and delivery treatment.
    # DEPLOYMENT_STAGE=live refuses to start without it.
    finance_rules_approved: bool = False

    # Automatic retries of a failed order push: the delay doubles from the base up to the
    # maximum, and the event is dead-lettered for an operator after max_attempts.
    order_sync_max_attempts: int = 8
    order_sync_retry_base_seconds: int = 120
    order_sync_retry_max_seconds: int = 3600

    # "stub" (Launch Sprint default, explicit decision) never sends a real email/SMS.
    # See app/integrations/notifications/factory.py for the swap point.
    notification_provider: str = "stub"

    # Admin Portal auth (task brief §2) — signs the admin-audience JWT access/refresh
    # tokens issued by /api/v1/admin/auth/login. The default below is an obviously
    # insecure placeholder (never used verbatim in production; every deployed
    # environment must set its own ADMIN_JWT_SECRET), same posture as ODOO_PASSWORD's
    # blank-by-default: the app must still start and be usable locally without one.
    admin_jwt_secret: str = INSECURE_ADMIN_JWT_SECRET
    # Domain attribute for the admin auth/CSRF cookies. Required in production, where the
    # API (api.<frontend-host>) and the frontend are on different hosts: without it the
    # JS-readable admin_csrf cookie is host-only to the API, the frontend cannot echo it
    # as X-CSRF-Token, and every mutating admin request fails with 403. Blank means
    # host-only, which is right for localhost development.
    admin_cookie_domain: str | None = None
    admin_access_token_ttl_minutes: int = 15
    admin_refresh_token_ttl_days: int = 7
    # Account lockout (DB-backed, works even when Redis is down) — after this many
    # consecutive failed logins, admin_users.locked_until is set this many minutes out.
    admin_login_max_attempts: int = 5
    admin_login_lockout_minutes: int = 15
    # Redis-backed login throttle (best-effort — skipped, not fatal, when Redis is
    # unreachable; the DB-backed lockout above is the layer that always works).
    admin_login_throttle_max_attempts: int = 10
    admin_login_throttle_window_seconds: int = 60

    # Dashboard "stuck order" threshold (task brief §4) — an order paid/processing for
    # longer than this with no forward progress surfaces as an operational alert.
    ops_stuck_order_minutes: int = 30
    # app/core/rate_limit.py: per-IP limits on the public order endpoints. A shopper places a
    # handful of orders at most, so these only stop automated abuse.
    rate_limit_enabled: bool = True
    rate_limit_order_create_per_10_min: int = 20
    rate_limit_order_pay_per_10_min: int = 20
    rate_limit_order_lookup_per_minute: int = 60

    # app/services/ops/health_monitor.py: alert thresholds for the operational check.
    ops_heartbeat_max_age_seconds: int = 300
    ops_outbox_max_age_minutes: int = 15

    # Selective Redis caching (cache-aside) for the read-heavy catalogue endpoints —
    # see app/cache/. PostgreSQL stays authoritative and the serving source of truth;
    # Redis is purely an acceleration layer, never written to before PostgreSQL
    # commits, and every catalogue endpoint keeps working with CACHE_ENABLED=false or
    # Redis stopped outright.
    cache_enabled: bool = True
    cache_key_prefix: str = "tb"
    cache_homepage_ttl_seconds: int = 300
    cache_categories_ttl_seconds: int = 900
    cache_product_detail_ttl_seconds: int = 300
    cache_moments_ttl_seconds: int = 900
    cache_recipients_ttl_seconds: int = 900
    cache_product_list_ttl_seconds: int = 120
    # Dedicated socket timeout for the cache Redis client — deliberately separate from
    # the general-purpose Redis client's fixed 2s timeout (app/core/redis.py), since a
    # catalogue request must fail over to PostgreSQL fast on a slow/unreachable cache.
    cache_redis_operation_timeout_seconds: float = 1.0
    # Soft cap on distinct cached product-list query variants (see app/cache/keys.py)
    # to bound key-space growth from arbitrary filter/search combinations.
    cache_max_product_list_keys: int = 500
    cache_log_hits: bool = False
    # Reserved for a future compressed-value codec (app/cache/serializer.py) — no
    # compression is implemented yet, so this only controls whether it would be used.
    cache_compression_enabled: bool = False
    # Emits the non-production-only X-Cache / X-Cache-Key-Version response headers
    # (app/api/v1/endpoints/catalogue.py) — always off in app_env=="production"
    # regardless of this flag.
    cache_debug_headers_enabled: bool = True

    @field_validator("cors_allowed_origins", "trusted_hosts", mode="before")
    @classmethod
    def _split_csv(cls, value: object) -> object:
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    @field_validator(
        "odoo_company_id",
        "odoo_default_pricelist_id",
        "odoo_default_warehouse_id",
        "odoo_stock_location_id",
        mode="before",
    )
    @classmethod
    def _blank_optional_int_to_none(cls, value: object) -> object:
        """An empty ODOO_COMPANY_ID=/ODOO_DEFAULT_PRICELIST_ID=/ODOO_DEFAULT_WAREHOUSE_ID=/
        ODOO_STOCK_LOCATION_ID= in the environment means "unset", not "parse '' as an
        int" — matches how every other optional Odoo setting in .env.example is left
        blank to mean "not configured".
        """
        if isinstance(value, str) and not value.strip():
            return None
        return value

    @field_validator("admin_cookie_domain", mode="before")
    @classmethod
    def _blank_cookie_domain_to_none(cls, value: object) -> object:
        if isinstance(value, str) and not value.strip():
            return None
        return value

    @property
    def is_demo_stage(self) -> bool:
        return self.deployment_stage == "demo"

    @model_validator(mode="after")
    def _enforce_deployment_stage(self) -> Settings:
        """A demo can never reach a real provider, and a live site can never fake one."""
        if self.deployment_stage not in DEPLOYMENT_STAGES:
            raise ValueError(f"DEPLOYMENT_STAGE must be one of {DEPLOYMENT_STAGES}")

        providers = {
            "PAYMENT_PROVIDER": self.payment_provider,
            "NOTIFICATION_PROVIDER": self.notification_provider,
            "ODOO_ORDER_PUSH_PROVIDER": self.odoo_order_push_provider,
        }
        if self.deployment_stage == "demo":
            wrong = sorted(name for name, value in providers.items() if value != "stub")
            if wrong:
                raise ValueError(f"DEPLOYMENT_STAGE=demo requires stub for: {', '.join(wrong)}")
        if self.deployment_stage == "live":
            wrong = sorted(name for name, value in providers.items() if value == "stub")
            if wrong:
                raise ValueError(f"DEPLOYMENT_STAGE=live refuses stub for: {', '.join(wrong)}")
            if not self.finance_rules_approved:
                raise ValueError(
                    "DEPLOYMENT_STAGE=live requires FINANCE_RULES_APPROVED=true, set once the "
                    "client's finance team has approved the VAT and delivery treatment"
                )
        if self.deployment_stage == "local_integration":
            self._check_local_integration()
        if self.deployment_stage == "staging":
            self._check_staging()
        return self

    @model_validator(mode="after")
    def _refuse_odoo_credentials_outside_workers(self) -> Settings:
        """The API and scheduler never talk to Odoo, so a credential there is only exposure."""
        if self.service_role in ODOO_CREDENTIAL_FREE_ROLES and (
            self.odoo_password or self.odoo_api_key
        ):
            raise ValueError(f"SERVICE_ROLE={self.service_role} must not hold Odoo credentials")
        return self

    def _check_local_integration(self) -> None:
        if self.app_env == "production":
            raise ValueError("DEPLOYMENT_STAGE=local_integration is refused in production")
        if self.payment_provider != "stub" or self.notification_provider != "stub":
            raise ValueError(
                "DEPLOYMENT_STAGE=local_integration requires stub payments and notifications"
            )
        if self.odoo_order_push_provider != "live":
            raise ValueError("DEPLOYMENT_STAGE=local_integration requires the live Odoo pusher")
        if urlsplit(self.odoo_base_url).hostname not in LOCAL_ODOO_HOSTS:
            raise ValueError("DEPLOYMENT_STAGE=local_integration requires a local Odoo host")

    def _check_staging(self) -> None:
        """Fail closed: staging may reach exactly one Odoo, with exactly the expected user.
        Messages name the setting that is wrong, never its value."""
        problems: list[str] = []
        if self.payment_provider != "stub":
            problems.append("PAYMENT_PROVIDER must be stub")
        if self.notification_provider != "stub":
            problems.append("NOTIFICATION_PROVIDER must be stub")
        if self.odoo_order_push_provider not in ("stub", "live"):
            problems.append("ODOO_ORDER_PUSH_PROVIDER must be stub or live")

        # Any process that has an Odoo address at all, reading or writing, gets the same one.
        if (self.odoo_base_url.strip() or self.odoo_order_push_provider == "live") and (
            self.odoo_base_url.strip().rstrip("/") != STAGING_ODOO_BASE_URL
        ):
            problems.append(f"ODOO_BASE_URL must be the staging Odoo {STAGING_ODOO_BASE_URL}")
        if (self.odoo_database.strip() or self.odoo_order_push_provider == "live") and (
            self.odoo_database.strip() != STAGING_ODOO_DATABASE
        ):
            problems.append(f"ODOO_DATABASE must be the staging database {STAGING_ODOO_DATABASE}")
        approved = self.odoo_write_approved_target.strip()
        if approved and approved != STAGING_ODOO_WRITE_TARGET:
            problems.append(
                f"ODOO_WRITE_APPROVED_TARGET may only name the staging Odoo "
                f"{STAGING_ODOO_WRITE_TARGET}"
            )

        holds_credential = bool(self.odoo_password or self.odoo_api_key)
        expected_login = STAGING_ODOO_LOGINS.get(self.service_role)
        if holds_credential and expected_login is None:
            role = self.service_role or "(blank)"
            problems.append(f"SERVICE_ROLE={role} must not hold Odoo credentials")
        if holds_credential and expected_login and self.odoo_username != expected_login:
            problems.append(
                f"ODOO_USERNAME for SERVICE_ROLE={self.service_role} must be the staging "
                f"integration user {expected_login}"
            )
        if self.service_role == "worker" and self.odoo_order_push_provider == "live":
            if not holds_credential:
                problems.append("the worker needs the staging order-sync credential to push orders")
            if approved != STAGING_ODOO_WRITE_TARGET:
                problems.append(
                    f"ODOO_WRITE_APPROVED_TARGET must be {STAGING_ODOO_WRITE_TARGET} for the "
                    "worker to push orders"
                )

        if problems:
            raise ValueError("Unsafe staging configuration: " + "; ".join(problems))

    @model_validator(mode="after")
    def _refuse_unsafe_production_config(self) -> Settings:
        """Fail at startup rather than serve production on development defaults. Reports
        which settings are wrong, never their values."""
        if self.app_env != "production":
            return self

        problems: list[str] = []
        if self.deployment_stage == "development":
            problems.append("DEPLOYMENT_STAGE must be demo, staging or live")
        if self.debug:
            problems.append("DEBUG must be false")
        if (
            self.admin_jwt_secret == INSECURE_ADMIN_JWT_SECRET
            or len(self.admin_jwt_secret) < MIN_PRODUCTION_JWT_SECRET_LENGTH
        ):
            problems.append(
                "ADMIN_JWT_SECRET must be a unique secret of at least "
                f"{MIN_PRODUCTION_JWT_SECRET_LENGTH} characters"
            )
        if not self.admin_cookie_domain:
            problems.append("ADMIN_COOKIE_DOMAIN must be set")
        if not self.cors_allowed_origins or any(
            origin == "*"
            or not origin.startswith("https://")
            or any(marker in origin for marker in _LOCAL_HOST_MARKERS)
            for origin in self.cors_allowed_origins
        ):
            problems.append("CORS_ALLOWED_ORIGINS must list only public https:// origins")
        if not self.trusted_hosts or any(
            host == "*" or any(marker in host for marker in _LOCAL_HOST_MARKERS)
            for host in self.trusted_hosts
        ):
            problems.append("TRUSTED_HOSTS must list only the public API hostname(s)")
        if not self.media_base_url.startswith("https://") or any(
            marker in self.media_base_url for marker in _LOCAL_HOST_MARKERS
        ):
            problems.append("MEDIA_BASE_URL must be a public https:// URL")
        if "postgres:postgres@" in self.database_url:
            problems.append("DATABASE_URL must not use the development postgres credentials")

        if problems:
            raise ValueError("Unsafe production configuration: " + "; ".join(problems))
        return self

    def masked_dict(self) -> dict[str, object]:
        """Config snapshot safe to log — secret fields replaced with a fixed marker."""
        data = self.model_dump()
        for name in SECRET_FIELD_NAMES:
            if name in data and data[name]:
                data[name] = "***REDACTED***"
        return data


@lru_cache
def get_settings() -> Settings:
    return Settings()
