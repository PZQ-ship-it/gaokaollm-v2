import json

import pytest

from gaokaollm_bench.data_gen.db_seeder import find_hierarchical_major_relax_gap_sets
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
    assert {item["major_name"] for item in volunteer_set} == {"医学检验技术", "医学影像技术"}
    assert restored.process_milestones["reject_generic_major_switch"] is True


def test_medical_major_cluster_patterns_are_auditable():
    clusters = load_major_clusters()
    include_patterns, exclude_patterns = get_major_cluster_patterns(["medical_technology"])

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
    assert suggested[0]["embedding_suggestion"]["parent_node_id"] == "basic_science_group"


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
    assert observed_tree["observed_build"]["embedding_auto_assign"]["assigned_row_count"] == 324


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
