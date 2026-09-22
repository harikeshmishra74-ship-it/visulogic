from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas import QueryRequest, QueryResponse
from app.services.query_manager import answer_what_if_query

router = APIRouter(prefix="/query", tags=["query"])


@router.post("/{session_token}", response_model=QueryResponse)
def answer_what_if(
    session_token: str,
    request: QueryRequest,
    db: Session = Depends(get_db),
) -> QueryResponse:
    try:
        result = answer_what_if_query(
            db=db,
            session_token=session_token,
            question=request.question,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Scan session is invalid or expired.",
        )

    return QueryResponse(
        status=result.query.status,
        query_id=result.query.id,
        analysis_id=result.query.analysis_id,
        answer=result.query.answer,
        evidence=result.evidence,
    )
