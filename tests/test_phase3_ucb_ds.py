import json
from typing import Any

import pytest
from langchain_core.messages import AIMessage

from app.graphs.nodes.preference_tracker import (
    FeedbackAnalysis,
    apply_feedback_update,
)
from app.graphs.nodes.radar import _build_probe_plan, select_ucb_dimension


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
            "school": 0.25,
            "major": 0.25,
            "tuition": 0.25,
            "quality": 0.25,
            "geo": 0.25,
        },
        "weight_variance": {
            "tuition": 2.0,
            "school": 0.1,
            "major": 0.1,
            "geo": 0.1,
            "quality": 0.1,
        },
    }

    max_dim, _ = select_ucb_dimension(state)
    assert max_dim == "tuition"

    plan = await _build_probe_plan(state)

    assert plan["probe_plan"][0]["probe"] == "tuition_value_relax"
    assert "tuition_value_relax" in [item["probe"] for item in plan["probe_plan"]]
    prompt_text = "\n".join(message.content for message in fake_llm.prompts[0])
    assert "probe_tuition_value_relax" in prompt_text


def test_ds_hesitate_keeps_weights_and_raises_variance():
    weights = {
        "school": 0.2,
        "major": 0.2,
        "tuition": 0.2,
        "quality": 0.2,
        "geo": 0.2,
    }
    variance = {
        "school": 0.4,
        "major": 0.4,
        "tuition": 0.4,
        "quality": 0.4,
        "geo": 0.4,
    }

    new_weights, new_variance = apply_feedback_update(
        weights,
        variance,
        FeedbackAnalysis(intent="hesitate", target_dimension="geo"),
    )

    assert new_weights == weights
    assert new_variance["geo"] > variance["geo"]


def test_bayesian_reject_increases_weight_and_collapses_variance():
    weights = {
        "school": 0.2,
        "major": 0.2,
        "tuition": 0.2,
        "quality": 0.2,
        "geo": 0.2,
    }
    variance = {
        "school": 0.4,
        "major": 0.4,
        "tuition": 0.4,
        "quality": 0.4,
        "geo": 0.4,
    }

    new_weights, new_variance = apply_feedback_update(
        weights,
        variance,
        FeedbackAnalysis(intent="reject", target_dimension="geo"),
    )

    assert new_weights["geo"] > weights["geo"]
    assert new_variance["geo"] <= variance["geo"] * 0.5
