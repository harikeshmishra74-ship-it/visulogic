from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas import DiagramUploadResponse
from app.services.upload_manager import UploadValidationError, create_uploaded_diagram

router = APIRouter(prefix="/upload", tags=["upload"])


@router.post("", response_model=DiagramUploadResponse)
async def upload_diagram(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> DiagramUploadResponse:
    try:
        session, diagram = await create_uploaded_diagram(db=db, upload=file)
    except UploadValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": exc.code, "message": str(exc)},
        ) from exc

    return DiagramUploadResponse(
        session_token=session.session_token,
        session_status=session.status,
        diagram_id=diagram.id,
        file_name=diagram.file_name,
        file_type=diagram.file_type,
        file_size=diagram.file_size,
        width=diagram.width,
        height=diagram.height,
        source=diagram.source,
        created_at=diagram.created_at,
    )
