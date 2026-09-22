from __future__ import annotations

import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parent
MANIFEST = ROOT / "demo_manifest.json"
CANVAS = (1280, 800)
BG = "#f8fafc"
INK = "#0f172a"
MUTED = "#475569"
BLUE = "#4f46e5"
GREEN = "#16a34a"
AMBER = "#d97706"
RED = "#dc2626"


def font(size: int) -> ImageFont.ImageFont:
    try:
        return ImageFont.truetype("arial.ttf", size)
    except OSError:
        return ImageFont.load_default()


def centered_text(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], text: str, fill: str = INK) -> None:
    text_box = draw.multiline_textbbox((0, 0), text, font=font(26), spacing=6, align="center")
    x = box[0] + ((box[2] - box[0]) - (text_box[2] - text_box[0])) / 2
    y = box[1] + ((box[3] - box[1]) - (text_box[3] - text_box[1])) / 2
    draw.multiline_text((x, y), text, font=font(26), fill=fill, spacing=6, align="center")


def arrow(draw: ImageDraw.ImageDraw, start: tuple[int, int], end: tuple[int, int], fill: str = MUTED) -> None:
    draw.line([start, end], fill=fill, width=5)
    x1, y1 = start
    x2, y2 = end
    if abs(x2 - x1) >= abs(y2 - y1):
        direction = 1 if x2 >= x1 else -1
        head = [(x2, y2), (x2 - direction * 18, y2 - 10), (x2 - direction * 18, y2 + 10)]
    else:
        direction = 1 if y2 >= y1 else -1
        head = [(x2, y2), (x2 - 10, y2 - direction * 18), (x2 + 10, y2 - direction * 18)]
    draw.polygon(head, fill=fill)


def rounded_node(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    text: str,
    outline: str = BLUE,
    radius: int = 24,
) -> None:
    draw.rounded_rectangle(box, radius=radius, fill="#ffffff", outline=outline, width=5)
    centered_text(draw, box, text)


def flowchart(path: Path) -> None:
    image = Image.new("RGB", CANVAS, BG)
    draw = ImageDraw.Draw(image)
    draw.text((56, 44), "Demo Flowchart", font=font(34), fill=INK)
    draw.text((56, 90), "Happy path plus review branch", font=font(22), fill=MUTED)

    rounded_node(draw, (90, 250, 290, 350), "Start", GREEN, 50)
    rounded_node(draw, (390, 235, 650, 365), "Validate\nOrder", BLUE, 18)
    draw.polygon([(820, 220), (980, 300), (820, 380), (660, 300)], fill="#ffffff", outline=AMBER)
    draw.line([(820, 220), (980, 300), (820, 380), (660, 300), (820, 220)], fill=AMBER, width=5)
    centered_text(draw, (700, 250, 940, 350), "Approved?")
    rounded_node(draw, (1040, 250, 1210, 350), "Ship", GREEN, 50)
    rounded_node(draw, (690, 520, 950, 650), "Manual\nReview", RED, 18)

    arrow(draw, (290, 300), (390, 300))
    arrow(draw, (650, 300), (660, 300))
    arrow(draw, (980, 300), (1040, 300))
    arrow(draw, (820, 380), (820, 520))
    draw.text((998, 265), "yes", font=font(22), fill=GREEN)
    draw.text((835, 440), "no", font=font(22), fill=RED)
    image.save(path)


def dfd(path: Path) -> None:
    image = Image.new("RGB", CANVAS, BG)
    draw = ImageDraw.Draw(image)
    draw.text((56, 44), "Demo Data Flow Diagram", font=font(34), fill=INK)
    draw.text((56, 90), "User request, processing, storage, and notification flow", font=font(22), fill=MUTED)

    rounded_node(draw, (80, 260, 260, 380), "User", GREEN, 16)
    draw.ellipse((490, 235, 750, 405), fill="#ffffff", outline=BLUE, width=5)
    centered_text(draw, (500, 245, 740, 395), "Process\nRequest")
    draw.rectangle((930, 250, 1170, 390), fill="#ffffff", outline=AMBER, width=5)
    centered_text(draw, (930, 250, 1170, 390), "Orders DB")
    rounded_node(draw, (500, 550, 760, 680), "Email\nService", RED, 16)

    arrow(draw, (260, 320), (490, 320))
    arrow(draw, (750, 320), (930, 320))
    arrow(draw, (625, 405), (625, 550))
    arrow(draw, (930, 355), (750, 365))
    draw.text((322, 282), "order details", font=font(21), fill=MUTED)
    draw.text((790, 282), "write", font=font(21), fill=MUTED)
    draw.text((650, 470), "receipt", font=font(21), fill=MUTED)
    draw.text((800, 375), "status", font=font(21), fill=MUTED)
    image.save(path)


def main() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    expected_files = {entry["path"] for entry in manifest["files"]}
    generators = {
        "demo-flowchart.png": flowchart,
        "demo-dfd.png": dfd,
    }

    if expected_files != set(generators):
        raise SystemExit("Manifest and generator outputs are out of sync.")

    for filename, generator in generators.items():
        generator(ROOT / filename)
        print(f"Wrote {filename}")


if __name__ == "__main__":
    main()
