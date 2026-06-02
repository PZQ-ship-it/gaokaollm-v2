from __future__ import annotations

from pathlib import Path

import pandas as pd

from app.evaluation import chapter4_c1_figures as c1fig


OUTPUT_DIR = Path("tmp/chapter4_c1_c6_average_preview")
GENERATED_DIR = OUTPUT_DIR / "_generated"
BASELINE_CSV = Path(
    "app/evaluation/results/preview_c1_c6_average_baseline_comparable.csv"
)
ABLATION_CSV = Path("app/evaluation/results/preview_c1_c6_average_ablation.csv")
PROCESS_MODE_CSV = Path(
    "app/evaluation/results/preview_c1_c6_average_process_by_mode.csv"
)
PROCESS_CASE_CSV = Path(
    "app/evaluation/results/preview_c1_c6_average_process_by_case.csv"
)


def main() -> None:
    c1fig.OUTPUT_DIR = GENERATED_DIR
    c1fig.METHOD_ORDER = ["app_pareto", "v1_prompt_direct"]
    c1fig.setup_style()
    baseline = pd.read_csv(BASELINE_CSV)
    ablation = pd.read_csv(ABLATION_CSV)
    process = pd.read_csv(PROCESS_MODE_CSV)
    output_dir = OUTPUT_DIR

    c1fig.figure_baseline_methods(baseline, output_dir)
    c1fig.figure_ablation_core(ablation, output_dir)
    c1fig.figure_planner_process(process, output_dir)
    c1fig.figure_negotiator_process(process, output_dir)
    c1fig.figure_tracker_process(process, output_dir)
    c1fig.write_summary(baseline, ablation, process)

    summary = OUTPUT_DIR / "preview_c1_c6_average_note.md"
    summary.write_text(
        "\n".join(
            [
                "# C1-C6 Average Preview",
                "",
                "- Baseline uses only complete comparable targets across C1-C6: `app_pareto` and `v1_prompt_direct`.",
                "- `v1_prompt_cot` is not included because C2/C4/C5/C6 do not have complete COT rows.",
                "- Ablation and process figures average complete C1-C6 rows.",
                "- These files are preview-only and are not copied into the thesis figure directory.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    print(f"wrote preview figures to {OUTPUT_DIR.resolve()}")


if __name__ == "__main__":
    main()
