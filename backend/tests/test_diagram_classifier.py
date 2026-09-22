from pathlib import Path

import cv2
import numpy as np

from app.classification.diagram_classifier import classify_diagram


def test_classify_flowchart_like_diagram(tmp_path: Path):
    image = np.full((240, 360), 255, dtype=np.uint8)
    cv2.rectangle(image, (25, 40), (115, 90), 0, 2)
    cv2.rectangle(image, (155, 40), (245, 90), 0, 2)
    diamond = np.array([[300, 35], [340, 65], [300, 95], [260, 65]])
    cv2.polylines(image, [diamond], isClosed=True, color=0, thickness=2)
    cv2.line(image, (115, 65), (155, 65), 0, 2)
    cv2.line(image, (245, 65), (260, 65), 0, 2)
    path = tmp_path / "flowchart.png"
    cv2.imwrite(str(path), image)

    result = classify_diagram(path)

    assert result.diagram_type == "Flowchart"
    assert result.confidence >= 0.6


def test_classify_blank_diagram_as_unknown(tmp_path: Path):
    path = tmp_path / "blank.png"
    cv2.imwrite(str(path), np.full((80, 80), 255, dtype=np.uint8))

    result = classify_diagram(path)

    assert result.diagram_type == "Unknown"
    assert result.confidence < 0.6

