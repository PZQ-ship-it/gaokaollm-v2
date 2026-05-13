from pathlib import Path
import shutil
from typing import Any

import pytest

from app.evaluation.benchmark import get_dataset
from app.evaluation.reference_baselines import (
    INITIAL_LLM_BASELINE,
    RANDOM_BASELINE,
    InitialPreferenceWeights,
    arun_reference_baselines,
    compute_mae,
    estimate_random_baseline,
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
                ]
            ),
            encoding="utf-8",
        )

        rows = _reference_mae_rows(output_dir)
        summary = "\n".join(_reference_summary_lines(output_dir))

        assert {row["model_variant"] for row in rows} == {
            "Random Dirichlet Baseline",
            "Initial-query LLM Baseline",
        }
        assert "Random Dirichlet Baseline: MAE=0.220000" in summary
        assert "Initial-query LLM Baseline: MAE=0.190000" in summary
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)


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
