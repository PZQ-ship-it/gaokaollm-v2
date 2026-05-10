import json

import pytest

from gaokaollm_bench.data_gen.db_seeder import (
    find_city_relax_gap_sets,
    find_hierarchical_major_relax_gap_sets,
    find_strength_relax_gap_sets,
    find_risk_band_gap_sets,
    find_tuition_value_gap_sets,
)
from gaokaollm_bench.data_gen.generate_personas import (
    build_deterministic_persona,
    build_deterministic_persona_from_gap_set,
)
from gaokaollm_bench.data_gen.major_tree_builder import (
    auto_assign_unassigned_major_clusters,
    build_observed_major_tree,
    collect_major_name_counts,
    suggest_unassigned_major_clusters,
)
from gaokaollm_bench.data_gen.major_embedding import (
    suggest_major_cluster_by_embedding,
    suggest_major_clusters_by_embedding,
)
from gaokaollm_bench.data_gen.major_clusters import (
    get_major_cluster_patterns,
    get_relaxation_path,
    load_major_clusters,
)
from gaokaollm_bench.data_gen.major_tree import (
    UnknownMajorError,
    build_relaxation_stages,
    collect_observed_major_names,
    get_major_cluster_patterns_from_tree,
    resolve_major_node,
)
from gaokaollm_bench.schemas import IcebergPersona


def test_build_deterministic_persona_uses_verified_gap_data():
    gap = {
        "score": 600,
        "province": "浙江",
        "constraint_relaxed": "province",
        "tier_delta": 1,
        "tier_a": {
            "school_id": 1,
            "school_name": "浙江普通学院",
            "school_province": "浙江",
            "is_985": False,
            "is_211": False,
            "is_double_first_class": False,
            "education_level": "本科",
            "major_name": "计算机类",
            "min_score": 596,
            "tier": 2,
        },
        "tier_b": {
            "school_id": 2,
            "school_name": "外省211大学",
            "school_province": "江苏",
            "is_985": False,
            "is_211": True,
            "is_double_first_class": True,
            "education_level": "本科",
            "major_name": "计算机类",
            "min_score": 598,
            "tier": 3,
        },
    }

    persona = build_deterministic_persona(gap, 1)
    restored = IcebergPersona.model_validate_json(persona.model_dump_json())

    assert restored.background["score"] == 600
    assert restored.explicit_red_lines["geo"] == "坚决不出浙江"
    assert restored.implicit_flexibilities["trigger_school"] == "外省211大学"
    assert restored.implicit_flexibilities["verified_min_score"] == 598
    assert "外省211大学" in restored.initial_utterance or "外省211大学" in json.dumps(
        restored.model_dump(), ensure_ascii=False
    )


def test_build_deterministic_persona_from_gap_set_uses_volunteer_set():
    gap_set = {
        "score": 600,
        "province": "浙江",
        "constraint_relaxed": "province",
        "volunteer_count": 2,
        "max_tier_delta": 1,
        "tier_a": {
            "school_id": 1,
            "school_name": "浙江普通学院",
            "school_province": "浙江",
            "is_985": False,
            "is_211": False,
            "is_double_first_class": False,
            "education_level": "本科",
            "major_name": "计算机类",
            "min_score": 596,
            "tier": 2,
        },
        "volunteer_set": [
            {
                "year": 2025,
                "school_id": 2,
                "school_name": "外省211大学",
                "school_province": "江苏",
                "school_city": "南京",
                "is_985": False,
                "is_211": True,
                "is_double_first_class": True,
                "education_level": "本科",
                "major_id": 20,
                "major_name": "计算机类",
                "min_score": 598,
                "min_rank": 50000,
                "tier": 3,
            },
            {
                "year": 2025,
                "school_id": 3,
                "school_name": "另一所双一流大学",
                "school_province": "安徽",
                "school_city": "合肥",
                "is_985": False,
                "is_211": False,
                "is_double_first_class": True,
                "education_level": "本科",
                "major_id": 30,
                "major_name": "软件工程",
                "min_score": 592,
                "min_rank": 53000,
                "tier": 3,
            },
        ],
    }

    persona = build_deterministic_persona_from_gap_set(gap_set, 1)
    restored = IcebergPersona.model_validate_json(persona.model_dump_json())
    volunteer_set = restored.implicit_flexibilities["volunteer_set"]

    assert restored.implicit_flexibilities["trigger_type"] == "volunteer_set"
    assert len(volunteer_set) == 2
    assert volunteer_set[0]["school_name"] == "外省211大学"
    assert volunteer_set[1]["score_margin"] == 8
    assert restored.process_milestones["require_complete_volunteer_set"] is True


def test_build_deterministic_persona_from_major_relax_gap_set():
    gap_set = {
        "score": 620,
        "province": "浙江",
        "constraint_relaxed": "major",
        "relaxation_kind": "clinical_to_medtech",
        "relax_scope": "national",
        "strict_major": "临床医学",
        "volunteer_count": 2,
        "max_tier_delta": 1,
        "tier_a": {
            "school_id": 1,
            "school_name": "浙江医学学院",
            "school_province": "浙江",
            "is_985": False,
            "is_211": False,
            "is_double_first_class": False,
            "education_level": "本科",
            "major_name": "临床医学",
            "min_score": 618,
            "tier": 2,
        },
        "volunteer_set": [
            {
                "year": 2025,
                "school_id": 2,
                "school_name": "浙江高层次大学",
                "school_province": "浙江",
                "school_city": "杭州",
                "is_985": False,
                "is_211": True,
                "is_double_first_class": True,
                "education_level": "本科",
                "major_id": 20,
                "major_name": "医学检验技术",
                "min_score": 612,
                "min_rank": 40000,
                "tier": 3,
            },
            {
                "year": 2025,
                "school_id": 3,
                "school_name": "浙江另一所大学",
                "school_province": "浙江",
                "school_city": "宁波",
                "is_985": False,
                "is_211": False,
                "is_double_first_class": True,
                "education_level": "本科",
                "major_id": 30,
                "major_name": "医学影像技术",
                "min_score": 615,
                "min_rank": 39000,
                "tier": 3,
            },
        ],
    }

    persona = build_deterministic_persona_from_gap_set(gap_set, 2)
    restored = IcebergPersona.model_validate_json(persona.model_dump_json())
    volunteer_set = restored.implicit_flexibilities["volunteer_set"]

    assert restored.background["constraint_relaxed"] == "major"
    assert restored.implicit_flexibilities["relaxation_kind"] == "clinical_to_medtech"
    assert restored.implicit_flexibilities["relax_scope"] == "national"
    assert restored.explicit_red_lines["major"] == "坚决只读临床医学"
    assert len(volunteer_set) == 2
    assert {item["major_name"] for item in volunteer_set} == {
        "医学检验技术",
        "医学影像技术",
    }
    assert restored.process_milestones["reject_generic_major_switch"] is True


def test_build_deterministic_persona_from_city_relax_gap_set():
    gap_set = {
        "score": 600,
        "province": "Zhejiang",
        "city": "Hangzhou",
        "constraint_relaxed": "city",
        "relaxation_kind": "city_to_other_city",
        "strict_major": "Clinical Medicine",
        "volunteer_count": 2,
        "max_tier_delta": 1,
        "tier_a": {
            "school_id": 1,
            "school_name": "Hangzhou Medical College",
            "school_province": "Zhejiang",
            "school_city": "Hangzhou",
            "is_985": False,
            "is_211": False,
            "is_double_first_class": False,
            "education_level": "本科",
            "major_name": "Clinical Medicine",
            "min_score": 596,
            "tier": 2,
        },
        "volunteer_set": [
            {
                "year": 2025,
                "school_id": 2,
                "school_name": "Ningbo University",
                "school_province": "Zhejiang",
                "school_city": "Ningbo",
                "is_985": False,
                "is_211": True,
                "is_double_first_class": True,
                "education_level": "本科",
                "major_id": 20,
                "major_name": "Clinical Medicine",
                "min_score": 592,
                "min_rank": 41000,
                "tier": 3,
            },
            {
                "year": 2025,
                "school_id": 3,
                "school_name": "Wenzhou Medical University",
                "school_province": "Zhejiang",
                "school_city": "Wenzhou",
                "is_985": False,
                "is_211": False,
                "is_double_first_class": True,
                "education_level": "本科",
                "major_id": 30,
                "major_name": "Clinical Medicine",
                "min_score": 590,
                "min_rank": 43000,
                "tier": 3,
            },
        ],
    }

    persona = build_deterministic_persona_from_gap_set(gap_set, 4)
    restored = IcebergPersona.model_validate_json(persona.model_dump_json())
    volunteer_set = restored.implicit_flexibilities["volunteer_set"]

    assert restored.background["constraint_relaxed"] == "city"
    assert restored.background["city"] == "Hangzhou"
    assert restored.background["preferred_major"] == "Clinical Medicine"
    assert restored.explicit_red_lines["city"] == "坚决只看Hangzhou"
    assert restored.implicit_flexibilities["constraint_relaxed"] == "city"
    assert {item["school_city"] for item in volunteer_set} == {"Ningbo", "Wenzhou"}
    assert (
        restored.process_milestones["require_each_option_city_and_score_evidence"]
        is True
    )


def test_build_deterministic_persona_from_risk_band_gap_set():
    gap_set = {
        "score": 600,
        "province": "娴欐睙",
        "constraint_relaxed": "risk_band",
        "relaxation_kind": "risk_band_portfolio",
        "strict_major": "涓村簥鍖诲",
        "baseline_risk_preference": "conservative",
        "student_rank": 50000,
        "volunteer_count": 3,
        "risk_levels": ["chong", "wen", "bao"],
        "portfolio_gain": 3,
        "max_tier_delta": 0,
        "tier_a": {
            "school_id": 1,
            "school_name": "保守锚点大学",
            "school_province": "娴欐睙",
            "school_city": "杭州",
            "is_985": False,
            "is_211": False,
            "is_double_first_class": False,
            "education_level": "鏈",
            "major_name": "涓村簥鍖诲",
            "min_score": 570,
            "min_rank": 75000,
            "tier": 2,
            "risk_level": "bao",
        },
        "volunteer_set": [
            {
                "year": 2025,
                "school_id": 2,
                "school_name": "风险组合大学",
                "school_province": "娴欐睙",
                "school_city": "杭州",
                "is_985": False,
                "is_211": False,
                "is_double_first_class": False,
                "education_level": "鏈",
                "major_id": 20,
                "major_name": "涓村簥鍖诲",
                "min_score": 596,
                "min_rank": 52000,
                "tier": 2,
                "risk_level": "chong",
                "score_margin": 4,
                "rank_gap": 2000,
                "student_rank": 50000,
            },
            {
                "year": 2025,
                "school_id": 3,
                "school_name": "稳妥大学",
                "school_province": "娴欐睙",
                "school_city": "宁波",
                "is_985": False,
                "is_211": False,
                "is_double_first_class": False,
                "education_level": "鏈",
                "major_id": 30,
                "major_name": "涓村簥鍖诲",
                "min_score": 588,
                "min_rank": 60000,
                "tier": 2,
                "risk_level": "wen",
                "score_margin": 12,
                "rank_gap": 10000,
                "student_rank": 50000,
            },
            {
                "year": 2025,
                "school_id": 4,
                "school_name": "保底大学",
                "school_province": "娴欐睙",
                "school_city": "温州",
                "is_985": False,
                "is_211": False,
                "is_double_first_class": False,
                "education_level": "鏈",
                "major_id": 40,
                "major_name": "涓村簥鍖诲",
                "min_score": 570,
                "min_rank": 75000,
                "tier": 2,
                "risk_level": "bao",
                "score_margin": 30,
                "rank_gap": 25000,
                "student_rank": 50000,
            },
        ],
    }

    persona = build_deterministic_persona_from_gap_set(gap_set, 3)
    restored = IcebergPersona.model_validate_json(persona.model_dump_json())
    volunteer_set = restored.implicit_flexibilities["volunteer_set"]

    assert restored.background["constraint_relaxed"] == "risk_band"
    assert restored.background["portfolio_gain"] == 3
    assert restored.implicit_flexibilities["constraint_relaxed"] == "risk_band"
    assert restored.implicit_flexibilities["risk_levels"] == ["chong", "wen", "bao"]
    assert {item["risk_level"] for item in volunteer_set} == {"chong", "wen", "bao"}
    assert restored.process_milestones["require_risk_band_evidence"] is True


@pytest.mark.asyncio
async def test_find_risk_band_gap_sets_builds_chong_wen_bao_portfolio():
    calls = []

    async def mock_db(query, *params):
        calls.append((query, params))
        if "score_rank_segments" in query:
            return [{"rank_min": 50000, "rank_max": 50100}]
        return [
            {
                "year": 2025,
                "school_id": 1,
                "school_name": "风险组合大学",
                "school_province": "娴欐睙",
                "school_city": "杭州",
                "is_985": False,
                "is_211": False,
                "is_double_first_class": False,
                "education_level": "鏈",
                "ranking": 50,
                "major_id": 10,
                "major_name": "涓村簥鍖诲",
                "min_score": 598,
                "min_rank": 52000,
                "tier": 2,
            },
            {
                "year": 2025,
                "school_id": 2,
                "school_name": "稳妥大学",
                "school_province": "娴欐睙",
                "school_city": "宁波",
                "is_985": False,
                "is_211": False,
                "is_double_first_class": False,
                "education_level": "鏈",
                "ranking": 90,
                "major_id": 20,
                "major_name": "涓村簥鍖诲",
                "min_score": 588,
                "min_rank": 60000,
                "tier": 2,
            },
            {
                "year": 2025,
                "school_id": 3,
                "school_name": "保底大学",
                "school_province": "娴欐睙",
                "school_city": "温州",
                "is_985": False,
                "is_211": False,
                "is_double_first_class": False,
                "education_level": "鏈",
                "ranking": 140,
                "major_id": 30,
                "major_name": "涓村簥鍖诲",
                "min_score": 570,
                "min_rank": 75000,
                "tier": 2,
            },
        ]

    gap_sets = await find_risk_band_gap_sets(
        mock_db,
        count=1,
        prov="娴欐睙",
        strict_major="涓村簥鍖诲",
        score_min=600,
        score_max=600,
        strict_target_quality=False,
    )

    assert len(gap_sets) == 1
    assert gap_sets[0]["constraint_relaxed"] == "risk_band"
    assert gap_sets[0]["portfolio_gain"] == 3
    assert [row["risk_level"] for row in gap_sets[0]["volunteer_set"]] == [
        "chong",
        "wen",
        "bao",
    ]
    assert "s.province = %s" in calls[-1][0]
    assert "a.major_name_raw LIKE %s" in calls[-1][0]


@pytest.mark.asyncio
async def test_find_city_relax_gap_sets_keep_province_major_and_drop_city():
    calls = []

    async def mock_db(query, *params):
        calls.append((query, params))
        if "s.city = %s" in query:
            return [
                {
                    "year": 2025,
                    "school_id": 1,
                    "school_name": "Hangzhou Medical College",
                    "school_province": "Zhejiang",
                    "school_city": "Hangzhou",
                    "is_985": False,
                    "is_211": False,
                    "is_double_first_class": False,
                    "education_level": "本科",
                    "ranking": 200,
                    "major_id": 10,
                    "major_name": "Clinical Medicine",
                    "min_score": 596,
                    "min_rank": 46000,
                    "tier": 2,
                }
            ]
        if "s.city <> %s" in query:
            return [
                {
                    "year": 2025,
                    "school_id": 2,
                    "school_name": "Ningbo University",
                    "school_province": "Zhejiang",
                    "school_city": "Ningbo",
                    "is_985": False,
                    "is_211": True,
                    "is_double_first_class": True,
                    "education_level": "本科",
                    "ranking": 90,
                    "major_id": 20,
                    "major_name": "Clinical Medicine",
                    "min_score": 592,
                    "min_rank": 41000,
                    "tier": 3,
                },
                {
                    "year": 2025,
                    "school_id": 3,
                    "school_name": "Wenzhou Medical University",
                    "school_province": "Zhejiang",
                    "school_city": "Wenzhou",
                    "is_985": False,
                    "is_211": False,
                    "is_double_first_class": True,
                    "education_level": "本科",
                    "ranking": 100,
                    "major_id": 30,
                    "major_name": "Clinical Medicine",
                    "min_score": 590,
                    "min_rank": 43000,
                    "tier": 3,
                },
            ]
        return []

    gap_sets = await find_city_relax_gap_sets(
        mock_db,
        count=1,
        prov="Zhejiang",
        city="Hangzhou",
        strict_major="Clinical Medicine",
        score_min=600,
        score_max=600,
        candidates_per_score=2,
        max_volunteers_per_case=2,
        strict_target_quality=False,
    )

    assert len(gap_sets) == 1
    assert gap_sets[0]["constraint_relaxed"] == "city"
    assert gap_sets[0]["city"] == "Hangzhou"
    assert gap_sets[0]["strict_major"] == "Clinical Medicine"
    assert [row["school_city"] for row in gap_sets[0]["volunteer_set"]] == [
        "Ningbo",
        "Wenzhou",
    ]

    baseline_query, baseline_params = calls[0]
    relaxed_query, relaxed_params = calls[1]
    assert "s.city = %s" in baseline_query
    assert "s.province = %s" in relaxed_query
    assert "s.city <> %s" in relaxed_query
    assert "a.major_name_raw LIKE %s" in relaxed_query
    assert baseline_params == (600, "Zhejiang", "Hangzhou", "%Clinical Medicine%", 1)
    assert "Hangzhou" in relaxed_params
    assert "%Clinical Medicine%" in relaxed_params


def test_medical_major_cluster_patterns_are_auditable():
    clusters = load_major_clusters()
    include_patterns, exclude_patterns = get_major_cluster_patterns(
        ["medical_technology"]
    )

    assert "medical_technology" in clusters["nodes"]
    assert "%医学检验技术%" in include_patterns
    assert "%医学影像技术%" in include_patterns
    assert "%临床医学%" in exclude_patterns


def test_medical_relaxation_path_is_staged():
    path = get_relaxation_path("medical_clinical")

    assert [stage["stage"] for stage in path] == [1, 2, 3, 4]
    assert path[0]["cluster_ids"] == ["medical_clinical"]
    assert "medical_stomatology" in path[1]["cluster_ids"]
    assert "medical_pharmacy" in path[2]["cluster_ids"]
    assert path[3]["cluster_ids"] == ["medical_all"]


def test_major_tree_resolves_arbitrary_starting_majors():
    assert resolve_major_node("临床医学(5+3一体化)").id == "medical_clinical"
    assert resolve_major_node("口腔医学").id == "medical_stomatology"
    assert resolve_major_node("医学检验技术").id == "medical_technology"
    assert resolve_major_node("药学").id == "medical_pharmacy"
    assert resolve_major_node("计算机科学与技术").id == "computer_science"
    assert resolve_major_node("大数据与会计").id == "finance_accounting"
    assert resolve_major_node("法学").id == "law_politics"
    assert resolve_major_node("计算机应用技术").id == "vocational_computer_network"
    assert resolve_major_node("工程造价").id == "vocational_cost_construction"
    assert resolve_major_node("机电一体化技术").id == "vocational_mechatronics"
    assert resolve_major_node("空中乘务").id == "vocational_air_transport"


def test_unknown_major_error_contains_suggestions():
    with pytest.raises(UnknownMajorError) as exc_info:
        resolve_major_node("火星殖民工程")

    assert isinstance(exc_info.value.suggestions, list)


def test_collect_observed_major_names_assigns_db_names_to_leaf_nodes():
    assignments = collect_observed_major_names(
        ["临床医学(仓前校区)", "医学检验技术(临安校区)", "药学类"]
    )

    assert "临床医学(仓前校区)" in assignments["medical_clinical"]
    assert "医学检验技术(临安校区)" in assignments["medical_technology"]
    assert "药学类" in assignments["medical_pharmacy"]


def test_build_relaxation_stages_from_major_name():
    stages = build_relaxation_stages("口腔医学")

    assert stages[0]["source_cluster"] == "medical_stomatology"
    assert stages[0]["cluster_ids"] == ["medical_stomatology"]
    assert "medical_clinical" in stages[1]["cluster_ids"]


def test_build_relaxation_stages_adds_probe_neighbor_categories_and_any_major():
    stages = build_relaxation_stages(
        "口腔医学",
        neighbor_node_ids=[
            "medical_stomatology",
            "medical_clinical",
            "computer_science",
            "law_politics",
            "finance_accounting",
            "electronic_information",
        ],
        neighbor_limit=3,
        skip_ancestor_category=True,
        include_any_major_stage=True,
    )

    assert [stage["stage"] for stage in stages] == [1, 2, 3, 4, 5]
    assert stages[-2]["strategy"] == "probe_neighbor_categories"
    assert stages[-2]["category_ids"] == [
        "computer_core",
        "law_public_group",
        "econ_finance_group",
    ]
    assert "computer_science" in stages[-2]["cluster_ids"]
    assert "law_politics" in stages[-2]["cluster_ids"]
    assert "finance_accounting" in stages[-2]["cluster_ids"]
    assert stages[-1]["strategy"] == "any_major"
    assert stages[-1]["relaxation_kind"] == "any_major"
    assert stages[-1]["include_patterns"] == []


def test_filtered_cluster_patterns_drop_polluted_observed_names():
    tree = {
        "nodes": {
            "root": {
                "id": "root",
                "label": "root",
                "parent": None,
                "level": 0,
                "include_keywords": [],
                "exclude_keywords": [],
                "observed_names": [],
            },
            "medical_stomatology": {
                "id": "medical_stomatology",
                "label": "口腔医学类",
                "parent": "root",
                "level": 1,
                "include_keywords": ["口腔医学"],
                "exclude_keywords": [],
                "observed_names": ["医学技术类", "口腔医学"],
            },
        }
    }
    include_patterns, _ = get_major_cluster_patterns_from_tree(
        tree,
        ["medical_stomatology"],
        filter_observed=True,
        max_observed_name_length=60,
        exclude_special_observed=True,
    )

    assert "%口腔医学%" in include_patterns
    assert "%医学技术类%" not in include_patterns


@pytest.mark.asyncio
async def test_collect_major_name_counts_reads_distinct_db_names():
    captured = {}

    async def mock_db(query, *params):
        captured["query"] = query
        captured["params"] = params
        return [
            {"major_name": "计算机科学与技术", "row_count": 12},
            {"major_name": "临床医学", "row_count": 8},
        ]

    rows = await collect_major_name_counts(mock_db, min_count=2, limit=20)

    assert "admission_scores" in captured["query"]
    assert captured["params"] == (2, 20)
    assert rows[0]["major_name"] == "计算机科学与技术"


def test_build_observed_major_tree_populates_multiple_domains_and_audit_rows():
    observed_tree, unassigned = build_observed_major_tree(
        [
            {"major_name": "临床医学(5+3一体化)", "row_count": 9},
            {"major_name": "计算机科学与技术", "row_count": 12},
            {"major_name": "大数据与会计", "row_count": 10},
            {"major_name": "工程造价", "row_count": 1032},
            {"major_name": "计算机应用技术", "row_count": 837},
            {"major_name": "未知星际工程", "row_count": 99},
        ],
        top_unassigned=5,
    )

    nodes = observed_tree["nodes"]
    build = observed_tree["observed_build"]

    assert "临床医学(5+3一体化)" in nodes["medical_clinical"]["observed_names"]
    assert "计算机科学与技术" in nodes["computer_science"]["observed_names"]
    assert "大数据与会计" in nodes["finance_accounting"]["observed_names"]
    assert "工程造价" in nodes["vocational_cost_construction"]["observed_names"]
    assert "计算机应用技术" in nodes["vocational_computer_network"]["observed_names"]
    assert "工程造价" in nodes["vocational_all"]["observed_names"]
    assert "计算机科学与技术" in nodes["computer_all"]["observed_names"]
    assert unassigned[0]["major_name"] == "未知星际工程"
    assert build["unassigned_distinct_names"] == 1


@pytest.mark.asyncio
async def test_embedding_suggestion_can_propose_new_sibling_leaf_for_unknown_major():
    class MockEmbeddingClient:
        async def embed(self, texts):
            vectors = []
            for text in texts:
                if text == "生物工程":
                    vectors.append([1.0, 0.0, 0.0])
                elif "生物地理生态" in text:
                    vectors.append([0.74, 0.6726, 0.0])
                else:
                    vectors.append([0.0, 1.0, 0.0])
            return vectors

    suggestion = await suggest_major_cluster_by_embedding(
        "生物工程",
        MockEmbeddingClient(),
        attach_threshold=0.9,
        new_sibling_threshold=0.7,
    )

    assert suggestion.action == "suggest_new_sibling_leaf"
    assert suggestion.target_node_id == "bio_geo_ecology"
    assert suggestion.parent_node_id == "basic_science_group"


@pytest.mark.asyncio
async def test_unassigned_report_can_include_embedding_suggestions():
    class MockEmbeddingClient:
        async def embed(self, texts):
            vectors = []
            for text in texts:
                if text == "生物工程":
                    vectors.append([1.0, 0.0, 0.0])
                elif "生物地理生态" in text:
                    vectors.append([0.74, 0.6726, 0.0])
                else:
                    vectors.append([0.0, 1.0, 0.0])
            return vectors

    observed_tree, unassigned = build_observed_major_tree(
        [{"major_name": "生物工程", "row_count": 324}],
        top_unassigned=5,
    )
    suggested = await suggest_unassigned_major_clusters(
        unassigned,
        MockEmbeddingClient(),
        tree=observed_tree,
        attach_threshold=0.9,
        new_sibling_threshold=0.7,
    )

    assert suggested[0]["major_name"] == "生物工程"
    assert suggested[0]["embedding_suggestion"]["action"] == "suggest_new_sibling_leaf"
    assert (
        suggested[0]["embedding_suggestion"]["parent_node_id"] == "basic_science_group"
    )


@pytest.mark.asyncio
async def test_batch_embedding_suggestions_embed_leaf_profiles_once():
    class CountingEmbeddingClient:
        def __init__(self):
            self.calls = []

        async def embed(self, texts):
            self.calls.append(list(texts))
            vectors = []
            for text in texts:
                if text in {"生物工程", "生物制药"}:
                    vectors.append([1.0, 0.0, 0.0])
                elif "生物地理生态" in text:
                    vectors.append([0.74, 0.6726, 0.0])
                else:
                    vectors.append([0.0, 1.0, 0.0])
            return vectors

    client = CountingEmbeddingClient()
    suggestions = await suggest_major_clusters_by_embedding(
        ["生物工程", "生物制药"],
        client,
        attach_threshold=0.9,
        new_sibling_threshold=0.7,
    )

    assert len(client.calls) == 1
    assert client.calls[0][:2] == ["生物工程", "生物制药"]
    assert [suggestion.action for suggestion in suggestions] == [
        "suggest_new_sibling_leaf",
        "suggest_new_sibling_leaf",
    ]


@pytest.mark.asyncio
async def test_auto_assign_unassigned_major_clusters_updates_tree_and_audit():
    class MockEmbeddingClient:
        async def embed(self, texts):
            vectors = []
            for text in texts:
                if text == "生物工程":
                    vectors.append([1.0, 0.0, 0.0])
                elif "生物地理生态" in text:
                    vectors.append([0.74, 0.6726, 0.0])
                else:
                    vectors.append([0.0, 1.0, 0.0])
            return vectors

    observed_tree, unassigned = build_observed_major_tree(
        [{"major_name": "生物工程", "row_count": 324}],
        top_unassigned=5,
    )
    audit = await auto_assign_unassigned_major_clusters(
        observed_tree,
        unassigned,
        MockEmbeddingClient(),
        attach_threshold=0.9,
        new_sibling_threshold=0.7,
        major_batch_size=1,
    )

    assert audit[0]["embedding_auto_assignment"]["target_node_id"] == "bio_geo_ecology"
    assert "生物工程" in observed_tree["nodes"]["bio_geo_ecology"]["observed_names"]
    assert "生物工程" in observed_tree["nodes"]["science_agri_all"]["observed_names"]
    assert observed_tree["observed_build"]["unassigned_distinct_names"] == 0
    assert (
        observed_tree["observed_build"]["embedding_auto_assign"]["assigned_row_count"]
        == 324
    )


def test_build_deterministic_persona_from_hierarchical_major_relax_gap_set():
    gap_set = {
        "score": 620,
        "province": "浙江",
        "constraint_relaxed": "major",
        "relaxation_kind": "hierarchical_major",
        "relax_scope": "national",
        "strict_major": "临床医学",
        "source_major_cluster": "medical_clinical",
        "relaxation_stage": 2,
        "relaxation_stage_label": "医学相关非临床",
        "target_major_clusters": ["medical_technology", "medical_pharmacy"],
        "psychological_distance": "medium",
        "volunteer_count": 1,
        "max_tier_delta": 1,
        "tier_a": {
            "school_id": 1,
            "school_name": "浙江医学学院",
            "school_province": "浙江",
            "is_985": False,
            "is_211": False,
            "is_double_first_class": False,
            "education_level": "本科",
            "major_name": "临床医学",
            "min_score": 618,
            "tier": 2,
        },
        "volunteer_set": [
            {
                "year": 2025,
                "school_id": 2,
                "school_name": "外省医科大学",
                "school_province": "天津",
                "school_city": "天津",
                "is_985": False,
                "is_211": True,
                "is_double_first_class": True,
                "education_level": "本科",
                "major_id": 20,
                "major_name": "药学类",
                "min_score": 612,
                "min_rank": 40000,
                "tier": 3,
            }
        ],
    }

    persona = build_deterministic_persona_from_gap_set(gap_set, 3)
    restored = IcebergPersona.model_validate_json(persona.model_dump_json())

    assert restored.background["relaxation_kind"] == "hierarchical_major"
    assert restored.background["preferred_major"] == "临床医学"
    assert restored.implicit_flexibilities["accepted_major_examples"] == ["药学类"]
    assert restored.implicit_flexibilities["relaxation_stage"] == 2
    assert restored.implicit_flexibilities["target_major_clusters"] == [
        "medical_technology",
        "medical_pharmacy",
    ]
    assert restored.process_milestones["require_cluster_level_relaxation"] is True


@pytest.mark.asyncio
async def test_hierarchical_major_relax_uses_recommendation_threshold():
    async def mock_db(query, *params):
        if "a.major_name_raw LIKE" in query and params[-1] == 1:
            return [
                {
                    "year": 2025,
                    "school_id": 1,
                    "school_name": "浙江医学学院",
                    "school_province": "浙江",
                    "school_city": "杭州",
                    "is_985": False,
                    "is_211": False,
                    "is_double_first_class": False,
                    "education_level": "本科",
                    "major_id": 10,
                    "major_name": "临床医学",
                    "min_score": 600,
                    "min_rank": 50000,
                    "tier": 2,
                }
            ]

        stage_marker = params[2]
        if stage_marker == "%stage1%":
            rows = [
                {
                    "year": 2025,
                    "school_id": 2,
                    "school_name": "一阶段大学",
                    "school_province": "天津",
                    "school_city": "天津",
                    "is_985": False,
                    "is_211": True,
                    "is_double_first_class": True,
                    "education_level": "本科",
                    "major_id": 20,
                    "major_name": "医学检验技术",
                    "min_score": 590,
                    "min_rank": 45000,
                    "tier": 3,
                }
            ]
        else:
            rows = []
            for idx in range(3):
                rows.append(
                    {
                        "year": 2025,
                        "school_id": 30 + idx,
                        "school_name": f"二阶段大学{idx}",
                        "school_province": "江苏",
                        "school_city": "南京",
                        "is_985": False,
                        "is_211": True,
                        "is_double_first_class": True,
                        "education_level": "本科",
                        "major_id": 40 + idx,
                        "major_name": "药学类",
                        "min_score": 588 + idx,
                        "min_rank": 44000 + idx,
                        "tier": 3,
                    }
                )
        return rows

    gap_sets = await find_hierarchical_major_relax_gap_sets(
        mock_db,
        count=1,
        prov="浙江",
        strict_major="临床医学",
        relaxation_stages=[
            {
                "stage": 1,
                "label": "第一阶段",
                "cluster_ids": ["stage1"],
                "include_patterns": ["%stage1%"],
                "exclude_patterns": [],
            },
            {
                "stage": 2,
                "label": "第二阶段",
                "cluster_ids": ["stage2"],
                "include_patterns": ["%stage2%"],
                "exclude_patterns": [],
            },
        ],
        score_min=600,
        score_max=600,
        recommendation_threshold=3,
        strict_target_quality=False,
        relax_scope="national",
    )

    assert len(gap_sets) == 1
    assert gap_sets[0]["relaxation_stage"] == 2
    assert gap_sets[0]["volunteer_count"] == 3


@pytest.mark.asyncio
async def test_hierarchical_major_relax_can_fall_back_to_any_major():
    async def mock_db(query, *params):
        if "a.major_name_raw LIKE" in query and params[-1] == 1:
            return [
                {
                    "year": 2025,
                    "school_id": 1,
                    "school_name": "浙江医学学院",
                    "school_province": "浙江",
                    "school_city": "杭州",
                    "is_985": False,
                    "is_211": False,
                    "is_double_first_class": False,
                    "education_level": "本科",
                    "major_id": 10,
                    "major_name": "临床医学",
                    "min_score": 600,
                    "min_rank": 50000,
                    "tier": 2,
                }
            ]

        if "a.major_name_raw NOT LIKE" not in query:
            return []

        return [
            {
                "year": 2025,
                "school_id": 20 + idx,
                "school_name": f"无专业限制大学{idx}",
                "school_province": "江苏",
                "school_city": "南京",
                "is_985": False,
                "is_211": True,
                "is_double_first_class": True,
                "education_level": "本科",
                "major_id": 30 + idx,
                "major_name": "计算机科学与技术",
                "min_score": 590 + idx,
                "min_rank": 45000 + idx,
                "tier": 3,
            }
            for idx in range(2)
        ]

    gap_sets = await find_hierarchical_major_relax_gap_sets(
        mock_db,
        count=1,
        prov="浙江",
        strict_major="临床医学",
        relaxation_stages=[
            {
                "stage": 4,
                "label": "probe_neighbor_categories",
                "strategy": "probe_neighbor_categories",
                "cluster_ids": ["nohit"],
                "include_patterns": ["%nohit%"],
                "exclude_patterns": [],
            },
            {
                "stage": 5,
                "label": "any_major",
                "strategy": "any_major",
                "cluster_ids": [],
                "include_patterns": [],
                "exclude_patterns": [],
                "relaxation_kind": "any_major",
            },
        ],
        score_min=600,
        score_max=600,
        recommendation_threshold=2,
        strict_target_quality=False,
        relax_scope="national",
    )

    assert len(gap_sets) == 1
    assert gap_sets[0]["relaxation_stage"] == 5
    assert gap_sets[0]["stage_relaxation_kind"] == "any_major"
    assert gap_sets[0]["volunteer_count"] == 2


@pytest.mark.asyncio
async def test_hierarchical_major_relax_audits_below_threshold_before_stage5():
    async def mock_db(query, *params):
        if "a.major_name_raw LIKE" in query and params[-1] == 1:
            return [
                {
                    "year": 2025,
                    "school_id": 1,
                    "school_name": "浙江医学学院",
                    "school_province": "浙江",
                    "school_city": "杭州",
                    "is_985": False,
                    "is_211": False,
                    "is_double_first_class": False,
                    "education_level": "本科",
                    "major_id": 10,
                    "major_name": "临床医学",
                    "min_score": 600,
                    "min_rank": 50000,
                    "tier": 2,
                }
            ]

        if "a.major_name_raw NOT LIKE" in query:
            return [
                {
                    "year": 2025,
                    "school_id": 100 + idx // 2,
                    "school_name": f"兜底大学{idx // 2}",
                    "school_province": "浙江",
                    "school_city": "杭州",
                    "is_985": False,
                    "is_211": True,
                    "is_double_first_class": True,
                    "education_level": "本科",
                    "major_id": 200 + idx,
                    "major_name": f"普通专业{idx}",
                    "min_score": 590 + idx,
                    "min_rank": 40000 + idx,
                    "tier": 3,
                }
                for idx in range(10)
            ]

        return [
            {
                "year": 2025,
                "school_id": 20 + idx,
                "school_name": f"三阶段大学{idx}",
                "school_province": "浙江",
                "school_city": "杭州",
                "is_985": False,
                "is_211": True,
                "is_double_first_class": True,
                "education_level": "本科",
                "major_id": 30 + idx,
                "major_name": "预防医学",
                "min_score": 590 + idx,
                "min_rank": 45000 + idx,
                "tier": 3,
            }
            for idx in range(2)
        ]

    gap_sets = await find_hierarchical_major_relax_gap_sets(
        mock_db,
        count=1,
        prov="浙江",
        strict_major="临床医学",
        relaxation_stages=[
            {
                "stage": 3,
                "label": "三阶段",
                "strategy": "cousin_leaf_clusters",
                "cluster_ids": ["stage3"],
                "include_patterns": ["%stage3%"],
                "exclude_patterns": [],
            },
            {
                "stage": 5,
                "label": "去除专业限制",
                "strategy": "any_major",
                "cluster_ids": [],
                "include_patterns": [],
                "exclude_patterns": [],
                "relaxation_kind": "any_major",
            },
        ],
        score_min=600,
        score_max=600,
        recommendation_threshold=10,
        max_volunteers_per_school=2,
        include_special_majors=False,
        strict_target_quality=False,
        relax_scope="national",
    )

    assert len(gap_sets) == 1
    assert gap_sets[0]["relaxation_stage"] == 5
    attempts = gap_sets[0]["stage_attempts"]
    assert attempts[0]["stage"] == 3
    assert attempts[0]["raw_candidate_count"] == 2
    assert attempts[0]["filtered_volunteer_count"] == 2
    assert attempts[0]["failure_reason"] == "below_threshold"
    assert attempts[1]["stage"] == 5
    assert attempts[1]["accepted"] is True


@pytest.mark.asyncio
async def test_hierarchical_major_relax_limits_volunteers_per_school():
    async def mock_db(query, *params):
        if "a.major_name_raw LIKE" in query and params[-1] == 1:
            return [
                {
                    "year": 2025,
                    "school_id": 1,
                    "school_name": "浙江医学学院",
                    "school_province": "浙江",
                    "school_city": "杭州",
                    "is_985": False,
                    "is_211": False,
                    "is_double_first_class": False,
                    "education_level": "本科",
                    "major_id": 10,
                    "major_name": "临床医学",
                    "min_score": 600,
                    "min_rank": 50000,
                    "tier": 2,
                }
            ]

        rows = []
        for idx in range(5):
            rows.append(
                {
                    "year": 2025,
                    "school_id": 2,
                    "school_name": "同校大学",
                    "school_province": "浙江",
                    "school_city": "杭州",
                    "is_985": False,
                    "is_211": True,
                    "is_double_first_class": True,
                    "education_level": "本科",
                    "major_id": 20 + idx,
                    "major_name": f"专业{idx}",
                    "min_score": 590 + idx,
                    "min_rank": 45000 + idx,
                    "tier": 3,
                }
            )
        rows.append(
            {
                "year": 2025,
                "school_id": 3,
                "school_name": "另一所大学",
                "school_province": "浙江",
                "school_city": "杭州",
                "is_985": False,
                "is_211": True,
                "is_double_first_class": True,
                "education_level": "本科",
                "major_id": 99,
                "major_name": "专业A",
                "min_score": 595,
                "min_rank": 44000,
                "tier": 3,
            }
        )
        return rows

    gap_sets = await find_hierarchical_major_relax_gap_sets(
        mock_db,
        count=1,
        prov="浙江",
        strict_major="临床医学",
        relaxation_stages=[
            {
                "stage": 3,
                "label": "三阶段",
                "strategy": "cousin_leaf_clusters",
                "cluster_ids": ["stage3"],
                "include_patterns": ["%stage3%"],
                "exclude_patterns": [],
            }
        ],
        score_min=600,
        score_max=600,
        recommendation_threshold=3,
        max_volunteers_per_school=2,
        strict_target_quality=False,
        relax_scope="national",
    )

    volunteers = gap_sets[0]["volunteer_set"]
    assert [row["school_name"] for row in volunteers].count("同校大学") == 2
    assert [row["school_name"] for row in volunteers].count("另一所大学") == 1
    assert gap_sets[0]["stage_attempts"][0]["skipped"]["school_cap"] == 3


@pytest.mark.asyncio
async def test_hierarchical_major_relax_filters_special_majors_by_default():
    async def mock_db(query, *params):
        if "a.major_name_raw LIKE" in query and params[-1] == 1:
            return [
                {
                    "year": 2025,
                    "school_id": 1,
                    "school_name": "浙江医学学院",
                    "school_province": "浙江",
                    "school_city": "杭州",
                    "is_985": False,
                    "is_211": False,
                    "is_double_first_class": False,
                    "education_level": "本科",
                    "major_id": 10,
                    "major_name": "临床医学",
                    "min_score": 600,
                    "min_rank": 50000,
                    "tier": 2,
                }
            ]
        return [
            {
                "year": 2025,
                "school_id": 2,
                "school_name": "特殊大学",
                "school_province": "浙江",
                "school_city": "杭州",
                "is_985": False,
                "is_211": True,
                "is_double_first_class": True,
                "education_level": "本科",
                "major_id": 20,
                "major_name": "工商管理(中外合作办学)",
                "min_score": 590,
                "min_rank": 45000,
                "tier": 3,
            },
            {
                "year": 2024,
                "school_id": 3,
                "school_name": "普通大学",
                "school_province": "浙江",
                "school_city": "杭州",
                "is_985": False,
                "is_211": True,
                "is_double_first_class": True,
                "education_level": "本科",
                "major_id": 21,
                "major_name": "药学类",
                "min_score": 590,
                "min_rank": 45000,
                "tier": 3,
            },
        ]

    common_kwargs = dict(
        count=1,
        prov="浙江",
        strict_major="临床医学",
        relaxation_stages=[
            {
                "stage": 3,
                "label": "三阶段",
                "strategy": "cousin_leaf_clusters",
                "cluster_ids": ["stage3"],
                "include_patterns": ["%stage3%"],
                "exclude_patterns": [],
            }
        ],
        score_min=600,
        score_max=600,
        recommendation_threshold=1,
        max_volunteers_per_school=2,
        strict_target_quality=False,
        relax_scope="national",
    )

    filtered = await find_hierarchical_major_relax_gap_sets(mock_db, **common_kwargs)
    included = await find_hierarchical_major_relax_gap_sets(
        mock_db,
        include_special_majors=True,
        **common_kwargs,
    )

    assert filtered[0]["volunteer_set"][0]["major_name"] == "药学类"
    assert filtered[0]["stage_attempts"][0]["skipped"]["special_major"] == 1
    assert included[0]["volunteer_set"][0]["major_name"] == "工商管理(中外合作办学)"
    assert included[0]["years_used"] == [2025]


@pytest.mark.asyncio
async def test_hierarchical_major_relax_prefers_latest_year_before_backfill():
    async def mock_db(query, *params):
        if "a.major_name_raw LIKE" in query and params[-1] == 1:
            return [
                {
                    "year": 2025,
                    "school_id": 1,
                    "school_name": "浙江医学学院",
                    "school_province": "浙江",
                    "school_city": "杭州",
                    "is_985": False,
                    "is_211": False,
                    "is_double_first_class": False,
                    "education_level": "本科",
                    "major_id": 10,
                    "major_name": "临床医学",
                    "min_score": 600,
                    "min_rank": 50000,
                    "tier": 2,
                }
            ]
        return [
            {
                "year": 2024,
                "school_id": 2,
                "school_name": "旧年大学",
                "school_province": "浙江",
                "school_city": "杭州",
                "is_985": False,
                "is_211": True,
                "is_double_first_class": True,
                "education_level": "本科",
                "major_id": 20,
                "major_name": "药学类",
                "min_score": 590,
                "min_rank": 45000,
                "tier": 3,
            },
            {
                "year": 2025,
                "school_id": 3,
                "school_name": "新年大学",
                "school_province": "浙江",
                "school_city": "杭州",
                "is_985": False,
                "is_211": True,
                "is_double_first_class": True,
                "education_level": "本科",
                "major_id": 21,
                "major_name": "药学类",
                "min_score": 591,
                "min_rank": 44000,
                "tier": 3,
            },
        ]

    gap_sets = await find_hierarchical_major_relax_gap_sets(
        mock_db,
        count=1,
        prov="浙江",
        strict_major="临床医学",
        relaxation_stages=[
            {
                "stage": 3,
                "label": "三阶段",
                "strategy": "cousin_leaf_clusters",
                "cluster_ids": ["stage3"],
                "include_patterns": ["%stage3%"],
                "exclude_patterns": [],
            }
        ],
        score_min=600,
        score_max=600,
        recommendation_threshold=1,
        max_volunteers_per_school=2,
        strict_target_quality=False,
        relax_scope="national",
    )

    assert gap_sets[0]["volunteer_set"][0]["school_name"] == "新年大学"
    assert gap_sets[0]["years_used"] == [2025]


@pytest.mark.asyncio
async def test_build_deterministic_persona_from_strength_relax_gap_set():
    gap_set = {
        "score": 600,
        "province": "Zhejiang",
        "constraint_relaxed": "strength",
        "relaxation_kind": "school_strength",
        "strict_major": "Clinical Medicine",
        "strength_anchor_rank": 260,
        "volunteer_count": 2,
        "max_tier_delta": 1,
        "tier_a": {
            "school_id": 1,
            "school_name": "Zhejiang Medical College",
            "school_province": "Zhejiang",
            "school_city": "Hangzhou",
            "is_985": False,
            "is_211": False,
            "is_double_first_class": False,
            "education_level": "本科",
            "major_name": "Clinical Medicine",
            "min_score": 580,
            "major_strength_rank": 260,
            "major_strength_rating": "B+",
            "major_strength_level": "discipline",
            "tier": 2,
        },
        "volunteer_set": [
            {
                "year": 2025,
                "school_id": 2,
                "school_name": "Ningbo University",
                "school_province": "Zhejiang",
                "school_city": "Ningbo",
                "is_985": False,
                "is_211": True,
                "is_double_first_class": True,
                "education_level": "本科",
                "major_id": 20,
                "major_name": "Clinical Medicine",
                "min_score": 598,
                "min_rank": 41000,
                "major_strength_rank": 80,
                "major_strength_rating": "A",
                "major_strength_level": "discipline",
                "tier": 3,
            }
        ],
    }

    persona = build_deterministic_persona_from_gap_set(gap_set, 1)
    restored = IcebergPersona.model_validate_json(persona.model_dump_json())

    assert restored.background["constraint_relaxed"] == "strength"
    assert restored.background["strength_anchor_rank"] == 260
    assert restored.explicit_red_lines["strength"] == "更看重学科实力，普通学校先不考虑"
    assert restored.implicit_flexibilities["strength_anchor_rank"] == 260
    assert (
        restored.implicit_flexibilities["volunteer_set"][0]["major_strength_rank"] == 80
    )
    assert restored.process_milestones["require_strength_evidence"] is True


@pytest.mark.asyncio
async def test_find_strength_relax_gap_sets_builds_rank_improvement_cases():
    calls = []

    async def mock_db(query, *params):
        calls.append((query, params))
        if "sms.major_strength_rank < %s" not in query:
            return [
                {
                    "year": 2025,
                    "school_id": 1,
                    "school_name": "Zhejiang Medical College",
                    "school_province": "Zhejiang",
                    "school_city": "Hangzhou",
                    "is_985": False,
                    "is_211": False,
                    "is_double_first_class": False,
                    "education_level": "本科",
                    "major_id": 10,
                    "major_name": "Clinical Medicine",
                    "min_score": 580,
                    "major_strength_rank": 260,
                    "major_strength_rating": "B+",
                    "major_strength_level": "discipline",
                    "tier": 2,
                }
            ]
        return [
            {
                "year": 2025,
                "school_id": 2,
                "school_name": "Ningbo University",
                "school_province": "Zhejiang",
                "school_city": "Ningbo",
                "is_985": False,
                "is_211": True,
                "is_double_first_class": True,
                "education_level": "本科",
                "major_id": 20,
                "major_name": "Clinical Medicine",
                "min_score": 598,
                "major_strength_rank": 80,
                "major_strength_rating": "A",
                "major_strength_level": "discipline",
                "tier": 3,
            },
            {
                "year": 2025,
                "school_id": 3,
                "school_name": "Wenzhou Medical University",
                "school_province": "Zhejiang",
                "school_city": "Wenzhou",
                "is_985": False,
                "is_211": False,
                "is_double_first_class": True,
                "education_level": "本科",
                "major_id": 30,
                "major_name": "Clinical Medicine",
                "min_score": 596,
                "major_strength_rank": 120,
                "major_strength_rating": "A-",
                "major_strength_level": "discipline",
                "tier": 3,
            },
        ]

    gap_sets = await find_strength_relax_gap_sets(
        mock_db,
        count=1,
        prov="Zhejiang",
        strict_major="Clinical Medicine",
        score_min=600,
        score_max=600,
        candidates_per_score=3,
        max_volunteers_per_case=2,
        strict_target_quality=False,
    )

    assert len(gap_sets) == 1
    assert gap_sets[0]["constraint_relaxed"] == "strength"
    assert gap_sets[0]["strength_anchor_rank"] == 260
    assert [row["major_strength_rank"] for row in gap_sets[0]["volunteer_set"]] == [
        80,
        120,
    ]
    assert "sms.major_strength_rank < %s" in calls[-1][0]


@pytest.mark.asyncio
async def test_build_deterministic_persona_from_tuition_value_gap_set():
    gap_set = {
        "score": 600,
        "province": "Zhejiang",
        "constraint_relaxed": "tuition_value",
        "relaxation_kind": "tuition_value",
        "strict_major": "Computer Science",
        "budget_anchor": 6000,
        "budget_window": 10000,
        "max_tuition_delta": 5000,
        "max_tier_delta": 1,
        "max_ranking_gain": 100,
        "tier_a": {
            "school_id": 1,
            "school_name": "Budget University",
            "school_province": "Zhejiang",
            "school_city": "Hangzhou",
            "is_985": False,
            "is_211": False,
            "is_double_first_class": False,
            "education_level": "本科",
            "major_name": "Computer Science",
            "min_score": 580,
            "min_rank": 62000,
            "tuition": 5000,
            "ranking": 180,
            "tier": 2,
        },
        "volunteer_set": [
            {
                "year": 2025,
                "school_id": 2,
                "school_name": "Value University",
                "school_province": "Zhejiang",
                "school_city": "Ningbo",
                "is_985": False,
                "is_211": True,
                "is_double_first_class": True,
                "education_level": "本科",
                "major_id": 20,
                "major_name": "Computer Science",
                "min_score": 598,
                "min_rank": 42000,
                "tuition": 9000,
                "tuition_delta": 3000,
                "ranking": 80,
                "ranking_gain": 100,
                "tuition_value_gain": 1,
                "tier": 3,
            }
        ],
    }

    persona = build_deterministic_persona_from_gap_set(gap_set, 1)
    restored = IcebergPersona.model_validate_json(persona.model_dump_json())

    assert restored.background["constraint_relaxed"] == "tuition_value"
    assert restored.background["budget_anchor"] == 6000
    assert restored.explicit_red_lines["budget"] == "每年学费最好不超过6000元"
    assert restored.implicit_flexibilities["constraint_relaxed"] == "tuition_value"
    assert restored.implicit_flexibilities["budget_window"] == 10000
    assert restored.implicit_flexibilities["volunteer_set"][0]["tuition_delta"] == 3000
    assert restored.process_milestones["require_tuition_evidence"] is True


@pytest.mark.asyncio
async def test_find_tuition_value_gap_sets_builds_budget_improvement_cases():
    calls = []

    async def mock_db(query, *params):
        calls.append((query, params))
        if "plan.min_tuition > %s" not in query:
            return [
                {
                    "year": 2025,
                    "school_id": 1,
                    "school_name": "Budget University",
                    "school_province": "Zhejiang",
                    "school_city": "Hangzhou",
                    "is_985": False,
                    "is_211": False,
                    "is_double_first_class": False,
                    "education_level": "本科",
                    "major_id": 10,
                    "major_name": "Computer Science",
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
                "school_name": "Value University A",
                "school_province": "Zhejiang",
                "school_city": "Ningbo",
                "is_985": False,
                "is_211": True,
                "is_double_first_class": True,
                "education_level": "本科",
                "major_id": 20,
                "major_name": "Computer Science",
                "min_score": 598,
                "min_rank": 42000,
                "tuition": 9000,
                "ranking": 80,
                "tier": 3,
            },
            {
                "year": 2025,
                "school_id": 3,
                "school_name": "Value University B",
                "school_province": "Zhejiang",
                "school_city": "Wenzhou",
                "is_985": False,
                "is_211": False,
                "is_double_first_class": True,
                "education_level": "本科",
                "major_id": 30,
                "major_name": "Computer Science",
                "min_score": 596,
                "min_rank": 45000,
                "tuition": 11000,
                "ranking": 120,
                "tier": 2,
            },
        ]

    gap_sets = await find_tuition_value_gap_sets(
        mock_db,
        count=1,
        prov="Zhejiang",
        strict_major="Computer Science",
        budget=6000,
        budget_window=10000,
        score_min=600,
        score_max=600,
        candidates_per_score=3,
        max_volunteers_per_case=2,
        strict_target_quality=False,
    )

    assert len(gap_sets) == 1
    assert gap_sets[0]["constraint_relaxed"] == "tuition_value"
    assert gap_sets[0]["budget_anchor"] == 6000
    assert [row["tuition_delta"] for row in gap_sets[0]["volunteer_set"]] == [
        3000,
        5000,
    ]
    assert gap_sets[0]["volunteer_set"][0]["tuition_value_gain"] == 1
    assert "plan.min_tuition > %s" in calls[-1][0]
