from dataclasses import dataclass
from math import hypot
from pathlib import Path

from app.cv.arrow_detector import detect_arrows
from app.cv.element_detector import ExtractedElement


@dataclass(frozen=True)
class BuiltGraphEdge:
    source_key: str
    target_key: str
    edge_type: str
    label: str | None
    confidence: float


def _center(element: ExtractedElement) -> tuple[float, float]:
    return element.x + element.width / 2, element.y + element.height / 2


def _distance_to_box(element: ExtractedElement, x: float, y: float) -> float:
    left = element.x
    right = element.x + element.width
    top = element.y
    bottom = element.y + element.height
    dx = max(left - x, 0, x - right)
    dy = max(top - y, 0, y - bottom)
    return hypot(dx, dy)


def _nearest_element(
    elements: list[ExtractedElement],
    x: float,
    y: float,
    max_distance: float = 34,
) -> ExtractedElement | None:
    if not elements:
        return None
    nearest = min(elements, key=lambda element: _distance_to_box(element, x, y))
    if _distance_to_box(nearest, x, y) <= max_distance:
        return nearest
    return None


def _orient_edge(
    first: ExtractedElement,
    second: ExtractedElement,
    x1: float,
    y1: float,
    x2: float,
    y2: float,
) -> tuple[ExtractedElement, ExtractedElement]:
    first_center = _center(first)
    second_center = _center(second)
    line_vector = (x2 - x1, y2 - y1)
    element_vector = (second_center[0] - first_center[0], second_center[1] - first_center[1])
    dot = line_vector[0] * element_vector[0] + line_vector[1] * element_vector[1]
    if dot >= 0:
        return first, second
    return second, first


def build_graph_edges(
    image_path: str | Path,
    elements: list[ExtractedElement],
) -> list[BuiltGraphEdge]:
    arrows = detect_arrows(image_path)
    graph_edges: list[BuiltGraphEdge] = []
    seen: set[tuple[str, str]] = set()

    for arrow in arrows:
        first = _nearest_element(elements, arrow.x1, arrow.y1)
        second = _nearest_element(elements, arrow.x2, arrow.y2)
        if first is None or second is None or first.element_key == second.element_key:
            continue

        source, target = _orient_edge(first, second, arrow.x1, arrow.y1, arrow.x2, arrow.y2)
        key = (source.element_key, target.element_key)
        if key in seen:
            continue
        seen.add(key)

        graph_edges.append(
            BuiltGraphEdge(
                source_key=source.element_key,
                target_key=target.element_key,
                edge_type="FLOW",
                label=None,
                confidence=arrow.confidence,
            )
        )

    return graph_edges

