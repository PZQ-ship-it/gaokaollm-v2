import asyncio

import httpx
import pytest
from langgraph.types import interrupt

from app.api import chat_api
from app.core.llm_client import emit_text_stream_delta
from app.schemas.state import AgentState
from main import app


async def fake_semantic_normalizer_node(state: AgentState) -> dict:
    await asyncio.sleep(0.01)
    return {
        "rewritten_query": "浙江 600 物化生 医学 江浙沪 预算5500",
        "constraints": {"score": 600},
        "messages": state.get("messages", []),
    }


async def fake_gatekeeper_node(state: AgentState) -> dict:
    await asyncio.sleep(0.01)
    return {
        "constraints": {
            **state.get("constraints", {}),
            "province": "浙江",
            "major": "医学",
            "budget": 5500,
            "selected_subjects": ["物理", "化学", "生物"],
        },
        "missing_constraints": [],
    }


async def fake_radar_node(state: AgentState) -> dict:
    await asyncio.sleep(0.01)
    return {
        "baseline_results": [{"school_name": "温州医科大学", "major_name": "医学"}],
        "probe_plan": [{"probe_name": "probe_tuition_value_relax"}],
        "pareto_opportunities": {
            "tuition_value_relax": [
                {"school_name": "上海海洋大学", "major_name": "生物医学工程"}
            ]
        },
        "implicit_weights": {"school": 0.2, "major": 0.2},
    }


async def fake_negotiator_node(state: AgentState) -> dict:
    await asyncio.sleep(0.01)
    await emit_text_stream_delta("你是否愿意", label="fake_negotiator")
    await emit_text_stream_delta("小幅放宽预算？", label="fake_negotiator")
    user_reply = interrupt(
        {
            "text": "你是否愿意小幅放宽预算，换取更高学校层次？",
            "latest_question_kind": "tradeoff",
            "latest_question_source": "llm",
            "latest_probe_target_dimension": "tuition",
        }
    )
    return {
        "latest_human_feedback": str(user_reply),
        "latest_agent_probe_question": "你是否愿意小幅放宽预算，换取更高学校层次？",
    }


async def fake_long_unpunctuated_negotiator_node(state: AgentState) -> dict:
    await emit_text_stream_delta(
        "这是一段较长的取舍问题开头用于验证流式输出不必等待句末标点并且仍然保持连续可读",
        label="fake_negotiator",
    )
    user_reply = interrupt(
        {
            "text": "这是一段较长的取舍问题开头用于验证流式输出不必等待句末标点并且仍然保持连续可读。",
            "latest_question_kind": "tradeoff",
            "latest_question_source": "llm",
            "latest_probe_target_dimension": "tuition",
        }
    )
    return {
        "latest_human_feedback": str(user_reply),
        "latest_agent_probe_question": "这是一段较长的取舍问题开头用于验证流式输出不必等待句末标点并且仍然保持连续可读。",
    }


async def fake_preference_tracker_node(state: AgentState) -> dict:
    return {
        "latest_human_feedback": None,
        "feedback_analysis": {
            "intent": "reject"
            if state.get("latest_human_feedback") == "REJECT"
            else "accept",
            "target_dimension": state.get("latest_probe_target_dimension"),
        },
        "negotiation_turns": 1,
    }


def test_running_payload_hides_draft_candidates_until_question():
    thread_id = "draft-candidate-hide-test"
    chat_api._RUNS[thread_id] = {
        "status": "running",
        "mode": "message",
        "completed_nodes": ["semantic_normalizer", "gatekeeper", "radar"],
    }
    result = {
        "baseline_results": [
            {"school_name": "低分职业技术学院", "major_name": "护理", "min_score": 480}
        ],
        "pareto_opportunities": {
            "tuition_value_relax": [
                {"school_name": "中间探针候选", "major_name": "医学技术"}
            ]
        },
        "candidates": [{"school_name": "中间候选池"}],
    }

    payload = chat_api._payload_from_values(
        thread_id=thread_id,
        result=result,
        mode="message",
        include_pending=False,
    )

    assert payload["workflow_progress"]["radar"] == "ok"
    assert payload["baseline_results"] == []
    assert payload["pareto_opportunities"] == {}
    assert payload["candidates"] == []

    payload_with_question = chat_api._payload_from_values(
        thread_id=thread_id,
        result={
            **result,
            "latest_agent_probe_question": "正式取舍问题已经生成。",
        },
        mode="message",
        include_pending=False,
    )

    assert payload_with_question["baseline_results"][0]["school_name"] == (
        "低分职业技术学院"
    )
    assert payload_with_question["pareto_opportunities"]
    assert payload_with_question["candidates"]


@pytest.mark.asyncio
async def test_async_chat_run_exposes_intermediate_state(monkeypatch):
    monkeypatch.setattr(
        "app.graphs.workflow.semantic_normalizer_node",
        fake_semantic_normalizer_node,
    )
    monkeypatch.setattr("app.graphs.workflow.gatekeeper_node", fake_gatekeeper_node)
    monkeypatch.setattr("app.graphs.workflow.radar_node", fake_radar_node)
    monkeypatch.setattr("app.graphs.workflow.negotiator_node", fake_negotiator_node)
    monkeypatch.setattr(
        "app.graphs.workflow.preference_tracker_node",
        fake_preference_tracker_node,
    )
    monkeypatch.setattr(chat_api, "graph", chat_api.build_graph())
    chat_api._RUNS.clear()

    thread_id = "async-state-api-test"
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://testserver",
    ) as client:
        started = await client.post(
            "/api/v1/chat/runs",
            json={
                "thread_id": thread_id,
                "message": "我是浙江考生，分数600，选科物理、化学、生物。",
            },
        )

        assert started.status_code == 200
        first = started.json()
        assert first["status"] in {"running", "completed"}
        assert first["workflow_progress"]["semantic_normalizer"] in {"pending", "ok"}

        final = None
        for _ in range(30):
            state = await client.get(f"/api/v1/chat/state/{thread_id}")
            assert state.status_code == 200
            payload = state.json()
            if payload["status"] == "interrupt":
                final = payload
                break
            await asyncio.sleep(0.03)

        invalid_feedback = await client.post(
            "/api/v1/chat",
            json={
                "thread_id": thread_id,
                "message": "不能接受这个取舍，请保留我的底线。",
                "action": "feedback",
            },
        )
        assert invalid_feedback.status_code == 400
        assert "FINALIZE" in invalid_feedback.json()["detail"]

        feedback = await client.post(
            "/api/v1/chat",
            json={
                "thread_id": thread_id,
                "message": "REJECT",
                "action": "feedback",
            },
        )
        assert feedback.status_code == 200
        feedback_payload = feedback.json()
        assert feedback_payload["feedback_analysis"] == {
            "intent": "reject",
            "target_dimension": "tuition",
            "attribution": "none",
        }

    assert final is not None
    assert final["pending_interrupt"] == ("你是否愿意小幅放宽预算，换取更高学校层次？")
    assert final["workflow_progress"]["semantic_normalizer"] == "ok"
    assert final["workflow_progress"]["gatekeeper"] == "ok"
    assert final["workflow_progress"]["radar"] == "ok"
    assert final["workflow_progress"]["negotiator"] == "ok"
    assert final["workflow_progress"]["preference_tracker"] == "waiting"
    assert final["baseline_results"][0]["school_name"] == "温州医科大学"


@pytest.mark.asyncio
async def test_stream_chat_run_emits_text_deltas_and_final_state(monkeypatch):
    monkeypatch.setattr(
        "app.graphs.workflow.semantic_normalizer_node",
        fake_semantic_normalizer_node,
    )
    monkeypatch.setattr("app.graphs.workflow.gatekeeper_node", fake_gatekeeper_node)
    monkeypatch.setattr("app.graphs.workflow.radar_node", fake_radar_node)
    monkeypatch.setattr("app.graphs.workflow.negotiator_node", fake_negotiator_node)
    monkeypatch.setattr(chat_api, "graph", chat_api.build_graph())
    chat_api._RUNS.clear()

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://testserver",
    ) as client:
        response = await client.post(
            "/api/v1/chat/runs/stream",
            json={
                "thread_id": "stream-state-api-test",
                "message": "我是浙江考生，分数600，选科物理、化学、生物。",
            },
        )

    assert response.status_code == 200
    body = response.text
    assert "event: delta" in body
    assert "你是否愿意小幅放宽预算？" in body
    assert "event: state" in body
    assert "event: final" in body
    assert '"status": "interrupt"' in body


def test_stream_flush_index_flushes_long_text_without_boundary():
    text = "long user visible pareto question without sentence boundary yet"

    flush_index = chat_api._stream_flush_index(text, 0)

    assert 0 < flush_index < len(text)


@pytest.mark.asyncio
async def test_stream_chat_run_flushes_long_text_before_sentence_boundary(monkeypatch):
    monkeypatch.setattr(
        "app.graphs.workflow.semantic_normalizer_node",
        fake_semantic_normalizer_node,
    )
    monkeypatch.setattr("app.graphs.workflow.gatekeeper_node", fake_gatekeeper_node)
    monkeypatch.setattr("app.graphs.workflow.radar_node", fake_radar_node)
    monkeypatch.setattr(
        "app.graphs.workflow.negotiator_node",
        fake_long_unpunctuated_negotiator_node,
    )
    monkeypatch.setattr(chat_api, "graph", chat_api.build_graph())
    chat_api._RUNS.clear()

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://testserver",
    ) as client:
        response = await client.post(
            "/api/v1/chat/runs/stream",
            json={
                "thread_id": "stream-long-text-api-test",
                "message": "我是浙江考生，分数600，选科物理、化学、生物。",
            },
        )

    assert response.status_code == 200
    body = response.text
    assert "event: delta" in body
    assert "这是一段较长的取舍问题开头" in body
    assert "event: final" in body
