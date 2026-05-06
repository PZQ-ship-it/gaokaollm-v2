import json
from pathlib import Path

import pytest

from gaokaollm_bench.sandbox.arena import run_episode
from gaokaollm_bench.sandbox.base_target import BaseTargetAgent
from gaokaollm_bench.schemas import IcebergPersona, Transcript


class MockTargetAgent(BaseTargetAgent):
    def __init__(self):
        self.calls = 0

    async def chat(self, user_input):
        self.calls += 1
        if self.calls == 1:
            return (
                "外省也有很多机会，你可以稍微打开一点范围。",
                {"calls": self.calls, "strategy": "generic"},
            )
        return (
            "具体看数据：山东大学是省外985，去年在浙江最低分638，低于你的642分。",
            {"calls": self.calls, "strategy": "specific_pareto_gap", "school": "山东大学"},
        )


class MockSimulatorLlm:
    async def ainvoke(self, prompt):
        agent_reply = prompt.split("被测系统回复:", 1)[1].split("请输出本轮 JSON。", 1)[0]
        if "山东大学" in agent_reply and "最低分638" in agent_reply:
            return json.dumps(
                {
                    "thought": "具体985和分数对比满足隐藏妥协条件。",
                    "is_persuaded": True,
                    "utterance": "这个数据有点打动我，我愿意认真考虑山东大学。",
                },
                ensure_ascii=False,
            )
        return json.dumps(
            {
                "thought": "仍然只是泛泛扩大范围，没有证据。",
                "is_persuaded": False,
                "utterance": "还是太泛了，我暂时不想出省。",
            },
            ensure_ascii=False,
        )


def build_persona():
    return IcebergPersona(
        case_id="zj-arena-985-001",
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


@pytest.mark.asyncio
async def test_run_episode_stops_on_persuasion_and_persists_transcript():
    target = MockTargetAgent()
    output_dir = Path("gaokaollm_bench/tests/_phase4_output")
    output_path = output_dir / "transcript_zj-arena-985-001.json"
    if output_path.exists():
        output_path.unlink()

    transcript = await run_episode(
        build_persona(),
        target,
        max_turns=6,
        simulator_llm_client=MockSimulatorLlm(),
        output_dir=output_dir,
    )

    assert target.calls == 2
    assert len(transcript.turns) == 5
    assert transcript.turns[-1].role == "user"
    assert transcript.turns[-1].internal_state["is_persuaded"] is True
    assert any(turn.internal_state.get("school") == "山东大学" for turn in transcript.turns)

    assert output_path.exists()

    restored = Transcript.model_validate_json(output_path.read_text(encoding="utf-8"))
    assert restored == transcript
    assert restored.turns[-1].content == "这个数据有点打动我，我愿意认真考虑山东大学。"

    output_path.unlink()
    output_dir.rmdir()
