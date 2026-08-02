"""Reads the canonical catalogue JSON files under data/catalogue/.

Deliberately independent of backend/scripts/validate_catalogue.py (Phase 2A tooling,
not part of the installed `app` package) — this loader is the service layer's own,
minimal read path, per docs/catalogue/catalogue-import-readiness.md's framing of
Phase 3 as consuming the same canonical files by a new, separate mechanism.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[4]
DATA_DIR = REPO_ROOT / "data" / "catalogue"

CATEGORIES_PATH = DATA_DIR / "categories.json"
PRODUCTS_PATH = DATA_DIR / "products.json"
MERCHANDISING_PATH = DATA_DIR / "product-merchandising.json"
MOMENTS_PATH = DATA_DIR / "moments.json"
RECIPIENTS_PATH = DATA_DIR / "recipients.json"
RECOMMENDATIONS_PATH = DATA_DIR / "product-recommendations.json"

# Order matters: the checksum must be stable/reproducible across runs so re-seeding
# with unchanged source files is detectable as a no-op.
_SOURCE_FILES = (
    CATEGORIES_PATH,
    PRODUCTS_PATH,
    MERCHANDISING_PATH,
    MOMENTS_PATH,
    RECIPIENTS_PATH,
    RECOMMENDATIONS_PATH,
)


@dataclass
class CatalogueSeedData:
    categories: list[dict[str, Any]] = field(default_factory=list)
    products: list[dict[str, Any]] = field(default_factory=list)
    merchandising: list[dict[str, Any]] = field(default_factory=list)
    moments: list[dict[str, Any]] = field(default_factory=list)
    recipients: list[dict[str, Any]] = field(default_factory=list)
    recommendations: list[dict[str, Any]] = field(default_factory=list)
    source_checksum: str = ""


def _load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as f:
        result: dict[str, Any] = json.load(f)
        return result


def _compute_checksum() -> str:
    digest = hashlib.sha256()
    for path in _SOURCE_FILES:
        digest.update(path.name.encode("utf-8"))
        digest.update(path.read_bytes())
    return f"sha256:{digest.hexdigest()}"


def load_catalogue_seed_data() -> CatalogueSeedData:
    return CatalogueSeedData(
        categories=_load_json(CATEGORIES_PATH).get("categories", []),
        products=_load_json(PRODUCTS_PATH).get("products", []),
        merchandising=_load_json(MERCHANDISING_PATH).get("product_merchandising", []),
        moments=_load_json(MOMENTS_PATH).get("moments", []),
        recipients=_load_json(RECIPIENTS_PATH).get("recipients", []),
        recommendations=_load_json(RECOMMENDATIONS_PATH).get("product_recommendations", []),
        source_checksum=_compute_checksum(),
    )
