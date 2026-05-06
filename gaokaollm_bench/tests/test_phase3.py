import json

import pytest

from gaokaollm_bench.schemas import IcebergPersona
from gaokaollm_bench.simulator.user_agent import UserSimulator


class MockSimulatorLlm:
    async def ainvoke(self, prompt):
        assert "必须只返回 JSON" in prompt
        agent_reply = prompt.split("被测系统回复:", 1)[1].split("请输出本轮 JSON。", 1)[0]
        if "山东大学" in agent_reply and "最低分638" in agent_reply:
            return json.dumps(
                {
                    "thought": "这确实击中了我的隐藏条件，省外985且分数够。",
                    "is_persuaded": True,
                    "utterance": "等等，山东大学如果638分真能上，那我愿意认真考虑出省。",
                },
                ensure_ascii=False,
            )
        return json.dumps(
            {
                "thought": "对方只是在讲大道理，没有具体学校和分数证据。",
                "is_persuaded": False,
                "utterance": "你说得太泛了，我还是不想出省。",
            },
            ensure_ascii=False,
        )


def build_persona():
    return IcebergPersona(
        case_id="zj-985-flex-001",
        background={
            "score": 642,
            "province": "浙江",
            "subjects": ["物理", "化学", "生物"],
        },
        explicit_red_lines={
            "geo": "坚决不出浙江省",
            "reason": "担心离家太远和生活不适应",
        },
        implicit_flexibilities={
            "trigger_school": "山东大学",
            "trigger_condition": "看到山东大学这类省外985且最低分638低于本人642分",
            "compromise": "愿意为了985层次考虑出省",
        },
        initial_utterance="我只想留在浙江读大学，外省学校再好也不考虑。",
        process_milestones={
            "reject_generic_advice": True,
            "accept_after_specific_985_score_evidence": True,
        },
    )


@pytest.mark.asyncio
async def test_user_simulator_rejects_empty_persuasion_then_accepts_real_gap():
    simulator = UserSimulator(build_persona(), MockSimulatorLlm())

    first_reply = await simulator.chat("年轻人应该打开眼界，外面的世界也很精彩。")

    assert simulator.internal_state["is_persuaded"] is False
    assert simulator.internal_state["turn_count"] == 1
    assert "不想出省" in first_reply

    second_reply = await simulator.chat(
        "具体看数据：山东大学是省外985，去年在浙江最低分638，低于你的642分。"
    )

    assert simulator.internal_state["is_persuaded"] is True
    assert simulator.internal_state["turn_count"] == 2
    assert "愿意认真考虑出省" in second_reply
    assert "隐藏条件" in simulator.internal_state["last_thought"]
