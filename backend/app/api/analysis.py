from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas import (
    AnalysisResponse,
    DiagramElementResponse,
    GraphEdgeResponse,
    PreprocessingResponse,
    ValidationIssueResponse,
)
from app.services.analysis_manager import run_classification_analysis

router = APIRouter(prefix="/analysis", tags=["analysis"])


@router.post("/{session_token}", response_model=AnalysisResponse)
def analyze(session_token: str, db: Session = Depends(get_db)) -> AnalysisResponse:
    try:
        result = run_classification_analysis(db=db, session_token=session_token)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Analysis failed before completion. Try a clearer diagram or retry the request.",
        ) from exc

    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Scan session is invalid or expired.",
        )

    analysis, metadata = result
    preprocessing = metadata["preprocessing"]
    issue_explanations = metadata["issue_explanations"]
    return AnalysisResponse(
        analysis_id=analysis.id,
        status=analysis.status,
        diagram_type=analysis.diagram_type,
        classification_confidence=analysis.classification_confidence,
        low_confidence=metadata["low_confidence"],
        preprocessing=PreprocessingResponse(
            original_width=preprocessing.original_width,
            original_height=preprocessing.original_height,
            processed_width=preprocessing.processed_width,
            processed_height=preprocessing.processed_height,
        ),
        classification_evidence=metadata["classification_evidence"],
        elements=[
            DiagramElementResponse(
                element_key=element.element_key,
                element_type=element.element_type,
                label=element.label,
                x=element.x,
                y=element.y,
                width=element.width,
                height=element.height,
                confidence=element.confidence,
                ocr_text=element.ocr_text,
            )
            for element in metadata["elements"]
        ],
        edges=[
            GraphEdgeResponse(
                source_key=edge.source_key,
                target_key=edge.target_key,
                edge_type=edge.edge_type,
                label=edge.label,
                confidence=edge.confidence,
            )
            for edge in metadata["edges"]
        ],
        issues=[
            ValidationIssueResponse(
                issue_code=issue.issue_code,
                severity=issue.severity,
                title=issue.title,
                description=issue.description,
                element_key=issue.element_key,
                evidence=issue.evidence_json,
                fix_suggestion=issue.fix_suggestion,
                what=issue_explanations[index].what,
                where=issue_explanations[index].where,
                why=issue_explanations[index].why,
                fix=issue_explanations[index].fix,
            )
            for index, issue in enumerate(metadata["issues"])
        ],
    )
