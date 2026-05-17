"""Build constraint-ladder diagnostic personas from fresh DB scans."""

from __future__ import annotations

import argparse
import asyncio
import csv
import json
import os
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from app.core import db_pg
from gaokaollm_bench.data_gen.db_seeder import (
    BASE_ORDER,
    BASE_SELECT,
    _annotate_risk_candidate,
    _fetch,
    _student_rank_for_score,
    _tier,
    find_employment_outcome_gap_candidates,
    find_major_quality_gap_candidates,
    find_major_relax_gap_candidates,
    find_pareto_gap_candidates,
    find_tuition_value_gap_candidates,
)
from gaokaollm_bench.data_gen.generate_personas import (
    DEFAULT_EXCLUDE_PATTERNS,
    _school_label,
    _volunteer_entry,
)
from gaokaollm_bench.schemas import IcebergPersona


SAMPLE_DATA_DIR = Path("gaokaollm_bench/sample_data")
OUTPUTS_DIR = Path("gaokaollm_bench/outputs")
DEFAULT_OUTPUT = SAMPLE_DATA_DIR / "iceberg_personas_1constrain_real_db_30.json"
DEFAULT_AUDIT_CSV = OUTPUTS_DIR / "one_constraint_persona_audit.csv"
DEFAULT_AUDIT_JSON = OUTPUTS_DIR / "one_constraint_persona_audit.json"
DEFAULT_AUDIT_MD = OUTPUTS_DIR / "one_constraint_persona_audit.md"
DEFAULT_OUTPUTS = {
    1: DEFAULT_OUTPUT,
    2: SAMPLE_DATA_DIR / "iceberg_personas_2constrain_real_db_30.json",
    3: SAMPLE_DATA_DIR / "iceberg_personas_3constrain_real_db_30.json",
    4: SAMPLE_DATA_DIR / "iceberg_personas_4constrain_real_db_30.json",
    5: SAMPLE_DATA_DIR / "iceberg_personas_5constrain_real_db_30.json",
    6: SAMPLE_DATA_DIR / "iceberg_personas_6constrain_real_db_30.json",
}
DEFAULT_AUDIT_CSVS = {
    1: DEFAULT_AUDIT_CSV,
    2: OUTPUTS_DIR / "two_constraint_persona_audit.csv",
    3: OUTPUTS_DIR / "three_constraint_persona_audit.csv",
    4: OUTPUTS_DIR / "four_constraint_persona_audit.csv",
    5: OUTPUTS_DIR / "five_constraint_persona_audit.csv",
    6: OUTPUTS_DIR / "six_constraint_persona_audit.csv",
}
DEFAULT_AUDIT_JSONS = {
    1: DEFAULT_AUDIT_JSON,
    2: OUTPUTS_DIR / "two_constraint_persona_audit.json",
    3: OUTPUTS_DIR / "three_constraint_persona_audit.json",
    4: OUTPUTS_DIR / "four_constraint_persona_audit.json",
    5: OUTPUTS_DIR / "five_constraint_persona_audit.json",
    6: OUTPUTS_DIR / "six_constraint_persona_audit.json",
}
DEFAULT_AUDIT_MDS = {
    1: DEFAULT_AUDIT_MD,
    2: OUTPUTS_DIR / "two_constraint_persona_audit.md",
    3: OUTPUTS_DIR / "three_constraint_persona_audit.md",
    4: OUTPUTS_DIR / "four_constraint_persona_audit.md",
    5: OUTPUTS_DIR / "five_constraint_persona_audit.md",
    6: OUTPUTS_DIR / "six_constraint_persona_audit.md",
}

SUBJECTS = ["物理", "化学", "生物"]
BANDS: tuple[tuple[str, int, int], ...] = (
    ("520-549", 520, 549),
    ("550-579", 550, 579),
    ("580-609", 580, 609),
    ("610-639", 610, 639),
    ("640-680", 640, 680),
)
SPECIAL_MAJOR_TERMS = (
    "中外合作",
    "合作办学",
    "学分互认",
    "国际班",
    "国际贸易班",
    "外语成绩",
    "不低于",
    "留学",
    "双文凭",
)
MAJOR_NOISE_MARKERS = (
    "(",
    "（",
    "校区",
    "启用前",
    "过渡办学",
    "国际",
    "5+3",
    "实验班",
)


@dataclass(frozen=True)
class AxisSpec:
    axis: str
    constraint_relaxed: str
    preference_axis: str
    benefit_axis: str
    redline_key: str
    finder: str


AXES: tuple[AxisSpec, ...] = (
    AxisSpec("geo_tier", "province", "geo", "school", "geo", "pareto_province"),
    AxisSpec("major_tier", "major", "major", "school", "major", "major_relax"),
    AxisSpec("risk_tier", "risk_tier", "school", "school", "risk", "single_risk"),
    AxisSpec(
        "tuition_value",
        "tuition_value",
        "tuition",
        "school",
        "tuition",
        "tuition_value",
    ),
    AxisSpec(
        "major_quality",
        "major_quality",
        "quality",
        "quality",
        "quality",
        "major_quality",
    ),
    AxisSpec(
        "employment_outcome",
        "employment_outcome",
        "quality",
        "employment",
        "employment",
        "employment_outcome",
    ),
)

QUALITY_NAME_SELECT = """
SELECT
    a.year,
    a.school_id,
    s.name AS school_name,
    s.province AS school_province,
    s.city AS school_city,
    s.is_985,
    s.is_211,
    s.is_double_first_class,
    s.education_level,
    s.ranking,
    a.major_id,
    a.major_name_raw AS major_name,
    a.min_score,
    a.min_rank,
    mq.quality_score,
    mq.quality_tier,
    mq.best_major_rank,
    mq.best_rating,
    mq.has_key_major,
    mq.has_featured_major,
    mq.satisfaction_score,
    mq.vote_count AS satisfaction_vote_count,
    mq.evidence_sources AS quality_evidence_sources,
    CASE
        WHEN s.is_985 THEN 4
        WHEN s.is_211 OR s.is_double_first_class THEN 3
        WHEN s.education_level = '本科' THEN 2
        ELSE 1
    END AS tier
FROM admission_scores a
JOIN schools s ON s.id = a.school_id
LEFT JOIN LATERAL (
    SELECT
        profile.quality_score,
        profile.quality_tier,
        profile.best_major_rank,
        profile.best_rating,
        profile.has_key_major,
        profile.has_featured_major,
        profile.satisfaction_score,
        profile.vote_count,
        profile.evidence_sources
    FROM school_major_quality_profiles profile
    WHERE profile.school_id = a.school_id
      AND (
          profile.major_id = a.major_id
          OR profile.major_name = trim(replace(a.major_name_raw, '专业', ''))
          OR a.major_name_raw LIKE ('%%' || profile.major_name || '%%')
      )
    ORDER BY
        CASE
            WHEN profile.major_id = a.major_id THEN 0
            WHEN profile.major_name = trim(replace(a.major_name_raw, '专业', '')) THEN 1
            ELSE 2
        END,
        profile.quality_score DESC,
        profile.best_major_rank ASC NULLS LAST
    LIMIT 1
) mq ON true
WHERE a.min_score IS NOT NULL
  AND a.min_score <= %s
"""


class DbPool:
    async def fetch(self, query: str, *params: Any) -> list[dict[str, Any]]:
        return await db_pg.fetch_query(query, *params)


@dataclass
class Candidate:
    axis: str
    requested_band: str
    source_band: str
    score: int
    gap: dict[str, Any]
    finder: str


@dataclass
class SelectionState:
    seen_options: set[tuple[Any, Any, str]]
    school_axis_counts: dict[tuple[Any, str], int]
    school_total_counts: dict[Any, int]

    @classmethod
    def create(cls) -> "SelectionState":
        return cls(set(), defaultdict(int), defaultdict(int))


def _band_order(requested_band: str) -> list[tuple[str, int, int]]:
    labels = [label for label, _, _ in BANDS]
    index = labels.index(requested_band)
    return sorted(
        BANDS,
        key=lambda item: (abs(labels.index(item[0]) - index), labels.index(item[0])),
    )


def _bad_major_name(major_name: Any, max_major_name_length: int) -> bool:
    text = str(major_name or "")
    if not text:
        return True
    if len(text) > max_major_name_length:
        return True
    return any(term in text for term in SPECIAL_MAJOR_TERMS) or any(
        marker in text for marker in MAJOR_NOISE_MARKERS
    )


def _ranking_gain(tier_a: dict[str, Any], tier_b: dict[str, Any]) -> int:
    try:
        baseline = int(float(tier_a.get("ranking")))
        target = int(float(tier_b.get("ranking")))
    except (TypeError, ValueError):
        return 0
    return max(0, baseline - target)


def _required_candidate_fields(row: dict[str, Any]) -> bool:
    return bool(
        row.get("school_name")
        and row.get("major_name")
        and row.get("year")
        and row.get("min_score") is not None
    )


def _passes_axis_threshold(axis: str, gap: dict[str, Any]) -> bool:
    tier_a = gap.get("tier_a") or {}
    tier_b = gap.get("tier_b") or {}
    tier_delta = int(gap.get("tier_delta") or (_tier(tier_b) - _tier(tier_a)))
    ranking_gain = int(gap.get("ranking_gain") or _ranking_gain(tier_a, tier_b))
    if axis in {"geo_tier", "major_tier", "risk_tier"}:
        if axis == "risk_tier":
            return tier_delta >= 1 or ranking_gain >= 50
        return tier_delta >= 1
    if axis == "tuition_value":
        tuition_delta = int(
            float(gap.get("tuition_delta") or tier_b.get("tuition_delta") or 0)
        )
        return 0 < tuition_delta <= 10000 and (tier_delta >= 1 or ranking_gain >= 50)
    if axis == "major_quality":
        gain = float(gap.get("quality_gain") or tier_b.get("quality_gain") or 0)
        return gain >= 10
    if axis == "employment_outcome":
        gain = float(gap.get("outcome_gain") or tier_b.get("outcome_gain") or 0)
        return gain >= 15
    return False


def _candidate_sort_key(candidate: Candidate) -> tuple[Any, ...]:
    gap = candidate.gap
    tier_a = gap.get("tier_a") or {}
    tier_b = gap.get("tier_b") or {}
    tier_delta = int(gap.get("tier_delta") or (_tier(tier_b) - _tier(tier_a)))
    ranking_gain = int(gap.get("ranking_gain") or _ranking_gain(tier_a, tier_b))
    if candidate.axis == "major_quality":
        primary = float(gap.get("quality_gain") or tier_b.get("quality_gain") or 0)
    elif candidate.axis == "employment_outcome":
        primary = float(gap.get("outcome_gain") or tier_b.get("outcome_gain") or 0)
    elif candidate.axis == "tuition_value":
        primary = int(
            gap.get("ranking_gain") or tier_b.get("ranking_gain") or ranking_gain
        )
    elif candidate.axis == "risk_tier":
        margin = tier_b.get("score_margin")
        primary = -abs(float(margin)) if margin is not None else -999
    else:
        primary = tier_delta
    ranking = tier_b.get("ranking")
    return (
        -tier_delta,
        -primary,
        int(ranking) if ranking is not None else 999999,
        -int(tier_b.get("year") or 0),
        str(tier_b.get("school_name") or ""),
    )


def _reject_reason(
    candidate: Candidate, state: SelectionState, max_major_name_length: int
) -> str | None:
    row = candidate.gap.get("tier_b") or {}
    if not _required_candidate_fields(row):
        return "missing_required_fields"
    if _bad_major_name(row.get("major_name"), max_major_name_length):
        return "special_or_long_major"
    if not _passes_axis_threshold(candidate.axis, candidate.gap):
        return "below_axis_threshold"

    school_key = row.get("school_id") or row.get("school_name")
    option_key = (
        school_key,
        row.get("major_id") or row.get("major_name"),
        candidate.axis,
    )
    if option_key in state.seen_options:
        return "duplicate_school_major_axis"
    if state.school_axis_counts[(school_key, candidate.axis)] >= 2:
        return "school_axis_cap"
    if state.school_total_counts[school_key] >= 4:
        return "school_total_cap"
    return None


def _accept(candidate: Candidate, state: SelectionState) -> None:
    row = candidate.gap["tier_b"]
    school_key = row.get("school_id") or row.get("school_name")
    option_key = (
        school_key,
        row.get("major_id") or row.get("major_name"),
        candidate.axis,
    )
    state.seen_options.add(option_key)
    state.school_axis_counts[(school_key, candidate.axis)] += 1
    state.school_total_counts[school_key] += 1


def _with_bands(
    candidate: Candidate, *, requested_band: str, source_band: str
) -> Candidate:
    return Candidate(
        axis=candidate.axis,
        requested_band=requested_band,
        source_band=source_band,
        score=candidate.score,
        gap=candidate.gap,
        finder=candidate.finder,
    )


async def _axis_candidates(
    db_pool: Any,
    spec: AxisSpec,
    *,
    band: tuple[str, int, int],
    args: argparse.Namespace,
) -> list[Candidate]:
    label, start, end = band
    candidates: list[Candidate] = []
    for score in range(start, end + 1, args.score_step):
        raw = await _raw_axis_candidates(db_pool, spec, score=score, args=args)
        for gap in raw:
            candidates.append(
                Candidate(
                    axis=spec.axis,
                    requested_band=label,
                    source_band=label,
                    score=score,
                    gap=gap,
                    finder=spec.finder,
                )
            )
    return sorted(candidates, key=_candidate_sort_key)


async def _raw_axis_candidates(
    db_pool: Any,
    spec: AxisSpec,
    *,
    score: int,
    args: argparse.Namespace,
) -> list[dict[str, Any]]:
    exclude_patterns = [] if args.include_suspect_schools else DEFAULT_EXCLUDE_PATTERNS
    strict_target_quality = not args.no_strict_target_quality
    if spec.axis == "geo_tier":
        return await find_pareto_gap_candidates(
            db_pool,
            score,
            args.province,
            limit=args.candidates_per_score,
            exclude_name_patterns=exclude_patterns,
            strict_target_quality=strict_target_quality,
        )
    if spec.axis == "major_tier":
        return await find_major_relax_gap_candidates(
            db_pool,
            score,
            args.province,
            strict_major=args.strict_major,
            relaxation_kind="clinical_to_medtech",
            relax_scope=args.major_relax_scope,
            limit=args.candidates_per_score,
            exclude_name_patterns=exclude_patterns,
            strict_target_quality=strict_target_quality,
        )
    if spec.axis == "risk_tier":
        return await find_single_risk_tier_candidates(
            db_pool,
            score,
            args.province,
            strict_major=args.strict_major,
            limit=args.candidates_per_score,
            exclude_name_patterns=exclude_patterns,
            strict_target_quality=strict_target_quality,
            max_score_margin=args.risk_max_score_margin,
        )
    if spec.axis == "tuition_value":
        return await find_tuition_value_gap_candidates(
            db_pool,
            score,
            args.province,
            strict_major=args.tuition_strict_major,
            budget=args.budget,
            budget_window=args.budget_window,
            relax_scope=args.tuition_relax_scope,
            limit=args.candidates_per_score,
            exclude_name_patterns=exclude_patterns,
            strict_target_quality=strict_target_quality,
        )
    if spec.axis == "major_quality":
        rows = await find_major_quality_gap_candidates(
            db_pool,
            score,
            args.province,
            strict_major=args.quality_strict_major,
            limit=args.candidates_per_score,
            exclude_name_patterns=exclude_patterns,
            strict_target_quality=strict_target_quality,
            min_quality_gain=args.min_quality_gain,
        )
        if rows:
            return rows
        return await find_major_quality_name_gap_candidates(
            db_pool,
            score,
            args.province,
            strict_major=args.quality_strict_major,
            limit=args.candidates_per_score,
            exclude_name_patterns=exclude_patterns,
            strict_target_quality=strict_target_quality,
            min_quality_gain=args.min_quality_gain,
        )
    if spec.axis == "employment_outcome":
        return await find_employment_outcome_gap_candidates(
            db_pool,
            score,
            args.province,
            strict_major=args.employment_strict_major,
            limit=args.candidates_per_score,
            exclude_name_patterns=exclude_patterns,
            strict_target_quality=strict_target_quality,
            min_outcome_gain=args.min_outcome_gain,
        )
    raise ValueError(f"unsupported axis: {spec.axis}")


async def find_major_quality_name_gap_candidates(
    db_pool: Any,
    score: int,
    prov: str,
    *,
    strict_major: str | None,
    limit: int,
    exclude_name_patterns: list[str] | None,
    strict_target_quality: bool,
    min_quality_gain: int,
) -> list[dict[str, Any]]:
    major_clause = "  AND a.major_name_raw LIKE %s\n" if strict_major else ""
    major_params = [f"%{strict_major}%"] if strict_major else []
    quality_clause = ""
    quality_params: list[Any] = []
    if strict_target_quality:
        quality_clause = (
            "  AND (s.name LIKE %s OR s.name LIKE %s)\n"
            "  AND NOT (s.name LIKE %s AND s.name NOT LIKE %s)\n"
        )
        quality_params = ["%大学%", "%医学院%", "%大学%学院%", "%医学院%"]

    exclude_clauses = []
    exclude_params: list[Any] = []
    for pattern in exclude_name_patterns or []:
        exclude_clauses.append("s.name NOT LIKE %s")
        exclude_params.append(f"%{pattern}%")

    baseline_query = (
        f"{QUALITY_NAME_SELECT}"
        "  AND s.province = %s\n"
        f"{major_clause}"
        "  AND mq.quality_score IS NOT NULL\n"
        f"{quality_clause}"
        f"{'  AND ' + ' AND '.join(exclude_clauses) if exclude_clauses else ''}\n"
        "ORDER BY\n"
        "    tier DESC,\n"
        "    s.ranking ASC NULLS LAST,\n"
        "    a.min_score DESC NULLS LAST,\n"
        "    mq.quality_score DESC NULLS LAST,\n"
        "    mq.best_major_rank ASC NULLS LAST,\n"
        "    a.year DESC,\n"
        "    s.name ASC,\n"
        "    a.major_name_raw ASC\n"
        "LIMIT %s"
    )
    baseline_rows = await _fetch(
        db_pool,
        baseline_query,
        [score, prov, *major_params, *quality_params, *exclude_params, 40],
    )
    if not baseline_rows:
        return []

    candidates: list[dict[str, Any]] = []
    for tier_a in baseline_rows:
        if tier_a.get("quality_score") is None:
            continue
        anchor_score = float(tier_a["quality_score"])
        relaxed_query = (
            f"{QUALITY_NAME_SELECT}"
            f"{major_clause}"
            "  AND s.province <> %s\n"
            "  AND s.education_level = '本科'\n"
            "  AND mq.quality_score IS NOT NULL\n"
            "  AND mq.quality_score >= %s\n"
            f"{quality_clause}"
            f"{'  AND ' + ' AND '.join(exclude_clauses) if exclude_clauses else ''}\n"
            "ORDER BY\n"
            "    mq.quality_score DESC NULLS LAST,\n"
            "    mq.best_major_rank ASC NULLS LAST,\n"
            "    tier DESC,\n"
            "    s.ranking ASC NULLS LAST,\n"
            "    a.min_score DESC NULLS LAST,\n"
            "    a.year DESC,\n"
            "    s.name ASC,\n"
            "    a.major_name_raw ASC\n"
            "LIMIT %s"
        )
        relaxed_rows = await _fetch(
            db_pool,
            relaxed_query,
            [
                score,
                *major_params,
                prov,
                anchor_score + min_quality_gain,
                *quality_params,
                *exclude_params,
                limit,
            ],
        )
        for tier_b in relaxed_rows:
            candidate_score = tier_b.get("quality_score")
            if candidate_score is None:
                continue
            quality_gain = float(candidate_score) - anchor_score
            if quality_gain < min_quality_gain:
                continue
            tier_b = dict(tier_b)
            tier_b["quality_score"] = round(float(candidate_score), 3)
            tier_b["quality_anchor_score"] = round(anchor_score, 3)
            tier_b["quality_gain"] = round(quality_gain, 3)
            tier_b["quality_anchor_school"] = tier_a.get("school_name")
            tier_b["quality_anchor_major"] = tier_a.get("major_name")
            candidates.append(
                {
                    "score": score,
                    "province": prov,
                    "constraint_relaxed": "major_quality",
                    "relaxation_kind": "major_quality_name_fallback",
                    "relax_scope": "national",
                    "strict_major": strict_major,
                    "quality_anchor_score": round(anchor_score, 3),
                    "tier_a": tier_a,
                    "tier_b": tier_b,
                    "tier_delta": _tier(tier_b) - _tier(tier_a),
                    "quality_gain": round(quality_gain, 3),
                }
            )
        if candidates:
            break
    return candidates


async def find_single_risk_tier_candidates(
    db_pool: Any,
    score: int,
    prov: str,
    *,
    strict_major: str,
    limit: int,
    exclude_name_patterns: list[str] | None,
    strict_target_quality: bool,
    max_score_margin: int,
) -> list[dict[str, Any]]:
    quality_clause = ""
    quality_params: list[Any] = []
    if strict_target_quality:
        quality_clause = (
            "  AND s.education_level = '本科'\n"
            "  AND (s.name LIKE %s OR s.name LIKE %s)\n"
            "  AND NOT (s.name LIKE %s AND s.name NOT LIKE %s)\n"
        )
        quality_params = ["%大学%", "%医学院%", "%大学%学院%", "%医学院%"]

    exclude_clauses = []
    exclude_params: list[Any] = []
    for pattern in exclude_name_patterns or []:
        exclude_clauses.append("s.name NOT LIKE %s")
        exclude_params.append(f"%{pattern}%")

    query = (
        f"{BASE_SELECT}"
        "  AND s.province = %s\n"
        "  AND a.major_name_raw LIKE %s\n"
        f"{quality_clause}"
        f"{'  AND ' + ' AND '.join(exclude_clauses) if exclude_clauses else ''}\n"
        f"{BASE_ORDER}"
    )
    student_rank = await _student_rank_for_score(db_pool, score=score, prov=prov)
    rows = await _fetch(
        db_pool,
        query,
        [score, prov, f"%{strict_major}%", *quality_params, *exclude_params, limit],
    )
    annotated = [
        _annotate_risk_candidate(row, score=score, student_rank=student_rank)
        for row in rows
    ]
    conservative = [
        row for row in annotated if str(row.get("risk_level") or "") in {"bao", "dian"}
    ]
    targets = [
        row
        for row in annotated
        if str(row.get("risk_level") or "") in {"chong", "wen"}
        and row.get("score_margin") is not None
        and 0 <= int(float(row["score_margin"])) <= max_score_margin
    ]
    results: list[dict[str, Any]] = []
    for baseline in sorted(
        conservative, key=lambda row: (_tier(row), -int(row.get("ranking") or 0))
    ):
        for target in sorted(
            targets, key=lambda row: (-_tier(row), int(row.get("ranking") or 999999))
        ):
            if target.get("school_id") == baseline.get("school_id") and (
                target.get("major_id") == baseline.get("major_id")
                or target.get("major_name") == baseline.get("major_name")
            ):
                continue
            tier_delta = _tier(target) - _tier(baseline)
            ranking_gain = _ranking_gain(baseline, target)
            if tier_delta < 1 and ranking_gain < 50:
                continue
            enriched = dict(target)
            enriched["risk_tier_gain"] = max(tier_delta, 1 if ranking_gain >= 50 else 0)
            enriched["ranking_gain"] = ranking_gain
            results.append(
                {
                    "score": score,
                    "province": prov,
                    "constraint_relaxed": "risk_tier",
                    "relaxation_kind": "single_risk_tier",
                    "strict_major": strict_major,
                    "baseline_risk_preference": "conservative",
                    "student_rank": student_rank,
                    "tier_a": baseline,
                    "tier_b": enriched,
                    "tier_delta": tier_delta,
                    "ranking_gain": ranking_gain,
                }
            )
    return results


def _diagnostic_level(constraint_count: int) -> str:
    return f"{constraint_count}-constrain"


def _case_prefix(constraint_count: int) -> str:
    return {
        1: "one-constrain",
        2: "two-constrain",
        3: "three-constrain",
        4: "four-constrain",
        5: "five-constrain",
        6: "six-constrain",
    }[constraint_count]


def build_persona(
    spec: AxisSpec,
    candidate: Candidate,
    index: int,
    constraint_count: int,
) -> IcebergPersona:
    gap = candidate.gap
    tier_a = gap["tier_a"]
    tier_b = gap["tier_b"]
    volunteer = _volunteer_entry(tier_b, candidate.score)
    tier_a_label = _school_label(tier_a)
    tier_b_label = _school_label(tier_b)
    preferred_major = (
        gap.get("strict_major")
        or tier_b.get("major_name")
        or tier_a.get("major_name")
        or "目标专业"
    )
    tier_delta = int(gap.get("tier_delta") or (_tier(tier_b) - _tier(tier_a)))
    ranking_gain = int(gap.get("ranking_gain") or _ranking_gain(tier_a, tier_b))
    case_id = (
        f"{_case_prefix(constraint_count)}-{spec.axis}-{candidate.score}-{index:03d}"
    )

    background = {
        "score": candidate.score,
        "province": gap.get("province") or "浙江",
        "subjects": SUBJECTS,
        "preferred_major": preferred_major,
        "baseline_school": tier_a.get("school_name"),
        "baseline_major": tier_a.get("major_name"),
        "baseline_tier": tier_a.get("tier"),
        "baseline_label": tier_a_label,
        "baseline_ranking": tier_a.get("ranking"),
        "constraint_count": constraint_count,
        "diagnostic_level": _diagnostic_level(constraint_count),
        "diagnostic_axis": spec.axis,
        "relax_axis": spec.axis,
        "preference_axis": spec.preference_axis,
        "benefit_axis": spec.benefit_axis,
        "score_band": candidate.requested_band,
        "source_score_band": candidate.source_band,
        "borrowed_score_band": candidate.source_band != candidate.requested_band,
        "trigger_evidence_count": 1,
        "finder": candidate.finder,
        "target_tier_delta": tier_delta,
        "target_ranking_gain": ranking_gain,
    }

    flex = {
        "trigger_type": "single_verified_option",
        "constraint_relaxed": spec.constraint_relaxed,
        "diagnostic_axis": spec.axis,
        "preference_axis": spec.preference_axis,
        "benefit_axis": spec.benefit_axis,
        "trigger_condition": _trigger_condition(
            spec, gap, volunteer, tier_a_label, tier_b_label
        ),
        "volunteer_set": [volunteer],
        "minimum_required_volunteers": 1,
        "representative_schools": [volunteer["school_name"]],
        "tier_labels": [volunteer.get("tier_label")],
        "baseline_tier": tier_a.get("tier"),
        "baseline_label": tier_a_label,
        "compromise": _compromise(spec, gap, volunteer, tier_a_label, tier_b_label),
    }
    for key in (
        "quality_anchor_score",
        "quality_gain",
        "budget_anchor",
        "budget_window",
        "tuition_delta",
        "ranking_gain",
        "outcome_anchor_score",
        "outcome_gain",
        "student_rank",
        "baseline_risk_preference",
    ):
        value = gap.get(key) or tier_b.get(key)
        if value is not None:
            flex[key] = value

    red_lines = _explicit_red_lines(
        spec, gap, volunteer, preferred_major, constraint_count
    )
    initial_utterance = _initial_utterance_with_constraints(
        spec,
        gap,
        preferred_major,
        red_lines,
    )

    return IcebergPersona(
        case_id=case_id,
        background=background,
        explicit_red_lines=red_lines,
        implicit_flexibilities=flex,
        initial_utterance=initial_utterance,
        process_milestones=_milestones(spec, volunteer, red_lines),
    )


def _explicit_red_lines(
    spec: AxisSpec,
    gap: dict[str, Any],
    volunteer: dict[str, Any],
    preferred_major: str,
    constraint_count: int,
) -> dict[str, str]:
    red_lines = {spec.redline_key: _redline(spec, gap, preferred_major)}
    for key, value in _extra_redline_pool(spec, gap, volunteer, preferred_major):
        if len(red_lines) >= constraint_count:
            break
        if key not in red_lines:
            red_lines[key] = value
    if len(red_lines) != constraint_count:
        raise AssertionError(
            f"could not build {constraint_count} explicit red lines for {spec.axis}: {red_lines}"
        )
    return red_lines


def _extra_redline_pool(
    spec: AxisSpec,
    gap: dict[str, Any],
    volunteer: dict[str, Any],
    preferred_major: str,
) -> list[tuple[str, str]]:
    province = str(gap.get("province") or "浙江")
    target_major = str(volunteer.get("major_name") or preferred_major)
    tuition = volunteer.get("tuition")
    tuition_cap = int(float(tuition)) + 3000 if tuition is not None else 8000
    candidates = [
        ("risk", "必须能看到学校名、专业名和最低分证据，不接受没有分数依据的推荐"),
        (
            "major",
            f"专业方向至少要和{preferred_major}或{target_major}相关，不接受完全无关专业",
        ),
        (
            "geo",
            f"如果离开{province}，必须说明目标学校所在省份和真实收益，不接受只报学校名",
        ),
        ("tuition", f"学费最好不超过{tuition_cap}元/年，明显高收费项目不考虑"),
        ("quality", "需要说明学校层级、专业质量或排名证据，不接受泛泛说口碑好"),
        ("employment", "需要给出就业、行业或薪资去向证据，不接受只说就业不错"),
    ]
    return [(key, value) for key, value in candidates if key != spec.redline_key]


def _initial_utterance_with_constraints(
    spec: AxisSpec,
    gap: dict[str, Any],
    preferred_major: str,
    red_lines: dict[str, str],
) -> str:
    base = _initial_utterance(spec, gap, preferred_major)
    extras = [text for key, text in red_lines.items() if key != spec.redline_key]
    if not extras:
        return base
    return base.rstrip("。") + "；另外，" + "；".join(extras) + "。"


def _redline(spec: AxisSpec, gap: dict[str, Any], preferred_major: str) -> str:
    if spec.axis == "geo_tier":
        return "只考虑浙江，外省学校默认不看"
    if spec.axis == "major_tier":
        return f"只读{preferred_major}，其他相近专业先不看"
    if spec.axis == "risk_tier":
        return "只求稳妥，不接受没有最低分和位次证据的贴线方案"
    if spec.axis == "tuition_value":
        budget = int(gap.get("budget_anchor") or 6000)
        return f"每年学费预算不超过{budget}元"
    if spec.axis == "major_quality":
        return "必须有明确的专业实力、专业排名或学科评估证据"
    if spec.axis == "employment_outcome":
        return "必须有就业、薪资、行业或岗位去向证据"
    return "只接受有明确证据的方案"


def _initial_utterance(
    spec: AxisSpec, gap: dict[str, Any], preferred_major: str
) -> str:
    score = int(gap["score"])
    subjects = "、".join(SUBJECTS)
    if spec.axis == "geo_tier":
        return f"我{score}分，选考{subjects}，只想留在浙江，外省学校先别推荐。"
    if spec.axis == "major_tier":
        return f"我{score}分，选考{subjects}，只想读{preferred_major}，其他医学相关专业先别推荐。"
    if spec.axis == "risk_tier":
        return f"我{score}分，选考{subjects}，想读{preferred_major}，只求稳一点，不想冒太大风险。"
    if spec.axis == "tuition_value":
        budget = int(gap.get("budget_anchor") or 6000)
        return f"我{score}分，选考{subjects}，专业可以先宽一点，但每年学费最好别超过{budget}元。"
    if spec.axis == "major_quality":
        return f"我{score}分，选考{subjects}，更看重专业实力和质量证据，没有专业排名或学科评估证据的先别推荐。"
    if spec.axis == "employment_outcome":
        return f"我{score}分，选考{subjects}，更看重就业和薪资去向，没有真实就业证据的专业先别推荐。"
    return f"我{score}分，选考{subjects}，请只给有真实分数证据的方案。"


def _trigger_condition(
    spec: AxisSpec,
    gap: dict[str, Any],
    volunteer: dict[str, Any],
    tier_a_label: str,
    tier_b_label: str,
) -> str:
    score = int(gap["score"])
    school = volunteer["school_name"]
    major = volunteer["major_name"]
    min_score = volunteer["min_score"]
    base = (
        f"只要看到一个真实可达的候选：{school} {major}，年份{volunteer.get('year')}，"
        f"最低分{min_score}不高于本人{score}分，并给出学校名、专业名和最低分证据，就会认真考虑。"
    )
    if spec.axis == "geo_tier":
        return base + f" 该候选从{tier_a_label}提升到{tier_b_label}，可以触发出省妥协。"
    if spec.axis == "major_tier":
        return (
            base + f" 该候选通过相近专业换来{tier_b_label}层次，可以触发专业小类妥协。"
        )
    if spec.axis == "risk_tier":
        return (
            base
            + " 该候选需要同时说明 score_margin、min_rank 或 risk_level，才接受轻微冲刺。"
        )
    if spec.axis == "tuition_value":
        return base + " 该候选需要说明学费、超预算幅度和学校层级或排名收益。"
    if spec.axis == "major_quality":
        return (
            base
            + " 该候选需要说明 quality_score、quality_gain 或专业排名/学科评估证据。"
        )
    if spec.axis == "employment_outcome":
        return (
            base
            + " 该候选需要说明 outcome_score、outcome_gain、就业排名或薪资/行业证据。"
        )
    return base


def _compromise(
    spec: AxisSpec,
    gap: dict[str, Any],
    volunteer: dict[str, Any],
    tier_a_label: str,
    tier_b_label: str,
) -> str:
    if spec.axis == "geo_tier":
        return f"可以为了从{tier_a_label}跃迁到{tier_b_label}而放宽地域。"
    if spec.axis == "major_tier":
        return (
            f"可以为了更高学校层次，把专业从严格原专业放宽到{volunteer['major_name']}。"
        )
    if spec.axis == "risk_tier":
        return "可以接受一个证据清楚、最低分贴近但真实可达的更高层级候选。"
    if spec.axis == "tuition_value":
        return f"可以接受小幅超预算，换取层级或排名收益；本候选学费增量约{volunteer.get('tuition_delta')}元。"
    if spec.axis == "major_quality":
        return f"可以为了更强专业质量证据接受该候选，质量增益约{volunteer.get('quality_gain')}。"
    if spec.axis == "employment_outcome":
        return f"可以为了更强就业结果证据接受该候选，就业结果增益约{volunteer.get('outcome_gain')}。"
    return "可以为了真实可核验收益放宽单一显式红线。"


def _milestones(
    spec: AxisSpec,
    volunteer: dict[str, Any],
    red_lines: dict[str, str] | None = None,
) -> dict[str, Any]:
    milestones: dict[str, Any] = {
        "reject_generic_advice": True,
        "reject_unverified_option": True,
        "require_single_verified_option": True,
        "require_school_major_score_evidence": True,
        "require_option_advantage": True,
        "accept_after_verified_option": [volunteer["school_name"]],
    }
    if spec.axis == "risk_tier":
        milestones["require_risk_evidence"] = True
    elif spec.axis == "tuition_value":
        milestones["require_tuition_evidence"] = True
    elif spec.axis == "major_quality":
        milestones["require_major_quality_evidence"] = True
    elif spec.axis == "employment_outcome":
        milestones["require_employment_evidence"] = True
    if red_lines:
        milestones["explicit_red_line_keys"] = list(red_lines)
        milestones["preserve_non_relaxed_constraints"] = [
            key for key in red_lines if key != spec.redline_key
        ]
    return milestones


async def build_dataset(
    args: argparse.Namespace,
) -> tuple[list[IcebergPersona], list[dict[str, Any]], dict[str, Any]]:
    db_pool = DbPool()
    state = SelectionState.create()
    scan_cache: dict[tuple[str, str], list[Candidate]] = {}
    filter_stats: Counter[str] = Counter()
    selected: list[Candidate] = []
    personas: list[IcebergPersona] = []

    async def candidates_for(
        spec: AxisSpec, band: tuple[str, int, int]
    ) -> list[Candidate]:
        key = (spec.axis, band[0])
        if key not in scan_cache:
            scan_cache[key] = await _axis_candidates(
                db_pool, spec, band=band, args=args
            )
        return scan_cache[key]

    index = 1
    for spec in AXES:
        axis_selected = 0
        missing_bands: list[str] = []
        for requested in BANDS:
            picked: Candidate | None = None
            for source_band in _band_order(requested[0]):
                for candidate in await candidates_for(spec, source_band):
                    candidate = _with_bands(
                        candidate,
                        requested_band=requested[0],
                        source_band=source_band[0],
                    )
                    reason = _reject_reason(
                        candidate, state, args.max_major_name_length
                    )
                    if reason:
                        filter_stats[f"{spec.axis}:{reason}"] += 1
                        continue
                    picked = candidate
                    break
                if picked:
                    break
            if not picked:
                filter_stats[f"{spec.axis}:missing_requested_{requested[0]}"] += 1
                missing_bands.append(requested[0])
                continue
            _accept(picked, state)
            selected.append(picked)
            personas.append(build_persona(spec, picked, index, args.constraint_count))
            index += 1
            axis_selected += 1

        while axis_selected < args.per_axis and missing_bands:
            requested_label = missing_bands.pop(0)
            picked = None
            for source_band in _band_order(requested_label):
                for candidate in await candidates_for(spec, source_band):
                    candidate = _with_bands(
                        candidate,
                        requested_band=requested_label,
                        source_band=source_band[0],
                    )
                    reason = _reject_reason(
                        candidate, state, args.max_major_name_length
                    )
                    if reason:
                        filter_stats[f"{spec.axis}:fill_{reason}"] += 1
                        continue
                    picked = candidate
                    break
                if picked:
                    break
            if not picked:
                filter_stats[f"{spec.axis}:fill_missing_{requested_label}"] += 1
                continue
            _accept(picked, state)
            selected.append(picked)
            personas.append(build_persona(spec, picked, index, args.constraint_count))
            index += 1
            axis_selected += 1

        if axis_selected < args.per_axis:
            filter_stats[f"{spec.axis}:selected_less_than_target"] += (
                args.per_axis - axis_selected
            )

    audit_rows = [
        _audit_row(persona, candidate)
        for persona, candidate in zip(personas, selected, strict=True)
    ]
    stats = {
        "requested_total": len(AXES) * args.per_axis,
        "selected_total": len(personas),
        "per_axis_target": args.per_axis,
        "constraint_count": args.constraint_count,
        "diagnostic_level": _diagnostic_level(args.constraint_count),
        "axes": [spec.axis for spec in AXES],
        "score_bands": [band[0] for band in BANDS],
        "raw_candidates_by_axis_band": {
            f"{axis}:{band}": len(candidates)
            for (axis, band), candidates in sorted(scan_cache.items())
        },
        "filter_stats": dict(sorted(filter_stats.items())),
    }
    if len(personas) != len(AXES) * args.per_axis and not args.allow_partial:
        raise RuntimeError(
            f"Expected {len(AXES) * args.per_axis} personas, selected {len(personas)}. "
            "Use --allow-partial to write a partial diagnostic set."
        )
    return personas, audit_rows, stats


def _audit_row(persona: IcebergPersona, candidate: Candidate) -> dict[str, Any]:
    gap = candidate.gap
    tier_a = gap.get("tier_a") or {}
    tier_b = gap.get("tier_b") or {}
    volunteer = persona.implicit_flexibilities["volunteer_set"][0]
    return {
        "case_id": persona.case_id,
        "constraint_count": persona.background.get("constraint_count"),
        "diagnostic_level": persona.background.get("diagnostic_level"),
        "diagnostic_axis": persona.background.get("diagnostic_axis"),
        "preference_axis": persona.background.get("preference_axis"),
        "requested_score_band": persona.background.get("score_band"),
        "source_score_band": persona.background.get("source_score_band"),
        "borrowed_score_band": persona.background.get("borrowed_score_band"),
        "score": candidate.score,
        "finder": candidate.finder,
        "baseline_school": tier_a.get("school_name"),
        "baseline_major": tier_a.get("major_name"),
        "baseline_tier": tier_a.get("tier"),
        "baseline_ranking": tier_a.get("ranking"),
        "target_school": tier_b.get("school_name"),
        "target_major": tier_b.get("major_name"),
        "target_year": tier_b.get("year"),
        "target_min_score": tier_b.get("min_score"),
        "target_min_rank": tier_b.get("min_rank"),
        "target_min_rank_missing": tier_b.get("min_rank") is None,
        "target_tier": tier_b.get("tier"),
        "tier_delta": gap.get("tier_delta") or (_tier(tier_b) - _tier(tier_a)),
        "ranking_gain": gap.get("ranking_gain")
        or volunteer.get("ranking_gain")
        or _ranking_gain(tier_a, tier_b),
        "tuition_delta": gap.get("tuition_delta") or volunteer.get("tuition_delta"),
        "quality_gain": gap.get("quality_gain") or volunteer.get("quality_gain"),
        "outcome_gain": gap.get("outcome_gain") or volunteer.get("outcome_gain"),
        "risk_level": volunteer.get("risk_level"),
        "score_margin": volunteer.get("score_margin"),
    }


def validate_personas(
    personas: list[IcebergPersona],
    *,
    constraint_count: int,
    require_all_axes: bool = True,
) -> None:
    axis_counts = Counter(
        str(persona.background.get("diagnostic_axis")) for persona in personas
    )
    for persona in personas:
        restored = IcebergPersona.model_validate_json(persona.model_dump_json())
        flex = restored.implicit_flexibilities
        if restored.background.get("constraint_count") != constraint_count:
            raise AssertionError(
                f"{restored.case_id} constraint_count is not {constraint_count}"
            )
        if restored.background.get("diagnostic_level") != _diagnostic_level(
            constraint_count
        ):
            raise AssertionError(f"{restored.case_id} diagnostic_level mismatch")
        if len(flex.get("volunteer_set") or []) != 1:
            raise AssertionError(f"{restored.case_id} volunteer_set length is not 1")
        if flex.get("trigger_type") != "single_verified_option":
            raise AssertionError(f"{restored.case_id} trigger_type mismatch")
        if len(restored.explicit_red_lines) != constraint_count:
            raise AssertionError(
                f"{restored.case_id} does not have exactly {constraint_count} red-line keys"
            )
        utterance = restored.initial_utterance
        if (
            str(restored.background["score"]) not in utterance
            or "物理" not in utterance
        ):
            raise AssertionError(
                f"{restored.case_id} initial utterance lacks score or subjects"
            )
    if require_all_axes:
        expected_axes = {spec.axis for spec in AXES}
        if set(axis_counts) != expected_axes:
            raise AssertionError(f"axis mismatch: {dict(axis_counts)}")


def write_outputs(
    personas: list[IcebergPersona],
    audit_rows: list[dict[str, Any]],
    stats: dict[str, Any],
    args: argparse.Namespace,
) -> None:
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(
            [persona.model_dump() for persona in personas], ensure_ascii=False, indent=2
        )
        + "\n",
        encoding="utf-8",
    )

    audit_csv = Path(args.audit_csv)
    audit_csv.parent.mkdir(parents=True, exist_ok=True)
    with audit_csv.open("w", encoding="utf-8", newline="") as handle:
        fieldnames = list(audit_rows[0]) if audit_rows else ["case_id"]
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(audit_rows)

    audit_json = Path(args.audit_json)
    audit_json.parent.mkdir(parents=True, exist_ok=True)
    audit_json.write_text(
        json.dumps(
            {"stats": stats, "selected": audit_rows},
            ensure_ascii=False,
            indent=2,
            default=str,
        )
        + "\n",
        encoding="utf-8",
    )

    write_markdown_audit(audit_rows, stats, Path(args.audit_md))


def write_markdown_audit(
    audit_rows: list[dict[str, Any]], stats: dict[str, Any], path: Path
) -> None:
    counts = Counter(str(row["diagnostic_axis"]) for row in audit_rows)
    borrowed = Counter(
        str(row["diagnostic_axis"])
        for row in audit_rows
        if row.get("borrowed_score_band")
    )
    title = str(stats.get("diagnostic_level") or "constraint-ladder")
    lines = [
        f"# {title} Persona Audit",
        "",
        f"Selected personas: {stats['selected_total']} / {stats['requested_total']}.",
        "",
        "| Axis | Selected | Borrowed band |",
        "| --- | ---: | ---: |",
    ]
    for axis in stats["axes"]:
        lines.append(f"| {axis} | {counts.get(axis, 0)} | {borrowed.get(axis, 0)} |")
    lines.extend(["", "## Selected Cases", ""])
    lines.append(
        "| Case | Axis | Band | Source Band | Score | Baseline | Target | Gain | Missing Rank |"
    )
    lines.append("| --- | --- | --- | --- | ---: | --- | --- | ---: | --- |")
    for row in audit_rows:
        gain = (
            row.get("tier_delta")
            or row.get("quality_gain")
            or row.get("outcome_gain")
            or row.get("ranking_gain")
            or ""
        )
        lines.append(
            f"| {row['case_id']} | {row['diagnostic_axis']} | {row['requested_score_band']} | "
            f"{row['source_score_band']} | {row['score']} | {row['baseline_school']} / {row['baseline_major']} | "
            f"{row['target_school']} / {row['target_major']} | {gain} | {row['target_min_rank_missing']} |"
        )
    if stats.get("filter_stats"):
        lines.extend(["", "## Filter Stats", ""])
        for key, value in stats["filter_stats"].items():
            lines.append(f"- `{key}`: {value}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--constraint-count", type=int, choices=[1, 2, 3, 4, 5, 6], default=1
    )
    parser.add_argument("--output")
    parser.add_argument("--audit-csv")
    parser.add_argument("--audit-json")
    parser.add_argument("--audit-md")
    parser.add_argument("--province", default="浙江")
    parser.add_argument("--per-axis", type=int, default=5)
    parser.add_argument("--score-step", type=int, default=10)
    parser.add_argument("--candidates-per-score", type=int, default=160)
    parser.add_argument("--strict-major", default="临床医学")
    parser.add_argument(
        "--major-relax-scope", choices=["province", "national"], default="national"
    )
    parser.add_argument("--tuition-strict-major")
    parser.add_argument("--quality-strict-major", default="软件")
    parser.add_argument("--employment-strict-major", default="机械设计制造及其自动化")
    parser.add_argument("--budget", type=int, default=5000)
    parser.add_argument("--budget-window", type=int, default=10000)
    parser.add_argument(
        "--tuition-relax-scope", choices=["province", "national"], default="national"
    )
    parser.add_argument("--min-quality-gain", type=int, default=10)
    parser.add_argument("--min-outcome-gain", type=int, default=15)
    parser.add_argument("--risk-max-score-margin", type=int, default=8)
    parser.add_argument("--max-major-name-length", type=int, default=40)
    parser.add_argument("--include-suspect-schools", action="store_true")
    parser.add_argument("--no-strict-target-quality", action="store_true")
    parser.add_argument("--allow-partial", action="store_true")
    args = parser.parse_args(argv)
    if args.output is None:
        args.output = str(DEFAULT_OUTPUTS[args.constraint_count])
    if args.audit_csv is None:
        args.audit_csv = str(DEFAULT_AUDIT_CSVS[args.constraint_count])
    if args.audit_json is None:
        args.audit_json = str(DEFAULT_AUDIT_JSONS[args.constraint_count])
    if args.audit_md is None:
        args.audit_md = str(DEFAULT_AUDIT_MDS[args.constraint_count])
    return args


def main(argv: list[str] | None = None) -> int:
    load_dotenv()
    if os.name == "nt":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    args = parse_args(argv)
    personas, audit_rows, stats = asyncio.run(build_dataset(args))
    validate_personas(
        personas,
        constraint_count=args.constraint_count,
        require_all_axes=not args.allow_partial,
    )
    write_outputs(personas, audit_rows, stats, args)
    print(f"Wrote {len(personas)} personas to {args.output}")
    print(f"Wrote audit CSV to {args.audit_csv}")
    print(f"Wrote audit JSON to {args.audit_json}")
    print(f"Wrote audit markdown to {args.audit_md}")
    for axis, count in sorted(
        Counter(row["diagnostic_axis"] for row in audit_rows).items()
    ):
        print(f"{axis}: {count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
