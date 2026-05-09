from pathlib import Path

import pytest

from app.core.db_pg import close_pool
from app.flows.probers import probe_major_geo_relax, run_all_probes, run_baseline
from tests._env_checks import require_database


STRICT_CONSTRAINTS = {
    "score": 600,
    "province": "浙江",
    "major": "临床医学",
    "budget": 100000,
}


class CapturingDb:
    def __init__(self):
        self.calls = []

    async def __call__(self, query, *params):
        self.calls.append((query, params))
        if len(self.calls) == 1:
            return [
                {
                    "school_id": 1,
                    "school_name": "浙江学院",
                    "school_province": "浙江",
                    "major_id": 10,
                    "major_name": "临床医学",
                    "min_score": 580,
                    "tier": 2,
                }
            ]
        return [
            {
                "year": 2023,
                "school_id": 2,
                "school_name": "西南交通大学",
                "school_province": "四川",
                "major_id": 20,
                "major_name": "生物医学工程",
                "min_score": 598,
                "ranking": 50,
                "tier": 3,
            },
            {
                "year": 2023,
                "school_id": 2,
                "school_name": "西南交通大学",
                "school_province": "四川",
                "major_id": 21,
                "major_name": "智能医学工程",
                "min_score": 596,
                "ranking": 50,
                "tier": 3,
            },
            {
                "year": 2022,
                "school_id": 3,
                "school_name": "广西大学",
                "school_province": "广西",
                "major_id": 30,
                "major_name": "药学",
                "min_score": 590,
                "ranking": 80,
                "tier": 3,
            },
        ]


class EmptyDb:
    async def __call__(self, query, *params):
        return []


def test_probers_flow_has_no_llm_dependency():
    source = Path("app/flows/probers.py").read_text(encoding="utf-8")

    assert "langchain" not in source.lower()
    assert "openai" not in source.lower()
    assert "get_chat_model" not in source


@pytest.mark.asyncio
async def test_major_geo_relax_drops_province_filter_and_selects_candidates():
    db = CapturingDb()

    rows = await probe_major_geo_relax(
        STRICT_CONSTRAINTS,
        db=db,
        limit=2,
        recommendation_threshold=2,
        max_per_school=1,
        major_tree_path="missing-major-tree.json",
    )

    probe_query, probe_params = db.calls[-1]
    assert "s.province = %s" not in probe_query
    assert "s.province <> %s" not in probe_query
    assert "a.major_name_raw NOT LIKE %s" in probe_query
    assert "%临床医学%" in probe_params
    assert rows == [
        {
            "year": 2023,
            "school_id": 2,
            "school_name": "西南交通大学",
            "school_province": "四川",
            "major_id": 20,
            "major_name": "生物医学工程",
            "min_score": 598,
            "ranking": 50,
            "tier": 3,
            "relaxation_stage": 5,
            "relaxation_stage_label": "去除专业限制",
            "relaxation_strategy": "any_major",
        },
        {
            "year": 2022,
            "school_id": 3,
            "school_name": "广西大学",
            "school_province": "广西",
            "major_id": 30,
            "major_name": "药学",
            "min_score": 590,
            "ranking": 80,
            "tier": 3,
            "relaxation_stage": 5,
            "relaxation_stage_label": "去除专业限制",
            "relaxation_strategy": "any_major",
        },
    ]


@pytest.mark.asyncio
async def test_major_geo_relax_missing_tree_falls_back_without_crashing():
    rows = await probe_major_geo_relax(
        STRICT_CONSTRAINTS,
        db=EmptyDb(),
        major_tree_path="missing-major-tree.json",
    )

    assert rows == []


@pytest.mark.asyncio
async def test_baseline_returns_only_local_ordinary_clinical_schools():
    require_database()
    baseline = await run_baseline(STRICT_CONSTRAINTS)
    await close_pool()

    assert baseline
    assert len(baseline) <= 3
    assert all(row["school_province"] == "浙江" for row in baseline)
    assert all("临床医学" in row["major_name"] for row in baseline)
    assert all(row["min_score"] <= STRICT_CONSTRAINTS["score"] for row in baseline)
    assert max(row["tier"] for row in baseline) == 2


@pytest.mark.asyncio
async def test_all_probes_find_real_higher_tier_opportunities():
    require_database()
    baseline = await run_baseline(STRICT_CONSTRAINTS)
    opportunities = await run_all_probes(STRICT_CONSTRAINTS)
    await close_pool()

    baseline_tier = max(row["tier"] for row in baseline)
    geo_relax = opportunities["geo_relax"]
    major_relax = opportunities["major_relax"]
    major_geo_relax = opportunities["major_geo_relax"]

    assert geo_relax
    assert all(row["tier"] > baseline_tier for row in geo_relax)
    assert all(
        row["school_province"] != STRICT_CONSTRAINTS["province"] for row in geo_relax
    )
    assert any(row["school_name"] == "石河子大学" for row in geo_relax)

    assert major_relax
    assert all(row["tier"] > baseline_tier for row in major_relax)
    assert all(
        row["school_province"] == STRICT_CONSTRAINTS["province"] for row in major_relax
    )
    assert any(row["school_name"] == "宁波大学" for row in major_relax)

    assert major_geo_relax
    assert all(row["tier"] > baseline_tier for row in major_geo_relax)
    assert any(
        row["school_province"] != STRICT_CONSTRAINTS["province"]
        for row in major_geo_relax
    )
    assert any("临床医学" not in row["major_name"] for row in major_geo_relax)
