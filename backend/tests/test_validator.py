from app.graph.validator import validate_graph
from app.models import DiagramElement, GraphEdge


def make_element(key: str, element_type: str = "PROCESS") -> DiagramElement:
    return DiagramElement(
        element_key=key,
        element_type=element_type,
        label=key,
        x=0,
        y=0,
        width=20,
        height=20,
    )


def test_validate_graph_reports_no_elements():
    issues = validate_graph("Flowchart", [], [])

    assert issues[0].issue_code == "INVALID_STRUCTURE"
    assert issues[0].severity == "CRITICAL"


def test_validate_graph_reports_dead_end():
    start = make_element("start", "START")
    process = make_element("process", "PROCESS")
    edge = GraphEdge(source_element=start, target_element=process, edge_type="FLOW")

    issues = validate_graph("Flowchart", [start, process], [edge])

    codes = {issue.issue_code for issue in issues}
    assert "DEAD_END" in codes
    assert "MISSING_END" in codes


def test_validate_graph_reports_disconnected_components():
    first = make_element("first")
    second = make_element("second")

    issues = validate_graph("Flowchart", [first, second], [])

    assert any(issue.issue_code == "DISCONNECTED_COMPONENT" for issue in issues)

