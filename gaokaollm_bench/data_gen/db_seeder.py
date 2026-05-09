"""Database-backed seed discovery for benchmark persona generation."""

from __future__ import annotations

from typing import Any

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


BASE_SELECT = """
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
    CASE
        WHEN s.is_985 THEN 4
        WHEN s.is_211 OR s.is_double_first_class THEN 3
        WHEN s.education_level = '本科' THEN 2
        ELSE 1
    END AS tier
FROM admission_scores a
JOIN schools s ON s.id = a.school_id
WHERE a.min_score IS NOT NULL
  AND a.min_score <= %s
"""

BASE_ORDER = """
ORDER BY
    tier DESC,
    s.ranking ASC NULLS LAST,
    a.min_score DESC NULLS LAST,
    a.year DESC,
    s.name ASC,
    a.major_name_raw ASC
LIMIT %s
"""


async def _fetch(db_pool: Any, query: str, params: list[Any]) -> list[dict[str, Any]]:
    if hasattr(db_pool, "fetch_query"):
        rows = await db_pool.fetch_query(query, *params)
    elif hasattr(db_pool, "fetch"):
        rows = await db_pool.fetch(query, *params)
    elif callable(db_pool):
        rows = await db_pool(query, *params)
    elif hasattr(db_pool, "connection"):
        async with db_pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(query, params)
                rows = await cur.fetchall()
    else:
        raise TypeError(
            "db_pool must provide fetch_query, fetch, connection, or be callable"
        )

    return [dict(row) for row in rows]


def _tier(row: dict[str, Any] | None) -> int:
    if not row:
        return 0
    return int(row.get("tier") or 0)


def _is_special_major_name(
    major_name: str | None,
    *,
    include_special_majors: bool,
    max_major_name_length: int | None,
) -> bool:
    if include_special_majors:
        return False
    major_name = major_name or ""
    if max_major_name_length is not None and len(major_name) > max_major_name_length:
        return True
    return any(term in major_name for term in SPECIAL_MAJOR_TERMS)


def _candidate_year(candidate: dict[str, Any]) -> int:
    year = candidate["tier_b"].get("year")
    return int(year or 0)


def _select_volunteers_from_candidates(
    candidates: list[dict[str, Any]],
    *,
    max_volunteers_per_case: int | None,
    max_volunteers_per_school: int | None,
    include_special_majors: bool,
    max_major_name_length: int | None,
    minimum_volunteers: int = 1,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    volunteers: list[dict[str, Any]] = []
    seen_options: set[tuple[Any, Any]] = set()
    school_counts: dict[Any, int] = {}
    skipped = {
        "duplicate_option": 0,
        "school_cap": 0,
        "special_major": 0,
    }

    years = sorted(
        {_candidate_year(candidate) for candidate in candidates}, reverse=True
    )
    for year in years:
        for candidate in candidates:
            if _candidate_year(candidate) != year:
                continue
            tier_b = candidate["tier_b"]
            if _is_special_major_name(
                tier_b.get("major_name"),
                include_special_majors=include_special_majors,
                max_major_name_length=max_major_name_length,
            ):
                skipped["special_major"] += 1
                continue

            option_key = (
                tier_b.get("school_id"),
                tier_b.get("major_id") or tier_b.get("major_name"),
            )
            if option_key in seen_options:
                skipped["duplicate_option"] += 1
                continue

            school_key = tier_b.get("school_id") or tier_b.get("school_name")
            if (
                max_volunteers_per_school is not None
                and school_counts.get(school_key, 0) >= max_volunteers_per_school
            ):
                skipped["school_cap"] += 1
                continue

            seen_options.add(option_key)
            school_counts[school_key] = school_counts.get(school_key, 0) + 1
            volunteers.append(tier_b)
            if max_volunteers_per_case and len(volunteers) >= max_volunteers_per_case:
                break
        if max_volunteers_per_case and len(volunteers) >= max_volunteers_per_case:
            break
        if max_volunteers_per_case is None and len(volunteers) >= minimum_volunteers:
            break

    return volunteers, {
        "years_considered": [year for year in years if year],
        "years_used": sorted(
            {int(row.get("year") or 0) for row in volunteers if row.get("year")},
            reverse=True,
        ),
        "skipped": skipped,
    }


def _first_unique_school_ids(
    volunteers: list[dict[str, Any]], limit: int = 4
) -> tuple[Any, ...]:
    school_ids: list[Any] = []
    for row in volunteers:
        school_id = row.get("school_id") or row.get("school_name")
        if school_id not in school_ids:
            school_ids.append(school_id)
        if len(school_ids) >= limit:
            break
    return tuple(school_ids)


async def find_pareto_gaps(db_pool: Any, score: int, prov: str) -> dict[str, Any]:
    """Find a real school-tier jump unlocked by relaxing the province constraint."""

    local_query = f"{BASE_SELECT}  AND s.province = %s\n{BASE_ORDER}"
    national_query = f"{BASE_SELECT}\n{BASE_ORDER}"

    local_rows = await _fetch(db_pool, local_query, [score, prov, 1])
    national_rows = await _fetch(db_pool, national_query, [score, 1])

    tier_a = local_rows[0] if local_rows else None
    tier_b = national_rows[0] if national_rows else None

    if _tier(tier_b) <= _tier(tier_a):
        return {}

    return {
        "score": score,
        "province": prov,
        "constraint_relaxed": "province",
        "tier_a": tier_a,
        "tier_b": tier_b,
        "tier_delta": _tier(tier_b) - _tier(tier_a),
    }


async def find_pareto_gap_candidates(
    db_pool: Any,
    score: int,
    prov: str,
    *,
    limit: int = 20,
    exclude_name_patterns: list[str] | None = None,
    strict_target_quality: bool = True,
) -> list[dict[str, Any]]:
    """Return multiple real tier-jump candidates unlocked by leaving a province."""

    if limit < 1:
        raise ValueError("limit must be at least 1")

    local_query = f"{BASE_SELECT}  AND s.province = %s\n{BASE_ORDER}"
    local_rows = await _fetch(db_pool, local_query, [score, prov, 1])
    tier_a = local_rows[0] if local_rows else None
    if not tier_a:
        return []

    exclude_name_patterns = exclude_name_patterns or []
    exclude_clauses = []
    exclude_params: list[Any] = []
    for pattern in exclude_name_patterns:
        exclude_clauses.append("s.name NOT LIKE %s")
        exclude_params.append(f"%{pattern}%")

    quality_clause = ""
    quality_params: list[Any] = []
    if strict_target_quality:
        quality_clause = (
            "  AND (s.name LIKE %s OR s.name LIKE %s)\n"
            "  AND NOT (s.name LIKE %s AND s.name NOT LIKE %s)\n"
        )
        quality_params = ["%大学%", "%医学院%", "%大学%学院%", "%医学院%"]

    national_query = (
        f"{BASE_SELECT}"
        "  AND s.province <> %s\n"
        "  AND s.education_level = '本科'\n"
        "  AND CASE\n"
        "        WHEN s.is_985 THEN 4\n"
        "        WHEN s.is_211 OR s.is_double_first_class THEN 3\n"
        "        WHEN s.education_level = '本科' THEN 2\n"
        "        ELSE 1\n"
        "      END > %s\n"
        f"{quality_clause}"
        f"{'  AND ' + ' AND '.join(exclude_clauses) if exclude_clauses else ''}\n"
        f"{BASE_ORDER}"
    )
    national_rows = await _fetch(
        db_pool,
        national_query,
        [score, prov, _tier(tier_a), *quality_params, *exclude_params, limit],
    )

    candidates: list[dict[str, Any]] = []
    for tier_b in national_rows:
        if _tier(tier_b) <= _tier(tier_a):
            continue
        candidates.append(
            {
                "score": score,
                "province": prov,
                "constraint_relaxed": "province",
                "tier_a": tier_a,
                "tier_b": tier_b,
                "tier_delta": _tier(tier_b) - _tier(tier_a),
            }
        )
    return candidates


async def find_many_pareto_gaps(
    db_pool: Any,
    *,
    count: int,
    prov: str = "浙江",
    score_min: int = 520,
    score_max: int = 700,
    score_step: int = 1,
    candidates_per_score: int = 20,
    unique_by: str = "school_pair",
    exclude_name_patterns: list[str] | None = None,
    strict_target_quality: bool = True,
) -> list[dict[str, Any]]:
    """Scan a score range and return distinct province-relaxation tier gaps."""

    if count < 1:
        raise ValueError("count must be at least 1")
    if score_step < 1:
        raise ValueError("score_step must be at least 1")
    if score_min > score_max:
        raise ValueError("score_min must be less than or equal to score_max")
    if unique_by not in {"school_pair", "school_major", "score"}:
        raise ValueError("unique_by must be one of: school_pair, school_major, score")

    gaps: list[dict[str, Any]] = []
    seen: set[tuple[Any, ...]] = set()

    for score in range(score_min, score_max + 1, score_step):
        candidates = await find_pareto_gap_candidates(
            db_pool,
            score,
            prov,
            limit=candidates_per_score,
            exclude_name_patterns=exclude_name_patterns,
            strict_target_quality=strict_target_quality,
        )
        for gap in candidates:
            if unique_by == "school_pair":
                key = (gap["tier_a"].get("school_id"), gap["tier_b"].get("school_id"))
            elif unique_by == "school_major":
                key = (
                    gap["tier_a"].get("school_id"),
                    gap["tier_b"].get("school_id"),
                    gap["tier_a"].get("major_id"),
                    gap["tier_b"].get("major_id"),
                )
            else:
                key = (
                    gap["tier_a"].get("school_id"),
                    gap["tier_b"].get("school_id"),
                    int(gap["score"]),
                )

            if key in seen:
                continue

            seen.add(key)
            gaps.append(gap)
            if len(gaps) >= count:
                return gaps

    return gaps


async def find_pareto_gap_sets(
    db_pool: Any,
    *,
    count: int,
    prov: str = "浙江",
    score_min: int = 520,
    score_max: int = 700,
    score_step: int = 10,
    candidates_per_score: int = 120,
    max_volunteers_per_case: int | None = None,
    exclude_name_patterns: list[str] | None = None,
    strict_target_quality: bool = True,
) -> list[dict[str, Any]]:
    """Scan scores and return persona seeds whose relaxed side is a volunteer set."""

    if count < 1:
        raise ValueError("count must be at least 1")
    if max_volunteers_per_case is not None and max_volunteers_per_case < 1:
        raise ValueError("max_volunteers_per_case must be at least 1 when provided")

    gap_sets: list[dict[str, Any]] = []
    seen_cases: set[tuple[Any, int]] = set()

    for score in range(score_min, score_max + 1, score_step):
        candidates = await find_pareto_gap_candidates(
            db_pool,
            score,
            prov,
            limit=candidates_per_score,
            exclude_name_patterns=exclude_name_patterns,
            strict_target_quality=strict_target_quality,
        )
        if not candidates:
            continue

        tier_a = candidates[0]["tier_a"]
        case_key = (tier_a.get("school_id"), int(score))
        if case_key in seen_cases:
            continue

        seen_schools: set[Any] = set()
        volunteers: list[dict[str, Any]] = []
        for candidate in candidates:
            tier_b = candidate["tier_b"]
            school_key = tier_b.get("school_id")
            if school_key in seen_schools:
                continue
            seen_schools.add(school_key)
            volunteers.append(tier_b)
            if max_volunteers_per_case and len(volunteers) >= max_volunteers_per_case:
                break

        if not volunteers:
            continue

        seen_cases.add(case_key)
        gap_sets.append(
            {
                "score": score,
                "province": prov,
                "constraint_relaxed": "province",
                "tier_a": tier_a,
                "volunteer_set": volunteers,
                "volunteer_count": len(volunteers),
                "max_tier_delta": max(_tier(row) - _tier(tier_a) for row in volunteers),
            }
        )
        if len(gap_sets) >= count:
            break

    return gap_sets


DEFAULT_MEDTECH_PATTERNS = [
    "%医学检验%",
    "%医学影像%",
    "%康复治疗%",
    "%卫生检验%",
    "%医学实验%",
    "%眼视光%",
    "%医学技术%",
]


async def find_major_relax_gap_candidates(
    db_pool: Any,
    score: int,
    prov: str,
    *,
    strict_major: str = "临床医学",
    relaxation_kind: str = "clinical_to_medtech",
    target_major_patterns: list[str] | None = None,
    exclude_major_patterns: list[str] | None = None,
    relax_scope: str = "province",
    limit: int = 120,
    exclude_name_patterns: list[str] | None = None,
    strict_target_quality: bool = True,
) -> list[dict[str, Any]]:
    """Return same-province tier jumps unlocked by relaxing the major constraint."""

    if limit < 1:
        raise ValueError("limit must be at least 1")
    if relaxation_kind not in {"clinical_to_medtech", "any_major"}:
        raise ValueError("relaxation_kind must be clinical_to_medtech or any_major")
    if relax_scope not in {"province", "national"}:
        raise ValueError("relax_scope must be province or national")

    strict_major_pattern = f"%{strict_major}%"
    baseline_query = (
        f"{BASE_SELECT}"
        "  AND s.province = %s\n"
        "  AND a.major_name_raw LIKE %s\n"
        f"{BASE_ORDER}"
    )
    baseline_rows = await _fetch(
        db_pool, baseline_query, [score, prov, strict_major_pattern, 1]
    )
    tier_a = baseline_rows[0] if baseline_rows else None
    if not tier_a:
        return []

    exclude_name_patterns = exclude_name_patterns or []
    exclude_clauses = []
    exclude_params: list[Any] = []
    for pattern in exclude_name_patterns:
        exclude_clauses.append("s.name NOT LIKE %s")
        exclude_params.append(f"%{pattern}%")

    quality_clause = ""
    quality_params: list[Any] = []
    if strict_target_quality:
        quality_clause = (
            "  AND (s.name LIKE %s OR s.name LIKE %s)\n"
            "  AND NOT (s.name LIKE %s AND s.name NOT LIKE %s)\n"
        )
        quality_params = ["%大学%", "%医学院%", "%大学%学院%", "%医学院%"]

    major_clause = ""
    major_params: list[Any] = []
    exclude_major_patterns = exclude_major_patterns or []
    if relaxation_kind == "clinical_to_medtech":
        patterns = target_major_patterns or DEFAULT_MEDTECH_PATTERNS
        major_clause = (
            "  AND ("
            + " OR ".join(["a.major_name_raw LIKE %s"] * len(patterns))
            + ")\n"
        )
        major_params.extend(patterns)
        for pattern in exclude_major_patterns:
            major_clause += "  AND a.major_name_raw NOT LIKE %s\n"
            major_params.append(pattern)
    else:
        major_clause = "  AND a.major_name_raw NOT LIKE %s\n"
        major_params.append(strict_major_pattern)

    relaxed_geo_clause = "  AND s.province = %s\n" if relax_scope == "province" else ""
    relaxed_params: list[Any] = [score]
    if relax_scope == "province":
        relaxed_params.append(prov)
    relaxed_params.append(_tier(tier_a))

    relaxed_query = (
        f"{BASE_SELECT}"
        f"{relaxed_geo_clause}"
        "  AND s.education_level = '本科'\n"
        "  AND CASE\n"
        "        WHEN s.is_985 THEN 4\n"
        "        WHEN s.is_211 OR s.is_double_first_class THEN 3\n"
        "        WHEN s.education_level = '本科' THEN 2\n"
        "        ELSE 1\n"
        "      END > %s\n"
        f"{major_clause}"
        f"{quality_clause}"
        f"{'  AND ' + ' AND '.join(exclude_clauses) if exclude_clauses else ''}\n"
        f"{BASE_ORDER}"
    )
    relaxed_rows = await _fetch(
        db_pool,
        relaxed_query,
        [
            *relaxed_params,
            *major_params,
            *quality_params,
            *exclude_params,
            limit,
        ],
    )

    candidates: list[dict[str, Any]] = []
    for tier_b in relaxed_rows:
        if _tier(tier_b) <= _tier(tier_a):
            continue
        candidates.append(
            {
                "score": score,
                "province": prov,
                "constraint_relaxed": "major",
                "relaxation_kind": relaxation_kind,
                "relax_scope": relax_scope,
                "strict_major": strict_major,
                "tier_a": tier_a,
                "tier_b": tier_b,
                "tier_delta": _tier(tier_b) - _tier(tier_a),
            }
        )
    return candidates


async def find_major_relax_gap_sets(
    db_pool: Any,
    *,
    count: int,
    prov: str = "浙江",
    strict_major: str = "临床医学",
    relaxation_kind: str = "clinical_to_medtech",
    target_major_patterns: list[str] | None = None,
    exclude_major_patterns: list[str] | None = None,
    relax_scope: str = "province",
    score_min: int = 520,
    score_max: int = 700,
    score_step: int = 10,
    candidates_per_score: int = 120,
    max_volunteers_per_case: int | None = None,
    max_volunteers_per_school: int | None = None,
    include_special_majors: bool = True,
    max_major_name_length: int | None = None,
    exclude_name_patterns: list[str] | None = None,
    strict_target_quality: bool = True,
) -> list[dict[str, Any]]:
    """Return major-relaxation persona seeds whose relaxed side is a volunteer set."""

    if count < 1:
        raise ValueError("count must be at least 1")
    if max_volunteers_per_case is not None and max_volunteers_per_case < 1:
        raise ValueError("max_volunteers_per_case must be at least 1 when provided")
    if max_volunteers_per_school is not None and max_volunteers_per_school < 1:
        raise ValueError("max_volunteers_per_school must be at least 1 when provided")
    if max_major_name_length is not None and max_major_name_length < 1:
        raise ValueError("max_major_name_length must be at least 1 when provided")

    gap_sets: list[dict[str, Any]] = []
    seen_cases: set[tuple[Any, ...]] = set()

    for score in range(score_min, score_max + 1, score_step):
        candidates = await find_major_relax_gap_candidates(
            db_pool,
            score,
            prov,
            strict_major=strict_major,
            relaxation_kind=relaxation_kind,
            target_major_patterns=target_major_patterns,
            exclude_major_patterns=exclude_major_patterns,
            relax_scope=relax_scope,
            limit=candidates_per_score,
            exclude_name_patterns=exclude_name_patterns,
            strict_target_quality=strict_target_quality,
        )
        if not candidates:
            continue

        tier_a = candidates[0]["tier_a"]
        case_key = (tier_a.get("school_id"), int(score), relaxation_kind)
        if case_key in seen_cases:
            continue

        volunteers, selection_audit = _select_volunteers_from_candidates(
            candidates,
            max_volunteers_per_case=max_volunteers_per_case,
            max_volunteers_per_school=max_volunteers_per_school,
            include_special_majors=include_special_majors,
            max_major_name_length=max_major_name_length,
            minimum_volunteers=1,
        )

        if not volunteers:
            continue

        seen_cases.add(case_key)
        gap_sets.append(
            {
                "score": score,
                "province": prov,
                "constraint_relaxed": "major",
                "relaxation_kind": relaxation_kind,
                "relax_scope": relax_scope,
                "strict_major": strict_major,
                "tier_a": tier_a,
                "volunteer_set": volunteers,
                "volunteer_count": len(volunteers),
                "years_used": selection_audit["years_used"],
                "max_tier_delta": max(_tier(row) - _tier(tier_a) for row in volunteers),
            }
        )
        if len(gap_sets) >= count:
            break

    return gap_sets


async def find_hierarchical_major_relax_gap_sets(
    db_pool: Any,
    *,
    count: int,
    prov: str = "浙江",
    strict_major: str = "临床医学",
    relaxation_stages: list[dict[str, Any]],
    score_min: int = 520,
    score_max: int = 700,
    score_step: int = 10,
    candidates_per_score: int = 120,
    recommendation_threshold: int = 1,
    max_volunteers_per_case: int | None = None,
    max_volunteers_per_school: int | None = 2,
    include_special_majors: bool = False,
    max_major_name_length: int | None = 60,
    relax_scope: str = "province",
    exclude_name_patterns: list[str] | None = None,
    strict_target_quality: bool = True,
) -> list[dict[str, Any]]:
    """Try staged major-cluster relaxations and keep the earliest stage with gaps."""

    if count < 1:
        raise ValueError("count must be at least 1")
    if recommendation_threshold < 1:
        raise ValueError("recommendation_threshold must be at least 1")
    if max_volunteers_per_case is not None and max_volunteers_per_case < 1:
        raise ValueError("max_volunteers_per_case must be at least 1 when provided")
    if max_volunteers_per_school is not None and max_volunteers_per_school < 1:
        raise ValueError("max_volunteers_per_school must be at least 1 when provided")
    if max_major_name_length is not None and max_major_name_length < 1:
        raise ValueError("max_major_name_length must be at least 1 when provided")
    if not relaxation_stages:
        raise ValueError("relaxation_stages must not be empty")

    gap_sets: list[dict[str, Any]] = []
    seen_cases: set[tuple[Any, ...]] = set()

    for score in range(score_min, score_max + 1, score_step):
        stage_attempts: list[dict[str, Any]] = []
        for stage in relaxation_stages:
            include_patterns = stage.get("include_patterns") or []
            exclude_patterns = stage.get("exclude_patterns") or []
            stage_relaxation_kind = stage.get("relaxation_kind") or (
                "any_major"
                if stage.get("strategy") == "any_major"
                else "clinical_to_medtech"
            )
            if not include_patterns and stage_relaxation_kind != "any_major":
                continue

            candidates = await find_major_relax_gap_candidates(
                db_pool,
                score,
                prov,
                strict_major=strict_major,
                relaxation_kind=stage_relaxation_kind,
                target_major_patterns=include_patterns,
                exclude_major_patterns=exclude_patterns,
                relax_scope=relax_scope,
                limit=candidates_per_score,
                exclude_name_patterns=exclude_name_patterns,
                strict_target_quality=strict_target_quality,
            )
            attempt = {
                "stage": stage.get("stage"),
                "label": stage.get("label"),
                "strategy": stage.get("strategy"),
                "stage_relaxation_kind": stage_relaxation_kind,
                "raw_candidate_count": len(candidates),
                "filtered_volunteer_count": 0,
                "recommendation_threshold": recommendation_threshold,
                "accepted": False,
                "failure_reason": None,
                "years_used": [],
                "skipped": {},
            }
            if not candidates:
                attempt["failure_reason"] = "no_candidates"
                stage_attempts.append(attempt)
                continue

            tier_a = candidates[0]["tier_a"]
            stage_id = str(stage.get("stage"))

            volunteers, selection_audit = _select_volunteers_from_candidates(
                candidates,
                max_volunteers_per_case=max_volunteers_per_case,
                max_volunteers_per_school=max_volunteers_per_school,
                include_special_majors=include_special_majors,
                max_major_name_length=max_major_name_length,
                minimum_volunteers=recommendation_threshold,
            )
            attempt["filtered_volunteer_count"] = len(volunteers)
            attempt["years_used"] = selection_audit["years_used"]
            attempt["years_considered"] = selection_audit["years_considered"]
            attempt["skipped"] = selection_audit["skipped"]

            if not volunteers:
                attempt["failure_reason"] = "filtered_empty"
                stage_attempts.append(attempt)
                continue
            if len(volunteers) < recommendation_threshold:
                attempt["failure_reason"] = "below_threshold"
                stage_attempts.append(attempt)
                continue

            case_key = (
                tier_a.get("school_id"),
                stage_id,
                _first_unique_school_ids(volunteers),
            )
            if case_key in seen_cases:
                attempt["failure_reason"] = "duplicate_case"
                stage_attempts.append(attempt)
                continue

            attempt["accepted"] = True
            stage_attempts.append(attempt)
            seen_cases.add(case_key)
            gap_sets.append(
                {
                    "score": score,
                    "province": prov,
                    "constraint_relaxed": "major",
                    "relaxation_kind": "hierarchical_major",
                    "stage_relaxation_kind": stage_relaxation_kind,
                    "relax_scope": relax_scope,
                    "strict_major": strict_major,
                    "source_major_cluster": stage.get("source_cluster"),
                    "relaxation_stage": stage.get("stage"),
                    "relaxation_stage_label": stage.get("label"),
                    "target_major_clusters": stage.get("cluster_ids"),
                    "target_major_categories": stage.get("category_ids"),
                    "psychological_distance": stage.get("psychological_distance"),
                    "stage_attempts": list(stage_attempts),
                    "years_used": selection_audit["years_used"],
                    "tier_a": tier_a,
                    "volunteer_set": volunteers,
                    "volunteer_count": len(volunteers),
                    "max_tier_delta": max(
                        _tier(row) - _tier(tier_a) for row in volunteers
                    ),
                }
            )
            break

        if len(gap_sets) >= count:
            break

    return gap_sets


def _risk_level_from_margins(
    *,
    score_margin: int | float | None,
    rank_gap: int | float | None,
) -> str:
    if rank_gap is not None:
        gap = float(rank_gap)
        if gap <= 3000:
            return "chong"
        if gap <= 12000:
            return "wen"
        if gap <= 30000:
            return "bao"
        return "dian"

    if score_margin is None:
        return "unknown"
    margin = float(score_margin)
    if margin <= 5:
        return "chong"
    if margin <= 20:
        return "wen"
    if margin <= 45:
        return "bao"
    return "dian"


async def _student_rank_for_score(
    db_pool: Any,
    *,
    score: int,
    prov: str,
) -> int | None:
    query = """
    SELECT rank_min, rank_max
    FROM score_rank_segments
    WHERE province = %s
      AND score_min <= %s
      AND score_max >= %s
    ORDER BY year DESC
    LIMIT 1
    """
    rows = await _fetch(db_pool, query, [prov, score, score])
    if not rows:
        return None
    rank_value = rows[0].get("rank_min") or rows[0].get("rank_max")
    if rank_value is None:
        return None
    return int(float(rank_value))


def _annotate_risk_candidate(
    row: dict[str, Any],
    *,
    score: int,
    student_rank: int | None,
) -> dict[str, Any]:
    annotated = dict(row)
    min_score = row.get("min_score")
    min_rank = row.get("min_rank")
    score_margin = None
    rank_gap = None
    if min_score is not None:
        score_margin = score - int(float(min_score))
    if student_rank is not None and min_rank is not None:
        rank_gap = int(float(min_rank)) - student_rank
    annotated["score_margin"] = score_margin
    annotated["student_rank"] = student_rank
    annotated["rank_gap"] = rank_gap
    annotated["risk_level"] = _risk_level_from_margins(
        score_margin=score_margin,
        rank_gap=rank_gap,
    )
    return annotated


def _risk_sort_key(row: dict[str, Any]) -> tuple[Any, ...]:
    order = {"chong": 0, "wen": 1, "bao": 2, "dian": 3, "unknown": 4}
    ranking = row.get("ranking")
    margin = row.get("score_margin")
    return (
        order.get(str(row.get("risk_level") or "unknown"), 4),
        int(ranking) if ranking is not None else 999999,
        abs(float(margin)) if margin is not None else 9999.0,
        -int(row.get("tier") or 0),
        -int(row.get("year") or 0),
        str(row.get("school_name") or ""),
    )


def _select_risk_band_volunteers(
    rows: list[dict[str, Any]],
    *,
    max_volunteers_per_case: int | None,
    max_volunteers_per_school: int | None,
) -> list[dict[str, Any]]:
    limit = max_volunteers_per_case or 6
    volunteers: list[dict[str, Any]] = []
    seen_options: set[tuple[Any, Any]] = set()
    school_counts: dict[Any, int] = {}

    def append(row: dict[str, Any]) -> bool:
        option_key = (
            row.get("school_id"),
            row.get("major_id") or row.get("major_name"),
        )
        if option_key in seen_options:
            return False
        school_key = row.get("school_id") or row.get("school_name")
        if (
            max_volunteers_per_school is not None
            and school_counts.get(school_key, 0) >= max_volunteers_per_school
        ):
            return False
        seen_options.add(option_key)
        school_counts[school_key] = school_counts.get(school_key, 0) + 1
        volunteers.append(row)
        return True

    sorted_rows = sorted(rows, key=_risk_sort_key)
    for required_band in ("chong", "wen", "bao"):
        for row in sorted_rows:
            if row.get("risk_level") == required_band and append(row):
                break

    if not {"chong", "wen", "bao"}.issubset(
        {str(row.get("risk_level")) for row in volunteers}
    ):
        return []

    for row in sorted_rows:
        if len(volunteers) >= limit:
            break
        append(row)
    return volunteers[:limit]


async def find_risk_band_gap_sets(
    db_pool: Any,
    *,
    count: int,
    prov: str = "浙江",
    strict_major: str = "临床医学",
    score_min: int = 520,
    score_max: int = 700,
    score_step: int = 10,
    candidates_per_score: int = 120,
    max_volunteers_per_case: int | None = None,
    max_volunteers_per_school: int | None = 2,
    strict_target_quality: bool = True,
) -> list[dict[str, Any]]:
    """Return persona seeds for relaxing conservative risk preference."""

    if count < 1:
        raise ValueError("count must be at least 1")
    if max_volunteers_per_case is not None and max_volunteers_per_case < 3:
        raise ValueError("max_volunteers_per_case must be at least 3 when provided")

    quality_clause = ""
    quality_params: list[Any] = []
    if strict_target_quality:
        quality_clause = (
            "  AND s.education_level = '本科'\n"
            "  AND (s.name LIKE %s OR s.name LIKE %s)\n"
            "  AND NOT (s.name LIKE %s AND s.name NOT LIKE %s)\n"
        )
        quality_params = ["%大学%", "%医学院%", "%大学%学院%", "%医学院%"]

    query = (
        f"{BASE_SELECT}"
        "  AND s.province = %s\n"
        "  AND a.major_name_raw LIKE %s\n"
        f"{quality_clause}"
        f"{BASE_ORDER}"
    )

    gap_sets: list[dict[str, Any]] = []
    seen_cases: set[tuple[Any, ...]] = set()
    major_pattern = f"%{strict_major}%"
    for score in range(score_min, score_max + 1, score_step):
        student_rank = await _student_rank_for_score(db_pool, score=score, prov=prov)
        rows = await _fetch(
            db_pool,
            query,
            [
                score,
                prov,
                major_pattern,
                *quality_params,
                candidates_per_score,
            ],
        )
        annotated = [
            _annotate_risk_candidate(row, score=score, student_rank=student_rank)
            for row in rows
        ]
        conservative = [
            row for row in annotated if row.get("risk_level") in {"bao", "dian"}
        ]
        volunteers = _select_risk_band_volunteers(
            annotated,
            max_volunteers_per_case=max_volunteers_per_case,
            max_volunteers_per_school=max_volunteers_per_school,
        )
        if not conservative or not volunteers:
            continue

        tier_a = conservative[0]
        case_key = (
            int(score),
            tier_a.get("school_id"),
            tuple(row.get("school_id") for row in volunteers[:3]),
        )
        if case_key in seen_cases:
            continue

        seen_cases.add(case_key)
        risk_levels = [str(row.get("risk_level")) for row in volunteers]
        gap_sets.append(
            {
                "score": score,
                "province": prov,
                "constraint_relaxed": "risk_band",
                "relaxation_kind": "risk_band_portfolio",
                "strict_major": strict_major,
                "baseline_risk_preference": "conservative",
                "student_rank": student_rank,
                "tier_a": tier_a,
                "volunteer_set": volunteers,
                "volunteer_count": len(volunteers),
                "risk_levels": risk_levels,
                "portfolio_gain": len(set(risk_levels) & {"chong", "wen", "bao"}),
                "max_tier_delta": max(_tier(row) - _tier(tier_a) for row in volunteers),
            }
        )
        if len(gap_sets) >= count:
            break

    return gap_sets
