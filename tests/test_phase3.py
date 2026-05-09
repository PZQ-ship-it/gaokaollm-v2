import pytest
from langchain_core.messages import HumanMessage

from app.core.db_pg import close_pool
from app.graphs.workflow import build_graph
from tests._env_checks import require_database


@pytest.mark.asyncio
async def test_graph_invocation_negotiates_with_real_probe_data(capsys):
    require_database()
    graph = build_graph()

    result = await graph.ainvoke(
        {
            "messages": [HumanMessage(content="物化生，600分必须在北京读临床")],
            "constraints": {},
            "baseline_results": [],
            "score_waste": 0,
            "pareto_opportunities": {},
        },
        config={"configurable": {"thread_id": "phase3-test-thread"}},
    )
    await close_pool()

    captured = capsys.readouterr().out
    assert "[gatekeeper]" in captured
    assert "[radar]" in captured
    assert "[negotiator]" in captured

    assert result["baseline_results"] == []
    assert result["pareto_opportunities"]["geo_relax"]
    assert result["pareto_opportunities"]["major_relax"]
    assert result["pareto_opportunities"]["major_geo_relax"]

    final_message = result["messages"][-1].content
    assert "选项A" in final_message
    assert "选项B" in final_message
