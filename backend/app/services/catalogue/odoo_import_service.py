"""Phase 5 Odoo catalogue import orchestration.

Ties together: the approval gate (approval_gate.py), read-only matching/planning
(odoo_import_planning.py), the write-capable client (write_client.py), and the
PostgreSQL audit tables (odoo_catalogue_import_runs/items). One class,
OdooCatalogueImportService, backs all five CLI modes (--validate/--plan/--dry-run/
--apply/--reconcile) so they can never disagree about matching or blocking logic —
each mode is a thin wrapper that calls build_import_plan() the same way.

Session/transaction discipline follows CatalogueSeedService's pattern (see
services/catalogue/seed_service.py): this service only add()/flush()es via
repositories, never commits — the calling script owns session.commit().

Odoo/PostgreSQL cannot share a transaction (CLAUDE.md Phase 5 §13). Apply therefore
processes one entity at a time: Odoo write → immediately record + flush the
corresponding odoo_catalogue_import_items row and catalogue odoo_*_id update, before
moving to the next entity. The caller (import_odoo_catalogue.py) commits once at the
end of the whole run. If the process crashes or the final commit fails after some
Odoo writes already succeeded, those items are recoverable on retry: every write is
matched by external key/XML ID *before* a create is attempted (see
odoo_import_planning.py's matching priority), so a re-run adopts the already-created
Odoo record instead of duplicating it — this is the ODOO_WRITE_SUCCEEDED_POSTGRES_
PENDING recovery path described in CLAUDE.md Phase 5 §13, implemented via
re-matching rather than a per-item nested transaction.
"""

from __future__ import annotations

import base64
import json
import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.integrations.odoo.client import OdooClient
from app.integrations.odoo.config import OdooConfig
from app.integrations.odoo.exceptions import OdooConfigurationError, OdooIntegrationError
from app.integrations.odoo.repositories.attributes import OdooAttributeRepository
from app.integrations.odoo.write_client import ImportExecutionContext, OdooWriteClient, WriteAudit
from app.models.integration.odoo_import_item import OdooCatalogueImportItem
from app.models.integration.odoo_import_run import OdooCatalogueImportRun
from app.repositories.catalogue.category_repository import CategoryRepository
from app.repositories.catalogue.product_attribute_value_repository import (
    ProductAttributeValueRepository,
)
from app.repositories.catalogue.product_repository import ProductRepository
from app.repositories.catalogue.product_variant_repository import ProductVariantRepository
from app.repositories.integration.odoo_import_item_repository import OdooImportItemRepository
from app.repositories.integration.odoo_import_run_repository import OdooImportRunRepository
from app.services.catalogue.approval_gate import (
    ApprovalDecision,
    ApprovalFileError,
    evaluate_approval_gate,
    load_business_approvals,
)
from app.services.catalogue.odoo_import_planning import (
    CATALOGUE_DATA_DIR,
    EnvironmentSnapshot,
    ImportPlan,
    ImportPlanItem,
    capture_environment_snapshot,
    compute_import_source_checksum,
    known_attribute_names,
    plan_attributes,
    plan_categories,
    plan_products,
    plan_variants,
    unresolved_attribute_values,
)

logger = logging.getLogger("app.services.catalogue.odoo_import_service")

REPO_ROOT = Path(__file__).resolve().parents[4]


class ImportBlockedError(Exception):
    """Raised (and caught by the caller, never propagated as a crash) when --apply is
    refused before any Odoo write is attempted — missing confirmation, an unresolved
    approval, a stale checksum, or a mismatched environment fingerprint.
    """


@dataclass
class ValidationReport:
    ok: bool
    checks: dict[str, Any] = field(default_factory=dict)
    issues: list[str] = field(default_factory=list)


@dataclass
class ApplyResult:
    run: OdooCatalogueImportRun
    items: list[OdooCatalogueImportItem]
    blocked_reason: str | None = None


def _connect() -> tuple[OdooClient | None, str | None]:
    settings = get_settings()
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


def _load_canonical_catalogue() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    categories = json.loads((CATALOGUE_DATA_DIR / "categories.json").read_text(encoding="utf-8"))[
        "categories"
    ]
    products = json.loads((CATALOGUE_DATA_DIR / "products.json").read_text(encoding="utf-8"))[
        "products"
    ]
    return categories, products


class OdooCatalogueImportService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.categories = CategoryRepository(session)
        self.products = ProductRepository(session)
        self.variants = ProductVariantRepository(session)
        self.attribute_values = ProductAttributeValueRepository(session)
        self.import_runs = OdooImportRunRepository(session)
        self.import_items = OdooImportItemRepository(session)

    # -- shared plan building ---------------------------------------------------------

    def _postgres_odoo_ids(self) -> tuple[dict[str, int], dict[str, int]]:
        category_ids: dict[str, int] = {}
        for cat in self.categories.list_active():
            if cat.odoo_category_id:
                category_ids[cat.external_key] = cat.odoo_category_id
        product_ids: dict[str, int] = {}
        for prod in self.products.list_active():
            if prod.odoo_product_template_id:
                product_ids[prod.external_key] = prod.odoo_product_template_id
        return category_ids, product_ids

    def _postgres_attribute_ids(self) -> tuple[dict[str, int], dict[tuple[str, str], int]]:
        attribute_ids: dict[str, int] = {}
        value_ids: dict[tuple[str, str], int] = {}
        for row in self.attribute_values.list_all():
            if row.odoo_attribute_id:
                attribute_ids.setdefault(row.attribute_name_en, row.odoo_attribute_id)
            if row.odoo_attribute_value_id:
                value_ids[(row.attribute_name_en, row.value_label_en)] = row.odoo_attribute_value_id
        return attribute_ids, value_ids

    def _postgres_variant_ids(self) -> dict[str, int]:
        variant_ids: dict[str, int] = {}
        for v in self.variants.list_active():
            if v.odoo_product_variant_id:
                variant_ids[v.external_key] = v.odoo_product_variant_id
        return variant_ids

    def build_plan(
        self, client: OdooClient | None, connect_failure: str | None, correlation_id: str
    ) -> ImportPlan:
        categories, products = _load_canonical_catalogue()
        try:
            approvals = load_business_approvals()
        except ApprovalFileError:
            approvals = []

        category_odoo_ids, product_odoo_ids = self._postgres_odoo_ids()

        environment: EnvironmentSnapshot | None = None
        if client is not None:
            try:
                environment = capture_environment_snapshot(client)
            except OdooIntegrationError as exc:
                connect_failure = f"Environment snapshot failed: {exc}"
                client = None

        category_items = plan_categories(
            categories, approvals, client, connect_failure, category_odoo_ids, correlation_id
        )
        product_items = plan_products(
            products, approvals, client, connect_failure, product_odoo_ids, correlation_id
        )

        attribute_odoo_ids, attribute_value_odoo_ids = self._postgres_attribute_ids()
        attribute_items = plan_attributes(
            products,
            approvals,
            client,
            connect_failure,
            attribute_odoo_ids,
            attribute_value_odoo_ids,
            correlation_id,
        )
        product_items.extend(attribute_items)
        product_items.extend(
            plan_variants(
                products,
                approvals,
                client,
                connect_failure,
                self._postgres_variant_ids(),
                unresolved_attribute_values(attribute_items),
                correlation_id,
            )
        )

        try:
            approval_checksum = _approval_checksum(approvals)
        except ApprovalFileError:
            approval_checksum = "unavailable"

        return ImportPlan(
            generated_at=datetime.now(UTC).isoformat(),
            environment=environment,
            source_checksum=compute_import_source_checksum(),
            approval_checksum=approval_checksum,
            category_items=category_items,
            product_items=product_items,
            connection_error=connect_failure,
        )

    # -- --validate ---------------------------------------------------------------

    def run_validate(self) -> ValidationReport:
        checks: dict[str, Any] = {}
        issues: list[str] = []

        try:
            categories, products = _load_canonical_catalogue()
            checks["canonical_catalogue"] = {
                "categories": len(categories),
                "products": len(products),
            }
        except (OSError, KeyError) as exc:
            issues.append(f"Canonical catalogue could not be loaded: {exc}")
            checks["canonical_catalogue"] = "FAILED"

        try:
            approvals = load_business_approvals()
            gate = evaluate_approval_gate(approvals)
            checks["approvals"] = gate.to_dict()
            if not gate.all_blocking_resolved:
                issues.append(
                    f"{len(gate.unresolved)} unresolved and {len(gate.rejected)} rejected "
                    "blocking decision(s) — see 'approvals' above"
                )
        except ApprovalFileError as exc:
            issues.append(f"Approval file invalid: {exc}")
            checks["approvals"] = "FAILED"

        client, connect_failure = _connect()
        if client is None:
            issues.append(f"Odoo connectivity/authentication failed: {connect_failure}")
            checks["odoo_connection"] = connect_failure
        else:
            try:
                environment = capture_environment_snapshot(client)
                checks["odoo_environment"] = {
                    "odoo_version": environment.odoo_version,
                    "company_id": environment.company_id,
                    "company_name": environment.company_name,
                    "currency": environment.currency,
                    "fingerprint": environment.fingerprint,
                }
                if environment.currency != "SAR":
                    issues.append(f"Company currency is {environment.currency!r}, expected SAR")
            except OdooIntegrationError as exc:
                issues.append(f"Could not verify Odoo company/currency: {exc}")
                checks["odoo_environment"] = "FAILED"
            finally:
                client.session  # noqa: B018 — no-op access; real cleanup is the transport's

        return ValidationReport(ok=not issues, checks=checks, issues=issues)

    # -- --plan ---------------------------------------------------------------------

    def run_plan(self, *, initiated_by: str, correlation_id: str) -> ImportPlan:
        client, connect_failure = _connect()
        plan = self.build_plan(client, connect_failure, correlation_id)

        run = OdooCatalogueImportRun(
            environment_fingerprint=plan.environment.fingerprint
            if plan.environment
            else "unavailable",
            odoo_version=plan.environment.odoo_version if plan.environment else "unavailable",
            company_id=plan.environment.company_id if plan.environment else 0,
            company_name=plan.environment.company_name if plan.environment else "unavailable",
            currency=plan.environment.currency if plan.environment else "",
            source_checksum=plan.source_checksum,
            approval_checksum=plan.approval_checksum,
            import_plan_checksum=plan.compute_plan_checksum(),
            mode="PLAN",
            status="SUCCEEDED",
            started_at=datetime.now(UTC),
            completed_at=datetime.now(UTC),
            planned_create_count=plan.action_counts.get("CREATE", 0),
            planned_update_count=plan.action_counts.get("UPDATE", 0),
            planned_skip_count=plan.action_counts.get("SKIP", 0),
            planned_blocked_count=plan.action_counts.get("BLOCKED", 0),
            correlation_id=correlation_id,
            initiated_by=initiated_by,
        )
        self.import_runs.create(run)
        return plan

    # -- --dry-run --------------------------------------------------------------------

    def run_dry_run(
        self, *, initiated_by: str, correlation_id: str
    ) -> tuple[ImportPlan, OdooCatalogueImportRun]:
        client, connect_failure = _connect()
        plan = self.build_plan(client, connect_failure, correlation_id)

        run = OdooCatalogueImportRun(
            environment_fingerprint=plan.environment.fingerprint
            if plan.environment
            else "unavailable",
            odoo_version=plan.environment.odoo_version if plan.environment else "unavailable",
            company_id=plan.environment.company_id if plan.environment else 0,
            company_name=plan.environment.company_name if plan.environment else "unavailable",
            currency=plan.environment.currency if plan.environment else "",
            source_checksum=plan.source_checksum,
            approval_checksum=plan.approval_checksum,
            import_plan_checksum=plan.compute_plan_checksum(),
            mode="DRY_RUN",
            status="SUCCEEDED",
            started_at=datetime.now(UTC),
            completed_at=datetime.now(UTC),
            planned_create_count=plan.action_counts.get("CREATE", 0),
            planned_update_count=plan.action_counts.get("UPDATE", 0),
            planned_skip_count=plan.action_counts.get("SKIP", 0),
            planned_blocked_count=plan.action_counts.get("BLOCKED", 0),
            correlation_id=correlation_id,
            initiated_by=initiated_by,
        )
        self.import_runs.create(run)

        for plan_item in plan.all_items:
            item = OdooCatalogueImportItem(
                import_run_id=run.id,
                entity_type=plan_item.entity_type,
                canonical_external_key=plan_item.canonical_external_key,
                canonical_sku=plan_item.canonical_sku,
                canonical_name=plan_item.canonical_name,
                odoo_model=plan_item.odoo_model,
                planned_action=plan_item.planned_action,
                actual_action=None,
                odoo_record_id=plan_item.existing_odoo_id,
                external_xml_id=plan_item.xml_id_name or None,
                proposed_values_json=_json_safe(plan_item.proposed_values),
                result_status="SKIPPED" if plan_item.planned_action != "CREATE" else "PENDING",
            )
            self.import_items.create(item)

        return plan, run

    # -- --apply ----------------------------------------------------------------------

    def run_apply(
        self, *, confirmed: bool, allow_partial: bool, initiated_by: str, correlation_id: str
    ) -> ApplyResult:
        if not confirmed:
            raise ImportBlockedError(
                "--apply requires the explicit --confirm-import flag; refusing to write to Odoo."
            )

        try:
            approvals = load_business_approvals()
        except ApprovalFileError as exc:
            raise ImportBlockedError(f"Approval file could not be evaluated: {exc}") from exc

        gate = evaluate_approval_gate(approvals)
        if not gate.all_blocking_resolved:
            raise ImportBlockedError(
                f"{len(gate.unresolved)} unresolved and {len(gate.rejected)} rejected blocking "
                "approval decision(s) — run check_catalogue_import_approvals for detail."
            )

        client, connect_failure = _connect()
        if client is None:
            raise ImportBlockedError(f"Cannot apply: {connect_failure}")

        plan = self.build_plan(client, None, correlation_id)
        if plan.environment is None:
            raise ImportBlockedError("Cannot apply: Odoo environment could not be verified.")
        if plan.environment.currency != "SAR":
            raise ImportBlockedError(
                f"Cannot apply: company currency is {plan.environment.currency!r}, expected SAR."
            )

        if plan.blocked_items and not allow_partial:
            raise ImportBlockedError(
                f"{len(plan.blocked_items)} item(s) are BLOCKED and --allow-partial was not "
                "given — refusing to write anything. Re-run --plan for detail, or pass "
                "--allow-partial to import only the unblocked items."
            )

        run = OdooCatalogueImportRun(
            environment_fingerprint=plan.environment.fingerprint,
            odoo_version=plan.environment.odoo_version,
            company_id=plan.environment.company_id,
            company_name=plan.environment.company_name,
            currency=plan.environment.currency,
            source_checksum=plan.source_checksum,
            approval_checksum=plan.approval_checksum,
            import_plan_checksum=plan.compute_plan_checksum(),
            mode="APPLY",
            status="RUNNING",
            started_at=datetime.now(UTC),
            planned_create_count=plan.action_counts.get("CREATE", 0),
            planned_update_count=plan.action_counts.get("UPDATE", 0),
            planned_skip_count=plan.action_counts.get("SKIP", 0),
            planned_blocked_count=plan.action_counts.get("BLOCKED", 0),
            correlation_id=correlation_id,
            initiated_by=initiated_by,
        )
        self.import_runs.create(run)

        exec_context = ImportExecutionContext(
            run_id=run.id, correlation_id=correlation_id, initiated_by=initiated_by, mode="APPLY"
        )
        write_client = OdooWriteClient(client.config, client._transport, exec_context)  # noqa: SLF001
        write_client.authenticate()

        items: list[OdooCatalogueImportItem] = []
        category_odoo_ids: dict[str, int] = {}
        product_odoo_ids: dict[str, int] = {}
        failed_count = 0
        created_count = 0
        updated_count = 0
        skipped_count = 0

        for plan_item in plan.category_items:
            item, odoo_id = self._apply_category_item(write_client, plan_item)
            items.append(item)
            if odoo_id:
                category_odoo_ids[plan_item.canonical_external_key] = odoo_id
            if item.result_status == "SUCCEEDED" and item.actual_action == "CREATE":
                created_count += 1
            elif item.result_status == "SUCCEEDED" and item.actual_action == "MATCH":
                updated_count += 1 if item.written_values_json else 0
                skipped_count += 0 if item.written_values_json else 1
            elif item.result_status == "FAILED":
                failed_count += 1
            elif item.result_status in ("BLOCKED", "SKIPPED"):
                skipped_count += 1

        attribute_odoo_ids: dict[str, int] = {}
        attribute_value_odoo_ids: dict[tuple[str, str], int] = {}

        # Dependency order: attributes/values (shared master data, no template
        # dependency) and templates can apply independently of each other, but
        # variants need BOTH resolved first — this loop relies on plan.product_items
        # already being ordered [templates, attributes+values, variants] by build_plan.
        for plan_item in plan.product_items:
            if plan_item.entity_type == "PRODUCT_ATTRIBUTE":
                item, odoo_id = self._apply_attribute_item(write_client, plan_item)
                items.append(item)
                if odoo_id:
                    attribute_odoo_ids[plan_item.canonical_name] = odoo_id
                if item.result_status == "SUCCEEDED" and item.actual_action == "CREATE":
                    created_count += 1
                elif item.result_status == "SUCCEEDED" and item.actual_action == "MATCH":
                    skipped_count += 1
                elif item.result_status == "FAILED":
                    failed_count += 1
                elif item.result_status in ("BLOCKED", "SKIPPED"):
                    skipped_count += 1
                continue

            if plan_item.entity_type == "PRODUCT_ATTRIBUTE_VALUE":
                attr_name = plan_item.proposed_values.get("attribute_name_en", "")
                value_label = plan_item.proposed_values.get("value_label_en", "")
                item, odoo_id = self._apply_attribute_value_item(
                    write_client, plan_item, attribute_odoo_ids.get(attr_name)
                )
                items.append(item)
                if odoo_id:
                    attribute_value_odoo_ids[(attr_name, value_label)] = odoo_id
                if item.result_status == "SUCCEEDED" and item.actual_action == "CREATE":
                    created_count += 1
                elif item.result_status == "SUCCEEDED" and item.actual_action == "MATCH":
                    skipped_count += 1
                elif item.result_status == "FAILED":
                    failed_count += 1
                elif item.result_status in ("BLOCKED", "SKIPPED"):
                    skipped_count += 1
                continue

            if plan_item.entity_type == "PRODUCT_VARIANT":
                template_id = product_odoo_ids.get(
                    plan_item.proposed_values.get("template_external_key", "")
                )
                item, odoo_id = self._apply_variant_item(
                    write_client,
                    plan_item,
                    template_id,
                    attribute_odoo_ids,
                    attribute_value_odoo_ids,
                    client,
                )
                items.append(item)
                if item.result_status == "SUCCEEDED" and item.actual_action == "CREATE":
                    created_count += 1
                elif item.result_status == "SUCCEEDED" and item.actual_action == "MATCH":
                    skipped_count += 1
                elif item.result_status == "FAILED":
                    failed_count += 1
                elif item.result_status in ("BLOCKED", "SKIPPED"):
                    skipped_count += 1
                continue

            categ_id = category_odoo_ids.get(plan_item.category_external_key or "")
            item, odoo_id = self._apply_product_item(write_client, plan_item, categ_id)
            items.append(item)
            if odoo_id:
                product_odoo_ids[plan_item.canonical_external_key] = odoo_id
            if item.result_status == "SUCCEEDED" and item.actual_action == "CREATE":
                created_count += 1
            elif item.result_status == "SUCCEEDED" and item.actual_action == "MATCH":
                updated_count += 1 if item.written_values_json else 0
                skipped_count += 0 if item.written_values_json else 1
            elif item.result_status == "FAILED":
                failed_count += 1
            elif item.result_status in ("BLOCKED", "SKIPPED"):
                skipped_count += 1

        _, canonical_products = _load_canonical_catalogue()
        image_items, image_created, image_matched, image_failed = self._apply_images(
            write_client, canonical_products, product_odoo_ids
        )
        items.extend(image_items)
        created_count += image_created
        skipped_count += image_matched
        failed_count += image_failed

        final_status = "SUCCEEDED"
        if failed_count and (created_count or updated_count):
            final_status = "PARTIALLY_COMPLETED"
        elif failed_count:
            final_status = "FAILED"
        elif plan.blocked_items:
            final_status = "PARTIALLY_COMPLETED"

        self.import_runs.mark_status(
            run,
            final_status,
            completed_at=datetime.now(UTC),
            actual_create_count=created_count,
            actual_update_count=updated_count,
            actual_skip_count=skipped_count,
            actual_failed_count=failed_count,
        )

        return ApplyResult(run=run, items=items)

    def _apply_category_item(
        self, write_client: OdooWriteClient, plan_item: ImportPlanItem
    ) -> tuple[OdooCatalogueImportItem, int | None]:
        started_at = datetime.now(UTC)

        if plan_item.planned_action == "BLOCKED":
            item = OdooCatalogueImportItem(
                import_run_id=write_client.context.run_id,
                entity_type=plan_item.entity_type,
                canonical_external_key=plan_item.canonical_external_key,
                canonical_name=plan_item.canonical_name,
                odoo_model=plan_item.odoo_model,
                planned_action="BLOCKED",
                actual_action="SKIP",
                result_status="BLOCKED",
                error_message="; ".join(plan_item.blocking_issues) or None,
                started_at=started_at,
                completed_at=datetime.now(UTC),
            )
            self.import_items.create(item)
            return item, None

        if plan_item.planned_action == "MATCH":
            odoo_id = plan_item.existing_odoo_id
            item = OdooCatalogueImportItem(
                import_run_id=write_client.context.run_id,
                entity_type=plan_item.entity_type,
                canonical_external_key=plan_item.canonical_external_key,
                canonical_name=plan_item.canonical_name,
                odoo_model=plan_item.odoo_model,
                planned_action="MATCH",
                actual_action="MATCH",
                odoo_record_id=odoo_id,
                external_xml_id=plan_item.xml_id_name,
                proposed_values_json=_json_safe(plan_item.proposed_values),
                result_status="SUCCEEDED",
                started_at=started_at,
                completed_at=datetime.now(UTC),
            )
            self.import_items.create(item)
            self._adopt_category_odoo_id(plan_item.canonical_external_key, odoo_id)
            return item, odoo_id

        # CREATE
        try:
            audit = WriteAudit(
                entity_type="CATEGORY",
                canonical_external_key=plan_item.canonical_external_key,
                planned_operation="CREATE",
            )
            odoo_id = write_client.create(
                "product.category", plan_item.proposed_values, audit=audit
            )
            self._pin_xml_id(write_client, "product.category", plan_item.xml_id_name, odoo_id)
            self._adopt_category_odoo_id(plan_item.canonical_external_key, odoo_id)

            item = OdooCatalogueImportItem(
                import_run_id=write_client.context.run_id,
                entity_type=plan_item.entity_type,
                canonical_external_key=plan_item.canonical_external_key,
                canonical_name=plan_item.canonical_name,
                odoo_model=plan_item.odoo_model,
                planned_action="CREATE",
                actual_action="CREATE",
                odoo_record_id=odoo_id,
                external_xml_id=plan_item.xml_id_name,
                proposed_values_json=_json_safe(plan_item.proposed_values),
                written_values_json=_json_safe(plan_item.proposed_values),
                result_status="SUCCEEDED",
                started_at=started_at,
                completed_at=datetime.now(UTC),
            )
            self.import_items.create(item)
            return item, odoo_id
        except OdooIntegrationError as exc:
            item = OdooCatalogueImportItem(
                import_run_id=write_client.context.run_id,
                entity_type=plan_item.entity_type,
                canonical_external_key=plan_item.canonical_external_key,
                canonical_name=plan_item.canonical_name,
                odoo_model=plan_item.odoo_model,
                planned_action="CREATE",
                actual_action="CREATE",
                result_status="FAILED",
                error_code=type(exc).__name__,
                error_message=str(exc),
                started_at=started_at,
                completed_at=datetime.now(UTC),
            )
            self.import_items.create(item)
            return item, None

    def _apply_product_item(
        self, write_client: OdooWriteClient, plan_item: ImportPlanItem, categ_id: int | None
    ) -> tuple[OdooCatalogueImportItem, int | None]:
        started_at = datetime.now(UTC)

        if plan_item.planned_action == "BLOCKED":
            item = OdooCatalogueImportItem(
                import_run_id=write_client.context.run_id,
                entity_type=plan_item.entity_type,
                canonical_external_key=plan_item.canonical_external_key,
                canonical_sku=plan_item.canonical_sku,
                canonical_name=plan_item.canonical_name,
                odoo_model=plan_item.odoo_model,
                planned_action="BLOCKED",
                actual_action="SKIP",
                result_status="BLOCKED",
                error_message="; ".join(plan_item.blocking_issues) or None,
                started_at=started_at,
                completed_at=datetime.now(UTC),
            )
            self.import_items.create(item)
            return item, None

        if plan_item.planned_action == "MATCH":
            odoo_id = plan_item.existing_odoo_id
            item = OdooCatalogueImportItem(
                import_run_id=write_client.context.run_id,
                entity_type=plan_item.entity_type,
                canonical_external_key=plan_item.canonical_external_key,
                canonical_sku=plan_item.canonical_sku,
                canonical_name=plan_item.canonical_name,
                odoo_model=plan_item.odoo_model,
                planned_action="MATCH",
                actual_action="MATCH",
                odoo_record_id=odoo_id,
                external_xml_id=plan_item.xml_id_name,
                proposed_values_json=_json_safe(plan_item.proposed_values),
                result_status="SUCCEEDED",
                started_at=started_at,
                completed_at=datetime.now(UTC),
            )
            self.import_items.create(item)
            self._adopt_product_odoo_id(plan_item.canonical_external_key, odoo_id)
            return item, odoo_id

        # CREATE — categ_id must be resolved (the category pass ran first).
        if categ_id is None:
            item = OdooCatalogueImportItem(
                import_run_id=write_client.context.run_id,
                entity_type=plan_item.entity_type,
                canonical_external_key=plan_item.canonical_external_key,
                canonical_sku=plan_item.canonical_sku,
                canonical_name=plan_item.canonical_name,
                odoo_model=plan_item.odoo_model,
                planned_action="CREATE",
                actual_action="SKIP",
                result_status="FAILED",
                error_code="CATEGORY_NOT_RESOLVED",
                error_message=(
                    f"Category {plan_item.category_external_key!r} was not created/matched in "
                    "this run — cannot resolve categ_id for this product."
                ),
                started_at=started_at,
                completed_at=datetime.now(UTC),
            )
            self.import_items.create(item)
            return item, None

        values = dict(plan_item.proposed_values)
        values["categ_id"] = categ_id

        try:
            audit = WriteAudit(
                entity_type="PRODUCT_TEMPLATE",
                canonical_external_key=plan_item.canonical_external_key,
                planned_operation="CREATE",
            )
            odoo_id = write_client.create("product.template", values, audit=audit)
            self._pin_xml_id(write_client, "product.template", plan_item.xml_id_name, odoo_id)
            self._adopt_product_odoo_id(plan_item.canonical_external_key, odoo_id)

            item = OdooCatalogueImportItem(
                import_run_id=write_client.context.run_id,
                entity_type=plan_item.entity_type,
                canonical_external_key=plan_item.canonical_external_key,
                canonical_sku=plan_item.canonical_sku,
                canonical_name=plan_item.canonical_name,
                odoo_model=plan_item.odoo_model,
                planned_action="CREATE",
                actual_action="CREATE",
                odoo_record_id=odoo_id,
                external_xml_id=plan_item.xml_id_name,
                proposed_values_json=_json_safe(values),
                written_values_json=_json_safe(values),
                result_status="SUCCEEDED",
                started_at=started_at,
                completed_at=datetime.now(UTC),
            )
            self.import_items.create(item)
            return item, odoo_id
        except OdooIntegrationError as exc:
            item = OdooCatalogueImportItem(
                import_run_id=write_client.context.run_id,
                entity_type=plan_item.entity_type,
                canonical_external_key=plan_item.canonical_external_key,
                canonical_sku=plan_item.canonical_sku,
                canonical_name=plan_item.canonical_name,
                odoo_model=plan_item.odoo_model,
                planned_action="CREATE",
                actual_action="CREATE",
                result_status="FAILED",
                error_code=type(exc).__name__,
                error_message=str(exc),
                started_at=started_at,
                completed_at=datetime.now(UTC),
            )
            self.import_items.create(item)
            return item, None

    def _apply_attribute_item(
        self, write_client: OdooWriteClient, plan_item: ImportPlanItem
    ) -> tuple[OdooCatalogueImportItem, int | None]:
        """Mirrors _apply_category_item's MATCH/CREATE/BLOCKED shape, with one
        difference: a MATCH/CREATE here fans its odoo_attribute_id out to every
        Postgres row sharing this attribute name (N:1 — many products/variants can
        reference the same shared "Flavor" attribute), unlike category/product ids
        which are always 1:1 with a single row.
        """
        started_at = datetime.now(UTC)

        if plan_item.planned_action == "BLOCKED":
            item = OdooCatalogueImportItem(
                import_run_id=write_client.context.run_id,
                entity_type=plan_item.entity_type,
                canonical_external_key=plan_item.canonical_external_key,
                canonical_name=plan_item.canonical_name,
                odoo_model=plan_item.odoo_model,
                planned_action="BLOCKED",
                actual_action="SKIP",
                odoo_record_id=plan_item.existing_odoo_id,
                result_status="BLOCKED",
                error_message="; ".join(plan_item.blocking_issues) or None,
                started_at=started_at,
                completed_at=datetime.now(UTC),
            )
            self.import_items.create(item)
            return item, None

        if plan_item.planned_action == "MATCH":
            odoo_id = plan_item.existing_odoo_id
            item = OdooCatalogueImportItem(
                import_run_id=write_client.context.run_id,
                entity_type=plan_item.entity_type,
                canonical_external_key=plan_item.canonical_external_key,
                canonical_name=plan_item.canonical_name,
                odoo_model=plan_item.odoo_model,
                planned_action="MATCH",
                actual_action="MATCH",
                odoo_record_id=odoo_id,
                result_status="SUCCEEDED",
                started_at=started_at,
                completed_at=datetime.now(UTC),
            )
            self.import_items.create(item)
            self._adopt_attribute_odoo_id(plan_item.canonical_name, odoo_id)
            return item, odoo_id

        # CREATE
        try:
            audit = WriteAudit(
                entity_type="PRODUCT_ATTRIBUTE",
                canonical_external_key=plan_item.canonical_external_key,
                planned_operation="CREATE",
            )
            odoo_id = write_client.create(
                "product.attribute", plan_item.proposed_values, audit=audit
            )
            self._adopt_attribute_odoo_id(plan_item.canonical_name, odoo_id)

            item = OdooCatalogueImportItem(
                import_run_id=write_client.context.run_id,
                entity_type=plan_item.entity_type,
                canonical_external_key=plan_item.canonical_external_key,
                canonical_name=plan_item.canonical_name,
                odoo_model=plan_item.odoo_model,
                planned_action="CREATE",
                actual_action="CREATE",
                odoo_record_id=odoo_id,
                proposed_values_json=_json_safe(plan_item.proposed_values),
                written_values_json=_json_safe(plan_item.proposed_values),
                result_status="SUCCEEDED",
                started_at=started_at,
                completed_at=datetime.now(UTC),
            )
            self.import_items.create(item)
            return item, odoo_id
        except OdooIntegrationError as exc:
            item = OdooCatalogueImportItem(
                import_run_id=write_client.context.run_id,
                entity_type=plan_item.entity_type,
                canonical_external_key=plan_item.canonical_external_key,
                canonical_name=plan_item.canonical_name,
                odoo_model=plan_item.odoo_model,
                planned_action="CREATE",
                actual_action="CREATE",
                result_status="FAILED",
                error_code=type(exc).__name__,
                error_message=str(exc),
                started_at=started_at,
                completed_at=datetime.now(UTC),
            )
            self.import_items.create(item)
            return item, None

    def _apply_attribute_value_item(
        self,
        write_client: OdooWriteClient,
        plan_item: ImportPlanItem,
        attribute_odoo_id: int | None,
    ) -> tuple[OdooCatalogueImportItem, int | None]:
        started_at = datetime.now(UTC)

        if plan_item.planned_action == "BLOCKED":
            item = OdooCatalogueImportItem(
                import_run_id=write_client.context.run_id,
                entity_type=plan_item.entity_type,
                canonical_external_key=plan_item.canonical_external_key,
                canonical_name=plan_item.canonical_name,
                odoo_model=plan_item.odoo_model,
                planned_action="BLOCKED",
                actual_action="SKIP",
                odoo_record_id=plan_item.existing_odoo_id,
                result_status="BLOCKED",
                error_message="; ".join(plan_item.blocking_issues) or None,
                started_at=started_at,
                completed_at=datetime.now(UTC),
            )
            self.import_items.create(item)
            return item, None

        if plan_item.planned_action == "MATCH":
            odoo_id = plan_item.existing_odoo_id
            item = OdooCatalogueImportItem(
                import_run_id=write_client.context.run_id,
                entity_type=plan_item.entity_type,
                canonical_external_key=plan_item.canonical_external_key,
                canonical_name=plan_item.canonical_name,
                odoo_model=plan_item.odoo_model,
                planned_action="MATCH",
                actual_action="MATCH",
                odoo_record_id=odoo_id,
                result_status="SUCCEEDED",
                started_at=started_at,
                completed_at=datetime.now(UTC),
            )
            self.import_items.create(item)
            self._adopt_attribute_value_odoo_id(plan_item, odoo_id)
            return item, odoo_id

        # CREATE — requires the parent attribute's real id, resolved earlier in this
        # same apply pass (attributes are processed before their values in plan
        # order — see plan_attributes()).
        if attribute_odoo_id is None:
            item = OdooCatalogueImportItem(
                import_run_id=write_client.context.run_id,
                entity_type=plan_item.entity_type,
                canonical_external_key=plan_item.canonical_external_key,
                canonical_name=plan_item.canonical_name,
                odoo_model=plan_item.odoo_model,
                planned_action="CREATE",
                actual_action="SKIP",
                result_status="FAILED",
                error_code="ATTRIBUTE_NOT_RESOLVED",
                error_message=(
                    "Parent attribute was not created/matched in this run — cannot create "
                    "its value."
                ),
                started_at=started_at,
                completed_at=datetime.now(UTC),
            )
            self.import_items.create(item)
            return item, None

        values = {
            k: v
            for k, v in plan_item.proposed_values.items()
            if k not in ("attribute_name_en", "value_label_en")
        }
        values["attribute_id"] = attribute_odoo_id

        try:
            audit = WriteAudit(
                entity_type="PRODUCT_ATTRIBUTE_VALUE",
                canonical_external_key=plan_item.canonical_external_key,
                planned_operation="CREATE",
            )
            odoo_id = write_client.create("product.attribute.value", values, audit=audit)
            self._adopt_attribute_value_odoo_id(plan_item, odoo_id)

            item = OdooCatalogueImportItem(
                import_run_id=write_client.context.run_id,
                entity_type=plan_item.entity_type,
                canonical_external_key=plan_item.canonical_external_key,
                canonical_name=plan_item.canonical_name,
                odoo_model=plan_item.odoo_model,
                planned_action="CREATE",
                actual_action="CREATE",
                odoo_record_id=odoo_id,
                proposed_values_json=_json_safe(values),
                written_values_json=_json_safe(values),
                result_status="SUCCEEDED",
                started_at=started_at,
                completed_at=datetime.now(UTC),
            )
            self.import_items.create(item)
            return item, odoo_id
        except OdooIntegrationError as exc:
            item = OdooCatalogueImportItem(
                import_run_id=write_client.context.run_id,
                entity_type=plan_item.entity_type,
                canonical_external_key=plan_item.canonical_external_key,
                canonical_name=plan_item.canonical_name,
                odoo_model=plan_item.odoo_model,
                planned_action="CREATE",
                actual_action="CREATE",
                result_status="FAILED",
                error_code=type(exc).__name__,
                error_message=str(exc),
                started_at=started_at,
                completed_at=datetime.now(UTC),
            )
            self.import_items.create(item)
            return item, None

    def _apply_variant_item(
        self,
        write_client: OdooWriteClient,
        plan_item: ImportPlanItem,
        template_id: int | None,
        attribute_odoo_ids: dict[str, int],
        attribute_value_odoo_ids: dict[tuple[str, str], int],
        read_client: OdooClient,
    ) -> tuple[OdooCatalogueImportItem, int | None]:
        """CREATE has no direct product.product.create call (not on the allowlist,
        deliberately — Odoo auto-generates combination variants as a side effect of
        product.template.attribute.line writes). This: (1) ensures each referenced
        attribute line exists on the template with its value included (ADD via (4, id),
        never REPLACE, so existing combinations already in Odoo are never disturbed),
        (2) reads product.product back by product_tmpl_id and matches the one whose
        product.template.attribute.value combination equals this plan item's exactly,
        (3) writes default_code onto the matched variant.
        """
        started_at = datetime.now(UTC)

        if plan_item.planned_action == "BLOCKED":
            item = OdooCatalogueImportItem(
                import_run_id=write_client.context.run_id,
                entity_type=plan_item.entity_type,
                canonical_external_key=plan_item.canonical_external_key,
                canonical_sku=plan_item.canonical_sku,
                canonical_name=plan_item.canonical_name,
                odoo_model=plan_item.odoo_model,
                planned_action="BLOCKED",
                actual_action="SKIP",
                odoo_record_id=plan_item.existing_odoo_id,
                result_status="BLOCKED",
                error_message="; ".join(plan_item.blocking_issues) or None,
                started_at=started_at,
                completed_at=datetime.now(UTC),
            )
            self.import_items.create(item)
            return item, None

        if plan_item.planned_action == "MATCH":
            odoo_id = plan_item.existing_odoo_id
            item = OdooCatalogueImportItem(
                import_run_id=write_client.context.run_id,
                entity_type=plan_item.entity_type,
                canonical_external_key=plan_item.canonical_external_key,
                canonical_sku=plan_item.canonical_sku,
                canonical_name=plan_item.canonical_name,
                odoo_model=plan_item.odoo_model,
                planned_action="MATCH",
                actual_action="MATCH",
                odoo_record_id=odoo_id,
                result_status="SUCCEEDED",
                started_at=started_at,
                completed_at=datetime.now(UTC),
            )
            self.import_items.create(item)
            self._adopt_variant_odoo_id(plan_item.canonical_external_key, odoo_id)
            return item, odoo_id

        # CREATE — the template pass must have already resolved this product's template.
        if template_id is None:
            item = OdooCatalogueImportItem(
                import_run_id=write_client.context.run_id,
                entity_type=plan_item.entity_type,
                canonical_external_key=plan_item.canonical_external_key,
                canonical_sku=plan_item.canonical_sku,
                canonical_name=plan_item.canonical_name,
                odoo_model=plan_item.odoo_model,
                planned_action="CREATE",
                actual_action="SKIP",
                result_status="FAILED",
                error_code="TEMPLATE_NOT_RESOLVED",
                error_message=(
                    "Product template was not created/matched in this run — cannot "
                    "resolve product_tmpl_id for this variant."
                ),
                started_at=started_at,
                completed_at=datetime.now(UTC),
            )
            self.import_items.create(item)
            return item, None

        resolved_pairs: list[tuple[int, int]] = []
        for pair in plan_item.proposed_values.get("attribute_lines", []):
            attr_id = attribute_odoo_ids.get(pair["attribute_name_en"])
            value_id = attribute_value_odoo_ids.get(
                (pair["attribute_name_en"], pair["value_label_en"])
            )
            if attr_id is None or value_id is None:
                item = OdooCatalogueImportItem(
                    import_run_id=write_client.context.run_id,
                    entity_type=plan_item.entity_type,
                    canonical_external_key=plan_item.canonical_external_key,
                    canonical_sku=plan_item.canonical_sku,
                    canonical_name=plan_item.canonical_name,
                    odoo_model=plan_item.odoo_model,
                    planned_action="CREATE",
                    actual_action="SKIP",
                    result_status="FAILED",
                    error_code="ATTRIBUTE_NOT_RESOLVED",
                    error_message=(
                        f"Attribute/value not resolved this run: "
                        f"{pair['attribute_name_en']!r}={pair['value_label_en']!r}"
                    ),
                    started_at=started_at,
                    completed_at=datetime.now(UTC),
                )
                self.import_items.create(item)
                return item, None
            resolved_pairs.append((attr_id, value_id))

        correlation_id = write_client.context.correlation_id
        attribute_repo = OdooAttributeRepository(read_client)

        try:
            for attr_id, value_id in resolved_pairs:
                existing_lines = attribute_repo.find_template_attribute_line(
                    template_id, attr_id, correlation_id=correlation_id
                )
                if existing_lines:
                    line = existing_lines[0]
                    current_value_ids = set(line.get("value_ids") or [])
                    if value_id not in current_value_ids:
                        audit = WriteAudit(
                            entity_type="PRODUCT_VARIANT",
                            canonical_external_key=plan_item.canonical_external_key,
                            planned_operation="UPDATE",
                            before_state={"value_ids": sorted(current_value_ids)},
                        )
                        write_client.write(
                            "product.template.attribute.line",
                            [line["id"]],
                            {"value_ids": [(4, value_id)]},
                            audit=audit,
                        )
                else:
                    audit = WriteAudit(
                        entity_type="PRODUCT_VARIANT",
                        canonical_external_key=plan_item.canonical_external_key,
                        planned_operation="CREATE",
                    )
                    write_client.create(
                        "product.template.attribute.line",
                        {
                            "product_tmpl_id": template_id,
                            "attribute_id": attr_id,
                            "value_ids": [(6, 0, [value_id])],
                        },
                        audit=audit,
                    )

            matched_variant_id = self._find_matching_variant(
                read_client, template_id, {v for _, v in resolved_pairs}, correlation_id
            )
            if matched_variant_id is None:
                item = OdooCatalogueImportItem(
                    import_run_id=write_client.context.run_id,
                    entity_type=plan_item.entity_type,
                    canonical_external_key=plan_item.canonical_external_key,
                    canonical_sku=plan_item.canonical_sku,
                    canonical_name=plan_item.canonical_name,
                    odoo_model=plan_item.odoo_model,
                    planned_action="CREATE",
                    actual_action="CREATE",
                    result_status="FAILED",
                    error_code="VARIANT_COMBINATION_NOT_FOUND",
                    error_message=(
                        "Attribute lines were written but no matching product.product "
                        "combination was found on read-back."
                    ),
                    started_at=started_at,
                    completed_at=datetime.now(UTC),
                )
                self.import_items.create(item)
                return item, None

            default_code = plan_item.proposed_values.get("default_code")
            written_values: dict[str, Any] = {}
            if default_code:
                audit = WriteAudit(
                    entity_type="PRODUCT_VARIANT",
                    canonical_external_key=plan_item.canonical_external_key,
                    planned_operation="UPDATE",
                    before_state={"default_code": None},
                )
                write_client.write(
                    "product.product",
                    [matched_variant_id],
                    {"default_code": default_code},
                    audit=audit,
                )
                written_values["default_code"] = default_code

            self._adopt_variant_odoo_id(plan_item.canonical_external_key, matched_variant_id)

            item = OdooCatalogueImportItem(
                import_run_id=write_client.context.run_id,
                entity_type=plan_item.entity_type,
                canonical_external_key=plan_item.canonical_external_key,
                canonical_sku=plan_item.canonical_sku,
                canonical_name=plan_item.canonical_name,
                odoo_model=plan_item.odoo_model,
                planned_action="CREATE",
                actual_action="CREATE",
                odoo_record_id=matched_variant_id,
                proposed_values_json=_json_safe(plan_item.proposed_values),
                written_values_json=_json_safe(written_values),
                result_status="SUCCEEDED",
                started_at=started_at,
                completed_at=datetime.now(UTC),
            )
            self.import_items.create(item)
            return item, matched_variant_id
        except OdooIntegrationError as exc:
            item = OdooCatalogueImportItem(
                import_run_id=write_client.context.run_id,
                entity_type=plan_item.entity_type,
                canonical_external_key=plan_item.canonical_external_key,
                canonical_sku=plan_item.canonical_sku,
                canonical_name=plan_item.canonical_name,
                odoo_model=plan_item.odoo_model,
                planned_action="CREATE",
                actual_action="CREATE",
                result_status="FAILED",
                error_code=type(exc).__name__,
                error_message=str(exc),
                started_at=started_at,
                completed_at=datetime.now(UTC),
            )
            self.import_items.create(item)
            return item, None

    @staticmethod
    def _find_matching_variant(
        read_client: OdooClient,
        template_id: int,
        target_value_ids: set[int],
        correlation_id: str,
    ) -> int | None:
        """Reads product.product back by product_tmpl_id (Odoo has already
        auto-generated/updated these as a side effect of the attribute-line writes)
        and returns the id whose combination of underlying product.attribute.value ids
        exactly equals target_value_ids — never inferred from a create() return value,
        since this client never calls product.product.create directly.
        """
        variants = read_client.search_read(
            "product.product",
            [["product_tmpl_id", "=", template_id]],
            ["id", "product_template_attribute_value_ids"],
            correlation_id=correlation_id,
        )
        for variant in variants.records:
            ptav_ids = variant.get("product_template_attribute_value_ids") or []
            if not ptav_ids:
                continue
            ptavs = read_client.read(
                "product.template.attribute.value",
                ptav_ids,
                ["product_attribute_value_id"],
                correlation_id=correlation_id,
            )
            combo_value_ids = set()
            for row in ptavs:
                raw = row.get("product_attribute_value_id")
                combo_value_ids.add(raw[0] if isinstance(raw, list) else raw)
            if combo_value_ids == target_value_ids:
                return int(variant["id"])
        return None

    def _apply_images(
        self,
        write_client: OdooWriteClient,
        products: list[dict[str, Any]],
        product_odoo_ids: dict[str, int],
    ) -> tuple[list[OdooCatalogueImportItem], int, int, int]:
        """Uploads the primary image (product.template.image_1920) and gallery images
        (product.image) for every product whose template was created/matched this run.
        Idempotent across runs: before uploading, checks whether a prior run already
        succeeded for the same image external key (product_external_key + role +
        display_order) via the import-items audit table — never re-uploads a
        previously-imported image just because it appears again in a later run.
        """
        items: list[OdooCatalogueImportItem] = []
        created = matched = failed = 0

        for product in products:
            template_id = product_odoo_ids.get(product["external_key"])
            if template_id is None:
                continue

            primary = product.get("primary_image")
            if primary and primary.get("original_path"):
                item, outcome = self._apply_one_image(
                    write_client, product, template_id, primary, role="PRIMARY", display_order=0
                )
                items.append(item)
                created += outcome == "CREATE"
                matched += outcome == "MATCH"
                failed += outcome == "FAILED"

            for idx, img in enumerate(product.get("additional_images") or []):
                if not img.get("original_path"):
                    continue
                item, outcome = self._apply_one_image(
                    write_client, product, template_id, img, role="GALLERY", display_order=idx + 1
                )
                items.append(item)
                created += outcome == "CREATE"
                matched += outcome == "MATCH"
                failed += outcome == "FAILED"

        return items, created, matched, failed

    def _apply_one_image(
        self,
        write_client: OdooWriteClient,
        product: dict[str, Any],
        template_id: int,
        img: dict[str, Any],
        *,
        role: str,
        display_order: int,
    ) -> tuple[OdooCatalogueImportItem, str]:
        started_at = datetime.now(UTC)
        image_external_key = f"{product['external_key']}.image.{role.lower()}.{display_order}"

        prior = self.import_items.find_latest_by_external_key_across_runs(image_external_key)
        if prior is not None:
            item = OdooCatalogueImportItem(
                import_run_id=write_client.context.run_id,
                entity_type="PRODUCT_IMAGE",
                canonical_external_key=image_external_key,
                canonical_name=product["name_en"],
                odoo_model=prior.odoo_model,
                planned_action="MATCH",
                actual_action="MATCH",
                odoo_record_id=prior.odoo_record_id,
                result_status="SUCCEEDED",
                started_at=started_at,
                completed_at=datetime.now(UTC),
            )
            self.import_items.create(item)
            return item, "MATCH"

        encoded = encode_image_base64(img["original_path"])
        if encoded is None:
            item = OdooCatalogueImportItem(
                import_run_id=write_client.context.run_id,
                entity_type="PRODUCT_IMAGE",
                canonical_external_key=image_external_key,
                canonical_name=product["name_en"],
                odoo_model="product.template" if role == "PRIMARY" else "product.image",
                planned_action="CREATE",
                actual_action="SKIP",
                result_status="FAILED",
                error_code="IMAGE_FILE_NOT_FOUND",
                error_message=f"original_path not found on disk: {img['original_path']!r}",
                started_at=started_at,
                completed_at=datetime.now(UTC),
            )
            self.import_items.create(item)
            return item, "FAILED"

        try:
            if role == "PRIMARY":
                audit = WriteAudit(
                    entity_type="PRODUCT_IMAGE",
                    canonical_external_key=image_external_key,
                    planned_operation="UPDATE",
                    before_state={"image_1920": None},
                )
                write_client.write(
                    "product.template", [template_id], {"image_1920": encoded}, audit=audit
                )
                odoo_id = template_id
                model = "product.template"
            else:
                audit = WriteAudit(
                    entity_type="PRODUCT_IMAGE",
                    canonical_external_key=image_external_key,
                    planned_operation="CREATE",
                )
                odoo_id = write_client.create(
                    "product.image",
                    {
                        "product_tmpl_id": template_id,
                        "name": f"{product['slug']}-{display_order}",
                        "image_1920": encoded,
                    },
                    audit=audit,
                )
                model = "product.image"

            item = OdooCatalogueImportItem(
                import_run_id=write_client.context.run_id,
                entity_type="PRODUCT_IMAGE",
                canonical_external_key=image_external_key,
                canonical_name=product["name_en"],
                odoo_model=model,
                planned_action="CREATE",
                actual_action="CREATE",
                odoo_record_id=odoo_id,
                written_values_json={
                    "role": role,
                    "display_order": display_order,
                    "checksum": img.get("checksum"),
                    "source_path": img["original_path"],
                    "image_payload": "EXCLUDED_FROM_AUDIT_LOG",
                },
                result_status="SUCCEEDED",
                started_at=started_at,
                completed_at=datetime.now(UTC),
            )
            self.import_items.create(item)
            return item, "CREATE"
        except OdooIntegrationError as exc:
            item = OdooCatalogueImportItem(
                import_run_id=write_client.context.run_id,
                entity_type="PRODUCT_IMAGE",
                canonical_external_key=image_external_key,
                canonical_name=product["name_en"],
                odoo_model="product.template" if role == "PRIMARY" else "product.image",
                planned_action="CREATE",
                actual_action="CREATE",
                result_status="FAILED",
                error_code=type(exc).__name__,
                error_message=str(exc),
                started_at=started_at,
                completed_at=datetime.now(UTC),
            )
            self.import_items.create(item)
            return item, "FAILED"

    def _pin_xml_id(
        self, write_client: OdooWriteClient, model: str, xml_id_name: str, res_id: int
    ) -> None:
        from app.services.catalogue.odoo_import_planning import XML_ID_MODULE

        started_at = datetime.now(UTC)
        canonical_key = f"{model}:{xml_id_name}"
        audit = WriteAudit(
            entity_type="EXTERNAL_XML_ID",
            canonical_external_key=canonical_key,
            planned_operation="CREATE",
        )
        try:
            xml_id_record_id = write_client.create(
                "ir.model.data",
                {
                    "name": xml_id_name,
                    "module": XML_ID_MODULE,
                    "model": model,
                    "res_id": res_id,
                    "noupdate": True,
                },
                audit=audit,
            )
            item = OdooCatalogueImportItem(
                import_run_id=write_client.context.run_id,
                entity_type="EXTERNAL_XML_ID",
                canonical_external_key=canonical_key,
                canonical_name=f"{XML_ID_MODULE}.{xml_id_name}",
                odoo_model="ir.model.data",
                planned_action="CREATE",
                actual_action="CREATE",
                odoo_record_id=xml_id_record_id,
                external_xml_id=xml_id_name,
                written_values_json={"model": model, "res_id": res_id},
                result_status="SUCCEEDED",
                started_at=started_at,
                completed_at=datetime.now(UTC),
            )
        except OdooIntegrationError as exc:
            item = OdooCatalogueImportItem(
                import_run_id=write_client.context.run_id,
                entity_type="EXTERNAL_XML_ID",
                canonical_external_key=canonical_key,
                canonical_name=f"{XML_ID_MODULE}.{xml_id_name}",
                odoo_model="ir.model.data",
                planned_action="CREATE",
                actual_action="CREATE",
                result_status="FAILED",
                error_code=type(exc).__name__,
                error_message=str(exc),
                started_at=started_at,
                completed_at=datetime.now(UTC),
            )
        self.import_items.create(item)

    # -- --reconcile ------------------------------------------------------------------

    def run_reconcile(self, run_id: str | None) -> dict[str, Any]:
        """Read-only. Re-reads every SUCCEEDED item from the given (or most recent
        APPLY) run's Odoo records and diffs them against the canonical proposed
        values and the current PostgreSQL odoo_*_id mapping. Never calls create/write
        — uses the ordinary read-only OdooClient, not OdooWriteClient.
        """
        run = self.import_runs.get_by_id_str(run_id) if run_id else None
        if run is None:
            candidates = [r for r in self.import_runs.list_recent(limit=50) if r.mode == "APPLY"]
            run = candidates[0] if candidates else None

        if run is None:
            return {
                "generated_at": datetime.now(UTC).isoformat(),
                "run_id": None,
                "items_checked": 0,
                "field_mismatches": [],
                "postgresql_mapping_mismatches": [],
                "errors": ["No APPLY run found to reconcile."],
                "clean": False,
            }

        items = [
            i
            for i in self.import_items.list_for_run(run.id)
            if i.result_status == "SUCCEEDED" and i.odoo_record_id is not None
        ]

        client, connect_failure = _connect()
        mismatches: list[dict[str, Any]] = []
        errors: list[str] = []
        checked = 0

        if client is None:
            errors.append(f"Cannot reconcile: {connect_failure}")
        else:
            by_model: dict[str, list[OdooCatalogueImportItem]] = {}
            for item in items:
                by_model.setdefault(item.odoo_model, []).append(item)

            for model, model_items in by_model.items():
                ids = [i.odoo_record_id for i in model_items if i.odoo_record_id]
                if not ids:
                    continue
                try:
                    records = {r["id"]: r for r in client.read(model, ids)}
                except OdooIntegrationError as exc:
                    errors.append(f"Could not read {model} ids={ids}: {exc}")
                    continue
                for item in model_items:
                    checked += 1
                    record = records.get(item.odoo_record_id)
                    if record is None:
                        mismatches.append(
                            {
                                "canonical_external_key": item.canonical_external_key,
                                "odoo_model": model,
                                "odoo_record_id": item.odoo_record_id,
                                "issue": (
                                    "Record no longer exists in Odoo (deleted/archived out-of-band)"
                                ),
                            }
                        )
                        continue
                    proposed = item.proposed_values_json or item.written_values_json or {}
                    for field_name, expected in proposed.items():
                        actual = record.get(field_name)
                        # Any many2one field (categ_id, uom_id, ...) reads back as Odoo's
                        # [id, display_name] pair, never a bare id — unwrap it before
                        # comparing against the scalar id we originally wrote.
                        if (
                            isinstance(actual, list)
                            and len(actual) == 2
                            and isinstance(actual[0], int)
                            and isinstance(expected, int)
                        ):
                            actual = actual[0]
                        if field_name in record and actual != expected and expected is not None:
                            mismatches.append(
                                {
                                    "canonical_external_key": item.canonical_external_key,
                                    "odoo_model": model,
                                    "odoo_record_id": item.odoo_record_id,
                                    "field": field_name,
                                    "expected": expected,
                                    "actual": actual,
                                }
                            )

        postgres_mismatches: list[dict[str, Any]] = []
        for item in items:
            stored: int | None
            if item.entity_type == "CATEGORY":
                category_row = self.categories.get_by_external_key(item.canonical_external_key)
                stored = category_row.odoo_category_id if category_row else None
            elif item.entity_type == "PRODUCT_TEMPLATE":
                product_row = self.products.get_by_external_key(item.canonical_external_key)
                stored = product_row.odoo_product_template_id if product_row else None
            else:
                continue
            if stored != item.odoo_record_id:
                postgres_mismatches.append(
                    {
                        "canonical_external_key": item.canonical_external_key,
                        "entity_type": item.entity_type,
                        "postgresql_odoo_id": stored,
                        "import_item_odoo_id": item.odoo_record_id,
                    }
                )

        duplicate_attribute_warnings = (
            self._check_duplicate_attribute_names(client) if client is not None else []
        )

        return {
            "generated_at": datetime.now(UTC).isoformat(),
            "run_id": str(run.id),
            "run_mode": run.mode,
            "run_status": run.status,
            "duplicate_attribute_warnings": duplicate_attribute_warnings,
            "items_checked": checked,
            "field_mismatches": mismatches,
            "postgresql_mapping_mismatches": postgres_mismatches,
            "errors": errors,
            "clean": (
                not mismatches
                and not postgres_mismatches
                and not errors
                and not duplicate_attribute_warnings
            ),
        }

    def _check_duplicate_attribute_names(self, client: OdooClient) -> list[dict[str, Any]]:
        """Safety net for the highest-consequence new failure mode this feature
        introduces: attributes are N:1 shared master data (unlike categories/
        templates, which are 1:1 with a canonical key), so a matching bug or a race
        between concurrent applies could duplicate a shared attribute like "Flavor"
        across runs. Catches that after the fact even if the plan-time match-before-
        create gate is somehow bypassed.
        """
        _, products = _load_canonical_catalogue()
        repo = OdooAttributeRepository(client)
        warnings: list[dict[str, Any]] = []
        for name in known_attribute_names(products):
            matches = repo.find_attribute_by_name(name)
            if len(matches) > 1:
                warnings.append(
                    {
                        "attribute_name": name,
                        "duplicate_odoo_ids": [int(m["id"]) for m in matches],  # type: ignore[call-overload]
                        "issue": (
                            f"{len(matches)} product.attribute records named {name!r} exist in "
                            "Odoo — should be exactly one shared attribute."
                        ),
                    }
                )
        return warnings

    def _adopt_category_odoo_id(self, external_key: str, odoo_id: int | None) -> None:
        if odoo_id is None:
            return
        row = self.categories.get_by_external_key(external_key)
        if row is not None and row.odoo_category_id != odoo_id:
            self.categories.update(row, odoo_category_id=odoo_id, last_synced_at=datetime.now(UTC))

    def _adopt_product_odoo_id(self, external_key: str, odoo_id: int | None) -> None:
        if odoo_id is None:
            return
        row = self.products.get_by_external_key(external_key)
        if row is not None and row.odoo_product_template_id != odoo_id:
            self.products.update(
                row, odoo_product_template_id=odoo_id, last_synced_at=datetime.now(UTC)
            )

    def _adopt_attribute_odoo_id(self, attribute_name_en: str, odoo_id: int | None) -> None:
        """Fans out to every Postgres row sharing this attribute name — an Odoo
        attribute is N:1 with Postgres rows (many products/variants reference the
        same shared "Flavor"), unlike category/product ids which are 1:1.
        """
        if odoo_id is None:
            return
        for row in self.attribute_values.list_by_attribute_name(attribute_name_en):
            if row.odoo_attribute_id != odoo_id:
                self.attribute_values.update(row, odoo_attribute_id=odoo_id)

    def _adopt_attribute_value_odoo_id(self, plan_item: ImportPlanItem, odoo_id: int | None) -> None:
        if odoo_id is None:
            return
        attribute_name_en = plan_item.proposed_values.get("attribute_name_en")
        value_label_en = plan_item.proposed_values.get("value_label_en")
        if not attribute_name_en or not value_label_en:
            return
        for row in self.attribute_values.list_by_attribute_name_and_value(
            attribute_name_en, value_label_en
        ):
            if row.odoo_attribute_value_id != odoo_id:
                self.attribute_values.update(row, odoo_attribute_value_id=odoo_id)

    def _adopt_variant_odoo_id(self, external_key: str, odoo_id: int | None) -> None:
        if odoo_id is None:
            return
        row = self.variants.get_by_external_key(external_key)
        if row is not None and row.odoo_product_variant_id != odoo_id:
            self.variants.update(row, odoo_product_variant_id=odoo_id)


def _approval_checksum(approvals: list[ApprovalDecision]) -> str:
    from app.services.catalogue.approval_gate import compute_approval_checksum

    return compute_approval_checksum(approvals)


def _json_safe(value: Any) -> Any:
    return json.loads(json.dumps(value, default=str))


def encode_image_base64(original_path: str) -> str | None:
    """Reads and base64-encodes an image file for an Odoo image field. Returns None
    (never raises) if the file can't be found — the caller records that as a FAILED
    item rather than crashing the whole apply run. Never called during --dry-run: the
    dry-run report only ever carries role/path/checksum, never image bytes.
    """
    path = REPO_ROOT / original_path
    if not path.is_file():
        return None
    return base64.b64encode(path.read_bytes()).decode("ascii")
