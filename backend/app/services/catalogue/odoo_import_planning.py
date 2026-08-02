"""Pure planning logic for the Phase 5 Odoo catalogue importer.

This module never touches PostgreSQL and never writes to Odoo — it only reads (via
the existing read-only OdooClient/repositories) and computes what *would* happen.
app.services.catalogue.odoo_import_service uses build_import_plan() as the single
source of truth for --plan, --dry-run, and --apply alike, so all three modes can never
disagree about what's blocked, matched, or about to be created.

Matching priority (category and product alike, per CLAUDE.md Phase 5 §5/§6):
    1. External XML ID (ir.model.data, module="terrific_bites")
    2. PostgreSQL-stored Odoo id (catalogue_categories.odoo_category_id /
       catalogue_products.odoo_product_template_id) — checked by the caller, since
       only it has a PostgreSQL session; this module accepts it as an input.
    3. Exact unique name match (category) / exact SKU match then exact unique name
       match (product) — both require review (MATCH_REQUIRES_ADOPTION), never a
       silent create.
    4. Otherwise CREATE.
"""

from __future__ import annotations

import hashlib
import itertools
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.integrations.odoo.client import OdooClient
from app.integrations.odoo.exceptions import OdooIntegrationError
from app.integrations.odoo.repositories.attributes import OdooAttributeRepository
from app.integrations.odoo.repositories.categories import OdooCategoryRepository
from app.integrations.odoo.repositories.metadata import MetadataRepository
from app.integrations.odoo.repositories.products import OdooProductRepository
from app.services.catalogue.approval_gate import ApprovalDecision

BACKEND_DIR = Path(__file__).resolve().parents[3]
REPO_ROOT = BACKEND_DIR.parent
CATALOGUE_DATA_DIR = REPO_ROOT / "data" / "catalogue"

# Only categories.json/products.json feed Odoo writes — merchandising/moments/
# recipients/recommendations never do (CLAUDE.md Phase 5 §4 "Do not import" list),
# so the import source checksum is scoped to just these two files, deliberately
# narrower than the seed service's whole-catalogue checksum.
_IMPORT_SOURCE_FILES = (
    CATALOGUE_DATA_DIR / "categories.json",
    CATALOGUE_DATA_DIR / "products.json",
)

XML_ID_MODULE = "terrific_bites"

CATEGORY_BLOCKING_DECISION_IDS = {"D03"}
PRODUCT_BLOCKING_DECISION_IDS = {"D04", "D08", "D09", "D10", "D19"}
# Deliberately separate from PRODUCT_BLOCKING_DECISION_IDS and NOT set blocks_import=true
# in the approvals file (see D09's precedent: a decision can gate specific plan items
# without gating the whole --apply run) — this scopes the higher-risk, newer
# attribute/variant write path to its own approval, independent of category/template
# creation, which can keep shipping on its own timeline without also having to bless the
# newer write surface.
VARIANT_BLOCKING_DECISION_IDS = {"D20"}

# Variant-attribute modelling: attributes ("Box Size", "Flavor") are shared master data
# across products, so they get their own matching pass (plan_attributes), separate from
# and run before plan_variants — a variant's CREATE always references an attribute/value
# that plan_attributes already resolved (MATCH or CREATE), never a dangling id. See
# docs/integrations/odoo-catalogue-variant-model.md for the full Odoo attribute/variant
# model this implements against (product.attribute -> product.attribute.value ->
# product.template.attribute.line -> auto-generated product.product).


def compute_import_source_checksum() -> str:
    digest = hashlib.sha256()
    for path in _IMPORT_SOURCE_FILES:
        digest.update(path.name.encode("utf-8"))
        digest.update(path.read_bytes())
    return f"sha256:{digest.hexdigest()}"


@dataclass(frozen=True)
class EnvironmentSnapshot:
    odoo_version: str
    company_id: int
    company_name: str
    currency: str
    base_url: str
    database: str
    captured_at: str

    @property
    def fingerprint(self) -> str:
        """A stable identity for "the Odoo environment this plan was verified
        against" — apply refuses to proceed if the live environment's fingerprint at
        apply time doesn't match the one the plan/approval were generated against
        (CLAUDE.md Phase 5 §11 "Require the environment fingerprint to match").
        """
        digest = hashlib.sha256(
            f"{self.odoo_version}|{self.company_id}|{self.company_name}|"
            f"{self.currency}|{self.base_url}|{self.database}".encode()
        )
        return f"sha256:{digest.hexdigest()[:32]}"


def capture_environment_snapshot(client: OdooClient) -> EnvironmentSnapshot:
    version = client.get_server_version()
    companies = MetadataRepository(client).get_companies()
    if not companies:
        raise OdooIntegrationError("No res.company records visible to the authenticated user")
    company = companies[0]
    return EnvironmentSnapshot(
        odoo_version=version.server_version,
        company_id=company.id,
        company_name=company.name,
        currency=company.currency_name or "",
        base_url=client.config.base_url,
        database=client.config.database,
        captured_at=datetime.now(UTC).isoformat(),
    )


@dataclass
class ImportPlanItem:
    entity_type: str  # CATEGORY | PRODUCT_TEMPLATE | PRODUCT_VARIANT | PRODUCT_ATTRIBUTE
    # | PRODUCT_ATTRIBUTE_VALUE
    canonical_external_key: str
    canonical_sku: str | None
    canonical_name: str
    odoo_model: str
    xml_id_name: str
    match_strategy: str | None
    existing_odoo_id: int | None
    planned_action: str  # CREATE | UPDATE | MATCH | SKIP | BLOCKED
    blocking_issues: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    proposed_values: dict[str, Any] = field(default_factory=dict)
    category_external_key: str | None = None  # products only — resolved to categ_id at apply time


@dataclass
class ImportPlan:
    generated_at: str
    environment: EnvironmentSnapshot | None
    source_checksum: str
    approval_checksum: str
    category_items: list[ImportPlanItem]
    product_items: list[ImportPlanItem]
    connection_error: str | None = None

    @property
    def all_items(self) -> list[ImportPlanItem]:
        return self.category_items + self.product_items

    @property
    def action_counts(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for item in self.all_items:
            counts[item.planned_action] = counts.get(item.planned_action, 0) + 1
        return counts

    @property
    def blocked_items(self) -> list[ImportPlanItem]:
        return [i for i in self.all_items if i.planned_action == "BLOCKED"]

    def compute_plan_checksum(self) -> str:
        payload = "|".join(
            f"{i.entity_type}:{i.canonical_external_key}:{i.planned_action}"
            for i in sorted(self.all_items, key=lambda i: (i.entity_type, i.canonical_external_key))
        )
        return f"sha256:{hashlib.sha256(payload.encode()).hexdigest()[:32]}"


def _open_blocking_decisions(
    approvals: list[ApprovalDecision], ids: set[str]
) -> list[ApprovalDecision]:
    """Deliberately does NOT use ApprovalDecision.is_resolved_approval here — that
    property answers "does this decision block the overall approval-file gate"
    (blocks_import=False short-circuits it to resolved), a different question from
    "is this specific category/product's CREATE allowed to proceed". CATEGORY_
    BLOCKING_DECISION_IDS/PRODUCT_BLOCKING_DECISION_IDS are a fixed, code-level list
    of decisions every planned CREATE always requires — independent of whichever
    blocks_import value happens to be set on the approval row — so a decision only
    stops blocking item-level planning once it is genuinely APPROVED with a value.
    """
    return [
        d
        for d in approvals
        if d.decision_id in ids and not (d.status == "APPROVED" and d.approved_value is not None)
    ]


def _find_external_key_match(
    client: OdooClient, model: str, xml_id_name: str, correlation_id: str
) -> dict[str, Any] | None:
    try:
        page = client.search_read(
            "ir.model.data",
            [["module", "=", XML_ID_MODULE], ["name", "=", xml_id_name], ["model", "=", model]],
            ["id", "res_id", "module", "name", "model"],
            limit=1,
            correlation_id=correlation_id,
        )
    except OdooIntegrationError:
        return None
    return page.records[0] if page.records else None


def _approved_value(approvals: list[ApprovalDecision], decision_id: str) -> Any:
    for d in approvals:
        if d.decision_id == decision_id:
            return d.approved_value if d.status == "APPROVED" else None
    return None


def plan_categories(
    categories: list[dict[str, Any]],
    approvals: list[ApprovalDecision],
    client: OdooClient | None,
    connect_failure: str | None,
    postgres_odoo_ids: dict[str, int],
    correlation_id: str,
) -> list[ImportPlanItem]:
    repo = OdooCategoryRepository(client) if client else None
    open_decisions = _open_blocking_decisions(approvals, CATEGORY_BLOCKING_DECISION_IDS)
    items: list[ImportPlanItem] = []

    for cat in categories:
        xml_id_name = f"category_{cat['slug']}"
        # product.category has no `active` field on every Odoo instance (verified absent
        # on terrific_dev/Odoo 19 via fields_get — only `name`/`parent_id` exist here);
        # unlike product.template, category active/inactive is not a real write target.
        proposed_values = {"name": cat["name_en"]}

        base_kwargs = dict(
            entity_type="CATEGORY",
            canonical_external_key=cat["external_key"],
            canonical_sku=None,
            canonical_name=cat["name_en"],
            odoo_model="product.category",
            xml_id_name=xml_id_name,
            proposed_values=proposed_values,
        )

        if client is None or repo is None:
            items.append(
                ImportPlanItem(
                    **base_kwargs,
                    match_strategy=None,
                    existing_odoo_id=None,
                    planned_action="BLOCKED",
                    blocking_issues=[f"Cannot verify against Odoo: {connect_failure}"],
                )
            )
            continue

        stored_id = postgres_odoo_ids.get(cat["external_key"])
        if stored_id:
            items.append(
                ImportPlanItem(
                    **base_kwargs,
                    match_strategy="POSTGRES_STORED_ID",
                    existing_odoo_id=stored_id,
                    planned_action="MATCH",
                )
            )
            continue

        external_match = _find_external_key_match(
            client, "product.category", xml_id_name, correlation_id
        )
        if external_match:
            items.append(
                ImportPlanItem(
                    **base_kwargs,
                    match_strategy="EXTERNAL_KEY",
                    existing_odoo_id=external_match["res_id"],
                    planned_action="MATCH",
                )
            )
            continue

        name_matches = repo.find_by_name(cat["name_en"], correlation_id=correlation_id)
        if name_matches:
            items.append(
                ImportPlanItem(
                    **base_kwargs,
                    match_strategy="NAME",
                    existing_odoo_id=int(name_matches[0]["id"]),  # type: ignore[call-overload]
                    planned_action="BLOCKED",
                    warnings=[
                        f"product.category id={name_matches[0]['id']} already has this exact name "
                        "but no terrific_bites XML ID — requires explicit plan approval before "
                        "adoption (MATCH_REQUIRES_ADOPTION), not an automatic create."
                    ],
                    blocking_issues=["MATCH_REQUIRES_ADOPTION — see warnings"],
                )
            )
            continue

        if open_decisions:
            items.append(
                ImportPlanItem(
                    **base_kwargs,
                    match_strategy=None,
                    existing_odoo_id=None,
                    planned_action="BLOCKED",
                    blocking_issues=[
                        f"{d.decision_id} ({d.title}) is {d.status}, not APPROVED"
                        for d in open_decisions
                    ],
                )
            )
            continue

        items.append(
            ImportPlanItem(
                **base_kwargs, match_strategy=None, existing_odoo_id=None, planned_action="CREATE"
            )
        )

    return items


def plan_products(
    products: list[dict[str, Any]],
    approvals: list[ApprovalDecision],
    client: OdooClient | None,
    connect_failure: str | None,
    postgres_odoo_ids: dict[str, int],
    correlation_id: str,
) -> list[ImportPlanItem]:
    repo = OdooProductRepository(client) if client else None
    open_decisions = _open_blocking_decisions(approvals, PRODUCT_BLOCKING_DECISION_IDS)

    uom_approval = _approved_value(approvals, "D09")
    type_approval = _approved_value(approvals, "D10")

    items: list[ImportPlanItem] = []

    for product in products:
        xml_id_name = f"product_{product['slug']}"
        proposed_values: dict[str, Any] = {
            "name": product["name_en"],
            "default_code": product["sku"],
            "list_price": product["sales_price"],
            "sale_ok": product.get("sellable", True),
            "active": product.get("active", True),
            "description_sale": product.get("description_en"),
        }
        if uom_approval:
            proposed_values["uom_id"] = uom_approval.get("odoo_uom_id")
        if type_approval:
            proposed_values["type"] = type_approval.get("odoo_product_type")

        base_kwargs = dict(
            entity_type="PRODUCT_TEMPLATE",
            canonical_external_key=product["external_key"],
            canonical_sku=product["sku"],
            canonical_name=product["name_en"],
            odoo_model="product.template",
            xml_id_name=xml_id_name,
            proposed_values=proposed_values,
            category_external_key=product["category_external_key"],
        )

        if client is None or repo is None:
            items.append(
                ImportPlanItem(
                    **base_kwargs,
                    match_strategy=None,
                    existing_odoo_id=None,
                    planned_action="BLOCKED",
                    blocking_issues=[f"Cannot verify against Odoo: {connect_failure}"],
                )
            )
            continue

        stored_id = postgres_odoo_ids.get(product["external_key"])
        if stored_id:
            items.append(
                ImportPlanItem(
                    **base_kwargs,
                    match_strategy="POSTGRES_STORED_ID",
                    existing_odoo_id=stored_id,
                    planned_action="MATCH",
                )
            )
            continue

        external_match = _find_external_key_match(
            client, "product.template", xml_id_name, correlation_id
        )
        if external_match:
            items.append(
                ImportPlanItem(
                    **base_kwargs,
                    match_strategy="EXTERNAL_KEY",
                    existing_odoo_id=external_match["res_id"],
                    planned_action="MATCH",
                )
            )
            continue

        sku_matches = repo.find_templates_by_default_code(
            product["sku"], correlation_id=correlation_id
        )
        if sku_matches:
            items.append(
                ImportPlanItem(
                    **base_kwargs,
                    match_strategy="SKU",
                    existing_odoo_id=sku_matches[0]["id"],
                    planned_action="BLOCKED",
                    warnings=[
                        f"product.template id={sku_matches[0]['id']} already has default_code="
                        f"{product['sku']!r} but no terrific_bites XML ID — requires explicit plan "
                        "approval before adoption, not an automatic create."
                    ],
                    blocking_issues=["MATCH_REQUIRES_ADOPTION — see warnings"],
                )
            )
            continue

        name_matches = repo.find_templates_by_name(
            product["name_en"], correlation_id=correlation_id
        )
        if name_matches:
            items.append(
                ImportPlanItem(
                    **base_kwargs,
                    match_strategy="NAME",
                    existing_odoo_id=int(name_matches[0]["id"]),
                    planned_action="BLOCKED",
                    warnings=[
                        f"product.template id={name_matches[0]['id']} matches this name with a "
                        "different/absent SKU — requires manual review, never matched by name "
                        "alone."
                    ],
                    blocking_issues=["MATCH_REQUIRES_ADOPTION — see warnings"],
                )
            )
            continue

        if open_decisions:
            items.append(
                ImportPlanItem(
                    **base_kwargs,
                    match_strategy=None,
                    existing_odoo_id=None,
                    planned_action="BLOCKED",
                    blocking_issues=[
                        f"{d.decision_id} ({d.title}) is {d.status}, not APPROVED"
                        for d in open_decisions
                    ],
                )
            )
            continue

        items.append(
            ImportPlanItem(
                **base_kwargs, match_strategy=None, existing_odoo_id=None, planned_action="CREATE"
            )
        )

    return items


def _label_to_slug(label: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", label.lower()).strip("-")


def known_attribute_names(products: list[dict[str, Any]]) -> list[str]:
    """Public wrapper over _collect_distinct_attributes for callers that only need the
    distinct attribute names (e.g. run_reconcile's duplicate-attribute-name check) —
    not the full name->values mapping plan_attributes() itself needs.
    """
    return [name for name, _ in _collect_distinct_attributes(products)]


def _collect_distinct_attributes(products: list[dict[str, Any]]) -> list[tuple[str, list[str]]]:
    """Returns [(attribute_name_en, [value_label_en, ...]), ...] in first-seen order,
    deduped by name across every variant_parent product — attributes are shared master
    data (e.g. "Flavor" reused by many products), planned once here, never once per
    product (unlike categories/templates, which are 1:1 with a canonical external key).
    """
    seen: dict[str, list[str]] = {}
    order: list[str] = []
    for product in products:
        if product.get("product_type") != "variant_parent":
            continue
        for axis in (product.get("variants") or {}).get("attributes", []):
            name = axis["name_en"]
            if name not in seen:
                seen[name] = []
                order.append(name)
            for value in axis.get("values", []):
                label = value["label"]
                if label not in seen[name]:
                    seen[name].append(label)
    return [(name, seen[name]) for name in order]


def plan_attributes(
    products: list[dict[str, Any]],
    approvals: list[ApprovalDecision],
    client: OdooClient | None,
    connect_failure: str | None,
    postgres_attribute_ids: dict[str, int],
    postgres_value_ids: dict[tuple[str, str], int],
    correlation_id: str,
) -> list[ImportPlanItem]:
    """Shared master-data matching pass — run once per import, before plan_variants(),
    never once per product. Matching ladder per attribute: POSTGRES_STORED_ID -> live
    exact-name match (also verifying create_variant == "always", the only mode
    consistent with this app's per-combination SKU/price/availability model) ->
    (VARIANT_BLOCKING_DECISION_IDS resolved?) -> CREATE. Each value gets the identical
    ladder, scoped to its own attribute.
    """
    repo = OdooAttributeRepository(client) if client else None
    open_decisions = _open_blocking_decisions(approvals, VARIANT_BLOCKING_DECISION_IDS)
    items: list[ImportPlanItem] = []

    for name, value_labels in _collect_distinct_attributes(products):
        stored_attr_id = postgres_attribute_ids.get(name)
        attr_warnings: list[str] = []
        attr_blocking: list[str] = []

        if stored_attr_id:
            attr_action, attr_match_strategy, attr_odoo_id = "MATCH", "POSTGRES_STORED_ID", stored_attr_id
        elif client is None or repo is None:
            attr_action, attr_match_strategy, attr_odoo_id = "BLOCKED", None, None
            attr_blocking = [f"Cannot verify against Odoo: {connect_failure}"]
        else:
            name_matches = repo.find_attribute_by_name(name, correlation_id=correlation_id)
            if not name_matches and open_decisions:
                attr_action, attr_match_strategy, attr_odoo_id = "BLOCKED", None, None
                attr_blocking = [
                    f"{d.decision_id} ({d.title}) is {d.status}, not APPROVED" for d in open_decisions
                ]
            elif not name_matches:
                attr_action, attr_match_strategy, attr_odoo_id = "CREATE", None, None
            elif name_matches[0].get("create_variant") != "always":
                found = name_matches[0]
                attr_action, attr_match_strategy, attr_odoo_id = "BLOCKED", "NAME", int(found["id"])  # type: ignore[call-overload]
                attr_blocking = ["EXISTING_ATTRIBUTE_WRONG_CREATE_VARIANT_MODE"]
                attr_warnings = [
                    f"product.attribute id={found['id']} named {name!r} already exists with "
                    f"create_variant={found.get('create_variant')!r}, not 'always' — this app's "
                    "model requires every combination to materialize immediately as its own "
                    "product.product; using it as-is would silently break variant generation."
                ]
            else:
                found = name_matches[0]
                attr_action, attr_match_strategy, attr_odoo_id = "MATCH", "NAME", int(found["id"])  # type: ignore[call-overload]

        items.append(
            ImportPlanItem(
                entity_type="PRODUCT_ATTRIBUTE",
                canonical_external_key=f"attribute:{name}",
                canonical_sku=None,
                canonical_name=name,
                odoo_model="product.attribute",
                xml_id_name="",
                match_strategy=attr_match_strategy,
                existing_odoo_id=attr_odoo_id,
                planned_action=attr_action,
                blocking_issues=attr_blocking,
                warnings=attr_warnings,
                proposed_values=(
                    {"name": name, "create_variant": "always"} if attr_action == "CREATE" else {}
                ),
            )
        )

        for value_label in value_labels:
            items.append(
                _plan_attribute_value(
                    name,
                    value_label,
                    attr_action=attr_action,
                    attr_odoo_id=attr_odoo_id,
                    client=client,
                    repo=repo,
                    connect_failure=connect_failure,
                    stored_value_id=postgres_value_ids.get((name, value_label)),
                    open_decisions=open_decisions,
                    correlation_id=correlation_id,
                )
            )

    return items


def _plan_attribute_value(
    attribute_name: str,
    value_label: str,
    *,
    attr_action: str,
    attr_odoo_id: int | None,
    client: OdooClient | None,
    repo: OdooAttributeRepository | None,
    connect_failure: str | None,
    stored_value_id: int | None,
    open_decisions: list[ApprovalDecision],
    correlation_id: str,
) -> ImportPlanItem:
    # attribute_name_en/value_label_en are always carried in proposed_values (not just
    # for CREATE) so callers can identify which axis/value an item is about without
    # parsing canonical_external_key/canonical_name strings — the source of the
    # `unresolved_attribute_values` set plan_variants() needs.
    identity_values = {"attribute_name_en": attribute_name, "value_label_en": value_label}
    base_kwargs = dict(
        entity_type="PRODUCT_ATTRIBUTE_VALUE",
        canonical_external_key=f"attribute_value:{attribute_name}:{value_label}",
        canonical_sku=None,
        canonical_name=f"{attribute_name}: {value_label}",
        odoo_model="product.attribute.value",
        xml_id_name="",
    )

    if attr_action == "BLOCKED":
        return ImportPlanItem(
            **base_kwargs,
            match_strategy=None,
            existing_odoo_id=None,
            planned_action="BLOCKED",
            blocking_issues=["ATTRIBUTE_NOT_RESOLVED"],
            proposed_values=identity_values,
        )
    if stored_value_id:
        return ImportPlanItem(
            **base_kwargs,
            match_strategy="POSTGRES_STORED_ID",
            existing_odoo_id=stored_value_id,
            planned_action="MATCH",
            proposed_values=identity_values,
        )
    if client is None or repo is None:
        return ImportPlanItem(
            **base_kwargs,
            match_strategy=None,
            existing_odoo_id=None,
            planned_action="BLOCKED",
            blocking_issues=[f"Cannot verify against Odoo: {connect_failure}"],
            proposed_values=identity_values,
        )
    if attr_odoo_id is not None:
        value_matches = repo.find_value_by_name_and_attribute(
            value_label, attr_odoo_id, correlation_id=correlation_id
        )
        if value_matches:
            return ImportPlanItem(
                **base_kwargs,
                match_strategy="NAME",
                existing_odoo_id=int(value_matches[0]["id"]),  # type: ignore[call-overload]
                planned_action="MATCH",
                proposed_values=identity_values,
            )
    if open_decisions:
        return ImportPlanItem(
            **base_kwargs,
            match_strategy=None,
            existing_odoo_id=None,
            planned_action="BLOCKED",
            blocking_issues=[
                f"{d.decision_id} ({d.title}) is {d.status}, not APPROVED" for d in open_decisions
            ],
            proposed_values=identity_values,
        )
    # attr_action == "CREATE" (no attr_odoo_id to scope a search against yet) or no
    # existing value found under a matched attribute — either way, create fresh.
    return ImportPlanItem(
        **base_kwargs,
        match_strategy=None,
        existing_odoo_id=None,
        planned_action="CREATE",
        proposed_values={**identity_values, "name": value_label},
    )


def unresolved_attribute_values(attribute_items: list[ImportPlanItem]) -> set[tuple[str, str]]:
    """The (attribute_name_en, value_label_en) pairs plan_attributes() could not
    resolve (BLOCKED) — plan_variants()'s required input, so a variant is never given
    a dangling attribute/value id to write against.
    """
    return {
        (item.proposed_values["attribute_name_en"], item.proposed_values["value_label_en"])
        for item in attribute_items
        if item.entity_type == "PRODUCT_ATTRIBUTE_VALUE" and item.planned_action == "BLOCKED"
    }


def _iter_variant_combinations(
    product: dict[str, Any],
) -> list[tuple[str, str, list[tuple[str, str]]]]:
    """Mirrors seed_service.py::_seed_combinatorial_variants' external_key/SKU scheme
    exactly (external_key = f"{product_ext_key}.variant.{slug}.{slug}...", sku =
    f"{sku}-{SLUG}-{SLUG}...") — this module is deliberately PostgreSQL/ORM-free (pure
    planning over the same raw JSON seed_service.py consumes), so it recomputes the
    same combination identity independently rather than importing the seed service.
    Keep both in sync if either's scheme changes. Returns (external_key, sku,
    [(attribute_name_en, value_label_en), ...]) per combination.
    """
    attributes = (product.get("variants") or {}).get("attributes", [])
    if not attributes:
        return []
    value_lists = [axis.get("values", []) for axis in attributes]
    results: list[tuple[str, str, list[tuple[str, str]]]] = []
    for combo in itertools.product(*value_lists):
        slugs = [_label_to_slug(v["label"]) for v in combo]
        external_key = f"{product['external_key']}.variant." + ".".join(slugs)
        sku = f"{product['sku']}-" + "-".join(s.upper().replace("-", "") for s in slugs)
        pairs = [(axis["name_en"], v["label"]) for axis, v in zip(attributes, combo, strict=True)]
        results.append((external_key, sku, pairs))
    return results


def plan_variants(
    products: list[dict[str, Any]],
    approvals: list[ApprovalDecision],
    client: OdooClient | None,
    connect_failure: str | None,
    postgres_variant_odoo_ids: dict[str, int],
    unresolved_attribute_values: set[tuple[str, str]],
    correlation_id: str,
) -> list[ImportPlanItem]:
    """Replaces the old plan_variant_skips(): every combination in the Cartesian
    product of a variant_parent product's attribute axes gets its own real plan item
    (MATCH/CREATE/BLOCKED) — never SKIP. `unresolved_attribute_values` is the set of
    (attribute_name_en, value_label_en) pairs whose plan_attributes() item came back
    BLOCKED; any variant referencing one of those is BLOCKED too
    (ATTRIBUTE_NOT_RESOLVED), never given a dangling attribute/value id to write
    against. See docs/integrations/odoo-catalogue-variant-model.md.
    """
    repo = OdooProductRepository(client) if client else None
    open_decisions = _open_blocking_decisions(approvals, VARIANT_BLOCKING_DECISION_IDS)
    items: list[ImportPlanItem] = []

    for product in products:
        if product.get("product_type") != "variant_parent":
            continue
        for external_key, sku, pairs in _iter_variant_combinations(product):
            canonical_name = f"{product['name_en']} — " + " / ".join(label for _, label in pairs)
            base_kwargs = dict(
                entity_type="PRODUCT_VARIANT",
                canonical_external_key=external_key,
                canonical_sku=sku,
                canonical_name=canonical_name,
                odoo_model="product.product",
                xml_id_name="",
                proposed_values={
                    "template_external_key": product["external_key"],
                    "attribute_lines": [
                        {"attribute_name_en": n, "value_label_en": label} for n, label in pairs
                    ],
                    "default_code": sku,
                },
            )

            unresolved = [p for p in pairs if p in unresolved_attribute_values]
            if unresolved:
                items.append(
                    ImportPlanItem(
                        **base_kwargs,
                        match_strategy=None,
                        existing_odoo_id=None,
                        planned_action="BLOCKED",
                        blocking_issues=["ATTRIBUTE_NOT_RESOLVED"],
                        warnings=[f"Attribute/value not resolved: {n!r}={v!r}" for n, v in unresolved],
                    )
                )
                continue

            stored_id = postgres_variant_odoo_ids.get(external_key)
            if stored_id:
                items.append(
                    ImportPlanItem(
                        **base_kwargs,
                        match_strategy="POSTGRES_STORED_ID",
                        existing_odoo_id=stored_id,
                        planned_action="MATCH",
                    )
                )
                continue

            if client is None or repo is None:
                items.append(
                    ImportPlanItem(
                        **base_kwargs,
                        match_strategy=None,
                        existing_odoo_id=None,
                        planned_action="BLOCKED",
                        blocking_issues=[f"Cannot verify against Odoo: {connect_failure}"],
                    )
                )
                continue

            sku_matches = repo.find_variants_by_default_code(sku, correlation_id=correlation_id)
            if sku_matches:
                items.append(
                    ImportPlanItem(
                        **base_kwargs,
                        match_strategy="SKU",
                        existing_odoo_id=int(sku_matches[0]["id"]),
                        planned_action="BLOCKED",
                        warnings=[
                            f"product.product id={sku_matches[0]['id']} already has "
                            f"default_code={sku!r} but was never adopted via a prior import "
                            "run — requires explicit review, not an automatic MATCH."
                        ],
                        blocking_issues=["MATCH_REQUIRES_ADOPTION — see warnings"],
                    )
                )
                continue

            if open_decisions:
                items.append(
                    ImportPlanItem(
                        **base_kwargs,
                        match_strategy=None,
                        existing_odoo_id=None,
                        planned_action="BLOCKED",
                        blocking_issues=[
                            f"{d.decision_id} ({d.title}) is {d.status}, not APPROVED"
                            for d in open_decisions
                        ],
                    )
                )
                continue

            items.append(
                ImportPlanItem(
                    **base_kwargs, match_strategy=None, existing_odoo_id=None, planned_action="CREATE"
                )
            )

    return items
