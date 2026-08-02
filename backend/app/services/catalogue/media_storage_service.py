"""Local-disk storage for image bytes pulled from Odoo (product.template.image_1920 /
product.image.image_1920 base64 payloads).

Deliberately local disk, not object storage: this app has no existing storage/
credential story to build on, and CLAUDE.md says not to introduce infrastructure
without a demonstrated need. This class is the one swappable seam — moving to S3/Azure
Blob later only touches this file, never the sync service that calls it.
"""

from __future__ import annotations

from pathlib import Path

from app.core.config import Settings

# Magic-byte sniffing instead of a Pillow dependency — Odoo's image fields are always
# PNG or JPEG in practice, and a hand-written check is enough for "what extension do I
# save this under."
_MAGIC_BYTES: tuple[tuple[bytes, str], ...] = (
    (b"\xff\xd8\xff", "jpg"),
    (b"\x89PNG\r\n\x1a\n", "png"),
    (b"GIF87a", "gif"),
    (b"GIF89a", "gif"),
    (b"RIFF", "webp"),
)


def sniff_image_extension(image_bytes: bytes) -> str:
    for signature, extension in _MAGIC_BYTES:
        if image_bytes.startswith(signature):
            return extension
    return "bin"


class MediaStorageService:
    def __init__(self, settings: Settings) -> None:
        self._root = Path(settings.media_root)
        self._base_url = settings.media_base_url.rstrip("/")

    def save_product_image(
        self, product_slug: str, role: str, display_order: int, image_bytes: bytes
    ) -> tuple[str, str]:
        """Writes `image_bytes` under MEDIA_ROOT/catalogue/products/ and returns
        (relative_path, absolute_url). relative_path is stored in the image row's
        original_path column (provenance — "where under MEDIA_ROOT this came from"),
        absolute_url is stored in storage_url and is what the API/frontend actually
        render (catalogue_query_service._image_out already prefers storage_url over
        original_path, so no frontend change is needed for this to work).
        """
        extension = sniff_image_extension(image_bytes)
        filename = f"{product_slug}-{role.lower()}-{display_order}.{extension}"
        relative_path = f"catalogue/products/{filename}"
        full_path = self._root / relative_path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_bytes(image_bytes)
        return relative_path, f"{self._base_url}/{relative_path}"
