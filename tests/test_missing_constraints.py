import pytest
from fastapi.testclient import TestClient
from langchain_core.messages import HumanMessage

from app.core.db_pg import close_pool
from app.graphs.nodes.gatekeeper import _extract_constraints, _fallback_extract
from app.graphs.workflow import build_graph
from main import app
from tests._env_checks import require_database


@pytest.mark.asyncio
async def test_graph_asks_for_score_and_subjects_without_probing(capsys, monkeypatch):
    monkeypatch.setenv("GAOKAOLLM_OFFLINE_DETERMINISTIC", "1")
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
    assert result["original_constraints"]["major"] == "临床医学"
    assert set(result["missing_constraints"]) == {"score", "selected_subjects"}
    assert "高考分数" in result["messages"][-1].content
    assert "选考科目" in result["messages"][-1].content


@pytest.mark.asyncio
async def test_graph_asks_only_for_subjects_when_score_exists(capsys, monkeypatch):
    monkeypatch.setenv("GAOKAOLLM_OFFLINE_DETERMINISTIC", "1")
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
    assert result["original_constraints"]["major"] == "临床医学"
    assert result["missing_constraints"] == ["selected_subjects"]
    assert "选考科目" in result["messages"][-1].content


@pytest.mark.asyncio
async def test_graph_continues_when_score_and_subjects_exist(capsys):
    require_database()
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
    require_database()
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


def test_fallback_extracts_zhejiang_candidate_and_jiangzhehu_target_scope():
    extracted = _fallback_extract(
        "我是浙江考生，分数600，选科物理、化学、生物，"
        "想读医学相关专业，只看江浙沪的学校，预算每年5500元以内。"
    )

    assert extracted["score"] == 600
    assert extracted["province"] == "浙江"
    assert extracted["target_provinces"] == ["江苏", "浙江", "上海"]
    assert extracted["budget"] == 5500
    assert extracted["selected_subjects"] == ["物理", "化学", "生物"]


def test_fallback_extracts_subjects_with_chinese_separators():
    extracted = _fallback_extract(
        "我是浙江考生，分数600，选科物理、化学、生物，想读医学相关专业。"
    )

    assert extracted["selected_subjects"] == ["物理", "化学", "生物"]
    assert extracted["major"] == "医学"


@pytest.mark.asyncio
async def test_extract_constraints_preserves_original_text_when_rewrite_is_bad(
    monkeypatch,
):
    monkeypatch.setenv("GAOKAOLLM_OFFLINE_DETERMINISTIC", "1")
    text = (
        "我是浙江考生，分数600，选科物理、化学、生物，想读医学相关专业，只看江浙沪的学校，预算每年5500元以内。"
        "\n"
        "损坏的改写文本"
    )

    extracted = await _extract_constraints(text, {})

    assert extracted["selected_subjects"] == ["物理", "化学", "生物"]
    assert extracted["budget"] == 5500
    assert extracted["target_provinces"] == ["江苏", "浙江", "上海"]
