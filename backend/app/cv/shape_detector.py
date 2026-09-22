from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np


@dataclass(frozen=True)
class DetectedShape:
    element_key: str
    element_type: str
    x: float
    y: float
    width: float
    height: float
    confidence: float


def _classify_shape(approx_vertices: int, width: int, height: int, area: float) -> tuple[str, float]:
    ratio = width / max(height, 1)
    extent = area / max(width * height, 1)

    if approx_vertices == 4:
        if extent < 0.65:
            return "DECISION", 0.76
        if ratio >= 1.25:
            return "PROCESS", 0.82
        return "DATA", 0.62

    if approx_vertices >= 7:
        if 0.75 <= ratio <= 1.25:
            return "PROCESS_DFD", 0.72
        return "START", 0.62

    return "UNKNOWN", 0.45


def detect_shapes(image_path: str | Path) -> list[DetectedShape]:
    image = cv2.imread(str(image_path), cv2.IMREAD_GRAYSCALE)
    if image is None:
        raise FileNotFoundError(f"Image could not be read: {image_path}")

    _, threshold = cv2.threshold(image, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    kernel = np.ones((3, 3), np.uint8)
    threshold = cv2.morphologyEx(threshold, cv2.MORPH_CLOSE, kernel, iterations=1)
    contours, _ = cv2.findContours(threshold, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)

    image_area = image.shape[0] * image.shape[1]
    detected: list[DetectedShape] = []

    for contour in contours:
        area = cv2.contourArea(contour)
        if area < max(120, image_area * 0.0008):
            continue

        x, y, width, height = cv2.boundingRect(contour)
        if width < 18 or height < 18:
            continue

        perimeter = cv2.arcLength(contour, True)
        approx = cv2.approxPolyDP(contour, 0.04 * perimeter, True)
        if len(approx) < 4:
            continue
        element_type, confidence = _classify_shape(len(approx), width, height, area)

        detected.append(
            DetectedShape(
                element_key=f"node_{len(detected) + 1}",
                element_type=element_type,
                x=float(x),
                y=float(y),
                width=float(width),
                height=float(height),
                confidence=confidence,
            )
        )

    return sorted(_remove_container_shapes(detected), key=lambda item: (item.y, item.x))


def _contains_center(container: DetectedShape, child: DetectedShape) -> bool:
    center_x = child.x + child.width / 2
    center_y = child.y + child.height / 2
    return (
        container.x <= center_x <= container.x + container.width
        and container.y <= center_y <= container.y + container.height
    )


def _remove_container_shapes(shapes: list[DetectedShape]) -> list[DetectedShape]:
    filtered: list[DetectedShape] = []
    for shape in shapes:
        shape_area = shape.width * shape.height
        contained = [
            other
            for other in shapes
            if other is not shape
            and _contains_center(shape, other)
            and shape_area > (other.width * other.height * 1.8)
        ]
        if len(contained) >= 2:
            continue
        filtered.append(shape)
    return filtered
