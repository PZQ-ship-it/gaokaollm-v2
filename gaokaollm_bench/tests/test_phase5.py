import json
from pathlib import Path

import pytest

from gaokaollm_bench.evaluator.deterministic_judge import check_hallucination
from gaokaollm_bench.evaluator.llm_as_a_judge import evaluate_process
from gaokaollm_bench.schemas import ConversationTurn, IcebergPersona, Transcript


class MockDbPool:
    async def fetch(self, query, *params):
        school_name = params[0]
        if school_name == "山东大学":
            return [{"school_name": "山东大学", "min_score": 638}]
        return []


class MockJudgeLlm:
    async def ainvoke(self, prompt):
        assert "Transcript:" in prompt
        assert "山东大学" in prompt
        return json.dumps(
            {
                "case_id": "zj-phase5-001",
                "hallucination_rate": 0.0,
                "elicitation_success": True,
                "pareto_gain": 2,
                "judge_reasoning": "被测系统先识别地理红线，再用山东大学985层次和638分证据触发隐藏妥协条件。",
            },
            ensure_ascii=False,
        )


def build_transcript():
    persona = IcebergPersona(
        case_id="zj-phase5-001",
        background={
            "score": 642,
            "province": "浙江",
            "subjects": ["物理", "化学", "生物"],
        },
        explicit_red_lines={"geo": "坚决不出浙江省"},
        implicit_flexibilities={
            "trigger_school": "山东大学",
            "trigger_condition": "山东大学省外985且最低分638低于本人642分",
        },
        initial_utterance="我只想留在浙江读大学，外省学校再好也不考虑。",
        process_milestones={"accept_after_specific_985_score_evidence": True},
    )
    return Transcript(
        persona=persona,
        turns=[
            ConversationTurn(
                turn_id=1,
                role="user",
                content=persona.initial_utterance,
                internal_state={"is_persuaded": False},
            ),
            ConversationTurn(
                turn_id=2,
                role="target_agent",
                content="具体看数据：山东大学是省外985，去年在浙江最低分638，低于你的642分。",
                internal_state={
                    "school": "山东大学",
                    "tier_before": 2,
                    "tier_after": 4,
                },
            ),
            ConversationTurn(
                turn_id=3,
                role="user",
                content="这个数据有点打动我，我愿意认真考虑山东大学。",
                internal_state={"is_persuaded": True},
            ),
        ],
    )


@pytest.mark.asyncio
async def test_phase5_evaluators_load_transcript_and_emit_report():
    transcript = build_transcript()
    output_dir = Path("gaokaollm_bench/tests/_phase5_output")
    output_dir.mkdir(parents=True, exist_ok=True)
    transcript_path = output_dir / "transcript_zj-phase5-001.json"
    transcript_path.write_text(transcript.model_dump_json(indent=2), encoding="utf-8")

    loaded = Transcript.model_validate_json(transcript_path.read_text(encoding="utf-8"))
    hallucination_rate = await check_hallucination(loaded, MockDbPool())
    report = await evaluate_process(loaded, loaded.persona, MockJudgeLlm())
    report = report.model_copy(update={"hallucination_rate": hallucination_rate})

    assert hallucination_rate == 0.0
    assert report.case_id == "zj-phase5-001"
    assert report.elicitation_success is True
    assert report.pareto_gain == 2
    assert "山东大学" in report.judge_reasoning

    print(report.model_dump())

    transcript_path.unlink()
    output_dir.rmdir()
