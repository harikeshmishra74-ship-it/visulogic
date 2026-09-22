from datetime import datetime

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str = "ok"
    app: str = "VisuLogic"


class ScanSessionCreateResponse(BaseModel):
    session_token: str
    session_url: str
    status: str
    expires_at: datetime


class ScanSessionStatusResponse(BaseModel):
    session_token: str
    status: str
    expires_at: datetime
    connected_at: datetime | None = None
    completed_at: datetime | None = None


class DiagramUploadResponse(BaseModel):
    session_token: str
    session_status: str
    diagram_id: int
    file_name: str | None = None
    file_type: str
    file_size: int
    width: int | None = None
    height: int | None = None
    source: str
    created_at: datetime


class PreprocessingResponse(BaseModel):
    original_width: int
    original_height: int
    processed_width: int
    processed_height: int


class DiagramElementResponse(BaseModel):
    element_key: str
    element_type: str
    label: str | None = None
    x: float
    y: float
    width: float
    height: float
    confidence: float | None = None
    ocr_text: str | None = None


class GraphEdgeResponse(BaseModel):
    source_key: str
    target_key: str
    edge_type: str
    label: str | None = None
    confidence: float | None = None


class ValidationIssueResponse(BaseModel):
    issue_code: str
    severity: str
    title: str
    description: str
    element_key: str | None = None
    evidence: str | None = None
    fix_suggestion: str | None = None
    what: str | None = None
    where: str | None = None
    why: str | None = None
    fix: str | None = None


class AnalysisResponse(BaseModel):
    analysis_id: int
    status: str
    diagram_type: str | None = None
    classification_confidence: float | None = None
    low_confidence: bool = False
    preprocessing: PreprocessingResponse | None = None
    classification_evidence: dict[str, int] = Field(default_factory=dict)
    elements: list[DiagramElementResponse] = Field(default_factory=list)
    edges: list[GraphEdgeResponse] = Field(default_factory=list)
    issues: list[ValidationIssueResponse] = Field(default_factory=list)


class QueryRequest(BaseModel):
    question: str = Field(min_length=1, max_length=1000)


class QueryResponse(BaseModel):
    status: str
    query_id: int | None = None
    analysis_id: int | None = None
    answer: str | None = None
    evidence: dict | None = None
