"""Render polished thesis diagrams as hand-authored SVG/PNG assets.

The previous Graphviz/Diagrams layout was reproducible but too wide and
engineering-like for the thesis. This generator keeps everything local and
deterministic: it writes curated SVG layouts and uses a local headless browser
only to rasterize PNG copies. It does not read benchmark hidden fields, connect
to PostgreSQL, call an LLM, or rerun any experiment.
"""

from __future__ import annotations

import argparse
import html
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_OUTPUT_DIR = REPO_ROOT / "gaokaollm_bench" / "outputs" / "thesis_figures"

FONT = "Microsoft YaHei, Noto Sans CJK SC, SimHei, Arial, sans-serif"

COLORS = {
    "ink": "#1f2937",
    "muted": "#64748b",
    "line": "#64748b",
    "data": "#e6f2ff",
    "data_stroke": "#7aa7d9",
    "agent": "#e8f7ed",
    "agent_stroke": "#67a87b",
    "bench": "#f1eaff",
    "bench_stroke": "#9b83d4",
    "artifact": "#f4f6f8",
    "artifact_stroke": "#9aa4af",
    "hidden": "#fff3cf",
    "hidden_stroke": "#d6a23a",
    "white": "#ffffff",
}


class SvgCanvas:
    """Small SVG helper tailored for thesis box diagrams."""

    def __init__(self, width: int = 1920, height: int = 1080) -> None:
        self.width = width
        self.height = height
        self.items: list[str] = []

    def panel(
        self,
        x: int,
        y: int,
        w: int,
        h: int,
        title: str,
        fill: str,
        stroke: str,
    ) -> None:
        self.items.append(
            f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="28" '
            f'fill="{fill}" stroke="{stroke}" stroke-width="2" opacity="0.95"/>'
        )
        self.text(title, x + 28, y + 42, size=26, weight="700", anchor="start")

    def box(
        self,
        x: int,
        y: int,
        w: int,
        h: int,
        lines: list[str] | str,
        *,
        fill: str,
        stroke: str,
        size: int = 22,
        weight: str = "600",
        radius: int = 18,
    ) -> None:
        if isinstance(lines, str):
            lines = [lines]
        self.items.append(
            f'<rect class="card" x="{x}" y="{y}" width="{w}" height="{h}" rx="{radius}" '
            f'fill="{fill}" stroke="{stroke}" stroke-width="2"/>'
        )
        line_gap = int(size * 1.35)
        start_y = y + h / 2 - (len(lines) - 1) * line_gap / 2 + size * 0.35
        for idx, line in enumerate(lines):
            self.text(
                line,
                x + w / 2,
                int(start_y + idx * line_gap),
                size=size,
                weight=weight if idx == 0 else "500",
            )

    def badge(self, x: int, y: int, text: str, *, fill: str, stroke: str) -> None:
        width = max(120, len(text) * 18 + 34)
        self.items.append(
            f'<rect x="{x}" y="{y}" width="{width}" height="42" rx="21" '
            f'fill="{fill}" stroke="{stroke}" stroke-width="1.8"/>'
        )
        self.text(text, x + width / 2, y + 28, size=18, weight="700")

    def text(
        self,
        content: str,
        x: float,
        y: float,
        *,
        size: int = 20,
        weight: str = "500",
        fill: str | None = None,
        anchor: str = "middle",
    ) -> None:
        fill = fill or COLORS["ink"]
        self.items.append(
            f'<text x="{x}" y="{y}" text-anchor="{anchor}" '
            f'font-size="{size}" font-weight="{weight}" fill="{fill}">'
            f"{html.escape(content)}</text>"
        )

    def arrow(
        self,
        x1: int,
        y1: int,
        x2: int,
        y2: int,
        *,
        label: str | None = None,
        dashed: bool = False,
        color: str | None = None,
    ) -> None:
        color = color or COLORS["line"]
        dash = ' stroke-dasharray="9 8"' if dashed else ""
        self.items.append(
            f'<path d="M{x1},{y1} L{x2},{y2}" fill="none" stroke="{color}" '
            f'stroke-width="3" marker-end="url(#arrow)"{dash}/>'
        )
        if label:
            self.text(
                label,
                (x1 + x2) / 2,
                (y1 + y2) / 2 - 10,
                size=17,
                weight="600",
                fill=color,
            )

    def polyline(
        self,
        points: list[tuple[int, int]],
        *,
        label: str | None = None,
        dashed: bool = False,
        color: str | None = None,
    ) -> None:
        color = color or COLORS["line"]
        point_text = " ".join(f"{x},{y}" for x, y in points)
        dash = ' stroke-dasharray="9 8"' if dashed else ""
        self.items.append(
            f'<polyline points="{point_text}" fill="none" stroke="{color}" '
            f'stroke-width="3" marker-end="url(#arrow)"{dash}/>'
        )
        if label and len(points) >= 2:
            mid = points[len(points) // 2]
            self.text(label, mid[0], mid[1] - 12, size=17, weight="600", fill=color)

    def render(self) -> str:
        defs = f"""
<defs>
  <marker id="arrow" markerWidth="14" markerHeight="14" refX="11" refY="5"
          orient="auto" markerUnits="strokeWidth">
    <path d="M0,0 L12,5 L0,10 Z" fill="{COLORS["line"]}"/>
  </marker>
  <filter id="shadow" x="-10%" y="-10%" width="120%" height="130%">
    <feDropShadow dx="0" dy="8" stdDeviation="8" flood-color="#0f172a" flood-opacity="0.12"/>
  </filter>
</defs>
<style>
  text {{
    font-family: {FONT};
    dominant-baseline: alphabetic;
  }}
  .card {{
    filter: url(#shadow);
  }}
</style>
"""
        body = "\n".join(self.items)
        return (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.width}" '
            f'height="{self.height}" viewBox="0 0 {self.width} {self.height}">\n'
            f'<rect width="100%" height="100%" fill="#ffffff"/>\n{defs}\n{body}\n</svg>\n'
        )


def render_system_architecture() -> SvgCanvas:
    c = SvgCanvas()
    c.text("数据证据驱动的交互式偏好启发闭环", 960, 62, size=34, weight="800")
    c.text(
        "数据层提供事实边界，业务 Agent 进行语义归一、机会规划与证据谈判，Benchmark 负责可复核评测",
        960,
        104,
        size=20,
        fill=COLORS["muted"],
    )

    c.panel(70, 165, 430, 710, "数据层", COLORS["data"], COLORS["data_stroke"])
    c.box(
        115,
        245,
        340,
        110,
        ["招生事实库", "分数 / 位次 / 选科 / 学费"],
        fill=COLORS["white"],
        stroke=COLORS["data_stroke"],
    )
    c.box(
        115,
        405,
        340,
        130,
        ["层级画像", "专业层级本体", "地域层级画像"],
        fill=COLORS["white"],
        stroke=COLORS["data_stroke"],
    )
    c.box(
        115,
        585,
        340,
        130,
        ["收益画像", "专业质量", "就业结果"],
        fill=COLORS["white"],
        stroke=COLORS["data_stroke"],
    )

    c.panel(
        565, 165, 790, 710, "轻量 MAS Agent", COLORS["agent"], COLORS["agent_stroke"]
    )
    c.box(
        610,
        245,
        290,
        105,
        ["前置语义归一", "查询重写 / 偏好轴拆解"],
        fill=COLORS["white"],
        stroke=COLORS["agent_stroke"],
    )
    c.box(
        1020,
        245,
        290,
        105,
        ["约束解析器", "显式约束 / SQL 锁定"],
        fill=COLORS["white"],
        stroke=COLORS["agent_stroke"],
    )
    c.box(
        610,
        445,
        290,
        120,
        ["LLM 机会规划器", "排序 / 澄清", "不生成事实候选"],
        fill=COLORS["white"],
        stroke=COLORS["agent_stroke"],
    )
    c.box(
        1020,
        445,
        290,
        120,
        ["确定性证据探针", "SQL / 本体 / 画像查询"],
        fill=COLORS["white"],
        stroke=COLORS["agent_stroke"],
    )
    c.box(
        815,
        655,
        290,
        105,
        ["证据谈判器", "对比基线并组织回复"],
        fill=COLORS["white"],
        stroke=COLORS["agent_stroke"],
    )

    c.panel(
        1420, 165, 430, 420, "Benchmark 层", COLORS["bench"], COLORS["bench_stroke"]
    )
    c.box(
        1465,
        255,
        340,
        115,
        ["冰山用户画像", "显式话语 + 隐藏妥协"],
        fill=COLORS["white"],
        stroke=COLORS["bench_stroke"],
    )
    c.box(
        1465,
        420,
        340,
        115,
        ["多轮评测器", "事实命中 + 过程检查"],
        fill=COLORS["white"],
        stroke=COLORS["bench_stroke"],
    )

    c.panel(
        1420, 650, 430, 225, "论文产物", COLORS["artifact"], COLORS["artifact_stroke"]
    )
    c.box(
        1465,
        730,
        340,
        95,
        ["聚合指标 / 逐例证据", "论文图表与失败分析"],
        fill=COLORS["white"],
        stroke=COLORS["artifact_stroke"],
    )

    c.arrow(455, 300, 610, 300, label="硬约束事实")
    c.polyline(
        [(455, 470), (520, 470), (520, 610), (1165, 610), (1165, 565)],
        label="证据空间",
    )
    c.arrow(900, 298, 1020, 298)
    c.polyline([(1165, 350), (1165, 410), (755, 410), (755, 445)], label="显式意图")
    c.arrow(900, 505, 1020, 505, label="规划探针")
    c.polyline([(1165, 565), (1165, 705), (1105, 705)])
    c.polyline([(1105, 705), (1375, 705), (1375, 312), (1465, 312)], label="证据链")
    c.arrow(1635, 535, 1635, 730, label="结果")
    return c


def render_mas_workflow() -> SvgCanvas:
    c = SvgCanvas()
    c.text(
        "轻量 MAS 工作流：LLM 规划，确定性探针给出事实候选",
        960,
        62,
        size=34,
        weight="800",
    )
    c.text(
        "实现角色可括注为 gatekeeper / radar / negotiator，但正文主叙述采用学术化角色名",
        960,
        104,
        size=20,
        fill=COLORS["muted"],
    )

    c.box(
        85,
        205,
        270,
        120,
        ["用户显式话语", "分数 / 专业 / 地域", "风险 / 预算"],
        fill=COLORS["white"],
        stroke=COLORS["artifact_stroke"],
    )
    c.box(
        430,
        205,
        285,
        120,
        ["前置语义归一", "CoT 查询重写", "偏好轴拆解"],
        fill=COLORS["agent"],
        stroke=COLORS["agent_stroke"],
    )
    c.box(
        790,
        205,
        285,
        120,
        ["约束解析器", "实体抽取", "SQL 硬约束锁定"],
        fill=COLORS["agent"],
        stroke=COLORS["agent_stroke"],
    )
    c.box(
        1150,
        205,
        300,
        120,
        ["LLM 机会规划器", "probe_plan", "排序 / 澄清提示"],
        fill=COLORS["agent"],
        stroke=COLORS["agent_stroke"],
    )

    c.box(
        790,
        460,
        300,
        150,
        ["确定性证据探针", "专业-地域 / 风险组合", "预算 / 质量 / 就业", "地域层级"],
        fill=COLORS["agent"],
        stroke=COLORS["agent_stroke"],
    )
    c.box(
        1150,
        460,
        300,
        150,
        ["可谈判机会集合", "事实候选", "证据来源", "收益计算"],
        fill=COLORS["agent"],
        stroke=COLORS["agent_stroke"],
    )
    c.box(
        1515,
        460,
        300,
        150,
        ["证据谈判器", "保留什么", "放宽什么", "换来什么"],
        fill=COLORS["agent"],
        stroke=COLORS["agent_stroke"],
    )

    c.box(
        790,
        735,
        300,
        105,
        ["硬约束基线", "只返回显式约束内结果"],
        fill=COLORS["artifact"],
        stroke=COLORS["artifact_stroke"],
    )
    c.box(
        1515,
        735,
        300,
        105,
        ["面向用户的回复", "二选一式偏好启发"],
        fill=COLORS["artifact"],
        stroke=COLORS["artifact_stroke"],
    )

    c.box(
        430,
        735,
        285,
        105,
        ["hidden fields", "业务 Agent 不可见"],
        fill=COLORS["hidden"],
        stroke=COLORS["hidden_stroke"],
    )

    c.arrow(355, 265, 430, 265)
    c.arrow(715, 265, 790, 265)
    c.arrow(1075, 265, 1150, 265)
    c.polyline([(1300, 325), (1300, 390), (940, 390), (940, 460)], label="选择探测轴")
    c.arrow(1090, 535, 1150, 535)
    c.arrow(1450, 535, 1515, 535)
    c.polyline([(932, 325), (932, 690), (940, 735)], label="对照")
    c.polyline([(1090, 785), (1360, 785), (1515, 585)])
    c.arrow(1665, 610, 1665, 735)
    c.arrow(715, 785, 790, 785, dashed=True, label="不进入业务链")
    c.badge(
        1185,
        360,
        "LLM 只规划，不编造事实候选",
        fill="#ffffff",
        stroke=COLORS["agent_stroke"],
    )
    return c


def render_benchmark_flow() -> SvgCanvas:
    c = SvgCanvas()
    c.text(
        "Benchmark 多轮评测流程：显式输入与隐藏偏好隔离", 960, 62, size=34, weight="800"
    )
    c.text(
        "隐藏妥协字段只进入模拟器/评测器，不进入被测业务 Agent",
        960,
        104,
        size=20,
        fill=COLORS["muted"],
    )

    c.box(
        95,
        260,
        290,
        120,
        ["真实数据库 gap", "基线集合 vs 放宽集合"],
        fill=COLORS["data"],
        stroke=COLORS["data_stroke"],
    )
    c.box(
        465,
        260,
        290,
        120,
        ["冰山用户画像", "显式约束 + 隐藏妥协"],
        fill=COLORS["bench"],
        stroke=COLORS["bench_stroke"],
    )
    c.box(
        835,
        175,
        300,
        120,
        ["显式用户话语", "只暴露表层约束"],
        fill=COLORS["bench"],
        stroke=COLORS["bench_stroke"],
    )
    c.box(
        1215,
        175,
        300,
        120,
        ["用户模拟器", "多轮交互"],
        fill=COLORS["bench"],
        stroke=COLORS["bench_stroke"],
    )
    c.box(
        1595,
        175,
        270,
        120,
        ["被测 Agent", "语义归一 + 规划 + 探针"],
        fill=COLORS["agent"],
        stroke=COLORS["agent_stroke"],
    )

    c.box(
        835,
        535,
        300,
        120,
        ["隐藏妥协条件", "仅评测端可见"],
        fill=COLORS["hidden"],
        stroke=COLORS["hidden_stroke"],
    )
    c.box(
        1215,
        535,
        300,
        120,
        ["对话记录", "回复 + 可审计状态"],
        fill=COLORS["artifact"],
        stroke=COLORS["artifact_stroke"],
    )
    c.box(
        1595,
        535,
        270,
        120,
        ["评测器", "事实命中 + 过程检查"],
        fill=COLORS["bench"],
        stroke=COLORS["bench_stroke"],
    )
    c.box(
        1215,
        790,
        300,
        105,
        ["聚合结果与逐例证据", "summary / evidence"],
        fill=COLORS["artifact"],
        stroke=COLORS["artifact_stroke"],
    )

    c.arrow(385, 320, 465, 320)
    c.arrow(755, 320, 835, 235)
    c.arrow(1135, 235, 1215, 235)
    c.arrow(1515, 235, 1595, 235)
    c.polyline([(1730, 295), (1730, 455), (1365, 455), (1365, 535)])
    c.arrow(1515, 595, 1595, 595)
    c.arrow(1730, 655, 1515, 840)
    c.polyline([(610, 380), (610, 595), (835, 595)], dashed=True, label="hidden only")
    c.arrow(1135, 595, 1215, 595, dashed=True, label="evaluator-only")
    c.badge(
        835,
        405,
        "Agent 不读取 implicit_flexibilities / volunteer_set / axis_flexibilities",
        fill="#ffffff",
        stroke=COLORS["hidden_stroke"],
    )
    return c


def render_data_mapping() -> SvgCanvas:
    c = SvgCanvas()
    c.text("数据证据层与可谈判偏好轴映射", 960, 62, size=34, weight="800")
    c.text(
        "LLM 决定先探什么；确定性探针返回候选和证据；谈判器组织可解释对比",
        960,
        104,
        size=20,
        fill=COLORS["muted"],
    )

    evidence = [
        (85, 175, "招生事实", "最低分 / 位次 / 选科"),
        (85, 315, "专业层级本体", "规则挂载 + 模型候选 + LLM 复核"),
        (85, 455, "风险证据", "分差 / 位次差"),
        (85, 595, "成本证据", "学费与预算差"),
        (85, 735, "质量 / 就业 / 地域画像", "专业质量 / 就业结果 / 地域层级"),
    ]
    for x, y, title, desc in evidence:
        c.box(
            x,
            y,
            390,
            95,
            [title, desc],
            fill=COLORS["data"],
            stroke=COLORS["data_stroke"],
            size=20,
        )

    c.box(
        630,
        260,
        320,
        120,
        ["LLM 机会规划", "选择探测顺序", "输出澄清提示"],
        fill=COLORS["agent"],
        stroke=COLORS["agent_stroke"],
    )
    c.box(
        630,
        520,
        320,
        120,
        ["确定性证据探针", "SQL / 本体 / 画像查询", "唯一事实候选来源"],
        fill=COLORS["agent"],
        stroke=COLORS["agent_stroke"],
    )

    relax = [
        (1120, 150, "专业-地域联合放宽", "Staged Relaxation"),
        (1475, 150, "风险组合放宽", "冲 / 稳 / 保"),
        (1120, 320, "预算性价比放宽", "小幅超预算"),
        (1475, 320, "专业质量放宽", "质量收益证据"),
        (1120, 490, "就业导向放宽", "结果证据"),
        (1475, 490, "地域层级放宽", "偏好显性化证据"),
    ]
    for x, y, title, desc in relax:
        c.box(
            x,
            y,
            310,
            110,
            [title, desc],
            fill=COLORS["agent"],
            stroke=COLORS["agent_stroke"],
            size=20,
        )

    c.box(
        1220,
        760,
        480,
        110,
        ["证据谈判器", "对比硬约束基线与可谈判机会", "城市层级不直接计入客观收益"],
        fill=COLORS["artifact"],
        stroke=COLORS["artifact_stroke"],
        size=21,
    )

    for _, y, _, _ in evidence:
        c.arrow(475, y + 48, 630, 580)
    c.arrow(790, 380, 790, 520, label="只规划")
    for x, y, _, _ in relax:
        c.arrow(950, 580, x, y + 55)
    c.arrow(1460, 600, 1460, 760, label="证据汇总")
    c.badge(
        600,
        715,
        "事实候选来自数据探针，不来自 LLM 生成",
        fill="#ffffff",
        stroke=COLORS["agent_stroke"],
    )
    return c


def _write_svg(path: Path, canvas: SvgCanvas) -> None:
    path.write_text(canvas.render(), encoding="utf-8")


def _find_browser() -> Path | None:
    candidates = [
        shutil.which("msedge"),
        "C:/Program Files/Microsoft/Edge/Application/msedge.exe",
        "C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe",
        shutil.which("chrome"),
        "C:/Program Files/Google/Chrome/Application/chrome.exe",
        "C:/Program Files (x86)/Google/Chrome/Application/chrome.exe",
    ]
    for candidate in candidates:
        if candidate and Path(candidate).exists():
            return Path(candidate)
    return None


def _svg_to_png(
    svg_path: Path, png_path: Path, browser: Path, width: int, height: int
) -> None:
    with tempfile.TemporaryDirectory() as profile_dir:
        subprocess.run(
            [
                str(browser),
                "--headless",
                "--disable-gpu",
                "--no-sandbox",
                "--allow-file-access-from-files",
                "--hide-scrollbars",
                f"--user-data-dir={profile_dir}",
                f"--window-size={width},{height}",
                f"--screenshot={png_path}",
                str(svg_path),
            ],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )


def render_all(output_dir: Path) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    browser = _find_browser()
    if browser is None:
        raise RuntimeError(
            "Could not find Chrome or Edge for PNG export. SVG files can still be produced, "
            "but the thesis currently expects PNG copies too."
        )

    figures = {
        "fig_4_1_system_architecture": render_system_architecture(),
        "fig_5_1_mas_workflow": render_mas_workflow(),
        "fig_4_2_benchmark_flow": render_benchmark_flow(),
        "fig_4_3_data_evidence_relax_mapping": render_data_mapping(),
    }
    rendered: list[Path] = []
    for stem, canvas in figures.items():
        svg_path = output_dir / f"{stem}.svg"
        png_path = output_dir / f"{stem}.png"
        _write_svg(svg_path, canvas)
        _svg_to_png(svg_path, png_path, browser, canvas.width, canvas.height)
        rendered.extend([png_path, svg_path])
    return rendered


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Render polished thesis diagrams as hand-authored SVG/PNG.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help=f"Output directory. Defaults to {DEFAULT_OUTPUT_DIR}",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        files = render_all(args.output_dir)
    except (RuntimeError, subprocess.CalledProcessError) as exc:
        print(str(exc), file=sys.stderr)
        return 2

    print("Rendered thesis diagrams:")
    for path in files:
        print(f"  {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
