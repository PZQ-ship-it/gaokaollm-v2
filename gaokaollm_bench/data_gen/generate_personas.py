"""CLI for generating IcebergPersona datasets from real DB Pareto gaps."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any

from gaokaollm_bench.constrains.enums import (
    DedupKeyMode,
    MajorRelaxScope,
    PersonaRelaxation,
    PersonaShape,
    PersonaSynthesisMode,
    values,
)
from gaokaollm_bench.constrains.paths import (
    DEFAULT_PERSONA_OUTPUT,
    MAJOR_DEFAULT_LABEL_MAP,
    MAJOR_DEFAULT_PROBE,
    MAJOR_FINAL_TREE,
)
from gaokaollm_bench.data_gen.db_seeder import (
    find_city_relax_gap_sets,
    find_employment_outcome_gap_sets,
    find_hierarchical_major_relax_gap_sets,
    find_major_relax_gap_sets,
    find_major_quality_gap_sets,
    find_many_pareto_gaps,
    find_pareto_gap_sets,
    find_region_tree_relax_gap_sets,
    find_risk_band_gap_sets,
    find_strength_relax_gap_sets,
    find_tuition_value_gap_sets,
)
from gaokaollm_bench.data_gen.major_tree import (
    UnknownMajorError,
    build_relaxation_stages,
    get_major_cluster_patterns,
)
from gaokaollm_bench.data_gen.persona_builder import synthesize_persona
from gaokaollm_bench.schemas import IcebergPersona


DEFAULT_OUTPUT = str(DEFAULT_PERSONA_OUTPUT)
DEFAULT_MAJOR_TREE = str(MAJOR_FINAL_TREE)
DEFAULT_NEIGHBOR_PROBE = str(MAJOR_DEFAULT_PROBE)
DEFAULT_NEIGHBOR_LABEL_MAP = str(MAJOR_DEFAULT_LABEL_MAP)
DEFAULT_EXCLUDE_PATTERNS = [
    "中北学院",
    "泰州学院",
    "职业学院",
    "职业技术学院",
    "职业",
    "专科学校",
    "专科",
    "独立学院",
    "京江学院",
    "杏林学院",
    "嘉华学院",
    "滇池学院",
    "江淮学院",
    "皖江学院",
    "张家界学院",
]

SAMPLE_DATA_DIR = Path("gaokaollm_bench/sample_data")
MULTI_AXIS_SOURCE_FILES = {
    "major_geo": SAMPLE_DATA_DIR / "iceberg_personas_real_db_10.json",
    "risk_band": SAMPLE_DATA_DIR / "iceberg_personas_risk_band_real_db_10.json",
    "major_quality": SAMPLE_DATA_DIR / "iceberg_personas_major_quality_real_db_10.json",
    "tuition_value": SAMPLE_DATA_DIR / "iceberg_personas_tuition_value_real_db_10.json",
    "employment_outcome": SAMPLE_DATA_DIR
    / "iceberg_personas_employment_outcome_real_db_10.json",
    "region_tree": SAMPLE_DATA_DIR / "iceberg_personas_region_tree_real_db_10.json",
}


async def _probe_neighbor_clusters(args: argparse.Namespace) -> list[str]:
    if args.neighbor_clusters:
        return args.neighbor_clusters
    if not args.use_probe_neighbors:
        return []

    from gaokaollm_bench.data_gen.major_probe_predict import predict_major_labels

    predictions = await predict_major_labels(
        [args.strict_major],
        probe_path=args.neighbor_probe,
        label_map_path=args.neighbor_label_map,
        major_tree_path=args.major_tree,
        top_k=max(args.neighbor_count + 30, 40),
    )
    neighbor_ids: list[str] = []
    for prediction in predictions[0]["predictions"]:
        label = prediction["label"]
        if label not in neighbor_ids:
            neighbor_ids.append(label)
    return neighbor_ids


def _school_label(row: dict[str, Any]) -> str:
    labels = []
    if row.get("is_985"):
        labels.append("985")
    if row.get("is_211"):
        labels.append("211")
    if row.get("is_double_first_class"):
        labels.append("双一流")
    return "/".join(labels) or str(row.get("education_level") or "普通院校")


def build_deterministic_persona(gap: dict[str, Any], index: int) -> IcebergPersona:
    """Build a schema-valid persona from verified DB rows without an LLM."""

    tier_a = gap["tier_a"]
    tier_b = gap["tier_b"]
    score = int(gap["score"])
    province = str(gap["province"])
    tier_a_name = str(tier_a["school_name"])
    tier_b_name = str(tier_b["school_name"])
    tier_b_score = int(float(tier_b["min_score"]))
    tier_a_label = _school_label(tier_a)
    tier_b_label = _school_label(tier_b)
    major_name = tier_b.get("major_name") or tier_a.get("major_name") or "目标专业"

    return IcebergPersona(
        case_id=f"real-db-{province}-{score}-{index:03d}",
        background={
            "score": score,
            "province": province,
            "subjects": ["物理", "化学", "生物"],
            "preferred_major": major_name,
            "baseline_school": tier_a_name,
            "baseline_tier": tier_a.get("tier"),
            "baseline_label": tier_a_label,
            "gap_school": tier_b_name,
            "gap_tier": tier_b.get("tier"),
            "gap_label": tier_b_label,
        },
        explicit_red_lines={
            "geo": f"坚决不出{province}",
            "reason": f"认为留在{province}更安全，只愿意先看本省的{tier_a_label}选择",
            "current_anchor_school": tier_a_name,
        },
        implicit_flexibilities={
            "trigger_school": tier_b_name,
            "trigger_condition": (
                f"只有看到{tier_b_name}是{province}外的{tier_b_label}，"
                f"且真实最低分{tier_b_score}不高于本人{score}分，才会动摇"
            ),
            "verified_min_score": tier_b_score,
            "tier_delta": gap["tier_delta"],
            "compromise": f"可以为了从{tier_a_label}跃迁到{tier_b_label}而考虑出省",
        },
        initial_utterance=f"我{score}分，只想留在{province}，外省学校先别推荐。",
        process_milestones={
            "reject_generic_advice": True,
            "name_baseline_constraint": tier_a_name,
            "require_specific_school_and_score": True,
            "accept_after_verified_tier_jump": tier_b_name,
        },
    )


def _volunteer_entry(row: dict[str, Any], score: int) -> dict[str, Any]:
    entry = {
        "school_id": row.get("school_id"),
        "school_name": row.get("school_name"),
        "school_province": row.get("school_province"),
        "school_city": row.get("school_city"),
        "major_id": row.get("major_id"),
        "major_name": row.get("major_name"),
        "year": row.get("year"),
        "min_score": int(float(row["min_score"])),
        "score_margin": score - int(float(row["min_score"])),
        "min_rank": row.get("min_rank"),
        "tier": row.get("tier"),
        "tier_label": _school_label(row),
        "is_985": bool(row.get("is_985")),
        "is_211": bool(row.get("is_211")),
        "is_double_first_class": bool(row.get("is_double_first_class")),
    }
    for key in (
        "student_rank",
        "rank_gap",
        "risk_level",
        "major_strength_rank",
        "major_strength_rating",
        "major_strength_level",
        "major_strength_source_type",
        "discipline_name",
        "quality_score",
        "quality_gain",
        "quality_anchor_score",
        "quality_tier",
        "best_major_rank",
        "best_rating",
        "has_key_major",
        "has_featured_major",
        "satisfaction_score",
        "satisfaction_vote_count",
        "quality_evidence_sources",
        "tuition",
        "tuition_delta",
        "budget_anchor",
        "ranking_gain",
        "tuition_value_gain",
        "outcome_score",
        "outcome_gain",
        "outcome_anchor_score",
        "outcome_tier",
        "employment_rank",
        "employment_rank_desc",
        "employment_top_city",
        "top_industry",
        "industry_distribution",
        "employment_city_distribution",
        "job_distribution",
        "salary_distribution",
        "employment_evidence_sources",
        "region_relax_strategy",
        "region_tree_type",
        "source_region_node_id",
        "source_region_name",
        "target_region_node_id",
        "target_region_name",
        "target_region_parent_id",
        "region_tree_confidence",
        "region_tree_mapping_rule",
        "region_tree_review_status",
        "region_tree_evidence",
    ):
        if row.get(key) is not None:
            value = row.get(key)
            if key in {
                "tuition",
                "tuition_delta",
                "budget_anchor",
                "ranking_gain",
                "tuition_value_gain",
                "employment_rank",
            }:
                value = int(float(value))
            elif key in {
                "quality_score",
                "quality_gain",
                "quality_anchor_score",
                "satisfaction_score",
                "outcome_score",
                "outcome_gain",
                "outcome_anchor_score",
                "region_tree_confidence",
            }:
                value = float(value)
            entry[key] = value
    return entry


def build_deterministic_persona_from_gap_set(
    gap_set: dict[str, Any],
    index: int,
) -> IcebergPersona:
    """Build a persona whose compromise target is a real volunteer set."""

    tier_a = gap_set["tier_a"]
    score = int(gap_set["score"])
    province = str(gap_set["province"])
    tier_a_name = str(tier_a["school_name"])
    tier_a_label = _school_label(tier_a)
    volunteers = [_volunteer_entry(row, score) for row in gap_set["volunteer_set"]]
    best_labels = sorted({item["tier_label"] for item in volunteers})
    best_names = [item["school_name"] for item in volunteers[:5]]
    relaxed_constraint = gap_set.get("constraint_relaxed", "province")
    relaxation_kind = gap_set.get("relaxation_kind")
    stage_relaxation_kind = gap_set.get("stage_relaxation_kind")
    relax_scope = gap_set.get("relax_scope", "province")
    relaxation_stage = gap_set.get("relaxation_stage")
    target_major_clusters = gap_set.get("target_major_clusters")
    accepted_major_examples = list(
        dict.fromkeys(
            item["major_name"] for item in volunteers if item.get("major_name")
        )
    )[:8]

    if relaxed_constraint == "city":
        strict_major = str(
            gap_set.get("strict_major") or tier_a.get("major_name") or "目标专业"
        )
        major_name = strict_major
        city = str(gap_set.get("city") or tier_a.get("school_city") or "目标城市")
        explicit_red_lines = {
            "city": f"坚决只看{city}",
            "major": f"优先保持{strict_major}",
            "reason": f"认为留在{city}更方便安全，暂时不接受同省其他城市",
            "current_anchor_school": tier_a_name,
            "current_anchor_city": tier_a.get("school_city"),
            "current_anchor_major": tier_a.get("major_name"),
        }
        trigger_condition = (
            f"只有看到仍在{province}、但不限定{city}后形成的真实可达更高层次志愿集合，"
            f"且每个志愿都有城市、学校、专业、最低分不高于{score}分的证据，才会动摇"
        )
        compromise = f"可以为了学校层次跃迁，从{city}放宽到{province}内其他城市"
        initial_utterance = (
            f"我{score}分，只想在{city}读{strict_major}，其他城市先别推荐。"
        )
        milestones = {
            "reject_generic_city_switch": True,
            "require_complete_volunteer_set": True,
            "require_each_option_city_and_score_evidence": True,
            "accept_after_verified_city_relax_set": best_names,
        }
    elif relaxed_constraint == "strength":
        strict_major = str(
            gap_set.get("strict_major") or tier_a.get("major_name") or "目标专业"
        )
        major_name = strict_major
        anchor_rank = gap_set.get("strength_anchor_rank") or tier_a.get(
            "major_strength_rank"
        )
        explicit_red_lines = {
            "strength": "更看重学科实力，普通学校先不考虑",
            "major": f"优先保持{strict_major}",
            "reason": f"只想要{strict_major}中学科实力更强的学校",
            "current_anchor_school": tier_a_name,
            "current_anchor_strength_rank": anchor_rank,
        }
        trigger_condition = (
            f"只有看到{strict_major}在更强学科实力学校中的真实可达志愿集合，"
            "且每个志愿都有学校、专业、学科实力排名和最低分证据，才会动摇"
        )
        compromise = f"可以为了更强的学科实力，把{strict_major}从普通学校放宽到更强学校"
        initial_utterance = (
            f"我{score}分，想读{strict_major}，但更看重学科实力，普通学校先别急着推荐。"
        )
        milestones = {
            "reject_generic_strength_advice": True,
            "require_strength_evidence": True,
            "require_complete_volunteer_set": True,
            "require_each_option_strength_and_score_evidence": True,
            "accept_after_verified_strength_jump": best_names,
        }
    elif relaxed_constraint == "major_quality":
        strict_major = str(
            gap_set.get("strict_major") or tier_a.get("major_name") or "目标专业"
        )
        major_name = strict_major
        anchor_score = gap_set.get("quality_anchor_score") or tier_a.get(
            "quality_score"
        )
        max_quality_gain = gap_set.get("max_quality_gain")
        explicit_red_lines = {
            "major": f"优先保持{strict_major}",
            "quality": "更看重这个专业本身的排名、评估和特色重点证据",
            "reason": f"不想只看学校名气，希望{strict_major}有更强的专业证据",
            "current_anchor_school": tier_a_name,
            "current_anchor_major": tier_a.get("major_name"),
            "current_anchor_quality_score": anchor_score,
        }
        trigger_condition = (
            f"只有看到{strict_major}或近似同专业的真实可达志愿集合，"
            "并且每个志愿都有学校、专业、最低分、最低位次、专业排名/学科评估/"
            "特色重点/满意度等专业质量证据，才会接受跨省比较。"
        )
        compromise = (
            "可以为了更强的专业质量证据接受跨省同专业方案；"
            f"最高质量增益约为{max_quality_gain}"
        )
        initial_utterance = (
            f"我{score}分，想读{strict_major}，更看重专业实力和专业排名，"
            "但省外学校先别急着推荐。"
        )
        milestones = {
            "reject_generic_quality_advice": True,
            "require_major_quality_evidence": True,
            "require_complete_volunteer_set": True,
            "require_each_option_quality_and_score_evidence": True,
            "accept_after_verified_major_quality_set": best_names,
        }
    elif relaxed_constraint == "tuition_value":
        strict_major = str(
            gap_set.get("strict_major") or tier_a.get("major_name") or "目标专业"
        )
        major_name = strict_major
        budget_anchor = int(gap_set.get("budget_anchor") or 6000)
        budget_window = int(gap_set.get("budget_window") or 10000)
        max_tuition_delta = int(gap_set.get("max_tuition_delta") or 0)
        explicit_red_lines = {
            "budget": f"每年学费最好不超过{budget_anchor}元",
            "major": f"优先保持{strict_major}",
            "reason": "家庭预算比较保守，暂时不接受明显超预算方案",
            "current_anchor_school": tier_a_name,
            "current_anchor_major": tier_a.get("major_name"),
            "current_anchor_tuition": tier_a.get("tuition"),
        }
        trigger_condition = (
            f"只有看到仍满足分数、专业和选科约束，且学费只比{budget_anchor}元/年预算"
            f"最多增加{budget_window}元/年的真实可达志愿集合，"
            "并且每个志愿都有学校、专业、最低分、最低位次、学费和学费增量证据，"
            "才会接受小幅放宽学费预算。"
        )
        compromise = (
            f"可以为了更好的学校层次、排名或风险结构，接受每年最多增加"
            f"{max_tuition_delta}元学费"
        )
        scope_phrase = (
            "地域不限，" if relax_scope == "national" else f"尽量留在{province}，"
        )
        initial_utterance = (
            f"我{score}分，{scope_phrase}想读{strict_major}，每年学费预算最好"
            f"{budget_anchor}元以内，太贵的先别推荐。"
        )
        milestones = {
            "reject_generic_budget_advice": True,
            "require_tuition_evidence": True,
            "require_complete_volunteer_set": True,
            "require_each_option_tuition_and_score_evidence": True,
            "accept_after_verified_tuition_value_set": best_names,
        }
    elif relaxed_constraint == "employment_outcome":
        strict_major = str(
            gap_set.get("strict_major") or tier_a.get("major_name") or "目标专业"
        )
        major_name = strict_major
        anchor_score = gap_set.get("outcome_anchor_score") or tier_a.get(
            "outcome_score"
        )
        max_outcome_gain = gap_set.get("max_outcome_gain")
        explicit_red_lines = {
            "major": f"优先保持{strict_major}",
            "employment": "希望就业、薪资、行业和岗位去向证据更清楚",
            "reason": "不想只听泛泛而谈的好就业，必须能看到真实就业证据",
            "current_anchor_school": tier_a_name,
            "current_anchor_major": tier_a.get("major_name"),
            "current_anchor_outcome_score": anchor_score,
        }
        trigger_condition = (
            f"只有看到{strict_major}或相近专业的真实可达志愿集合，"
            "并且每个志愿都有学校、专业、最低分、最低位次、就业排名、行业/岗位/薪资等就业证据，"
            "才会接受跨省或相近专业比较。"
        )
        compromise = (
            "可以为了更强的就业结果证据接受跨省或相近专业比较，"
            f"最高就业结果增益约为{max_outcome_gain}"
        )
        initial_utterance = (
            f"我{score}分，想读{strict_major}，希望以后就业和薪资稳定，"
            "但省外或相近专业先别急着推荐，除非你有真实数据。"
        )
        milestones = {
            "reject_generic_employment_advice": True,
            "require_employment_evidence": True,
            "require_complete_volunteer_set": True,
            "require_each_option_employment_and_score_evidence": True,
            "accept_after_verified_employment_outcome_set": best_names,
        }
    elif relaxed_constraint == "region_tree":
        strict_major = str(
            gap_set.get("strict_major") or tier_a.get("major_name") or "target major"
        )
        major_name = strict_major
        city = str(gap_set.get("city") or tier_a.get("school_city") or "target city")
        strategies = list(gap_set.get("region_relax_strategies") or [])
        target_regions = list(
            dict.fromkeys(
                item.get("target_region_name")
                for item in volunteers
                if item.get("target_region_name")
            )
        )[:5]
        explicit_red_lines = {
            "region": f"prefer {city} or familiar nearby region",
            "major": f"keep {strict_major}",
            "reason": "do not accept arbitrary city switches without region-tree and score evidence",
            "current_anchor_school": tier_a_name,
            "current_anchor_city": tier_a.get("school_city"),
            "current_anchor_major": tier_a.get("major_name"),
            "current_region_strategies": strategies,
        }
        trigger_condition = (
            f"Only accept options relaxed from {city} by region_tree_relax when each option "
            f"contains school, city, major, min_score <= {score}, region strategy, "
            "source node and target node evidence."
        )
        compromise = (
            "Can compare reviewed geo-block or urban-tier region-tree neighbors, "
            "while school gain is still judged by tier/ranking rather than city tier itself: "
            f"{', '.join(str(item) for item in target_regions) or 'reviewed region nodes'}"
        )
        initial_utterance = (
            f"我{score}分，选考物化生，想读{strict_major}，优先只看{city}或别太远的地方。"
            "如果没有地域树和最低分证据，先别随便推荐其他城市。"
        )
        milestones = {
            "reject_generic_city_advice": True,
            "require_region_tree_evidence": True,
            "require_complete_volunteer_set": True,
            "require_each_option_region_tree_and_score_evidence": True,
            "accept_after_verified_region_tree_set": best_names,
            "accepted_region_nodes": target_regions,
            "region_relax_strategies": strategies,
        }
    elif relaxed_constraint == "risk_band":
        strict_major = str(
            gap_set.get("strict_major") or tier_a.get("major_name") or "目标专业"
        )
        major_name = strict_major
        risk_levels = list(dict.fromkeys(item.get("risk_level") for item in volunteers))
        explicit_red_lines = {
            "risk": "只求稳妥，不接受冲刺风险",
            "major": f"优先保持{strict_major}",
            "reason": "担心冲刺志愿浪费名额，希望先看保守方案",
            "current_anchor_school": tier_a_name,
            "current_anchor_major": tier_a.get("major_name"),
            "current_anchor_risk_level": tier_a.get("risk_level"),
        }
        trigger_condition = (
            "只有看到同省、同专业、选科与分数均可核验的冲稳保组合，"
            "且每个志愿都有学校、专业、最低分、最低位次和风险层级证据，才会接受适度冲刺。"
        )
        compromise = "可以把单一保守方案放宽为包含 chong/wen/bao 的冲稳保组合"
        initial_utterance = (
            f"鐗╁寲鐢燂紝{score}鍒嗭紝只想稳妥一点，"
            f"{strict_major}不要冲刺太危险的学校。"
        )
        milestones = {
            "reject_generic_risk_advice": True,
            "require_risk_band_evidence": True,
            "require_complete_volunteer_set": True,
            "require_each_option_score_and_rank_evidence": True,
            "accept_after_verified_risk_portfolio": best_names,
            "required_risk_levels": risk_levels,
        }
    elif relaxed_constraint == "major":
        strict_major = str(
            gap_set.get("strict_major") or tier_a.get("major_name") or "原专业"
        )
        if (
            relaxation_kind in {"clinical_to_medtech", "hierarchical_major"}
            and stage_relaxation_kind != "any_major"
        ):
            explicit_red_lines = {
                "major": f"坚决只读{strict_major}",
                "reason": f"认为只有{strict_major}才算真正的医学路线，不接受未经证明的专业替代",
                "current_anchor_school": tier_a_name,
                "current_anchor_major": tier_a.get("major_name"),
            }
            scope_text = (
                f"仍留在{province}" if relax_scope == "province" else "可包含外省"
            )
            stage_text = (
                f"第{relaxation_stage}阶段{gap_set.get('relaxation_stage_label')}"
                if relaxation_stage
                else "医学技术类"
            )
            trigger_condition = (
                f"只有看到一个{scope_text}、按专业簇层级放宽到{stage_text}后形成的真实可达志愿集合，"
                f"且每个志愿都有学校名、专业名、最低分不高于{score}分的证据，才会动摇"
            )
            compromise = f"可以从{strict_major}按专业簇层级逐步妥协到{stage_text}"
            initial_utterance = (
                f"我{score}分，只想读{strict_major}，其他医学相关专业先别推荐。"
            )
            milestones = {
                "reject_single_school_bait": True,
                "reject_generic_major_switch": True,
                "require_cluster_level_relaxation": True,
                "require_complete_volunteer_set": True,
                "require_each_option_score_evidence": True,
                "accept_after_verified_medtech_set": best_names,
            }
        else:
            explicit_red_lines = {
                "major": f"坚决只读{strict_major}",
                "reason": "担心换专业会影响职业路径，暂时不接受任何专业放宽",
                "current_anchor_school": tier_a_name,
                "current_anchor_major": tier_a.get("major_name"),
            }
            scope_text = (
                f"仍留在{province}" if relax_scope == "province" else "可包含外省"
            )
            trigger_condition = (
                f"只有看到一个{scope_text}、专业不限后真实可达的更高层次志愿集合，"
                f"且每个志愿都有学校名、专业名、最低分不高于{score}分的证据，才会动摇"
            )
            compromise = f"可以为了学校层次跃迁而暂时放宽{strict_major}专业执念"
            initial_utterance = (
                f"我{score}分，只想读{strict_major}，专业不对的学校再好也不考虑。"
            )
            milestones = {
                "reject_single_school_bait": True,
                "reject_generic_major_switch": True,
                "require_complete_volunteer_set": True,
                "require_each_option_score_evidence": True,
                "accept_after_verified_any_major_set": best_names,
            }
    else:
        major_name = (
            volunteers[0].get("major_name") or tier_a.get("major_name") or "目标专业"
        )
        explicit_red_lines = {
            "geo": f"坚决不出{province}",
            "reason": f"认为留在{province}更安全，只愿意先看本省的{tier_a_label}选择",
            "current_anchor_school": tier_a_name,
        }
        trigger_condition = (
            f"只有看到一个由多所{province}外真实可达跃迁志愿组成的集合，"
            f"且每个志愿都有学校名、专业名、最低分不高于{score}分的证据，才会动摇"
        )
        compromise = f"可以为了从{tier_a_label}跃迁到更高层次志愿集合而考虑出省"
        initial_utterance = f"我{score}分，只想留在{province}，外省学校先别推荐。"
        milestones = {
            "reject_single_school_bait": True,
            "reject_generic_advice": True,
            "require_complete_volunteer_set": True,
            "require_each_option_score_evidence": True,
            "accept_after_verified_volunteer_set": best_names,
        }

    return IcebergPersona(
        case_id=f"real-db-set-{province}-{score}-{index:03d}",
        background={
            "score": score,
            "province": province,
            "city": gap_set.get("city"),
            "subjects": ["物理", "化学", "生物"],
            "preferred_major": strict_major
            if relaxed_constraint == "major"
            else major_name,
            "baseline_school": tier_a_name,
            "baseline_major": tier_a.get("major_name"),
            "baseline_tier": tier_a.get("tier"),
            "baseline_label": tier_a_label,
            "baseline_ranking": tier_a.get("ranking"),
            "volunteer_count": len(volunteers),
            "max_gap_tier": max(item["tier"] for item in volunteers),
            "max_tier_delta": gap_set["max_tier_delta"],
            "constraint_relaxed": relaxed_constraint,
            "relaxation_kind": relaxation_kind,
            "stage_relaxation_kind": stage_relaxation_kind,
            "relax_scope": relax_scope,
            "baseline_risk_preference": gap_set.get("baseline_risk_preference"),
            "relaxation_stage": relaxation_stage,
            "relaxation_stage_label": gap_set.get("relaxation_stage_label"),
            "target_major_clusters": target_major_clusters,
            "target_major_categories": gap_set.get("target_major_categories"),
            "psychological_distance": gap_set.get("psychological_distance"),
            "years_used": gap_set.get("years_used"),
            "stage_attempts": gap_set.get("stage_attempts"),
            "student_rank": gap_set.get("student_rank"),
            "risk_levels": gap_set.get("risk_levels"),
            "portfolio_gain": gap_set.get("portfolio_gain"),
            "strength_anchor_rank": gap_set.get("strength_anchor_rank"),
            "quality_anchor_score": gap_set.get("quality_anchor_score"),
            "max_quality_gain": gap_set.get("max_quality_gain"),
            "budget_anchor": gap_set.get("budget_anchor"),
            "budget_window": gap_set.get("budget_window"),
            "max_tuition_delta": gap_set.get("max_tuition_delta"),
            "max_ranking_gain": gap_set.get("max_ranking_gain"),
            "outcome_anchor_score": gap_set.get("outcome_anchor_score"),
            "max_outcome_gain": gap_set.get("max_outcome_gain"),
            "region_relax_strategies": gap_set.get("region_relax_strategies"),
        },
        explicit_red_lines=explicit_red_lines,
        implicit_flexibilities={
            "trigger_type": "volunteer_set",
            "constraint_relaxed": relaxed_constraint,
            "city": gap_set.get("city"),
            "relaxation_kind": relaxation_kind,
            "stage_relaxation_kind": stage_relaxation_kind,
            "relax_scope": relax_scope,
            "baseline_risk_preference": gap_set.get("baseline_risk_preference"),
            "relaxation_stage": relaxation_stage,
            "relaxation_stage_label": gap_set.get("relaxation_stage_label"),
            "target_major_clusters": target_major_clusters,
            "target_major_categories": gap_set.get("target_major_categories"),
            "psychological_distance": gap_set.get("psychological_distance"),
            "trigger_condition": trigger_condition,
            "volunteer_set": volunteers,
            "minimum_required_volunteers": min(3, len(volunteers)),
            "representative_schools": best_names,
            "accepted_major_examples": accepted_major_examples,
            "years_used": gap_set.get("years_used"),
            "stage_attempts": gap_set.get("stage_attempts"),
            "student_rank": gap_set.get("student_rank"),
            "risk_levels": gap_set.get("risk_levels"),
            "portfolio_gain": gap_set.get("portfolio_gain"),
            "strength_anchor_rank": gap_set.get("strength_anchor_rank"),
            "quality_anchor_score": gap_set.get("quality_anchor_score"),
            "max_quality_gain": gap_set.get("max_quality_gain"),
            "budget_anchor": gap_set.get("budget_anchor"),
            "budget_window": gap_set.get("budget_window"),
            "max_tuition_delta": gap_set.get("max_tuition_delta"),
            "max_ranking_gain": gap_set.get("max_ranking_gain"),
            "outcome_anchor_score": gap_set.get("outcome_anchor_score"),
            "max_outcome_gain": gap_set.get("max_outcome_gain"),
            "baseline_tier": tier_a.get("tier"),
            "region_relax_strategies": gap_set.get("region_relax_strategies"),
            "tier_labels": best_labels,
            "compromise": compromise,
        },
        initial_utterance=initial_utterance,
        process_milestones=milestones,
    )


MULTI_AXIS_PROFILES: dict[str, tuple[str, str]] = {
    "major_geo_risk": ("major_geo", "risk_band"),
    "quality_tuition": ("major_quality", "tuition_value"),
    "employment_region": ("employment_outcome", "region_tree"),
}


def _axis_volunteer_entries(
    axis: str,
    gap_set: dict[str, Any],
    score: int,
) -> list[dict[str, Any]]:
    entries = []
    for row in gap_set.get("volunteer_set") or []:
        entry = _volunteer_entry(row, score)
        entry["axis"] = axis
        entries.append(entry)
    return entries


def _axis_flexibility(
    axis: str,
    gap_set: dict[str, Any],
    score: int,
) -> dict[str, Any]:
    volunteers = _axis_volunteer_entries(axis, gap_set, score)
    flex = {
        "constraint_relaxed": axis,
        "trigger_type": "volunteer_set",
        "volunteer_set": volunteers,
        "representative_schools": [
            row.get("school_name") for row in volunteers[:5] if row.get("school_name")
        ],
        "baseline_tier": (gap_set.get("tier_a") or {}).get("tier"),
        "max_tier_delta": gap_set.get("max_tier_delta"),
    }
    for key in (
        "risk_levels",
        "portfolio_gain",
        "strength_anchor_rank",
        "quality_anchor_score",
        "max_quality_gain",
        "budget_anchor",
        "budget_window",
        "max_tuition_delta",
        "max_ranking_gain",
        "outcome_anchor_score",
        "max_outcome_gain",
        "region_relax_strategies",
        "city",
        "strict_major",
    ):
        if gap_set.get(key) is not None:
            flex[key] = gap_set.get(key)
    return flex


def _multi_axis_gap_set(
    *,
    profile: str,
    first_axis: str,
    first_gap: dict[str, Any],
    second_axis: str,
    second_gap: dict[str, Any],
) -> dict[str, Any]:
    score = max(int(first_gap["score"]), int(second_gap["score"]))
    tier_a = first_gap["tier_a"]
    first_flex = _axis_flexibility(first_axis, first_gap, score)
    second_flex = _axis_flexibility(second_axis, second_gap, score)
    volunteers = first_flex["volunteer_set"] + second_flex["volunteer_set"]
    max_tier_delta = max(
        int(first_gap.get("max_tier_delta") or 0),
        int(second_gap.get("max_tier_delta") or 0),
    )
    return {
        "constraint_relaxed": "multi_axis",
        "multi_axis_profile": profile,
        "relaxation_axes": [first_axis, second_axis],
        "axis_flexibilities": {
            first_axis: first_flex,
            second_axis: second_flex,
        },
        "tier_a": tier_a,
        "score": score,
        "province": first_gap.get("province") or second_gap.get("province"),
        "city": second_gap.get("city") or first_gap.get("city"),
        "strict_major": (
            first_gap.get("strict_major")
            or second_gap.get("strict_major")
            or tier_a.get("major_name")
        ),
        "volunteer_set": volunteers,
        "max_tier_delta": max_tier_delta,
        "axis_case_scores": {
            first_axis: int(first_gap["score"]),
            second_axis: int(second_gap["score"]),
        },
    }


def build_multi_axis_persona_from_gap_set(
    gap_set: dict[str, Any],
    index: int,
) -> IcebergPersona:
    """Build a two-axis iceberg persona from verified single-axis gap sets."""

    score = int(gap_set["score"])
    province = str(gap_set["province"])
    city = str(gap_set.get("city") or (gap_set["tier_a"].get("school_city") or ""))
    strict_major = str(gap_set.get("strict_major") or "target major")
    profile = str(gap_set["multi_axis_profile"])
    axes = list(gap_set["relaxation_axes"])
    axis_flexibilities = dict(gap_set["axis_flexibilities"])
    all_schools = []
    for axis in axes:
        all_schools.extend(axis_flexibilities[axis].get("representative_schools") or [])
    all_schools = list(dict.fromkeys(str(item) for item in all_schools if item))[:8]
    tier_a = gap_set["tier_a"]

    if profile == "major_geo_risk":
        explicit_red_lines = {
            "major": f"keep {strict_major}",
            "geo": f"prefer {province}",
            "risk": "prefer conservative choices only",
            "reason": "will only reconsider if both major/region relaxation and chong/wen/bao evidence are shown",
        }
        initial_utterance = (
            f"我{score}分，选考物理化学生物，想读{strict_major}，优先留在{province}，"
            "而且只求稳，不接受冲刺。除非你能同时给出专业/地域放宽和冲稳保证据，"
            "否则先不要推荐随机外省或冒险方案。"
        )
    elif profile == "quality_tuition":
        budget = axis_flexibilities.get("tuition_value", {}).get("budget_anchor", 6000)
        explicit_red_lines = {
            "major": f"prefer {strict_major}",
            "budget": f"annual tuition should stay near {budget}",
            "quality": "care about major-level quality evidence",
            "reason": "will only accept a small budget relaxation if professional quality evidence is strong",
        }
        initial_utterance = (
            f"我{score}分，选考物理化学生物，地域不限，想读{strict_major}，每年学费预算大概{budget}以内，"
            "也很看重专业排名和学科实力。除非你能同时给出小幅超预算的性价比证据"
            "和专业质量证据，否则太贵的先别推荐。"
        )
    else:
        explicit_red_lines = {
            "major": f"prefer {strict_major}",
            "region": f"prefer {city or province} or a familiar region",
            "employment": "care about employment outcome evidence",
            "reason": "will only consider a region-tree move if employment evidence and region-tree evidence are both concrete",
        }
        initial_utterance = (
            f"我{score}分，选考物理化学生物，想读{strict_major}，希望就业和薪资稳定，"
            f"但不想随便离开{city or province}。除非你能同时给出就业结果证据"
            "和 reviewed 地域树证据，否则先别随便换地域。"
        )

    axis_descriptions = {
        "major_geo": "major/region joint relaxation evidence",
        "risk_band": "chong/wen/bao risk portfolio evidence",
        "major_quality": "school-major quality evidence",
        "tuition_value": "small tuition-budget relaxation with value evidence",
        "employment_outcome": "employment outcome evidence",
        "region_tree": "reviewed region-tree evidence",
    }
    trigger_condition = (
        "The persona accepts only if the target agent supplies both required axes: "
        + ", ".join(axis_descriptions.get(axis, axis) for axis in axes)
        + ". Hidden axis_flexibilities and volunteer_set are evaluator-only."
    )

    return IcebergPersona(
        case_id=f"multi-axis-{profile}-{province}-{score}-{index:03d}",
        background={
            "score": score,
            "province": province,
            "city": city,
            "subjects": ["物理", "化学", "生物"],
            "preferred_major": strict_major,
            "baseline_school": tier_a.get("school_name"),
            "baseline_major": tier_a.get("major_name"),
            "baseline_tier": tier_a.get("tier"),
            "baseline_label": _school_label(tier_a),
            "constraint_relaxed": "multi_axis",
            "multi_axis_profile": profile,
            "relaxation_axes": axes,
            "volunteer_count": len(gap_set.get("volunteer_set") or []),
            "max_tier_delta": gap_set.get("max_tier_delta"),
            "axis_case_scores": gap_set.get("axis_case_scores"),
        },
        explicit_red_lines=explicit_red_lines,
        implicit_flexibilities={
            "trigger_type": "multi_axis",
            "constraint_relaxed": "multi_axis",
            "multi_axis_profile": profile,
            "relaxation_axes": axes,
            "axis_flexibilities": axis_flexibilities,
            "volunteer_set": gap_set.get("volunteer_set") or [],
            "minimum_required_axes": len(axes),
            "representative_schools": all_schools,
            "trigger_condition": trigger_condition,
            "compromise": (
                "The user can compromise only when both axes are evidenced with "
                "real school, major, minimum-score/rank, and axis-specific evidence."
            ),
        },
        initial_utterance=initial_utterance,
        process_milestones={
            "reject_single_axis_solution": True,
            "require_multi_axis_evidence": True,
            "required_axes": axes,
            "accept_after_verified_multi_axis_set": all_schools,
        },
    )


def _load_source_axis_personas(axis: str) -> list[dict[str, Any]]:
    path = MULTI_AXIS_SOURCE_FILES[axis]
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, dict) and "items" in data:
        data = data["items"]
    return data if isinstance(data, list) else []


def _gap_from_source_persona(item: dict[str, Any], axis: str) -> dict[str, Any]:
    background = item.get("background") or {}
    flex = item.get("implicit_flexibilities") or {}
    volunteers = [
        row for row in flex.get("volunteer_set") or [] if isinstance(row, dict)
    ]
    if not volunteers:
        raise ValueError(f"source persona {item.get('case_id')} has no volunteer_set")
    tier_a = {
        "school_name": background.get("baseline_school"),
        "major_name": background.get("baseline_major")
        or background.get("preferred_major"),
        "school_city": background.get("city"),
        "tier": background.get("baseline_tier"),
        "ranking": background.get("baseline_ranking"),
    }
    gap = {
        "score": int(background.get("score") or 0),
        "province": background.get("province"),
        "city": background.get("city"),
        "strict_major": background.get("preferred_major"),
        "tier_a": tier_a,
        "volunteer_set": volunteers,
        "max_tier_delta": background.get("max_tier_delta") or 0,
        "constraint_relaxed": axis,
    }
    for key in (
        "risk_levels",
        "portfolio_gain",
        "strength_anchor_rank",
        "quality_anchor_score",
        "max_quality_gain",
        "budget_anchor",
        "budget_window",
        "max_tuition_delta",
        "max_ranking_gain",
        "outcome_anchor_score",
        "max_outcome_gain",
        "region_relax_strategies",
    ):
        if flex.get(key) is not None:
            gap[key] = flex.get(key)
        elif background.get(key) is not None:
            gap[key] = background.get(key)
    return gap


def _multi_axis_gap_sets_from_source_files(count: int) -> list[dict[str, Any]]:
    if count % len(MULTI_AXIS_PROFILES) != 0:
        raise ValueError(
            f"--count for --relaxation multi_axis must be divisible by 3 (got {count})."
        )
    per_profile = count // len(MULTI_AXIS_PROFILES)
    source_items = {
        axis: _load_source_axis_personas(axis) for axis in MULTI_AXIS_SOURCE_FILES
    }
    required_axes = {axis for axes in MULTI_AXIS_PROFILES.values() for axis in axes}
    if any(len(source_items[axis]) < per_profile for axis in required_axes):
        return []

    gap_sets: list[dict[str, Any]] = []
    for profile, (first_axis, second_axis) in MULTI_AXIS_PROFILES.items():
        for idx in range(per_profile):
            first_gap = _gap_from_source_persona(
                source_items[first_axis][idx], first_axis
            )
            second_gap = _gap_from_source_persona(
                source_items[second_axis][idx],
                second_axis,
            )
            gap_sets.append(
                _multi_axis_gap_set(
                    profile=profile,
                    first_axis=first_axis,
                    first_gap=first_gap,
                    second_axis=second_axis,
                    second_gap=second_gap,
                )
            )
    return gap_sets


async def find_multi_axis_gap_sets(
    fetch_query: Any,
    *,
    count: int,
    args: argparse.Namespace,
) -> list[dict[str, Any]]:
    """Compose existing real-DB single-axis gap sets into two-axis cases."""

    source_gap_sets = _multi_axis_gap_sets_from_source_files(count)
    if source_gap_sets:
        return source_gap_sets

    if count % len(MULTI_AXIS_PROFILES) != 0:
        raise ValueError(
            f"--count for --relaxation multi_axis must be divisible by 3 (got {count})."
        )
    per_profile = count // len(MULTI_AXIS_PROFILES)
    common_kwargs = {
        "prov": args.province,
        "score_min": args.score_min,
        "score_max": args.score_max,
        "score_step": args.score_step,
        "candidates_per_score": args.candidates_per_score,
        "max_volunteers_per_case": args.max_volunteers_per_case,
        "max_volunteers_per_school": args.max_volunteers_per_school,
        "include_special_majors": args.include_special_majors,
        "max_major_name_length": args.max_major_name_length,
        "strict_target_quality": not args.no_strict_target_quality,
    }
    exclude_name_patterns = (
        [] if args.include_suspect_schools else DEFAULT_EXCLUDE_PATTERNS
    )

    major_geo_gaps = await find_pareto_gap_sets(
        fetch_query,
        count=per_profile,
        prov=args.province,
        score_min=args.score_min,
        score_max=args.score_max,
        score_step=args.score_step,
        candidates_per_score=args.candidates_per_score,
        max_volunteers_per_case=args.max_volunteers_per_case,
        exclude_name_patterns=exclude_name_patterns,
        strict_target_quality=not args.no_strict_target_quality,
    )
    risk_gaps = await find_risk_band_gap_sets(
        fetch_query,
        count=per_profile,
        prov=args.province,
        strict_major=args.strict_major,
        score_min=args.score_min,
        score_max=args.score_max,
        score_step=args.score_step,
        candidates_per_score=args.candidates_per_score,
        max_volunteers_per_case=args.max_volunteers_per_case,
        max_volunteers_per_school=args.max_volunteers_per_school,
        strict_target_quality=not args.no_strict_target_quality,
    )
    quality_gaps = await find_major_quality_gap_sets(
        fetch_query,
        count=per_profile,
        strict_major=args.strict_major or None,
        exclude_name_patterns=exclude_name_patterns,
        min_quality_gain=args.min_quality_gain,
        **common_kwargs,
    )
    tuition_gaps = await find_tuition_value_gap_sets(
        fetch_query,
        count=per_profile,
        budget=args.budget,
        budget_window=args.budget_window,
        relax_scope=args.tuition_relax_scope,
        strict_major=args.strict_major or None,
        exclude_name_patterns=exclude_name_patterns,
        **common_kwargs,
    )
    employment_gaps = await find_employment_outcome_gap_sets(
        fetch_query,
        count=per_profile,
        strict_major=args.strict_major or None,
        exclude_name_patterns=exclude_name_patterns,
        min_outcome_gain=args.min_outcome_gain,
        **common_kwargs,
    )
    region_gaps = await find_region_tree_relax_gap_sets(
        fetch_query,
        count=per_profile,
        city=args.city,
        strict_major=args.strict_major or None,
        exclude_name_patterns=exclude_name_patterns,
        **common_kwargs,
    )

    source_pairs = {
        "major_geo_risk": ("major_geo", major_geo_gaps, "risk_band", risk_gaps),
        "quality_tuition": (
            "major_quality",
            quality_gaps,
            "tuition_value",
            tuition_gaps,
        ),
        "employment_region": (
            "employment_outcome",
            employment_gaps,
            "region_tree",
            region_gaps,
        ),
    }
    missing = {
        profile: {
            first_axis: len(first_gaps),
            second_axis: len(second_gaps),
            "required_each": per_profile,
        }
        for profile, (
            first_axis,
            first_gaps,
            second_axis,
            second_gaps,
        ) in source_pairs.items()
        if len(first_gaps) < per_profile or len(second_gaps) < per_profile
    }
    if missing:
        raise ValueError(
            "Cannot build enough multi_axis real-DB cases: "
            + json.dumps(missing, ensure_ascii=False)
        )

    gap_sets: list[dict[str, Any]] = []
    for profile, (
        first_axis,
        first_gaps,
        second_axis,
        second_gaps,
    ) in source_pairs.items():
        for idx in range(per_profile):
            gap_sets.append(
                _multi_axis_gap_set(
                    profile=profile,
                    first_axis=first_axis,
                    first_gap=first_gaps[idx],
                    second_axis=second_axis,
                    second_gap=second_gaps[idx],
                )
            )
    return gap_sets


async def _generate(args: argparse.Namespace) -> list[IcebergPersona]:
    from app.core.db_pg import close_pool, fetch_query

    personas: list[IcebergPersona] = []
    if args.persona_shape == "volunteer_set":
        if args.relaxation == "multi_axis":
            gap_sets = await find_multi_axis_gap_sets(
                fetch_query,
                count=args.count,
                args=args,
            )
            personas = [
                build_multi_axis_persona_from_gap_set(gap_set, i + 1)
                for i, gap_set in enumerate(gap_sets)
            ]
            await close_pool()
            return personas
        if args.relaxation == "province":
            gap_sets = await find_pareto_gap_sets(
                fetch_query,
                count=args.count,
                prov=args.province,
                score_min=args.score_min,
                score_max=args.score_max,
                score_step=args.score_step,
                candidates_per_score=args.candidates_per_score,
                max_volunteers_per_case=args.max_volunteers_per_case,
                exclude_name_patterns=[]
                if args.include_suspect_schools
                else DEFAULT_EXCLUDE_PATTERNS,
                strict_target_quality=not args.no_strict_target_quality,
            )
        elif args.relaxation == "city":
            gap_sets = await find_city_relax_gap_sets(
                fetch_query,
                count=args.count,
                prov=args.province,
                city=args.city,
                strict_major=args.strict_major,
                score_min=args.score_min,
                score_max=args.score_max,
                score_step=args.score_step,
                candidates_per_score=args.candidates_per_score,
                max_volunteers_per_case=args.max_volunteers_per_case,
                max_volunteers_per_school=args.max_volunteers_per_school,
                include_special_majors=args.include_special_majors,
                max_major_name_length=args.max_major_name_length,
                exclude_name_patterns=[]
                if args.include_suspect_schools
                else DEFAULT_EXCLUDE_PATTERNS,
                strict_target_quality=not args.no_strict_target_quality,
            )
        elif args.relaxation == "school_strength":
            gap_sets = await find_strength_relax_gap_sets(
                fetch_query,
                count=args.count,
                prov=args.province,
                strict_major=args.strict_major or None,
                score_min=args.score_min,
                score_max=args.score_max,
                score_step=args.score_step,
                candidates_per_score=args.candidates_per_score,
                max_volunteers_per_case=args.max_volunteers_per_case,
                max_volunteers_per_school=args.max_volunteers_per_school,
                include_special_majors=args.include_special_majors,
                max_major_name_length=args.max_major_name_length,
                exclude_name_patterns=[]
                if args.include_suspect_schools
                else DEFAULT_EXCLUDE_PATTERNS,
                strict_target_quality=not args.no_strict_target_quality,
            )
        elif args.relaxation == "major_quality":
            gap_sets = await find_major_quality_gap_sets(
                fetch_query,
                count=args.count,
                prov=args.province,
                strict_major=args.strict_major or None,
                score_min=args.score_min,
                score_max=args.score_max,
                score_step=args.score_step,
                candidates_per_score=args.candidates_per_score,
                max_volunteers_per_case=args.max_volunteers_per_case,
                max_volunteers_per_school=args.max_volunteers_per_school,
                include_special_majors=args.include_special_majors,
                max_major_name_length=args.max_major_name_length,
                exclude_name_patterns=[]
                if args.include_suspect_schools
                else DEFAULT_EXCLUDE_PATTERNS,
                strict_target_quality=not args.no_strict_target_quality,
                min_quality_gain=args.min_quality_gain,
            )
        elif args.relaxation == "tuition_value":
            gap_sets = await find_tuition_value_gap_sets(
                fetch_query,
                count=args.count,
                prov=args.province,
                strict_major=args.strict_major or None,
                budget=args.budget,
                budget_window=args.budget_window,
                relax_scope=args.tuition_relax_scope,
                score_min=args.score_min,
                score_max=args.score_max,
                score_step=args.score_step,
                candidates_per_score=args.candidates_per_score,
                max_volunteers_per_case=args.max_volunteers_per_case,
                max_volunteers_per_school=args.max_volunteers_per_school,
                include_special_majors=args.include_special_majors,
                max_major_name_length=args.max_major_name_length,
                exclude_name_patterns=[]
                if args.include_suspect_schools
                else DEFAULT_EXCLUDE_PATTERNS,
                strict_target_quality=not args.no_strict_target_quality,
            )
        elif args.relaxation == "employment_outcome":
            gap_sets = await find_employment_outcome_gap_sets(
                fetch_query,
                count=args.count,
                prov=args.province,
                strict_major=args.strict_major or None,
                score_min=args.score_min,
                score_max=args.score_max,
                score_step=args.score_step,
                candidates_per_score=args.candidates_per_score,
                max_volunteers_per_case=args.max_volunteers_per_case,
                max_volunteers_per_school=args.max_volunteers_per_school,
                include_special_majors=args.include_special_majors,
                max_major_name_length=args.max_major_name_length,
                exclude_name_patterns=[]
                if args.include_suspect_schools
                else DEFAULT_EXCLUDE_PATTERNS,
                strict_target_quality=not args.no_strict_target_quality,
                min_outcome_gain=args.min_outcome_gain,
            )
        elif args.relaxation == "region_tree":
            gap_sets = await find_region_tree_relax_gap_sets(
                fetch_query,
                count=args.count,
                prov=args.province,
                city=args.city,
                strict_major=args.strict_major or None,
                score_min=args.score_min,
                score_max=args.score_max,
                score_step=args.score_step,
                candidates_per_score=args.candidates_per_score,
                max_volunteers_per_case=args.max_volunteers_per_case,
                max_volunteers_per_school=args.max_volunteers_per_school,
                include_special_majors=args.include_special_majors,
                max_major_name_length=args.max_major_name_length,
                exclude_name_patterns=[]
                if args.include_suspect_schools
                else DEFAULT_EXCLUDE_PATTERNS,
                strict_target_quality=not args.no_strict_target_quality,
            )
        elif args.relaxation == "major_hierarchy":
            try:
                neighbor_clusters = await _probe_neighbor_clusters(args)
                stages = build_relaxation_stages(
                    args.strict_major,
                    source_node_id=args.source_major_cluster,
                    path=args.major_tree,
                    neighbor_node_ids=neighbor_clusters,
                    neighbor_limit=args.neighbor_count,
                    neighbor_category_level=args.neighbor_category_level,
                    skip_ancestor_category=True,
                    include_any_major_stage=True,
                    filter_observed_patterns=True,
                    max_observed_name_length=args.max_major_name_length,
                    exclude_special_observed=not args.include_special_majors,
                )
            except UnknownMajorError as exc:
                raise ValueError(
                    f"Cannot resolve strict major '{args.strict_major}'. "
                    f"Suggestions: {', '.join(exc.suggestions) or 'none'}"
                ) from exc
            gap_sets = await find_hierarchical_major_relax_gap_sets(
                fetch_query,
                count=args.count,
                prov=args.province,
                strict_major=args.strict_major,
                relaxation_stages=stages,
                score_min=args.score_min,
                score_max=args.score_max,
                score_step=args.score_step,
                candidates_per_score=args.candidates_per_score,
                recommendation_threshold=args.recommendation_threshold,
                max_volunteers_per_case=args.max_volunteers_per_case,
                max_volunteers_per_school=args.max_volunteers_per_school,
                include_special_majors=args.include_special_majors,
                max_major_name_length=args.max_major_name_length,
                relax_scope=args.major_relax_scope,
                exclude_name_patterns=[]
                if args.include_suspect_schools
                else DEFAULT_EXCLUDE_PATTERNS,
                strict_target_quality=not args.no_strict_target_quality,
            )
        elif args.relaxation == "risk_band":
            gap_sets = await find_risk_band_gap_sets(
                fetch_query,
                count=args.count,
                prov=args.province,
                strict_major=args.strict_major,
                score_min=args.score_min,
                score_max=args.score_max,
                score_step=args.score_step,
                candidates_per_score=args.candidates_per_score,
                max_volunteers_per_case=args.max_volunteers_per_case,
                max_volunteers_per_school=args.max_volunteers_per_school,
                strict_target_quality=not args.no_strict_target_quality,
            )
        else:
            relaxation_kind = (
                "clinical_to_medtech"
                if args.relaxation == "major_clinical_to_medtech"
                else "any_major"
            )
            target_major_patterns = None
            exclude_major_patterns = None
            if relaxation_kind == "clinical_to_medtech":
                target_major_patterns, exclude_major_patterns = (
                    get_major_cluster_patterns(args.target_major_clusters)
                )
            gap_sets = await find_major_relax_gap_sets(
                fetch_query,
                count=args.count,
                prov=args.province,
                strict_major=args.strict_major,
                relaxation_kind=relaxation_kind,
                target_major_patterns=target_major_patterns,
                exclude_major_patterns=exclude_major_patterns,
                relax_scope=args.major_relax_scope,
                score_min=args.score_min,
                score_max=args.score_max,
                score_step=args.score_step,
                candidates_per_score=args.candidates_per_score,
                max_volunteers_per_case=args.max_volunteers_per_case,
                max_volunteers_per_school=args.max_volunteers_per_school,
                include_special_majors=args.include_special_majors,
                max_major_name_length=args.max_major_name_length,
                exclude_name_patterns=[]
                if args.include_suspect_schools
                else DEFAULT_EXCLUDE_PATTERNS,
                strict_target_quality=not args.no_strict_target_quality,
            )
        personas = [
            build_deterministic_persona_from_gap_set(gap_set, i + 1)
            for i, gap_set in enumerate(gap_sets)
        ]
    elif args.mode == "template":
        gaps = await find_many_pareto_gaps(
            fetch_query,
            count=args.count,
            prov=args.province,
            score_min=args.score_min,
            score_max=args.score_max,
            score_step=args.score_step,
            candidates_per_score=args.candidates_per_score,
            unique_by=args.unique_by,
            exclude_name_patterns=[]
            if args.include_suspect_schools
            else DEFAULT_EXCLUDE_PATTERNS,
            strict_target_quality=not args.no_strict_target_quality,
        )
        personas = [
            build_deterministic_persona(gap, i + 1) for i, gap in enumerate(gaps)
        ]
    else:
        from app.core.llm_client import get_chat_model

        gaps = await find_many_pareto_gaps(
            fetch_query,
            count=args.count,
            prov=args.province,
            score_min=args.score_min,
            score_max=args.score_max,
            score_step=args.score_step,
            candidates_per_score=args.candidates_per_score,
            unique_by=args.unique_by,
            exclude_name_patterns=[]
            if args.include_suspect_schools
            else DEFAULT_EXCLUDE_PATTERNS,
            strict_target_quality=not args.no_strict_target_quality,
        )
        llm_client = get_chat_model()
        for gap in gaps:
            personas.append(await synthesize_persona(gap, llm_client))

    await close_pool()
    return personas


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate IcebergPersona JSON from real PostgreSQL Pareto gaps."
    )
    parser.add_argument(
        "--count", type=int, default=10, help="Number of personas to generate."
    )
    parser.add_argument("--province", default="浙江", help="Strict province red-line.")
    parser.add_argument(
        "--city",
        default="杭州",
        help="Strict city red-line used by --relaxation city.",
    )
    parser.add_argument(
        "--score-min", type=int, default=520, help="Minimum score to scan."
    )
    parser.add_argument(
        "--score-max", type=int, default=700, help="Maximum score to scan."
    )
    parser.add_argument(
        "--score-step", type=int, default=1, help="Score scan interval."
    )
    parser.add_argument(
        "--relaxation",
        choices=values(PersonaRelaxation),
        default="province",
        help="Constraint relaxation axis used to build volunteer-set personas.",
    )
    parser.add_argument(
        "--strict-major",
        default="临床医学",
        help="Original hard major constraint for major relaxation.",
    )
    parser.add_argument(
        "--budget",
        type=int,
        default=6000,
        help="Annual tuition budget used by --relaxation tuition_value.",
    )
    parser.add_argument(
        "--budget-window",
        type=int,
        default=10000,
        help="Maximum annual tuition increase allowed by tuition-value relaxation.",
    )
    parser.add_argument(
        "--tuition-relax-scope",
        choices=values(MajorRelaxScope),
        default="national",
        help="Whether tuition-value personas keep province or search nationally.",
    )
    parser.add_argument(
        "--min-quality-gain",
        type=int,
        default=10,
        help="Minimum quality-score gain used by --relaxation major_quality.",
    )
    parser.add_argument(
        "--min-outcome-gain",
        type=int,
        default=10,
        help="Minimum outcome-score gain used by --relaxation employment_outcome.",
    )
    parser.add_argument(
        "--target-major-clusters",
        nargs="+",
        default=["medical_technology"],
        help="Major cluster IDs used as the relaxed target set for cluster-based major relaxation.",
    )
    parser.add_argument(
        "--source-major-cluster",
        default=None,
        help="Optional explicit source tree node. If omitted, strict-major is resolved automatically.",
    )
    parser.add_argument(
        "--major-tree",
        default=DEFAULT_MAJOR_TREE,
        help="Major tree JSON used by --relaxation major_hierarchy.",
    )
    parser.add_argument(
        "--neighbor-clusters",
        nargs="+",
        default=None,
        help="Optional explicit Stage 4 neighbor cluster IDs; bypasses probe inference.",
    )
    parser.add_argument(
        "--neighbor-count",
        type=int,
        default=3,
        help="Number of probe-neighbor level-1 categories to keep for Stage 4.",
    )
    parser.add_argument(
        "--neighbor-category-level",
        type=int,
        default=1,
        help="Major-tree level used to group probe predictions into Stage 4 neighbor categories.",
    )
    parser.add_argument(
        "--neighbor-probe",
        default=DEFAULT_NEIGHBOR_PROBE,
        help="Probe checkpoint used to infer Stage 4 neighbor clusters.",
    )
    parser.add_argument(
        "--neighbor-label-map",
        default=DEFAULT_NEIGHBOR_LABEL_MAP,
        help="Probe label map JSON used to infer Stage 4 neighbor clusters.",
    )
    parser.add_argument(
        "--no-probe-neighbors",
        dest="use_probe_neighbors",
        action="store_false",
        help="Disable probe-inferred Stage 4 neighbors for --relaxation major_hierarchy.",
    )
    parser.set_defaults(use_probe_neighbors=True)
    parser.add_argument(
        "--major-relax-scope",
        choices=values(MajorRelaxScope),
        default="province",
        help="Whether major relaxation keeps the original province or searches nationally.",
    )
    parser.add_argument(
        "--candidates-per-score",
        type=int,
        default=20,
        help="Number of relaxed candidates inspected per score.",
    )
    parser.add_argument(
        "--unique-by",
        choices=values(DedupKeyMode),
        default="school_pair",
        help="Deduplicate generated gaps by school pair, school+major pair, or score slice.",
    )
    parser.add_argument(
        "--persona-shape",
        choices=values(PersonaShape),
        default="volunteer_set",
        help="Generate personas with a volunteer set or the legacy single-school gap shape.",
    )
    parser.add_argument(
        "--max-volunteers-per-case",
        type=int,
        default=None,
        help="Optional cap for volunteers inside each generated case; omitted means as complete as the candidate scan allows.",
    )
    parser.add_argument(
        "--max-volunteers-per-school",
        type=int,
        default=2,
        help="Maximum volunteers kept per school in each generated major-relaxation case.",
    )
    parser.add_argument(
        "--recommendation-threshold",
        type=int,
        default=None,
        help="Minimum recommendations required before accepting a hierarchical relaxation stage.",
    )
    parser.add_argument(
        "--min-volunteers-per-case",
        type=int,
        default=None,
        help="Deprecated alias for --recommendation-threshold.",
    )
    parser.add_argument(
        "--include-suspect-schools",
        action="store_true",
        help="Do not exclude obvious independent/vocational-school name patterns.",
    )
    parser.add_argument(
        "--include-special-majors",
        action="store_true",
        help="Keep special/noisy major names such as cooperation programs, credit-transfer programs, or long admissions notes.",
    )
    parser.add_argument(
        "--max-major-name-length",
        type=int,
        default=60,
        help="Maximum major-name length kept by default quality filters.",
    )
    parser.add_argument(
        "--no-strict-target-quality",
        action="store_true",
        help="Allow relaxed target schools that do not look like high-tier undergraduate universities.",
    )
    parser.add_argument("--output", default=DEFAULT_OUTPUT, help="Output JSON path.")
    parser.add_argument(
        "--mode",
        choices=values(PersonaSynthesisMode),
        default="template",
        help="template uses deterministic persona text; llm calls the configured LLM.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    if os.name == "nt":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    args = parse_args(argv or sys.argv[1:])
    if args.neighbor_count < 1:
        raise ValueError("--neighbor-count must be at least 1")
    if (
        args.max_volunteers_per_school is not None
        and args.max_volunteers_per_school < 1
    ):
        raise ValueError("--max-volunteers-per-school must be at least 1")
    if args.max_major_name_length is not None and args.max_major_name_length < 1:
        raise ValueError("--max-major-name-length must be at least 1")
    if args.budget < 0:
        raise ValueError("--budget must be non-negative")
    if args.budget_window < 1:
        raise ValueError("--budget-window must be at least 1")
    if args.recommendation_threshold is None:
        if args.min_volunteers_per_case is not None:
            args.recommendation_threshold = args.min_volunteers_per_case
        elif args.relaxation == "major_hierarchy":
            args.recommendation_threshold = 10
        else:
            args.recommendation_threshold = 1
    personas = asyncio.run(_generate(args))

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(
            [persona.model_dump() for persona in personas], ensure_ascii=False, indent=2
        ),
        encoding="utf-8",
    )

    print(f"Wrote {len(personas)} personas to {output_path}")
    for persona in personas:
        print(persona.case_id)
    if len(personas) < args.count:
        print(
            f"Warning: requested {args.count}, found {len(personas)} real gaps in scan range.",
            file=sys.stderr,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
