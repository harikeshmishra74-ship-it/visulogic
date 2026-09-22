from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np


@dataclass(frozen=True)
class DiagramClassification:
    diagram_type: str
    confidence: float
    evidence: dict[str, int]


def classify_diagram(image_path: str | Path) -> DiagramClassification:
    image = cv2.imread(str(image_path), cv2.IMREAD_GRAYSCALE)
    if image is None:
        raise FileNotFoundError(f"Image could not be read: {image_path}")

    threshold = cv2.adaptiveThreshold(
        image,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY_INV,
        31,
        8,
    )
    contours, _ = cv2.findContours(threshold, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    rectangles = 0
    diamonds = 0
    circles = 0
    large_shapes = 0
    image_area = image.shape[0] * image.shape[1]

    for contour in contours:
        area = cv2.contourArea(contour)
        if area < max(80, image_area * 0.0005):
            continue

        large_shapes += 1
        perimeter = cv2.arcLength(contour, True)
        approx = cv2.approxPolyDP(contour, 0.04 * perimeter, True)

        if len(approx) == 4:
            x, y, width, height = cv2.boundingRect(approx)
            ratio = width / max(height, 1)
            rect_area = width * height
            fill_ratio = area / max(rect_area, 1)
            if 0.75 <= fill_ratio <= 1.05 and (ratio > 1.25 or ratio < 0.8):
                rectangles += 1
            else:
                diamonds += 1
        elif len(approx) >= 7:
            circles += 1

    edges = cv2.Canny(image, 80, 180)
    lines = cv2.HoughLinesP(edges, 1, np.pi / 180, threshold=30, minLineLength=25, maxLineGap=8)
    line_count = 0 if lines is None else len(lines)

    evidence = {
        "large_shapes": large_shapes,
        "rectangles": rectangles,
        "diamonds": diamonds,
        "circles": circles,
        "lines": line_count,
    }

    if large_shapes < 2 and line_count < 2:
        return DiagramClassification("Unknown", 0.25, evidence)

    flowchart_score = rectangles * 0.18 + diamonds * 0.28 + min(line_count, 8) * 0.04
    dfd_score = circles * 0.28 + rectangles * 0.08 + min(line_count, 8) * 0.04

    if flowchart_score >= dfd_score and flowchart_score >= 0.3:
        confidence = min(0.92, 0.45 + flowchart_score)
        return DiagramClassification("Flowchart", round(confidence, 3), evidence)

    if dfd_score >= 0.3:
        confidence = min(0.88, 0.42 + dfd_score)
        return DiagramClassification("DFD", round(confidence, 3), evidence)

    return DiagramClassification("Unknown", 0.35, evidence)

