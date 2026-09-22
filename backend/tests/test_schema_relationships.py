from datetime import timedelta

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import Base
from app.models import Analysis, Diagram, DiagramElement, GraphEdge, ScanSession, utc_now


def make_db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine, autocommit=False, autoflush=False)()


def test_analysis_cascades_elements_and_edges():
    db = make_db()
    scan = ScanSession(
        session_token="token",
        status="CREATED",
        expires_at=utc_now() + timedelta(minutes=10),
    )
    diagram = Diagram(
        session=scan,
        file_name="sample.png",
        file_type="PNG",
        file_size=100,
        storage_path="uploads/sample.png",
        source="UPLOAD",
    )
    analysis = Analysis(diagram=diagram, status="QUEUED")
    start = DiagramElement(
        analysis=analysis,
        element_key="n1",
        element_type="START",
        label="Start",
        x=0,
        y=0,
        width=10,
        height=10,
    )
    end = DiagramElement(
        analysis=analysis,
        element_key="n2",
        element_type="END",
        label="End",
        x=20,
        y=0,
        width=10,
        height=10,
    )
    edge = GraphEdge(
        analysis=analysis,
        source_element=start,
        target_element=end,
        edge_type="FLOW",
    )
    db.add_all([scan, diagram, analysis, start, end, edge])
    db.commit()

    db.delete(analysis)
    db.commit()

    assert db.query(DiagramElement).count() == 0
    assert db.query(GraphEdge).count() == 0
