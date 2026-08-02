"""Catalogue domain models: categories, products, variants, prices, availability,
images, merchandising, moments, recipients, and recommendations.
"""

from __future__ import annotations

from app.models.catalogue.category import CatalogueCategory
from app.models.catalogue.moment import CatalogueMoment
from app.models.catalogue.product import CatalogueProduct
from app.models.catalogue.product_attribute_value import CatalogueProductAttributeValue
from app.models.catalogue.product_availability import CatalogueProductAvailability
from app.models.catalogue.product_image import CatalogueProductImage
from app.models.catalogue.product_merchandising import CatalogueProductMerchandising
from app.models.catalogue.product_moment import CatalogueProductMoment
from app.models.catalogue.product_price import CatalogueProductPrice
from app.models.catalogue.product_recipient import CatalogueProductRecipient
from app.models.catalogue.product_recommendation import CatalogueProductRecommendation
from app.models.catalogue.product_variant import CatalogueProductVariant
from app.models.catalogue.recipient import CatalogueRecipient

__all__ = [
    "CatalogueCategory",
    "CatalogueMoment",
    "CatalogueProduct",
    "CatalogueProductAttributeValue",
    "CatalogueProductAvailability",
    "CatalogueProductImage",
    "CatalogueProductMerchandising",
    "CatalogueProductMoment",
    "CatalogueProductPrice",
    "CatalogueProductRecipient",
    "CatalogueProductRecommendation",
    "CatalogueProductVariant",
    "CatalogueRecipient",
]
