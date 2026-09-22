from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageOps


@dataclass(frozen=True)
class PreprocessingResult:
    original_path: str
    processed_path: str
    original_width: int
    original_height: int
    processed_width: int
    processed_height: int


def load_image_with_orientation(image_path: str | Path) -> Image.Image:
    with Image.open(image_path) as image:
        return ImageOps.exif_transpose(image).convert("RGB")


def resize_within_limit(image: np.ndarray, max_dimension: int = 1600) -> np.ndarray:
    height, width = image.shape[:2]
    largest = max(width, height)
    if largest <= max_dimension:
        return image

    scale = max_dimension / largest
    next_size = (max(1, int(width * scale)), max(1, int(height * scale)))
    return cv2.resize(image, next_size, interpolation=cv2.INTER_AREA)


def normalize_for_cv(image: np.ndarray) -> np.ndarray:
    grayscale = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
    denoised = cv2.fastNlMeansDenoising(grayscale, None, h=8, templateWindowSize=7, searchWindowSize=21)
    return cv2.adaptiveThreshold(
        denoised,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        31,
        8,
    )


def preprocess_image(
    image_path: str | Path,
    output_dir: str | Path,
    max_dimension: int = 1600,
) -> PreprocessingResult:
    source = Path(image_path)
    if not source.exists():
        raise FileNotFoundError(f"Image does not exist: {source}")

    pil_image = load_image_with_orientation(source)
    original_width, original_height = pil_image.size
    rgb = np.array(pil_image)
    resized = resize_within_limit(rgb, max_dimension=max_dimension)
    normalized = normalize_for_cv(resized)

    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    processed_path = output / f"{source.stem}_preprocessed.png"
    success = cv2.imwrite(str(processed_path), normalized)
    if not success:
        raise OSError(f"Could not write preprocessed image: {processed_path}")

    processed_height, processed_width = normalized.shape[:2]
    return PreprocessingResult(
        original_path=str(source),
        processed_path=str(processed_path),
        original_width=original_width,
        original_height=original_height,
        processed_width=processed_width,
        processed_height=processed_height,
    )

