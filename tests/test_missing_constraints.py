import pytest
from fastapi.testclient import TestClient
from langchain_core.messages import HumanMessage

from app.core.db_pg import close_pool
from app.graphs.workflow import build_graph
from main import app


@pytest.mark.asyncio
async def test_graph_asks_for_score_and_subjects_without_probing(capsys):
    graph = build_graph()

    result = await graph.ainvoke(
        {
            "messages": [HumanMessage(content="我想读临床医学")],
            "constraints": {},
            "baseline_results": [],
            "score_waste": 0,
            "pareto_opportunities": {},
            "missing_constraints": [],
        },
        config={"configurable": {"thread_id": "missing-score-subjects"}},
    )
    await close_pool()

    captured = capsys.readouterr().out
    assert "[gatekeeper]" in captured
    assert "[radar]" not in captured
    assert "[negotiator]" not in captured
    assert result["constraints"]["major"] == "临床医学"
    assert set(result["missing_constraints"]) == {"score", "selected_subjects"}
    assert "高考分数" in result["messages"][-1].content
    assert "选考科目" in result["messages"][-1].content


@pytest.mark.asyncio
async def test_graph_asks_only_for_subjects_when_score_exists(capsys):
    graph = build_graph()

    result = await graph.ainvoke(
        {
            "messages": [HumanMessage(content="600分想去北京读临床")],
            "constraints": {},
            "baseline_results": [],
            "score_waste": 0,
            "pareto_opportunities": {},
            "missing_constraints": [],
        },
        config={"configurable": {"thread_id": "missing-subjects-only"}},
    )
    await close_pool()

    captured = capsys.readouterr().out
    assert "[radar]" not in captured
    assert result["constraints"]["score"] == 600
    assert result["constraints"]["province"] == "北京"
    assert result["constraints"]["major"] == "临床医学"
    assert result["missing_constraints"] == ["selected_subjects"]
    assert "选考科目" in result["messages"][-1].content


@pytest.mark.asyncio
async def test_graph_continues_when_score_and_subjects_exist(capsys):
    graph = build_graph()

    result = await graph.ainvoke(
        {
            "messages": [HumanMessage(content="物化生，600分想去北京读临床")],
            "constraints": {},
            "baseline_results": [],
            "score_waste": 0,
            "pareto_opportunities": {},
            "missing_constraints": [],
        },
        config={"configurable": {"thread_id": "complete-constraints"}},
    )
    await close_pool()

    captured = capsys.readouterr().out
    assert "[radar]" in captured
    assert result["missing_constraints"] == []
    assert result["constraints"]["selected_subjects"] == ["物理", "化学", "生物"]
    assert result["messages"][-1].content


def test_api_memory_asks_then_uses_later_subjects():
    client = TestClient(app)
    thread_id = "api-missing-subjects-thread"

    first = client.post(
        "/api/v1/chat",
        json={"thread_id": thread_id, "message": "600分想去北京读临床"},
    )
    assert first.status_code == 200
    first_data = first.json()
    assert first_data["missing_constraints"] == ["selected_subjects"]
    assert "选考科目" in first_data["reply"]

    second = client.post(
        "/api/v1/chat",
        json={"thread_id": thread_id, "message": "物化生"},
    )
    assert second.status_code == 200
    second_data = second.json()
    assert second_data["missing_constraints"] == []
    assert second_data["constraints"]["score"] == 600
    assert second_data["constraints"]["province"] == "北京"
    assert second_data["constraints"]["major"] == "临床医学"
    assert second_data["constraints"]["selected_subjects"] == ["物理", "化学", "生物"]
