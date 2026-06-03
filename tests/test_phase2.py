import json
import shutil
from pathlib import Path

import pytest

from app.core.db_pg import close_pool
from app.flows.probers import (
    _MAJOR_SIMILARITY_CACHE,
    _MAJOR_VECTOR_CACHE,
    _major_similarity_text,
    annotate_full_context_semantic_score,
    annotate_major_similarity,
    classify_risk_band,
    extract_phi_features,
    probe_city_relax,
    probe_employment_outcome_relax,
    probe_major_geo_relax,
    probe_major_quality_relax,
    probe_region_tree_relax,
    probe_risk_band_relax,
    probe_strength_relax,
    probe_tuition_value_relax,
    rank_by_implicit_utility,
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
                    "ranking": 180,
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


class MajorQualityDb:
    def __init__(self):
        self.calls = []

    async def __call__(self, query, *params):
        self.calls.append((query, params))
        if len(self.calls) == 1:
            return [
                {
                    "year": 2025,
                    "school_id": 1,
                    "school_name": "省内锚点大学",
                    "school_province": "浙江",
                    "school_city": "杭州",
                    "major_id": 10,
                    "major_name": "软件工程",
                    "min_score": 570,
                    "min_rank": 70000,
                    "quality_score": 72,
                    "quality_tier": "C",
                    "best_major_rank": 90,
                    "best_rating": "B",
                    "tier": 2,
                }
            ]
        return [
            {
                "year": 2025,
                "school_id": 2,
                "school_name": "专业强校大学",
                "school_province": "江苏",
                "school_city": "南京",
                "major_id": 10,
                "major_name": "软件工程",
                "min_score": 588,
                "min_rank": 52000,
                "quality_score": 95,
                "quality_tier": "A",
                "best_major_rank": 8,
                "best_rating": "A",
                "has_key_major": True,
                "has_featured_major": False,
                "quality_evidence_sources": [
                    {"source_type": "major_ranking", "evidence_label": "专业排名 8"}
                ],
                "ranking": 80,
                "tier": 3,
            },
            {
                "year": 2025,
                "school_id": 3,
                "school_name": "特色专业大学",
                "school_province": "安徽",
                "school_city": "合肥",
                "major_id": 10,
                "major_name": "软件工程",
                "min_score": 580,
                "min_rank": 59000,
                "quality_score": 84,
                "quality_tier": "B",
                "best_major_rank": None,
                "best_rating": "B+",
                "has_key_major": False,
                "has_featured_major": True,
                "ranking": 120,
                "tier": 2,
            },
        ]


class EmploymentOutcomeDb:
    def __init__(self):
        self.calls = []

    async def __call__(self, query, *params):
        self.calls.append((query, params))
        if len(self.calls) == 1:
            return [
                {
                    "year": 2025,
                    "school_id": 1,
                    "school_name": "省内就业锚点大学",
                    "school_province": "浙江",
                    "school_city": "杭州",
                    "major_id": 10,
                    "major_name": "软件工程",
                    "min_score": 570,
                    "min_rank": 70000,
                    "outcome_score": 62,
                    "outcome_tier": "D",
                    "employment_rank": 42,
                    "top_industry": "软件服务",
                    "tier": 2,
                }
            ]
        return [
            {
                "year": 2025,
                "school_id": 2,
                "school_name": "就业强校大学",
                "school_province": "江苏",
                "school_city": "南京",
                "major_id": 10,
                "major_name": "软件工程",
                "min_score": 588,
                "min_rank": 52000,
                "outcome_score": 88,
                "outcome_tier": "B",
                "employment_rank": 9,
                "top_industry": "互联网",
                "salary_distribution": {"items": ["10k-15k"]},
                "employment_evidence_sources": [
                    "employment_rank=9",
                    "salary_distribution",
                ],
                "ranking": 80,
                "tier": 3,
            },
            {
                "year": 2025,
                "school_id": 3,
                "school_name": "行业特色大学",
                "school_province": "安徽",
                "school_city": "合肥",
                "major_id": 11,
                "major_name": "计算机科学与技术",
                "min_score": 580,
                "min_rank": 59000,
                "outcome_score": 80,
                "outcome_tier": "B",
                "employment_rank": 17,
                "top_industry": "信息技术",
                "ranking": 120,
                "tier": 2,
            },
        ]


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
                "min_rank": 45000,
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
                "min_rank": 53000,
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
                "min_rank": 65000,
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


class RegionTreeDb:
    def __init__(self):
        self.calls = []

    async def __call__(self, query, *params):
        self.calls.append((query, params))
        if len(self.calls) == 1:
            return [
                {
                    "year": 2025,
                    "school_id": 1,
                    "school_name": "Hangzhou Anchor University",
                    "school_province": "Zhejiang",
                    "school_city": "Hangzhou City",
                    "major_id": 10,
                    "major_name": "Computer Science",
                    "min_score": 580,
                    "min_rank": 70000,
                    "ranking": 180,
                    "tier": 2,
                }
            ]
        return [
            {
                "year": 2025,
                "school_id": 2,
                "school_name": "Ningbo Jump University",
                "school_province": "Zhejiang",
                "school_city": "Ningbo City",
                "major_id": 20,
                "major_name": "Computer Science",
                "min_score": 596,
                "min_rank": 52000,
                "ranking": 80,
                "tier": 3,
            }
        ]


def test_probers_flow_has_no_llm_dependency():
    source = Path("app/flows/probers.py").read_text(encoding="utf-8")

    assert "langchain" not in source.lower()
    assert "openai" not in source.lower()
    assert "get_chat_model" not in source


def test_extract_phi_features_maps_school_tiers_and_budget_penalties():
    state = {"constraints": {"budget": 10000}}

    assert extract_phi_features({"school_tier": "C9"}, state)["school"] == 1.0
    assert extract_phi_features({"school_tier": "顶尖985"}, state)["school"] == 1.0
    assert extract_phi_features({"school_tier": "985高校"}, state)["school"] == 0.85
    assert extract_phi_features({"school_tier": "211 双一流"}, state)["school"] == 0.70
    assert extract_phi_features({"school_tier": "一本重点"}, state)["school"] == 0.40
    assert extract_phi_features({"school_tier": "普通本科"}, state)["school"] == 0.10

    budget_ok = extract_phi_features({"tuition": "6000元/年"}, state)
    assert budget_ok["tuition"] == 1.0

    small_excess = extract_phi_features({"tuition": "12000元/年"}, state)
    assert small_excess["tuition"] == pytest.approx(0.6)

    veto = extract_phi_features({"tuition": "15000元/年"}, state)
    assert veto["tuition"] == -9999.0


def test_extract_phi_features_handles_dirty_or_missing_values():
    features = extract_phi_features(
        {
            "school_tier": None,
            "major_relax_level": "bad",
            "geo_relax_level": object(),
            "quality_score": "bad",
            "tuition": "bad",
        },
        {},
    )

    assert set(features) == {"school", "major", "tuition", "quality", "geo", "risk"}
    assert features["tuition"] == 1.0
    assert features["quality"] == 0.5


def test_major_similarity_score_is_explanatory_not_primary_utility():
    state = {"constraints": {"major": "医学"}}

    close = extract_phi_features(
        {"major_relax_level": 1, "major_similarity_score": 0.86},
        state,
    )
    distant = extract_phi_features(
        {"major_relax_level": 1, "major_similarity_score": 0.52},
        state,
    )
    stage_only = extract_phi_features({"major_relax_level": 1}, state)

    assert close["major"] == pytest.approx(stage_only["major"])
    assert distant["major"] == pytest.approx(stage_only["major"])
    assert stage_only["major"] > 0.0


def test_major_similarity_text_keeps_semantic_parenthetical_content():
    assert "水生动物医学" in _major_similarity_text("水产类(含水生动物医学)")
    assert "校区" not in _major_similarity_text("动物医学(凤凰校区)")


@pytest.mark.asyncio
async def test_major_similarity_does_not_boost_broad_keyword_substrings(monkeypatch):
    class FakeEmbeddingClient:
        async def embed(self, texts):
            vectors = []
            for text in texts:
                if text == "医学":
                    vectors.append([1.0, 0.0])
                elif "生物医学工程" in text:
                    vectors.append([0.8, 0.6])
                elif "水产类" in text:
                    vectors.append([0.5, 0.866])
                else:
                    vectors.append([0.0, 1.0])
            return vectors

    from app.flows import probers

    _MAJOR_VECTOR_CACHE.clear()
    _MAJOR_SIMILARITY_CACHE.clear()
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    monkeypatch.setenv("EMBEDDING_MODEL", "fake-embedding")
    monkeypatch.setattr(
        probers.embedding_client,
        "OpenAIEmbeddingClient",
        lambda: FakeEmbeddingClient(),
    )

    rows = await annotate_major_similarity(
        [
            {"major_name": "生物医学工程"},
            {"major_name": "水产类(含水生动物医学)"},
        ],
        {"constraints": {"major": "医学"}},
    )

    biomedical, aquatic = rows
    assert biomedical["major_similarity_score"] == pytest.approx(0.8)
    assert aquatic["major_similarity_score"] == pytest.approx(0.5, abs=0.001)
    assert aquatic["major_similarity_score"] < biomedical["major_similarity_score"]


@pytest.mark.asyncio
async def test_full_context_semantic_score_is_pgvector_annotation(monkeypatch):
    async def fake_fetch(db, query, params):
        assert "knowledge_documents" in query
        return [
            {
                "admission_score_id": 1,
                "school_id": 10,
                "major_id": 100,
                "major_name": "临床医学",
                "semantic_score": 0.91,
            },
            {
                "admission_score_id": 2,
                "school_id": 20,
                "major_id": 200,
                "major_name": "水产类",
                "semantic_score": 0.42,
            },
        ]

    monkeypatch.setattr("app.flows.probers._fetch", fake_fetch)

    rows = await annotate_full_context_semantic_score(
        [
            {
                "admission_score_id": 1,
                "school_id": 10,
                "major_id": 100,
                "major_name": "临床医学",
            },
            {
                "admission_score_id": 2,
                "school_id": 20,
                "major_id": 200,
                "major_name": "水产类",
            },
        ],
        {"full_context_embedding": [1.0] * 1536},
        db=object(),
    )

    assert rows[0]["semantic_score"] == pytest.approx(0.91)
    assert rows[0]["semantic_score_source"] == "knowledge_documents_pgvector"
    assert rows[1]["semantic_score"] == pytest.approx(0.42)


def test_lexicographic_sort_uses_semantic_score_only_inside_epsilon():
    state = {
        "constraints": {"budget": 10000},
        "lexicographic_epsilon": 0.01,
        "implicit_weights": {
            "school": 1.0,
            "major": 0.0,
            "tuition": 0.0,
            "quality": 0.0,
            "geo": 0.0,
            "risk": 0.0,
        },
    }
    ranked = rank_by_implicit_utility(
        [
            {
                "school_name": "语义更贴合大学",
                "tier": 2,
                "quality_score": 80,
                "tuition": 8000,
                "semantic_score": 0.95,
            },
            {
                "school_name": "语义稍弱大学",
                "tier": 2,
                "quality_score": 80,
                "tuition": 8000,
                "semantic_score": 0.20,
            },
            {
                "school_name": "主效用更高大学",
                "tier": 3,
                "quality_score": 80,
                "tuition": 8000,
                "semantic_score": 0.01,
            },
        ],
        state,
    )

    assert ranked[0]["school_name"] == "主效用更高大学"
    assert ranked[1]["school_name"] == "语义更贴合大学"
    assert ranked[2]["school_name"] == "语义稍弱大学"


def test_rank_by_implicit_utility_vetoes_ghost_trap_option():
    state = {
        "constraints": {"budget": 10000},
        "implicit_weights": {
            "school": 0.25,
            "major": 0.25,
            "tuition": 0.25,
            "quality": 0.25,
            "geo": 0.25,
            "risk": 0.0,
        },
    }
    ranked = rank_by_implicit_utility(
        [
            {
                "school_name": "高性价比一本大学",
                "school_tier": "一本重点",
                "major_relax_level": 0,
                "geo_relax_level": 0,
                "quality_score": 75,
                "tuition": 8000,
            },
            {
                "school_name": "幽灵陷阱C9大学",
                "school_tier": "C9",
                "major_relax_level": 0,
                "geo_relax_level": 0,
                "quality_score": 95,
                "tuition": "15000元/年",
            },
        ],
        state,
    )

    assert ranked[0]["school_name"] == "高性价比一本大学"
    assert ranked[0]["_implicit_utility"] > ranked[1]["_implicit_utility"]
    assert ranked[1]["_phi_features"]["tuition"] == -9999.0


def test_risk_band_classifier_uses_rank_then_score_margin():
    assert classify_risk_band(score_margin=30, rank_ratio=0.90) == "chong"
    assert classify_risk_band(score_margin=3, rank_ratio=1.05) == "wen"
    assert classify_risk_band(score_margin=3, rank_ratio=1.25) == "bao"
    assert classify_risk_band(score_margin=3, rank_ratio=1.50) == "dian"
    assert classify_risk_band(score_margin=3, rank_gap=-3000) == "chong"
    assert classify_risk_band(score_margin=3, rank_gap=10000) == "wen"
    assert classify_risk_band(score_margin=4) == "chong"
    assert classify_risk_band(score_margin=18) == "wen"
    assert classify_risk_band(score_margin=35) == "bao"


@pytest.mark.asyncio
async def test_risk_band_relax_keeps_hard_filters_and_returns_material_risk_options():
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
    assert [row["risk_level"] for row in rows] == ["chong"]
    assert rows[0]["risk_relax_level"] == 1
    assert rows[0]["score_margin"] == 2
    assert rows[0]["student_rank"] == 50100
    assert rows[0]["rank_gap"] == -5100
    assert rows[0]["rank_ratio"] == pytest.approx(0.8982, abs=0.0001)


@pytest.mark.asyncio
async def test_risk_band_relax_runs_as_default_elasticity_probe():
    rows = await probe_risk_band_relax(STRICT_CONSTRAINTS, db=RiskDb(), limit=3)

    assert [row["risk_level"] for row in rows] == ["chong"]


@pytest.mark.asyncio
async def test_marginal_one_point_reach_is_not_risk_relaxation():
    class MildRiskDb:
        async def __call__(self, query, *params):
            if "score_rank_segments" in query:
                return [{"rank_min": 52000, "rank_max": 52529}]
            return [
                {
                    "year": 2025,
                    "school_id": 1,
                    "school_name": "Mild Reach Medical University",
                    "school_province": "黑龙江",
                    "school_city": "哈尔滨",
                    "major_id": 10,
                    "major_name": "精神医学",
                    "min_score": 601,
                    "min_rank": 51129,
                    "ranking": 125,
                    "tier": 2,
                }
            ]

    rows = await probe_risk_band_relax(STRICT_CONSTRAINTS, db=MildRiskDb(), limit=3)

    assert rows == []


@pytest.mark.asyncio
async def test_run_all_probes_applies_accepted_geo_major_relaxations():
    calls: list[tuple[str, tuple[object, ...]]] = []

    async def fake_db(query, *params):
        calls.append((query, params))
        if "score_rank_segments" in query:
            return [{"rank_min": 52000, "rank_max": 52529}]
        return []

    constraints = {
        **STRICT_CONSTRAINTS,
        "target_provinces": ["江苏", "浙江", "上海"],
        "city": "杭州",
    }
    await run_all_probes(
        constraints,
        db=fake_db,
        user_state={
            "constraints": constraints,
            "accepted_relaxations": [
                {"dimension": "geo"},
                {"dimension": "major"},
            ],
        },
    )

    combined_queries = "\n".join(query for query, _params in calls)
    combined_params = [param for _query, params in calls for param in params]
    assert "s.province = ANY(%s::text[])" not in combined_queries
    assert "s.city = ANY(%s::text[])" not in combined_queries
    assert "a.major_name_raw LIKE %s" not in combined_queries
    assert ["江苏", "浙江", "上海"] not in combined_params
    assert "%临床医学%" not in combined_params


@pytest.mark.asyncio
async def test_baseline_respects_city_constraint():
    db = CityDb()
    constraints = {**STRICT_CONSTRAINTS, "city": "杭州"}

    await run_baseline(constraints, db=db)

    query, params = db.calls[-1]
    assert "s.province = %s" in query
    assert "s.city = ANY(%s::text[])" in query
    assert "a.major_name_raw LIKE %s" in query
    assert constraints["province"] in params
    assert any(
        isinstance(param, list) and constraints["city"] in param for param in params
    )
    assert f"%{constraints['major']}%" in params


@pytest.mark.asyncio
async def test_baseline_uses_target_provinces_when_present():
    db = CityDb()
    constraints = {
        **STRICT_CONSTRAINTS,
        "target_provinces": ["江苏", "浙江", "上海"],
        "major": "医学",
        "budget": 5500,
    }

    await run_baseline(constraints, db=db)

    query, params = db.calls[-1]
    assert "s.province = ANY(%s::text[])" in query
    assert "s.province = %s" not in query
    assert "plan.min_tuition IS NOT NULL" in query
    assert "plan.min_tuition <= %s" in query
    assert ["江苏", "浙江", "上海"] in params
    assert "浙江" not in params
    assert 5500 in params
    assert "%医学%" in params


@pytest.mark.asyncio
async def test_city_relax_drops_city_but_keeps_other_hard_filters():
    db = CityDb()
    constraints = {**STRICT_CONSTRAINTS, "city": "杭州"}

    rows = await probe_city_relax(constraints, db=db, limit=3)

    probe_query, probe_params = db.calls[-1]
    assert "s.province = %s" in probe_query
    assert "s.city = %s" not in probe_query
    assert "s.city <> ALL(%s::text[])" in probe_query
    assert "a.major_name_raw LIKE %s" in probe_query
    assert constraints["province"] in probe_params
    assert any(
        isinstance(param, list) and constraints["city"] in param
        for param in probe_params
    )
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
async def test_region_tree_relax_uses_tree_nodes_and_keeps_hard_filters():
    db = RegionTreeDb()
    constraints = {
        "score": 600,
        "province": "Zhejiang",
        "city": "Hangzhou",
        "major": "Computer Science",
        "budget": 100000,
    }
    geo_tree = {
        "nodes": [
            {
                "node_id": "geo:china",
                "name": "China",
                "parent_id": None,
                "aliases": [],
                "tree_type": "geo",
                "mapping_rule": "manual",
                "confidence": 1.0,
                "review_status": "reviewed",
                "source": "test",
            },
            {
                "node_id": "geo:zhejiang",
                "name": "Zhejiang",
                "parent_id": "geo:china",
                "aliases": [],
                "tree_type": "geo",
                "mapping_rule": "manual",
                "confidence": 1.0,
                "review_status": "reviewed",
                "source": "test",
            },
            {
                "node_id": "geo:hangzhou",
                "name": "Hangzhou",
                "parent_id": "geo:zhejiang",
                "aliases": ["Hangzhou City"],
                "tree_type": "geo",
                "mapping_rule": "manual",
                "confidence": 0.95,
                "review_status": "reviewed",
                "source": "test",
            },
            {
                "node_id": "geo:ningbo",
                "name": "Ningbo",
                "parent_id": "geo:zhejiang",
                "aliases": ["Ningbo City"],
                "tree_type": "geo",
                "mapping_rule": "manual",
                "confidence": 0.95,
                "review_status": "reviewed",
                "source": "test",
            },
        ]
    }
    urban_tree = {
        "nodes": [
            {
                "node_id": "urban:tier:new_first",
                "name": "New First",
                "parent_id": None,
                "aliases": [],
                "tree_type": "urban_tier",
                "mapping_rule": "manual",
                "confidence": 1.0,
                "review_status": "reviewed",
                "source": "test",
            }
        ]
    }
    tmp_dir = Path("tests/_tmp_region_tree")
    try:
        tmp_dir.mkdir(parents=True, exist_ok=True)
        geo_path = tmp_dir / "geo.json"
        urban_path = tmp_dir / "urban.json"
        geo_path.write_text(json.dumps(geo_tree), encoding="utf-8")
        urban_path.write_text(json.dumps(urban_tree), encoding="utf-8")

        rows = await probe_region_tree_relax(
            constraints,
            db=db,
            limit=1,
            geo_tree_path=geo_path,
            urban_tree_path=urban_path,
        )

        assert rows
        probe_query, probe_params = db.calls[-1]
        assert "s.city = ANY(%s::text[])" in probe_query
        assert "s.city <> ALL(%s::text[])" in probe_query
        assert "a.major_name_raw LIKE %s" in probe_query
        assert f"%{constraints['major']}%" in probe_params
        assert rows[0]["region_relax_strategy"] in {
            "geo_block_relax",
            "urban_tier_relax",
        }
        assert rows[0]["target_region_node_id"]
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


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
    assert "s.ranking IS NOT NULL AND s.ranking < %s" in probe_query
    assert "%临床医学%" in probe_params
    assert len(rows) == 2
    assert rows[0]["school_id"] == 2
    assert rows[0]["major_id"] == 20
    assert rows[0]["relaxation_stage"] == 5
    assert rows[0]["relaxation_strategy"] == "any_major"
    assert rows[0]["geo_relax_level"] == 1
    assert rows[0]["major_relax_level"] == 5
    assert rows[0]["_phi_features"]["geo"] < 1.0
    assert rows[0]["_phi_features"]["major"] < 1.0
    assert "_phi_features" in rows[0]
    assert "_implicit_utility" in rows[0]
    assert rows[1]["school_id"] == 3
    assert rows[1]["major_id"] == 30


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
async def test_major_quality_relax_keeps_major_and_returns_quality_options():
    db = MajorQualityDb()
    constraints = {
        **STRICT_CONSTRAINTS,
        "province": "浙江",
        "major": "软件工程",
        "strength": "school_strength",
    }

    rows = await probe_major_quality_relax(constraints, db=db, limit=2)

    baseline_query, baseline_params = db.calls[0]
    probe_query, probe_params = db.calls[-1]
    assert "s.province = %s" in baseline_query
    assert constraints["province"] in baseline_params
    assert "s.province <> %s" in probe_query
    assert "a.major_name_raw LIKE %s" in probe_query
    assert "mq.quality_score >= %s" in probe_query
    assert constraints["province"] in probe_params
    assert f"%{constraints['major']}%" in probe_params
    assert rows[0]["quality_score"] == 95
    assert rows[0]["quality_gain"] == 23
    assert rows[0]["best_major_rank"] == 8
    assert rows[0]["quality_evidence_sources"][0]["source_type"] == "major_ranking"


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
    assert "_phi_features" in rows[0]
    assert "_implicit_utility" in rows[0]


@pytest.mark.asyncio
async def test_employment_outcome_relax_returns_outcome_evidence():
    db = EmploymentOutcomeDb()
    constraints = {
        **STRICT_CONSTRAINTS,
        "province": "浙江",
        "major": "软件工程",
        "employment_preference": "employment_outcome",
    }

    rows = await probe_employment_outcome_relax(
        constraints,
        db=db,
        limit=2,
        min_outcome_gain=10,
    )

    baseline_query, baseline_params = db.calls[0]
    probe_query, probe_params = db.calls[-1]
    assert "s.province = %s" in baseline_query
    assert constraints["province"] in baseline_params
    assert "s.province <> %s" in probe_query
    assert "me.outcome_score >= %s" in probe_query
    assert constraints["province"] in probe_params
    assert rows[0]["outcome_score"] == 88
    assert rows[0]["outcome_gain"] == 26
    assert rows[0]["employment_rank"] == 9
    assert rows[0]["top_industry"] == "互联网"
