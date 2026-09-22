from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class DetectedText:
    text: str
    x: float
    y: float
    width: float
    height: float
    confidence: float


def detect_text(_image_path: str | Path) -> list[DetectedText]:
    return []

