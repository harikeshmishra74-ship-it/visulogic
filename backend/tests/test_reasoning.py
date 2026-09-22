import json

from app.ai.reasoning import explain_issue
from app.graph.validator import ValidationFinding
from app.models import DiagramElement


def test_explain_dead_end_uses_detected_element_evidence():
    element = DiagramElement(
        element_key="node_2",
        element_type="PROCESS",
        label="Payment Verification",
        x=10,
        y=20,
        width=80,
        height=40,
    )
    issue = ValidationFinding(
        issue_code="DEAD_END",
        severity="WARNING",
        title="Dead-end element",
        description="This element has no outgoing connection.",
        element_key="node_2",
        edge_key=None,
        evidence_json=json.dumps({"element_key": "node_2", "element_type": "PROCESS", "out_degree": 0}),
        fix_suggestion="Connect this element to the next valid step.",
    )

    explanation = explain_issue(issue, {"node_2": element})

    assert explanation.what == "Dead-end element"
    assert explanation.where == "Payment Verification (node_2)"
    assert "out-degree of 0" in explanation.why
    assert explanation.fix == "Connect this element to the next valid step."

