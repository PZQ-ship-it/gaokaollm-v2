import json
import shutil
from pathlib import Path
from types import SimpleNamespace

import pytest

from gaokaollm_bench.evaluator.deterministic_judge import check_hallucination
from gaokaollm_bench.evaluator.llm_as_a_judge import evaluate_process
from gaokaollm_bench.data_gen.generate_personas import (
    MULTI_AXIS_VERSION_V2,
    _multi_axis_coherence_report,
    _select_coherent_multi_axis_pairs,
)
from gaokaollm_bench.sandbox.target_agents import (
    AppGraphTargetAgent,
    HardConstraintBaselineAgent,
    V1SoftRagBaselineAgent,
)
from gaokaollm_bench.schemas import IcebergPersona
from gaokaollm_bench.tests.manual.agent_benchmark_run import (
    RunConfig,
    TARGET_V1_SOFT_RAG,
    _employment_outcome_gain,
    _has_employment_outcome_evidence,
    _has_major_quality_evidence,
    _has_multi_axis_evidence,
    _has_region_tree_evidence,
    _major_quality_gain,
    _multi_axis_details,
    _multi_axis_gain,
    _region_tree_gain,
    _has_tuition_value_evidence,
    _tuition_value_gain,
    load_personas,
    run_target_cases,
    write_summary_files,
    build_target,
    target_requires_db,
)
from app.graphs.nodes.negotiator import _fallback_reply_v2


class FakeGraph:
    def __init__(self, expected_thread_id="case-thread"):
        self.expected_thread_id = expected_thread_id

    async def ainvoke(self, payload, config):
        assert payload["messages"][0].content == "物化生，600分必须在北京读临床"
        assert config["configurable"]["thread_id"] == self.expected_thread_id
        return {
            "messages": [
                SimpleNamespace(
                    content=(
                        "选项A：可以看山东大学。选项B：可以看医学技术。"
                        "联合方案：可以看西南交通大学生物医学工程，最低分597。"
                    )
                )
            ],
            "constraints": {
                "score": 600,
                "province": "北京",
                "major": "临床医学",
                "selected_subjects": ["物理", "化学", "生物"],
            },
            "baseline_results": [
                {
                    "school_name": "北京学院",
                    "school_province": "北京",
                    "major_name": "临床医学",
                    "min_score": 590,
                    "tier": 2,
                }
            ],
            "pareto_opportunities": {
                "geo_relax": [
                    {
                        "school_name": "山东大学",
                        "school_province": "山东",
                        "major_name": "临床医学",
                        "min_score": 598,
                        "tier": 4,
                    }
                ],
                "major_relax": [],
                "strength_relax": [],
                "major_quality_relax": [],
                "tuition_value_relax": [],
                "employment_outcome_relax": [],
                "region_tree_relax": [
                    {
                        "school_name": "Region Tree University",
                        "school_province": "Zhejiang",
                        "school_city": "Ningbo",
                        "major_name": "Clinical Medicine",
                        "min_score": 596,
                        "tier": 3,
                        "region_relax_strategy": "geo_block_relax",
                        "target_region_name": "Ningbo",
                    }
                ],
                "major_geo_relax": [
                    {
                        "school_name": "西南交通大学",
                        "school_province": "四川",
                        "major_name": "生物医学工程",
                        "min_score": 597,
                        "tier": 3,
                    }
                ],
                "risk_band_relax": [
                    {
                        "school_name": "风险组合大学",
                        "school_province": "鍖椾含",
                        "major_name": "涓村簥鍖诲",
                        "min_score": 596,
                        "min_rank": 52000,
                        "tier": 2,
                        "risk_level": "chong",
                        "score_margin": 4,
                        "rank_gap": 2000,
                    }
                ],
            },
            "score_waste": 10,
            "missing_constraints": [],
        }


class FakeRiskGraph:
    async def ainvoke(self, payload, config):
        return {
            "messages": [
                SimpleNamespace(
                    content=(
                        "风险方案：风险组合大学 min_score=596 risk=chong；"
                        "稳妥大学 min_score=588 risk=wen；"
                        "保底大学 min_score=570 risk=bao。"
                    )
                )
            ],
            "constraints": {
                "score": 600,
                "province": "鍖椾含",
                "major": "涓村簥鍖诲",
                "selected_subjects": ["鐗╃悊", "鍖栧", "鐢熺墿"],
                "risk_preference": "conservative",
            },
            "baseline_results": [],
            "pareto_opportunities": {
                "geo_relax": [],
                "city_relax": [],
                "major_relax": [],
                "strength_relax": [],
                "major_quality_relax": [],
                "tuition_value_relax": [],
                "employment_outcome_relax": [],
                "region_tree_relax": [],
                "major_geo_relax": [],
                "risk_band_relax": [
                    {
                        "school_name": "风险组合大学",
                        "school_province": "鍖椾含",
                        "major_name": "涓村簥鍖诲",
                        "min_score": 596,
                        "min_rank": 52000,
                        "tier": 2,
                        "risk_level": "chong",
                        "score_margin": 4,
                        "rank_gap": 2000,
                    },
                    {
                        "school_name": "稳妥大学",
                        "school_province": "鍖椾含",
                        "major_name": "涓村簥鍖诲",
                        "min_score": 588,
                        "min_rank": 60000,
                        "tier": 2,
                        "risk_level": "wen",
                        "score_margin": 12,
                        "rank_gap": 10000,
                    },
                    {
                        "school_name": "保底大学",
                        "school_province": "鍖椾含",
                        "major_name": "涓村簥鍖诲",
                        "min_score": 570,
                        "min_rank": 75000,
                        "tier": 2,
                        "risk_level": "bao",
                        "score_margin": 30,
                        "rank_gap": 25000,
                    },
                ],
            },
            "score_waste": 0,
            "missing_constraints": [],
        }


class FakeRegionGraph:
    async def ainvoke(self, payload, config):
        return {
            "messages": [
                SimpleNamespace(
                    content=(
                        "region_tree_relax 证据：Region Tree University "
                        "Computer Science min_score=596 strategy=geo_block_relax "
                        "region=Hangzhou->Ningbo confidence=0.95。"
                    )
                )
            ],
            "constraints": {
                "score": 600,
                "province": "Zhejiang",
                "city": "Hangzhou",
                "major": "Computer Science",
                "selected_subjects": ["Physics", "Chemistry", "Biology"],
            },
            "baseline_results": [],
            "pareto_opportunities": {
                "geo_relax": [],
                "city_relax": [],
                "major_relax": [],
                "strength_relax": [],
                "major_quality_relax": [],
                "tuition_value_relax": [],
                "employment_outcome_relax": [],
                "region_tree_relax": [
                    {
                        "school_name": "Region Tree University",
                        "school_province": "Zhejiang",
                        "school_city": "Ningbo",
                        "major_name": "Computer Science",
                        "min_score": 596,
                        "min_rank": 43000,
                        "tier": 3,
                        "region_relax_strategy": "geo_block_relax",
                        "source_region_name": "Hangzhou",
                        "target_region_name": "Ningbo",
                        "region_tree_confidence": 0.95,
                    }
                ],
                "major_geo_relax": [],
                "risk_band_relax": [],
            },
            "score_waste": 4,
            "missing_constraints": [],
        }


class FakeDb:
    async def __call__(self, query, *params):
        assert params[-1] == 3
        return [
            {
                "school_name": "北京学院",
                "school_province": "北京",
                "major_name": "临床医学",
                "min_score": 590,
                "tier": 2,
            }
        ]


class EmptyDb:
    async def __call__(self, query, *params):
        return []


class FakeV1Db:
    async def __call__(self, query, *params):
        assert "admission_scores" in query
        assert "soft_match_score" in query
        return [
            {
                "school_name": "冲刺大学",
                "school_province": "浙江",
                "school_city": "杭州",
                "major_name": "计算机科学与技术",
                "min_score": 612,
                "min_rank": 30000,
                "tier": 3,
                "soft_match_score": 8,
            },
            {
                "school_name": "稳妥大学",
                "school_province": "浙江",
                "school_city": "宁波",
                "major_name": "软件工程",
                "min_score": 600,
                "min_rank": 40000,
                "tier": 2,
                "soft_match_score": 4,
            },
            {
                "school_name": "保底大学",
                "school_province": "浙江",
                "school_city": "温州",
                "major_name": "信息管理与信息系统",
                "min_score": 580,
                "min_rank": 60000,
                "tier": 2,
                "soft_match_score": 2,
            },
        ]


class FakeSimulatorLlm:
    async def ainvoke(self, prompt):
        return json.dumps(
            {
                "thought": "看到了具体学校和分数。",
                "is_persuaded": True,
                "utterance": "我愿意考虑这个方案。",
            },
            ensure_ascii=False,
        )


class FakeJudgeLlm:
    async def ainvoke(self, prompt):
        return json.dumps(
            {
                "case_id": "case-001",
                "hallucination_rate": 0.0,
                "elicitation_success": True,
                "pareto_gain": 2,
                "judge_reasoning": "被测系统给出了可核验的学校和分数证据。",
            },
            ensure_ascii=False,
        )


class FakeHallucinationDb:
    async def fetch(self, query, *params):
        return [{"school_name": params[0], "min_score": 598}]


def build_persona():
    return IcebergPersona(
        case_id="case-001",
        background={"score": 600, "province": "北京"},
        explicit_red_lines={"geo": "只去北京"},
        implicit_flexibilities={"trigger_school": "山东大学"},
        initial_utterance="物化生，600分必须在北京读临床",
        process_milestones={"accept_after_specific_evidence": True},
    )


def build_risk_persona():
    return IcebergPersona(
        case_id="risk-case-001",
        background={
            "score": 600,
            "province": "鍖椾含",
            "baseline_tier": 2,
            "constraint_relaxed": "risk_band",
        },
        explicit_red_lines={"risk": "只求稳妥，不接受冲刺风险"},
        implicit_flexibilities={
            "trigger_type": "volunteer_set",
            "constraint_relaxed": "risk_band",
            "risk_levels": ["chong", "wen", "bao"],
            "portfolio_gain": 3,
            "volunteer_set": [
                {
                    "school_name": "风险组合大学",
                    "major_name": "涓村簥鍖诲",
                    "min_score": 596,
                    "risk_level": "chong",
                    "tier": 2,
                },
                {
                    "school_name": "稳妥大学",
                    "major_name": "涓村簥鍖诲",
                    "min_score": 588,
                    "risk_level": "wen",
                    "tier": 2,
                },
                {
                    "school_name": "保底大学",
                    "major_name": "涓村簥鍖诲",
                    "min_score": 570,
                    "risk_level": "bao",
                    "tier": 2,
                },
            ],
        },
        initial_utterance="鐗╁寲鐢燂紝600鍒嗭紝只想稳妥，不接受冲刺风险。",
        process_milestones={"accept_after_verified_risk_portfolio": True},
    )


def build_region_persona():
    return IcebergPersona(
        case_id="region-case-001",
        background={
            "score": 600,
            "province": "Zhejiang",
            "city": "Hangzhou",
            "baseline_tier": 2,
            "constraint_relaxed": "region_tree",
        },
        explicit_red_lines={
            "region": "prefer Hangzhou or familiar nearby region",
            "major": "keep Computer Science",
        },
        implicit_flexibilities={
            "trigger_type": "volunteer_set",
            "constraint_relaxed": "region_tree",
            "baseline_tier": 2,
            "volunteer_set": [
                {
                    "school_name": "Region Tree University",
                    "major_name": "Computer Science",
                    "min_score": 596,
                    "tier": 3,
                    "region_relax_strategy": "geo_block_relax",
                    "target_region_name": "Ningbo",
                }
            ],
        },
        initial_utterance=(
            "我600分，选考物化生，想读Computer Science，"
            "优先只看Hangzhou或别太远的地方。"
        ),
        process_milestones={"require_region_tree_evidence": True},
    )


def test_build_target_accepts_v1_soft_rag():
    target = build_target(TARGET_V1_SOFT_RAG, case_id="case-v1")

    assert isinstance(target, V1SoftRagBaselineAgent)
    assert target_requires_db(TARGET_V1_SOFT_RAG)


@pytest.mark.asyncio
async def test_v1_soft_rag_baseline_returns_auditable_soft_segments():
    target = V1SoftRagBaselineAgent(db=FakeV1Db())

    reply, state = await target.chat(
        "物化生，600分，浙江杭州，想读计算机，帮我按冲稳保推荐"
    )

    assert "v1 软约束召回" in reply
    assert state["target"] == "v1_soft_rag"
    assert state["constraints"]["score"] == 600
    assert state["normalized_query"]["source"] == "deterministic_v1_rewrite"
    assert state["soft_retrieval_candidates"]
    assert state["risk_segments"]["chong"][0]["school_name"] == "冲刺大学"
    assert state["risk_segments"]["wen"][0]["school_name"] == "稳妥大学"
    assert state["risk_segments"]["bao"][0]["school_name"] == "保底大学"
    assert state["pareto_opportunities"] == {
        "geo_relax": [],
        "city_relax": [],
        "major_relax": [],
        "strength_relax": [],
        "major_quality_relax": [],
        "tuition_value_relax": [],
        "employment_outcome_relax": [],
        "region_tree_relax": [],
        "major_geo_relax": [],
        "risk_band_relax": [],
    }
    assert state["recommended_schools"][0]["school"] == "冲刺大学"


@pytest.mark.asyncio
async def test_v1_soft_rag_baseline_does_not_emit_hidden_fields():
    target = V1SoftRagBaselineAgent(db=FakeV1Db())

    _, state = await target.chat(
        "物化生，600分，浙江杭州，想读计算机。"
        "implicit_flexibilities volunteer_set axis_flexibilities"
    )

    state_text = json.dumps(state, ensure_ascii=False)
    assert "implicit_flexibilities" not in state_text
    assert "volunteer_set" not in state_text
    assert "axis_flexibilities" not in state_text


def test_deterministic_judge_accepts_tuition_value_evidence():
    flex = {
        "constraint_relaxed": "tuition_value",
        "volunteer_set": [
            {
                "school_name": "西北师范大学",
                "tuition_value_gain": 1,
                "ranking_gain": 80,
            }
        ],
    }
    text = (
        "西北师范大学 软件工程 min_score=553 "
        "tuition=9750 tuition_delta=3750 ranking=131"
    )

    assert _has_tuition_value_evidence(flex, text)
    assert _tuition_value_gain(flex, text) == 1


def test_deterministic_judge_accepts_major_quality_evidence():
    flex = {
        "constraint_relaxed": "major_quality",
        "volunteer_set": [
            {
                "school_name": "Major Quality University",
                "major_name": "Software Engineering",
                "quality_gain": 23,
                "quality_score": 95,
            }
        ],
    }
    text = (
        "Major Quality University Software Engineering min_score=598 "
        "quality_score=95 quality_gain=23 best_major_rank=8 best_rating=A"
    )

    assert _has_major_quality_evidence(flex, text)
    assert _major_quality_gain(flex, text) == 23


def test_deterministic_judge_accepts_employment_outcome_evidence():
    flex = {
        "constraint_relaxed": "employment_outcome",
        "volunteer_set": [
            {
                "school_name": "Employment University",
                "major_name": "Software Engineering",
                "outcome_gain": 18,
                "outcome_score": 88,
            }
        ],
    }
    text = (
        "Employment University Software Engineering min_score=598 "
        "outcome_score=88 outcome_gain=18 employment_rank=9 "
        "top_industry=互联网 salary=10k-15k"
    )

    assert _has_employment_outcome_evidence(flex, text)
    assert _employment_outcome_gain(flex, text) == 18


def test_deterministic_judge_accepts_region_tree_evidence():
    flex = {
        "constraint_relaxed": "region_tree",
        "baseline_tier": 2,
        "volunteer_set": [
            {
                "school_name": "Region Tree University",
                "major_name": "Computer Science",
                "tier": 3,
                "region_relax_strategy": "geo_block_relax",
                "target_region_name": "Ningbo",
            }
        ],
    }
    text = (
        "Region Tree University Computer Science min_score=596 "
        "strategy=geo_block_relax region=Hangzhou->Ningbo confidence=0.95"
    )

    assert _has_region_tree_evidence(flex, text)
    assert _region_tree_gain(flex, text) == 1


def test_multi_axis_requires_all_axes():
    flex = {
        "constraint_relaxed": "multi_axis",
        "relaxation_axes": ["major_quality", "tuition_value"],
        "axis_flexibilities": {
            "major_quality": {
                "constraint_relaxed": "major_quality",
                "volunteer_set": [
                    {
                        "school_name": "Major Quality University",
                        "quality_gain": 16,
                    }
                ],
            },
            "tuition_value": {
                "constraint_relaxed": "tuition_value",
                "volunteer_set": [
                    {
                        "school_name": "Tuition Value University",
                        "tuition_value_gain": 1,
                    }
                ],
            },
        },
    }
    one_axis_text = (
        "Major Quality University min_score=598 quality_score=90 "
        "quality_gain=16 best_major_rank=8"
    )
    both_axes_text = (
        one_axis_text + "\nTuition Value University min_score=590 tuition=12000 "
        "tuition_delta=3000"
    )

    assert not _has_multi_axis_evidence(flex, one_axis_text)
    assert _has_multi_axis_evidence(flex, both_axes_text)
    assert _multi_axis_gain(flex, both_axes_text) == 17
    assert _multi_axis_details(flex, both_axes_text)["axis_successes"] == {
        "major_quality": True,
        "tuition_value": True,
    }


def test_negotiator_fallback_outputs_two_axis_evidence():
    reply = _fallback_reply_v2(
        {
            "major_quality_relax": [
                {
                    "school_name": "Major Quality University",
                    "major_name": "Software Engineering",
                    "min_score": 598,
                    "quality_score": 90,
                    "quality_gain": 16,
                }
            ],
            "tuition_value_relax": [
                {
                    "school_name": "Tuition Value University",
                    "major_name": "Software Engineering",
                    "min_score": 590,
                    "tuition": 12000,
                    "tuition_delta": 3000,
                }
            ],
        }
    )

    assert "major_quality_relax" in reply
    assert "tuition_value_relax" in reply
    assert "Major Quality University" in reply
    assert "Tuition Value University" in reply


def test_multi_axis_v2_validator_rejects_unrelated_major_family():
    ok, report = _multi_axis_coherence_report(
        profile="major_geo_risk",
        first_gap={
            "score": 592,
            "province": "浙江",
            "strict_major": "城市设计",
            "tier_a": {"major_name": "城市设计"},
            "volunteer_set": [{"major_name": "城乡规划"}],
        },
        second_gap={
            "score": 592,
            "province": "浙江",
            "strict_major": "临床医学",
            "tier_a": {"major_name": "临床医学"},
            "volunteer_set": [{"major_name": "临床医学"}],
        },
        score_tolerance=8,
    )

    assert not ok
    assert not report["major_match"]


def test_multi_axis_v2_pair_selector_keeps_coherent_axes():
    pairs, diagnostic = _select_coherent_multi_axis_pairs(
        profile="quality_tuition",
        first_axis="major_quality",
        first_gaps=[
            {
                "score": 600,
                "province": "浙江",
                "strict_major": "软件工程",
                "tier_a": {"major_name": "软件工程"},
                "volunteer_set": [
                    {"major_name": "软件工程", "school_name": "A", "min_score": 596}
                ],
                "max_tier_delta": 1,
            }
        ],
        second_axis="tuition_value",
        second_gaps=[
            {
                "score": 604,
                "province": "浙江",
                "strict_major": "计算机科学与技术",
                "tier_a": {"major_name": "计算机科学与技术"},
                "volunteer_set": [
                    {
                        "major_name": "计算机科学与技术",
                        "school_name": "B",
                        "min_score": 598,
                    }
                ],
                "max_tier_delta": 1,
            }
        ],
        required=1,
        score_tolerance=8,
    )

    assert diagnostic["found"] == 1
    assert pairs[0]["multi_axis_version"] == MULTI_AXIS_VERSION_V2
    assert pairs[0]["coherence_checks"]["major_match"]


async def evaluate_by_joint_school(transcript, *, judge_llm):
    combined = "\n".join(turn.content for turn in transcript.turns)
    success = "西南交通大学" in combined and "最低分" in combined
    return SimpleNamespace(
        hallucination_rate=0.0,
        elicitation_success=success,
        pareto_gain=1 if success else 0,
        judge_reasoning=(
            "命中联合放宽学校和分数证据。"
            if success
            else "未命中联合放宽学校和分数证据。"
        ),
        model_copy=lambda update: SimpleNamespace(
            hallucination_rate=update.get("hallucination_rate", 0.0),
            elicitation_success=success,
            pareto_gain=1 if success else 0,
            judge_reasoning=(
                "命中联合放宽学校和分数证据。"
                if success
                else "未命中联合放宽学校和分数证据。"
            ),
        ),
    )


async def evaluate_by_risk_portfolio(transcript, *, judge_llm):
    combined = "\n".join(turn.content for turn in transcript.turns)
    success = (
        "风险组合大学" in combined
        and "稳妥大学" in combined
        and "保底大学" in combined
        and "min_score" in combined
    )
    return SimpleNamespace(
        hallucination_rate=0.0,
        elicitation_success=success,
        pareto_gain=3 if success else 0,
        judge_reasoning=(
            "命中风险偏好放宽的冲稳保组合。" if success else "未命中风险偏好放宽组合。"
        ),
    )


async def evaluate_by_region_tree(transcript, *, judge_llm):
    combined = "\n".join(turn.content for turn in transcript.turns)
    flex = transcript.persona.implicit_flexibilities
    success = _has_region_tree_evidence(flex, combined)
    gain = _region_tree_gain(flex, combined) if success else 0
    return SimpleNamespace(
        hallucination_rate=0.0,
        elicitation_success=success,
        pareto_gain=gain,
        judge_reasoning="region-tree deterministic smoke",
        model_copy=lambda update: SimpleNamespace(
            hallucination_rate=update.get("hallucination_rate", 0.0),
            elicitation_success=success,
            pareto_gain=gain,
            judge_reasoning="region-tree deterministic smoke",
        ),
    )


@pytest.mark.asyncio
async def test_app_graph_target_agent_preserves_auditable_state():
    target = AppGraphTargetAgent(thread_id="case-thread", graph=FakeGraph())

    reply, state = await target.chat("物化生，600分必须在北京读临床")

    assert "选项A" in reply
    assert state["target"] == "app_pareto"
    assert state["constraints"]["score"] == 600
    assert state["baseline_results"]
    assert state["pareto_opportunities"]["geo_relax"]
    assert state["pareto_opportunities"]["major_geo_relax"]
    assert state["pareto_opportunities"]["risk_band_relax"]
    assert state["pareto_opportunities"]["strength_relax"] == []
    assert state["pareto_opportunities"]["major_quality_relax"] == []
    assert state["pareto_opportunities"]["tuition_value_relax"] == []
    assert state["pareto_opportunities"]["employment_outcome_relax"] == []
    assert state["pareto_opportunities"]["region_tree_relax"]
    assert any(
        item.get("risk_level") == "chong" for item in state["recommended_schools"]
    )
    assert any(
        item.get("region_relax_strategy") == "geo_block_relax"
        for item in state["recommended_schools"]
    )
    assert state["recommended_schools"][0]["school"] == "北京学院"
    assert state["recommended_schools"][1]["school"] == "山东大学"
    assert state["recommended_schools"][2]["school"] == "西南交通大学"


@pytest.mark.asyncio
async def test_hard_constraint_baseline_only_reports_baseline():
    target = HardConstraintBaselineAgent(db=FakeDb())

    reply, state = await target.chat("物化生，600分必须在北京读临床")

    assert "按你当前坚持的硬约束" in reply
    assert state["target"] == "hard_constraint"
    assert state["baseline_results"]
    assert state["pareto_opportunities"] == {
        "geo_relax": [],
        "city_relax": [],
        "major_relax": [],
        "strength_relax": [],
        "major_quality_relax": [],
        "tuition_value_relax": [],
        "employment_outcome_relax": [],
        "region_tree_relax": [],
        "major_geo_relax": [],
        "risk_band_relax": [],
    }
    assert state["recommended_schools"] == [
        {
            "school": "北京学院",
            "province": "北京",
            "major": "临床医学",
            "min_score": 590,
            "tier": 2,
        }
    ]


@pytest.mark.asyncio
async def test_hard_constraint_baseline_handles_empty_results():
    target = HardConstraintBaselineAgent(db=EmptyDb())

    reply, state = await target.chat("物化生，600分必须在北京读临床")

    assert "没有找到" in reply
    assert state["baseline_results"] == []
    assert state["recommended_schools"] == []


@pytest.mark.asyncio
async def test_agent_benchmark_cli_smoke_writes_outputs(monkeypatch):
    work_dir = Path("gaokaollm_bench/tests/_agent_benchmark_output")
    if work_dir.exists():
        shutil.rmtree(work_dir)
    work_dir.mkdir(parents=True)

    persona_path = work_dir / "personas.json"
    persona_path.write_text(
        json.dumps([build_persona().model_dump()], ensure_ascii=False),
        encoding="utf-8",
    )

    async def fake_evaluate_transcript(transcript, *, judge_llm):
        hallucination_rate = await check_hallucination(
            transcript, FakeHallucinationDb()
        )
        report = await evaluate_process(transcript, transcript.persona, judge_llm)
        return report.model_copy(update={"hallucination_rate": hallucination_rate})

    monkeypatch.setattr(
        "gaokaollm_bench.tests.manual.agent_benchmark_run.build_target",
        lambda name, case_id: AppGraphTargetAgent(
            thread_id=f"bench-{case_id}",
            graph=FakeGraph(expected_thread_id=f"bench-{case_id}"),
        ),
    )
    monkeypatch.setattr(
        "gaokaollm_bench.tests.manual.agent_benchmark_run.evaluate_transcript",
        fake_evaluate_transcript,
    )

    config = RunConfig(
        personas_path=persona_path,
        targets=["app_pareto"],
        max_turns=2,
        limit=None,
        output_dir=work_dir / "agent_benchmark",
        judge_model="mock-judge",
        simulator_model="mock-simulator",
        paper_summary_path=None,
    )
    personas = load_personas(persona_path)
    rows = await run_target_cases(
        target_name="app_pareto",
        personas=personas,
        config=config,
        simulator_llm=FakeSimulatorLlm(),
        judge_llm=FakeJudgeLlm(),
    )
    summary = write_summary_files(config=config, personas=personas, rows=rows)

    assert (
        config.output_dir / "transcripts/app_pareto/transcript_case-001.json"
    ).exists()
    assert (config.output_dir / "reports/app_pareto.jsonl").exists()
    assert (config.output_dir / "summary.json").exists()
    assert (config.output_dir / "summary.md").exists()
    metrics = summary["targets"]["app_pareto"]
    assert metrics["elicitation_success_rate"] == 1.0
    assert metrics["mean_pareto_gain"] == 2.0
    assert metrics["mean_hallucination_rate"] == 0.0
    assert metrics["avg_turns"] == 3.0

    shutil.rmtree(work_dir)


@pytest.mark.asyncio
async def test_agent_benchmark_smoke_app_beats_hard_constraint(monkeypatch):
    work_dir = Path("gaokaollm_bench/tests/_agent_benchmark_joint_output")
    if work_dir.exists():
        shutil.rmtree(work_dir)
    work_dir.mkdir(parents=True)

    persona_path = work_dir / "personas.json"
    persona = build_persona().model_copy(
        update={
            "implicit_flexibilities": {
                "trigger_school": "西南交通大学",
                "volunteer_set": [
                    {
                        "school_name": "西南交通大学",
                        "major_name": "生物医学工程",
                        "min_score": 597,
                        "tier": 3,
                    }
                ],
            }
        }
    )
    persona_path.write_text(
        json.dumps([persona.model_dump()], ensure_ascii=False),
        encoding="utf-8",
    )

    def fake_build_target(name, case_id):
        if name == "app_pareto":
            return AppGraphTargetAgent(
                thread_id=f"bench-{case_id}",
                graph=FakeGraph(expected_thread_id=f"bench-{case_id}"),
            )
        return HardConstraintBaselineAgent(db=FakeDb())

    monkeypatch.setattr(
        "gaokaollm_bench.tests.manual.agent_benchmark_run.build_target",
        fake_build_target,
    )
    monkeypatch.setattr(
        "gaokaollm_bench.tests.manual.agent_benchmark_run.evaluate_transcript",
        evaluate_by_joint_school,
    )

    config = RunConfig(
        personas_path=persona_path,
        targets=["app_pareto", "hard_constraint"],
        max_turns=1,
        limit=None,
        output_dir=work_dir / "agent_benchmark",
        judge_model="mock-judge",
        simulator_model="mock-simulator",
        paper_summary_path=None,
    )
    personas = load_personas(persona_path)
    rows = []
    for target_name in config.targets:
        rows.extend(
            await run_target_cases(
                target_name=target_name,
                personas=personas,
                config=config,
                simulator_llm=FakeSimulatorLlm(),
                judge_llm=FakeJudgeLlm(),
            )
        )
    summary = write_summary_files(config=config, personas=personas, rows=rows)

    assert (
        summary["targets"]["app_pareto"]["elicitation_success_rate"]
        > summary["targets"]["hard_constraint"]["elicitation_success_rate"]
    )
    assert (
        summary["targets"]["app_pareto"]["mean_pareto_gain"]
        > summary["targets"]["hard_constraint"]["mean_pareto_gain"]
    )
    assert (config.output_dir / "summary.json").exists()
    assert (config.output_dir / "summary.md").exists()

    shutil.rmtree(work_dir)


@pytest.mark.asyncio
async def test_agent_benchmark_smoke_risk_band_app_beats_hard_constraint(monkeypatch):
    work_dir = Path("gaokaollm_bench/tests/_agent_benchmark_risk_output")
    if work_dir.exists():
        shutil.rmtree(work_dir)
    work_dir.mkdir(parents=True)

    persona_path = work_dir / "personas.json"
    persona_path.write_text(
        json.dumps([build_risk_persona().model_dump()], ensure_ascii=False),
        encoding="utf-8",
    )

    def fake_build_target(name, case_id):
        if name == "app_pareto":
            return AppGraphTargetAgent(
                thread_id=f"bench-{case_id}",
                graph=FakeRiskGraph(),
            )
        return HardConstraintBaselineAgent(db=FakeDb())

    monkeypatch.setattr(
        "gaokaollm_bench.tests.manual.agent_benchmark_run.build_target",
        fake_build_target,
    )
    monkeypatch.setattr(
        "gaokaollm_bench.tests.manual.agent_benchmark_run.evaluate_transcript",
        evaluate_by_risk_portfolio,
    )

    config = RunConfig(
        personas_path=persona_path,
        targets=["app_pareto", "hard_constraint"],
        max_turns=1,
        limit=None,
        output_dir=work_dir / "agent_benchmark",
        judge_model="mock-judge",
        simulator_model="mock-simulator",
        paper_summary_path=None,
    )
    personas = load_personas(persona_path)
    rows = []
    for target_name in config.targets:
        rows.extend(
            await run_target_cases(
                target_name=target_name,
                personas=personas,
                config=config,
                simulator_llm=FakeSimulatorLlm(),
                judge_llm=FakeJudgeLlm(),
            )
        )
    summary = write_summary_files(config=config, personas=personas, rows=rows)

    assert (
        summary["targets"]["app_pareto"]["elicitation_success_rate"]
        > summary["targets"]["hard_constraint"]["elicitation_success_rate"]
    )
    assert (
        summary["targets"]["app_pareto"]["mean_pareto_gain"]
        > summary["targets"]["hard_constraint"]["mean_pareto_gain"]
    )
    assert (
        config.output_dir / "transcripts/app_pareto/transcript_risk-case-001.json"
    ).exists()
    assert (config.output_dir / "reports/app_pareto.jsonl").exists()
    assert (config.output_dir / "summary.json").exists()
    assert (config.output_dir / "summary.md").exists()

    shutil.rmtree(work_dir)


@pytest.mark.asyncio
async def test_agent_benchmark_smoke_region_tree_app_beats_hard_constraint(
    monkeypatch,
):
    work_dir = Path("gaokaollm_bench/tests/_agent_benchmark_region_output")
    if work_dir.exists():
        shutil.rmtree(work_dir)
    work_dir.mkdir(parents=True)

    persona_path = work_dir / "personas.json"
    persona_path.write_text(
        json.dumps([build_region_persona().model_dump()], ensure_ascii=False),
        encoding="utf-8",
    )

    def fake_build_target(name, case_id):
        if name == "app_pareto":
            return AppGraphTargetAgent(
                thread_id=f"bench-{case_id}",
                graph=FakeRegionGraph(),
            )
        return HardConstraintBaselineAgent(db=FakeDb())

    monkeypatch.setattr(
        "gaokaollm_bench.tests.manual.agent_benchmark_run.build_target",
        fake_build_target,
    )
    monkeypatch.setattr(
        "gaokaollm_bench.tests.manual.agent_benchmark_run.evaluate_transcript",
        evaluate_by_region_tree,
    )

    config = RunConfig(
        personas_path=persona_path,
        targets=["app_pareto", "hard_constraint"],
        max_turns=1,
        limit=None,
        output_dir=work_dir / "agent_benchmark",
        judge_model="mock-judge",
        simulator_model="mock-simulator",
        paper_summary_path=None,
    )
    personas = load_personas(persona_path)
    rows = []
    for target_name in config.targets:
        rows.extend(
            await run_target_cases(
                target_name=target_name,
                personas=personas,
                config=config,
                simulator_llm=FakeSimulatorLlm(),
                judge_llm=FakeJudgeLlm(),
            )
        )
    summary = write_summary_files(config=config, personas=personas, rows=rows)

    assert (
        summary["targets"]["app_pareto"]["elicitation_success_rate"]
        > summary["targets"]["hard_constraint"]["elicitation_success_rate"]
    )
    assert (
        summary["targets"]["app_pareto"]["mean_pareto_gain"]
        > summary["targets"]["hard_constraint"]["mean_pareto_gain"]
    )
    assert (
        config.output_dir / "transcripts/app_pareto/transcript_region-case-001.json"
    ).exists()
    assert (config.output_dir / "reports/app_pareto.jsonl").exists()
    assert (config.output_dir / "summary.json").exists()
    assert (config.output_dir / "summary.md").exists()

    shutil.rmtree(work_dir)
