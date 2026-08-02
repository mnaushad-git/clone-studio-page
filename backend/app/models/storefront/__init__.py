"""Storefront presentation models: homepage sections and their product assignments.

Modeled to support future homepage-rail wiring; does not change current frontend
behaviour (docs/catalogue/current-catalogue-audit.md §6 rail bug is preserved as-is
this phase).
"""

from __future__ import annotations

from app.models.storefront.section import StorefrontSection
from app.models.storefront.section_product import StorefrontSectionProduct

__all__ = ["StorefrontSection", "StorefrontSectionProduct"]
