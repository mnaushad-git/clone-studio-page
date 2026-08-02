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

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

# Field names whose values must never be written to logs verbatim.
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
    media_base_url: str = "http://localhost:8000/media"

    # Checkout pricing — mirrors the Admin Portal's current localStorage-only defaults
    # (src/lib/admin-store.ts SiteSettings) since admin settings aren't backend-owned
    # yet (Launch Sprint scope). Server-authoritative regardless: checkout always
    # recomputes from these, never from a client-submitted tax/delivery/total value.
    checkout_tax_rate_percent: float = 5.0
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

    # "stub" (Launch Sprint default, explicit decision) never sends a real email/SMS.
    # See app/integrations/notifications/factory.py for the swap point.
    notification_provider: str = "stub"

    # Admin Portal auth (task brief §2) — signs the admin-audience JWT access/refresh
    # tokens issued by /api/v1/admin/auth/login. The default below is an obviously
    # insecure placeholder (never used verbatim in production; every deployed
    # environment must set its own ADMIN_JWT_SECRET), same posture as ODOO_PASSWORD's
    # blank-by-default: the app must still start and be usable locally without one.
    admin_jwt_secret: str = "dev-insecure-admin-jwt-secret-change-me"
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
