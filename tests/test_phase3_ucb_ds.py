import json
from typing import Any

import pytest
from langchain_core.messages import AIMessage

from app.graphs.nodes.preference_tracker import (
    FeedbackAnalysis,
    apply_feedback_update,
    preference_tracker_node,
)
from app.graphs.nodes.radar import _build_probe_plan, select_ucb_dimension
from app.graphs.nodes.radar import _plan_with_available_opportunities
from app.graphs.nodes.radar import _without_global_baseline_duplicates
from app.graphs.nodes.radar import should_halt_for_global_baseline


class FakePlannerLLM:
    def __init__(self) -> None:
        self.prompts: list[list[Any]] = []

    async def ainvoke(self, prompt: list[Any]) -> AIMessage:
        self.prompts.append(prompt)
        return AIMessage(
            content=json.dumps(
                {
                    "probe_plan": [
                        {
                            "probe": "major_geo_relax",
                            "priority": 1,
                            "reason": "fake planner drift",
                        }
                    ],
                    "opportunity_rankings": ["major_geo_relax"],
                    "clarification_hint": None,
                },
                ensure_ascii=False,
            )
        )


@pytest.mark.asyncio
async def test_ucb_override_forces_tuition_probe(monkeypatch):
    monkeypatch.delenv("GAOKAOLLM_OFFLINE_DETERMINISTIC", raising=False)
    fake_llm = FakePlannerLLM()
    monkeypatch.setattr("app.graphs.nodes.radar.get_chat_model", lambda: fake_llm)

    state = {
        "constraints": {
            "score": 600,
            "major": "计算机科学与技术",
            "budget": 8000,
            "selected_subjects": ["物理", "化学", "生物"],
        },
        "implicit_weights": {
            "school": 1 / 6,
            "major": 1 / 6,
            "tuition": 1 / 6,
            "quality": 1 / 6,
            "geo": 1 / 6,
            "risk": 1 / 6,
        },
        "weight_variance": {
            "tuition": 2.0,
            "school": 0.1,
            "major": 0.1,
            "geo": 0.1,
            "quality": 0.1,
            "risk": 0.1,
        },
    }

    max_dim, _ = select_ucb_dimension(state)
    assert max_dim == "tuition"

    plan = await _build_probe_plan(state)

    assert plan["probe_plan"][0]["probe"] == "tuition_value_relax"
    assert "tuition_value_relax" in [item["probe"] for item in plan["probe_plan"]]
    prompt_text = "\n".join(message.content for message in fake_llm.prompts[0])
    assert "probe_tuition_value_relax" in prompt_text


@pytest.mark.asyncio
async def test_ucb_override_forces_risk_probe(monkeypatch):
    monkeypatch.delenv("GAOKAOLLM_OFFLINE_DETERMINISTIC", raising=False)
    fake_llm = FakePlannerLLM()
    monkeypatch.setattr("app.graphs.nodes.radar.get_chat_model", lambda: fake_llm)

    state = {
        "constraints": {
            "score": 600,
            "major": "医学",
            "budget": 10000,
            "risk_preference": "stable",
            "selected_subjects": ["物理", "化学", "生物"],
        },
        "intent_axes": ["risk"],
        "implicit_weights": {
            "school": 1 / 6,
            "major": 1 / 6,
            "tuition": 1 / 6,
            "quality": 1 / 6,
            "geo": 1 / 6,
            "risk": 1 / 6,
        },
        "weight_variance": {
            "risk": 2.0,
            "school": 0.1,
            "major": 0.1,
            "geo": 0.1,
            "quality": 0.1,
            "tuition": 0.1,
        },
    }

    max_dim, _ = select_ucb_dimension(state)
    assert max_dim == "risk"

    plan = await _build_probe_plan(state)

    assert plan["probe_plan"][0]["probe"] == "risk_band_relax"
    prompt_text = "\n".join(message.content for message in fake_llm.prompts[0])
    assert "probe_risk_band_relax" in prompt_text


def test_ds_hesitate_keeps_weights_and_raises_variance():
    weights = {
        "school": 1 / 6,
        "major": 1 / 6,
        "tuition": 1 / 6,
        "quality": 1 / 6,
        "geo": 1 / 6,
        "risk": 1 / 6,
    }
    variance = {
        "school": 0.4,
        "major": 0.4,
        "tuition": 0.4,
        "quality": 0.4,
        "geo": 0.4,
        "risk": 0.4,
    }

    new_weights, new_variance = apply_feedback_update(
        weights,
        variance,
        FeedbackAnalysis(intent="hesitate", target_dimension="geo"),
    )

    assert new_weights == weights
    assert new_variance["geo"] > variance["geo"]


def test_feedback_signal_prefers_structured_probe_dimension_over_question_keywords():
    from app.graphs.nodes.preference_tracker import _feedback_analysis_from_signal

    analysis = _feedback_analysis_from_signal(
        {
            "latest_human_feedback": "ACCEPT",
            "latest_probe_target_dimension": "tuition",
        }
    )

    assert analysis is not None
    assert analysis.intent == "accept"
    assert analysis.target_dimension == "tuition"


def test_reject_target_feedback_uses_intent_mask_without_touching_side_axes():
    weights = {
        "school": 1 / 6,
        "major": 1 / 6,
        "tuition": 1 / 6,
        "quality": 1 / 6,
        "geo": 1 / 6,
        "risk": 1 / 6,
    }
    variance = {key: 0.6 for key in weights}

    new_weights, _new_variance = apply_feedback_update(
        weights,
        variance,
        FeedbackAnalysis(
            intent="reject",
            target_dimension="tuition",
            attribution="target",
        ),
        {
            "school": 0.4,
            "major": -0.8,
            "tuition": -0.5,
            "quality": 0.2,
            "geo": -0.3,
            "risk": 0.0,
        },
        {"school": 1.0, "tuition": 1.0},
    )

    assert new_weights["major"] == pytest.approx(weights["major"])
    assert new_weights["geo"] == pytest.approx(weights["geo"])
    assert new_weights["quality"] == pytest.approx(weights["quality"])
    assert new_weights["school"] != pytest.approx(weights["school"])
    assert new_weights["tuition"] != pytest.approx(weights["tuition"])


@pytest.mark.asyncio
async def test_continue_after_accepted_tuition_explores_other_axes(monkeypatch):
    monkeypatch.setenv("GAOKAOLLM_OFFLINE_DETERMINISTIC", "1")

    state = {
        "navigation_intent": "continue",
        "constraints": {
            "score": 600,
            "province": "浙江",
            "target_provinces": ["江苏", "浙江", "上海"],
            "major": "医学",
            "budget": 5500,
            "selected_subjects": ["物理", "化学", "生物"],
        },
        "accepted_relaxations": [{"dimension": "tuition"}],
        "implicit_weights": {
            "school": 1 / 6,
            "major": 1 / 6,
            "tuition": 1 / 6,
            "quality": 1 / 6,
            "geo": 1 / 6,
            "risk": 1 / 6,
        },
        "weight_variance": {
            "tuition": 1.0,
            "geo": 1.0,
            "major": 1.0,
            "risk": 1.0,
            "school": 0.1,
            "quality": 0.1,
        },
        "negotiation_turns": 3,
    }

    assert should_halt_for_global_baseline(state) is False
    assert select_ucb_dimension(state)[0] == "geo"

    plan = await _build_probe_plan(state)

    assert plan["probe_plan"][0]["probe"] == "major_geo_relax"
    assert "risk_band_relax" in [item["probe"] for item in plan["probe_plan"]]
    assert plan["ucb_target_dimension"] == "geo"


@pytest.mark.asyncio
async def test_reject_blocks_current_dimension(monkeypatch):
    state = {
        "latest_human_feedback": "REJECT",
        "latest_agent_probe_question": "是否愿意放宽专业匹配换学校层次？",
        "latest_question_kind": "tradeoff",
        "latest_probe_target_dimension": "major",
        "probe_plan": [{"probe": "major_geo_relax"}],
        "latest_pareto_diff": {
            "school": 0.3,
            "major": -1.0,
            "tuition": 0.0,
            "quality": 0.0,
            "geo": -0.3,
            "risk": 0.0,
        },
        "implicit_weights": {
            "school": 1 / 6,
            "major": 1 / 6,
            "tuition": 1 / 6,
            "quality": 1 / 6,
            "geo": 1 / 6,
            "risk": 1 / 6,
        },
        "weight_variance": {
            "major": 0.4,
            "risk": 1.5,
            "geo": 1.0,
            "school": 0.1,
            "tuition": 0.1,
            "quality": 0.1,
        },
        "factual_blocked_dimensions": [],
    }

    updated = await preference_tracker_node(state)

    assert updated["navigation_intent"] == "continue"
    assert "major" in updated["factual_blocked_dimensions"]
    assert "geo" in updated["factual_blocked_dimensions"]
    assert updated["feedback_analysis"] == {
        "intent": "reject",
        "target_dimension": "major",
        "attribution": "none",
    }


@pytest.mark.asyncio
async def test_hesitate_feedback_inflates_uncertainty_without_blocking(monkeypatch):
    state = {
        "latest_human_feedback": "HESITATE",
        "latest_agent_probe_question": "是否愿意放宽专业匹配换学校层次？",
        "latest_question_kind": "tradeoff",
        "latest_probe_target_dimension": "major",
        "probe_plan": [{"probe": "major_geo_relax"}],
        "latest_pareto_diff": {
            "school": 0.3,
            "major": -1.0,
            "tuition": 0.0,
            "quality": 0.0,
            "geo": -0.3,
            "risk": 0.0,
        },
        "latest_tradeoff_pair": {
            "option_a": {"school_name": "西藏大学", "major_name": "临床医学"},
            "option_b": {"school_name": "宁波大学", "major_name": "土木工程"},
        },
        "implicit_weights": {
            "school": 1 / 6,
            "major": 1 / 6,
            "tuition": 1 / 6,
            "quality": 1 / 6,
            "geo": 1 / 6,
            "risk": 1 / 6,
        },
        "weight_variance": {
            "major": 0.4,
            "risk": 1.5,
            "geo": 1.0,
            "school": 0.1,
            "tuition": 0.1,
            "quality": 0.1,
        },
        "factual_blocked_dimensions": [],
    }

    updated = await preference_tracker_node(state)

    assert updated["navigation_intent"] == "continue"
    assert updated["force_final_recommendation"] is False
    assert updated["factual_blocked_dimensions"] == []
    assert updated["implicit_weights"] == state["implicit_weights"]
    assert updated["weight_variance"]["major"] > state["weight_variance"]["major"]
    assert updated["probed_candidate_history"] == [
        "西藏大学|临床医学",
        "宁波大学|土木工程",
    ]
    assert updated["probed_pairs_history"] == [
        ["宁波大学|土木工程", "西藏大学|临床医学"]
    ]
    assert updated["feedback_analysis"] == {
        "intent": "hesitate",
        "target_dimension": "major",
        "attribution": "none",
    }


@pytest.mark.asyncio
async def test_side_reject_blocks_residual_dimension_without_weight_update(monkeypatch):
    weights = {
        "school": 1 / 6,
        "major": 1 / 6,
        "tuition": 1 / 6,
        "quality": 1 / 6,
        "geo": 1 / 6,
        "risk": 1 / 6,
    }
    state = {
        "latest_human_feedback": "REJECT_SIDE",
        "latest_agent_probe_question": "是否愿意放宽预算换学校层次？",
        "latest_question_kind": "tradeoff",
        "latest_probe_target_dimension": "tuition",
        "latest_pareto_diff": {
            "school": 0.4,
            "major": -0.8,
            "tuition": -0.5,
            "quality": 0.2,
            "geo": 0.0,
            "risk": 0.0,
        },
        "latest_residual_noise": {
            "top_dimension": "major",
            "top_value": 0.8,
            "threshold": 0.15,
            "requires_attribution": True,
        },
        "latest_tradeoff_pair": {
            "option_a": {"school_name": "温州医科大学", "major_name": "临床医学"},
            "option_b": {"school_name": "宁波大学", "major_name": "土木工程"},
        },
        "implicit_weights": dict(weights),
        "weight_variance": {key: 0.4 for key in weights},
        "factual_blocked_dimensions": [],
    }

    updated = await preference_tracker_node(state)

    assert updated["implicit_weights"] == weights
    assert "major" in updated["factual_blocked_dimensions"]
    assert "宁波大学|土木工程" in updated["probed_candidate_history"]
    assert updated["feedback_analysis"] == {
        "intent": "hesitate",
        "target_dimension": "tuition",
        "attribution": "side",
    }


@pytest.mark.asyncio
async def test_finalize_navigation_does_not_update_tradeoff_weights(monkeypatch):
    weights = {
        "school": 1 / 6,
        "major": 1 / 6,
        "tuition": 1 / 6,
        "quality": 1 / 6,
        "geo": 1 / 6,
        "risk": 1 / 6,
    }
    variance = {
        "school": 0.4,
        "major": 0.4,
        "tuition": 0.4,
        "quality": 0.4,
        "geo": 0.4,
        "risk": 0.4,
    }
    state = {
        "latest_human_feedback": "ACCEPT",
        "latest_agent_probe_question": "是否愿意放宽专业匹配换学校层次？",
        "latest_question_kind": "no_significant_tradeoff",
        "latest_probe_target_dimension": "major",
        "probe_plan": [{"probe": "major_geo_relax"}],
        "latest_pareto_diff": {
            "school": 0.3,
            "major": -1.0,
            "tuition": 0.0,
            "quality": 0.0,
            "geo": -0.3,
            "risk": 0.0,
        },
        "implicit_weights": dict(weights),
        "weight_variance": dict(variance),
        "factual_blocked_dimensions": [],
    }

    updated = await preference_tracker_node(state)

    assert updated["navigation_intent"] == "finalize"
    assert updated["force_final_recommendation"] is True
    assert updated["implicit_weights"] == weights
    assert updated["weight_variance"] == variance
    assert updated["feedback_analysis"] == {
        "intent": "hesitate",
        "target_dimension": "unknown",
        "attribution": "none",
    }


@pytest.mark.asyncio
async def test_explicit_finalize_signal_does_not_update_tradeoff_weights(monkeypatch):
    weights = {
        "school": 1 / 6,
        "major": 1 / 6,
        "tuition": 1 / 6,
        "quality": 1 / 6,
        "geo": 1 / 6,
        "risk": 1 / 6,
    }
    variance = {
        "school": 0.4,
        "major": 0.4,
        "tuition": 0.4,
        "quality": 0.4,
        "geo": 0.4,
        "risk": 0.4,
    }
    state = {
        "latest_human_feedback": "FINALIZE",
        "latest_agent_probe_question": "是否愿意放宽专业匹配换学校层次？",
        "latest_question_kind": "tradeoff",
        "latest_probe_target_dimension": "major",
        "latest_pareto_diff": {
            "school": 0.3,
            "major": -1.0,
            "tuition": 0.0,
            "quality": 0.0,
            "geo": -0.3,
            "risk": 0.0,
        },
        "implicit_weights": dict(weights),
        "weight_variance": dict(variance),
        "accepted_relaxations": [{"dimension": "geo"}],
        "factual_blocked_dimensions": ["tuition"],
    }

    updated = await preference_tracker_node(state)

    assert updated["navigation_intent"] == "finalize"
    assert updated["force_final_recommendation"] is True
    assert updated["implicit_weights"] == weights
    assert updated["weight_variance"] == variance
    assert updated["accepted_relaxations"] == [{"dimension": "geo"}]
    assert updated["factual_blocked_dimensions"] == ["tuition"]
    assert updated["feedback_analysis"] == {
        "intent": "hesitate",
        "target_dimension": "unknown",
        "attribution": "none",
    }


def test_bayesian_reject_increases_weight_without_global_variance_collapse():
    weights = {
        "school": 1 / 6,
        "major": 1 / 6,
        "tuition": 1 / 6,
        "quality": 1 / 6,
        "geo": 1 / 6,
        "risk": 1 / 6,
    }
    variance = {
        "school": 0.4,
        "major": 0.4,
        "tuition": 0.4,
        "quality": 0.4,
        "geo": 0.4,
        "risk": 0.4,
    }

    new_weights, new_variance = apply_feedback_update(
        weights,
        variance,
        FeedbackAnalysis(intent="reject", target_dimension="geo"),
    )

    assert new_weights["geo"] > weights["geo"]
    assert new_variance["geo"] <= variance["geo"] * 0.5
    for key in ("school", "major", "tuition", "quality", "risk"):
        assert new_variance[key] == pytest.approx(variance[key])


def test_relaxed_opportunities_drop_options_already_in_global_baseline():
    opportunities = {
        "tuition_value_relax": [
            {
                "school_name": "江苏大学",
                "major_name": "医学检验技术",
                "tuition": 7480,
            },
            {
                "school_name": "宁波大学",
                "major_name": "预防医学",
                "tuition": 6000,
            },
        ]
    }
    global_result = {
        "match": [
            {
                "school_name": "江苏大学",
                "major_name": "医学检验技术",
                "tuition": 5720,
            }
        ]
    }

    filtered = _without_global_baseline_duplicates(opportunities, global_result)

    rows = filtered["tuition_value_relax"]
    assert len(rows) == 1
    assert rows[0]["school_name"] == "宁波大学"


def test_empty_required_probe_is_skipped_when_other_opportunities_exist():
    plan = {
        "probe_plan": [
            {"probe": "strength_relax", "priority": 1},
            {"probe": "major_geo_relax", "priority": 2},
            {"probe": "risk_band_relax", "priority": 3},
        ],
        "opportunity_rankings": [
            "strength_relax",
            "major_geo_relax",
            "risk_band_relax",
        ],
        "ucb_required_probe": "strength_relax",
    }
    opportunities = {
        "strength_relax": [],
        "major_geo_relax": [{"school_name": "非预算跃迁"}],
        "risk_band_relax": [
            {"school_name": "风险候选", "risk_level": "chong", "risk_relax_level": 1}
        ],
    }

    adjusted = _plan_with_available_opportunities(plan, opportunities)

    assert adjusted["probe_plan"][0]["probe"] == "major_geo_relax"
    assert "strength_relax" not in adjusted["opportunity_rankings"]


def test_blocked_probe_dimensions_are_skipped_when_other_opportunities_exist():
    plan = {
        "probe_plan": [
            {"probe": "major_geo_relax", "priority": 1},
            {"probe": "risk_band_relax", "priority": 2},
        ],
        "opportunity_rankings": ["major_geo_relax", "risk_band_relax"],
    }
    opportunities = {
        "major_geo_relax": [{"school_name": "非预算跃迁"}],
        "risk_band_relax": [
            {"school_name": "风险候选", "risk_level": "chong", "risk_relax_level": 1}
        ],
    }

    adjusted = _plan_with_available_opportunities(
        plan,
        opportunities,
        {"factual_blocked_dimensions": ["major", "geo"]},
    )

    assert adjusted["probe_plan"][0]["probe"] == "risk_band_relax"
    assert "major_geo_relax" not in adjusted["opportunity_rankings"]


def test_single_bucket_risk_probe_can_compare_against_global_baseline():
    plan = {
        "probe_plan": [
            {"probe": "risk_band_relax", "priority": 1},
            {"probe": "major_geo_relax", "priority": 2},
        ],
        "opportunity_rankings": ["risk_band_relax", "major_geo_relax"],
    }
    opportunities = {
        "risk_band_relax": [
            {"school_name": "风险候选1", "risk_level": "chong", "risk_relax_level": 1},
            {"school_name": "风险候选2", "risk_level": "chong", "risk_relax_level": 1},
        ],
        "major_geo_relax": [{"school_name": "非预算跃迁"}],
    }

    adjusted = _plan_with_available_opportunities(plan, opportunities)

    assert adjusted["probe_plan"][0]["probe"] == "risk_band_relax"
    assert "risk_band_relax" in adjusted["opportunity_rankings"]


def test_safety_only_risk_probe_is_not_a_relaxation_opportunity():
    plan = {
        "probe_plan": [
            {"probe": "risk_band_relax", "priority": 1},
            {"probe": "major_geo_relax", "priority": 2},
        ],
        "opportunity_rankings": ["risk_band_relax", "major_geo_relax"],
    }
    opportunities = {
        "risk_band_relax": [
            {
                "school_name": "保底候选",
                "risk_level": "bao",
                "_phi_features": {"risk": 1.0},
            }
        ],
        "major_geo_relax": [{"school_name": "非预算跃迁"}],
    }

    adjusted = _plan_with_available_opportunities(plan, opportunities)

    assert adjusted["probe_plan"][0]["probe"] == "major_geo_relax"
    assert "risk_band_relax" not in adjusted["opportunity_rankings"]


def test_no_available_probe_returns_global_baseline_plan():
    plan = {
        "probe_plan": [
            {"probe": "strength_relax", "priority": 1},
            {"probe": "major_geo_relax", "priority": 2},
        ],
        "opportunity_rankings": ["strength_relax", "major_geo_relax"],
    }
    opportunities = {
        "strength_relax": [],
        "major_geo_relax": [{"school_name": "已屏蔽跃迁"}],
    }

    adjusted = _plan_with_available_opportunities(
        plan,
        opportunities,
        {"factual_blocked_dimensions": ["major", "geo"]},
    )

    assert adjusted["probe_plan"][0]["probe_name"] == "probe_global_baseline"
    assert adjusted["planner_source"] == "no_available_opportunities"
