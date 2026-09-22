from dataclasses import dataclass
import json

from app.graph.validator import ValidationFinding
from app.models import DiagramElement


@dataclass(frozen=True)
class IssueExplanation:
    issue_code: str
    what: str
    where: str
    why: str
    fix: str


def _element_name(elements_by_key: dict[str, DiagramElement], element_key: str | None) -> str:
    if element_key is None:
        return "Diagram-wide"
    element = elements_by_key.get(element_key)
    if element is None:
        return element_key
    label = element.label or element.ocr_text
    if label:
        return f"{label} ({element.element_key})"
    return f"{element.element_type} {element.element_key}"


def _parse_evidence(evidence_json: str) -> dict:
    try:
        value = json.loads(evidence_json)
    except json.JSONDecodeError:
        return {}
    return value if isinstance(value, dict) else {}


def explain_issue(
    issue: ValidationFinding,
    elements_by_key: dict[str, DiagramElement],
) -> IssueExplanation:
    where = _element_name(elements_by_key, issue.element_key)
    evidence = _parse_evidence(issue.evidence_json)

    if issue.issue_code == "DEAD_END":
        element_type = evidence.get("element_type", "element")
        why = (
            f"The detected {element_type} has an out-degree of 0, so no outgoing path "
            "was found from this element."
        )
    elif issue.issue_code == "MISSING_BRANCH":
        out_degree = evidence.get("out_degree", 0)
        why = (
            f"The decision node has {out_degree} outgoing detected path(s). "
            "A decision normally needs separate branches for different outcomes."
        )
    elif issue.issue_code == "DISCONNECTED_COMPONENT":
        component = evidence.get("component") or evidence.get("element_keys") or []
        why = f"The graph evidence shows a disconnected set of elements: {component}."
    elif issue.issue_code == "UNREACHABLE_NODE":
        starts = evidence.get("start_nodes", [])
        why = f"The element is not reachable from the detected Start node(s): {starts}."
    elif issue.issue_code in {"MISSING_START", "MISSING_END"}:
        detected_types = evidence.get("detected_types", [])
        why = f"The detected element types are {detected_types}, and the expected marker was not found."
    elif issue.issue_code == "INVALID_STRUCTURE":
        why = "The extracted evidence does not contain enough supported elements to build a reliable graph."
    else:
        why = issue.description

    return IssueExplanation(
        issue_code=issue.issue_code,
        what=issue.title,
        where=where,
        why=why,
        fix=issue.fix_suggestion,
    )


def explain_issues(
    issues: list[ValidationFinding],
    elements: list[DiagramElement],
) -> list[IssueExplanation]:
    elements_by_key = {element.element_key: element for element in elements}
    return [explain_issue(issue, elements_by_key) for issue in issues]

