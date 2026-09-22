from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np


@dataclass(frozen=True)
class DetectedArrow:
    x1: float
    y1: float
    x2: float
    y2: float
    confidence: float


def detect_arrows(image_path: str | Path) -> list[DetectedArrow]:
    image = cv2.imread(str(image_path), cv2.IMREAD_GRAYSCALE)
    if image is None:
        raise FileNotFoundError(f"Image could not be read: {image_path}")

    edges = cv2.Canny(image, 80, 180)
    lines = cv2.HoughLinesP(edges, 1, np.pi / 180, threshold=35, minLineLength=25, maxLineGap=8)
    if lines is None:
        return []

    arrows: list[DetectedArrow] = []
    for line in lines[:80]:
        x1, y1, x2, y2 = line[0]
        length = float(np.hypot(x2 - x1, y2 - y1))
        confidence = min(0.8, 0.35 + length / 300)
        arrows.append(
            DetectedArrow(
                x1=float(x1),
                y1=float(y1),
                x2=float(x2),
                y2=float(y2),
                confidence=round(confidence, 3),
            )
        )
    return arrows

