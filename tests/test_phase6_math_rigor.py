import math
from typing import Any

import pytest

from app.flows.probers import (
    _annotate_terminal_relaxation_features,
    extract_phi_features,
    probe_global_baseline,
)
from app.graphs.nodes.negotiator import select_max_divergence_pair
from app.graphs.nodes.preference_tracker import (
    BT_LEARNING_RATE,
    BT_TAU,
    FeedbackAnalysis,
    apply_feedback_update,
)


PREFERENCE_KEYS = ("school", "major", "tuition", "quality", "geo", "risk")


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


def _uniform_preferences(value: float | None = None) -> dict[str, float]:
    if value is None:
        value = 1.0 / len(PREFERENCE_KEYS)
    return {key: float(value) for key in PREFERENCE_KEYS}


def _candidate(
    school: str,
    utility: float,
    features: dict[str, float],
    *,
    score_margin: float | None = None,
    min_rank: int | None = None,
    student_rank: int | None = None,
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
    if min_rank is not None:
        row["min_rank"] = min_rank
    if student_rank is not None:
        row["student_rank"] = student_rank
    return row


def test_bradley_terry_gradient_update_direction_and_formula():
    weights = _uniform_preferences()
    variance = {key: 0.8 for key in PREFERENCE_KEYS}
    delta_phi = {
        "school": 0.6,
        "major": 0.2,
        "tuition": 0.0,
        "quality": 0.0,
        "geo": -0.4,
        "risk": 0.0,
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
    for key in ("school", "major", "geo"):
        assert accept_variance[key] == pytest.approx(variance[key] * 0.5)
        assert reject_variance[key] == pytest.approx(variance[key] * 0.5)
    for key in ("tuition", "quality", "risk"):
        assert accept_variance[key] == pytest.approx(variance[key])
        assert reject_variance[key] == pytest.approx(variance[key])


def test_bradley_terry_update_does_not_create_global_variance_collapse():
    weights = _uniform_preferences()
    variance = {key: 1.0 for key in PREFERENCE_KEYS}

    weights, variance = apply_feedback_update(
        weights,
        variance,
        FeedbackAnalysis(intent="accept", target_dimension="tuition"),
        {
            "school": 0.0,
            "major": 0.0,
            "tuition": -1.0,
            "quality": 0.0,
            "geo": 0.0,
            "risk": 0.0,
        },
    )
    weights, variance = apply_feedback_update(
        weights,
        variance,
        FeedbackAnalysis(intent="reject", target_dimension="tuition"),
        {
            "school": 0.0,
            "major": 0.0,
            "tuition": -1.0,
            "quality": 0.0,
            "geo": 0.0,
            "risk": 0.0,
        },
    )

    assert variance["tuition"] == pytest.approx(0.25)
    for key in ("school", "major", "quality", "geo", "risk"):
        assert variance[key] == pytest.approx(1.0)
    assert sum(variance.values()) == pytest.approx(5.25)


def test_bradley_terry_clips_hard_veto_sentinel_for_learning_delta():
    weights = _uniform_preferences()
    variance = {key: 1.0 for key in PREFERENCE_KEYS}
    physical_delta_phi = {
        "school": 0.3,
        "major": 0.0,
        "tuition": -10000.0,
        "quality": 0.0,
        "geo": 0.0,
        "risk": -0.5,
    }
    learning_delta_phi = {
        "school": 0.3,
        "major": 0.0,
        "tuition": -1.0,
        "quality": 0.0,
        "geo": 0.0,
        "risk": -0.5,
    }

    new_weights, new_variance = apply_feedback_update(
        weights,
        variance,
        FeedbackAnalysis(intent="reject", target_dimension="tuition"),
        physical_delta_phi,
    )

    assert new_weights == pytest.approx(
        _bt_expected(weights, learning_delta_phi, label=0.0)
    )
    assert new_weights["tuition"] > 0.30
    assert round(new_weights["tuition"], 2) != round(weights["tuition"], 2)
    assert new_variance["tuition"] == pytest.approx(0.5)


def test_hesitate_inflates_uncertainty_by_delta_phi_only():
    weights = _uniform_preferences()
    variance = {key: 0.4 for key in PREFERENCE_KEYS}

    new_weights, new_variance = apply_feedback_update(
        weights,
        variance,
        FeedbackAnalysis(intent="hesitate", target_dimension="geo"),
        {
            "school": 0.0,
            "major": 0.0,
            "tuition": 0.0,
            "quality": 0.0,
            "geo": -0.5,
            "risk": 0.0,
        },
    )

    assert new_weights == pytest.approx(weights)
    assert new_variance["geo"] == pytest.approx(0.5)
    for key in ("school", "major", "tuition", "quality", "risk"):
        assert new_variance[key] == pytest.approx(variance[key])


def test_select_max_divergence_pair_skips_homogeneous_top2():
    top_features = {
        "school": 0.8,
        "major": 0.8,
        "tuition": 1.0,
        "quality": 0.8,
        "geo": 0.8,
        "risk": 0.7,
    }
    candidates = [
        _candidate("Top1", 1.00, top_features),
        _candidate("Homogeneous Top2", 0.95, dict(top_features)),
        _candidate(
            "Small Difference Top3",
            0.90,
            {
                "school": 0.75,
                "major": 0.8,
                "tuition": 1.0,
                "quality": 0.7,
                "geo": 0.75,
                "risk": 0.7,
            },
        ),
        _candidate(
            "Max Tension Top4",
            0.85,
            {
                "school": 0.1,
                "major": 0.2,
                "tuition": 0.2,
                "quality": 0.1,
                "geo": 0.1,
                "risk": 0.0,
            },
        ),
    ]

    option_a, option_b, delta_phi = select_max_divergence_pair(candidates)

    assert option_a["school_name"] == "Top1"
    assert option_b["school_name"] == "Max Tension Top4"
    assert delta_phi["school"] == pytest.approx(-0.7)
    assert sum(abs(value) for value in delta_phi.values()) > 2.0


@pytest.mark.asyncio
async def test_global_baseline_returns_reach_match_safety_matrix(monkeypatch):
    student_rank = 10000
    rows = [
        _candidate("Reach High", 0.0, {}, min_rank=9000, quality_score=98),
        _candidate("Reach Low", 0.0, {}, min_rank=9700, quality_score=70),
        _candidate("Reach High", 0.0, {}, min_rank=9300, quality_score=40),
        _candidate("Match High", 0.0, {}, min_rank=10000, quality_score=95),
        _candidate("Match Low", 0.0, {}, min_rank=11400, quality_score=75),
        _candidate("Safety High", 0.0, {}, min_rank=11800, quality_score=90),
        _candidate("Safety Low", 0.0, {}, min_rank=13500, quality_score=65),
    ]
    calls: list[tuple[str, list[Any]]] = []

    async def fake_fetch(
        db: Any, query: str, params: list[Any]
    ) -> list[dict[str, Any]]:
        calls.append((query, params))
        if "score_rank_segments" in query:
            return [{"rank_min": 9900, "rank_max": student_rank}]
        return rows

    monkeypatch.setattr("app.flows.probers._fetch", fake_fetch)

    matrix = await probe_global_baseline(
        {
            "constraints": {
                "score": 600,
                "province": "浙江",
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
    assert all(0.85 <= row["rank_ratio"] < 0.98 for row in matrix["reach"])
    assert all(0.98 <= row["rank_ratio"] <= 1.15 for row in matrix["match"])
    assert all(1.15 <= row["rank_ratio"] <= 1.40 for row in matrix["safety"])
    assert all(row["student_rank"] == student_rank for row in matrix["reach"])
    for bucket_rows in matrix.values():
        utilities = [row["_implicit_utility"] for row in bucket_rows]
        assert utilities == sorted(utilities, reverse=True)

    baseline_query, baseline_params = calls[-1]
    assert "a.min_score <= %s" not in baseline_query
    assert int(student_rank * 0.85) in baseline_params
    assert int(student_rank * 1.40) in baseline_params


@pytest.mark.asyncio
async def test_global_baseline_final_table_can_return_up_to_80(monkeypatch):
    student_rank = 10000
    rows: list[dict[str, Any]] = []
    for index in range(30):
        rows.append(
            _candidate(
                f"Reach {index}",
                0.0,
                {},
                min_rank=8600 + index,
                quality_score=100 - index,
            )
        )
        rows.append(
            _candidate(
                f"Match {index}",
                0.0,
                {},
                min_rank=9900 + index,
                quality_score=100 - index,
            )
        )
        rows.append(
            _candidate(
                f"Safety {index}",
                0.0,
                {},
                min_rank=11600 + index,
                quality_score=100 - index,
            )
        )

    async def fake_fetch(
        db: Any, query: str, params: list[Any]
    ) -> list[dict[str, Any]]:
        if "score_rank_segments" in query:
            return [{"rank_min": 9900, "rank_max": student_rank}]
        return rows

    monkeypatch.setattr("app.flows.probers._fetch", fake_fetch)

    matrix = await probe_global_baseline(
        {
            "constraints": {
                "score": 600,
                "province": "浙江",
                "major": "计算机",
                "budget": 10000,
                "selected_subjects": ["物理", "化学", "生物"],
            }
        },
        db=object(),
        limit=80,
        total_limit=80,
    )

    assert sum(len(bucket_rows) for bucket_rows in matrix.values()) == 80
    assert len(matrix["reach"]) == 27
    assert len(matrix["match"]) == 27
    assert len(matrix["safety"]) == 26
    assert all(len(bucket_rows) > 3 for bucket_rows in matrix.values())


@pytest.mark.asyncio
async def test_accepted_risk_relaxation_extends_reach_window(monkeypatch):
    student_rank = 10000
    rows = [
        _candidate("More Aggressive Reach", 0.0, {}, min_rank=8000, quality_score=98),
        _candidate("Normal Reach", 0.0, {}, min_rank=9000, quality_score=95),
    ]
    calls: list[tuple[str, list[Any]]] = []

    async def fake_fetch(
        db: Any, query: str, params: list[Any]
    ) -> list[dict[str, Any]]:
        calls.append((query, params))
        if "score_rank_segments" in query:
            return [{"rank_min": 9900, "rank_max": student_rank}]
        return rows

    monkeypatch.setattr("app.flows.probers._fetch", fake_fetch)

    matrix = await probe_global_baseline(
        {
            "constraints": {
                "score": 600,
                "province": "浙江",
                "major": "医学",
                "budget": 10000,
                "risk_preference": "stable",
                "selected_subjects": ["物理", "化学", "生物"],
            },
            "accepted_relaxations": [{"dimension": "risk"}],
        },
        db=object(),
        limit=3,
    )

    baseline_query, baseline_params = calls[-1]
    assert int(student_rank * 0.75) in baseline_params
    assert int(student_rank * 0.85) not in baseline_params
    assert "More Aggressive Reach" in [row["school_name"] for row in matrix["reach"]]
    aggressive = next(
        row for row in matrix["reach"] if row["school_name"] == "More Aggressive Reach"
    )
    assert aggressive["rank_ratio"] == pytest.approx(0.8)
    assert aggressive["risk_relax_level"] == 1
    assert aggressive["_phi_features"]["risk"] == pytest.approx(0.0)


@pytest.mark.asyncio
async def test_global_baseline_keeps_unrelaxed_preference_filters(monkeypatch):
    calls: list[tuple[str, list[Any]]] = []

    async def fake_fetch(
        db: Any, query: str, params: list[Any]
    ) -> list[dict[str, Any]]:
        calls.append((query, params))
        if "score_rank_segments" in query:
            return [{"rank_min": 52000, "rank_max": 52529}]
        return []

    monkeypatch.setattr("app.flows.probers._fetch", fake_fetch)

    await probe_global_baseline(
        {
            "constraints": {
                "score": 600,
                "province": "浙江",
                "target_provinces": ["江苏", "浙江", "上海"],
                "city": "杭州",
                "major": "医学",
                "budget": 5500,
                "selected_subjects": ["物理", "化学", "生物"],
            }
        },
        db=object(),
        limit=3,
    )

    query, params = calls[-1]
    assert "s.province = ANY(%s::text[])" in query
    assert "s.city = ANY(%s::text[])" in query
    assert "a.major_name_raw LIKE %s" in query
    assert "plan.min_tuition IS NOT NULL" in query
    assert "plan.min_tuition <= %s" in query
    assert ["江苏", "浙江", "上海"] in params
    assert "%医学%" in params
    assert 5500 in params


@pytest.mark.asyncio
async def test_global_baseline_drops_accepted_relaxed_preference_filters(monkeypatch):
    calls: list[tuple[str, list[Any]]] = []
    rows = [
        _candidate(
            "Relaxed Option",
            0.0,
            {},
            min_rank=55000,
            quality_score=90,
        )
        | {
            "school_province": "北京",
            "school_city": "北京",
            "major_name": "药学",
            "tuition": 7480,
        }
    ]

    async def fake_fetch(
        db: Any, query: str, params: list[Any]
    ) -> list[dict[str, Any]]:
        calls.append((query, params))
        if "score_rank_segments" in query:
            return [{"rank_min": 52000, "rank_max": 52529}]
        return rows

    monkeypatch.setattr("app.flows.probers._fetch", fake_fetch)

    await probe_global_baseline(
        {
            "constraints": {
                "score": 600,
                "province": "浙江",
                "target_provinces": ["江苏", "浙江", "上海"],
                "city": "杭州",
                "major": "医学",
                "budget": 5500,
                "selected_subjects": ["物理", "化学", "生物"],
            },
            "accepted_relaxations": [
                {"dimension": "geo", "candidate_identity": "geo-option"},
                {"dimension": "major", "candidate_identity": "major-option"},
                {"dimension": "tuition", "candidate_identity": "tuition-option"},
            ],
        },
        db=object(),
        limit=3,
    )

    query, params = calls[-1]
    assert "s.province = ANY(%s::text[])" not in query
    assert "s.city = ANY(%s::text[])" not in query
    assert "a.major_name_raw LIKE %s" not in query
    assert "(plan.min_tuition IS NULL OR plan.min_tuition <= %s)" not in query
    assert ["江苏", "浙江", "上海"] not in params
    assert "%医学%" not in params
    assert 5500 not in params


def test_accepted_relaxation_still_uses_soft_feature_penalties():
    state = {
        "constraints": {
            "province": "浙江",
            "target_provinces": ["江苏", "浙江", "上海"],
            "city": "杭州",
            "major": "医学",
            "budget": 5500,
        },
        "accepted_relaxations": [
            {"dimension": "geo"},
            {"dimension": "major"},
            {"dimension": "tuition"},
        ],
    }
    row = {
        "school_province": "北京",
        "school_city": "北京",
        "major_name": "药学",
        "tuition": 7480,
    }

    annotated = _annotate_terminal_relaxation_features(row, state["constraints"], state)
    features = extract_phi_features(annotated, state)

    assert annotated["geo_relax_level"] == 1
    assert annotated["major_relax_level"] == 1
    assert features["geo"] < 1.0
    assert features["major"] < 1.0
    assert 0.0 < features["tuition"] < 1.0
