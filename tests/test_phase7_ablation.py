import csv
import json
import shutil
from pathlib import Path
from typing import Any

import pytest
from langchain_core.messages import AIMessage

from app.evaluation.benchmark import get_evaluation_dataset, run_ablation_benchmark
from app.evaluation.simulator import UserSimulator
from app.graphs.nodes.preference_tracker import preference_tracker_node
from app.graphs.nodes.radar import radar_node
from app.graphs.workflow import build_graph


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
                            "probe": "geo_relax",
                            "priority": 1,
                            "reason": "fake no-ucb planner choice",
                        }
                    ],
                    "opportunity_rankings": ["geo_relax"],
                    "clarification_hint": None,
                },
                ensure_ascii=False,
            )
        )


def _candidate(school: str, utility: float = 1.0) -> dict[str, Any]:
    return {
        "school_name": school,
        "school_province": "江苏",
        "school_city": "南京",
        "major_name": "计算机科学与技术",
        "min_score": 598,
        "tier": 3,
        "_implicit_utility": utility,
        "_phi_features": {
            "school": 0.85,
            "major": 1.0,
            "tuition": 1.0,
            "quality": 0.7,
            "geo": 0.4,
            "risk": 0.7,
        },
    }


def _opportunities() -> dict[str, list[dict[str, Any]]]:
    return {
        "geo_relax": [_candidate("随机地理探针大学", utility=1.1)],
        "city_relax": [],
        "major_relax": [],
        "strength_relax": [],
        "major_quality_relax": [],
        "tuition_value_relax": [],
        "employment_outcome_relax": [],
        "region_tree_relax": [],
        "major_geo_relax": [
            _candidate("跨省985大学", utility=1.2),
            _candidate("本省稳妥大学", utility=1.0),
        ],
        "risk_band_relax": [],
    }


@pytest.mark.asyncio
async def test_ucb_ablation_bypasses_forced_probe(monkeypatch):
    fake_llm = FakePlannerLLM()
    monkeypatch.delenv("GAOKAOLLM_OFFLINE_DETERMINISTIC", raising=False)
    monkeypatch.setattr("app.graphs.nodes.radar.get_chat_model", lambda: fake_llm)
    monkeypatch.setattr(
        "app.graphs.nodes.radar.random.choice", lambda items: "geo_relax"
    )

    async def fake_run_all_probes(constraints, db=None, user_state=None):
        return _opportunities()

    monkeypatch.setattr("app.graphs.nodes.radar.run_all_probes", fake_run_all_probes)

    result = await radar_node(
        {
            "constraints": {
                "score": 600,
                "major": "计算机",
                "budget": 100000,
                "selected_subjects": ["物理", "化学", "生物"],
            },
            "baseline_results": [{"school_name": "基准大学", "min_score": 590}],
            "score_waste": 5,
            "implicit_weights": {
                "school": 1 / 6,
                "major": 1 / 6,
                "tuition": 1 / 6,
                "quality": 1 / 6,
                "geo": 1 / 6,
                "risk": 1 / 6,
            },
            "weight_variance": {
                "tuition": 2.0,
                "school": 0.1,
                "major": 0.1,
                "quality": 0.1,
                "geo": 0.1,
                "risk": 0.1,
            },
        },
        config={"configurable": {"ablation_mode": "no_ucb"}},
    )

    assert result["probe_plan"][0]["probe"] == "geo_relax"
    assert result["probe_plan"][0]["probe"] != "tuition_value_relax"
    prompt_text = "\n".join(message.content for message in fake_llm.prompts[0])
    assert "UCB" not in prompt_text
    assert "probe_tuition_value_relax" not in prompt_text
    assert "强制" not in prompt_text


@pytest.mark.asyncio
async def test_tracker_ablation_keeps_weights_and_variance(monkeypatch):
    weights = {
        "school": 0.4,
        "major": 0.2,
        "tuition": 0.1,
        "quality": 0.2,
        "geo": 0.1,
        "risk": 0.0,
    }
    variance = {
        "school": 0.3,
        "major": 0.4,
        "tuition": 0.5,
        "quality": 0.6,
        "geo": 0.7,
        "risk": 0.8,
    }

    result = await preference_tracker_node(
        {
            "implicit_weights": dict(weights),
            "weight_variance": dict(variance),
            "latest_human_feedback": "ACCEPT",
            "latest_agent_probe_question": "是否牺牲地域换取学校？",
            "latest_pareto_diff": {"school": 0.5, "geo": -0.4},
        },
        config={"configurable": {"ablation_mode": "no_tracker"}},
    )

    assert result["implicit_weights"] == weights
    assert result["weight_variance"] == variance
    assert result["latest_human_feedback"] is None
    assert result["latest_agent_probe_question"] is None
    assert result["latest_pareto_diff"] is None


def test_ablation_benchmark_exports_csv(monkeypatch):
    monkeypatch.setenv("GAOKAOLLM_OFFLINE_DETERMINISTIC", "1")

    async def fake_run_baseline(constraints):
        return [{"school_name": "基准大学", "min_score": 590, "tier": 2}]

    async def fake_run_all_probes(constraints, db=None, user_state=None):
        return _opportunities()

    async def fake_probe_global_baseline(user_state, db=None, limit=5):
        return {
            "reach": [_candidate("冲刺大学", utility=1.3)],
            "match": [_candidate("稳妥大学", utility=1.2)],
            "safety": [_candidate("保底大学", utility=1.1)],
        }

    monkeypatch.setattr("app.graphs.nodes.gatekeeper.run_baseline", fake_run_baseline)
    monkeypatch.setattr("app.graphs.nodes.radar.run_all_probes", fake_run_all_probes)
    monkeypatch.setattr(
        "app.graphs.nodes.radar.probe_global_baseline",
        fake_probe_global_baseline,
    )

    output_dir = Path("app/evaluation/results/test_phase7")
    shutil.rmtree(output_dir, ignore_errors=True)

    result = run_ablation_benchmark(
        build_graph(),
        UserSimulator,
        get_evaluation_dataset()[:1],
        use_mock=True,
        output_dir=output_dir,
        max_turns=4,
    )

    csv_path = output_dir / "ablation_results.csv"
    assert result["csv_path"] == str(csv_path)
    assert csv_path.exists()

    with csv_path.open("r", encoding="utf-8", newline="") as file:
        rows = list(csv.DictReader(file))

    assert len(rows) == 3
    assert set(rows[0]) == {
        "profile_id",
        "ablation_mode",
        "mae_error",
        "negotiation_turns",
        "status",
        "error_message",
    }
    assert {row["ablation_mode"] for row in rows} == {"full", "no_ucb", "no_tracker"}

    shutil.rmtree(output_dir, ignore_errors=True)
