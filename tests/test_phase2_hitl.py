import pytest
from langchain_core.messages import HumanMessage
from langgraph.types import Command

from app.graphs.nodes.preference_tracker import FeedbackAnalysis
from app.graphs.workflow import build_graph


class FakeLLM:
    def __init__(self, content: str | None = None) -> None:
        self.content = content
        self.prompts = []

    async def ainvoke(self, prompt):
        from langchain_core.messages import AIMessage

        self.prompts.append(prompt)
        if self.content is not None:
            return AIMessage(content=self.content)
        payload = {}
        try:
            import json
            import re

            raw = str(prompt[-1].content)
            match = re.search(r"\{.*\}", raw, flags=re.S)
            payload = json.loads(match.group(0) if match else raw)
        except Exception:
            payload = {}
        candidate = payload.get("candidate_b_user_facing") or "这个放宽方案"
        return AIMessage(content=f"我看到 {candidate}。这类放宽是否可以继续比较？")


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
                "geo_relax_level": 1,
                "_implicit_utility": 1.05,
                "_phi_features": {
                    "school": 0.8,
                    "major": 0.8,
                    "tuition": 1.0,
                    "quality": 0.5,
                    "geo": 0.4,
                    "risk": 0.5,
                },
            }
        ],
        "risk_band_relax": [],
    }


@pytest.mark.asyncio
async def test_hitl_interrupt_resume_updates_preference_state(monkeypatch):
    monkeypatch.delenv("GAOKAOLLM_OFFLINE_DETERMINISTIC", raising=False)
    fake_llm = FakeLLM()

    async def fake_run_baseline(constraints):
        return [
            {
                "school_name": "基准大学",
                "school_province": "浙江",
                "school_city": "杭州",
                "major_name": "医学技术类",
                "min_score": 590,
                "tier": 2,
                "_implicit_utility": 1.0,
                "_phi_features": {
                    "school": 0.4,
                    "major": 0.8,
                    "tuition": 1.0,
                    "quality": 0.5,
                    "geo": 1.0,
                    "risk": 0.5,
                },
            }
        ]

    async def fake_run_all_probes(constraints, db=None, user_state=None):
        return _opportunities()

    async def fake_analyze_feedback(state):
        return FeedbackAnalysis(intent="accept", target_dimension="geo")

    monkeypatch.setattr("app.graphs.nodes.gatekeeper.run_baseline", fake_run_baseline)
    monkeypatch.setattr("app.graphs.nodes.radar.run_all_probes", fake_run_all_probes)
    monkeypatch.setattr(
        "app.graphs.nodes.radar.probe_global_baseline", fake_run_baseline
    )
    monkeypatch.setattr(
        "app.graphs.nodes.preference_tracker.analyze_feedback_with_llm",
        fake_analyze_feedback,
    )
    monkeypatch.setattr("app.graphs.nodes.negotiator.get_chat_model", lambda: fake_llm)

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
            "geo": 0.30,
        },
        "weight_variance": {
            "school": 1.0,
            "major": 1.0,
            "tuition": 1.0,
            "quality": 1.0,
            "geo": 1.2,
        },
    }

    events = [event async for event in app.astream(initial_state, config=config)]
    assert "__interrupt__" in events[-1]

    snapshot = app.get_state(config)
    interrupt_value = snapshot.tasks[0].interrupts[0].value
    assert (
        interrupt_value["latest_tradeoff_pair"]["option_b"]["school_name"]
        == "外省跃迁大学"
    )
    question = interrupt_value["text"]
    print(f"[interrupt] {question}")
    assert "换取" in question or "放宽" in question
    assert "外省跃迁大学" in question
    assert interrupt_value["latest_question_source"] == "llm"

    resume_text = "行，我可以接受出省"
    print(f"[resume] {resume_text}")
    resume_events = [
        event
        async for event in app.astream(
            Command(resume=resume_text),
            config=config,
        )
    ]
    assert any("preference_tracker" in event for event in resume_events)

    updated = app.get_state(config).values
    print(
        "[tracker] "
        f"weights={updated['implicit_weights']} "
        f"variance={updated['weight_variance']}"
    )
    assert updated["implicit_weights"]["geo"] < initial_state["implicit_weights"]["geo"]
    assert updated["weight_variance"]["geo"] < initial_state["weight_variance"]["geo"]
    assert updated["negotiation_turns"] == 1
    assert updated.get("latest_human_feedback") is None
    assert updated["feedback_analysis"]["intent"] == "accept"
    assert updated["feedback_analysis"]["target_dimension"] == "geo"
    assert not app.get_state(config).tasks
    assert updated["probe_plan"][0]["probe_name"] == "probe_global_baseline"
    assert updated["latest_question_kind"] == "finalize_offer"


@pytest.mark.asyncio
async def test_accepting_tuition_relaxation_records_accepted_candidate(monkeypatch):
    monkeypatch.delenv("GAOKAOLLM_OFFLINE_DETERMINISTIC", raising=False)
    fake_llm = FakeLLM()

    async def fake_run_baseline(constraints):
        return [
            {
                "school_name": "基准大学",
                "school_province": "浙江",
                "school_city": "杭州",
                "major_name": "医学技术类",
                "min_score": 590,
                "tuition": 5500,
                "tier": 2,
                "_implicit_utility": 1.0,
                "_phi_features": {
                    "school": 0.4,
                    "major": 0.8,
                    "tuition": 1.0,
                    "quality": 0.5,
                    "geo": 0.8,
                    "risk": 0.5,
                },
            }
        ]

    async def fake_run_all_probes(constraints, db=None, user_state=None):
        return {
            "geo_relax": [],
            "city_relax": [],
            "major_relax": [],
            "strength_relax": [],
            "major_quality_relax": [],
            "tuition_value_relax": [
                {
                    "school_name": "不应被接受大学",
                    "school_province": "浙江",
                    "school_city": "宁波",
                    "major_name": "医学技术类",
                    "min_score": 595,
                    "tuition": 6200,
                    "tuition_delta": 700,
                    "_implicit_utility": 1.1,
                    "_phi_features": {
                        "school": 0.6,
                        "major": 0.8,
                        "tuition": 0.7,
                        "quality": 0.6,
                        "geo": 0.8,
                        "risk": 0.5,
                    },
                },
                {
                    "school_name": "江苏大学",
                    "school_province": "江苏",
                    "school_city": "镇江",
                    "major_name": "医学检验技术",
                    "min_score": 597,
                    "tuition": 7480,
                    "tuition_delta": 1980,
                    "_implicit_utility": 1.2,
                    "_phi_features": {
                        "school": 0.9,
                        "major": 0.8,
                        "tuition": 0.6,
                        "quality": 0.7,
                        "geo": 0.8,
                        "risk": 0.5,
                    },
                },
            ],
            "employment_outcome_relax": [],
            "region_tree_relax": [],
            "major_geo_relax": [],
            "risk_band_relax": [],
        }

    async def fake_analyze_feedback(state):
        return FeedbackAnalysis(intent="accept", target_dimension="tuition")

    monkeypatch.setattr("app.graphs.nodes.gatekeeper.run_baseline", fake_run_baseline)
    monkeypatch.setattr("app.graphs.nodes.radar.run_all_probes", fake_run_all_probes)
    monkeypatch.setattr(
        "app.graphs.nodes.radar.probe_global_baseline", fake_run_baseline
    )
    monkeypatch.setattr(
        "app.graphs.nodes.preference_tracker.analyze_feedback_with_llm",
        fake_analyze_feedback,
    )
    monkeypatch.setattr("app.graphs.nodes.negotiator.get_chat_model", lambda: fake_llm)

    app = build_graph()
    config = {"configurable": {"thread_id": "test_thread_tuition_accept"}}
    initial_state = {
        "messages": [HumanMessage(content="我愿意小幅放宽当前问题里的底线。")],
        "constraints": {
            "score": 600,
            "province": "浙江",
            "major": "医学",
            "budget": 5500,
            "selected_subjects": ["物理", "化学", "生物"],
        },
        "baseline_results": await fake_run_baseline({}),
        "score_waste": 0,
        "pareto_opportunities": await fake_run_all_probes({}),
        "probe_plan": [{"probe": "tuition_value_relax", "priority": 1}],
        "opportunity_rankings": ["tuition_value_relax"],
        "implicit_weights": {
            "school": 0.2,
            "major": 0.2,
            "tuition": 0.2,
            "quality": 0.2,
            "geo": 0.2,
        },
        "weight_variance": {
            "school": 1.0,
            "major": 1.0,
            "tuition": 1.2,
            "quality": 1.0,
            "geo": 1.0,
        },
    }

    events = [event async for event in app.astream(initial_state, config=config)]
    assert "__interrupt__" in events[-1]
    interrupt_value = events[-1]["__interrupt__"][0].value
    assert (
        interrupt_value["latest_tradeoff_pair"]["option_b"]["school_name"] == "江苏大学"
    )
    assert "江苏大学" in interrupt_value["text"]
    assert interrupt_value["latest_question_source"] == "llm"
    resume_events = [
        event
        async for event in app.astream(
            Command(resume="可以接受这个预算放宽"), config=config
        )
    ]
    assert any("preference_tracker" in event for event in resume_events)

    updated = app.get_state(config).values
    accepted = updated["accepted_relaxations"]
    assert accepted[0]["dimension"] == "tuition"
    assert accepted[0]["accepted_budget"] == 7480
    assert accepted[0]["candidate"]["school_name"] == "江苏大学"
