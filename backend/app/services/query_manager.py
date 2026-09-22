from __future__ import annotations

import json
import re
from dataclasses import dataclass

import networkx as nx
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.graph.validator import build_networkx_graph
from app.models import Analysis, DiagramElement, Query, ScanSession, utc_now
from app.services.session_manager import get_active_session


@dataclass(frozen=True)
class QueryAnswer:
    query: Query
    evidence: dict


def _latest_completed_analysis(db: Session, session: ScanSession) -> Analysis | None:
    return db.scalar(
        select(Analysis)
        .join(Analysis.diagram)
        .where(Analysis.diagram.has(session_id=session.id))
        .where(Analysis.status == "COMPLETED")
        .options(
            selectinload(Analysis.elements),
            selectinload(Analysis.edges),
            selectinload(Analysis.issues),
        )
        .order_by(Analysis.created_at.desc())
    )


def _element_name(element: DiagramElement) -> str:
    return element.label or element.ocr_text or element.element_key


def _find_element(question: str, elements: list[DiagramElement]) -> DiagramElement | None:
    normalized_question = question.lower()
    for element in elements:
        candidates = [
            element.element_key,
            element.label or "",
            element.ocr_text or "",
            element.element_type,
        ]
        if any(candidate and candidate.lower() in normalized_question for candidate in candidates):
            return element
    return None


def _format_elements(element_keys: list[str], elements_by_key: dict[str, DiagramElement]) -> str:
    names = [_element_name(elements_by_key[key]) for key in element_keys if key in elements_by_key]
    if not names:
        return "no elements"
    if len(names) == 1:
        return names[0]
    return ", ".join(names[:-1]) + f", and {names[-1]}"


def _answer_downstream(
    graph: nx.DiGraph,
    element: DiagramElement,
    elements_by_key: dict[str, DiagramElement],
) -> tuple[str, dict]:
    descendants = sorted(nx.descendants(graph, element.element_key))
    if not descendants:
        return (
            f"{_element_name(element)} does not currently affect any later detected element.",
            {"intent": "downstream", "element_key": element.element_key, "downstream": []},
        )
    return (
        f"{_element_name(element)} can affect {_format_elements(descendants, elements_by_key)}.",
        {"intent": "downstream", "element_key": element.element_key, "downstream": descendants},
    )


def _answer_removal(
    graph: nx.DiGraph,
    element: DiagramElement,
    elements_by_key: dict[str, DiagramElement],
) -> tuple[str, dict]:
    downstream = sorted(nx.descendants(graph, element.element_key))
    upstream = sorted(nx.ancestors(graph, element.element_key))
    affected = sorted(set(downstream + upstream))
    if not affected:
        answer = f"Removing {_element_name(element)} would isolate only that element in the detected graph."
    else:
        answer = (
            f"Removing {_element_name(element)} would affect paths touching "
            f"{_format_elements(affected, elements_by_key)}."
        )
    return (
        answer,
        {
            "intent": "remove_element",
            "element_key": element.element_key,
            "upstream": upstream,
            "downstream": downstream,
        },
    )


def _answer_path(
    question: str,
    graph: nx.DiGraph,
    elements: list[DiagramElement],
    elements_by_key: dict[str, DiagramElement],
) -> tuple[str, dict] | None:
    matches = [element for element in elements if (element.label or element.element_key).lower() in question.lower()]
    if len(matches) < 2:
        keys = re.findall(r"\bnode_\d+\b", question.lower())
        matches = [elements_by_key[key] for key in keys if key in elements_by_key]
    if len(matches) < 2:
        return None

    source, target = matches[0], matches[1]
    if not nx.has_path(graph, source.element_key, target.element_key):
        return (
            f"No directed path is currently detected from {_element_name(source)} to {_element_name(target)}.",
            {"intent": "path", "source": source.element_key, "target": target.element_key, "path": []},
        )
    path = nx.shortest_path(graph, source.element_key, target.element_key)
    return (
        f"The detected path is {_format_elements(path, elements_by_key)}.",
        {"intent": "path", "source": source.element_key, "target": target.element_key, "path": path},
    )


def _answer_summary(analysis: Analysis) -> tuple[str, dict]:
    critical = sum(1 for issue in analysis.issues if issue.severity == "CRITICAL")
    warnings = sum(1 for issue in analysis.issues if issue.severity == "WARNING")
    answer = (
        f"This {analysis.diagram_type or 'diagram'} has {len(analysis.elements)} detected element(s), "
        f"{len(analysis.edges)} detected relationship(s), {critical} critical issue(s), "
        f"and {warnings} warning(s)."
    )
    return (
        answer,
        {
            "intent": "summary",
            "analysis_id": analysis.id,
            "element_count": len(analysis.elements),
            "edge_count": len(analysis.edges),
            "critical_count": critical,
            "warning_count": warnings,
        },
    )


def _answer_issues(analysis: Analysis) -> tuple[str, dict]:
    if not analysis.issues:
        return (
            "No supported structural issues were detected in the latest analysis.",
            {"intent": "issues", "issue_count": 0, "issues": []},
        )
    issues = [f"{issue.severity}: {issue.title}" for issue in analysis.issues[:5]]
    return (
        "The main detected issues are " + "; ".join(issues) + ".",
        {
            "intent": "issues",
            "issue_count": len(analysis.issues),
            "issues": [issue.issue_code for issue in analysis.issues],
        },
    )


def answer_what_if_query(db: Session, session_token: str, question: str) -> QueryAnswer | None:
    session = get_active_session(db=db, session_token=session_token)
    if session is None:
        return None

    analysis = _latest_completed_analysis(db, session)
    if analysis is None:
        raise ValueError("No completed analysis is available for this session.")

    elements_by_key = {element.element_key: element for element in analysis.elements}
    graph = build_networkx_graph(analysis.elements, analysis.edges)
    normalized = question.lower()
    selected_element = _find_element(question, analysis.elements)

    if any(term in normalized for term in ["issue", "problem", "warning", "error"]):
        answer, evidence = _answer_issues(analysis)
    elif any(term in normalized for term in ["path", "route", "reach"]):
        path_answer = _answer_path(question, graph, analysis.elements, elements_by_key)
        if path_answer is not None:
            answer, evidence = path_answer
        elif selected_element is not None:
            answer, evidence = _answer_downstream(graph, selected_element, elements_by_key)
        else:
            answer, evidence = _answer_summary(analysis)
    elif selected_element is not None and any(term in normalized for term in ["remove", "delete", "drop", "change"]):
        answer, evidence = _answer_removal(graph, selected_element, elements_by_key)
    elif selected_element is not None:
        answer, evidence = _answer_downstream(graph, selected_element, elements_by_key)
    else:
        answer, evidence = _answer_summary(analysis)

    query = Query(
        analysis=analysis,
        question=question,
        answer=answer,
        status="COMPLETED",
        evidence_json=json.dumps(evidence),
        completed_at=utc_now(),
    )
    db.add(query)
    db.commit()
    db.refresh(query)
    return QueryAnswer(query=query, evidence=evidence)
