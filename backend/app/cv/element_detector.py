from dataclasses import dataclass
from pathlib import Path

from app.cv.shape_detector import DetectedShape, detect_shapes
from app.cv.text_detector import detect_text


@dataclass(frozen=True)
class ExtractedElement:
    element_key: str
    element_type: str
    label: str | None
    x: float
    y: float
    width: float
    height: float
    confidence: float
    ocr_text: str | None


def _contains(shape: DetectedShape, x: float, y: float, width: float, height: float) -> bool:
    return (
        x >= shape.x
        and y >= shape.y
        and x + width <= shape.x + shape.width
        and y + height <= shape.y + shape.height
    )


def extract_elements(image_path: str | Path) -> list[ExtractedElement]:
    shapes = detect_shapes(image_path)
    texts = detect_text(image_path)
    elements: list[ExtractedElement] = []

    for index, shape in enumerate(shapes, start=1):
        text_candidates = [
            text
            for text in texts
            if _contains(shape, text.x, text.y, text.width, text.height)
        ]
        label = " ".join(candidate.text for candidate in text_candidates).strip() or None
        confidence = shape.confidence
        if text_candidates:
            confidence = round((shape.confidence + max(item.confidence for item in text_candidates)) / 2, 3)

        elements.append(
            ExtractedElement(
                element_key=f"node_{index}",
                element_type=shape.element_type,
                label=label,
                x=shape.x,
                y=shape.y,
                width=shape.width,
                height=shape.height,
                confidence=confidence,
                ocr_text=label,
            )
        )

    return elements

