# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from pathlib import Path
from xml.sax.saxutils import escape

from PIL import Image, ImageDraw, ImageFont


OUT = Path(__file__).resolve().parent / "generated_assets"
OUT.mkdir(parents=True, exist_ok=True)

W, H = 1600, 1200

COLORS = {
    "bg": "#FAFAFA",
    "ink": "#263238",
    "muted": "#607D8B",
    "line": "#CFD8DC",
    "blue": "#0072B2",
    "orange": "#E69F00",
    "green": "#009E73",
    "grey": "#90A4AE",
    "white": "#FFFFFF",
    "pale_blue": "#EEF6FC",
    "pale_orange": "#FFF7E6",
    "pale_green": "#EEF9F5",
}


def font(size, bold=False):
    candidates = [
        r"C:\Windows\Fonts\arialbd.ttf" if bold else r"C:\Windows\Fonts\arial.ttf",
        r"C:\Windows\Fonts\msyhbd.ttc" if bold else r"C:\Windows\Fonts\msyh.ttc",
    ]
    for path in candidates:
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def rgb(hex_color):
    hex_color = hex_color.lstrip("#")
    return tuple(int(hex_color[i : i + 2], 16) for i in (0, 2, 4))


def draw_center(draw, xy, text, size=24, fill=None, bold=False):
    fill = fill or COLORS["ink"]
    f = font(size, bold=bold)
    x1, y1, x2, y2 = xy
    lines = text.split("\n")
    sizes = [draw.textsize(line, font=f) for line in lines]
    line_h = max((s[1] for s in sizes), default=size)
    spacing = 4
    th = line_h * len(lines) + spacing * max(0, len(lines) - 1)
    start_y = y1 + (y2 - y1 - th) / 2
    for idx, line in enumerate(lines):
        lw, lh = draw.textsize(line, font=f)
        draw.text(
            (x1 + (x2 - x1 - lw) / 2, start_y + idx * (line_h + spacing)),
            line,
            font=f,
            fill=rgb(fill),
        )


def box(draw, xy, text, stroke, fill="#FFFFFF", size=22, bold=False, radius=18):
    try:
        draw.rounded_rectangle(
            xy, radius=radius, fill=rgb(fill), outline=rgb(stroke), width=3
        )
    except AttributeError:
        draw.rectangle(xy, fill=rgb(fill), outline=rgb(stroke))
        x1, y1, x2, y2 = xy
        for inset in (1, 2):
            draw.rectangle(
                (x1 + inset, y1 + inset, x2 - inset, y2 - inset), outline=rgb(stroke)
            )
    draw_center(draw, xy, text, size=size, bold=bold)


def arrow(draw, start, end, color=None, width=4):
    color = rgb(color or COLORS["line"])
    draw.line([start, end], fill=color, width=width)
    x1, y1 = start
    x2, y2 = end
    if x2 >= x1:
        pts = [(x2, y2), (x2 - 18, y2 - 10), (x2 - 18, y2 + 10)]
    else:
        pts = [(x2, y2), (x2 + 18, y2 - 10), (x2 + 18, y2 + 10)]
    draw.polygon(pts, fill=color)


def rect_outline(draw, xy, outline, fill=None, thick=1):
    if fill is not None:
        draw.rectangle(xy, fill=rgb(fill), outline=rgb(outline))
    else:
        draw.rectangle(xy, outline=rgb(outline))
    x1, y1, x2, y2 = xy
    for inset in range(1, max(1, thick)):
        draw.rectangle(
            (x1 + inset, y1 + inset, x2 - inset, y2 - inset), outline=rgb(outline)
        )


def draw_curve(draw, x, y, w, h, color, drop=False):
    rect_outline(draw, [x, y, x + w, y + h], COLORS["line"], thick=2)
    pts = []
    for i in range(0, w + 1, 8):
        t = i / float(w)
        if drop:
            val = 0.85 if t < 0.62 else max(0.12, 0.85 - (t - 0.62) * 2.1)
        else:
            val = 0.18 + 0.68 * (1 - (t - 0.5) ** 2 * 1.6)
        pts.append((x + i, y + h - int(val * h)))
    draw.line(pts, fill=rgb(color), width=4)


def save_vai_png():
    img = Image.new("RGB", (W, H), rgb(COLORS["bg"]))
    d = ImageDraw.Draw(img)
    draw_center(
        d,
        (60, 35, 1540, 95),
        "Algorithm Macro Flow with Mechanism Microscopes",
        34,
        COLORS["ink"],
        True,
    )
    draw_center(
        d,
        (60, 93, 1540, 132),
        "Explanatory source-derived visual, not experimental evidence",
        18,
        COLORS["muted"],
    )

    labels = [
        ("USER\nREQUEST", COLORS["grey"]),
        ("EVIDENCE\nCANDIDATES", COLORS["blue"]),
        ("SAVF\nPROTECT", COLORS["orange"]),
        ("UCB\nPROBE AXIS", COLORS["green"]),
        ("PARETO A/B\nTRADEOFF", COLORS["orange"]),
        ("BT POSTERIOR\nSTATE", COLORS["blue"]),
        ("RECOMMENDATION\nEXPLANATION", COLORS["green"]),
    ]
    x0, y0, bw, bh, gap = 65, 510, 190, 94, 28
    centers = []
    for i, (label, color) in enumerate(labels):
        x = x0 + i * (bw + gap)
        box(d, (x, y0, x + bw, y0 + bh), label, color, COLORS["white"], 20, True)
        centers.append((x + bw / 2, y0 + bh / 2))
        if i:
            arrow(
                d, (x - gap + 6, y0 + bh / 2), (x - 10, y0 + bh / 2), COLORS["line"], 4
            )

    # Input and evidence thumbnails
    box(
        d,
        (95, 665, 285, 765),
        "region\nbudget\nmajor fit\nrisk",
        COLORS["line"],
        COLORS["white"],
        18,
    )
    for i, c in enumerate(
        [COLORS["blue"], COLORS["orange"], COLORS["green"], COLORS["grey"]]
    ):
        d.rectangle([350, 675 + i * 22, 470 + i * 12, 690 + i * 22], fill=rgb(c))
    for row in range(2):
        for col in range(4):
            x, y = 535 + col * 78, 666 + row * 55
            box(
                d,
                (x, y, x + 58, y + 40),
                "C{}".format(row * 4 + col + 1),
                COLORS["line"],
                "#FFFFFF",
                14,
                True,
                10,
            )

    # SAVF microscope
    box(d, (70, 170, 505, 430), "", COLORS["orange"], COLORS["pale_orange"], 22, True)
    draw_center(
        d, (95, 190, 480, 222), "SAVF: bottom-line protection", 21, COLORS["ink"], True
    )
    draw_curve(d, 105, 235, 110, 70, COLORS["blue"], drop=True)
    draw_curve(d, 235, 235, 110, 70, COLORS["orange"], drop=True)
    draw_curve(d, 365, 235, 110, 70, COLORS["green"], drop=False)
    draw_center(
        d,
        (105, 325, 475, 372),
        "attribute value -> penalty -> protected score",
        16,
        COLORS["ink"],
    )
    box(d, (142, 380, 228, 415), "safe", COLORS["green"], COLORS["white"], 14)
    box(d, (246, 380, 332, 415), "warn", COLORS["orange"], COLORS["white"], 14)
    box(d, (350, 380, 436, 415), "suppress", COLORS["grey"], "#ECEFF1", 14)

    # UCB microscope
    box(d, (585, 170, 1015, 430), "", COLORS["green"], COLORS["pale_green"], 22, True)
    draw_center(
        d, (610, 190, 990, 222), "UCB: choose what to ask next", 21, COLORS["ink"], True
    )
    axes = ["region", "major", "tuition", "risk"]
    vals = [(58, 55), (74, 82), (43, 64), (62, 38)]
    for i, name in enumerate(axes):
        x = 635 + i * 90
        d.rectangle([x, 330 - vals[i][0], x + 26, 330], fill=rgb(COLORS["blue"]))
        d.rectangle([x + 30, 330 - vals[i][1], x + 56, 330], fill=rgb(COLORS["green"]))
        draw_center(d, (x - 8, 340, x + 70, 370), name, 13, COLORS["ink"])
    rect_outline(d, [708, 225, 795, 345], COLORS["green"], thick=4)
    draw_center(
        d, (665, 374, 925, 407), "benefit signal + uncertainty", 16, COLORS["ink"]
    )

    # BT microscope
    box(d, (1095, 170, 1530, 430), "", COLORS["blue"], COLORS["pale_blue"], 22, True)
    draw_center(
        d,
        (1120, 190, 1505, 222),
        "BT posterior preference state",
        21,
        COLORS["ink"],
        True,
    )
    prefs = [
        ("region", 0.62, COLORS["blue"]),
        ("major", 0.82, COLORS["green"]),
        ("tuition", 0.48, COLORS["orange"]),
        ("risk", 0.58, COLORS["grey"]),
    ]
    for i, (name, val, color) in enumerate(prefs):
        y = 230 + i * 42
        draw_center(d, (1130, y - 8, 1210, y + 18), name, 14, COLORS["ink"])
        rect_outline(d, [1225, y, 1460, y + 16], COLORS["line"], thick=2)
        d.rectangle([1225, y, 1225 + int(235 * val), y + 16], fill=rgb(color))
        d.line(
            [1225 + int(235 * val), y - 8, 1225 + int(235 * val), y + 24],
            fill=rgb(COLORS["ink"]),
            width=2,
        )
    draw_center(
        d,
        (1160, 383, 1488, 410),
        "influences next axis, scoring, explanation",
        14,
        COLORS["muted"],
    )

    # Tradeoff detail and feedback
    box(
        d,
        (715, 680, 895, 790),
        "A\nsafer risk\nlower tuition",
        COLORS["blue"],
        COLORS["white"],
        18,
        True,
    )
    box(
        d,
        (925, 680, 1105, 790),
        "B\nbetter major fit\nrelax budget",
        COLORS["orange"],
        COLORS["white"],
        18,
        True,
    )
    box(
        d,
        (745, 825, 1075, 880),
        "prefer A | prefer B | uncertain",
        COLORS["line"],
        COLORS["white"],
        18,
    )
    arrow(d, (910, 884), (1210, 884), COLORS["line"], 4)
    box(
        d,
        (1230, 835, 1510, 935),
        "final report\nsafe / balanced / aspirational",
        COLORS["green"],
        COLORS["pale_green"],
        18,
        True,
    )
    arrow(d, (1345, 835), (1345, 615), COLORS["line"], 4)

    # Feedback loop
    d.arc([790, 590, 1325, 1080], 20, 155, fill=rgb(COLORS["grey"]))
    draw_center(d, (860, 990, 1250, 1025), "next round state", 16, COLORS["muted"])

    # Legend
    legend = [
        ("blue", "evidence-grounded scoring", COLORS["blue"]),
        ("orange", "bottom-line penalty", COLORS["orange"]),
        ("green", "selected probe / updated preference", COLORS["green"]),
    ]
    for i, (_, text, color) in enumerate(legend):
        x, y = 72, 1040 + i * 38
        d.rectangle([x, y, x + 32, y + 20], fill=rgb(color))
        d.text((x + 44, y - 1), text, font=font(17), fill=rgb(COLORS["muted"]))

    img.save(str(OUT / "v_ai01_algorithm_flow.png"))


def save_arch_png():
    img = Image.new("RGB", (W, H), rgb(COLORS["bg"]))
    d = ImageDraw.Draw(img)
    draw_center(
        d,
        (70, 40, 1530, 98),
        "Source-Derived Horizontal System Architecture",
        34,
        COLORS["ink"],
        True,
    )
    draw_center(
        d,
        (70, 102, 1530, 140),
        "PPT redraw from thesis architecture semantics; original vertical figure remains unchanged",
        18,
        COLORS["muted"],
    )
    blocks = [
        (
            "DATA / EVIDENCE",
            "PostgreSQL\nmajor tree\ntuition / region\nquality profile",
            COLORS["blue"],
            120,
        ),
        (
            "AGENT SERVICE",
            "semantic normalizer\nconstraint parser\nprobe planner\nexpression organizer",
            COLORS["green"],
            460,
        ),
        ("DECISION LOOP", "SAVF\nUCB\nPareto A/B\nBT posterior", COLORS["orange"], 800),
        (
            "UI + BENCHMARK",
            "elicitation console\nfinal report\ncontrolled profiles\nevaluator",
            "#1A3A5C",
            1140,
        ),
    ]
    for i, (head, body, color, x) in enumerate(blocks):
        box(d, (x, 230, x + 285, 395), head, color, COLORS["white"], 22, True)
        box(d, (x, 430, x + 285, 690), body, COLORS["line"], "#FFFFFF", 20)
        if i < len(blocks) - 1:
            arrow(d, (x + 300, 505), (x + 330, 505), COLORS["line"], 5)
    box(
        d,
        (145, 785, 615, 900),
        "Fact boundary:\nLLM does not generate candidates",
        COLORS["orange"],
        COLORS["pale_orange"],
        20,
        True,
    )
    box(
        d,
        (805, 785, 1285, 900),
        "Reviewable process:\nquestion -> feedback -> state update",
        COLORS["green"],
        COLORS["pale_green"],
        20,
        True,
    )
    d.arc([260, 700, 1380, 1090], 15, 165, fill=rgb(COLORS["grey"]))
    draw_center(
        d,
        (570, 1010, 1060, 1050),
        "Benchmark checks mechanism, not single-turn fluency",
        22,
        COLORS["muted"],
    )
    img.save(str(OUT / "architecture_wide.png"))


def save_svg_simple(path, title, kind):
    if kind == "vai":
        body = """
<rect x="60" y="160" width="1480" height="170" rx="18" fill="#ffffff" stroke="#CFD8DC" stroke-width="3"/>
<text x="800" y="210" text-anchor="middle" font-size="32" font-weight="700">USER REQUEST -> EVIDENCE -> SAVF -> UCB -> PARETO A/B -> BT POSTERIOR -> EXPLANATION</text>
<text x="800" y="270" text-anchor="middle" font-size="22">Explanatory source-derived visual, not experimental evidence</text>
<rect x="90" y="420" width="420" height="260" rx="18" fill="#FFF7E6" stroke="#E69F00" stroke-width="4"/>
<text x="300" y="475" text-anchor="middle" font-size="28" font-weight="700">SAVF microscope</text>
<text x="300" y="540" text-anchor="middle" font-size="22">value curves + threshold penalty</text>
<text x="300" y="590" text-anchor="middle" font-size="22">protected score suppresses violations</text>
<rect x="590" y="420" width="420" height="260" rx="18" fill="#EEF9F5" stroke="#009E73" stroke-width="4"/>
<text x="800" y="475" text-anchor="middle" font-size="28" font-weight="700">UCB microscope</text>
<text x="800" y="540" text-anchor="middle" font-size="22">benefit signal + uncertainty</text>
<text x="800" y="590" text-anchor="middle" font-size="22">select next question axis</text>
<rect x="1090" y="420" width="420" height="260" rx="18" fill="#EEF6FC" stroke="#0072B2" stroke-width="4"/>
<text x="1300" y="475" text-anchor="middle" font-size="28" font-weight="700">BT posterior state</text>
<text x="1300" y="540" text-anchor="middle" font-size="22">preference bars + uncertainty</text>
<text x="1300" y="590" text-anchor="middle" font-size="22">influences next axis / score / explanation</text>
<rect x="300" y="790" width="1000" height="140" rx="18" fill="#ffffff" stroke="#CFD8DC" stroke-width="3"/>
<text x="800" y="845" text-anchor="middle" font-size="26" font-weight="700">No real school names, scores, product UI, or experimental numbers</text>
<text x="800" y="892" text-anchor="middle" font-size="22">No SQL/query/filter overclaim</text>
"""
    else:
        body = """
<rect x="100" y="230" width="300" height="420" rx="18" fill="#ffffff" stroke="#0072B2" stroke-width="4"/>
<text x="250" y="290" text-anchor="middle" font-size="28" font-weight="700">DATA</text>
<text x="250" y="360" text-anchor="middle" font-size="22">PostgreSQL</text>
<text x="250" y="405" text-anchor="middle" font-size="22">major tree</text>
<text x="250" y="450" text-anchor="middle" font-size="22">region tree</text>
<rect x="470" y="230" width="300" height="420" rx="18" fill="#ffffff" stroke="#009E73" stroke-width="4"/>
<text x="620" y="290" text-anchor="middle" font-size="28" font-weight="700">AGENT</text>
<text x="620" y="360" text-anchor="middle" font-size="22">normalize</text>
<text x="620" y="405" text-anchor="middle" font-size="22">plan probe</text>
<text x="620" y="450" text-anchor="middle" font-size="22">organize expression</text>
<rect x="840" y="230" width="300" height="420" rx="18" fill="#ffffff" stroke="#E69F00" stroke-width="4"/>
<text x="990" y="290" text-anchor="middle" font-size="28" font-weight="700">DECISION</text>
<text x="990" y="360" text-anchor="middle" font-size="22">SAVF / UCB</text>
<text x="990" y="405" text-anchor="middle" font-size="22">Pareto A/B</text>
<text x="990" y="450" text-anchor="middle" font-size="22">BT posterior</text>
<rect x="1210" y="230" width="300" height="420" rx="18" fill="#ffffff" stroke="#1A3A5C" stroke-width="4"/>
<text x="1360" y="290" text-anchor="middle" font-size="28" font-weight="700">UI + BENCHMARK</text>
<text x="1360" y="360" text-anchor="middle" font-size="22">elicitation console</text>
<text x="1360" y="405" text-anchor="middle" font-size="22">final report</text>
<text x="1360" y="450" text-anchor="middle" font-size="22">controlled profiles</text>
<rect x="260" y="790" width="1080" height="135" rx="18" fill="#FFF7E6" stroke="#E69F00" stroke-width="4"/>
<text x="800" y="850" text-anchor="middle" font-size="28" font-weight="700">Fact boundary: LLM organizes language; evidence layer returns candidates</text>
<text x="800" y="895" text-anchor="middle" font-size="22">Benchmark checks the multi-round mechanism</text>
"""
    svg = """<svg xmlns="http://www.w3.org/2000/svg" width="1600" height="1200" viewBox="0 0 1600 1200">
<rect width="1600" height="1200" fill="#FAFAFA"/>
<text x="800" y="80" text-anchor="middle" font-family="Arial, sans-serif" font-size="40" font-weight="700" fill="#263238">{title}</text>
{body}
</svg>""".format(title=escape(title), body=body)
    (OUT / path).write_text(svg, encoding="utf-8")


def main():
    save_vai_png()
    save_arch_png()
    save_svg_simple(
        "v_ai01_algorithm_flow.svg",
        "Algorithm Macro Flow with Mechanism Microscopes",
        "vai",
    )
    save_svg_simple(
        "architecture_wide.svg", "Source-Derived Horizontal System Architecture", "arch"
    )
    readme = """# Generated local PPT figures v0

These figures are local fallback assets generated without external APIs.

- `v_ai01_algorithm_flow.png` / `.svg`: source-derived explanatory algorithm visual for B16 and optional Slide 9 after render QA.
- `architecture_wide.png` / `.svg`: source-derived horizontal architecture visual for B15 and optional Slide 5 after render QA.

They do not contain real school names, scores, product UI, or experimental numbers.
"""
    (OUT / "README.md").write_text(readme, encoding="utf-8")
    for name in [
        "v_ai01_algorithm_flow.png",
        "v_ai01_algorithm_flow.svg",
        "architecture_wide.png",
        "architecture_wide.svg",
    ]:
        print(OUT / name)


if __name__ == "__main__":
    main()
