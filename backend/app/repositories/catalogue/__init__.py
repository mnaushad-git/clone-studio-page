from __future__ import annotations

from app.repositories.catalogue.category_repository import CategoryRepository
from app.repositories.catalogue.moment_repository import MomentRepository
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
from app.repositories.catalogue.product_moment_repository import ProductMomentRepository
from app.repositories.catalogue.product_price_repository import ProductPriceRepository
from app.repositories.catalogue.product_recipient_repository import ProductRecipientRepository
from app.repositories.catalogue.product_recommendation_repository import (
    ProductRecommendationRepository,
)
from app.repositories.catalogue.product_repository import ProductRepository
from app.repositories.catalogue.product_variant_repository import ProductVariantRepository
from app.repositories.catalogue.recipient_repository import RecipientRepository

__all__ = [
    "CategoryRepository",
    "MomentRepository",
    "ProductAttributeValueRepository",
    "ProductAvailabilityRepository",
    "ProductImageRepository",
    "ProductMerchandisingRepository",
    "ProductMomentRepository",
    "ProductPriceRepository",
    "ProductRecipientRepository",
    "ProductRecommendationRepository",
    "ProductRepository",
    "ProductVariantRepository",
    "RecipientRepository",
]
