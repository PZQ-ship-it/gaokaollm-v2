import json

import pytest

from gaokaollm_bench.data_gen.db_seeder import find_pareto_gaps
from gaokaollm_bench.data_gen.persona_builder import synthesize_persona
from gaokaollm_bench.schemas import IcebergPersona


class MockDbPool:
    def __init__(self):
        self.queries = []

    async def fetch(self, query, *params):
        self.queries.append((query, params))
        if "s.province = %s" in query:
            return [
                {
                    "year": 2025,
                    "school_id": 101,
                    "school_name": "浙江普通学院",
                    "school_province": "浙江",
                    "school_city": "杭州",
                    "is_985": False,
                    "is_211": False,
                    "is_double_first_class": False,
                    "education_level": "本科",
                    "ranking": 360,
                    "major_id": 201,
                    "major_name": "计算机类",
                    "min_score": 600,
                    "min_rank": 52000,
                    "tier": 2,
                }
            ]
        return [
            {
                "year": 2025,
                "school_id": 102,
                "school_name": "外省211大学",
                "school_province": "江苏",
                "school_city": "南京",
                "is_985": False,
                "is_211": True,
                "is_double_first_class": True,
                "education_level": "本科",
                "ranking": 80,
                "major_id": 202,
                "major_name": "计算机类",
                "min_score": 598,
                "min_rank": 50000,
                "tier": 3,
            }
        ]


class MockLlmClient:
    async def ainvoke(self, prompt):
        assert "外省211大学" in prompt
        assert "浙江普通学院" in prompt
        return json.dumps(
            {
                "case_id": "zj-gap-600-211",
                "background": {
                    "score": 600,
                    "province": "浙江",
                    "subjects": ["物理", "化学", "技术"],
                },
                "explicit_red_lines": {
                    "geo": "坚决不出浙江省",
                    "reason": "担心外省生活成本和适应问题",
                },
                "implicit_flexibilities": {
                    "trigger_school": "外省211大学",
                    "trigger_condition": "看到外省211大学2025年最低分598分低于本人600分",
                    "compromise": "愿意为了211层次考虑出省",
                },
                "initial_utterance": "我600分，只想留在浙江，外省学校先别推荐。",
                "process_milestones": {
                    "reject_generic_advice": True,
                    "recognize_tier_gap": "省内双非到省外211",
                    "accept_after_specific_score_evidence": True,
                },
            },
            ensure_ascii=False,
        )


@pytest.mark.asyncio
async def test_find_pareto_gaps_returns_real_tier_jump():
    db_pool = MockDbPool()

    gap = await find_pareto_gaps(db_pool, score=600, prov="浙江")

    assert gap["score"] == 600
    assert gap["province"] == "浙江"
    assert gap["constraint_relaxed"] == "province"
    assert gap["tier_a"]["school_name"] == "浙江普通学院"
    assert gap["tier_b"]["school_name"] == "外省211大学"
    assert gap["tier_delta"] == 1
    assert len(db_pool.queries) == 2


@pytest.mark.asyncio
async def test_synthesize_persona_returns_valid_iceberg_persona(capsys):
    gap = await find_pareto_gaps(MockDbPool(), score=600, prov="浙江")

    persona = await synthesize_persona(gap, MockLlmClient())

    assert isinstance(persona, IcebergPersona)
    assert persona.case_id == "zj-gap-600-211"
    assert persona.background["score"] == 600
    assert persona.explicit_red_lines["geo"] == "坚决不出浙江省"
    assert persona.implicit_flexibilities["trigger_school"] == "外省211大学"

    print(persona.model_dump_json(indent=2))
    captured = capsys.readouterr()
    assert "外省211大学" in captured.out
