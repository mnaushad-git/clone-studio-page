"""Odoo -> PostgreSQL catalogue pull sync.

Reverse-direction counterpart of app.services.catalogue.odoo_import_service (which
pushes the canonical seed data OUT to Odoo). This service pulls categories, products,
variants, prices, images, and stock availability FROM Odoo and upserts them into the
PostgreSQL catalogue tables the storefront/admin portal actually read from (CLAUDE.md
rule 4: "Products flow Odoo -> background worker -> PostgreSQL").

Session/transaction discipline: each entity-type sync method commits after every
record it processes (same discipline as OdooOrderSyncService.sync_paid_orders) — one
bad record must never roll back another record's already-recorded success, and a
crash mid-run leaves partial progress durably in place. Six entity types run in
sequence (categories -> products -> variants -> prices -> images -> stock) because
each later phase needs an odoo-id -> postgres-id map built by an earlier phase. A
whole entity type failing (e.g. stock.quant is not installed on the connected Odoo
instance — a real, documented environment gap, see
docs/integrations/odoo-operations-runbook.md) marks that entity's checkpoint FAILED
and the overall run PARTIALLY_COMPLETED, but never aborts the remaining phases.

Odoo has no Arabic name/description field in this integration, so name_ar/
description_ar are simply excluded from every values dict below — never set to null,
never overwritten. They stay permanently seed/admin-owned until a translation
workflow exists.
"""

from __future__ import annotations

import base64
import logging
import re
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy.orm import Session

from app.cache import get_cache_client
from app.cache.invalidation import CacheInvalidationService
from app.core.config import Settings, get_settings
from app.integrations.odoo.client import OdooClient
from app.integrations.odoo.config import OdooConfig
from app.integrations.odoo.exceptions import OdooConfigurationError, OdooIntegrationError
from app.integrations.odoo.repositories.attributes import OdooAttributeRepository
from app.integrations.odoo.repositories.categories import OdooCategoryRepository
from app.integrations.odoo.repositories.product_images import OdooProductImageRepository
from app.integrations.odoo.repositories.products import OdooProductRepository
from app.integrations.odoo.repositories.stock import OdooStockRepository
from app.models.catalogue.category import CatalogueCategory
from app.models.catalogue.product import CatalogueProduct
from app.models.catalogue.product_variant import CatalogueProductVariant
from app.models.integration.odoo_catalogue_sync_item import OdooCatalogueSyncItem
from app.models.integration.odoo_catalogue_sync_run import OdooCatalogueSyncRun
from app.models.integration.sync_checkpoint import IntegrationSyncCheckpoint
from app.repositories.catalogue.category_repository import CategoryRepository
from app.repositories.catalogue.product_attribute_value_repository import (
    ProductAttributeValueRepository,
)
from app.repositories.catalogue.product_availability_repository import (
    ProductAvailabilityRepository,
)
from app.repositories.catalogue.product_image_repository import ProductImageRepository
from app.repositories.catalogue.product_merchandising_repository import (
    ProductMerchandisingRepository,
)
from app.repositories.catalogue.product_price_repository import ProductPriceRepository
from app.repositories.catalogue.product_repository import ProductRepository
from app.repositories.catalogue.product_variant_repository import ProductVariantRepository
from app.repositories.integration.odoo_catalogue_sync_item_repository import (
    OdooCatalogueSyncItemRepository,
)
from app.repositories.integration.odoo_catalogue_sync_run_repository import (
    OdooCatalogueSyncRunRepository,
)
from app.repositories.integration.sync_checkpoint_repository import SyncCheckpointRepository
from app.services.catalogue.media_storage_service import MediaStorageService

logger = logging.getLogger("app.services.catalogue.odoo_catalogue_sync_service")

INTEGRATION_NAME = "odoo_catalogue"

# Clock-skew / mid-read-commit safety buffer: the next incremental run's checkpoint is
# set to (window_start - this), not the max write_date seen in the batch, trading a
# small amount of harmless re-processing (matching is idempotent) for protection
# against records committed in Odoo during this run's own read window.
_CHECKPOINT_SAFETY_BUFFER = timedelta(seconds=60)
_ODOO_DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"

# _attribute_code_for's name-heuristic tier (see its docstring): every axis name
# already in use in data/catalogue/products.json, lowercased. An Odoo attribute whose
# name matches one of these renders correctly on today's two-slot storefront UI even
# on its very first sync (no prior Postgres row to reuse a code from yet).
_SIZE_ATTRIBUTE_NAMES = {"size", "pack size", "box size", "gift tier", "cake size", "ice cream size"}
_FLAVOR_ATTRIBUTE_NAMES = {"flavor", "flavour"}


@dataclass(frozen=True)
class ResolvedAttribute:
    attribute_code: str
    odoo_attribute_id: int
    attribute_name_en: str
    odoo_attribute_value_id: int
    value_label_en: str
    price_extra: Decimal


def _connect_readonly(settings: Settings) -> tuple[OdooClient | None, str | None]:
    if not OdooConfig.is_configured(settings):
        return None, "Odoo is not configured (ODOO_BASE_URL/DATABASE/USERNAME empty)"
    try:
        config = OdooConfig.from_settings(settings)
    except OdooConfigurationError as exc:
        return None, f"Invalid Odoo configuration: {exc}"

    from app.integrations.odoo.transport import OdooTransport

    transport = OdooTransport(config)
    client = OdooClient(config, transport)
    try:
        client.get_server_version()
        client.authenticate()
    except OdooIntegrationError as exc:
        transport.close()
        return None, f"Could not establish a verified Odoo session: {exc}"
    return client, None


def _parse_odoo_datetime(value: Any) -> datetime | None:
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    try:
        return datetime.strptime(value, _ODOO_DATETIME_FORMAT).replace(tzinfo=UTC)
    except (TypeError, ValueError):
        return None


def _slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-") or "item"


@dataclass
class EntityCounts:
    created: int = 0
    updated: int = 0
    skipped: int = 0
    failed: int = 0

    def record(self, action: str) -> None:
        if action == "CREATE":
            self.created += 1
        elif action == "UPDATE":
            self.updated += 1
        elif action == "SKIP_UNCHANGED":
            self.skipped += 1
        else:
            self.failed += 1

    def as_dict(self) -> dict[str, int]:
        return {
            "created": self.created,
            "updated": self.updated,
            "skipped": self.skipped,
            "failed": self.failed,
        }


class OdooCatalogueSyncService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.categories = CategoryRepository(session)
        self.products = ProductRepository(session)
        self.variants = ProductVariantRepository(session)
        self.prices = ProductPriceRepository(session)
        self.images = ProductImageRepository(session)
        self.availability = ProductAvailabilityRepository(session)
        self.merchandising = ProductMerchandisingRepository(session)
        self.attribute_values = ProductAttributeValueRepository(session)
        self.checkpoints = SyncCheckpointRepository(session)
        self.sync_runs = OdooCatalogueSyncRunRepository(session)
        self.sync_items = OdooCatalogueSyncItemRepository(session)
        self.settings = get_settings()
        self.media = MediaStorageService(self.settings)

    # -- orchestration ------------------------------------------------------------

    def sync_all(
        self, *, full_resync: bool = False, trigger: str, initiated_by: str, correlation_id: str
    ) -> OdooCatalogueSyncRun:
        client, connect_failure = _connect_readonly(self.settings)

        run = OdooCatalogueSyncRun(
            trigger=trigger,
            status="RUNNING",
            full_resync=full_resync,
            started_at=datetime.now(UTC),
            correlation_id=correlation_id,
            initiated_by=initiated_by,
        )
        self.sync_runs.create(run)
        self.session.commit()

        if client is None:
            self.sync_runs.mark_status(
                run, "FAILED", completed_at=datetime.now(UTC), error_summary=connect_failure
            )
            self.session.commit()
            return run

        counts_by_entity: dict[str, dict[str, int]] = {}

        category_counts, category_id_map = self.sync_categories(
            client, run=run, full_resync=full_resync
        )
        counts_by_entity["CATEGORY"] = category_counts.as_dict()

        product_counts, product_id_map, template_records = self.sync_products(
            client, run=run, full_resync=full_resync, category_id_map=category_id_map
        )
        counts_by_entity["PRODUCT_TEMPLATE"] = product_counts.as_dict()

        variant_counts, variant_id_map, variant_records, price_extra_by_variant = self.sync_variants(
            client, run=run, full_resync=full_resync, product_id_map=product_id_map
        )
        counts_by_entity["PRODUCT_VARIANT"] = variant_counts.as_dict()

        price_counts = self.sync_prices(
            run=run,
            variant_id_map=variant_id_map,
            variant_records=variant_records,
            template_records=template_records,
            price_extra_by_variant=price_extra_by_variant,
        )
        counts_by_entity["PRODUCT_PRICE"] = price_counts.as_dict()

        image_counts = self.sync_images(
            client,
            run=run,
            product_id_map=product_id_map,
            template_records=template_records,
        )
        counts_by_entity["PRODUCT_IMAGE"] = image_counts.as_dict()

        stock_counts = self.sync_stock(client, run=run, variant_id_map=variant_id_map)
        counts_by_entity["PRODUCT_AVAILABILITY"] = stock_counts.as_dict()

        all_counts = [
            category_counts,
            product_counts,
            variant_counts,
            price_counts,
            image_counts,
            stock_counts,
        ]
        total_created = sum(c.created for c in all_counts)
        total_updated = sum(c.updated for c in all_counts)
        total_skipped = sum(c.skipped for c in all_counts)
        total_failed = sum(c.failed for c in all_counts)

        # A whole entity type can fail before processing a single record (e.g.
        # stock.quant reporting "model not installed") — that contributes nothing to
        # total_failed above, since no per-record failure was ever counted, but it's
        # still a real degradation the run status must reflect.
        any_phase_failed = any(
            checkpoint is not None and checkpoint.status == "FAILED"
            for checkpoint in (
                self.checkpoints.get(INTEGRATION_NAME, entity_type)
                for entity_type in (
                    "CATEGORY",
                    "PRODUCT_TEMPLATE",
                    "PRODUCT_VARIANT",
                    "PRODUCT_PRICE",
                    "PRODUCT_IMAGE",
                    "PRODUCT_AVAILABILITY",
                )
            )
        )

        if not total_failed and not any_phase_failed:
            status = "SUCCEEDED"
        elif total_created or total_updated or total_skipped:
            status = "PARTIALLY_COMPLETED"
        else:
            status = "FAILED"

        self.sync_runs.mark_status(
            run,
            status,
            completed_at=datetime.now(UTC),
            total_created=total_created,
            total_updated=total_updated,
            total_skipped=total_skipped,
            total_failed=total_failed,
            counts_by_entity_json=counts_by_entity,
        )
        self.session.commit()

        # Cache invalidation happens strictly after the commit above (CLAUDE.md rule:
        # never populate/invalidate cache from uncommitted data) and is itself
        # best-effort — RedisCache never raises, so a Redis outage here can't roll
        # back or fail an otherwise-successful sync run.
        CacheInvalidationService(get_cache_client(), self.settings).invalidate_after_product_sync(
            status
        )
        return run

    def _incremental_domain(
        self, checkpoint: IntegrationSyncCheckpoint, full_resync: bool
    ) -> list[Any]:
        if full_resync or not checkpoint.checkpoint_value:
            return []
        return [["write_date", ">=", checkpoint.checkpoint_value]]

    def _write_sync_item(
        self,
        *,
        run: OdooCatalogueSyncRun,
        entity_type: str,
        odoo_model: str,
        odoo_record_id: int,
        postgres_entity_id: uuid.UUID | None,
        match_strategy: str | None,
        action: str,
        result_status: str,
        odoo_write_date: Any = None,
        error: Exception | None = None,
    ) -> None:
        item = OdooCatalogueSyncItem(
            sync_run_id=run.id,
            entity_type=entity_type,
            odoo_model=odoo_model,
            odoo_record_id=odoo_record_id,
            postgres_entity_id=postgres_entity_id,
            match_strategy=match_strategy,
            action=action,
            result_status=result_status,
            odoo_write_date=_parse_odoo_datetime(odoo_write_date),
            error_code=type(error).__name__ if error else None,
            error_message=str(error) if error else None,
            started_at=datetime.now(UTC),
            completed_at=datetime.now(UTC),
        )
        self.sync_items.create(item)

    # -- categories -----------------------------------------------------------------

    def sync_categories(
        self, client: OdooClient, *, run: OdooCatalogueSyncRun, full_resync: bool
    ) -> tuple[EntityCounts, dict[int, uuid.UUID]]:
        entity_type = "CATEGORY"
        checkpoint = self.checkpoints.get_or_create(INTEGRATION_NAME, entity_type)
        self.checkpoints.mark_running(checkpoint)
        self.session.commit()

        counts = EntityCounts()
        id_map: dict[int, uuid.UUID] = {
            c.odoo_category_id: c.id for c in self.categories.list_active() if c.odoo_category_id
        }
        window_start = datetime.now(UTC)
        domain = self._incremental_domain(checkpoint, full_resync)
        repo = OdooCategoryRepository(client)

        try:
            for record in repo.iter_all_categories(
                domain=domain, max_records=self.settings.odoo_catalogue_sync_max_records
            ):
                try:
                    row, action, strategy = self._match_and_upsert_category(record)
                    id_map[record["id"]] = row.id
                    counts.record(action)
                    self._write_sync_item(
                        run=run,
                        entity_type=entity_type,
                        odoo_model="product.category",
                        odoo_record_id=record["id"],
                        postgres_entity_id=row.id,
                        match_strategy=strategy,
                        action=action,
                        result_status="SUCCEEDED",
                        odoo_write_date=record.get("write_date"),
                    )
                    self.session.commit()
                except Exception as exc:  # noqa: BLE001 - one bad record must not abort the sweep
                    self.session.rollback()
                    counts.failed += 1
                    self._write_sync_item(
                        run=run,
                        entity_type=entity_type,
                        odoo_model="product.category",
                        odoo_record_id=record["id"],
                        postgres_entity_id=None,
                        match_strategy=None,
                        action="FAILED",
                        result_status="FAILED",
                        error=exc,
                    )
                    self.session.commit()
        except Exception as exc:  # noqa: BLE001 - whole-phase failure must not abort the run
            logger.warning("odoo_catalogue_sync_category_phase_failed", extra={"error": str(exc)})
            self.checkpoints.mark_failed(checkpoint, metadata={"error": str(exc)})
            self.session.commit()
            return counts, id_map

        self.checkpoints.mark_success(
            checkpoint,
            checkpoint_value=(window_start - _CHECKPOINT_SAFETY_BUFFER).strftime(
                _ODOO_DATETIME_FORMAT
            ),
            metadata=counts.as_dict(),
        )
        self.session.commit()
        return counts, id_map

    def _match_and_upsert_category(
        self, record: dict[str, Any]
    ) -> tuple[CatalogueCategory, str, str]:
        odoo_id = record["id"]
        row = self.categories.get_by_odoo_category_id(odoo_id)
        strategy = "ODOO_ID"

        if row is None:
            # Tier 2: adopt a seed-created category by exact name match, so a category
            # already in Postgres from the canonical JSON seed isn't duplicated. Only
            # ever matches a not-yet-mapped row (odoo_category_id is None) — a row
            # already mapped to a different Odoo category can't be "stolen" this way.
            row = next(
                (
                    c
                    for c in self.categories.list_active()
                    if c.odoo_category_id is None and c.name_en == record["name"]
                ),
                None,
            )
            if row is not None:
                strategy = "NATURAL_KEY"

        values: dict[str, Any] = {
            "name_en": record["name"],
            "odoo_category_id": odoo_id,
            "source_system": "odoo",
            "source_updated_at": _parse_odoo_datetime(record.get("write_date")),
            "last_synced_at": datetime.now(UTC),
        }

        if row is None:
            row = CatalogueCategory(
                external_key=f"odoo-category-{odoo_id}",
                code=self._unique_category_code(record["name"], odoo_id),
                slug=self._unique_slug(self.categories, record["name"], odoo_id),
                display_order=0,
                **values,
            )
            self.session.add(row)
            self.session.flush()
            return row, "CREATE", "CREATED"

        changed = any(getattr(row, key) != value for key, value in values.items())
        for key, value in values.items():
            setattr(row, key, value)
        if changed:
            self.session.flush()
        return row, ("UPDATE" if changed else "SKIP_UNCHANGED"), strategy

    def _unique_category_code(self, name: str, odoo_id: int) -> str:
        base = re.sub(r"[^A-Z0-9]+", "-", name.upper()).strip("-")[:16] or "CAT"
        if self.categories.get_by_code(base) is None:
            return base
        return f"{base[:10]}-{odoo_id}"[:20]

    def _unique_slug(self, repo: Any, name: str, odoo_id: int) -> str:
        base = _slugify(name)
        if repo.get_by_slug(base) is None:
            return base
        return f"{base}-{odoo_id}"

    # -- products ---------------------------------------------------------------

    def sync_products(
        self,
        client: OdooClient,
        *,
        run: OdooCatalogueSyncRun,
        full_resync: bool,
        category_id_map: dict[int, uuid.UUID],
    ) -> tuple[EntityCounts, dict[int, uuid.UUID], dict[int, dict[str, Any]]]:
        entity_type = "PRODUCT_TEMPLATE"
        checkpoint = self.checkpoints.get_or_create(INTEGRATION_NAME, entity_type)
        self.checkpoints.mark_running(checkpoint)
        self.session.commit()

        counts = EntityCounts()
        id_map: dict[int, uuid.UUID] = {
            p.odoo_product_template_id: p.id
            for p in self.products.list_active()
            if p.odoo_product_template_id
        }
        template_records: dict[int, dict[str, Any]] = {}
        window_start = datetime.now(UTC)
        domain = self._incremental_domain(checkpoint, full_resync)
        repo = OdooProductRepository(client)

        try:
            for record in repo.iter_all_templates(
                domain=domain, max_records=self.settings.odoo_catalogue_sync_max_records
            ):
                template_records[record["id"]] = record
                try:
                    row, action, strategy = self._match_and_upsert_product(record, category_id_map)
                    id_map[record["id"]] = row.id
                    counts.record(action)
                    self._write_sync_item(
                        run=run,
                        entity_type=entity_type,
                        odoo_model="product.template",
                        odoo_record_id=record["id"],
                        postgres_entity_id=row.id,
                        match_strategy=strategy,
                        action=action,
                        result_status="SUCCEEDED",
                        odoo_write_date=record.get("write_date"),
                    )
                    self.session.commit()
                except Exception as exc:  # noqa: BLE001
                    self.session.rollback()
                    counts.failed += 1
                    self._write_sync_item(
                        run=run,
                        entity_type=entity_type,
                        odoo_model="product.template",
                        odoo_record_id=record["id"],
                        postgres_entity_id=None,
                        match_strategy=None,
                        action="FAILED",
                        result_status="FAILED",
                        error=exc,
                    )
                    self.session.commit()
        except Exception as exc:  # noqa: BLE001
            logger.warning("odoo_catalogue_sync_product_phase_failed", extra={"error": str(exc)})
            self.checkpoints.mark_failed(checkpoint, metadata={"error": str(exc)})
            self.session.commit()
            return counts, id_map, template_records

        self.checkpoints.mark_success(
            checkpoint,
            checkpoint_value=(window_start - _CHECKPOINT_SAFETY_BUFFER).strftime(
                _ODOO_DATETIME_FORMAT
            ),
            metadata=counts.as_dict(),
        )
        self.session.commit()
        return counts, id_map, template_records

    def _match_and_upsert_product(
        self, record: dict[str, Any], category_id_map: dict[int, uuid.UUID]
    ) -> tuple[CatalogueProduct, str, str]:
        odoo_id = record["id"]
        row = self.products.get_by_odoo_product_template_id(odoo_id)
        strategy = "ODOO_ID"

        if row is None and record.get("default_code"):
            candidate = self.products.get_by_sku(record["default_code"])
            if candidate is not None:
                if (
                    candidate.odoo_product_template_id is not None
                    and candidate.odoo_product_template_id != odoo_id
                ):
                    raise ValueError(
                        f"SKU {record['default_code']!r} is already mapped to Odoo template "
                        f"{candidate.odoo_product_template_id}, not {odoo_id} — refusing to "
                        "overwrite."
                    )
                row = candidate
                strategy = "NATURAL_KEY"

        categ_ref = record.get("categ_id")
        category_id = category_id_map.get(categ_ref[0]) if categ_ref else None
        if category_id is None:
            raise ValueError(
                f"Category {categ_ref!r} not resolved for product {odoo_id} — category sync may "
                "have failed or not yet processed this category this run."
            )

        values: dict[str, Any] = {
            "sku": record.get("default_code") or f"odoo-{odoo_id}",
            "name_en": record["name"],
            "description_en": record.get("description_sale"),
            "category_id": category_id,
            "unit_of_measure": record["uom_id"][1] if record.get("uom_id") else None,
            "active": bool(record.get("active", True)),
            "sellable": bool(record.get("sale_ok", True)),
            "odoo_product_template_id": odoo_id,
            "source_system": "odoo",
            "source_updated_at": _parse_odoo_datetime(record.get("write_date")),
            "last_synced_at": datetime.now(UTC),
        }

        if row is None:
            row = CatalogueProduct(
                external_key=f"odoo-product-{odoo_id}",
                slug=self._unique_slug(self.products, record["name"], odoo_id),
                product_type="simple",
                **values,
            )
            self.session.add(row)
            self.session.flush()
            self.merchandising.upsert_for_product(
                row.id,
                {
                    "storefront_visible": True,
                    "featured": False,
                    "is_new": False,
                    "display_order": 0,
                },
            )
            return row, "CREATE", "CREATED"

        changed = any(getattr(row, key) != value for key, value in values.items())
        for key, value in values.items():
            setattr(row, key, value)
        if changed:
            self.session.flush()
        return row, ("UPDATE" if changed else "SKIP_UNCHANGED"), strategy

    # -- variants -----------------------------------------------------------------

    def sync_variants(
        self,
        client: OdooClient,
        *,
        run: OdooCatalogueSyncRun,
        full_resync: bool,
        product_id_map: dict[int, uuid.UUID],
    ) -> tuple[EntityCounts, dict[int, uuid.UUID], dict[int, dict[str, Any]], dict[int, Decimal]]:
        entity_type = "PRODUCT_VARIANT"
        checkpoint = self.checkpoints.get_or_create(INTEGRATION_NAME, entity_type)
        self.checkpoints.mark_running(checkpoint)
        self.session.commit()

        counts = EntityCounts()
        id_map: dict[int, uuid.UUID] = {
            v.odoo_product_variant_id: v.id
            for v in self.variants.list_active()
            if v.odoo_product_variant_id
        }
        variant_records: dict[int, dict[str, Any]] = {}
        price_extra_by_variant: dict[int, Decimal] = {}
        window_start = datetime.now(UTC)
        domain = self._incremental_domain(checkpoint, full_resync)
        repo = OdooProductRepository(client)

        try:
            records = list(
                repo.iter_all_variants(
                    domain=domain, max_records=self.settings.odoo_catalogue_sync_max_records
                )
            )
        except Exception as exc:  # noqa: BLE001 - whole-phase failure must not abort the run
            logger.warning("odoo_catalogue_sync_variant_phase_failed", extra={"error": str(exc)})
            self.checkpoints.mark_failed(checkpoint, metadata={"error": str(exc)})
            self.session.commit()
            return counts, id_map, variant_records, price_extra_by_variant

        # Batch-resolve every attribute combination referenced by this sweep's
        # variants up front — exactly 2 extra Odoo calls for the whole run, never one
        # per variant. Additive/best-effort: a failure here degrades gracefully to "no
        # attribute labels resolved this run" rather than failing the whole variant
        # phase (variants still get matched/created/updated normally below).
        ptav_by_id: dict[int, dict[str, Any]] = {}
        attribute_value_by_id: dict[int, dict[str, Any]] = {}
        try:
            attribute_repo = OdooAttributeRepository(client)
            all_ptav_ids: set[int] = set()
            for record in records:
                all_ptav_ids.update(record.get("product_template_attribute_value_ids") or [])
            if all_ptav_ids:
                ptav_rows = attribute_repo.read_template_attribute_values(list(all_ptav_ids))
                ptav_by_id = {row["id"]: row for row in ptav_rows}
                value_ids = {
                    row["product_attribute_value_id"][0]
                    for row in ptav_rows
                    if row.get("product_attribute_value_id")
                }
                if value_ids:
                    value_rows = attribute_repo.read_attribute_values(list(value_ids))
                    attribute_value_by_id = {row["id"]: row for row in value_rows}
        except OdooIntegrationError as exc:
            logger.warning(
                "odoo_catalogue_sync_variant_attribute_resolution_failed",
                extra={"error": str(exc)},
            )

        try:
            for record in records:
                variant_records[record["id"]] = record
                try:
                    row, action, strategy = self._match_and_upsert_variant(record, product_id_map)
                    id_map[record["id"]] = row.id
                    counts.record(action)

                    resolved_attrs, price_extra = self._resolve_variant_attributes(
                        record, ptav_by_id, attribute_value_by_id
                    )
                    if resolved_attrs:
                        self._upsert_variant_attribute_values(row.id, resolved_attrs)
                    if price_extra:
                        price_extra_by_variant[record["id"]] = price_extra

                    self._write_sync_item(
                        run=run,
                        entity_type=entity_type,
                        odoo_model="product.product",
                        odoo_record_id=record["id"],
                        postgres_entity_id=row.id,
                        match_strategy=strategy,
                        action=action,
                        result_status="SUCCEEDED",
                        odoo_write_date=record.get("write_date"),
                    )
                    self.session.commit()
                except Exception as exc:  # noqa: BLE001
                    self.session.rollback()
                    counts.failed += 1
                    self._write_sync_item(
                        run=run,
                        entity_type=entity_type,
                        odoo_model="product.product",
                        odoo_record_id=record["id"],
                        postgres_entity_id=None,
                        match_strategy=None,
                        action="FAILED",
                        result_status="FAILED",
                        error=exc,
                    )
                    self.session.commit()
        except Exception as exc:  # noqa: BLE001
            logger.warning("odoo_catalogue_sync_variant_phase_failed", extra={"error": str(exc)})
            self.checkpoints.mark_failed(checkpoint, metadata={"error": str(exc)})
            self.session.commit()
            return counts, id_map, variant_records, price_extra_by_variant

        self.checkpoints.mark_success(
            checkpoint,
            checkpoint_value=(window_start - _CHECKPOINT_SAFETY_BUFFER).strftime(
                _ODOO_DATETIME_FORMAT
            ),
            metadata=counts.as_dict(),
        )
        self.session.commit()
        return counts, id_map, variant_records, price_extra_by_variant

    def _match_and_upsert_variant(
        self, record: dict[str, Any], product_id_map: dict[int, uuid.UUID]
    ) -> tuple[CatalogueProductVariant, str, str]:
        odoo_id = record["id"]
        tmpl_ref = record.get("product_tmpl_id")
        product_id = product_id_map.get(tmpl_ref[0]) if tmpl_ref else None
        if product_id is None:
            raise ValueError(
                f"Product template {tmpl_ref!r} not resolved for variant {odoo_id} — product "
                "sync may have failed or not yet processed this template this run."
            )

        row = self.variants.get_by_odoo_product_variant_id(odoo_id)
        strategy = "ODOO_ID"

        if row is None and record.get("default_code"):
            candidate = self.variants.get_by_sku(record["default_code"])
            if candidate is not None:
                if (
                    candidate.odoo_product_variant_id is not None
                    and candidate.odoo_product_variant_id != odoo_id
                ):
                    raise ValueError(
                        f"SKU {record['default_code']!r} is already mapped to Odoo variant "
                        f"{candidate.odoo_product_variant_id}, not {odoo_id} — refusing to "
                        "overwrite."
                    )
                row = candidate
                strategy = "NATURAL_KEY"

        values: dict[str, Any] = {
            "product_id": product_id,
            "sku": record.get("default_code") or f"odoo-variant-{odoo_id}",
            "name_en": record["name"],
            "active": bool(record.get("active", True)),
            "odoo_product_variant_id": odoo_id,
            "source_system": "odoo",
            "source_updated_at": _parse_odoo_datetime(record.get("write_date")),
            "last_synced_at": datetime.now(UTC),
        }

        if row is None:
            values["is_default"] = self.variants.get_default_for_product(product_id) is None
            row = CatalogueProductVariant(external_key=f"odoo-variant-{odoo_id}", **values)
            self.session.add(row)
            self.session.flush()
            return row, "CREATE", "CREATED"

        changed = any(getattr(row, key) != value for key, value in values.items())
        for key, value in values.items():
            setattr(row, key, value)
        if changed:
            self.session.flush()
        return row, ("UPDATE" if changed else "SKIP_UNCHANGED"), strategy

    def _resolve_variant_attributes(
        self,
        record: dict[str, Any],
        ptav_by_id: dict[int, dict[str, Any]],
        attribute_value_by_id: dict[int, dict[str, Any]],
    ) -> tuple[list[ResolvedAttribute], Decimal]:
        """Turns a product.product record's product_template_attribute_value_ids into
        the full per-axis (attribute, value, price_extra) list plus the combination's
        total price_extra — see docs/integrations/odoo-catalogue-variant-model.md's
        Pull direction section for the underlying Odoo model this walks. Any id
        missing from the batch-read lookup dicts (e.g. the batch read failed, or a
        stale reference) is silently skipped for that one axis rather than failing
        the whole variant — partial attribute data is better than none.
        """
        ptav_ids = record.get("product_template_attribute_value_ids") or []
        resolved: list[ResolvedAttribute] = []
        total_extra = Decimal(0)
        used_codes: set[str] = set()

        for ptav_id in ptav_ids:
            ptav = ptav_by_id.get(ptav_id)
            if ptav is None:
                continue
            value_ref = ptav.get("product_attribute_value_id")
            if not value_ref:
                continue
            value_id = value_ref[0]
            attribute_value = attribute_value_by_id.get(value_id)
            if attribute_value is None:
                continue
            attribute_ref = attribute_value.get("attribute_id")
            if not attribute_ref:
                continue
            odoo_attribute_id, attribute_name = attribute_ref[0], attribute_ref[1]
            price_extra = Decimal(str(ptav.get("price_extra") or 0))
            total_extra += price_extra

            code = self._attribute_code_for(odoo_attribute_id, attribute_name, used_codes)
            used_codes.add(code)
            resolved.append(
                ResolvedAttribute(
                    attribute_code=code,
                    odoo_attribute_id=odoo_attribute_id,
                    attribute_name_en=attribute_name,
                    odoo_attribute_value_id=value_id,
                    value_label_en=attribute_value["name"],
                    price_extra=price_extra,
                )
            )

        return resolved, total_extra

    def _attribute_code_for(
        self, odoo_attribute_id: int, attribute_name: str, used_codes: set[str]
    ) -> str:
        """Resolves the stable Postgres attribute_code for an Odoo attribute
        encountered during pull sync. Three-tier ladder:
        1. Reuse — this exact Odoo attribute was already recorded (by a prior
           pull-sync run, or by the push side having created it), reuse its code
           verbatim. The primary path: keeps one Odoo attribute mapped to one code
           everywhere, regardless of which product references it.
        2. Name heuristic — matches every axis name already in use in
           data/catalogue/products.json (_SIZE_ATTRIBUTE_NAMES/_FLAVOR_ATTRIBUTE_NAMES),
           so a familiar-looking ops-defined attribute keeps the "size"/"box" style of
           selector rendering on the storefront even on its very first sync.
        3. Positional fallback for a genuinely unrecognized name — first unmatched
           axis on this variant becomes "size", second becomes "flavor" (still covers
           the common two-axis case), third and beyond get a slugified version of the
           attribute name. The storefront selector (src/routes/product.$id.tsx) renders
           any number of axes generically, so a slugified third-axis code still reaches
           the customer — it just uses the generic list style instead of "size"'s
           bordered-box style, since it has no prior visual precedent.
        """
        existing = self.attribute_values.get_by_odoo_attribute_id(odoo_attribute_id)
        if existing is not None:
            return existing.attribute_code

        lowered = attribute_name.strip().lower()
        if lowered in _SIZE_ATTRIBUTE_NAMES and "size" not in used_codes:
            return "size"
        if lowered in _FLAVOR_ATTRIBUTE_NAMES and "flavor" not in used_codes:
            return "flavor"
        if "size" not in used_codes:
            return "size"
        if "flavor" not in used_codes:
            return "flavor"
        return _slugify(attribute_name)

    def _upsert_variant_attribute_values(
        self, variant_id: uuid.UUID, resolved_attributes: list[ResolvedAttribute]
    ) -> None:
        for attr in resolved_attributes:
            self.attribute_values.upsert_for_variant(
                variant_id,
                attr.attribute_code,
                {
                    "attribute_name_en": attr.attribute_name_en,
                    "value_label_en": attr.value_label_en,
                    "odoo_attribute_id": attr.odoo_attribute_id,
                    "odoo_attribute_value_id": attr.odoo_attribute_value_id,
                },
            )

    # -- prices -----------------------------------------------------------------

    def sync_prices(
        self,
        *,
        run: OdooCatalogueSyncRun,
        variant_id_map: dict[int, uuid.UUID],
        variant_records: dict[int, dict[str, Any]],
        template_records: dict[int, dict[str, Any]],
        price_extra_by_variant: dict[int, Decimal],
    ) -> EntityCounts:
        """No independent Odoo read: reuses the template/variant records already
        fetched by sync_products/sync_variants this run (base price always comes from
        product.template.list_price, plus this combination's summed attribute-value
        price_extra from sync_variants — see _resolve_variant_attributes). Only
        variants actually re-read this run have a price recomputed — a variant
        unchanged since a prior run keeps its existing price row untouched.

        Deliberately the mirror-image of the push side's decision NOT to write
        price_extra (docs/integrations/odoo-catalogue-variant-model.md §4): here, Odoo
        genuinely is the authoritative source for ops-defined per-combination pricing,
        so reading it is the correct direction for that same authority split, not a
        contradiction of the push side's decision (which was about writing, a
        different direction with Postgres as the authority).
        """
        entity_type = "PRODUCT_PRICE"
        checkpoint = self.checkpoints.get_or_create(INTEGRATION_NAME, entity_type)
        self.checkpoints.mark_running(checkpoint)
        self.session.commit()

        counts = EntityCounts()
        try:
            for odoo_variant_id, variant_uuid in variant_id_map.items():
                variant_record = variant_records.get(odoo_variant_id)
                if variant_record is None:
                    continue
                tmpl_ref = variant_record.get("product_tmpl_id")
                if not tmpl_ref:
                    continue
                tmpl_id: int = tmpl_ref[0]
                template_record = template_records.get(tmpl_id)
                if template_record is None:
                    continue
                try:
                    currency = (
                        template_record["currency_id"][1]
                        if template_record.get("currency_id")
                        else "SAR"
                    )
                    amount = Decimal(
                        str(template_record.get("list_price") or 0)
                    ) + price_extra_by_variant.get(odoo_variant_id, Decimal(0))
                    _, created, changed = self.prices.upsert_current(
                        variant_uuid,
                        currency,
                        {
                            "amount": amount,
                            "odoo_pricelist_id": None,
                            "source_system": "odoo",
                            "source_updated_at": _parse_odoo_datetime(
                                template_record.get("write_date")
                            ),
                            "last_synced_at": datetime.now(UTC),
                        },
                    )
                    action = "CREATE" if created else ("UPDATE" if changed else "SKIP_UNCHANGED")
                    counts.record(action)
                    self._write_sync_item(
                        run=run,
                        entity_type=entity_type,
                        odoo_model="product.template",
                        odoo_record_id=tmpl_id,
                        postgres_entity_id=variant_uuid,
                        match_strategy="ODOO_ID",
                        action=action,
                        result_status="SUCCEEDED",
                        odoo_write_date=template_record.get("write_date"),
                    )
                    self.session.commit()
                except Exception as exc:  # noqa: BLE001
                    self.session.rollback()
                    counts.failed += 1
                    self._write_sync_item(
                        run=run,
                        entity_type=entity_type,
                        odoo_model="product.template",
                        odoo_record_id=tmpl_id,
                        postgres_entity_id=variant_uuid,
                        match_strategy=None,
                        action="FAILED",
                        result_status="FAILED",
                        error=exc,
                    )
                    self.session.commit()
        except Exception as exc:  # noqa: BLE001
            logger.warning("odoo_catalogue_sync_price_phase_failed", extra={"error": str(exc)})
            self.checkpoints.mark_failed(checkpoint, metadata={"error": str(exc)})
            self.session.commit()
            return counts

        self.checkpoints.mark_success(
            checkpoint,
            checkpoint_value=datetime.now(UTC).strftime(_ODOO_DATETIME_FORMAT),
            metadata=counts.as_dict(),
        )
        self.session.commit()
        return counts

    # -- images -------------------------------------------------------------------

    def sync_images(
        self,
        client: OdooClient,
        *,
        run: OdooCatalogueSyncRun,
        product_id_map: dict[int, uuid.UUID],
        template_records: dict[int, dict[str, Any]],
    ) -> EntityCounts:
        entity_type = "PRODUCT_IMAGE"
        checkpoint = self.checkpoints.get_or_create(INTEGRATION_NAME, entity_type)
        self.checkpoints.mark_running(checkpoint)
        self.session.commit()

        counts = EntityCounts()
        try:
            # Primary image reuses image_1920 already fetched with the template record
            # this run — no extra Odoo call, and only (re)written for templates this
            # run actually read.
            for tmpl_id, product_uuid in product_id_map.items():
                template_record = template_records.get(tmpl_id)
                if template_record is None or not template_record.get("image_1920"):
                    continue
                try:
                    self._upsert_primary_image(run, product_uuid, template_record, counts)
                    self.session.commit()
                except Exception as exc:  # noqa: BLE001
                    self.session.rollback()
                    counts.failed += 1
                    self._write_sync_item(
                        run=run,
                        entity_type=entity_type,
                        odoo_model="product.template",
                        odoo_record_id=tmpl_id,
                        postgres_entity_id=product_uuid,
                        match_strategy=None,
                        action="FAILED",
                        result_status="FAILED",
                        error=exc,
                    )
                    self.session.commit()

            # Gallery images: a real product.image read, scoped to the templates read
            # this run (an unchanged product's gallery isn't re-swept every run).
            template_ids = list(template_records.keys())
            if template_ids:
                repo = OdooProductImageRepository(client)
                for record in repo.iter_for_templates(
                    template_ids, max_records=self.settings.odoo_catalogue_sync_max_records
                ):
                    tmpl_ref = record.get("product_tmpl_id")
                    gallery_product_uuid = product_id_map.get(tmpl_ref[0]) if tmpl_ref else None
                    if gallery_product_uuid is None:
                        continue
                    try:
                        self._upsert_gallery_image(run, gallery_product_uuid, record, counts)
                        self.session.commit()
                    except Exception as exc:  # noqa: BLE001
                        self.session.rollback()
                        counts.failed += 1
                        self._write_sync_item(
                            run=run,
                            entity_type=entity_type,
                            odoo_model="product.image",
                            odoo_record_id=record["id"],
                            postgres_entity_id=gallery_product_uuid,
                            match_strategy=None,
                            action="FAILED",
                            result_status="FAILED",
                            error=exc,
                        )
                        self.session.commit()
        except Exception as exc:  # noqa: BLE001
            logger.warning("odoo_catalogue_sync_image_phase_failed", extra={"error": str(exc)})
            self.checkpoints.mark_failed(checkpoint, metadata={"error": str(exc)})
            self.session.commit()
            return counts

        self.checkpoints.mark_success(
            checkpoint,
            checkpoint_value=datetime.now(UTC).strftime(_ODOO_DATETIME_FORMAT),
            metadata=counts.as_dict(),
        )
        self.session.commit()
        return counts

    def _upsert_primary_image(
        self,
        run: OdooCatalogueSyncRun,
        product_uuid: uuid.UUID,
        template_record: dict[str, Any],
        counts: EntityCounts,
    ) -> None:
        product = self.products.get_by_id(product_uuid)
        assert product is not None  # invariant: product_id_map only ever holds real rows
        image_bytes = base64.b64decode(template_record["image_1920"])
        relative_path, absolute_url = self.media.save_product_image(
            product.slug, "PRIMARY", 0, image_bytes
        )
        _, created, changed = self.images.upsert_by_product_and_path(
            product_uuid,
            relative_path,
            {
                "image_role": "PRIMARY",
                "display_order": 0,
                "storage_url": absolute_url,
                "source_system": "odoo",
                "source_updated_at": _parse_odoo_datetime(template_record.get("write_date")),
                "last_synced_at": datetime.now(UTC),
            },
        )
        action = "CREATE" if created else ("UPDATE" if changed else "SKIP_UNCHANGED")
        counts.record(action)
        self._write_sync_item(
            run=run,
            entity_type="PRODUCT_IMAGE",
            odoo_model="product.template",
            odoo_record_id=template_record["id"],
            postgres_entity_id=product_uuid,
            match_strategy="ODOO_ID",
            action=action,
            result_status="SUCCEEDED",
            odoo_write_date=template_record.get("write_date"),
        )

    def _upsert_gallery_image(
        self,
        run: OdooCatalogueSyncRun,
        product_uuid: uuid.UUID,
        record: dict[str, Any],
        counts: EntityCounts,
    ) -> None:
        product = self.products.get_by_id(product_uuid)
        assert product is not None
        image_1920 = record.get("image_1920")
        if not image_1920:
            counts.record("SKIP_UNCHANGED")
            self._write_sync_item(
                run=run,
                entity_type="PRODUCT_IMAGE",
                odoo_model="product.image",
                odoo_record_id=record["id"],
                postgres_entity_id=product_uuid,
                match_strategy=None,
                action="SKIP_UNCHANGED",
                result_status="SUCCEEDED",
            )
            return

        image_bytes = base64.b64decode(image_1920)
        display_order = int(record.get("sequence") or 0) + 1  # 0 is reserved for PRIMARY
        relative_path, absolute_url = self.media.save_product_image(
            product.slug, "GALLERY", display_order, image_bytes
        )
        existing = self.images.get_by_odoo_image_id(record["id"])
        strategy = "ODOO_ID" if existing else "CREATED"
        _, created, changed = self.images.upsert_by_product_and_path(
            product_uuid,
            relative_path,
            {
                "image_role": "GALLERY",
                "display_order": display_order,
                "storage_url": absolute_url,
                "odoo_image_id": record["id"],
                "source_system": "odoo",
                "source_updated_at": _parse_odoo_datetime(record.get("write_date")),
                "last_synced_at": datetime.now(UTC),
            },
        )
        action = "CREATE" if created else ("UPDATE" if changed else "SKIP_UNCHANGED")
        counts.record(action)
        self._write_sync_item(
            run=run,
            entity_type="PRODUCT_IMAGE",
            odoo_model="product.image",
            odoo_record_id=record["id"],
            postgres_entity_id=product_uuid,
            match_strategy=strategy,
            action=action,
            result_status="SUCCEEDED",
            odoo_write_date=record.get("write_date"),
        )

    # -- stock ----------------------------------------------------------------------

    def sync_stock(
        self, client: OdooClient, *, run: OdooCatalogueSyncRun, variant_id_map: dict[int, uuid.UUID]
    ) -> EntityCounts:
        """Wraps the entire body in try/except: a "model not installed" failure (the
        real, current condition on the connected Odoo instance — the Inventory app
        isn't installed, see docs/integrations/odoo-operations-runbook.md) degrades
        this one checkpoint to FAILED without ever raising into sync_all, so the rest
        of the run still completes normally.
        """
        entity_type = "PRODUCT_AVAILABILITY"
        checkpoint = self.checkpoints.get_or_create(INTEGRATION_NAME, entity_type)
        self.checkpoints.mark_running(checkpoint)
        self.session.commit()

        counts = EntityCounts()
        if not variant_id_map:
            self.checkpoints.mark_success(
                checkpoint,
                checkpoint_value=datetime.now(UTC).strftime(_ODOO_DATETIME_FORMAT),
                metadata=counts.as_dict(),
            )
            self.session.commit()
            return counts

        repo = OdooStockRepository(client)
        try:
            quantities = repo.get_available_quantities(
                list(variant_id_map.keys()), location_id=self.settings.odoo_stock_location_id
            )
        except Exception as exc:  # noqa: BLE001 - e.g. Inventory app not installed
            logger.warning("odoo_catalogue_sync_stock_unavailable", extra={"error": str(exc)})
            self.checkpoints.mark_failed(checkpoint, metadata={"error": str(exc)})
            self.session.commit()
            return counts

        for odoo_variant_id, variant_uuid in variant_id_map.items():
            qty = quantities.get(odoo_variant_id)
            if qty is None:
                continue
            try:
                status = "AVAILABLE" if qty > 0 else "OUT_OF_STOCK"
                _, created, changed = self.availability.upsert_for_variant(
                    variant_uuid,
                    {
                        "availability_status": status,
                        "quantity_available": max(int(qty), 0),
                        "source_system": "odoo",
                        "last_synced_at": datetime.now(UTC),
                    },
                )
                action = "CREATE" if created else ("UPDATE" if changed else "SKIP_UNCHANGED")
                counts.record(action)
                self._write_sync_item(
                    run=run,
                    entity_type=entity_type,
                    odoo_model="stock.quant",
                    odoo_record_id=odoo_variant_id,
                    postgres_entity_id=variant_uuid,
                    match_strategy="ODOO_ID",
                    action=action,
                    result_status="SUCCEEDED",
                )
                self.session.commit()
            except Exception as exc:  # noqa: BLE001
                self.session.rollback()
                counts.failed += 1
                self._write_sync_item(
                    run=run,
                    entity_type=entity_type,
                    odoo_model="stock.quant",
                    odoo_record_id=odoo_variant_id,
                    postgres_entity_id=variant_uuid,
                    match_strategy=None,
                    action="FAILED",
                    result_status="FAILED",
                    error=exc,
                )
                self.session.commit()

        self.checkpoints.mark_success(
            checkpoint,
            checkpoint_value=datetime.now(UTC).strftime(_ODOO_DATETIME_FORMAT),
            metadata=counts.as_dict(),
        )
        self.session.commit()
        return counts
