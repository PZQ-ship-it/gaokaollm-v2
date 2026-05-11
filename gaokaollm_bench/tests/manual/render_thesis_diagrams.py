"""Render clean thesis box diagrams with mingrammer/diagrams.

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
    "pad": "0.25",
    "ranksep": "0.75",
    "nodesep": "0.5",
    "splines": "ortho",
}
NODE_ATTR = {
    "fontname": FONT,
    "fontsize": "13",
    "margin": "0.12,0.08",
    "shape": "box",
    "style": "rounded,filled",
    "color": "#7a8a99",
    "penwidth": "1.3",
}
EDGE_ATTR = {
    "color": EDGE_COLOR,
    "fontname": FONT,
    "fontsize": "11",
    "arrowsize": "0.7",
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
        message = _missing_dependency_message(missing)
        raise RuntimeError(message) from exc

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
        with _cluster("数据层：可核验证据", DATA_COLOR):
            data = _data(
                "PostgreSQL 招生事实\n"
                "专业树 / 地域树 reviewed v1\n"
                "学费 / 质量 / 就业标准化层"
            )

        with _cluster("Agent 层：轻量 MAS", AGENT_COLOR):
            gatekeeper = _agent("gatekeeper\n显式约束抽取")
            radar = _agent("radar\nSQL probe / opportunity")
            negotiator = _agent("negotiator\n证据组织与谈判")
            gatekeeper >> radar >> negotiator

        with _cluster("Benchmark 层：多轮评测", BENCH_COLOR):
            bench = _benchmark(
                "冰山画像 + simulator\n"
                "app_pareto vs hard_constraint\n"
                "事实 / 过程联合评价"
            )

        with _cluster("论文产物层", ARTIFACT_COLOR):
            outputs = _artifact("summary / transcripts / evidence\nSVG / PNG 图表素材")

        data >> Edge(label="事实证据") >> gatekeeper
        data >> Edge(label="真实 DB gap") >> bench
        negotiator >> Edge(label="可审计回复") >> bench
        bench >> Edge(label="指标与逐例证据") >> outputs


def render_mas_workflow(output_dir: Path) -> None:
    _, _, Edge, _ = _load_diagrams()
    with _diagram_context("fig_5_1_mas_workflow", output_dir):
        user = _node("用户显式话语\n分数 / 专业 / 地域 / 风险等", "#ffffff")

        with _cluster("业务 Agent：gatekeeper -> radar -> negotiator", AGENT_COLOR):
            gatekeeper = _agent("gatekeeper\n抽取显式约束")
            baseline = _agent("hard-constraint\nbaseline")
            radar = _agent("radar\n探测 Pareto 机会")
            opportunities = _agent(
                "opportunities\n"
                "major_geo / risk_band / strength\n"
                "tuition / quality / employment\n"
                "region_tree"
            )
            negotiator = _agent("negotiator\n组织证据与话术")
            gatekeeper >> radar >> opportunities >> negotiator
            gatekeeper >> baseline >> Edge(label="对照") >> negotiator

        reply = _artifact("面向用户的谈判回复")
        state = _artifact("internal_state\nopportunities / recommended_schools")

        user >> gatekeeper
        negotiator >> reply
        negotiator >> state


def render_benchmark_flow(output_dir: Path) -> None:
    _, _, Edge, _ = _load_diagrams()
    with _diagram_context("fig_4_2_benchmark_flow", output_dir):
        db_gap = _data("真实 DB gap\nbaseline vs relaxed")
        persona = _benchmark("冰山画像 persona")
        explicit = _benchmark("显式红线\n给 simulator")
        simulator = _benchmark("simulator\n多轮用户")
        target = _agent("target agent\napp_pareto / hard_constraint")
        transcript = _artifact("transcript\nturns + internal_state")
        judge = _benchmark("deterministic judge\n事实 + 过程")
        summary = _artifact("summary / report / evidence")

        hidden = _hidden("hidden ground truth\nimplicit_flexibilities\nvolunteer_set")

        db_gap >> persona >> explicit >> simulator >> target >> transcript >> judge
        judge >> summary
        persona >> Edge(style="dashed", label="仅 evaluator 可见") >> hidden
        hidden >> Edge(style="dashed", label="判定隐藏妥协") >> judge


def render_data_evidence_mapping(output_dir: Path) -> None:
    _, _, Edge, _ = _load_diagrams()
    with _diagram_context("fig_4_3_data_evidence_relax_mapping", output_dir):
        with _cluster("证据族", DATA_COLOR, direction="TB"):
            admissions = _data("招生事实\n最低分 / 位次 / 批次线")
            hierarchy = _data("层级本体\n专业树 / 地域树 reviewed v1")
            cost = _data("成本证据\nadmission_plans.tuition")
            quality = _data("专业质量证据\nschool_major_quality_profiles")
            employment = _data("就业结果证据\nmajor_employment_outcome_profiles")

        with _cluster("Relax 能力族", AGENT_COLOR, direction="TB"):
            admission_relax = _agent("录取与层级放宽\nmajor_geo / risk_band / strength")
            cost_relax = _agent("预算性价比\n tuition_value_relax")
            quality_relax = _agent("专业质量\nmajor_quality_relax")
            employment_relax = _agent("就业导向\nemployment_outcome_relax")
            region_relax = _agent("地域树\nregion_tree_relax\ngeo_block / urban_tier")

        admissions >> Edge(label="score / rank") >> admission_relax
        hierarchy >> Edge(label="staged relaxation") >> admission_relax
        cost >> Edge(label="tuition delta") >> cost_relax
        quality >> Edge(label="quality gain") >> quality_relax
        employment >> Edge(label="outcome gain") >> employment_relax
        hierarchy >> Edge(label="reviewed region nodes") >> region_relax


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
