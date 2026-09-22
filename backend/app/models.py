from datetime import UTC, datetime

from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


def utc_now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class ScanSession(Base):
    __tablename__ = "scan_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    session_token: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="CREATED")
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utc_now)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    connected_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    client_ip_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(Text, nullable=True)

    diagrams: Mapped[list["Diagram"]] = relationship(
        back_populates="session",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("ix_scan_sessions_status", "status"),
        Index("ix_scan_sessions_expires_at", "expires_at"),
    )


class Diagram(Base):
    __tablename__ = "diagrams"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    session_id: Mapped[int] = mapped_column(
        ForeignKey("scan_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    file_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    file_type: Mapped[str] = mapped_column(String(20), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    storage_path: Mapped[str] = mapped_column(Text, nullable=False)
    width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    height: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source: Mapped[str] = mapped_column(String(20), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utc_now)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    session: Mapped[ScanSession] = relationship(back_populates="diagrams")
    analyses: Mapped[list["Analysis"]] = relationship(
        back_populates="diagram",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("ix_diagrams_session_id", "session_id"),
        Index("ix_diagrams_created_at", "created_at"),
    )


class Analysis(Base):
    __tablename__ = "analyses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    diagram_id: Mapped[int] = mapped_column(
        ForeignKey("diagrams.id", ondelete="CASCADE"),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="QUEUED")
    diagram_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    classification_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    processing_started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    processing_completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utc_now)

    diagram: Mapped[Diagram] = relationship(back_populates="analyses")
    elements: Mapped[list["DiagramElement"]] = relationship(
        back_populates="analysis",
        cascade="all, delete-orphan",
    )
    edges: Mapped[list["GraphEdge"]] = relationship(
        back_populates="analysis",
        cascade="all, delete-orphan",
    )
    issues: Mapped[list["ValidationIssue"]] = relationship(
        back_populates="analysis",
        cascade="all, delete-orphan",
    )
    queries: Mapped[list["Query"]] = relationship(
        back_populates="analysis",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("ix_analyses_diagram_id", "diagram_id"),
        Index("ix_analyses_status", "status"),
        Index("ix_analyses_created_at", "created_at"),
    )


class DiagramElement(Base):
    __tablename__ = "diagram_elements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    analysis_id: Mapped[int] = mapped_column(
        ForeignKey("analyses.id", ondelete="CASCADE"),
        nullable=False,
    )
    element_key: Mapped[str] = mapped_column(String(100), nullable=False)
    element_type: Mapped[str] = mapped_column(String(50), nullable=False)
    label: Mapped[str | None] = mapped_column(Text, nullable=True)
    x: Mapped[float] = mapped_column(Float, nullable=False)
    y: Mapped[float] = mapped_column(Float, nullable=False)
    width: Mapped[float] = mapped_column(Float, nullable=False)
    height: Mapped[float] = mapped_column(Float, nullable=False)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    ocr_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utc_now)

    analysis: Mapped[Analysis] = relationship(back_populates="elements")
    outgoing_edges: Mapped[list["GraphEdge"]] = relationship(
        back_populates="source_element",
        foreign_keys="GraphEdge.source_element_id",
    )
    incoming_edges: Mapped[list["GraphEdge"]] = relationship(
        back_populates="target_element",
        foreign_keys="GraphEdge.target_element_id",
    )

    __table_args__ = (
        Index("ix_diagram_elements_analysis_id", "analysis_id"),
        Index("ix_diagram_elements_element_type", "element_type"),
        Index("ix_diagram_elements_analysis_key", "analysis_id", "element_key", unique=True),
    )


class GraphEdge(Base):
    __tablename__ = "graph_edges"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    analysis_id: Mapped[int] = mapped_column(
        ForeignKey("analyses.id", ondelete="CASCADE"),
        nullable=False,
    )
    source_element_id: Mapped[int] = mapped_column(
        ForeignKey("diagram_elements.id", ondelete="CASCADE"),
        nullable=False,
    )
    target_element_id: Mapped[int] = mapped_column(
        ForeignKey("diagram_elements.id", ondelete="CASCADE"),
        nullable=False,
    )
    edge_type: Mapped[str] = mapped_column(String(50), nullable=False)
    label: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utc_now)

    analysis: Mapped[Analysis] = relationship(back_populates="edges")
    source_element: Mapped[DiagramElement] = relationship(
        back_populates="outgoing_edges",
        foreign_keys=[source_element_id],
    )
    target_element: Mapped[DiagramElement] = relationship(
        back_populates="incoming_edges",
        foreign_keys=[target_element_id],
    )

    __table_args__ = (
        Index("ix_graph_edges_analysis_id", "analysis_id"),
        Index("ix_graph_edges_source_element_id", "source_element_id"),
        Index("ix_graph_edges_target_element_id", "target_element_id"),
        Index("ix_graph_edges_analysis_source", "analysis_id", "source_element_id"),
        Index("ix_graph_edges_analysis_target", "analysis_id", "target_element_id"),
    )


class ValidationIssue(Base):
    __tablename__ = "validation_issues"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    analysis_id: Mapped[int] = mapped_column(
        ForeignKey("analyses.id", ondelete="CASCADE"),
        nullable=False,
    )
    issue_code: Mapped[str] = mapped_column(String(100), nullable=False)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    element_id: Mapped[int | None] = mapped_column(
        ForeignKey("diagram_elements.id", ondelete="SET NULL"),
        nullable=True,
    )
    edge_id: Mapped[int | None] = mapped_column(
        ForeignKey("graph_edges.id", ondelete="SET NULL"),
        nullable=True,
    )
    evidence_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    fix_suggestion: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utc_now)

    analysis: Mapped[Analysis] = relationship(back_populates="issues")

    __table_args__ = (
        Index("ix_validation_issues_analysis_id", "analysis_id"),
        Index("ix_validation_issues_severity", "severity"),
        Index("ix_validation_issues_issue_code", "issue_code"),
        Index("ix_validation_issues_element_id", "element_id"),
    )


class Query(Base):
    __tablename__ = "queries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    analysis_id: Mapped[int] = mapped_column(
        ForeignKey("analyses.id", ondelete="CASCADE"),
        nullable=False,
    )
    question: Mapped[str] = mapped_column(Text, nullable=False)
    answer: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="QUEUED")
    evidence_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utc_now)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    analysis: Mapped[Analysis] = relationship(back_populates="queries")

    __table_args__ = (
        Index("ix_queries_analysis_id", "analysis_id"),
        Index("ix_queries_created_at", "created_at"),
    )
