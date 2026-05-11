"""Render thesis box diagrams with academic terminology.

This manual artifact generator does not read benchmark hidden fields, connect to
PostgreSQL, call an LLM, or rerun any experiment. It only turns the current
thesis figure plan into reproducible SVG/PNG diagrams.
"""

from __future__ import annotations

import argparse
import os
import shutil
import sys
from pathlib import Path
from typing import Any


FIGURE_FORMATS = ("png", "svg")
REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_OUTPUT_DIR = REPO_ROOT / "gaokaollm_bench" / "outputs" / "thesis_figures"

FONT = "Microsoft YaHei"
DATA_COLOR = "#d9ecff"
AGENT_COLOR = "#dcf5e5"
BENCH_COLOR = "#eadfff"
ARTIFACT_COLOR = "#eeeeee"
HIDDEN_COLOR = "#fff1cc"
EDGE_COLOR = "#5f6f7d"

GRAPH_ATTR = {
    "bgcolor": "white",
    "fontname": FONT,
    "fontsize": "18",
    "label": "",
    "nodesep": "0.48",
    "pad": "0.24",
    "ranksep": "0.72",
    "splines": "ortho",
}
NODE_ATTR = {
    "color": "#7a8a99",
    "fontname": FONT,
    "fontsize": "13",
    "margin": "0.12,0.08",
    "penwidth": "1.3",
    "shape": "box",
    "style": "rounded,filled",
}
EDGE_ATTR = {
    "arrowsize": "0.7",
    "color": EDGE_COLOR,
    "fontname": FONT,
    "fontsize": "11",
    "penwidth": "1.15",
}


def _load_diagrams() -> tuple[Any, Any, Any, Any]:
    """Import diagrams lazily so py_compile works without optional deps."""
    missing: list[str] = []
    _ensure_dot_on_path()
    if shutil.which("dot") is None:
        missing.append("Graphviz `dot` executable")

    try:
        from diagrams import Cluster, Diagram, Edge, Node
    except ImportError as exc:
        missing.append("Python package `diagrams`")
        raise RuntimeError(_missing_dependency_message(missing)) from exc

    if missing:
        raise RuntimeError(_missing_dependency_message(missing))

    return Diagram, Cluster, Edge, Node


def _ensure_dot_on_path() -> None:
    """Add a discovered Graphviz bin directory to PATH when dot is not exposed."""
    if shutil.which("dot") is not None:
        return

    for candidate in _candidate_dot_paths():
        if candidate.exists():
            os.environ["PATH"] = (
                f"{candidate.parent}{os.pathsep}{os.environ.get('PATH', '')}"
            )
            return


def _candidate_dot_paths() -> list[Path]:
    candidates: list[Path] = []
    graphviz_dot = os.environ.get("GRAPHVIZ_DOT")
    graphviz_bin = os.environ.get("GRAPHVIZ_BIN")
    if graphviz_dot:
        candidates.append(Path(graphviz_dot))
    if graphviz_bin:
        candidates.append(Path(graphviz_bin) / "dot.exe")

    candidates.extend(
        [
            Path(sys.prefix) / "Library" / "bin" / "dot.exe",
            Path("C:/Program Files/Graphviz/bin/dot.exe"),
            Path("C:/Program Files (x86)/Graphviz/bin/dot.exe"),
            Path("C:/ProgramData/Anaconda3/envs/gaokao_pg/Library/bin/dot.exe"),
            Path("C:/ProgramData/Anaconda3/envs/yasi/Library/bin/dot.exe"),
        ]
    )

    conda_pkgs = Path("C:/ProgramData/Anaconda3/pkgs")
    if conda_pkgs.exists():
        candidates.extend(conda_pkgs.glob("graphviz-*/Library/bin/dot.exe"))

    return candidates


def _missing_dependency_message(missing: list[str]) -> str:
    missing_text = ", ".join(dict.fromkeys(missing))
    return (
        f"Missing optional diagram runtime dependency: {missing_text}.\n"
        "Install Graphviz and Diagrams, for example:\n"
        "  conda install -n gaokao_pg -c conda-forge graphviz\n"
        "  C:\\ProgramData\\Anaconda3\\envs\\gaokao_pg\\python.exe -m pip install -r requirements-diagrams.txt\n"
        "Alternatively set GRAPHVIZ_BIN to a directory that contains dot.exe.\n"
        "Then verify `dot -V` works before rerunning this script."
    )


def _diagram_context(name: str, output_dir: Path, direction: str = "LR"):
    Diagram, _, _, _ = _load_diagrams()
    return Diagram(
        "",
        filename=str(output_dir / name),
        show=False,
        outformat=list(FIGURE_FORMATS),
        direction=direction,
        graph_attr=GRAPH_ATTR,
        node_attr=NODE_ATTR,
        edge_attr=EDGE_ATTR,
    )


def _cluster(label: str, fillcolor: str, direction: str = "LR"):
    _, Cluster, _, _ = _load_diagrams()
    return Cluster(
        label,
        direction=direction,
        graph_attr={
            "color": "#9aa9b5",
            "fillcolor": fillcolor,
            "fontname": FONT,
            "fontsize": "15",
            "labeljust": "l",
            "margin": "14",
            "penwidth": "1.2",
            "style": "rounded,filled",
        },
    )


def _node(
    label: str,
    fillcolor: str = "white",
    *,
    color: str = "#7a8a99",
    shape: str = "box",
    width: str = "1.95",
):
    _, _, _, Node = _load_diagrams()
    return Node(
        label,
        color=color,
        fillcolor=fillcolor,
        fixedsize="false",
        height="0.72",
        image="",
        labelloc="c",
        margin="0.15,0.10",
        shape=shape,
        style="rounded,filled",
        width=width,
    )


def _data(label: str):
    return _node(label, DATA_COLOR)


def _agent(label: str):
    return _node(label, AGENT_COLOR, color="#6a9b78")


def _benchmark(label: str):
    return _node(label, BENCH_COLOR, color="#8d7eb3")


def _artifact(label: str):
    return _node(label, ARTIFACT_COLOR, color="#888888")


def _hidden(label: str):
    return _node(label, HIDDEN_COLOR, color="#c28b2c")


def render_system_architecture(output_dir: Path) -> None:
    _, _, Edge, _ = _load_diagrams()
    with _diagram_context("fig_4_1_system_architecture", output_dir):
        with _cluster("数据层：可核验事实与标准化证据", DATA_COLOR):
            facts = _data("招生事实库\n分数 / 位次 / 选科 / 学费")
            ontology = _data("层级本体与画像\n专业层级本体\n经审校的地域层级画像")
            profiles = _data("质量与就业画像\n学校-专业质量\n专业就业结果")
            facts >> ontology >> profiles

        with _cluster("Agent 层：轻量多角色工作流", AGENT_COLOR):
            parser = _agent("约束解析器\nConstraint Parser")
            detector = _agent("机会探测器\nOpportunity Detector")
            negotiator = _agent("证据谈判器\nEvidence Negotiator")
            parser >> detector >> negotiator

        with _cluster("Benchmark 层：交互式偏好启发评测", BENCH_COLOR):
            bench = _benchmark("冰山用户画像\n多轮用户模拟\n事实/过程联合评价")
            stress = _benchmark("多轴隐藏妥协\n压力测试")
            bench >> stress

        with _cluster("论文产物层：可复核材料", ARTIFACT_COLOR):
            outputs = _artifact("聚合指标\n逐例证据\n论文图表")

        facts >> Edge(label="硬约束事实") >> parser
        ontology >> Edge(label="可谈判偏好轴") >> detector
        profiles >> Edge(label="收益证据") >> negotiator
        negotiator >> Edge(label="证据链") >> bench
        stress >> Edge(label="结果与失败分析") >> outputs


def render_mas_workflow(output_dir: Path) -> None:
    _, _, Edge, _ = _load_diagrams()
    with _diagram_context("fig_5_1_mas_workflow", output_dir):
        user = _node("用户显式需求\n分数 / 专业 / 地域 / 风险 / 预算", "#ffffff")

        with _cluster("业务 Agent：约束解析 -> 机会探测 -> 证据谈判", AGENT_COLOR):
            parser = _agent("约束解析器\nCoT 重写 + 实体校验\nSQL 硬约束锁定")
            baseline = _agent("硬约束基线\n只返回显式约束内结果")
            detector = _agent("机会探测器\n单变量 Delta Analysis\nBoundary Exploration")
            axes = _agent(
                "可谈判偏好轴\n专业-地域 / 风险组合\n预算 / 质量 / 就业 / 地域层级"
            )
            negotiator = _agent("证据谈判器\n候选重排\n二选一偏好启发")
            parser >> detector >> axes >> negotiator
            parser >> baseline >> Edge(label="对照") >> negotiator

        reply = _artifact("面向用户的谈判回复\n保留什么 / 放宽什么 / 换来什么")
        state = _artifact("状态记录\n机会集合 / 推荐候选 / 证据来源")

        user >> parser
        negotiator >> reply
        negotiator >> state


def render_benchmark_flow(output_dir: Path) -> None:
    _, _, Edge, _ = _load_diagrams()
    with _diagram_context("fig_4_2_benchmark_flow", output_dir):
        gap = _data("真实数据库 gap\n基线集合 vs 放宽集合")
        persona = _benchmark("冰山用户画像")
        visible = _benchmark("显性需求\n生成用户话语")
        simulator = _benchmark("用户模拟器\n多轮交互")
        target = _agent("被测 Agent\n证据谈判 Agent / 硬约束基线")
        transcript = _artifact("对话记录\n回复 + 状态")
        judge = _benchmark("评测器\n事实命中 + 过程检查")
        summary = _artifact("聚合结果\n逐例证据")
        hidden = _hidden("隐藏偏好与可接受集合\n仅评测端可见")

        gap >> persona >> visible >> simulator >> target >> transcript >> judge
        judge >> summary
        persona >> Edge(style="dashed", label="不进入 Agent 输入") >> hidden
        hidden >> Edge(style="dashed", label="判定隐藏妥协") >> judge


def render_data_evidence_mapping(output_dir: Path) -> None:
    _, _, Edge, _ = _load_diagrams()
    with _diagram_context("fig_4_3_data_evidence_relax_mapping", output_dir):
        with _cluster("证据族：从原始事实到标准化画像", DATA_COLOR, direction="TB"):
            admissions = _data("招生事实\n最低分 / 位次 / 选科")
            major_tree = _data("专业层级本体\n人工骨架 + 规则挂载\n模型辅助候选 + 审校")
            risk = _data("风险证据\n分差 / 位次差")
            tuition = _data("成本证据\n学费与预算差")
            quality = _data("专业质量画像\n排名 / 评估 / 特色")
            employment = _data("就业结果画像\n就业排名 / 行业 / 薪资")
            region = _data("地域层级画像\n地理板块 / 城市层级\n偏好显性化工具")

        with _cluster("放宽动作：可谈判偏好轴", AGENT_COLOR, direction="TB"):
            major_geo = _agent("专业-地域联合放宽\nStaged Relaxation")
            risk_band = _agent("风险组合放宽\n冲 / 稳 / 保")
            tuition_value = _agent("预算性价比放宽\n小幅超预算")
            major_quality = _agent("专业质量放宽\n质量收益证据")
            employment_outcome = _agent("就业导向放宽\n结果证据")
            region_tree = _agent("地域层级放宽\n不直接计入城市收益")

        admissions >> Edge(label="可达性锁定") >> major_geo
        major_tree >> Edge(label="同叶子 / 同父类") >> major_geo
        risk >> Edge(label="风险分层") >> risk_band
        tuition >> Edge(label="学费增量") >> tuition_value
        quality >> Edge(label="质量增益") >> major_quality
        employment >> Edge(label="结果增益") >> employment_outcome
        region >> Edge(label="地域证据") >> region_tree


def render_all(output_dir: Path) -> list[Path]:
    _load_diagrams()
    output_dir.mkdir(parents=True, exist_ok=True)
    render_system_architecture(output_dir)
    render_mas_workflow(output_dir)
    render_benchmark_flow(output_dir)
    render_data_evidence_mapping(output_dir)
    return [
        output_dir / f"{stem}.{fmt}"
        for stem in (
            "fig_4_1_system_architecture",
            "fig_5_1_mas_workflow",
            "fig_4_2_benchmark_flow",
            "fig_4_3_data_evidence_relax_mapping",
        )
        for fmt in FIGURE_FORMATS
    ]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Render clean thesis box diagrams as SVG/PNG.",
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
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    print("Rendered thesis diagrams:")
    for path in files:
        print(f"  {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
