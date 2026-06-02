# -*- coding: utf-8 -*-
"""Create slide-friendly cropped copies of source thesis figures."""

from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[2]
PROJECT_FIGS = ROOT / "gaokaollm_bench" / "outputs" / "thesis_figures"
OUT = Path(__file__).resolve().parent / "generated_assets"


FIGURES = [
    "fig_5_1_mas_workflow",
    "fig_3_1_v1_hybrid_rag_flow",
    "fig_5_3_ucb_dispatch",
    "fig_5_2_runtime_state_machine",
    "fig_4_2_benchmark_flow",
]


FONT_REGULAR = Path(r"C:\Windows\Fonts\msyh.ttc")
FONT_BOLD = Path(r"C:\Windows\Fonts\msyhbd.ttc")


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    path = FONT_BOLD if bold and FONT_BOLD.exists() else FONT_REGULAR
    if path.exists():
        return ImageFont.truetype(str(path), size)
    return ImageFont.load_default()


def trim_white_margin(src: Path, dst: Path, padding: int = 24) -> None:
    image = Image.open(src).convert("RGB")
    bg = Image.new("RGB", image.size, (255, 255, 255))
    diff = ImageChops.difference(image, bg).convert("L")
    bbox = diff.point(lambda p: 255 if p > 10 else 0).getbbox()
    if not bbox:
        image.save(dst)
        return
    left, top, right, bottom = bbox
    left = max(left - padding, 0)
    top = max(top - padding, 0)
    right = min(right + padding, image.width)
    bottom = min(bottom + padding, image.height)
    image.crop((left, top, right, bottom)).save(dst)


def text_center(
    draw: ImageDraw.ImageDraw, box, text: str, fill, size: int, bold: bool = False
) -> None:
    lines = text.split("\n")
    fnt = font(size, bold)

    def measure(line: str):
        if hasattr(draw, "textbbox"):
            bbox = draw.textbbox((0, 0), line, font=fnt)
            return bbox[2] - bbox[0], bbox[3] - bbox[1]
        return draw.textsize(line, font=fnt)

    sizes = [measure(line) for line in lines]
    heights = [item[1] for item in sizes]
    total_h = sum(heights) + (len(lines) - 1) * 8
    y = box[1] + (box[3] - box[1] - total_h) / 2
    for line, (w, h) in zip(lines, sizes):
        x = box[0] + (box[2] - box[0] - w) / 2
        draw.text((x, y), line, font=fnt, fill=fill)
        y += h + 8


def rounded(draw, box, outline, fill=(255, 255, 255), width=3, radius=18):
    if hasattr(draw, "rounded_rectangle"):
        draw.rounded_rectangle(
            box, radius=radius, fill=fill, outline=outline, width=width
        )
    else:
        draw.rectangle(box, fill=fill, outline=outline)
        for offset in range(1, width):
            draw.rectangle(
                (box[0] + offset, box[1] + offset, box[2] - offset, box[3] - offset),
                outline=outline,
            )


def draw_curve_panel(draw, box, title, curve_points, penalty_x=None):
    rounded(draw, box, (205, 216, 224), (255, 255, 255), 2, 16)
    text_center(
        draw, (box[0], box[1] + 8, box[2], box[1] + 54), title, (38, 50, 56), 24, True
    )
    x0, y0, x1, y1 = box[0] + 36, box[1] + 90, box[2] - 34, box[3] - 38
    draw.line((x0, y1, x1, y1), fill=(120, 135, 150), width=2)
    draw.line((x0, y0, x0, y1), fill=(120, 135, 150), width=2)
    if penalty_x is not None:
        px = x0 + int((x1 - x0) * penalty_x)
        draw.rectangle((px, y0, x1, y1), fill=(255, 240, 214))
        draw.line((px, y0, px, y1), fill=(230, 159, 0), width=3)
    pts = [(x0 + int((x1 - x0) * x), y1 - int((y1 - y0) * y)) for x, y in curve_points]
    draw.line(pts, fill=(0, 114, 178), width=5)


def generate_savf_mechanism(dst: Path) -> None:
    img = Image.new("RGB", (1500, 820), (250, 250, 250))
    draw = ImageDraw.Draw(img)
    ink = (38, 50, 56)
    blue = (0, 114, 178)
    orange = (230, 159, 0)
    green = (0, 158, 115)
    line = (207, 216, 220)

    rounded(draw, (60, 70, 430, 300), orange, (255, 248, 240), 4, 24)
    text_center(draw, (80, 88, 410, 150), "线性加权陷阱", ink, 30, True)
    text_center(
        draw, (90, 158, 400, 250), "学校层次高分\n可能抵消严重违约", ink, 28, True
    )

    rounded(draw, (535, 70, 1440, 300), green, (241, 250, 246), 4, 24)
    text_center(draw, (555, 88, 1420, 150), "SAVF 底线保护", ink, 30, True)
    text_center(
        draw,
        (570, 158, 1405, 250),
        "预算、专业、地域分别映射为单属性价值\n严重违约先被压低，再进入综合排序",
        ink,
        27,
        True,
    )

    draw.line((445, 185, 515, 185), fill=line, width=8)
    draw.polygon([(515, 185), (490, 168), (490, 202)], fill=line)

    draw_curve_panel(
        draw,
        (80, 380, 440, 680),
        "预算阈值",
        [(0, 0.9), (0.55, 0.9), (0.75, 0.35), (1, 0.05)],
        0.62,
    )
    draw_curve_panel(
        draw,
        (570, 380, 930, 680),
        "专业匹配",
        [(0, 0.08), (0.35, 0.45), (0.7, 0.82), (1, 0.95)],
        0.0,
    )
    draw_curve_panel(
        draw,
        (1060, 380, 1420, 680),
        "地域偏好",
        [(0, 0.9), (0.38, 0.78), (0.72, 0.52), (1, 0.36)],
        0.75,
    )

    for x in (460, 950):
        draw.line((x, 530, x + 80, 530), fill=line, width=8)
        draw.polygon([(x + 80, 530), (x + 55, 513), (x + 55, 547)], fill=line)

    rounded(draw, (330, 710, 1170, 775), blue, (255, 255, 255), 3, 20)
    text_center(
        draw,
        (350, 715, 1150, 770),
        "attribute value -> penalty -> protected score",
        ink,
        28,
        True,
    )
    img.save(dst)


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    for name in FIGURES:
        src = PROJECT_FIGS / f"{name}.png"
        if src.exists():
            trim_white_margin(src, OUT / f"crop_{name}.png")
            print("cropped", src.name)
    generate_savf_mechanism(OUT / "savf_mechanism_ppt.png")
    print("generated savf_mechanism_ppt.png")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
