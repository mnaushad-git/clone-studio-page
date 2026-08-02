"""Read-only validator for the canonical catalogue seed data under data/catalogue/.

Phase 2A tooling only. Never writes to any of the six input JSON files; the
only file it writes is data/catalogue/catalogue-validation-report.json.

Usage (from the backend/ virtualenv):
    python scripts/validate_catalogue.py
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent.parent
DATA_DIR = REPO_ROOT / "data" / "catalogue"

CATEGORIES_PATH = DATA_DIR / "categories.json"
PRODUCTS_PATH = DATA_DIR / "products.json"
MERCHANDISING_PATH = DATA_DIR / "product-merchandising.json"
MOMENTS_PATH = DATA_DIR / "moments.json"
RECIPIENTS_PATH = DATA_DIR / "recipients.json"
RECOMMENDATIONS_PATH = DATA_DIR / "product-recommendations.json"
REPORT_PATH = DATA_DIR / "catalogue-validation-report.json"

ERROR = "error"
WARNING = "warning"

# Categories a WARNING can be further classified into, so callers can tell a
# translation gap apart from a genuine pre-import sign-off requirement. ERROR
# issues are always "blocking"; there is no ambiguity to disambiguate there.
BLOCKING = "blocking"
BUSINESS_CONFIRMATION = "business_confirmation"
ODOO_VERIFICATION = "odoo_verification"
CONTENT_COMPLETION = "content_completion"
MERCHANDISING = "merchandising"


@dataclass
class Issue:
    severity: str
    code: str
    message: str
    entity: str | None = None
    category: str = BLOCKING


@dataclass
class CatalogueData:
    categories: list[dict[str, Any]] = field(default_factory=list)
    products: list[dict[str, Any]] = field(default_factory=list)
    merchandising: list[dict[str, Any]] = field(default_factory=list)
    moments: list[dict[str, Any]] = field(default_factory=list)
    recipients: list[dict[str, Any]] = field(default_factory=list)
    recommendations: list[dict[str, Any]] = field(default_factory=list)


def load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def load_catalogue() -> CatalogueData:
    return CatalogueData(
        categories=load_json(CATEGORIES_PATH).get("categories", []),
        products=load_json(PRODUCTS_PATH).get("products", []),
        merchandising=load_json(MERCHANDISING_PATH).get("product_merchandising", []),
        moments=load_json(MOMENTS_PATH).get("moments", []),
        recipients=load_json(RECIPIENTS_PATH).get("recipients", []),
        recommendations=load_json(RECOMMENDATIONS_PATH).get("product_recommendations", []),
    )


def _duplicates(values: list[str]) -> set[str]:
    seen: set[str] = set()
    dupes: set[str] = set()
    for v in values:
        if v in seen:
            dupes.add(v)
        seen.add(v)
    return dupes


def check_duplicate_external_keys(data: CatalogueData, issues: list[Issue]) -> None:
    groups = {
        "category": [c["external_key"] for c in data.categories],
        "product": [p["external_key"] for p in data.products],
        "moment": [m["external_key"] for m in data.moments],
        "recipient": [r["external_key"] for r in data.recipients],
    }
    for kind, keys in groups.items():
        for dup in sorted(_duplicates(keys)):
            issues.append(
                Issue(ERROR, "duplicate_external_key", f"Duplicate {kind} external_key: {dup}", dup)
            )

    all_keys = [k for keys in groups.values() for k in keys]
    all_dupes = _duplicates(all_keys)
    cross_type_dupes = all_dupes - {d for keys in groups.values() for d in _duplicates(keys)}
    for dup in sorted(cross_type_dupes):
        issues.append(
            Issue(
                ERROR,
                "duplicate_external_key_cross_type",
                f"external_key reused across entity types: {dup}",
                dup,
            )
        )


def check_duplicate_skus(data: CatalogueData, issues: list[Issue]) -> None:
    skus = [p["sku"] for p in data.products if p.get("sku")]
    for dup in sorted(_duplicates(skus)):
        issues.append(Issue(ERROR, "duplicate_sku", f"Duplicate SKU: {dup}", dup))


def check_duplicate_slugs(data: CatalogueData, issues: list[Issue]) -> None:
    groups = {
        "category": [c["slug"] for c in data.categories],
        "product": [p["slug"] for p in data.products],
        "moment": [m["slug"] for m in data.moments],
        "recipient": [r["slug"] for r in data.recipients],
    }
    for kind, slugs in groups.items():
        for dup in sorted(_duplicates(slugs)):
            issues.append(Issue(ERROR, "duplicate_slug", f"Duplicate {kind} slug: {dup}", dup))


def check_missing_category_references(data: CatalogueData, issues: list[Issue]) -> None:
    category_keys = {c["external_key"] for c in data.categories}
    for p in data.products:
        cat_ref = p.get("category_external_key")
        if not cat_ref:
            issues.append(
                Issue(
                    ERROR,
                    "product_missing_category",
                    f"Product has no category_external_key: {p.get('external_key')}",
                    p.get("external_key"),
                )
            )
        elif cat_ref not in category_keys:
            issues.append(
                Issue(
                    ERROR,
                    "product_invalid_category_reference",
                    f"Product {p.get('external_key')} references unknown category {cat_ref}",
                    p.get("external_key"),
                )
            )


def check_merchandising_references(data: CatalogueData, issues: list[Issue]) -> None:
    product_keys = {p["external_key"] for p in data.products}
    seen: set[str] = set()
    for m in data.merchandising:
        ref = m.get("product_external_key")
        if ref in seen:
            issues.append(
                Issue(
                    ERROR,
                    "duplicate_merchandising_record",
                    f"More than one merchandising record for product {ref}",
                    ref,
                )
            )
        if ref:
            seen.add(ref)
        if not ref or ref not in product_keys:
            issues.append(
                Issue(
                    ERROR,
                    "invalid_merchandising_product_reference",
                    f"Merchandising record references unknown product: {ref}",
                    ref,
                )
            )


def check_moment_and_recipient_references(data: CatalogueData, issues: list[Issue]) -> None:
    moment_keys = {m["external_key"] for m in data.moments}
    recipient_keys = {r["external_key"] for r in data.recipients}
    for m in data.merchandising:
        ref = m.get("product_external_key")
        for moment_ref in m.get("moments", []) or []:
            if moment_ref not in moment_keys:
                issues.append(
                    Issue(
                        ERROR,
                        "invalid_moment_reference",
                        f"Product {ref} references unknown moment {moment_ref}",
                        ref,
                    )
                )
        for recipient_ref in m.get("recipients", []) or []:
            if recipient_ref not in recipient_keys:
                issues.append(
                    Issue(
                        ERROR,
                        "invalid_recipient_reference",
                        f"Product {ref} references unknown recipient {recipient_ref}",
                        ref,
                    )
                )


def check_recommendation_references(data: CatalogueData, issues: list[Issue]) -> None:
    product_keys = {p["external_key"] for p in data.products}
    for rec in data.recommendations:
        source = rec.get("product_external_key")
        target = rec.get("recommended_product_external_key")
        if source not in product_keys:
            issues.append(
                Issue(
                    ERROR,
                    "invalid_recommendation_reference",
                    f"Recommendation source product unknown: {source}",
                    source,
                )
            )
        if target not in product_keys:
            issues.append(
                Issue(
                    ERROR,
                    "invalid_recommendation_reference",
                    f"Recommendation target product unknown: {target}",
                    target,
                )
            )
        if source and target and source == target:
            issues.append(
                Issue(
                    ERROR,
                    "self_referencing_recommendation",
                    f"Product recommends itself: {source}",
                    source,
                )
            )


def check_images(data: CatalogueData, issues: list[Issue]) -> None:
    for p in data.products:
        images = []
        if p.get("primary_image"):
            images.append(("primary_image", p["primary_image"]))
        for idx, img in enumerate(p.get("additional_images") or []):
            images.append((f"additional_images[{idx}]", img))

        for label, img in images:
            rel_path = img.get("original_path")
            if not rel_path:
                continue
            key = p.get("external_key")
            actual_path = REPO_ROOT / rel_path
            exists_on_disk = actual_path.is_file()
            if not exists_on_disk:
                issues.append(
                    Issue(
                        ERROR,
                        "missing_image_file",
                        f"Product {key} {label} references a missing file: {rel_path}",
                        key,
                    )
                )
            elif img.get("exists") is False:
                issues.append(
                    Issue(
                        WARNING,
                        "image_metadata_disagreement",
                        f"Product {key} {label} marked exists=false but file exists: {rel_path}",
                        key,
                    )
                )


def check_prices(data: CatalogueData, issues: list[Issue]) -> None:
    for p in data.products:
        price = p.get("sales_price")
        if price is None:
            issues.append(
                Issue(
                    ERROR,
                    "missing_price",
                    f"Product {p.get('external_key')} has no sales_price",
                    p.get("external_key"),
                )
            )
        elif not isinstance(price, (int, float)) or isinstance(price, bool) or price <= 0:
            issues.append(
                Issue(
                    ERROR,
                    "invalid_price",
                    f"Product {p.get('external_key')} has an invalid sales_price: {price!r}",
                    p.get("external_key"),
                )
            )


def check_mandatory_names(data: CatalogueData, issues: list[Issue]) -> None:
    collections = {
        "category": data.categories,
        "product": data.products,
        "moment": data.moments,
        "recipient": data.recipients,
    }
    for kind, records in collections.items():
        for r in records:
            name = r.get("name_en")
            if not name or not str(name).strip():
                issues.append(
                    Issue(
                        ERROR,
                        "missing_mandatory_name_en",
                        f"{kind} {r.get('external_key')} has no name_en",
                        r.get("external_key"),
                    )
                )


def check_circular_category_parents(data: CatalogueData, issues: list[Issue]) -> None:
    parent_of = {c["external_key"]: c.get("parent_external_key") for c in data.categories}
    for start in parent_of:
        visited: set[str] = set()
        current = start
        while current is not None:
            if current in visited:
                issues.append(
                    Issue(
                        ERROR,
                        "circular_category_parent",
                        f"Circular parent_external_key chain detected starting at {start}",
                        start,
                    )
                )
                break
            visited.add(current)
            current = parent_of.get(current)


def check_warnings(data: CatalogueData, issues: list[Issue]) -> None:
    for p in data.products:
        if not p.get("name_ar"):
            issues.append(
                Issue(
                    WARNING,
                    "missing_name_ar",
                    f"Product {p.get('external_key')} has no Arabic name",
                    p.get("external_key"),
                    category=CONTENT_COMPLETION,
                )
            )
        if not p.get("description_ar"):
            issues.append(
                Issue(
                    WARNING,
                    "missing_description_ar",
                    f"Product {p.get('external_key')} has no Arabic description",
                    p.get("external_key"),
                    category=CONTENT_COMPLETION,
                )
            )
        if not p.get("description_en"):
            issues.append(
                Issue(
                    WARNING,
                    "missing_description_en",
                    f"Product {p.get('external_key')} has no English description",
                    p.get("external_key"),
                    category=CONTENT_COMPLETION,
                )
            )
        if p.get("sku_requires_confirmation"):
            key = p.get("external_key")
            sku = p.get("sku")
            issues.append(
                Issue(
                    WARNING,
                    "sku_requires_confirmation",
                    f"Product {key} SKU {sku} is generated and unconfirmed",
                    key,
                    category=BUSINESS_CONFIRMATION,
                )
            )
    for c in data.categories:
        if not c.get("name_ar"):
            issues.append(
                Issue(
                    WARNING,
                    "missing_name_ar",
                    f"Category {c.get('external_key')} has no Arabic name",
                    c.get("external_key"),
                    category=CONTENT_COMPLETION,
                )
            )


def check_business_confirmation_fields(data: CatalogueData, issues: list[Issue]) -> None:
    """Values that are technically valid but still need explicit business sign-off
    before Odoo import, per docs/catalogue/catalogue-decision-pack.md (D03, D04)."""
    for c in data.categories:
        if c.get("code_requires_confirmation"):
            issues.append(
                Issue(
                    WARNING,
                    "category_code_requires_confirmation",
                    f"Category {c.get('external_key')} code {c.get('code')} is generated "
                    "and unconfirmed",
                    c.get("external_key"),
                    category=BUSINESS_CONFIRMATION,
                )
            )


def check_odoo_verification_fields(data: CatalogueData, issues: list[Issue]) -> None:
    """Fields that cannot be finalized without access to a real Odoo instance, per
    docs/catalogue/odoo-configuration-checklist.md (D08, D09)."""
    for p in data.products:
        key = p.get("external_key")
        if not p.get("tax_reference"):
            issues.append(
                Issue(
                    WARNING,
                    "tax_reference_requires_odoo_verification",
                    f"Product {key} has no tax_reference — real Odoo account.tax mapping "
                    "requires environment access",
                    key,
                    category=ODOO_VERIFICATION,
                )
            )
        if not p.get("unit_of_measure"):
            issues.append(
                Issue(
                    WARNING,
                    "unit_of_measure_requires_odoo_verification",
                    f"Product {key} has no unit_of_measure — real Odoo uom.uom mapping "
                    "requires environment access",
                    key,
                    category=ODOO_VERIFICATION,
                )
            )


def check_merchandising_non_blocking(data: CatalogueData, issues: list[Issue]) -> None:
    """Merchandising-only gaps that never block catalogue/Odoo readiness, per
    docs/catalogue/final-data-ownership.md."""
    for m in data.merchandising:
        key = m.get("product_external_key")
        if m.get("display_order_generated"):
            issues.append(
                Issue(
                    WARNING,
                    "display_order_requires_confirmation",
                    f"Product {key} display_order is generated from array position, not a "
                    "business source",
                    key,
                    category=MERCHANDISING,
                )
            )
        if m.get("is_bestseller") is None:
            issues.append(
                Issue(
                    WARNING,
                    "is_bestseller_concept_undefined",
                    f"Product {key} has no is_bestseller value — concept does not exist yet",
                    key,
                    category=MERCHANDISING,
                )
            )


CHECKS = [
    check_duplicate_external_keys,
    check_duplicate_skus,
    check_duplicate_slugs,
    check_missing_category_references,
    check_merchandising_references,
    check_moment_and_recipient_references,
    check_recommendation_references,
    check_images,
    check_prices,
    check_mandatory_names,
    check_circular_category_parents,
    check_warnings,
    check_business_confirmation_fields,
    check_odoo_verification_fields,
    check_merchandising_non_blocking,
]


def run_validation(data: CatalogueData) -> list[Issue]:
    issues: list[Issue] = []
    for check in CHECKS:
        check(data, issues)
    return issues


CATEGORY_LABELS = {
    BLOCKING: "Blocking errors",
    BUSINESS_CONFIRMATION: "Business-confirmation warnings",
    ODOO_VERIFICATION: "Odoo-verification warnings",
    CONTENT_COMPLETION: "Content-completion warnings",
    MERCHANDISING: "Non-blocking merchandising warnings",
}


def build_report(issues: list[Issue]) -> dict[str, Any]:
    errors = [i for i in issues if i.severity == ERROR]
    warnings = [i for i in issues if i.severity == WARNING]
    by_category = {
        category: len([i for i in issues if i.category == category]) for category in CATEGORY_LABELS
    }
    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "status": "fail" if errors else "pass",
        "summary": {
            "total_issues": len(issues),
            "errors": len(errors),
            "warnings": len(warnings),
        },
        "summary_by_category": by_category,
        "issues": [
            {
                "severity": i.severity,
                "code": i.code,
                "message": i.message,
                "entity": i.entity,
                "category": i.category,
            }
            for i in issues
        ],
    }


def print_human_readable(issues: list[Issue]) -> None:
    errors = [i for i in issues if i.severity == ERROR]
    warnings = [i for i in issues if i.severity == WARNING]

    print(f"Catalogue validation: {len(errors)} error(s), {len(warnings)} warning(s)\n")

    if errors:
        print("ERRORS (blocking):")
        for i in errors:
            print(f"  [{i.code}] {i.message}")
        print()

    for category, label in CATEGORY_LABELS.items():
        if category == BLOCKING:
            continue
        category_warnings = [i for i in warnings if i.category == category]
        if category_warnings:
            print(f"{label.upper()}:")
            for i in category_warnings:
                print(f"  [{i.code}] {i.message}")
            print()

    if not errors and not warnings:
        print("No issues found.")


def main() -> int:
    data = load_catalogue()
    issues = run_validation(data)
    print_human_readable(issues)

    report = build_report(issues)
    with REPORT_PATH.open("w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
        f.write("\n")
    print(f"Report written to {REPORT_PATH.relative_to(REPO_ROOT)}")

    return 1 if report["status"] == "fail" else 0


if __name__ == "__main__":
    sys.exit(main())
