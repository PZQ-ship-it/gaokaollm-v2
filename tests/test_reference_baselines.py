from pathlib import Path
import shutil
from typing import Any

import pytest

from app.evaluation.benchmark import get_dataset
from app.evaluation.reference_baselines import (
    INITIAL_LLM_BASELINE,
    RANDOM_BASELINE,
    V1_HYBRID_BASELINE,
    InitialPreferenceWeights,
    arun_reference_baselines,
    compute_mae,
    estimate_random_baseline,
    infer_weights_from_v1_candidates,
    infer_initial_weights_with_llm,
    normalize_weights,
)
from app.evaluation.sandbox import _mae as sandbox_mae
from app.evaluation.plotter import _reference_mae_rows, _reference_summary_lines


def test_compute_mae_matches_sandbox_formula():
    weights = {
        "school": 0.1,
        "major": 0.5,
        "tuition": 0.2,
        "quality": 0.1,
        "geo": 0.1,
    }
    ground_truth = {
        "school": 0.2,
        "major": 0.4,
        "tuition": 0.1,
        "quality": 0.2,
        "geo": 0.1,
    }

    assert compute_mae(weights, ground_truth) == pytest.approx(
        sandbox_mae(weights, ground_truth)
    )


def test_random_dirichlet_baseline_is_reproducible_and_valid():
    dataset = get_dataset("robust")[:3]
    first = estimate_random_baseline(dataset, samples=500, seed=7)
    second = estimate_random_baseline(dataset, samples=500, seed=7)

    assert first["mean_mae"] == pytest.approx(second["mean_mae"])
    assert 0.0 <= first["mean_mae"] <= 1.0
    assert len(first["profile_rows"]) == 3
    assert all(0.0 <= row["mean_mae"] <= 1.0 for row in first["profile_rows"])


def test_normalize_weights_clips_and_sums_to_one():
    normalized = normalize_weights(
        {"school": 2.0, "major": "bad", "tuition": -1.0, "quality": 0.0, "geo": 0.0}
    )

    assert sum(normalized.values()) == pytest.approx(1.0)
    assert normalized["school"] > normalized["major"]
    assert all(value >= 0.0 for value in normalized.values())


def test_plotter_reads_reference_baselines_for_mae_chart():
    output_dir = Path("app/evaluation/results/test_reference_plotter")
    shutil.rmtree(output_dir, ignore_errors=True)
    output_dir.mkdir(parents=True, exist_ok=True)
    try:
        csv_path = output_dir / "reference_baselines.csv"
        csv_path.write_text(
            "\n".join(
                [
                    "dataset,profile_id,baseline_type,mae_error,weights,status,error_message",
                    'robust,__dataset__,random_dirichlet_expected,0.22,"{}",ok,',
                    'robust,p1,initial_query_llm,0.18,"{}",ok,',
                    'robust,p2,initial_query_llm,0.20,"{}",ok,',
                    'robust,__dataset__,v1_hybrid_candidate_proxy,0.24,"{}",ok,',
                ]
            ),
            encoding="utf-8",
        )

        rows = _reference_mae_rows(output_dir)
        summary = "\n".join(_reference_summary_lines(output_dir))

        assert {row["model_variant"] for row in rows} == {
            "Random Dirichlet Baseline",
            "Initial-query LLM Baseline",
            "V1 Hybrid RAG Baseline",
        }
        assert "Random Dirichlet Baseline: MAE=0.220000" in summary
        assert "Initial-query LLM Baseline: MAE=0.190000" in summary
        assert "V1 Hybrid RAG Baseline: MAE=0.240000" in summary
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)


def test_v1_candidate_proxy_weights_are_normalized_and_evidence_driven():
    weights = infer_weights_from_v1_candidates(
        [
            {
                "school_name": "浙江大学",
                "school_province": "浙江",
                "school_city": "杭州",
                "major_name": "计算机科学与技术",
                "is_985": True,
                "is_211": True,
                "tuition": 6000,
                "quality_score": 95,
                "ranking": 3,
            },
            {
                "school_name": "杭州电子科技大学",
                "school_province": "浙江",
                "school_city": "杭州",
                "major_name": "软件工程",
                "is_985": False,
                "is_211": False,
                "tuition": 6900,
                "quality_score": 78,
                "ranking": 91,
            },
        ],
        query_text="浙江考生610分，想在浙江读计算机，预算一万以内。",
    )

    assert sum(weights.values()) == pytest.approx(1.0)
    assert weights["major"] > weights["tuition"]
    assert weights["school"] > 0.15
    assert weights["geo"] > 0.15


def test_v1_candidate_proxy_rejects_empty_candidates():
    with pytest.raises(ValueError, match="no reranked candidates"):
        infer_weights_from_v1_candidates([], query_text="浙江考生610分")


@pytest.mark.asyncio
async def test_initial_llm_baseline_uses_structured_output(monkeypatch):
    async def fail_native(profile: Any):
        raise RuntimeError("native unavailable")

    class FakeStructured:
        async def ainvoke(self, messages: Any):
            assert "explicit initial query" in messages[0].content
            return InitialPreferenceWeights(
                school=0.1,
                major=0.7,
                tuition=0.1,
                quality=0.1,
                geo=0.0,
                rationale="explicitly asks for computer major",
            )

    class FakeLLM:
        def with_structured_output(self, schema: Any):
            assert schema is InitialPreferenceWeights
            return FakeStructured()

    monkeypatch.setattr(
        "app.evaluation.reference_baselines._infer_initial_weights_native_json",
        fail_native,
    )
    monkeypatch.setattr(
        "app.evaluation.reference_baselines.get_structured_chat_model",
        lambda: FakeLLM(),
    )

    profile = get_dataset("smoke")[0]
    weights = await infer_initial_weights_with_llm(profile)

    assert sum(weights.values()) == pytest.approx(1.0)
    assert weights["major"] == pytest.approx(0.7)


@pytest.mark.asyncio
async def test_reference_baseline_csv_and_error_modes(monkeypatch):
    output_dir = Path("app/evaluation/results/test_reference_baselines")
    shutil.rmtree(output_dir, ignore_errors=True)
    output_dir.mkdir(parents=True, exist_ok=True)

    async def fake_native(profile: Any):
        return {
            "school": 0.2,
            "major": 0.4,
            "tuition": 0.2,
            "quality": 0.1,
            "geo": 0.1,
        }

    monkeypatch.setattr(
        "app.evaluation.reference_baselines._infer_initial_weights_native_json",
        fake_native,
    )

    try:
        result = await arun_reference_baselines(
            dataset_name="smoke",
            samples=100,
            seed=11,
            output_dir=output_dir,
            require_real=True,
        )

        csv_path = Path(result["csv_path"])
        text = csv_path.read_text(encoding="utf-8")
        assert csv_path.exists()
        assert RANDOM_BASELINE in text
        assert INITIAL_LLM_BASELINE in text
        assert "__dataset__" in text

        async def fail_native_after(profile: Any):
            raise RuntimeError("boom")

        def fail_llm():
            raise RuntimeError("boom")

        monkeypatch.setattr(
            "app.evaluation.reference_baselines._infer_initial_weights_native_json",
            fail_native_after,
        )
        monkeypatch.setattr(
            "app.evaluation.reference_baselines.get_structured_chat_model",
            fail_llm,
        )
        with pytest.raises(RuntimeError, match="boom"):
            await arun_reference_baselines(
                dataset_name="smoke",
                samples=10,
                output_dir=output_dir,
                require_real=True,
            )

        non_strict = await arun_reference_baselines(
            dataset_name="smoke",
            samples=10,
            output_dir=output_dir,
            require_real=False,
        )
        assert any(row["status"] == "error" for row in non_strict["rows"])
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)


@pytest.mark.asyncio
async def test_reference_baseline_can_include_mocked_v1_hybrid(monkeypatch):
    output_dir = Path("app/evaluation/results/test_reference_v1_hybrid")
    shutil.rmtree(output_dir, ignore_errors=True)
    output_dir.mkdir(parents=True, exist_ok=True)

    async def fake_native(profile: Any):
        return {
            "school": 0.2,
            "major": 0.4,
            "tuition": 0.2,
            "quality": 0.1,
            "geo": 0.1,
        }

    async def fake_v1(profile: Any, *, timeout_seconds: float = 180.0):
        assert timeout_seconds == 12.0
        return {
            "school": 0.25,
            "major": 0.45,
            "tuition": 0.10,
            "quality": 0.10,
            "geo": 0.10,
        }

    monkeypatch.setattr(
        "app.evaluation.reference_baselines._infer_initial_weights_native_json",
        fake_native,
    )
    monkeypatch.setattr(
        "app.evaluation.reference_baselines.infer_v1_hybrid_weights",
        fake_v1,
    )

    try:
        result = await arun_reference_baselines(
            dataset_name="smoke",
            samples=20,
            output_dir=output_dir,
            require_real=True,
            include_v1_hybrid=True,
            v1_timeout_seconds=12.0,
        )

        text = Path(result["csv_path"]).read_text(encoding="utf-8")
        class_text = Path(result["classification_csv_path"]).read_text(encoding="utf-8")

        assert V1_HYBRID_BASELINE in text
        assert "__dataset__,v1_hybrid_candidate_proxy" in text
        assert V1_HYBRID_BASELINE in class_text
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)
