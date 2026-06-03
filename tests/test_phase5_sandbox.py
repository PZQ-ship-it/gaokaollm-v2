from typing import Any

from langchain_core.messages import AIMessage

from app.evaluation.sandbox import run_sandbox_evaluation
from app.evaluation.schemas import IcebergProfile
from app.evaluation.simulator import UserSimulator
from app.graphs.workflow import build_graph


class FakeLLM:
    async def ainvoke(self, prompt):
        text = "\n".join(str(getattr(message, "content", "")) for message in prompt)
        if "最终志愿表" in text:
            return AIMessage(
                content="偏好解释：系统根据当前取舍重新排序。最终推荐：终局推荐大学。"
            )
        return AIMessage(
            content="我看到一个可比较的放宽方案。你愿意继续比较这个方向吗？"
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
        "geo_relax": [],
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


def test_auto_sandbox_episode(monkeypatch):
    monkeypatch.delenv("GAOKAOLLM_OFFLINE_DETERMINISTIC", raising=False)

    async def fake_run_baseline(constraints):
        return [{"school_name": "基准大学", "min_score": 590, "tier": 2}]

    async def fake_run_all_probes(constraints, db=None, user_state=None):
        return _opportunities()

    async def fake_probe_global_baseline(
        user_state,
        db=None,
        limit=5,
        total_limit=None,
    ):
        return [_candidate("终局推荐大学", utility=1.3)]

    monkeypatch.setattr("app.graphs.nodes.gatekeeper.run_baseline", fake_run_baseline)
    monkeypatch.setattr("app.graphs.nodes.radar.run_all_probes", fake_run_all_probes)
    monkeypatch.setattr(
        "app.graphs.nodes.radar.probe_global_baseline",
        fake_probe_global_baseline,
    )
    monkeypatch.setattr("app.graphs.nodes.negotiator.get_chat_model", lambda: FakeLLM())

    profile = IcebergProfile(
        profile_id="iceberg-smoke-001",
        explicit_query="物化生，我考了610，只想去江浙沪读计算机，绝对不出省。",
        hidden_bottom_line="其实如果有985高校，我可以接受去华中或西南地区；但专业绝对不接受调剂。",
        ground_truth_weights={
            "school": 0.5,
            "geo": 0.1,
            "major": 0.4,
            "tuition": 0.0,
            "quality": 0.0,
            "risk": 0.0,
        },
    )
    simulator = UserSimulator(
        profile,
        llm=None,
        mock_replies=["如果有好学校我可以考虑跨省", "绝对不行，预算最多一万"],
    )

    result = run_sandbox_evaluation(
        build_graph(),
        profile,
        simulator,
        thread_id="phase5-sandbox-thread",
    )

    assert result["turns"] >= 1
    assert isinstance(result["mae_error"], float)
    assert isinstance(result["inferred_weights"], dict)
    assert result["final_xai_report"]
