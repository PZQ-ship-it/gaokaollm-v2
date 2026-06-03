import json
from typing import Any

import pytest
from langchain_core.messages import AIMessage
from langgraph.errors import GraphInterrupt

from app.graphs.nodes.negotiator import negotiator_node
from app.graphs.nodes.radar import radar_node


class FakeLLM:
    def __init__(self, content: str) -> None:
        self.content = content
        self.prompts: list[list[Any]] = []

    async def ainvoke(self, prompt: list[Any]) -> AIMessage:
        self.prompts.append(prompt)
        return AIMessage(content=self.content)


def _candidate(
    school: str,
    *,
    school_phi: float,
    geo_phi: float,
    major_phi: float = 1.0,
    utility: float = 1.0,
) -> dict[str, Any]:
    return {
        "school_name": school,
        "school_province": "江苏",
        "school_city": "南京",
        "major_name": "计算机科学与技术",
        "min_score": 598,
        "tier": 3,
        "_implicit_utility": utility,
        "_phi_features": {
            "school": school_phi,
            "major": major_phi,
            "tuition": 1.0,
            "quality": 0.7,
            "geo": geo_phi,
            "risk": 0.7,
        },
    }


@pytest.mark.asyncio
async def test_radar_halting_routes_to_global_baseline(monkeypatch):
    async def fake_probe_global_baseline(user_state, db=None, limit=5, **kwargs):
        return [_candidate("全局收网大学", school_phi=0.85, geo_phi=0.7)]

    monkeypatch.setattr(
        "app.graphs.nodes.radar.probe_global_baseline",
        fake_probe_global_baseline,
    )

    result = await radar_node(
        {
            "constraints": {
                "score": 600,
                "major": "计算机科学与技术",
                "selected_subjects": ["物理", "化学", "生物"],
                "budget": 100000,
            },
            "baseline_results": [{"school_name": "基准大学", "min_score": 590}],
            "score_waste": 5,
            "weight_variance": {
                "school": 0.1,
                "major": 0.1,
                "tuition": 0.1,
                "quality": 0.1,
                "geo": 0.1,
                "risk": 0.1,
            },
            "negotiation_turns": 1,
        }
    )

    assert result["probe_plan"][0]["probe_name"] == "probe_global_baseline"
    assert result["candidates"][0]["school_name"] == "全局收网大学"
    assert result["pareto_opportunities"]["global_baseline"]


@pytest.mark.asyncio
async def test_negotiator_pareto_question_interrupts_with_mrs_prompt(monkeypatch):
    fake_llm = FakeLLM("牺牲/放宽 geo 换取 school 跃迁，您能接受吗？")
    monkeypatch.delenv("GAOKAOLLM_OFFLINE_DETERMINISTIC", raising=False)
    monkeypatch.setattr("app.graphs.nodes.negotiator.get_chat_model", lambda: fake_llm)
    monkeypatch.setattr(
        "app.graphs.nodes.negotiator.interrupt",
        lambda question: (_ for _ in ()).throw(GraphInterrupt()),
    )

    state = {
        "probe_plan": [{"probe": "major_geo_relax", "priority": 1}],
        "candidates": [
            _candidate("方案A大学", school_phi=0.85, geo_phi=0.4, utility=1.2),
            _candidate("方案B大学", school_phi=0.4, geo_phi=1.0, utility=1.1),
        ],
        "negotiation_turns": 0,
    }

    with pytest.raises(GraphInterrupt):
        await negotiator_node(state)

    prompt_text = "\n".join(message.content for message in fake_llm.prompts[0])
    assert "志愿咨询顾问" in prompt_text
    assert "不要输出 tier" in prompt_text
    assert "candidate_a_user_facing" in prompt_text


@pytest.mark.asyncio
async def test_negotiator_global_baseline_outputs_xai_without_interrupt(monkeypatch):
    fake_llm = FakeLLM("偏好解释：系统根据权重发现您看重专业。最终推荐如下。")
    monkeypatch.delenv("GAOKAOLLM_OFFLINE_DETERMINISTIC", raising=False)
    monkeypatch.setattr("app.graphs.nodes.negotiator.get_chat_model", lambda: fake_llm)

    result = await negotiator_node(
        {
            "probe_plan": [{"probe_name": "probe_global_baseline", "args": {}}],
            "candidates": [
                _candidate("终局大学", school_phi=0.85, geo_phi=0.7, utility=1.3)
            ],
            "implicit_weights": {
                "school": 0.15,
                "major": 0.45,
                "tuition": 0.1,
                "quality": 0.2,
                "geo": 0.1,
                "risk": 0.0,
            },
            "weight_variance": {
                "school": 0.1,
                "major": 0.1,
                "tuition": 0.1,
                "quality": 0.1,
                "geo": 0.1,
                "risk": 0.1,
            },
        }
    )

    final_message = result["messages"][-1].content
    assert "解释" in final_message
    assert "偏好" in final_message
    assert "权重" in final_message
    assert result["latest_human_feedback"] is None
    prompt_text = json.dumps(
        [message.content for message in fake_llm.prompts[0]],
        ensure_ascii=False,
    )
    assert "显示性偏好解释" in prompt_text
