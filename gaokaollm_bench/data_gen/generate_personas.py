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
    find_hierarchical_major_relax_gap_sets,
    find_major_relax_gap_sets,
    find_many_pareto_gaps,
    find_pareto_gap_sets,
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
    "专科学校",
    "独立学院",
    "京江学院",
    "杏林学院",
    "嘉华学院",
    "滇池学院",
    "江淮学院",
    "皖江学院",
    "张家界学院",
]


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
    return {
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

    if relaxed_constraint == "major":
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
            "subjects": ["物理", "化学", "生物"],
            "preferred_major": strict_major
            if relaxed_constraint == "major"
            else major_name,
            "baseline_school": tier_a_name,
            "baseline_major": tier_a.get("major_name"),
            "baseline_tier": tier_a.get("tier"),
            "baseline_label": tier_a_label,
            "volunteer_count": len(volunteers),
            "max_gap_tier": max(item["tier"] for item in volunteers),
            "max_tier_delta": gap_set["max_tier_delta"],
            "constraint_relaxed": relaxed_constraint,
            "relaxation_kind": relaxation_kind,
            "stage_relaxation_kind": stage_relaxation_kind,
            "relax_scope": relax_scope,
            "relaxation_stage": relaxation_stage,
            "relaxation_stage_label": gap_set.get("relaxation_stage_label"),
            "target_major_clusters": target_major_clusters,
            "target_major_categories": gap_set.get("target_major_categories"),
            "psychological_distance": gap_set.get("psychological_distance"),
            "years_used": gap_set.get("years_used"),
            "stage_attempts": gap_set.get("stage_attempts"),
        },
        explicit_red_lines=explicit_red_lines,
        implicit_flexibilities={
            "trigger_type": "volunteer_set",
            "constraint_relaxed": relaxed_constraint,
            "relaxation_kind": relaxation_kind,
            "stage_relaxation_kind": stage_relaxation_kind,
            "relax_scope": relax_scope,
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
            "tier_labels": best_labels,
            "compromise": compromise,
        },
        initial_utterance=initial_utterance,
        process_milestones=milestones,
    )


async def _generate(args: argparse.Namespace) -> list[IcebergPersona]:
    from app.core.db_pg import close_pool, fetch_query

    personas: list[IcebergPersona] = []
    if args.persona_shape == "volunteer_set":
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
