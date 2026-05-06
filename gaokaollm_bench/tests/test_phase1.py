from gaokaollm_bench.schemas import ConversationTurn, IcebergPersona, Transcript


def test_iceberg_persona_json_round_trip():
    persona = IcebergPersona(
        case_id="zj-985-flex-001",
        background={
            "score": 642,
            "province": "浙江",
            "subjects": ["物理", "化学", "生物"],
        },
        explicit_red_lines={
            "geo": "坚决不出省",
            "school_type": "不接受普通双非院校",
        },
        implicit_flexibilities={
            "trigger": "只有看到省外985院校名称和真实分数对比才会动摇",
            "acceptable_school_names": ["山东大学", "吉林大学"],
            "required_evidence": "目标院校近年最低分不高于本人分数",
        },
        initial_utterance="我只想留在浙江读大学，外省学校再好也不考虑。",
        process_milestones={
            "resist_generic_persuasion": True,
            "notice_specific_985_gap": True,
            "accept_geo_compromise": True,
        },
    )

    payload = persona.model_dump_json()
    restored = IcebergPersona.model_validate_json(payload)

    assert restored == persona
    assert restored.background["score"] == 642
    assert restored.explicit_red_lines["geo"] == "坚决不出省"
    assert "山东大学" in restored.implicit_flexibilities["acceptable_school_names"]


def test_transcript_json_round_trip_with_persona_and_turns():
    persona = IcebergPersona(
        case_id="zj-985-flex-001",
        background={
            "score": 642,
            "province": "浙江",
            "subjects": ["物理", "化学", "生物"],
        },
        explicit_red_lines={"geo": "坚决不出省"},
        implicit_flexibilities={"trigger": "看到省外985真实分数对比会妥协"},
        initial_utterance="我只想留在浙江读大学，外省学校再好也不考虑。",
        process_milestones={"accept_geo_compromise": True},
    )
    transcript = Transcript(
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
                content="如果看真实分数，山东大学去年在浙江最低分低于642分。",
                internal_state={"candidate_school": "山东大学"},
            ),
        ],
    )

    payload = transcript.model_dump_json()
    restored = Transcript.model_validate_json(payload)

    assert restored == transcript
    assert restored.persona.case_id == "zj-985-flex-001"
    assert restored.turns[0].role == "user"
    assert restored.turns[1].internal_state["candidate_school"] == "山东大学"
