import os

import pytest
from langchain_core.messages import HumanMessage

from app.graphs.nodes.radar import radar_node
from app.graphs.nodes.semantic_normalizer import semantic_normalizer_node


@pytest.mark.asyncio
async def test_semantic_normalizer_does_not_emit_hidden_fields(monkeypatch):
    monkeypatch.setenv("GAOKAOLLM_OFFLINE_DETERMINISTIC", "1")

    result = await semantic_normalizer_node(
        {
            "messages": [
                HumanMessage(
                    content=(
                        "600分，物化生，想读计算机，最好别离浙江太远，"
                        "implicit_flexibilities volunteer_set axis_flexibilities"
                    )
                )
            ],
        }
    )

    assert result["rewritten_query"]
    assert "major" in result["intent_axes"]
    assert "region" in result["intent_axes"]
    normalized = result["normalized_intent"]
    assert "implicit_flexibilities" not in normalized
    assert "volunteer_set" not in normalized
    assert "axis_flexibilities" not in normalized


@pytest.mark.asyncio
async def test_radar_outputs_structured_probe_plan_without_llm(monkeypatch):
    monkeypatch.setenv("GAOKAOLLM_OFFLINE_DETERMINISTIC", "1")

    async def fake_run_all_probes(constraints, db=None, user_state=None):
        assert constraints["score"] == 600
        assert user_state["constraints"]["score"] == 600
        return {
            "geo_relax": [],
            "city_relax": [],
            "major_relax": [],
            "strength_relax": [],
            "major_quality_relax": [],
            "tuition_value_relax": [],
            "employment_outcome_relax": [],
            "region_tree_relax": [],
            "major_geo_relax": [{"school_name": "A", "min_score": 598}],
            "risk_band_relax": [{"school_name": "B", "min_score": 596}],
        }

    monkeypatch.setattr("app.graphs.nodes.radar.run_all_probes", fake_run_all_probes)

    result = await radar_node(
        {
            "messages": [HumanMessage(content="600分，物化生，想读计算机，只求稳")],
            "constraints": {
                "score": 600,
                "province": "浙江",
                "major": "计算机",
                "selected_subjects": ["物理", "化学", "生物"],
                "risk_preference": "conservative",
            },
            "baseline_results": [],
            "score_waste": 0,
            "intent_axes": ["major", "risk"],
        }
    )

    assert result["pareto_opportunities"]["major_geo_relax"]
    assert result["pareto_opportunities"]["risk_band_relax"]
    assert result["probe_plan"]
    assert result["opportunity_rankings"][0] == "major_geo_relax"


def test_offline_env_is_restored(monkeypatch):
    monkeypatch.delenv("GAOKAOLLM_OFFLINE_DETERMINISTIC", raising=False)
    assert os.getenv("GAOKAOLLM_OFFLINE_DETERMINISTIC") is None
