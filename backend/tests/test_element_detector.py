from pathlib import Path

import cv2
import numpy as np

from app.cv.element_detector import extract_elements


def test_extract_elements_returns_bounding_boxes(tmp_path: Path):
    image = np.full((220, 340), 255, dtype=np.uint8)
    cv2.rectangle(image, (25, 40), (125, 95), 0, 3)
    cv2.rectangle(image, (180, 40), (285, 95), 0, 3)
    path = tmp_path / "elements.png"
    cv2.imwrite(str(path), image)

    elements = extract_elements(path)

    assert len(elements) >= 2
    assert all(element.width > 0 and element.height > 0 for element in elements)
    assert all(element.element_key.startswith("node_") for element in elements)

