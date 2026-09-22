from pathlib import Path

import cv2
import numpy as np

from app.cv.element_detector import extract_elements
from app.graph.graph_builder import build_graph_edges


def test_build_graph_edges_connects_adjacent_shapes(tmp_path: Path):
    image = np.full((180, 320), 255, dtype=np.uint8)
    cv2.rectangle(image, (25, 55), (105, 105), 0, 3)
    cv2.rectangle(image, (190, 55), (270, 105), 0, 3)
    cv2.line(image, (105, 80), (190, 80), 0, 3)
    path = tmp_path / "graph.png"
    cv2.imwrite(str(path), image)

    elements = extract_elements(path)
    edges = build_graph_edges(path, elements)

    assert len(elements) >= 2
    assert len(edges) >= 1
    assert edges[0].source_key != edges[0].target_key

