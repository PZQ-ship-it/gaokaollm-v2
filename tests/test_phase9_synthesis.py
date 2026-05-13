from pathlib import Path
import shutil

import pytest

from app.evaluation.benchmark import (
    has_valid_benchmark_rows,
    synthetic_ablation_rows,
    write_ablation_csv,
)
from app.evaluation.paper_writer import generate_paper, validate_paper
from app.evaluation.plotter import generate_academic_report_fallback
from app.evaluation.transcript_exporter import write_fallback_case_study


def _scratch(name: str) -> Path:
    path = Path("app/evaluation/results") / f"test_phase9_{name}"
    shutil.rmtree(path, ignore_errors=True)
    path.mkdir(parents=True, exist_ok=True)
    return path


def test_synthetic_fallback_csv_is_valid():
    scratch = _scratch("csv")
    rows = synthetic_ablation_rows()
    try:
        csv_path = write_ablation_csv(rows, scratch)
        assert Path(csv_path).exists()
        assert has_valid_benchmark_rows(rows)
        assert len(rows) == 9
        assert {row["ablation_mode"] for row in rows} == {
            "full",
            "no_ucb",
            "no_tracker",
        }
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_paper_writer_inlines_statistics_and_artifacts():
    scratch = _scratch("paper")
    rows = synthetic_ablation_rows()
    try:
        write_ablation_csv(rows, scratch)
        generate_academic_report_fallback(
            str(scratch / "ablation_results.csv"), str(scratch)
        )
        write_fallback_case_study(scratch / "case_study.md")
        paper_path = scratch / "EDMIE_Full_Paper.md"

        generate_paper(paper_path, scratch)
        validate_paper(paper_path, scratch)
        text = paper_path.read_text(encoding="utf-8")

        assert "fig_efficiency_turns.png" in text
        assert "fig_alignment_mae.png" in text
        assert "p-value=" in text
        assert "$$" in text
        assert "XXX" not in text
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_paper_validator_rejects_placeholders():
    scratch = _scratch("validator")
    rows = synthetic_ablation_rows()
    try:
        write_ablation_csv(rows, scratch)
        generate_academic_report_fallback(
            str(scratch / "ablation_results.csv"), str(scratch)
        )
        write_fallback_case_study(scratch / "case_study.md")
        paper_path = scratch / "bad.md"
        paper_path.write_text(
            "Abstract\nMethodology\nExperiments and Results\n"
            "app/evaluation/results/fig_efficiency_turns.png\n"
            "app/evaluation/results/fig_alignment_mae.png\n"
            "p-value=0.01\n$$x$$\nXXX",
            encoding="utf-8",
        )

        with pytest.raises(ValueError):
            validate_paper(paper_path, scratch)
    finally:
        shutil.rmtree(scratch, ignore_errors=True)
