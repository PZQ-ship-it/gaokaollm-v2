import json
import shutil
from pathlib import Path
from types import SimpleNamespace

import pytest

from gaokaollm_bench.evaluator.deterministic_judge import check_hallucination
from gaokaollm_bench.evaluator.llm_as_a_judge import evaluate_process
from gaokaollm_bench.sandbox.target_agents import (
    AppGraphTargetAgent,
    HardConstraintBaselineAgent,
)
from gaokaollm_bench.schemas import IcebergPersona
from gaokaollm_bench.tests.manual.agent_benchmark_run import (
    RunConfig,
    load_personas,
    run_target_cases,
    write_summary_files,
)


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
                "major_geo_relax": [
                    {
                        "school_name": "西南交通大学",
                        "school_province": "四川",
                        "major_name": "生物医学工程",
                        "min_score": 597,
                        "tier": 3,
                    }
                ],
            },
            "score_waste": 10,
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
        "major_relax": [],
        "major_geo_relax": [],
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
