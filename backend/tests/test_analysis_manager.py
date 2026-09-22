from datetime import timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import Base
from app.models import Analysis, Diagram, ScanSession, utc_now
from app.services import analysis_manager


def make_db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine, autocommit=False, autoflush=False)()


def test_failed_analysis_records_error_state(monkeypatch):
    db = make_db()
    scan = ScanSession(
        session_token="failure-token",
        status="IMAGE_RECEIVED",
        expires_at=utc_now() + timedelta(minutes=10),
    )
    diagram = Diagram(
        session=scan,
        file_name="broken.png",
        file_type="PNG",
        file_size=100,
        storage_path="uploads/broken.png",
        source="UPLOAD",
    )
    db.add_all([scan, diagram])
    db.commit()

    def fail_preprocessing(*_args, **_kwargs):
        raise RuntimeError("image could not be decoded")

    monkeypatch.setattr(analysis_manager, "preprocess_image", fail_preprocessing)

    with pytest.raises(RuntimeError):
        analysis_manager.run_classification_analysis(db, "failure-token")

    analysis = db.query(Analysis).one()
    assert analysis.status == "FAILED"
    assert analysis.error_code == "RuntimeError"
    assert analysis.error_message == "image could not be decoded"
