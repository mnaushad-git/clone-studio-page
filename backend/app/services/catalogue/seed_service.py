"""Idempotent catalogue seed service.

Loads the six canonical JSON files under data/catalogue/, validates cross-references,
and upserts them into the PostgreSQL catalogue domain in dependency order. Never
deletes or deactivates a row — a missing/removed source record simply isn't touched.

One deliberate scope decision, documented here since it isn't spelled out in the
canonical JSON or the phase's data-ownership docs:

1. Variants: a `product_type == "simple"` product gets exactly one default
   `catalogue_product_variants` row; a `"variant_parent"` product gets one variant per
   combination in the Cartesian product of `variants.attributes[*].values` (e.g. 2
   sizes x 2 flavors = 4 variant rows) — each axis's delta composes additively into
   that combination's price. Every axis of every combination gets a
   `catalogue_product_attribute_values` row — the single source of truth for a
   variant's per-axis data (storefront display, checkout matching, *and* the identity
   the Odoo variant importer adopts product.attribute/product.attribute.value ids
   into — there is no second, JSONB representation to keep in sync with it; see
   docs/integrations/odoo-catalogue-variant-model.md).

2. Storefront sections: product-merchandising.json's `homepage_sections` field is a
   list of bare string labels (e.g. "homepage_products_rail"), not a canonical section
   catalog with real title/description content — no data/catalogue/*.json file defines
   one. Fabricating title_en/description_en from those labels would violate the "do not
   invent content" rule that governs Arabic/English gaps elsewhere in this seed. This
   phase therefore seeds zero storefront_sections/storefront_section_products rows;
   populating them is carried forward as an open item pending real section content
   (see docs/backend/catalogue-seeding.md).
"""

from __future__ import annotations

import itertools
import re
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy.orm import Session

from app.models.integration.seed_run import CatalogueSeedRun
from app.repositories.catalogue import (
    CategoryRepository,
    MomentRepository,
    ProductAttributeValueRepository,
    ProductImageRepository,
    ProductMerchandisingRepository,
    ProductMomentRepository,
    ProductPriceRepository,
    ProductRecipientRepository,
    ProductRecommendationRepository,
    ProductRepository,
    ProductVariantRepository,
    RecipientRepository,
)
from app.repositories.integration.seed_run_repository import SeedRunRepository
from app.services.catalogue.seed_data_loader import CatalogueSeedData, load_catalogue_seed_data

SEED_VERSION = "phase3.v1"


class SeedValidationError(Exception):
    """Raised when the canonical JSON contains a reference the loaded data can't
    resolve (e.g. a product pointing at a category that doesn't exist). Carries every
    issue found, not just the first, so a single run reports the full picture.
    """

    def __init__(self, issues: list[str]) -> None:
        self.issues = issues
        super().__init__("; ".join(issues))


@dataclass
class SeedResult:
    status: str  # "DRY_RUN" | "SUCCESS" | "FAILED"
    started_at: datetime
    completed_at: datetime
    created_count: int = 0
    updated_count: int = 0
    skipped_count: int = 0
    failed_count: int = 0
    error_summary: str | None = None
    counts_by_entity: dict[str, dict[str, int]] = field(default_factory=dict)
    seed_run_id: uuid.UUID | None = None


def _slug_to_code(slug: str) -> str:
    """Mechanical fallback for entities whose canonical JSON has no `code` field
    (moments, recipients) — deterministic and idempotent across re-seeds.
    """
    return re.sub(r"[^A-Z0-9]+", "_", slug.upper()).strip("_")


def _label_to_slug(label: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", label.lower()).strip("-")


class CatalogueSeedService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.categories = CategoryRepository(session)
        self.products = ProductRepository(session)
        self.variants = ProductVariantRepository(session)
        self.attribute_values = ProductAttributeValueRepository(session)
        self.prices = ProductPriceRepository(session)
        self.images = ProductImageRepository(session)
        self.merchandising = ProductMerchandisingRepository(session)
        self.moments = MomentRepository(session)
        self.recipients = RecipientRepository(session)
        self.product_moments = ProductMomentRepository(session)
        self.product_recipients = ProductRecipientRepository(session)
        self.recommendations = ProductRecommendationRepository(session)
        self.seed_runs = SeedRunRepository(session)

        self._counts: dict[str, dict[str, int]] = {}

    def run(self, *, dry_run: bool) -> SeedResult:
        started_at = datetime.now(UTC)
        self._counts = {}

        try:
            data = load_catalogue_seed_data()
            self._validate_references(data)
        except SeedValidationError as exc:
            return self._finalize(
                status="FAILED",
                started_at=started_at,
                error_summary=str(exc),
                source_checksum="",
            )
        except OSError as exc:
            return self._finalize(
                status="FAILED",
                started_at=started_at,
                error_summary=f"Failed to read canonical catalogue files: {exc}",
                source_checksum="",
            )

        savepoint = self.session.begin_nested()
        try:
            category_ids = self._seed_categories(data.categories)
            product_ids = self._seed_products(data.products, category_ids)
            self._seed_variants_and_prices(data.products, product_ids)
            self._seed_images(data.products, product_ids)
            self._seed_merchandising(data.merchandising, product_ids)
            moment_ids = self._seed_moments(data.moments)
            recipient_ids = self._seed_recipients(data.recipients)
            self._seed_product_moments(data.merchandising, product_ids, moment_ids)
            self._seed_product_recipients(data.merchandising, product_ids, recipient_ids)
            self._seed_recommendations(data.recommendations, product_ids)
        except Exception as exc:  # noqa: BLE001 — any failure here must roll back and be reported
            savepoint.rollback()
            return self._finalize(
                status="FAILED",
                started_at=started_at,
                error_summary=f"{type(exc).__name__}: {exc}",
                source_checksum=data.source_checksum,
            )

        if dry_run:
            savepoint.rollback()
            return self._finalize(
                status="DRY_RUN", started_at=started_at, source_checksum=data.source_checksum
            )

        savepoint.commit()
        return self._finalize(
            status="SUCCESS", started_at=started_at, source_checksum=data.source_checksum
        )

    # -- reference validation -----------------------------------------------------

    def _validate_references(self, data: CatalogueSeedData) -> None:
        issues: list[str] = []

        category_keys = {c["external_key"] for c in data.categories}
        for p in data.products:
            ref = p.get("category_external_key")
            if ref not in category_keys:
                issues.append(
                    f"Product {p.get('external_key')} references unknown category {ref!r}"
                )

        product_keys = {p["external_key"] for p in data.products}
        moment_keys = {m["external_key"] for m in data.moments}
        recipient_keys = {r["external_key"] for r in data.recipients}
        seen_merch_products: set[str] = set()
        for m in data.merchandising:
            ref = m.get("product_external_key") or ""
            if ref not in product_keys:
                issues.append(f"Merchandising record references unknown product {ref!r}")
            if ref in seen_merch_products:
                issues.append(f"Duplicate merchandising record for product {ref!r}")
            seen_merch_products.add(ref)
            for moment_ref in m.get("moments") or []:
                if moment_ref not in moment_keys:
                    issues.append(f"Product {ref} references unknown moment {moment_ref!r}")
            for recipient_ref in m.get("recipients") or []:
                if recipient_ref not in recipient_keys:
                    issues.append(f"Product {ref} references unknown recipient {recipient_ref!r}")

        for rec in data.recommendations:
            source = rec.get("product_external_key")
            target = rec.get("recommended_product_external_key")
            if source not in product_keys:
                issues.append(f"Recommendation source product unknown: {source!r}")
            if target not in product_keys:
                issues.append(f"Recommendation target product unknown: {target!r}")
            if source and target and source == target:
                issues.append(f"Product recommends itself: {source!r}")

        if issues:
            raise SeedValidationError(issues)

    # -- per-entity loaders ---------------------------------------------------------

    def _record(self, entity: str, created: bool, changed: bool) -> None:
        bucket = self._counts.setdefault(entity, {"created": 0, "updated": 0, "skipped": 0})
        if created:
            bucket["created"] += 1
        elif changed:
            bucket["updated"] += 1
        else:
            bucket["skipped"] += 1

    def _seed_categories(self, categories: list[dict[str, Any]]) -> dict[str, uuid.UUID]:
        ids: dict[str, uuid.UUID] = {}
        for c in categories:
            obj, created, changed = self.categories.upsert_by_external_key(
                c["external_key"],
                {
                    "code": c["code"],
                    "slug": c["slug"],
                    "name_en": c["name_en"],
                    "name_ar": c.get("name_ar"),
                    "description_en": c.get("description_en"),
                    "description_ar": c.get("description_ar"),
                    "active": c.get("active", True),
                    "display_order": c.get("display_order", 0),
                },
            )
            self._record("categories", created, changed)
            ids[c["external_key"]] = obj.id

        # Second pass: resolve self-referencing parent_id now that every category exists.
        for c in categories:
            parent_ref = c.get("parent_external_key")
            if not parent_ref:
                continue
            category = self.categories.get_by_external_key(c["external_key"])
            assert category is not None
            parent_id = ids[parent_ref]
            if category.parent_id != parent_id:
                category.parent_id = parent_id
                self.session.flush()
        return ids

    def _seed_products(
        self, products: list[dict[str, Any]], category_ids: dict[str, uuid.UUID]
    ) -> dict[str, uuid.UUID]:
        ids: dict[str, uuid.UUID] = {}
        for p in products:
            obj, created, changed = self.products.upsert_by_external_key(
                p["external_key"],
                {
                    "sku": p["sku"],
                    "slug": p["slug"],
                    "name_en": p["name_en"],
                    "name_ar": p.get("name_ar"),
                    "description_en": p.get("description_en"),
                    "description_ar": p.get("description_ar"),
                    "short_description_en": p.get("short_description_en"),
                    "short_description_ar": p.get("short_description_ar"),
                    "category_id": category_ids[p["category_external_key"]],
                    "product_type": p.get("product_type", "simple"),
                    "unit_of_measure": p.get("unit_of_measure"),
                    "active": p.get("active", True),
                    "sellable": p.get("sellable", True),
                },
            )
            self._record("products", created, changed)
            ids[p["external_key"]] = obj.id
        return ids

    def _seed_variants_and_prices(
        self, products: list[dict[str, Any]], product_ids: dict[str, uuid.UUID]
    ) -> None:
        for p in products:
            product_id = product_ids[p["external_key"]]
            currency = p.get("currency", "SAR")
            tax_reference = p.get("tax_reference")
            # Decimal(str(x)), not Decimal(x): converting through the JSON float's repr
            # avoids binary floating-point artifacts (e.g. 7.99 -> Decimal("7.99"), not
            # Decimal("7.9900000000000002")) so re-seeding compares equal to the
            # NUMERIC(10,2) value Postgres returns and stays a true no-op.
            base_price = Decimal(str(p["sales_price"]))
            variants_data = p.get("variants")

            if p.get("product_type") == "variant_parent" and variants_data:
                attributes = variants_data.get("attributes", [])
                self._seed_combinatorial_variants(
                    p, product_id, currency, tax_reference, base_price, attributes
                )
            else:
                external_key = f"{p['external_key']}.variant.default"
                variant_id = self._upsert_variant(
                    product_id=product_id,
                    external_key=external_key,
                    sku=p["sku"],
                    name_en=p["name_en"],
                    is_default=True,
                )
                self._upsert_price(variant_id, currency, base_price, tax_reference)

    def _seed_combinatorial_variants(
        self,
        p: dict[str, Any],
        product_id: uuid.UUID,
        currency: str,
        tax_reference: str | None,
        base_price: Decimal,
        attributes: list[dict[str, Any]],
    ) -> None:
        """One `catalogue_product_variants` row per combination in the Cartesian product
        of every attribute axis's values (e.g. 2 sizes x 2 flavors = 4 rows), each axis's
        delta composing additively into that combination's price. Odoo generates
        `product.product` the same way from `product.template.attribute.line`
        combinations — this keeps Postgres's variant granularity exactly as fine as
        Odoo's, which the Odoo variant importer depends on (each combination needs its
        own unambiguous `odoo_product_variant_id` slot).
        """
        if not attributes:
            return
        value_lists = [axis.get("values", []) for axis in attributes]
        combos = list(itertools.product(*value_lists))
        delta_totals = [
            sum((Decimal(str(v.get("delta", 0))) for v in combo), start=Decimal(0))
            for combo in combos
        ]
        # Exactly one default per product is a DB-enforced invariant
        # (uq_catalogue_product_variants_one_default_per_product) — prefer the first
        # all-zero-delta combination, but always pick one even if every combination
        # happens to carry a nonzero delta.
        default_index = next((i for i, d in enumerate(delta_totals) if d == 0), 0)

        for i, combo in enumerate(combos):
            slugs = [_label_to_slug(v["label"]) for v in combo]
            external_key = f"{p['external_key']}.variant." + ".".join(slugs)
            sku = f"{p['sku']}-" + "-".join(s.upper().replace("-", "") for s in slugs)
            amount = base_price + delta_totals[i]
            name_suffix = " — ".join(v["label"] for v in combo)

            variant_id = self._upsert_variant(
                product_id=product_id,
                external_key=external_key,
                sku=sku,
                name_en=f"{p['name_en']} — {name_suffix}",
                is_default=(i == default_index),
            )
            self._upsert_price(variant_id, currency, amount, tax_reference)

            for axis, value in zip(attributes, combo, strict=True):
                self._upsert_attribute_value(
                    variant_id=variant_id,
                    attribute_code=axis["code"],
                    attribute_name_en=axis["name_en"],
                    value_label_en=value["label"],
                )

    def _upsert_variant(
        self,
        *,
        product_id: uuid.UUID,
        external_key: str,
        sku: str,
        name_en: str,
        is_default: bool,
    ) -> uuid.UUID:
        obj, created, changed = self.variants.upsert_by_external_key(
            external_key,
            {
                "product_id": product_id,
                "sku": sku,
                "name_en": name_en,
                "is_default": is_default,
            },
        )
        self._record("product_variants", created, changed)
        return obj.id

    def _upsert_attribute_value(
        self,
        *,
        variant_id: uuid.UUID,
        attribute_code: str,
        attribute_name_en: str,
        value_label_en: str,
    ) -> None:
        _, created, changed = self.attribute_values.upsert_for_variant(
            variant_id,
            attribute_code,
            {"attribute_name_en": attribute_name_en, "value_label_en": value_label_en},
        )
        self._record("product_attribute_values", created, changed)

    def _upsert_price(
        self, variant_id: uuid.UUID, currency: str, amount: Decimal, tax_reference: str | None
    ) -> None:
        _, created, changed = self.prices.upsert_current(
            variant_id,
            currency,
            {
                "amount": amount,
                "tax_reference": tax_reference,
                # Unresolved business ambiguity (D21) — never assumed either way.
                "price_includes_tax": None,
            },
        )
        self._record("product_prices", created, changed)

    def _seed_images(
        self, products: list[dict[str, Any]], product_ids: dict[str, uuid.UUID]
    ) -> None:
        for p in products:
            product_id = product_ids[p["external_key"]]
            primary = p.get("primary_image")
            if primary:
                self._upsert_image(product_id, primary, role="PRIMARY", display_order=0)
            for idx, img in enumerate(p.get("additional_images") or []):
                self._upsert_image(product_id, img, role="GALLERY", display_order=idx + 1)

    def _upsert_image(
        self, product_id: uuid.UUID, img: dict[str, Any], *, role: str, display_order: int
    ) -> None:
        original_path = img.get("original_path")
        if not original_path:
            return
        _, created, changed = self.images.upsert_by_product_and_path(
            product_id,
            original_path,
            {
                "image_role": role,
                "alt_text_en": img.get("alt_text_en"),
                "alt_text_ar": img.get("alt_text_ar"),
                "display_order": display_order,
                "checksum": img.get("checksum"),
            },
        )
        self._record("product_images", created, changed)

    def _seed_merchandising(
        self, merchandising: list[dict[str, Any]], product_ids: dict[str, uuid.UUID]
    ) -> None:
        for m in merchandising:
            product_id = product_ids.get(m.get("product_external_key", ""))
            if product_id is None:
                continue  # already reported by _validate_references
            _, created, changed = self.merchandising.upsert_for_product(
                product_id,
                {
                    "storefront_visible": m.get("storefront_visible", True),
                    "featured": m.get("featured", False),
                    "is_new": m.get("is_new", False),
                    "is_bestseller": m.get("is_bestseller"),
                    "badge_en": m.get("badge_en"),
                    "badge_ar": m.get("badge_ar"),
                    "display_order": m.get("display_order", 0),
                    "marketing_title_en": m.get("marketing_title_en"),
                    "marketing_title_ar": m.get("marketing_title_ar"),
                    "marketing_description_en": m.get("marketing_description_en"),
                    "marketing_description_ar": m.get("marketing_description_ar"),
                    "seo_title_en": m.get("seo_title_en"),
                    "seo_title_ar": m.get("seo_title_ar"),
                    "seo_description_en": m.get("seo_description_en"),
                    "seo_description_ar": m.get("seo_description_ar"),
                },
            )
            self._record("product_merchandising", created, changed)

    def _seed_moments(self, moments: list[dict[str, Any]]) -> dict[str, uuid.UUID]:
        ids: dict[str, uuid.UUID] = {}
        for mo in moments:
            obj, created, changed = self.moments.upsert_by_external_key(
                mo["external_key"],
                {
                    "code": _slug_to_code(mo["slug"]),
                    "slug": mo["slug"],
                    "name_en": mo["name_en"],
                    "name_ar": mo.get("name_ar"),
                    "description_en": mo.get("description_en"),
                    "description_ar": mo.get("description_ar"),
                    "active": mo.get("active", True),
                    "display_order": mo.get("display_order", 0),
                },
            )
            self._record("moments", created, changed)
            ids[mo["external_key"]] = obj.id
        return ids

    def _seed_recipients(self, recipients: list[dict[str, Any]]) -> dict[str, uuid.UUID]:
        ids: dict[str, uuid.UUID] = {}
        for r in recipients:
            obj, created, changed = self.recipients.upsert_by_external_key(
                r["external_key"],
                {
                    "code": _slug_to_code(r["slug"]),
                    "slug": r["slug"],
                    "name_en": r["name_en"],
                    "name_ar": r.get("name_ar"),
                    "description_en": r.get("description_en"),
                    "description_ar": r.get("description_ar"),
                    "active": r.get("active", True),
                    "display_order": r.get("display_order", 0),
                },
            )
            self._record("recipients", created, changed)
            ids[r["external_key"]] = obj.id
        return ids

    def _seed_product_moments(
        self,
        merchandising: list[dict[str, Any]],
        product_ids: dict[str, uuid.UUID],
        moment_ids: dict[str, uuid.UUID],
    ) -> None:
        for m in merchandising:
            product_id = product_ids.get(m.get("product_external_key", ""))
            if product_id is None:
                continue
            for idx, moment_ref in enumerate(m.get("moments") or []):
                moment_id = moment_ids.get(moment_ref)
                if moment_id is None:
                    continue
                _, created, changed = self.product_moments.upsert(
                    product_id, moment_id, {"display_order": idx, "active": True}
                )
                self._record("product_moments", created, changed)

    def _seed_product_recipients(
        self,
        merchandising: list[dict[str, Any]],
        product_ids: dict[str, uuid.UUID],
        recipient_ids: dict[str, uuid.UUID],
    ) -> None:
        for m in merchandising:
            product_id = product_ids.get(m.get("product_external_key", ""))
            if product_id is None:
                continue
            for idx, recipient_ref in enumerate(m.get("recipients") or []):
                recipient_id = recipient_ids.get(recipient_ref)
                if recipient_id is None:
                    continue
                _, created, changed = self.product_recipients.upsert(
                    product_id, recipient_id, {"display_order": idx, "active": True}
                )
                self._record("product_recipients", created, changed)

    def _seed_recommendations(
        self, recommendations: list[dict[str, Any]], product_ids: dict[str, uuid.UUID]
    ) -> None:
        for rec in recommendations:
            source_id = product_ids.get(rec.get("product_external_key", ""))
            target_id = product_ids.get(rec.get("recommended_product_external_key", ""))
            if source_id is None or target_id is None:
                continue
            rec_type = rec.get("recommendation_type", "MANUAL")
            _, created, changed = self.recommendations.upsert_by_triplet(
                source_id,
                target_id,
                rec_type,
                {"display_order": rec.get("display_order", 0), "active": True},
            )
            self._record("product_recommendations", created, changed)

    # -- finalization -----------------------------------------------------------------

    def _finalize(
        self,
        *,
        status: str,
        started_at: datetime,
        source_checksum: str,
        error_summary: str | None = None,
    ) -> SeedResult:
        completed_at = datetime.now(UTC)
        created = sum(b["created"] for b in self._counts.values())
        updated = sum(b["updated"] for b in self._counts.values())
        skipped = sum(b["skipped"] for b in self._counts.values())
        failed = 1 if status == "FAILED" else 0

        seed_run = CatalogueSeedRun(
            seed_version=SEED_VERSION,
            source_checksum=source_checksum or "unavailable",
            started_at=started_at,
            completed_at=completed_at,
            status=status,
            created_count=created,
            updated_count=updated,
            skipped_count=skipped,
            failed_count=failed,
            error_summary=error_summary,
        )
        self.seed_runs.create(seed_run)

        return SeedResult(
            status=status,
            started_at=started_at,
            completed_at=completed_at,
            created_count=created,
            updated_count=updated,
            skipped_count=skipped,
            failed_count=failed,
            error_summary=error_summary,
            counts_by_entity=dict(self._counts),
            seed_run_id=seed_run.id,
        )
