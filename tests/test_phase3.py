import pytest
from langchain_core.messages import AIMessage
from langchain_core.messages import HumanMessage

from app.core.db_pg import close_pool
from app.graphs.nodes.negotiator import negotiator_node
from app.graphs.workflow import build_graph
from tests._env_checks import require_database


class FakeLLM:
    prompts = []

    async def ainvoke(self, prompt):
        self.prompts.append(prompt)
        text = "\n".join(str(getattr(message, "content", "")) for message in prompt)
        if "最终推荐" in text or "冲、稳、保" in text:
            return AIMessage(
                content="偏好解释：系统根据当前取舍重新排序。最终推荐：收敛大学。"
            )
        return AIMessage(
            content="我看到一个可比较的放宽方案。你愿意继续比较这个方向吗？"
        )


class EmptyThenFinalLLM:
    calls = 0
    prompts = []

    async def ainvoke(self, prompt):
        self.prompts.append(prompt)
        self.calls += 1
        if self.calls == 1:
            return AIMessage(content="")
        return AIMessage(
            content="偏好解释：已重新排序。冲：收敛大学。稳：暂无。保：暂无。"
        )


@pytest.mark.asyncio
async def test_graph_invocation_interrupts_for_human_feedback(capsys, monkeypatch):
    require_database()
    monkeypatch.setattr("app.graphs.nodes.negotiator.get_chat_model", lambda: FakeLLM())
    graph = build_graph()
    config = {"configurable": {"thread_id": "phase3-test-thread"}}

    events = [
        event
        async for event in graph.astream(
            {
                "messages": [HumanMessage(content="物化生，600分必须在北京读临床")],
                "constraints": {},
                "baseline_results": [],
                "score_waste": 0,
                "pareto_opportunities": {},
            },
            config=config,
        )
    ]
    await close_pool()

    captured = capsys.readouterr().out
    assert "[gatekeeper]" in captured
    assert "[radar]" in captured
    assert "[negotiator]" in captured

    assert "__interrupt__" in events[-1]
    snapshot = graph.get_state(config)
    assert snapshot.values["pareto_opportunities"]["geo_relax"]
    assert snapshot.values["pareto_opportunities"]["major_relax"]
    assert snapshot.values["pareto_opportunities"]["major_geo_relax"]
    interrupt_value = snapshot.tasks[0].interrupts[0].value
    assert interrupt_value
    assert interrupt_value["latest_question_source"] == "llm"


@pytest.mark.asyncio
async def test_graph_invocation_outputs_final_recommendations_when_converged(
    monkeypatch,
):
    monkeypatch.delenv("GAOKAOLLM_OFFLINE_DETERMINISTIC", raising=False)
    fake_llm = FakeLLM()
    monkeypatch.setattr(
        "app.graphs.nodes.negotiator.get_chat_model",
        lambda: fake_llm,
    )

    result = await negotiator_node(
        {
            "messages": [HumanMessage(content="物化生，600分想去江浙沪读计算机")],
            "probe_plan": [{"probe_name": "probe_global_baseline", "args": {}}],
            "pareto_opportunities": {
                "global_baseline": {
                    "reach": [
                        {
                            "school_name": "收敛大学",
                            "school_province": "江苏",
                            "major_name": "计算机科学与技术",
                            "min_score": 598,
                            "tier": 3,
                            "_implicit_utility": 1.1,
                        }
                    ],
                    "match": [],
                    "safety": [],
                }
            },
            "implicit_weights": {
                "school": 0.4,
                "major": 0.2,
                "tuition": 0.1,
                "quality": 0.2,
                "geo": 0.1,
            },
            "weight_variance": {
                "school": 0.1,
                "major": 0.1,
                "tuition": 0.1,
                "quality": 0.1,
                "geo": 0.1,
            },
        }
    )

    final_message = result["messages"][-1].content
    assert "偏好解释" in final_message
    assert "收敛大学" in final_message
    assert result["latest_question_source"] == "llm"
    assert fake_llm.prompts
    prompt = fake_llm.prompts[-1]
    assert any(isinstance(message, HumanMessage) for message in prompt)
    system_text = "\n".join(str(getattr(message, "content", "")) for message in prompt)
    assert "不要说“精准推断”“真实权重”“极度看重”" in system_text
    assert "不要营销腔" in system_text


@pytest.mark.asyncio
async def test_final_recommendation_retries_empty_llm_content(monkeypatch):
    monkeypatch.delenv("GAOKAOLLM_OFFLINE_DETERMINISTIC", raising=False)
    fake_llm = EmptyThenFinalLLM()
    monkeypatch.setattr(
        "app.graphs.nodes.negotiator.get_reasoning_chat_model",
        lambda max_retries=None: fake_llm,
    )

    result = await negotiator_node(
        {
            "messages": [HumanMessage(content="请直接进入最终推荐")],
            "probe_plan": [{"probe_name": "probe_global_baseline", "args": {}}],
            "pareto_opportunities": {
                "global_baseline": {
                    "reach": [
                        {
                            "school_name": "收敛大学",
                            "school_province": "江苏",
                            "major_name": "计算机科学与技术",
                            "min_score": 598,
                            "tier": 3,
                            "_implicit_utility": 1.1,
                        }
                    ],
                    "match": [],
                    "safety": [],
                }
            },
            "implicit_weights": {
                "school": 0.4,
                "major": 0.2,
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
    assert fake_llm.calls == 2
    assert "收敛大学" in final_message
    assert any(isinstance(message, HumanMessage) for message in fake_llm.prompts[-1])
