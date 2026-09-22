from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.reasoning import explain_issues
from app.classification.diagram_classifier import classify_diagram
from app.config import get_settings
from app.cv.element_detector import extract_elements
from app.graph.graph_builder import build_graph_edges
from app.graph.validator import validate_graph
from app.models import (
    Analysis,
    Diagram,
    DiagramElement,
    GraphEdge,
    ScanSession,
    ValidationIssue,
    utc_now,
)
from app.preprocessing.image_cleaner import preprocess_image
from app.services.session_manager import get_active_session


def latest_session_diagram(db: Session, session: ScanSession) -> Diagram | None:
    return db.scalar(
        select(Diagram)
        .where(Diagram.session_id == session.id, Diagram.deleted_at.is_(None))
        .order_by(Diagram.created_at.desc())
    )


def run_classification_analysis(db: Session, session_token: str) -> tuple[Analysis, dict] | None:
    session = get_active_session(db=db, session_token=session_token)
    if session is None:
        return None

    diagram = latest_session_diagram(db, session)
    if diagram is None:
        raise ValueError("No diagram is associated with this session.")

    settings = get_settings()
    analysis = Analysis(
        diagram=diagram,
        status="CLASSIFYING",
        processing_started_at=utc_now(),
    )
    db.add(analysis)
    db.commit()
    db.refresh(analysis)

    try:
        processed_dir = Path(settings.upload_dir) / "processed"
        preprocessing = preprocess_image(diagram.storage_path, processed_dir)
        classification = classify_diagram(preprocessing.processed_path)

        analysis.diagram_type = classification.diagram_type
        analysis.classification_confidence = classification.confidence
        analysis.status = "EXTRACTING"
        db.commit()

        extracted_elements = extract_elements(preprocessing.processed_path)
        element_models: dict[str, DiagramElement] = {}
        for extracted in extracted_elements:
            element = DiagramElement(
                analysis=analysis,
                element_key=extracted.element_key,
                element_type=extracted.element_type,
                label=extracted.label,
                x=extracted.x,
                y=extracted.y,
                width=extracted.width,
                height=extracted.height,
                confidence=extracted.confidence,
                ocr_text=extracted.ocr_text,
            )
            db.add(element)
            element_models[extracted.element_key] = element

        analysis.status = "BUILDING_GRAPH"
        db.commit()

        graph_edges = build_graph_edges(preprocessing.processed_path, extracted_elements)
        edge_models: list[GraphEdge] = []
        for edge in graph_edges:
            source = element_models.get(edge.source_key)
            target = element_models.get(edge.target_key)
            if source is None or target is None:
                continue
            edge_model = GraphEdge(
                analysis=analysis,
                source_element=source,
                target_element=target,
                edge_type=edge.edge_type,
                label=edge.label,
                confidence=edge.confidence,
            )
            db.add(edge_model)
            edge_models.append(edge_model)

        analysis.status = "VALIDATING"
        db.commit()

        validation_findings = validate_graph(
            diagram_type=analysis.diagram_type,
            elements=list(element_models.values()),
            edges=edge_models,
        )
        for finding in validation_findings:
            affected_element = (
                element_models.get(finding.element_key)
                if finding.element_key is not None
                else None
            )
            db.add(
                ValidationIssue(
                    analysis=analysis,
                    issue_code=finding.issue_code,
                    severity=finding.severity,
                    title=finding.title,
                    description=finding.description,
                    element_id=affected_element.id if affected_element is not None else None,
                    evidence_json=finding.evidence_json,
                    fix_suggestion=finding.fix_suggestion,
                )
            )

        analysis.status = "GENERATING_INSIGHTS"
        db.commit()
        issue_explanations = explain_issues(
            validation_findings,
            list(element_models.values()),
        )

        analysis.status = "COMPLETED"
        analysis.processing_completed_at = utc_now()
        db.commit()
        db.refresh(analysis)

        return analysis, {
            "preprocessing": preprocessing,
            "classification_evidence": classification.evidence,
            "elements": extracted_elements,
            "edges": graph_edges,
            "issues": validation_findings,
            "issue_explanations": issue_explanations,
            "low_confidence": classification.confidence < 0.6,
        }
    except Exception as exc:
        db.rollback()
        analysis.status = "FAILED"
        analysis.error_code = exc.__class__.__name__
        analysis.error_message = str(exc) or "Analysis failed."
        analysis.processing_completed_at = utc_now()
        db.commit()
        raise
