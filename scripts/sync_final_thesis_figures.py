"""Sync final thesis figures into the LaTeX figure directory.

The script intentionally limits itself to figures referenced by the current
undergraduate final thesis body. Hand-authored SVG screenshots are converted to
single-page raster PDFs from their PNG copy; matplotlib figures keep their
vector PDF output.
"""

from __future__ import annotations

import argparse
import shutil
from dataclasses import dataclass
from pathlib import Path

from PIL import Image


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LATEX_ROOT = Path(r"D:\毕设\latex-for-zju-master\latex-for-zju-master")
DIAGRAM_DIR = REPO_ROOT / "gaokaollm_bench" / "outputs" / "thesis_figures"
CHAPTER6_DIR = REPO_ROOT / "tmp" / "chapter6_figures"
CHAPTER48_DIR = REPO_ROOT / "tmp" / "chapter48_microdynamics"


@dataclass(frozen=True)
class FigureSpec:
    stem: str
    source_dir: Path | None
    target_subdir: str
    copy_svg: bool = False
    copy_pdf: bool = False


FINAL_FIGURES: tuple[FigureSpec, ...] = (
    FigureSpec("agent_workflow_2", DIAGRAM_DIR, "figure", copy_svg=True),
    FigureSpec(
        "fig_3_1_system_use_cases", DIAGRAM_DIR, "figure/thesis_figures", copy_svg=True
    ),
    FigureSpec(
        "fig_4_1_system_architecture",
        DIAGRAM_DIR,
        "figure/thesis_figures",
        copy_svg=True,
    ),
    FigureSpec(
        "fig_4_6_database_physical_schema",
        DIAGRAM_DIR,
        "figure/thesis_figures",
        copy_svg=True,
    ),
    FigureSpec(
        "fig_4_4_major_tree_partial",
        DIAGRAM_DIR,
        "figure/thesis_figures",
        copy_svg=True,
    ),
    FigureSpec(
        "fig_4_5_region_hierarchy_partial",
        DIAGRAM_DIR,
        "figure/thesis_figures",
        copy_svg=True,
    ),
    FigureSpec(
        "fig_5_1_mas_workflow", DIAGRAM_DIR, "figure/thesis_figures", copy_svg=True
    ),
    FigureSpec(
        "fig_5_2_runtime_state_machine",
        DIAGRAM_DIR,
        "figure/thesis_figures",
        copy_svg=True,
    ),
    FigureSpec(
        "fig_5_3_ucb_dispatch", DIAGRAM_DIR, "figure/thesis_figures", copy_svg=True
    ),
    FigureSpec(
        "fig_4_2_benchmark_flow", DIAGRAM_DIR, "figure/thesis_figures", copy_svg=True
    ),
    FigureSpec(
        "fig_4_3_data_evidence_relax_mapping",
        DIAGRAM_DIR,
        "figure/thesis_figures",
        copy_svg=True,
    ),
    FigureSpec("fig_3_5_elicitation_console", None, "figure/thesis_figures"),
    FigureSpec("fig_3_6_final_decision_report", None, "figure/thesis_figures"),
    FigureSpec("fig_3_7_admin_trace_dashboard", None, "figure/thesis_figures"),
    FigureSpec(
        "fig_6_1_reference_baseline_metrics",
        CHAPTER6_DIR,
        "figure/thesis_figures",
        copy_pdf=True,
    ),
    FigureSpec(
        "fig_6_1_robust_main_metrics_grouped",
        CHAPTER6_DIR,
        "figure/thesis_figures",
        copy_pdf=True,
    ),
    FigureSpec(
        "fig_6_2_profile_type_breakdown",
        CHAPTER6_DIR,
        "figure/thesis_figures",
        copy_pdf=True,
    ),
    FigureSpec(
        "fig_4_8_1_uncertainty_collapse",
        CHAPTER48_DIR,
        "figure/thesis_figures",
        copy_pdf=True,
    ),
    FigureSpec(
        "fig_4_8_2_tension_information_gain",
        CHAPTER48_DIR,
        "figure/thesis_figures",
        copy_pdf=True,
    ),
    FigureSpec(
        "fig_4_8_3_belief_anchoring_decoy",
        CHAPTER48_DIR,
        "figure/thesis_figures",
        copy_pdf=True,
    ),
)


def png_to_pdf(png_path: Path, pdf_path: Path, *, dpi: float = 300.0) -> None:
    with Image.open(png_path) as image:
        if image.mode in {"RGBA", "LA"}:
            background = Image.new("RGB", image.size, "white")
            alpha = (
                image.getchannel("A") if image.mode == "RGBA" else image.getchannel(1)
            )
            background.paste(image.convert("RGB"), mask=alpha)
            output = background
        else:
            output = image.convert("RGB")
        output.save(pdf_path, "PDF", resolution=dpi)


def copy_if_present(source: Path, target: Path) -> bool:
    if not source.exists():
        return False
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)
    return True


def sync(latex_root: Path) -> list[Path]:
    written: list[Path] = []
    for spec in FINAL_FIGURES:
        target_dir = latex_root / spec.target_subdir
        target_dir.mkdir(parents=True, exist_ok=True)
        target_png = target_dir / f"{spec.stem}.png"
        target_pdf = target_dir / f"{spec.stem}.pdf"

        if spec.source_dir is not None:
            source_png = spec.source_dir / f"{spec.stem}.png"
            if not copy_if_present(source_png, target_png):
                raise FileNotFoundError(source_png)
            written.append(target_png)

            if spec.copy_svg:
                source_svg = spec.source_dir / f"{spec.stem}.svg"
                if copy_if_present(source_svg, target_dir / f"{spec.stem}.svg"):
                    written.append(target_dir / f"{spec.stem}.svg")

            if spec.copy_pdf:
                source_pdf = spec.source_dir / f"{spec.stem}.pdf"
                if not copy_if_present(source_pdf, target_pdf):
                    raise FileNotFoundError(source_pdf)
                written.append(target_pdf)
                continue

        if not target_png.exists():
            raise FileNotFoundError(target_png)
        png_to_pdf(target_png, target_pdf)
        written.append(target_pdf)

    return written


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--latex-root", type=Path, default=DEFAULT_LATEX_ROOT)
    args = parser.parse_args()

    written = sync(args.latex_root)
    for path in written:
        print(path)


if __name__ == "__main__":
    main()
