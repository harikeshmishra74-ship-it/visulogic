from pathlib import Path

from PIL import Image

from app.preprocessing.image_cleaner import preprocess_image


def test_preprocess_image_preserves_original_and_writes_processed(tmp_path: Path):
    source = tmp_path / "diagram.png"
    Image.new("RGB", (80, 40), color="white").save(source)

    result = preprocess_image(source, tmp_path / "processed", max_dimension=64)

    assert Path(result.original_path) == source
    assert Path(result.processed_path).exists()
    assert result.original_width == 80
    assert result.original_height == 40
    assert result.processed_width == 64
    assert result.processed_height == 32

