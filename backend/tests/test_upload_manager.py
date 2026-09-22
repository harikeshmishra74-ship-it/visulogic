from io import BytesIO
from types import SimpleNamespace

import pytest
from PIL import Image

from app.services import upload_manager
from app.services.upload_manager import UploadValidationError, validate_image_bytes


def make_png() -> bytes:
    buffer = BytesIO()
    Image.new("RGB", (24, 16), color="white").save(buffer, format="PNG")
    return buffer.getvalue()


def test_validate_image_bytes_accepts_png():
    file_type, width, height = validate_image_bytes(
        contents=make_png(),
        filename="diagram.png",
        content_type="image/png",
    )

    assert file_type == "PNG"
    assert width == 24
    assert height == 16


def test_validate_image_bytes_rejects_unsupported_extension():
    with pytest.raises(UploadValidationError) as exc:
        validate_image_bytes(
            contents=make_png(),
            filename="diagram.gif",
            content_type="image/gif",
        )

    assert exc.value.code == "UNSUPPORTED_FILE_TYPE"


def test_validate_image_bytes_rejects_invalid_image():
    with pytest.raises(UploadValidationError) as exc:
        validate_image_bytes(
            contents=b"not an image",
            filename="diagram.png",
            content_type="image/png",
        )

    assert exc.value.code == "INVALID_IMAGE"


def test_validate_image_bytes_rejects_excessive_pixel_count(monkeypatch):
    monkeypatch.setattr(
        upload_manager,
        "get_settings",
        lambda: SimpleNamespace(max_upload_bytes=8 * 1024 * 1024, max_image_pixels=100),
    )

    buffer = BytesIO()
    Image.new("RGB", (11, 10), color="white").save(buffer, format="PNG")

    with pytest.raises(UploadValidationError) as exc:
        validate_image_bytes(
            contents=buffer.getvalue(),
            filename="oversized.png",
            content_type="image/png",
        )

    assert exc.value.code == "IMAGE_DIMENSIONS_TOO_LARGE"
