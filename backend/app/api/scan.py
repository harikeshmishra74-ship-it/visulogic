from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas import DiagramUploadResponse, ScanSessionCreateResponse, ScanSessionStatusResponse
from app.services.session_manager import (
    create_scan_session,
    get_active_session,
    mark_phone_connected,
)
from app.services.upload_manager import UploadValidationError, attach_phone_scan_diagram

router = APIRouter(prefix="/scan", tags=["scan"])


@router.post("/create", response_model=ScanSessionCreateResponse)
def create_session(request: Request, db: Session = Depends(get_db)) -> ScanSessionCreateResponse:
    base_url = str(request.base_url).rstrip("/")
    session = create_scan_session(db=db)
    return ScanSessionCreateResponse(
        session_token=session.session_token,
        session_url=f"{base_url}/mobile/scan/{session.session_token}",
        status=session.status,
        expires_at=session.expires_at,
    )


@router.post("/{session_token}/connect", response_model=ScanSessionStatusResponse)
def connect_phone(session_token: str, db: Session = Depends(get_db)) -> ScanSessionStatusResponse:
    session = mark_phone_connected(db=db, session_token=session_token)
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Scan session is invalid or expired.",
        )
    return ScanSessionStatusResponse(
        session_token=session.session_token,
        status=session.status,
        expires_at=session.expires_at,
        connected_at=session.connected_at,
        completed_at=session.completed_at,
    )


@router.get("/{session_token}/status", response_model=ScanSessionStatusResponse)
def session_status(session_token: str, db: Session = Depends(get_db)) -> ScanSessionStatusResponse:
    session = get_active_session(db=db, session_token=session_token)
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Scan session is invalid or expired.",
        )
    return ScanSessionStatusResponse(
        session_token=session.session_token,
        status=session.status,
        expires_at=session.expires_at,
        connected_at=session.connected_at,
        completed_at=session.completed_at,
    )


@router.post("/{session_token}/upload", response_model=DiagramUploadResponse)
async def upload_phone_scan(
    session_token: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> DiagramUploadResponse:
    try:
        result = await attach_phone_scan_diagram(
            db=db,
            session_token=session_token,
            upload=file,
        )
    except UploadValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": exc.code, "message": str(exc)},
        ) from exc

    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Scan session is invalid or expired.",
        )

    session, diagram = result
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
