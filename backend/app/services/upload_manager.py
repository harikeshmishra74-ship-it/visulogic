from pathlib import Path
from secrets import token_urlsafe

from fastapi import UploadFile
from PIL import Image, UnidentifiedImageError
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import Diagram, ScanSession, utc_now
from app.services.session_manager import create_scan_session, get_active_session

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg"}
ALLOWED_MIME_TYPES = {"image/png", "image/jpeg"}


class UploadValidationError(ValueError):
    def __init__(self, message: str, code: str) -> None:
        super().__init__(message)
        self.code = code


def get_extension(filename: str | None) -> str:
    if not filename or "." not in filename:
        return ""
    return filename.rsplit(".", 1)[-1].lower()


def validate_image_bytes(
    *,
    contents: bytes,
    filename: str | None,
    content_type: str | None,
) -> tuple[str, int, int]:
    settings = get_settings()
    extension = get_extension(filename)

    if extension not in ALLOWED_EXTENSIONS or content_type not in ALLOWED_MIME_TYPES:
        raise UploadValidationError("Unsupported file type.", "UNSUPPORTED_FILE_TYPE")

    if not contents:
        raise UploadValidationError("We couldn't read this image.", "EMPTY_FILE")

    if len(contents) > settings.max_upload_bytes:
        raise UploadValidationError("This image is too large to process.", "FILE_TOO_LARGE")

    try:
        from io import BytesIO

        with Image.open(BytesIO(contents)) as image:
            image.verify()
        with Image.open(BytesIO(contents)) as image:
            width, height = image.size
    except (SyntaxError, UnidentifiedImageError, OSError) as exc:
        raise UploadValidationError("We couldn't read this image.", "INVALID_IMAGE") from exc

    if width <= 0 or height <= 0:
        raise UploadValidationError("We couldn't read this image.", "INVALID_IMAGE")

    if width * height > settings.max_image_pixels:
        raise UploadValidationError("This image is too large to process.", "IMAGE_DIMENSIONS_TOO_LARGE")

    return extension.upper(), width, height


async def create_uploaded_diagram(db: Session, upload: UploadFile) -> tuple[ScanSession, Diagram]:
    settings = get_settings()
    contents = await upload.read(settings.max_upload_bytes + 1)
    file_type, width, height = validate_image_bytes(
        contents=contents,
        filename=upload.filename,
        content_type=upload.content_type,
    )

    session = create_scan_session(db)
    session.status = "IMAGE_RECEIVED"

    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    storage_name = f"{session.session_token}_{token_urlsafe(12)}.{file_type.lower()}"
    storage_path = Path(settings.upload_dir) / storage_name
    storage_path.write_bytes(contents)

    diagram = Diagram(
        session=session,
        file_name=upload.filename,
        file_type=file_type,
        file_size=len(contents),
        storage_path=str(storage_path),
        width=width,
        height=height,
        source="UPLOAD",
        created_at=utc_now(),
    )
    db.add(diagram)
    db.commit()
    db.refresh(session)
    db.refresh(diagram)
    return session, diagram


async def attach_phone_scan_diagram(
    db: Session,
    session_token: str,
    upload: UploadFile,
) -> tuple[ScanSession, Diagram] | None:
    settings = get_settings()
    session = get_active_session(db=db, session_token=session_token)
    if session is None:
        return None
    if session.status not in {"CREATED", "PHONE_CONNECTED"}:
        raise UploadValidationError("This scan session cannot accept another image.", "SESSION_CLOSED")

    contents = await upload.read(settings.max_upload_bytes + 1)
    file_type, width, height = validate_image_bytes(
        contents=contents,
        filename=upload.filename,
        content_type=upload.content_type,
    )

    session.status = "IMAGE_RECEIVED"
    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    storage_name = f"{session.session_token}_{token_urlsafe(12)}.{file_type.lower()}"
    storage_path = Path(settings.upload_dir) / storage_name
    storage_path.write_bytes(contents)

    diagram = Diagram(
        session=session,
        file_name=upload.filename,
        file_type=file_type,
        file_size=len(contents),
        storage_path=str(storage_path),
        width=width,
        height=height,
        source="PHONE_SCAN",
        created_at=utc_now(),
    )
    db.add(diagram)
    db.commit()
    db.refresh(session)
    db.refresh(diagram)
    return session, diagram
