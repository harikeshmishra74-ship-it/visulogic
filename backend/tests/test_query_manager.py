from datetime import timedelta

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import Base
from app.models import (
    Analysis,
    Diagram,
    DiagramElement,
    GraphEdge,
    ScanSession,
    ValidationIssue,
    utc_now,
)
from app.services.query_manager import answer_what_if_query


def make_db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine, autocommit=False, autoflush=False)()


def seed_analysis():
    scan = ScanSession(
        session_token="query-token",
        status="IMAGE_RECEIVED",
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
    analysis = Analysis(diagram=diagram, status="COMPLETED", diagram_type="Flowchart")
    start = DiagramElement(
        analysis=analysis,
        element_key="node_1",
        element_type="START",
        label="Start",
        x=0,
        y=0,
        width=40,
        height=30,
    )
    approve = DiagramElement(
        analysis=analysis,
        element_key="node_2",
        element_type="PROCESS",
        label="Approve Request",
        x=100,
        y=0,
        width=80,
        height=30,
    )
    end = DiagramElement(
        analysis=analysis,
        element_key="node_3",
        element_type="END",
        label="End",
        x=220,
        y=0,
        width=40,
        height=30,
    )
    first_edge = GraphEdge(
        analysis=analysis,
        source_element=start,
        target_element=approve,
        edge_type="FLOW",
    )
    second_edge = GraphEdge(
        analysis=analysis,
        source_element=approve,
        target_element=end,
        edge_type="FLOW",
    )
    issue = ValidationIssue(
        analysis=analysis,
        issue_code="MISSING_BRANCH",
        severity="WARNING",
        title="Decision is missing a branch",
        description="A decision element should usually have at least two outgoing paths.",
        fix_suggestion="Add a second branch.",
    )
    return scan, diagram, analysis, start, approve, end, first_edge, second_edge, issue


def test_what_if_summary_is_persisted():
    db = make_db()
    db.add_all(seed_analysis())
    db.commit()

    result = answer_what_if_query(db, "query-token", "Summarize this diagram")

    assert result is not None
    assert result.query.status == "COMPLETED"
    assert result.query.id is not None
    assert "3 detected element" in result.query.answer
    assert result.evidence["intent"] == "summary"


def test_what_if_remove_element_reports_impacted_paths():
    db = make_db()
    db.add_all(seed_analysis())
    db.commit()

    result = answer_what_if_query(db, "query-token", "What if we remove Approve Request?")

    assert result is not None
    assert "Removing Approve Request" in result.query.answer
    assert result.evidence["upstream"] == ["node_1"]
    assert result.evidence["downstream"] == ["node_3"]


def test_what_if_issue_question_lists_validation_findings():
    db = make_db()
    db.add_all(seed_analysis())
    db.commit()

    result = answer_what_if_query(db, "query-token", "What issues should I fix?")

    assert result is not None
    assert "Decision is missing a branch" in result.query.answer
    assert result.evidence["issues"] == ["MISSING_BRANCH"]
