from pathlib import Path
import shutil

import pytest

from app.evaluation.classification_metrics import (
    INITIAL_QUERY_BASELINE,
    classification_rows_from_reference_rows,
    compute_prf,
    gold_dimensions,
    predicted_dimensions,
    write_classification_metrics,
)
from app.evaluation.schemas import IcebergProfile


def _profile(profile_id: str, weights: dict[str, float]) -> IcebergProfile:
    return IcebergProfile(
        profile_id=profile_id,
        explicit_query="浙江考生610分，物化生，想读计算机。",
        hidden_bottom_line="隐藏底线用于测试。",
        ground_truth_weights=weights,
    )


def test_single_extreme_dimension_prf_is_perfect():
    profile = _profile(
        "single_major",
        {
            "school": 0.03,
            "major": 0.85,
            "tuition": 0.04,
            "quality": 0.04,
            "geo": 0.04,
            "risk": 0.00,
        },
    )

    metrics = compute_prf(
        {
            "school": 0.1,
            "major": 0.7,
            "tuition": 0.1,
            "quality": 0.05,
            "geo": 0.05,
            "risk": 0.0,
        },
        profile,
    )

    assert gold_dimensions(profile) == ("major",)
    assert predicted_dimensions({"major": 0.9, "school": 0.1}, 1) == ("major",)
    assert metrics["precision"] == pytest.approx(1.0)
    assert metrics["recall"] == pytest.approx(1.0)
    assert metrics["f1"] == pytest.approx(1.0)


def test_two_dimension_profile_half_hit_scores_half():
    profile = _profile(
        "major_tuition",
        {
            "school": 0.05,
            "major": 0.48,
            "tuition": 0.38,
            "quality": 0.04,
            "geo": 0.05,
            "risk": 0.00,
        },
    )

    metrics = compute_prf(
        {
            "school": 0.4,
            "major": 0.5,
            "tuition": 0.05,
            "quality": 0.03,
            "geo": 0.02,
            "risk": 0.0,
        },
        profile,
    )

    assert set(metrics["gold_dims"]) == {"major", "tuition"}
    assert set(metrics["pred_dims"]) == {"major", "school"}
    assert metrics["precision"] == pytest.approx(0.5)
    assert metrics["recall"] == pytest.approx(0.5)
    assert metrics["f1"] == pytest.approx(0.5)


def test_balanced_profile_falls_back_to_ground_truth_top_one():
    profile = _profile(
        "balanced",
        {
            "school": 0.22,
            "major": 0.20,
            "tuition": 0.18,
            "quality": 0.20,
            "geo": 0.20,
            "risk": 0.00,
        },
    )

    assert gold_dimensions(profile) == ("school",)


def test_reference_rows_parse_json_weights_and_write_csv():
    output_dir = Path("app/evaluation/results/test_classification_metrics")
    shutil.rmtree(output_dir, ignore_errors=True)
    output_dir.mkdir(parents=True, exist_ok=True)
    profile = _profile(
        "p1",
        {
            "school": 0.05,
            "major": 0.45,
            "tuition": 0.40,
            "quality": 0.05,
            "geo": 0.05,
            "risk": 0.00,
        },
    )
    try:
        rows = classification_rows_from_reference_rows(
            [
                {
                    "profile_id": "p1",
                    "baseline_type": INITIAL_QUERY_BASELINE,
                    "weights": '{"major": 0.6, "tuition": 0.3, "school": 0.1}',
                    "status": "ok",
                    "error_message": "",
                },
                {
                    "profile_id": "p1",
                    "baseline_type": "random_dirichlet_expected",
                    "weights": '{"expected_f1": 0.25}',
                    "status": "ok",
                    "error_message": "",
                },
                {
                    "profile_id": "p1",
                    "baseline_type": "v1_hybrid_candidate_proxy",
                    "weights": '{"major": 0.2, "tuition": 0.6, "school": 0.2}',
                    "status": "ok",
                    "error_message": "",
                },
            ],
            [profile],
        )
        csv_path = Path(write_classification_metrics(rows, output_dir))
        content = csv_path.read_text(encoding="utf-8")

        assert len(rows) == 3
        assert rows[0]["ablation_mode"] == INITIAL_QUERY_BASELINE
        assert rows[0]["f1"] == pytest.approx(1.0)
        assert rows[1]["ablation_mode"] == "random_dirichlet_expected"
        assert rows[1]["f1"] == pytest.approx(0.25)
        assert rows[2]["ablation_mode"] == "v1_hybrid_candidate_proxy"
        assert rows[2]["f1"] == pytest.approx(0.5)
        assert csv_path.exists()
        assert "initial_query_llm" in content
        assert "v1_hybrid_candidate_proxy" in content
        assert "random_dirichlet_expected" in content
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)
