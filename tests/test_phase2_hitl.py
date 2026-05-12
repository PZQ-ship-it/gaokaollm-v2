import pytest
from langchain_core.messages import HumanMessage
from langgraph.types import Command

from app.graphs.workflow import build_graph


def _opportunities():
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
                "school_name": "外省跃迁大学",
                "school_province": "江苏",
                "school_city": "南京",
                "major_name": "计算机科学与技术",
                "min_score": 598,
                "tier": 3,
                "_implicit_utility": 1.05,
            }
        ],
        "risk_band_relax": [],
    }


@pytest.mark.asyncio
async def test_hitl_interrupt_resume_updates_preference_state(monkeypatch):
    monkeypatch.setenv("GAOKAOLLM_OFFLINE_DETERMINISTIC", "1")

    async def fake_run_baseline(constraints):
        return [{"school_name": "基准大学", "min_score": 590, "tier": 2}]

    async def fake_run_all_probes(constraints, db=None, user_state=None):
        return _opportunities()

    monkeypatch.setattr("app.graphs.nodes.gatekeeper.run_baseline", fake_run_baseline)
    monkeypatch.setattr("app.graphs.nodes.radar.run_all_probes", fake_run_all_probes)

    app = build_graph()
    config = {"configurable": {"thread_id": "test_thread_001"}}
    initial_state = {
        "messages": [HumanMessage(content="我想去江浙沪读计算机，求稳。")],
        "constraints": {
            "score": 600,
            "province": "浙江",
            "major": "计算机科学与技术",
            "budget": 100000,
            "selected_subjects": ["物理", "化学", "生物"],
        },
        "baseline_results": [],
        "score_waste": 0,
        "pareto_opportunities": _opportunities(),
        "probe_plan": [{"probe": "major_geo_relax", "priority": 1}],
        "opportunity_rankings": ["major_geo_relax"],
        "implicit_weights": {
            "school": 0.25,
            "major": 0.25,
            "tuition": 0.25,
            "quality": 0.25,
            "geo": 0.25,
        },
        "weight_variance": {
            "school": 1.0,
            "major": 1.0,
            "tuition": 1.0,
            "quality": 1.0,
            "geo": 1.0,
        },
    }

    events = [event async for event in app.astream(initial_state, config=config)]
    assert "__interrupt__" in events[-1]

    snapshot = app.get_state(config)
    question = snapshot.tasks[0].interrupts[0].value
    assert "能接受" in question
    assert "外省跃迁大学" in question

    resume_events = [
        event
        async for event in app.astream(
            Command(resume="行，我可以接受出省"),
            config=config,
        )
    ]
    assert any("preference_tracker" in event for event in resume_events)

    updated = app.get_state(config).values
    assert (
        updated["implicit_weights"]["school"]
        > initial_state["implicit_weights"]["school"]
    )
    assert (
        updated["weight_variance"]["school"]
        < initial_state["weight_variance"]["school"]
    )
    assert updated["negotiation_turns"] == 1
    assert updated.get("latest_human_feedback") is None
    assert app.get_state(config).tasks
