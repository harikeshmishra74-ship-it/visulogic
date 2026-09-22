from dataclasses import dataclass
import json

import networkx as nx

from app.models import DiagramElement, GraphEdge


@dataclass(frozen=True)
class ValidationFinding:
    issue_code: str
    severity: str
    title: str
    description: str
    element_key: str | None
    edge_key: str | None
    evidence_json: str
    fix_suggestion: str


def _node_label(element: DiagramElement) -> str:
    return element.label or element.ocr_text or element.element_key


def build_networkx_graph(
    elements: list[DiagramElement],
    edges: list[GraphEdge],
) -> nx.DiGraph:
    graph = nx.DiGraph()
    for element in elements:
        graph.add_node(
            element.element_key,
            element_type=element.element_type,
            label=_node_label(element),
            db_id=element.id,
        )
    for edge in edges:
        graph.add_edge(
            edge.source_element.element_key,
            edge.target_element.element_key,
            edge_type=edge.edge_type,
            confidence=edge.confidence,
            db_id=edge.id,
        )
    return graph


def validate_graph(
    diagram_type: str | None,
    elements: list[DiagramElement],
    edges: list[GraphEdge],
) -> list[ValidationFinding]:
    graph = build_networkx_graph(elements, edges)
    findings: list[ValidationFinding] = []

    if not elements:
        return [
            ValidationFinding(
                issue_code="INVALID_STRUCTURE",
                severity="CRITICAL",
                title="No diagram elements detected",
                description="VisuLogic could not detect supported diagram elements in this image.",
                element_key=None,
                edge_key=None,
                evidence_json=json.dumps({"element_count": 0, "edge_count": len(edges)}),
                fix_suggestion="Upload a clearer diagram with visible shapes and connectors.",
            )
        ]

    if len(elements) > 1 and not edges:
        findings.append(
            ValidationFinding(
                issue_code="DISCONNECTED_COMPONENT",
                severity="CRITICAL",
                title="No relationships detected",
                description="Multiple elements were detected, but no connecting flow or relationship was found.",
                element_key=None,
                edge_key=None,
                evidence_json=json.dumps(
                    {"element_keys": [element.element_key for element in elements], "edge_count": 0}
                ),
                fix_suggestion="Add visible connectors or arrows between related diagram elements.",
            )
        )

    weak_components = list(nx.weakly_connected_components(graph))
    if len(weak_components) > 1:
        for component in weak_components:
            findings.append(
                ValidationFinding(
                    issue_code="DISCONNECTED_COMPONENT",
                    severity="CRITICAL",
                    title="Disconnected diagram section",
                    description="This element belongs to a section that is not connected to the rest of the diagram.",
                    element_key=sorted(component)[0],
                    edge_key=None,
                    evidence_json=json.dumps({"component": sorted(component)}),
                    fix_suggestion="Connect this section to the main diagram flow or remove it if it is not needed.",
                )
            )

    start_nodes = [
        element.element_key
        for element in elements
        if element.element_type == "START" or (_node_label(element).lower() == "start")
    ]
    end_nodes = [
        element.element_key
        for element in elements
        if element.element_type == "END" or (_node_label(element).lower() == "end")
    ]

    if diagram_type == "Flowchart":
        if not start_nodes:
            findings.append(
                ValidationFinding(
                    issue_code="MISSING_START",
                    severity="WARNING",
                    title="Missing Start element",
                    description="A flowchart should normally include a visible Start element.",
                    element_key=None,
                    edge_key=None,
                    evidence_json=json.dumps({"detected_types": [element.element_type for element in elements]}),
                    fix_suggestion="Add or clearly label the starting point of the flowchart.",
                )
            )
        if not end_nodes:
            findings.append(
                ValidationFinding(
                    issue_code="MISSING_END",
                    severity="WARNING",
                    title="Missing End element",
                    description="A flowchart should normally include a visible End element.",
                    element_key=None,
                    edge_key=None,
                    evidence_json=json.dumps({"detected_types": [element.element_type for element in elements]}),
                    fix_suggestion="Add or clearly label the ending point of the flowchart.",
                )
            )

    reachable: set[str] = set()
    for start in start_nodes:
        if start in graph:
            reachable.add(start)
            reachable.update(nx.descendants(graph, start))
    if start_nodes:
        for element in elements:
            if element.element_key not in reachable:
                findings.append(
                    ValidationFinding(
                        issue_code="UNREACHABLE_NODE",
                        severity="WARNING",
                        title="Unreachable element",
                        description="This element is not reachable from the detected Start element.",
                        element_key=element.element_key,
                        edge_key=None,
                        evidence_json=json.dumps({"start_nodes": start_nodes, "element_key": element.element_key}),
                        fix_suggestion="Connect this element to the main flow from Start.",
                    )
                )

    for element in elements:
        if graph.out_degree(element.element_key) == 0 and element.element_key not in end_nodes:
            findings.append(
                ValidationFinding(
                    issue_code="DEAD_END",
                    severity="WARNING",
                    title="Dead-end element",
                    description="This element has no outgoing connection in the detected graph.",
                    element_key=element.element_key,
                    edge_key=None,
                    evidence_json=json.dumps(
                        {
                            "element_key": element.element_key,
                            "element_type": element.element_type,
                            "out_degree": 0,
                        }
                    ),
                    fix_suggestion="Connect this element to the next valid step, or mark it clearly as an End.",
                )
            )

    for element in elements:
        if element.element_type == "DECISION" and graph.out_degree(element.element_key) < 2:
            findings.append(
                ValidationFinding(
                    issue_code="MISSING_BRANCH",
                    severity="WARNING",
                    title="Decision is missing a branch",
                    description="A decision element should usually have at least two outgoing paths.",
                    element_key=element.element_key,
                    edge_key=None,
                    evidence_json=json.dumps(
                        {"element_key": element.element_key, "out_degree": graph.out_degree(element.element_key)}
                    ),
                    fix_suggestion="Add separate outgoing paths for each decision outcome.",
                )
            )

    return findings

