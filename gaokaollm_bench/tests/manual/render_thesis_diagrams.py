"""Render thesis architecture figures with mingrammer/diagrams.

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

GRAPH_ATTR = {
    "fontsize": "20",
    "pad": "0.35",
    "splines": "ortho",
    "nodesep": "0.65",
    "ranksep": "0.9",
}
NODE_ATTR = {
    "fontsize": "13",
    "shape": "box",
    "style": "rounded",
}
EDGE_ATTR = {
    "fontsize": "11",
}


def _load_diagrams() -> tuple[Any, Any, Any, dict[str, Any]]:
    """Import diagrams lazily so py_compile works without optional deps."""
    missing: list[str] = []
    _ensure_dot_on_path()
    if shutil.which("dot") is None:
        missing.append("Graphviz `dot` executable")

    try:
        from diagrams import Cluster, Diagram, Edge
        from diagrams.generic.blank import Blank
        from diagrams.generic.database import SQL
        from diagrams.generic.storage import Storage
        from diagrams.onprem.client import User
        from diagrams.onprem.compute import Server
        from diagrams.onprem.database import PostgreSQL
        from diagrams.programming.language import Latex, Python
    except ImportError as exc:
        missing.append("Python package `diagrams`")
        message = _missing_dependency_message(missing)
        raise RuntimeError(message) from exc

    if missing:
        raise RuntimeError(_missing_dependency_message(missing))

    nodes = {
        "Latex": Latex,
        "Blank": Blank,
        "PostgreSQL": PostgreSQL,
        "Python": Python,
        "Server": Server,
        "SQL": SQL,
        "Storage": Storage,
        "User": User,
    }
    return Diagram, Cluster, Edge, nodes


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


def _diagram_context(
    name: str,
    output_dir: Path,
    direction: str = "LR",
):
    Diagram, _, _, _ = _load_diagrams()
    return Diagram(
        name,
        filename=str(output_dir / name),
        show=False,
        outformat=list(FIGURE_FORMATS),
        direction=direction,
        graph_attr=GRAPH_ATTR,
        node_attr=NODE_ATTR,
        edge_attr=EDGE_ATTR,
    )


def render_system_architecture(output_dir: Path) -> None:
    _, Cluster, Edge, nodes = _load_diagrams()
    User = nodes["User"]
    PostgreSQL = nodes["PostgreSQL"]
    Python = nodes["Python"]
    Server = nodes["Server"]
    SQL = nodes["SQL"]
    Storage = nodes["Storage"]
    with _diagram_context("fig_4_1_system_architecture", output_dir):
        user = User("Candidate /\nSimulated user")

        with Cluster("Data contribution"):
            admissions = PostgreSQL("PostgreSQL\nadmission facts")
            profiles = SQL("quality +\nemployment profiles")
            reviewed_trees = Storage("major + region\ntrees")
            evidence_layer = Server("evidence layer\nSQL + artifacts")
            [admissions, profiles, reviewed_trees] >> evidence_layer

        with Cluster("Light MAS Agent"):
            gatekeeper = Python("gatekeeper\nexplicit constraints")
            radar = Python("radar\nSQL probes")
            negotiator = Python("negotiator\nevidence dialogue")
            gatekeeper >> radar >> negotiator

        with Cluster("Benchmark contribution"):
            persona = User("Iceberg\npersonas")
            sandbox = Server("multi-turn sandbox\napp vs baseline")
            judge = Python("factual +\nprocess judge")
            persona >> sandbox >> judge

        with Cluster("Thesis artifacts"):
            artifacts = Storage("summary / reports\ncase evidence")
            figures = nodes["Latex"]("figures /\ntables")
            artifacts >> figures

        user >> Edge(label="utterances") >> gatekeeper
        evidence_layer >> Edge(label="facts + standardized signals") >> radar
        evidence_layer >> Edge(label="real DB gaps") >> persona
        negotiator >> Edge(label="auditable reply + state") >> sandbox
        judge >> Edge(label="metrics + transcripts") >> artifacts


def render_mas_workflow(output_dir: Path) -> None:
    _, Cluster, Edge, nodes = _load_diagrams()
    Python = nodes["Python"]
    Server = nodes["Server"]
    Storage = nodes["Storage"]
    User = nodes["User"]
    Blank = nodes["Blank"]
    with _diagram_context("fig_5_1_mas_workflow", output_dir):
        user = User("Explicit user\nutterances")
        gatekeeper = Python("gatekeeper\nconstraint extraction")
        baseline = Storage("hard-constraint\nbaseline")
        radar = Python("radar\nopportunity probes")
        opportunity_set = Blank(
            "Pareto opportunity set\n"
            "major_geo_relax\n"
            "risk_band_relax\n"
            "strength_relax\n"
            "tuition_value_relax\n"
            "major_quality_relax\n"
            "employment_outcome_relax\n"
            "region_tree_relax"
        )
        negotiator = Python("negotiator\nevidence synthesis")
        reply = Server("Pareto negotiation\nreply")
        state = Storage("internal_state\nopportunities + recs")

        user >> gatekeeper
        gatekeeper >> baseline
        gatekeeper >> radar
        baseline >> Edge(label="contrast") >> radar
        radar >> opportunity_set >> negotiator
        baseline >> negotiator
        negotiator >> reply
        negotiator >> state


def render_benchmark_flow(output_dir: Path) -> None:
    _, Cluster, Edge, nodes = _load_diagrams()
    PostgreSQL = nodes["PostgreSQL"]
    Python = nodes["Python"]
    Server = nodes["Server"]
    Storage = nodes["Storage"]
    User = nodes["User"]
    with _diagram_context("fig_4_2_benchmark_flow", output_dir):
        db_gap = PostgreSQL("Real DB gap\nbaseline vs relaxed")
        generator = Python("Persona\ngenerator")
        persona = User("Iceberg persona")
        explicit = Storage("Explicit\nred lines")
        hidden = Storage("Hidden ground truth\nnot given to target")
        simulator = Server("Simulator\nmulti-turn user")
        target = Server("Target agent\napp_pareto / hard_constraint")
        transcript = Storage("Transcript\nturns + state")
        factual = Python("Deterministic\nfactual judge")
        process = Python("Process judge\nelicitation + gain")
        report = Storage("reports/*.jsonl")
        summary = Storage("summary +\nevidence docs")

        db_gap >> generator >> persona
        persona >> explicit >> simulator
        persona >> hidden >> process
        simulator >> target >> transcript
        transcript >> factual >> report
        transcript >> process >> report
        report >> summary

        explicit >> Edge(label="visible only") >> target
        hidden >> Edge(label="evaluator only", style="dashed") >> process


def render_data_evidence_mapping(output_dir: Path) -> None:
    _, Cluster, Edge, nodes = _load_diagrams()
    PostgreSQL = nodes["PostgreSQL"]
    Python = nodes["Python"]
    SQL = nodes["SQL"]
    Storage = nodes["Storage"]
    with _diagram_context("fig_4_3_data_evidence_relax_mapping", output_dir):
        with Cluster("Evidence bundles"):
            admissions = PostgreSQL(
                "Admission facts\nadmission_scores\nschool scores\nrank / batch"
            )
            cost = SQL("Cost facts\nadmission_plans.tuition")
            quality = SQL("Major quality\nquality profiles")
            employment = SQL("Employment outcomes\noutcome profiles")
            hierarchy = Storage(
                "Hierarchical evidence\nmajor_tree reviewed\nregion trees reviewed v1"
            )

        with Cluster("Relax capability families"):
            admission_relax = Python(
                "Admission-backed relax\nmajor_geo_relax\nrisk_band_relax\nstrength_relax"
            )
            cost_relax = Python("Cost relax\ntuition_value_relax")
            quality_relax = Python("Quality relax\nmajor_quality_relax")
            employment_relax = Python("Outcome relax\nemployment_outcome_relax")
            region_relax = Python(
                "Region relax\nregion_tree_relax\ngeo_block / urban_tier"
            )

        admissions >> Edge(label="score / rank") >> admission_relax
        cost >> Edge(label="tuition delta") >> cost_relax
        quality >> Edge(label="quality score") >> quality_relax
        employment >> Edge(label="outcome score") >> employment_relax
        hierarchy >> Edge(label="staged relaxation") >> admission_relax
        hierarchy >> Edge(label="nearby majors") >> employment_relax
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
        description="Render thesis architecture diagrams as SVG/PNG.",
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
