from datetime import timedelta
from secrets import token_urlsafe

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import ScanSession, utc_now


def create_scan_session(db: Session) -> ScanSession:
    settings = get_settings()
    session = ScanSession(
        session_token=token_urlsafe(32),
        status="CREATED",
        expires_at=utc_now() + timedelta(minutes=settings.session_ttl_minutes),
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def get_active_session(db: Session, session_token: str) -> ScanSession | None:
    session = db.scalar(
        select(ScanSession).where(ScanSession.session_token == session_token)
    )
    if session is None:
        return None
    if session.expires_at <= utc_now() and session.status not in {
        "COMPLETED",
        "CANCELLED",
        "FAILED",
        "EXPIRED",
    }:
        session.status = "EXPIRED"
        db.commit()
        return None
    return session


def mark_phone_connected(db: Session, session_token: str) -> ScanSession | None:
    session = get_active_session(db=db, session_token=session_token)
    if session is None:
        return None
    if session.status == "CREATED":
        session.status = "PHONE_CONNECTED"
        session.connected_at = utc_now()
        db.commit()
        db.refresh(session)
    return session
