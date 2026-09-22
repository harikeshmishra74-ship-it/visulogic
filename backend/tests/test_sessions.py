from datetime import timedelta

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import Base
from app.models import ScanSession, utc_now
from app.services.session_manager import (
    create_scan_session,
    get_active_session,
    mark_phone_connected,
)


def make_db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine, autocommit=False, autoflush=False)()


def test_create_scan_session_generates_active_token():
    db = make_db()

    session = create_scan_session(db)

    assert session.session_token
    assert session.status == "CREATED"
    assert session.expires_at > utc_now()


def test_phone_connection_updates_created_session():
    db = make_db()
    session = create_scan_session(db)

    connected = mark_phone_connected(db, session.session_token)

    assert connected is not None
    assert connected.status == "PHONE_CONNECTED"
    assert connected.connected_at is not None


def test_expired_session_is_marked_expired_and_hidden():
    db = make_db()
    session = ScanSession(
        session_token="expired-token",
        status="CREATED",
        expires_at=utc_now() - timedelta(minutes=1),
    )
    db.add(session)
    db.commit()

    active = get_active_session(db, "expired-token")

    assert active is None
    refreshed = db.query(ScanSession).filter_by(session_token="expired-token").one()
    assert refreshed.status == "EXPIRED"
