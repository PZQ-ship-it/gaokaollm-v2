import pytest
from langchain_core.messages import HumanMessage

from app.core.db_pg import close_pool
from app.graphs.workflow import build_graph
from tests._env_checks import require_database


@pytest.mark.asyncio
async def test_graph_invocation_interrupts_for_human_feedback(capsys):
    require_database()
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
    assert snapshot.tasks[0].interrupts[0].value


@pytest.mark.asyncio
async def test_graph_invocation_outputs_final_recommendations_when_converged(
    monkeypatch,
):
    monkeypatch.setenv("GAOKAOLLM_OFFLINE_DETERMINISTIC", "1")

    async def fake_run_baseline(constraints):
        return [{"school_name": "基准大学", "min_score": 590, "tier": 2}]

    async def fake_run_all_probes(constraints, db=None, user_state=None):
        return {
            "geo_relax": [],
            "city_relax": [],
            "major_relax": [],
            "strength_relax": [],
            "major_quality_relax": [],
            "tuition_value_relax": [],
            "employment_outcome_relax": [],
            "region_tree_relax": [],
            "major_geo_relax": [
                {
                    "school_name": "收敛大学",
                    "school_province": "江苏",
                    "major_name": "计算机科学与技术",
                    "min_score": 598,
                    "tier": 3,
                    "_implicit_utility": 1.1,
                }
            ],
            "risk_band_relax": [],
        }

    monkeypatch.setattr("app.graphs.nodes.gatekeeper.run_baseline", fake_run_baseline)
    monkeypatch.setattr("app.graphs.nodes.radar.run_all_probes", fake_run_all_probes)

    graph = build_graph()

    result = await graph.ainvoke(
        {
            "messages": [HumanMessage(content="物化生，600分想去江浙沪读计算机")],
            "constraints": {
                "score": 600,
                "province": "浙江",
                "major": "计算机科学与技术",
                "budget": 100000,
                "selected_subjects": ["物理", "化学", "生物"],
            },
            "baseline_results": [],
            "score_waste": 0,
            "pareto_opportunities": {},
            "probe_plan": [{"probe": "major_geo_relax", "priority": 1}],
            "opportunity_rankings": ["major_geo_relax"],
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
        },
        config={"configurable": {"thread_id": "phase3-converged-thread"}},
    )

    final_message = result["messages"][-1].content
    assert "Top-3" in final_message
    assert "收敛大学" in final_message
