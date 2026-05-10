from pathlib import Path

import pytest

from app.core.db_pg import close_pool
from app.flows.probers import (
    classify_risk_band,
    probe_city_relax,
    probe_major_geo_relax,
    probe_risk_band_relax,
    probe_strength_relax,
    probe_tuition_value_relax,
    run_all_probes,
    run_baseline,
)
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


class RiskDb:
    def __init__(self):
        self.calls = []

    async def __call__(self, query, *params):
        self.calls.append((query, params))
        if "score_rank_segments" in query:
            return [{"rank_min": 50000, "rank_max": 50100}]
        return [
            {
                "year": 2025,
                "school_id": 1,
                "school_name": "冲刺大学",
                "school_province": "娴欐睙",
                "school_city": "杭州",
                "major_id": 10,
                "major_name": "涓村簥鍖诲",
                "min_score": 598,
                "min_rank": 52000,
                "ranking": 80,
                "tier": 3,
            },
            {
                "year": 2025,
                "school_id": 2,
                "school_name": "稳妥大学",
                "school_province": "娴欐睙",
                "school_city": "宁波",
                "major_id": 20,
                "major_name": "涓村簥鍖诲",
                "min_score": 588,
                "min_rank": 60000,
                "ranking": 120,
                "tier": 2,
            },
            {
                "year": 2025,
                "school_id": 3,
                "school_name": "保底大学",
                "school_province": "娴欐睙",
                "school_city": "温州",
                "major_id": 30,
                "major_name": "涓村簥鍖诲",
                "min_score": 570,
                "min_rank": 75000,
                "ranking": 180,
                "tier": 2,
            },
        ]


class CityDb:
    def __init__(self):
        self.calls = []

    async def __call__(self, query, *params):
        self.calls.append((query, params))
        if len(self.calls) == 1:
            return [
                {
                    "school_id": 1,
                    "school_name": "杭州医学院",
                    "school_province": "浙江",
                    "school_city": "杭州",
                    "major_id": 10,
                    "major_name": "临床医学",
                    "min_score": 580,
                    "tier": 2,
                }
            ]
        return [
            {
                "year": 2025,
                "school_id": 2,
                "school_name": "宁波大学",
                "school_province": "浙江",
                "school_city": "宁波",
                "major_id": 20,
                "major_name": "临床医学",
                "min_score": 598,
                "ranking": 70,
                "tier": 3,
            }
        ]


def test_probers_flow_has_no_llm_dependency():
    source = Path("app/flows/probers.py").read_text(encoding="utf-8")

    assert "langchain" not in source.lower()
    assert "openai" not in source.lower()
    assert "get_chat_model" not in source


def test_risk_band_classifier_uses_rank_then_score_margin():
    assert classify_risk_band(score_margin=30, rank_gap=2500) == "chong"
    assert classify_risk_band(score_margin=3, rank_gap=10000) == "wen"
    assert classify_risk_band(score_margin=3, rank_gap=25000) == "bao"
    assert classify_risk_band(score_margin=3, rank_gap=45000) == "dian"
    assert classify_risk_band(score_margin=4) == "chong"
    assert classify_risk_band(score_margin=18) == "wen"
    assert classify_risk_band(score_margin=35) == "bao"


@pytest.mark.asyncio
async def test_risk_band_relax_keeps_hard_filters_and_returns_portfolio():
    db = RiskDb()
    constraints = {
        **STRICT_CONSTRAINTS,
        "risk_preference": "conservative",
    }

    rows = await probe_risk_band_relax(constraints, db=db, limit=3)

    probe_query, probe_params = db.calls[-1]
    assert "s.province = %s" in probe_query
    assert "a.major_name_raw LIKE %s" in probe_query
    assert "s.province <> %s" not in probe_query
    assert constraints["province"] in probe_params
    assert f"%{constraints['major']}%" in probe_params
    assert [row["risk_level"] for row in rows] == ["chong", "wen", "bao"]
    assert rows[0]["score_margin"] == 2
    assert rows[0]["rank_gap"] == 2000


@pytest.mark.asyncio
async def test_risk_band_relax_requires_conservative_signal():
    rows = await probe_risk_band_relax(STRICT_CONSTRAINTS, db=RiskDb(), limit=3)

    assert rows == []


@pytest.mark.asyncio
async def test_baseline_respects_city_constraint():
    db = CityDb()
    constraints = {**STRICT_CONSTRAINTS, "city": "杭州"}

    await run_baseline(constraints, db=db)

    query, params = db.calls[-1]
    assert "s.province = %s" in query
    assert "s.city = %s" in query
    assert "a.major_name_raw LIKE %s" in query
    assert constraints["province"] in params
    assert constraints["city"] in params
    assert f"%{constraints['major']}%" in params


@pytest.mark.asyncio
async def test_city_relax_drops_city_but_keeps_other_hard_filters():
    db = CityDb()
    constraints = {**STRICT_CONSTRAINTS, "city": "杭州"}

    rows = await probe_city_relax(constraints, db=db, limit=3)

    probe_query, probe_params = db.calls[-1]
    assert "s.province = %s" in probe_query
    assert "s.city = %s" not in probe_query
    assert "s.city <> %s" in probe_query
    assert "a.major_name_raw LIKE %s" in probe_query
    assert constraints["province"] in probe_params
    assert constraints["city"] in probe_params
    assert f"%{constraints['major']}%" in probe_params
    assert rows == [
        {
            "year": 2025,
            "school_id": 2,
            "school_name": "宁波大学",
            "school_province": "浙江",
            "school_city": "宁波",
            "major_id": 20,
            "major_name": "临床医学",
            "min_score": 598,
            "ranking": 70,
            "tier": 3,
        }
    ]


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


class StrengthDb:
    def __init__(self):
        self.calls = []

    async def __call__(self, query, *params):
        self.calls.append((query, params))
        if "sms.major_strength_rank < %s" not in query:
            return [
                {
                    "year": 2025,
                    "school_id": 1,
                    "school_name": "澶уA",
                    "school_province": "娴欐睙",
                    "school_city": "鏉窞",
                    "major_id": 10,
                    "major_name": "涓村簥鍖诲",
                    "min_score": 580,
                    "major_strength_rank": 260,
                    "major_strength_rating": "B+",
                    "major_strength_level": "discipline",
                    "ranking": 100,
                    "tier": 2,
                }
            ]
        return [
            {
                "year": 2025,
                "school_id": 2,
                "school_name": "澶уB",
                "school_province": "娴欐睙",
                "school_city": "瀹佹尝",
                "major_id": 20,
                "major_name": "涓村簥鍖诲",
                "min_score": 598,
                "major_strength_rank": 80,
                "major_strength_rating": "A",
                "major_strength_level": "discipline",
                "ranking": 50,
                "tier": 3,
            },
            {
                "year": 2025,
                "school_id": 3,
                "school_name": "澶уC",
                "school_province": "娴欐睙",
                "school_city": "娓╁窞",
                "major_id": 30,
                "major_name": "涓村簥鍖诲",
                "min_score": 596,
                "major_strength_rank": 120,
                "major_strength_rating": "A-",
                "major_strength_level": "discipline",
                "ranking": 80,
                "tier": 3,
            },
        ]


class TuitionDb:
    def __init__(self):
        self.calls = []

    async def __call__(self, query, *params):
        self.calls.append((query, params))
        if "plan.min_tuition > %s" not in query:
            return [
                {
                    "year": 2025,
                    "school_id": 1,
                    "school_name": "预算内大学",
                    "school_province": "浙江",
                    "school_city": "杭州",
                    "major_id": 10,
                    "major_name": "计算机科学与技术",
                    "min_score": 580,
                    "min_rank": 62000,
                    "tuition": 5000,
                    "ranking": 180,
                    "tier": 2,
                }
            ]
        return [
            {
                "year": 2025,
                "school_id": 2,
                "school_name": "性价比大学A",
                "school_province": "浙江",
                "school_city": "宁波",
                "major_id": 20,
                "major_name": "计算机科学与技术",
                "min_score": 598,
                "min_rank": 42000,
                "tuition": 9000,
                "ranking": 80,
                "tier": 3,
            },
            {
                "year": 2025,
                "school_id": 3,
                "school_name": "性价比大学B",
                "school_province": "浙江",
                "school_city": "温州",
                "major_id": 30,
                "major_name": "计算机科学与技术",
                "min_score": 596,
                "min_rank": 45000,
                "tuition": 12000,
                "ranking": 120,
                "tier": 2,
            },
        ]


@pytest.mark.asyncio
async def test_strength_relax_keeps_major_and_returns_stronger_rank_options():
    db = StrengthDb()
    constraints = {**STRICT_CONSTRAINTS, "strength": "school_strength"}

    rows = await probe_strength_relax(constraints, db=db, limit=2)

    baseline_query, baseline_params = db.calls[0]
    probe_query, probe_params = db.calls[-1]
    assert "s.province = %s" in baseline_query
    assert constraints["province"] in baseline_params
    assert "s.province = %s" not in probe_query
    assert "a.major_name_raw LIKE %s" in probe_query
    assert "sms.major_strength_rank < %s" in probe_query
    assert f"%{constraints['major']}%" in probe_params
    assert rows[0]["major_strength_rank"] == 80
    assert rows[1]["major_strength_rank"] == 120


@pytest.mark.asyncio
async def test_tuition_value_relax_keeps_hard_filters_and_returns_value_options():
    db = TuitionDb()
    constraints = {
        **STRICT_CONSTRAINTS,
        "major": "计算机科学与技术",
        "budget": 6000,
    }

    rows = await probe_tuition_value_relax(
        constraints, db=db, limit=2, budget_window=10000
    )

    baseline_query, baseline_params = db.calls[0]
    probe_query, probe_params = db.calls[-1]
    assert "s.province = %s" in baseline_query
    assert constraints["province"] in baseline_params
    assert "s.province = %s" in probe_query
    assert "a.major_name_raw LIKE %s" in probe_query
    assert "plan.min_tuition > %s" in probe_query
    assert "plan.min_tuition <= %s" in probe_query
    assert constraints["province"] in probe_params
    assert f"%{constraints['major']}%" in probe_params
    assert 6000 in probe_params
    assert 16000 in probe_params
    assert rows[0]["tuition"] == 9000
    assert rows[0]["tuition_delta"] == 3000
    assert rows[1]["tuition_delta"] == 6000
