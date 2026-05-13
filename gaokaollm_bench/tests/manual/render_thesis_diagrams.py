"""Render polished thesis diagrams as hand-authored SVG/PNG assets.

The previous Graphviz/Diagrams layout was reproducible but too wide and
engineering-like for the thesis. This generator keeps everything local and
deterministic: it writes curated SVG layouts and uses a local headless browser
only to rasterize PNG copies. It does not read benchmark hidden fields, connect
to PostgreSQL, call an LLM, or rerun any experiment.

正式论文图题统一由 LaTeX caption 承担，本脚本只绘制图内结构和必要标签。
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

    def tag(
        self,
        x: int,
        y: int,
        text: str,
        *,
        fill: str = "#ffffff",
        stroke: str | None = None,
        color: str | None = None,
        size: int = 16,
        width: int | None = None,
    ) -> None:
        stroke = stroke or fill
        color = color or COLORS["muted"]
        width = width or max(92, len(text) * 15 + 24)
        self.items.append(
            f'<rect x="{x}" y="{y}" width="{width}" height="30" rx="15" '
            f'fill="{fill}" stroke="{stroke}" stroke-width="1.2" opacity="0.96"/>'
        )
        self.text(text, x + width / 2, y + 21, size=size, weight="700", fill=color)

    def cylinder(
        self,
        x: int,
        y: int,
        w: int,
        h: int,
        lines: list[str] | str,
        *,
        fill: str,
        stroke: str,
        size: int = 20,
        weight: str = "600",
    ) -> None:
        if isinstance(lines, str):
            lines = [lines]
        cap = 28
        self.items.append(
            f'<path class="card" d="M{x},{y + cap} '
            f"C{x},{y} {x + w},{y} {x + w},{y + cap} "
            f"L{x + w},{y + h - cap} "
            f'C{x + w},{y + h} {x},{y + h} {x},{y + h - cap} Z" '
            f'fill="{fill}" stroke="{stroke}" stroke-width="2"/>'
        )
        self.items.append(
            f'<path d="M{x},{y + cap} C{x},{y + cap * 2} {x + w},{y + cap * 2} '
            f'{x + w},{y + cap}" fill="none" stroke="{stroke}" stroke-width="2"/>'
        )
        line_gap = int(size * 1.35)
        start_y = y + h / 2 - (len(lines) - 1) * line_gap / 2 + size * 0.35 + 8
        for idx, line in enumerate(lines):
            self.text(
                line,
                x + w / 2,
                int(start_y + idx * line_gap),
                size=size,
                weight=weight if idx == 0 else "500",
            )

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
    c.panel(
        70,
        55,
        1780,
        210,
        "Tier 1  混合倡议交互与评测环境",
        COLORS["data"],
        COLORS["data_stroke"],
    )
    c.box(
        115,
        130,
        260,
        80,
        ["用户", "显式目标与反馈"],
        fill=COLORS["white"],
        stroke=COLORS["data_stroke"],
        size=20,
    )
    c.box(
        455,
        120,
        310,
        100,
        ["冰山画像", "显式约束 + 隐藏底线", "只在交互中逐步暴露"],
        fill=COLORS["hidden"],
        stroke=COLORS["hidden_stroke"],
        size=19,
    )
    c.box(
        850,
        130,
        290,
        80,
        ["Interrupt 挂起", "抛出帕累托边际替代问题"],
        fill=COLORS["white"],
        stroke=COLORS["data_stroke"],
        size=19,
    )
    c.box(
        1225,
        130,
        290,
        80,
        ["Resume 唤醒", "接受 / 拒绝 / 犹豫"],
        fill=COLORS["white"],
        stroke=COLORS["data_stroke"],
        size=19,
    )
    c.box(
        1585,
        130,
        220,
        80,
        ["显式约束", "分数 / 位次 / 地域"],
        fill=COLORS["white"],
        stroke=COLORS["data_stroke"],
        size=19,
    )

    c.panel(
        70,
        300,
        1780,
        255,
        "Tier 2  轻量多角色智能体工作流（LLM 边界）",
        COLORS["agent"],
        COLORS["agent_stroke"],
    )
    mas_nodes = [
        (115, ["语义归一器", "查询重写 / 槽位标准化"]),
        (405, ["约束解析器", "事实锁定 / 一票否决"]),
        (695, ["机会规划器", "可谈判机会排序"]),
        (985, ["确定性证据探针", "SQL / 本体 / 画像"]),
        (1275, ["证据谈判器", "组织证据化提问"]),
        (1565, ["偏好追踪器", "w_t, σ²_t 后验更新"]),
    ]
    for x, lines in mas_nodes:
        c.box(
            x,
            395,
            240,
            95,
            lines,
            fill=COLORS["white"],
            stroke=COLORS["agent_stroke"],
            size=18,
        )

    c.panel(
        70,
        590,
        1780,
        205,
        "Tier 3  运筹学认知引擎层（本文核心创新）",
        "#fff2df",
        "#d97938",
    )
    c.box(
        185,
        665,
        390,
        90,
        ["非补偿性 SAVF", "单属性价值映射 v_j(x)", "触发隐藏底线一票否决"],
        fill="#ffe4c4",
        stroke="#d97938",
        size=19,
    )
    c.box(
        765,
        665,
        390,
        90,
        ["UCB Max-EIG 主动探测", "选择最大信息增益轴", "调度帕累托极大 L1 候选对"],
        fill="#ffe4c4",
        stroke="#d97938",
        size=19,
    )
    c.box(
        1345,
        665,
        390,
        90,
        ["BT 梯度与 D-S 追踪", "Bradley-Terry 更新 w_t", "犹豫反馈推高 σ²_t"],
        fill="#ffe4c4",
        stroke="#d97938",
        size=19,
    )

    c.panel(
        70,
        830,
        1780,
        185,
        "Tier 4  数据与证据物理底座",
        COLORS["artifact"],
        COLORS["artifact_stroke"],
    )
    c.cylinder(
        190,
        895,
        390,
        85,
        ["PostgreSQL 招生事实库", "分数 / 位次 / 计划 / 学费"],
        fill=COLORS["white"],
        stroke=COLORS["artifact_stroke"],
        size=18,
    )
    c.cylinder(
        765,
        895,
        390,
        85,
        ["层级本体库", "专业层级 / 地域层级"],
        fill=COLORS["white"],
        stroke=COLORS["artifact_stroke"],
        size=18,
    )
    c.cylinder(
        1340,
        895,
        390,
        85,
        ["标准化画像库", "专业质量 / 就业证据"],
        fill=COLORS["white"],
        stroke=COLORS["artifact_stroke"],
        size=18,
    )

    c.arrow(375, 170, 455, 170, label="陈述需求")
    c.arrow(765, 170, 850, 170, label="探索提问")
    c.arrow(1140, 170, 1225, 170, label="用户反馈")
    c.arrow(1515, 170, 1585, 170, label="事实锚定")

    c.arrow(355, 443, 405, 443)
    c.arrow(645, 443, 695, 443)
    c.arrow(935, 443, 985, 443)
    c.arrow(1225, 443, 1275, 443)
    c.arrow(1515, 443, 1565, 443)
    c.polyline([(1685, 490), (1685, 535), (815, 535), (815, 490)], dashed=True)
    c.tag(
        700,
        515,
        "反馈闭环：更新信念状态",
        fill=COLORS["agent"],
        stroke=COLORS["agent_stroke"],
        width=240,
    )

    c.polyline([(610, 220), (610, 335), (235, 335), (235, 395)])
    c.tag(
        300,
        268,
        "用户画像输入",
        fill=COLORS["agent"],
        stroke=COLORS["agent_stroke"],
        width=135,
    )
    c.polyline([(995, 395), (995, 270), (995, 210)])
    c.tag(
        945,
        272,
        "Interrupt",
        fill=COLORS["data"],
        stroke=COLORS["data_stroke"],
        width=100,
    )
    c.polyline([(1370, 210), (1370, 335), (1685, 335), (1685, 395)])
    c.tag(
        1628,
        313,
        "Resume",
        fill=COLORS["data"],
        stroke=COLORS["data_stroke"],
        width=100,
    )

    c.polyline([(385, 895), (385, 815), (1105, 815), (1105, 490)])
    c.tag(
        1008,
        795,
        "结构化事实",
        fill=COLORS["artifact"],
        stroke=COLORS["artifact_stroke"],
        width=120,
    )
    c.polyline([(960, 895), (960, 815), (235, 815), (235, 490)])
    c.tag(
        182,
        786,
        "语义标准化",
        fill=COLORS["artifact"],
        stroke=COLORS["artifact_stroke"],
        width=120,
    )
    c.polyline([(1535, 895), (1535, 815), (1105, 815), (1105, 490)])
    c.tag(
        1465,
        786,
        "画像证据",
        fill=COLORS["artifact"],
        stroke=COLORS["artifact_stroke"],
        width=110,
    )

    c.polyline(
        [(380, 665), (380, 575), (1105, 575), (1105, 490)], dashed=True, color="#d97938"
    )
    c.tag(
        995,
        556,
        "SAVF 映射探针结果",
        fill="#fff2df",
        stroke="#d97938",
        color="#d97938",
        width=190,
    )
    c.polyline(
        [(960, 665), (960, 575), (815, 575), (815, 490)], dashed=True, color="#d97938"
    )
    c.tag(
        735,
        556,
        "UCB 强控规划器",
        fill="#fff2df",
        stroke="#d97938",
        color="#d97938",
        width=160,
    )
    c.polyline(
        [(960, 665), (960, 575), (1105, 575), (1105, 490)], dashed=True, color="#d97938"
    )
    c.tag(
        1040,
        585,
        "Max-EIG 调度探针",
        fill="#fff2df",
        stroke="#d97938",
        color="#d97938",
        width=170,
    )
    c.polyline(
        [(1540, 665), (1540, 575), (1685, 575), (1685, 490)],
        dashed=True,
        color="#d97938",
    )
    c.tag(
        1590,
        556,
        "BT / D-S 更新后验",
        fill="#fff2df",
        stroke="#d97938",
        color="#d97938",
        width=180,
    )

    c.arrow(575, 710, 765, 710, label="价值曲面")
    c.arrow(1155, 710, 1345, 710, label="比较反馈")
    return c


def render_mas_workflow() -> SvgCanvas:
    c = SvgCanvas()
    c.box(
        85,
        125,
        270,
        120,
        ["用户显式话语", "分数 / 专业 / 地域", "风险 / 预算"],
        fill=COLORS["white"],
        stroke=COLORS["artifact_stroke"],
    )
    c.box(
        430,
        125,
        285,
        120,
        ["前置语义归一", "查询重写", "偏好轴拆解"],
        fill=COLORS["agent"],
        stroke=COLORS["agent_stroke"],
    )
    c.box(
        790,
        125,
        285,
        120,
        ["约束解析器", "实体抽取", "硬约束锁定"],
        fill=COLORS["agent"],
        stroke=COLORS["agent_stroke"],
    )
    c.box(
        1150,
        125,
        300,
        120,
        ["机会规划器", "探针计划", "排序 / 澄清提示"],
        fill=COLORS["agent"],
        stroke=COLORS["agent_stroke"],
    )

    c.box(
        610,
        365,
        300,
        135,
        ["确定性证据探针", "专业-地域 / 风险", "预算 / 质量 / 就业"],
        fill=COLORS["agent"],
        stroke=COLORS["agent_stroke"],
    )
    c.box(
        1000,
        365,
        300,
        135,
        ["可谈判机会集合", "事实候选", "证据来源", "收益计算"],
        fill=COLORS["agent"],
        stroke=COLORS["agent_stroke"],
    )
    c.box(
        1390,
        365,
        300,
        135,
        ["证据谈判器", "保留什么", "放宽什么", "换来什么"],
        fill=COLORS["agent"],
        stroke=COLORS["agent_stroke"],
    )

    c.box(
        610,
        600,
        300,
        105,
        ["置信上界选轴", "选择高不确定维度"],
        fill=COLORS["bench"],
        stroke=COLORS["bench_stroke"],
    )
    c.box(
        1000,
        600,
        300,
        105,
        ["后验追踪", "接受 / 拒绝 / 犹豫"],
        fill=COLORS["bench"],
        stroke=COLORS["bench_stroke"],
    )
    c.box(
        1390,
        600,
        300,
        105,
        ["暂停与恢复", "一问一答更新状态"],
        fill=COLORS["bench"],
        stroke=COLORS["bench_stroke"],
    )

    c.box(
        610,
        795,
        300,
        105,
        ["硬约束基准", "显式约束内结果"],
        fill=COLORS["artifact"],
        stroke=COLORS["artifact_stroke"],
    )
    c.box(
        1390,
        795,
        300,
        105,
        ["最终解释输出", "推荐 / 证据链 / 风险"],
        fill=COLORS["artifact"],
        stroke=COLORS["artifact_stroke"],
    )

    c.box(
        85,
        795,
        285,
        105,
        ["隐藏评测字段", "业务智能体不可见"],
        fill=COLORS["hidden"],
        stroke=COLORS["hidden_stroke"],
    )

    c.arrow(355, 185, 430, 185)
    c.arrow(715, 185, 790, 185)
    c.arrow(1075, 185, 1150, 185)
    c.polyline([(1300, 245), (1300, 305), (760, 305), (760, 365)], label="选择探测轴")
    c.arrow(910, 432, 1000, 432)
    c.arrow(1300, 432, 1390, 432)
    c.arrow(1540, 500, 1540, 600, label="用户反馈")
    c.arrow(1390, 652, 1300, 652)
    c.arrow(1000, 652, 910, 652)
    c.polyline([(760, 705), (760, 795)], label="对照")
    c.polyline([(910, 848), (1150, 848), (1390, 848)], label="停止后输出")
    c.arrow(370, 848, 610, 848, dashed=True, label="不进入业务链")
    return c


def render_benchmark_flow() -> SvgCanvas:
    c = SvgCanvas()
    c.box(
        95,
        210,
        290,
        120,
        ["真实数据差异", "基准集合 / 放宽集合"],
        fill=COLORS["data"],
        stroke=COLORS["data_stroke"],
    )
    c.box(
        465,
        210,
        290,
        120,
        ["冰山用户画像", "显式约束 + 隐藏妥协"],
        fill=COLORS["bench"],
        stroke=COLORS["bench_stroke"],
    )
    c.box(
        835,
        125,
        300,
        120,
        ["显式用户话语", "只暴露表层约束"],
        fill=COLORS["bench"],
        stroke=COLORS["bench_stroke"],
    )
    c.box(
        1215,
        125,
        300,
        120,
        ["用户模拟器", "多轮交互"],
        fill=COLORS["bench"],
        stroke=COLORS["bench_stroke"],
    )
    c.box(
        1595,
        125,
        270,
        120,
        ["被测智能体", "语义归一 + 规划 + 探针"],
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
        ["聚合结果", "逐例证据"],
        fill=COLORS["artifact"],
        stroke=COLORS["artifact_stroke"],
    )

    c.arrow(385, 270, 465, 270)
    c.arrow(755, 270, 835, 185)
    c.arrow(1135, 185, 1215, 185)
    c.arrow(1515, 185, 1595, 185)
    c.polyline([(1730, 245), (1730, 455), (1365, 455), (1365, 535)])
    c.arrow(1515, 595, 1595, 595)
    c.arrow(1730, 655, 1515, 840)
    c.polyline([(610, 330), (610, 595), (835, 595)], dashed=True, label="隐藏通道")
    c.arrow(1135, 595, 1215, 595, dashed=True, label="评测通道")
    c.box(
        650,
        375,
        520,
        72,
        ["隔离边界", "隐藏字段不进入被测智能体"],
        fill=COLORS["hidden"],
        stroke=COLORS["hidden_stroke"],
        size=20,
    )
    return c


def render_data_mapping() -> SvgCanvas:
    c = SvgCanvas()
    evidence = [
        (85, 125, "招生事实", "最低分 / 位次 / 选科"),
        (85, 265, "专业层级本体", "规则挂载 / 候选复核"),
        (85, 405, "风险证据", "分差 / 位次差"),
        (85, 545, "成本证据", "学费与预算差"),
        (85, 685, "质量 / 就业 / 地域画像", "质量 / 就业 / 地域"),
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
        210,
        320,
        120,
        ["机会规划", "选择探测顺序", "输出澄清提示"],
        fill=COLORS["agent"],
        stroke=COLORS["agent_stroke"],
    )
    c.box(
        630,
        500,
        320,
        120,
        ["确定性证据探针", "数据表 / 本体 / 画像", "事实候选来源"],
        fill=COLORS["agent"],
        stroke=COLORS["agent_stroke"],
    )

    relax = [
        (1120, 105, "专业-地域联合放宽", "分阶段放宽"),
        (1475, 105, "风险组合放宽", "冲 / 稳 / 保"),
        (1120, 275, "预算性价比放宽", "小幅超预算"),
        (1475, 275, "专业质量放宽", "质量收益证据"),
        (1120, 445, "就业导向放宽", "结果证据"),
        (1475, 445, "地域层级放宽", "偏好显性化证据"),
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
        735,
        480,
        110,
        ["证据谈判器", "保留什么", "放宽什么", "换来什么"],
        fill=COLORS["artifact"],
        stroke=COLORS["artifact_stroke"],
        size=21,
    )

    for _, y, _, _ in evidence:
        c.arrow(475, y + 48, 630, 560)
    c.arrow(790, 330, 790, 500, label="只规划")
    for x, y, _, _ in relax:
        c.arrow(950, 560, x, y + 55)
    c.arrow(1460, 555, 1460, 735, label="证据汇总")
    return c


def render_major_tree_partial() -> SvgCanvas:
    c = SvgCanvas()
    c.panel(90, 95, 575, 820, "8 个第 0 层大类", COLORS["data"], COLORS["data_stroke"])
    roots = [
        "医学大类",
        "计算机与电子信息大类",
        "传统工科大类",
        "经济管理商科大类",
        "人文社科教育大类",
        "理学农学大类",
        "艺术设计体育大类",
        "高职与应用技术大类",
    ]
    for idx, label in enumerate(roots):
        y = 170 + idx * 84
        fill = COLORS["white"] if idx not in {1, 2, 3} else "#f0fdf4"
        stroke = (
            COLORS["data_stroke"] if idx not in {1, 2, 3} else COLORS["agent_stroke"]
        )
        c.box(145, y, 460, 58, label, fill=fill, stroke=stroke, size=20, radius=14)

    c.panel(
        785, 95, 1035, 820, "典型高频分支展开", COLORS["agent"], COLORS["agent_stroke"]
    )
    branches = [
        (
            850,
            180,
            "计算机与电子信息",
            ["计算机软件与数据", "计算机科学", "数据与人工智能", "软件与网络工程"],
        ),
        (
            850,
            405,
            "传统工科",
            ["制造能源材料", "机械与车辆", "电气与能源", "材料与化工"],
        ),
        (
            850,
            630,
            "经济管理商科",
            ["经济金融会计", "金融会计财务", "经济与贸易", "工商管理营销"],
        ),
    ]
    for x, y, title, leaves in branches:
        c.box(
            x,
            y,
            250,
            62,
            title,
            fill=COLORS["white"],
            stroke=COLORS["agent_stroke"],
            size=19,
            radius=16,
        )
        c.box(
            x + 360,
            y - 38,
            260,
            54,
            leaves[0],
            fill=COLORS["white"],
            stroke=COLORS["agent_stroke"],
            size=18,
            radius=14,
        )
        for i, leaf in enumerate(leaves[1:]):
            ly = y + 35 + i * 58
            c.box(
                x + 360,
                ly,
                260,
                48,
                leaf,
                fill="#ffffff",
                stroke=COLORS["agent_stroke"],
                size=17,
                radius=14,
            )
            c.arrow(x + 250, y + 31, x + 360, ly + 24)
        c.arrow(x + 250, y + 31, x + 360, y - 11)

    c.arrow(605, 283, 785, 211, label="局部展开")
    c.arrow(605, 367, 785, 436)
    c.arrow(605, 451, 785, 661)
    return c


def render_region_hierarchy_partial() -> SvgCanvas:
    c = SvgCanvas()
    c.panel(80, 95, 820, 820, "地理邻近层级", COLORS["data"], COLORS["data_stroke"])
    c.box(
        385,
        175,
        210,
        64,
        "全国",
        fill=COLORS["white"],
        stroke=COLORS["data_stroke"],
        size=21,
    )
    geo_blocks = [
        (160, 320, "华东", ["浙江", "江苏", "上海", "安徽"]),
        (385, 320, "华北", ["北京", "天津", "河北"]),
        (610, 320, "华南 / 华中", ["广东", "湖北", "湖南"]),
    ]
    for x, y, block, cities in geo_blocks:
        c.box(
            x,
            y,
            175,
            58,
            block,
            fill=COLORS["white"],
            stroke=COLORS["data_stroke"],
            size=19,
        )
        c.arrow(490, 239, x + 88, y)
        for idx, city in enumerate(cities):
            cy = y + 92 + idx * 58
            c.box(
                x,
                cy,
                175,
                45,
                city,
                fill="#ffffff",
                stroke=COLORS["data_stroke"],
                size=17,
                radius=13,
            )
            c.arrow(x + 88, y + 58, x + 88, cy)
    c.badge(
        245,
        835,
        "用于表达：别太远 / 江浙沪 / 华东",
        fill="#ffffff",
        stroke=COLORS["data_stroke"],
    )

    c.panel(1020, 95, 820, 820, "城市层级画像", COLORS["agent"], COLORS["agent_stroke"])
    c.box(
        1325,
        175,
        230,
        64,
        "城市发展层级",
        fill=COLORS["white"],
        stroke=COLORS["agent_stroke"],
        size=21,
    )
    tiers = [
        (1085, 320, "一线城市", ["北京", "上海", "广州", "深圳"]),
        (1315, 320, "新一线城市", ["杭州", "成都", "南京", "武汉"]),
        (1545, 320, "区域中心", ["苏州", "宁波", "合肥", "温州"]),
    ]
    for x, y, tier, cities in tiers:
        c.box(
            x,
            y,
            190,
            58,
            tier,
            fill=COLORS["white"],
            stroke=COLORS["agent_stroke"],
            size=19,
        )
        c.arrow(1440, 239, x + 95, y)
        for idx, city in enumerate(cities):
            cy = y + 92 + idx * 58
            c.box(
                x,
                cy,
                190,
                45,
                city,
                fill="#ffffff",
                stroke=COLORS["agent_stroke"],
                size=17,
                radius=13,
            )
            c.arrow(x + 95, y + 58, x + 95, cy)
    c.badge(
        1185,
        835,
        "用于表达：好城市 / 城市资源 / 发展机会",
        fill="#ffffff",
        stroke=COLORS["agent_stroke"],
    )
    return c


def render_v1_hybrid_rag_flow() -> SvgCanvas:
    c = SvgCanvas()
    c.box(
        80,
        210,
        260,
        110,
        ["用户话语", "分数 / 选科 / 地域", "专业与风险表达"],
        fill=COLORS["white"],
        stroke=COLORS["artifact_stroke"],
    )
    c.box(
        410,
        210,
        285,
        110,
        ["显式意图归一", "查询重写", "约束抽取"],
        fill=COLORS["agent"],
        stroke=COLORS["agent_stroke"],
    )
    c.box(
        765,
        105,
        310,
        110,
        ["关系库硬过滤", "分数 / 位次 / 选科 / 地域", "形成候选池"],
        fill=COLORS["data"],
        stroke=COLORS["data_stroke"],
    )
    c.box(
        765,
        315,
        310,
        110,
        ["向量召回排序", "语义相似度计算", "补充文本相关性"],
        fill=COLORS["data"],
        stroke=COLORS["data_stroke"],
    )
    c.box(
        1145,
        210,
        305,
        110,
        ["交叉编码重排", "二阶段相关性重排", "提升候选顺序"],
        fill=COLORS["agent"],
        stroke=COLORS["agent_stroke"],
    )
    c.box(
        1515,
        105,
        300,
        110,
        ["冲 / 稳 / 保分段", "分数差", "位次差"],
        fill=COLORS["bench"],
        stroke=COLORS["bench_stroke"],
    )
    c.box(
        1515,
        315,
        300,
        110,
        ["候选列表与解释", "基线结果", "风险分段"],
        fill=COLORS["artifact"],
        stroke=COLORS["artifact_stroke"],
    )
    c.box(
        660,
        645,
        600,
        120,
        [
            "工程边界",
            "检索分数服务于材料/候选排序",
            "不选择下一轮探测轴，也不更新隐性权重",
        ],
        fill=COLORS["hidden"],
        stroke=COLORS["hidden_stroke"],
        size=22,
    )

    c.arrow(340, 265, 410, 265)
    c.arrow(695, 265, 765, 160, label="结构化条件")
    c.arrow(695, 265, 765, 370, label="语义条件")
    c.arrow(1075, 160, 1145, 265)
    c.arrow(1075, 370, 1145, 265)
    c.arrow(1450, 265, 1515, 160)
    c.arrow(1450, 265, 1515, 370)
    c.polyline(
        [(1665, 425), (1665, 575), (960, 575), (960, 645)],
        dashed=True,
        label="对照基线",
    )
    return c


def render_database_physical_schema() -> SvgCanvas:
    c = SvgCanvas()
    c.panel(70, 100, 510, 760, "基础事实表", COLORS["data"], COLORS["data_stroke"])
    c.box(
        115,
        190,
        420,
        95,
        ["院校与专业维表", "学校属性 / 专业代码", "层次与基础身份"],
        fill=COLORS["white"],
        stroke=COLORS["data_stroke"],
        size=20,
    )
    c.box(
        115,
        340,
        420,
        110,
        ["录取分数事实表", "年份 / 最低分 / 最低位次", "院校与专业关联"],
        fill=COLORS["white"],
        stroke=COLORS["data_stroke"],
        size=20,
    )
    c.box(
        115,
        510,
        420,
        110,
        ["招生计划事实表", "计划数 / 学费", "选科要求"],
        fill=COLORS["white"],
        stroke=COLORS["data_stroke"],
        size=20,
    )
    c.box(
        115,
        680,
        420,
        95,
        ["分数位次与批次线", "位次换算", "录取边界参照"],
        fill=COLORS["white"],
        stroke=COLORS["data_stroke"],
        size=20,
    )

    c.panel(
        705, 100, 510, 760, "标准化证据画像", COLORS["agent"], COLORS["agent_stroke"]
    )
    c.box(
        750,
        190,
        420,
        105,
        ["选科要求画像", "标准化选科集合", "支持快速匹配"],
        fill=COLORS["white"],
        stroke=COLORS["agent_stroke"],
        size=20,
    )
    c.box(
        750,
        360,
        420,
        120,
        ["学校-专业质量画像", "质量分与质量层级", "证据来源可追溯"],
        fill=COLORS["white"],
        stroke=COLORS["agent_stroke"],
        size=20,
    )
    c.box(
        750,
        550,
        420,
        120,
        ["专业就业结果画像", "就业结果分层", "薪资 / 岗位 / 行业证据"],
        fill=COLORS["white"],
        stroke=COLORS["agent_stroke"],
        size=20,
    )
    c.box(
        750,
        735,
        420,
        70,
        ["专业树 / 地域树", "分阶段放宽目标"],
        fill=COLORS["white"],
        stroke=COLORS["agent_stroke"],
        size=20,
    )

    c.panel(
        1340,
        100,
        510,
        760,
        "文本知识库与索引",
        COLORS["artifact"],
        COLORS["artifact_stroke"],
    )
    c.box(
        1385,
        190,
        420,
        115,
        ["文本材料库", "材料类型 / 正文 / 元数据", "向量表示"],
        fill=COLORS["white"],
        stroke=COLORS["artifact_stroke"],
        size=20,
    )
    c.box(
        1385,
        395,
        420,
        105,
        ["向量近邻索引", "余弦相似度", "近似检索加速"],
        fill=COLORS["white"],
        stroke=COLORS["artifact_stroke"],
        size=20,
    )
    c.box(
        1385,
        605,
        420,
        120,
        ["数据库连接池", "异步连接复用", "结构化查询封装"],
        fill=COLORS["white"],
        stroke=COLORS["artifact_stroke"],
        size=20,
    )

    c.arrow(535, 395, 750, 242, label="选科/硬约束")
    c.arrow(535, 565, 750, 420, label="学费与质量")
    c.arrow(1170, 420, 1385, 248, label="解释材料")
    c.arrow(1170, 610, 1385, 450, label="向量索引")
    return c


def render_runtime_state_machine() -> SvgCanvas:
    c = SvgCanvas()
    nodes = [
        (90, 190, "开始", "接收用户话语"),
        (360, 190, "语义归一", "查询重写 / 偏好轴"),
        (720, 190, "约束解析", "显式约束 / 基线候选"),
        (1080, 190, "主动探测规划", "探针计划 / 候选机会"),
        (1440, 190, "证据谈判", "边际替代问题"),
        (1440, 520, "偏好后验追踪", "权重 / 方差"),
        (1080, 520, "继续探测判定", "下一探针或停止"),
        (720, 520, "生成报告", "最终推荐"),
        (360, 520, "结束", "输出回答"),
    ]
    for x, y, title, subtitle in nodes:
        fill = (
            COLORS["artifact"]
            if title in {"开始", "结束", "生成报告"}
            else COLORS["agent"]
        )
        stroke = (
            COLORS["artifact_stroke"]
            if title in {"开始", "结束", "生成报告"}
            else COLORS["agent_stroke"]
        )
        c.box(
            x,
            y,
            260,
            100,
            [title, subtitle],
            fill=fill,
            stroke=stroke,
            size=18,
        )

    c.box(
        1505,
        360,
        300,
        90,
        ["暂停提问", "等待用户回答"],
        fill=COLORS["hidden"],
        stroke=COLORS["hidden_stroke"],
        size=20,
    )
    c.box(
        90,
        720,
        660,
        90,
        ["运行时状态", "消息 / 约束 / 隐性权重 / 方差 / 最新候选差异"],
        fill=COLORS["data"],
        stroke=COLORS["data_stroke"],
        size=20,
    )
    c.box(
        930,
        720,
        660,
        90,
        ["路由条件", "缺少约束则结束；收到反馈则更新；收敛后报告"],
        fill=COLORS["data"],
        stroke=COLORS["data_stroke"],
        size=20,
    )

    c.arrow(350, 240, 360, 240)
    c.arrow(620, 240, 720, 240)
    c.arrow(980, 240, 1080, 240)
    c.arrow(1340, 240, 1440, 240)
    c.arrow(1570, 290, 1570, 360)
    c.arrow(1570, 450, 1570, 520, label="恢复执行")
    c.arrow(1440, 570, 1340, 570)
    c.arrow(1080, 570, 980, 570)
    c.arrow(720, 570, 620, 570)
    c.polyline([(1210, 520), (1210, 380), (1210, 290)], dashed=True, label="继续探测")
    c.polyline([(850, 290), (850, 480), (720, 520)], dashed=True, label="停止")
    c.arrow(420, 720, 540, 620, dashed=True)
    c.arrow(1260, 720, 1260, 620, dashed=True)
    return c


def render_ucb_dispatch() -> SvgCanvas:
    c = SvgCanvas()
    c.box(
        80,
        170,
        310,
        120,
        ["读取后验状态", "隐性权重", "不确定性方差"],
        fill=COLORS["data"],
        stroke=COLORS["data_stroke"],
    )
    c.box(
        465,
        170,
        310,
        120,
        ["计算 UCB 分数", "权重均值 + 方差奖励", "五类偏好维度"],
        fill=COLORS["agent"],
        stroke=COLORS["agent_stroke"],
        size=20,
    )
    c.box(
        850,
        170,
        310,
        120,
        ["选择探测维度", "结合查询上下文打破并列", "确定下一轮目标"],
        fill=COLORS["agent"],
        stroke=COLORS["agent_stroke"],
        size=20,
    )
    c.box(
        1235,
        170,
        310,
        120,
        ["映射确定性探针", "学校层次 -> 实力探针", "专业/地域 -> 联合探针"],
        fill=COLORS["agent"],
        stroke=COLORS["agent_stroke"],
        size=20,
    )
    c.box(
        1515,
        380,
        310,
        120,
        ["强制纳入目标探针", "规划器必须包含目标", "语言模型不能绕过"],
        fill=COLORS["hidden"],
        stroke=COLORS["hidden_stroke"],
        size=20,
    )
    c.box(
        1135,
        380,
        310,
        120,
        ["运行证据探针", "SQL / 本体 / 画像", "返回真实候选"],
        fill=COLORS["data"],
        stroke=COLORS["data_stroke"],
        size=20,
    )
    c.box(
        755,
        380,
        310,
        120,
        ["选择最大分歧候选对", "最大化特征差异", "避免重复追问"],
        fill=COLORS["agent"],
        stroke=COLORS["agent_stroke"],
        size=20,
    )
    c.box(
        375,
        380,
        310,
        120,
        ["提出边际替代问题", "A/B 候选对", "等待用户反馈"],
        fill=COLORS["artifact"],
        stroke=COLORS["artifact_stroke"],
        size=20,
    )
    c.box(
        80,
        600,
        355,
        120,
        ["应用反馈更新", "接受/拒绝更新权重", "犹豫则提高方差"],
        fill=COLORS["agent"],
        stroke=COLORS["agent_stroke"],
        size=20,
    )
    c.box(
        620,
        600,
        540,
        120,
        ["收敛判定", "总方差足够小或轮次达到上限", "进入最终报告"],
        fill=COLORS["artifact"],
        stroke=COLORS["artifact_stroke"],
        size=20,
    )

    c.arrow(390, 230, 465, 230)
    c.arrow(775, 230, 850, 230)
    c.arrow(1160, 230, 1235, 230)
    c.polyline([(1545, 230), (1670, 230), (1670, 380)])
    c.arrow(1515, 440, 1445, 440)
    c.arrow(1135, 440, 1065, 440)
    c.arrow(755, 440, 685, 440)
    c.polyline([(375, 440), (255, 440), (255, 600)])
    c.arrow(435, 660, 620, 660)
    c.polyline(
        [(255, 600), (255, 535), (235, 535), (235, 290)], dashed=True, label="后验循环"
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
    svg_uri = svg_path.resolve().as_uri()
    png_target = png_path.resolve()
    before_mtime = png_target.stat().st_mtime if png_target.exists() else None
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
                f"--screenshot={png_target}",
                svg_uri,
            ],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    if not png_target.exists():
        raise RuntimeError(f"PNG export failed: {png_target} was not created")
    after_mtime = png_target.stat().st_mtime
    if before_mtime is not None and after_mtime <= before_mtime:
        raise RuntimeError(f"PNG export failed: {png_target} was not updated")


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
        "fig_4_4_major_tree_partial": render_major_tree_partial(),
        "fig_4_5_region_hierarchy_partial": render_region_hierarchy_partial(),
        "fig_3_1_v1_hybrid_rag_flow": render_v1_hybrid_rag_flow(),
        "fig_4_6_database_physical_schema": render_database_physical_schema(),
        "fig_5_2_runtime_state_machine": render_runtime_state_machine(),
        "fig_5_3_ucb_dispatch": render_ucb_dispatch(),
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
