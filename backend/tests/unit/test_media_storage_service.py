from __future__ import annotations

from pathlib import Path

from app.core.config import Settings
from app.services.catalogue.media_storage_service import (
    MediaStorageService,
    sniff_image_extension,
)

_JPEG_BYTES = b"\xff\xd8\xff\xe0rest-of-a-fake-jpeg"
_PNG_BYTES = b"\x89PNG\r\n\x1a\nrest-of-a-fake-png"


def test_sniff_image_extension_detects_jpeg() -> None:
    assert sniff_image_extension(_JPEG_BYTES) == "jpg"


def test_sniff_image_extension_detects_png() -> None:
    assert sniff_image_extension(_PNG_BYTES) == "png"


def test_sniff_image_extension_falls_back_to_bin_for_unknown_bytes() -> None:
    assert sniff_image_extension(b"not an image") == "bin"


def test_save_product_image_writes_file_and_returns_url(tmp_path: Path) -> None:
    settings = Settings(media_root=str(tmp_path), media_base_url="http://localhost:8000/media")
    service = MediaStorageService(settings)

    relative_path, absolute_url = service.save_product_image(
        "chocolate-cake", "PRIMARY", 0, _JPEG_BYTES
    )

    assert relative_path == "catalogue/products/chocolate-cake-primary-0.jpg"
    assert (
        absolute_url
        == "http://localhost:8000/media/catalogue/products/chocolate-cake-primary-0.jpg"
    )
    assert (tmp_path / relative_path).read_bytes() == _JPEG_BYTES


def test_save_product_image_overwrites_same_path_on_reupload(tmp_path: Path) -> None:
    settings = Settings(media_root=str(tmp_path), media_base_url="http://localhost:8000/media")
    service = MediaStorageService(settings)
    updated_jpeg = _JPEG_BYTES + b"-updated"

    first_path, _ = service.save_product_image("chocolate-cake", "PRIMARY", 0, _JPEG_BYTES)
    second_path, _ = service.save_product_image("chocolate-cake", "PRIMARY", 0, updated_jpeg)

    # Same product+role+display_order+format re-synced overwrites the same
    # deterministic filename in place (matches upsert_by_product_and_path's
    # idempotent matching key on the Postgres side).
    assert first_path == second_path
    assert (tmp_path / second_path).read_bytes() == updated_jpeg
