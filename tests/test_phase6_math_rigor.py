import math
from typing import Any

import pytest

from app.flows.probers import probe_global_baseline
from app.graphs.nodes.negotiator import select_max_divergence_pair
from app.graphs.nodes.preference_tracker import (
    BT_LEARNING_RATE,
    BT_TAU,
    FeedbackAnalysis,
    apply_feedback_update,
)


PREFERENCE_KEYS = ("school", "major", "tuition", "quality", "geo")


def _normalized_expected(raw_weights: dict[str, float]) -> dict[str, float]:
    clamped = {
        key: max(0.05, min(0.95, float(raw_weights.get(key, 0.0))))
        for key in PREFERENCE_KEYS
    }
    total = sum(clamped.values())
    return {key: clamped[key] / total for key in PREFERENCE_KEYS}


def _bt_expected(
    weights: dict[str, float],
    delta_phi: dict[str, float],
    *,
    label: float,
) -> dict[str, float]:
    delta_u = sum(weights[key] * delta_phi.get(key, 0.0) for key in PREFERENCE_KEYS)
    delta_u = max(-10.0, min(10.0, delta_u))
    probability = 1.0 / (1.0 + math.exp(-BT_TAU * delta_u))
    raw = {
        key: weights[key]
        + BT_LEARNING_RATE * (label - probability) * delta_phi.get(key, 0.0)
        for key in PREFERENCE_KEYS
    }
    return _normalized_expected(raw)


def _candidate(
    school: str,
    utility: float,
    features: dict[str, float],
    *,
    score_margin: float | None = None,
    quality_score: float = 80.0,
) -> dict[str, Any]:
    row: dict[str, Any] = {
        "school_name": school,
        "school_tier": "一本重点",
        "major_name": "计算机科学与技术",
        "major_relax_level": 0,
        "geo_relax_level": 0,
        "quality_score": quality_score,
        "tuition": 8000,
        "_implicit_utility": utility,
        "_phi_features": features,
    }
    if score_margin is not None:
        row["score_margin"] = score_margin
    return row


def test_bradley_terry_gradient_update_direction_and_formula():
    weights = {key: 0.2 for key in PREFERENCE_KEYS}
    variance = {key: 0.8 for key in PREFERENCE_KEYS}
    delta_phi = {
        "school": 0.6,
        "major": 0.2,
        "tuition": 0.0,
        "quality": 0.0,
        "geo": -0.4,
    }

    accept_weights, accept_variance = apply_feedback_update(
        weights,
        variance,
        FeedbackAnalysis(intent="accept", target_dimension="school"),
        delta_phi,
    )
    reject_weights, reject_variance = apply_feedback_update(
        weights,
        variance,
        FeedbackAnalysis(intent="reject", target_dimension="school"),
        delta_phi,
    )

    assert accept_weights == pytest.approx(_bt_expected(weights, delta_phi, label=1.0))
    assert reject_weights == pytest.approx(_bt_expected(weights, delta_phi, label=0.0))
    assert accept_weights["school"] > weights["school"]
    assert reject_weights["school"] < weights["school"]
    assert accept_weights["geo"] < weights["geo"]
    assert reject_weights["geo"] > weights["geo"]
    assert sum(accept_weights.values()) == pytest.approx(1.0)
    assert sum(reject_weights.values()) == pytest.approx(1.0)
    assert all(
        accept_variance[key] == pytest.approx(variance[key] * 0.5)
        for key in PREFERENCE_KEYS
    )
    assert all(
        reject_variance[key] == pytest.approx(variance[key] * 0.5)
        for key in PREFERENCE_KEYS
    )


def test_select_max_divergence_pair_skips_homogeneous_top2():
    top_features = {
        "school": 0.8,
        "major": 0.8,
        "tuition": 1.0,
        "quality": 0.8,
        "geo": 0.8,
    }
    candidates = [
        _candidate("Top1", 1.00, top_features),
        _candidate("Homogeneous Top2", 0.95, dict(top_features)),
        _candidate(
            "Small Difference Top3",
            0.90,
            {"school": 0.75, "major": 0.8, "tuition": 1.0, "quality": 0.7, "geo": 0.75},
        ),
        _candidate(
            "Max Tension Top4",
            0.85,
            {"school": 0.1, "major": 0.2, "tuition": 0.2, "quality": 0.1, "geo": 0.1},
        ),
    ]

    option_a, option_b, delta_phi = select_max_divergence_pair(candidates)

    assert option_a["school_name"] == "Top1"
    assert option_b["school_name"] == "Max Tension Top4"
    assert delta_phi["school"] == pytest.approx(-0.7)
    assert sum(abs(value) for value in delta_phi.values()) > 2.0


@pytest.mark.asyncio
async def test_global_baseline_returns_reach_match_safety_matrix(monkeypatch):
    rows = [
        _candidate("Reach High", 0.0, {}, score_margin=-2, quality_score=98),
        _candidate("Reach Low", 0.0, {}, score_margin=4, quality_score=70),
        _candidate("Match High", 0.0, {}, score_margin=10, quality_score=95),
        _candidate("Match Low", 0.0, {}, score_margin=14, quality_score=75),
        _candidate("Safety High", 0.0, {}, score_margin=20, quality_score=90),
        _candidate("Safety Low", 0.0, {}, score_margin=30, quality_score=65),
    ]

    async def fake_fetch(
        db: Any, query: str, params: list[Any]
    ) -> list[dict[str, Any]]:
        return rows

    monkeypatch.setattr("app.flows.probers._fetch", fake_fetch)

    matrix = await probe_global_baseline(
        {
            "constraints": {
                "score": 600,
                "major": "计算机",
                "budget": 10000,
                "selected_subjects": ["物理", "化学", "生物"],
            }
        },
        db=object(),
        limit=3,
    )

    assert set(matrix) == {"reach", "match", "safety"}
    assert [row["school_name"] for row in matrix["reach"]] == [
        "Reach High",
        "Reach Low",
    ]
    assert [row["school_name"] for row in matrix["match"]] == [
        "Match High",
        "Match Low",
    ]
    assert [row["school_name"] for row in matrix["safety"]] == [
        "Safety High",
        "Safety Low",
    ]
    assert all(-5 <= row["score_margin"] <= 5 for row in matrix["reach"])
    assert all(5 < row["score_margin"] <= 15 for row in matrix["match"])
    assert all(row["score_margin"] > 15 for row in matrix["safety"])
    for bucket_rows in matrix.values():
        utilities = [row["_implicit_utility"] for row in bucket_rows]
        assert utilities == sorted(utilities, reverse=True)
