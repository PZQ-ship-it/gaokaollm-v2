import asyncio
from pathlib import Path
from typing import Any

from app.core import db_pg
from gaokaollm_bench.data_gen.major_tree import build_relaxation_stages


DEFAULT_MAJOR_TREE_PATH = Path("gaokaollm_bench/outputs/major_tree_final_reviewed.json")
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
    a.id AS admission_score_id,
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
    a.subject_requirement,
    a.requirement_normalized,
    COALESCE(sr.requirement_type, 'unknown') AS requirement_type,
    a.min_score,
    a.min_rank,
    plan.min_tuition AS tuition,
    CASE
        WHEN s.is_985 THEN 4
        WHEN s.is_211 OR s.is_double_first_class THEN 3
        WHEN s.education_level = '本科' THEN 2
        ELSE 1
    END AS tier
FROM admission_scores a
JOIN schools s ON s.id = a.school_id
LEFT JOIN subject_requirements sr ON sr.raw_requirement = a.subject_requirement
LEFT JOIN LATERAL (
    SELECT min(p.tuition) AS min_tuition
    FROM admission_plans p
    WHERE p.school_id = a.school_id
      AND p.year = a.year
      AND (
          p.major_id = a.major_id
          OR p.major_code = a.major_code
          OR p.major_name_raw = a.major_name_raw
      )
) plan ON true
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

MAJOR_GEO_ORDER = """
ORDER BY
    a.year DESC,
    tier DESC,
    s.ranking ASC NULLS LAST,
    a.min_score DESC NULLS LAST,
    s.name ASC,
    a.major_name_raw ASC
LIMIT %s
"""


async def _fetch(db: Any, query: str, params: list[Any]) -> list[dict[str, Any]]:
    if db is None:
        return await db_pg.fetch_query(query, *params)
    if hasattr(db, "fetch_query"):
        return await db.fetch_query(query, *params)
    return await db(query, *params)


def _score(constraints: dict[str, Any]) -> int:
    score = constraints.get("score")
    if score is None:
        raise ValueError("constraints['score'] is required")
    return int(score)


def _budget(constraints: dict[str, Any]) -> int | None:
    budget = constraints.get("budget")
    if budget in (None, ""):
        return None
    return int(budget)


def _max_tier(rows: list[dict[str, Any]]) -> int:
    if not rows:
        return 0
    return max(int(row.get("tier") or 0) for row in rows)


def classify_risk_band(
    *,
    score_margin: int | float | None,
    rank_gap: int | float | None = None,
) -> str:
    """Classify admission risk using deterministic score/rank margins."""

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


def _risk_band_order(risk_level: str | None) -> int:
    order = {
        "chong": 0,
        "wen": 1,
        "bao": 2,
        "dian": 3,
        "unknown": 4,
    }
    return order.get(str(risk_level or "unknown"), 4)


def _annotate_risk_row(
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
    annotated["risk_level"] = classify_risk_band(
        score_margin=score_margin,
        rank_gap=rank_gap,
    )
    return annotated


def _risk_selection_key(row: dict[str, Any]) -> tuple[Any, ...]:
    ranking = row.get("ranking")
    score_margin = row.get("score_margin")
    return (
        _risk_band_order(row.get("risk_level")),
        int(ranking) if ranking is not None else 999999,
        abs(float(score_margin)) if score_margin is not None else 9999.0,
        -int(row.get("tier") or 0),
        -int(row.get("year") or 0),
        str(row.get("school_name") or ""),
        str(row.get("major_name") or ""),
    )


def _select_risk_portfolio(
    rows: list[dict[str, Any]],
    *,
    limit: int,
    max_per_school: int,
) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    school_counts: dict[Any, int] = {}
    seen_options: set[tuple[Any, Any]] = set()

    for required_band in ("chong", "wen", "bao"):
        for row in sorted(rows, key=_risk_selection_key):
            if row.get("risk_level") != required_band:
                continue
            if _append_unique_option(
                selected,
                row,
                seen_options=seen_options,
                school_counts=school_counts,
                max_per_school=max_per_school,
            ):
                break

    for row in sorted(rows, key=_risk_selection_key):
        if len(selected) >= limit:
            break
        _append_unique_option(
            selected,
            row,
            seen_options=seen_options,
            school_counts=school_counts,
            max_per_school=max_per_school,
        )

    required = {"chong", "wen", "bao"}
    if not required.issubset({str(row.get("risk_level")) for row in selected}):
        return []
    return selected[:limit]


def _append_unique_option(
    selected: list[dict[str, Any]],
    row: dict[str, Any],
    *,
    seen_options: set[tuple[Any, Any]],
    school_counts: dict[Any, int],
    max_per_school: int,
) -> bool:
    option_key = (
        row.get("school_id"),
        row.get("major_id") or row.get("major_name"),
    )
    if option_key in seen_options:
        return False
    school_key = row.get("school_id") or row.get("school_name")
    if school_counts.get(school_key, 0) >= max_per_school:
        return False
    seen_options.add(option_key)
    school_counts[school_key] = school_counts.get(school_key, 0) + 1
    selected.append(row)
    return True


def _tier_sql() -> str:
    return """
    CASE
        WHEN s.is_985 THEN 4
        WHEN s.is_211 OR s.is_double_first_class THEN 3
        WHEN s.education_level = '本科' THEN 2
        ELSE 1
    END
    """


def _where_common(constraints: dict[str, Any]) -> tuple[list[str], list[Any]]:
    where = ["a.min_score IS NOT NULL", "a.min_score <= %s"]
    params: list[Any] = [_score(constraints)]

    budget = _budget(constraints)
    if budget is not None:
        where.append("(plan.min_tuition IS NULL OR plan.min_tuition <= %s)")
        params.append(budget)

    selected_subjects = constraints.get("selected_subjects")
    if selected_subjects:
        where.append(
            """
            (
                COALESCE(sr.requirement_type, 'unknown') = 'none'
                OR COALESCE(cardinality(sr.normalized_subjects), 0) = 0
                OR (
                    sr.requirement_type = 'all_required'
                    AND sr.normalized_subjects <@ %s::text[]
                )
                OR (
                    sr.requirement_type = 'any_required'
                    AND sr.normalized_subjects && %s::text[]
                )
            )
            """
        )
        params.extend([selected_subjects, selected_subjects])

    return where, params


def _add_province_filter(
    where: list[str],
    params: list[Any],
    constraints: dict[str, Any],
) -> None:
    province = constraints.get("province")
    if province:
        where.append("s.province = %s")
        params.append(province)


def _add_major_filter(
    where: list[str],
    params: list[Any],
    constraints: dict[str, Any],
) -> None:
    major = constraints.get("major")
    if major:
        where.append("a.major_name_raw LIKE %s")
        params.append(f"%{major}%")


def _add_higher_tier_filter(
    where: list[str],
    params: list[Any],
    baseline: list[dict[str, Any]],
) -> None:
    where.append(f"{_tier_sql()} > %s")
    params.append(_max_tier(baseline))


def _add_undergraduate_quality_filters(
    where: list[str],
    params: list[Any],
) -> None:
    where.extend(
        [
            "s.education_level = '本科'",
            "(s.name LIKE %s OR s.name LIKE %s)",
            "NOT (s.name LIKE %s AND s.name NOT LIKE %s)",
        ]
    )
    params.extend(["%大学%", "%医学院%", "%大学%学院%", "%医学院%"])


def _add_major_quality_filters(
    where: list[str],
    params: list[Any],
    *,
    max_major_name_length: int | None,
) -> None:
    if max_major_name_length is not None:
        where.append("char_length(a.major_name_raw) <= %s")
        params.append(max_major_name_length)
    for term in SPECIAL_MAJOR_TERMS:
        where.append("a.major_name_raw NOT LIKE %s")
        params.append(f"%{term}%")


def _stage_major_patterns(
    stage: dict[str, Any],
    strict_major: str | None,
) -> tuple[list[str], list[str]]:
    strategy = stage.get("strategy")
    include_patterns = list(stage.get("include_patterns") or [])
    exclude_patterns = list(stage.get("exclude_patterns") or [])
    if strategy == "any_major" or not include_patterns:
        if strict_major:
            exclude_patterns.append(f"%{strict_major}%")
        return [], list(dict.fromkeys(exclude_patterns))
    return list(dict.fromkeys(include_patterns)), list(dict.fromkeys(exclude_patterns))


def _add_stage_major_filters(
    where: list[str],
    params: list[Any],
    *,
    stage: dict[str, Any],
    strict_major: str | None,
) -> None:
    include_patterns, exclude_patterns = _stage_major_patterns(stage, strict_major)
    if include_patterns:
        where.append(
            "("
            + " OR ".join(["a.major_name_raw LIKE %s"] * len(include_patterns))
            + ")"
        )
        params.extend(include_patterns)
    for pattern in exclude_patterns:
        where.append("a.major_name_raw NOT LIKE %s")
        params.append(pattern)


def _fallback_any_major_stage() -> dict[str, Any]:
    return {
        "stage": 5,
        "label": "去除专业限制",
        "strategy": "any_major",
        "include_patterns": [],
        "exclude_patterns": [],
    }


def _major_relaxation_stages(
    constraints: dict[str, Any],
    *,
    major_tree_path: str | Path | None,
) -> list[dict[str, Any]]:
    major = constraints.get("major")
    if not major:
        return [_fallback_any_major_stage()]
    tree_path = Path(major_tree_path or DEFAULT_MAJOR_TREE_PATH)
    if not tree_path.exists():
        return [_fallback_any_major_stage()]
    try:
        stages = build_relaxation_stages(
            str(major),
            path=tree_path,
            include_any_major_stage=True,
        )
    except Exception:
        return [_fallback_any_major_stage()]
    return stages or [_fallback_any_major_stage()]


def _selection_key(row: dict[str, Any]) -> tuple[Any, ...]:
    ranking = row.get("ranking")
    min_score = row.get("min_score")
    return (
        -int(row.get("year") or 0),
        -int(row.get("tier") or 0),
        int(ranking) if ranking is not None else 999999,
        -float(min_score) if min_score is not None else 0.0,
        str(row.get("school_name") or ""),
        str(row.get("major_name") or ""),
    )


def _select_relaxation_rows(
    rows: list[dict[str, Any]],
    *,
    limit: int,
    max_per_school: int,
) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    seen_options: set[tuple[Any, Any]] = set()
    school_counts: dict[Any, int] = {}
    for row in sorted(rows, key=_selection_key):
        option_key = (
            row.get("school_id"),
            row.get("major_id") or row.get("major_name"),
        )
        if option_key in seen_options:
            continue
        school_key = row.get("school_id") or row.get("school_name")
        if school_counts.get(school_key, 0) >= max_per_school:
            continue
        seen_options.add(option_key)
        school_counts[school_key] = school_counts.get(school_key, 0) + 1
        selected.append(row)
        if len(selected) >= limit:
            break
    return selected


async def run_baseline(
    constraints: dict[str, Any],
    db: Any = None,
    limit: int = 3,
) -> list[dict[str, Any]]:
    where, params = _where_common(constraints)
    _add_province_filter(where, params, constraints)
    _add_major_filter(where, params, constraints)
    params.append(limit)

    query = f"{BASE_SELECT}\nWHERE {' AND '.join(where)}\n{BASE_ORDER}"
    return await _fetch(db, query, params)


async def _student_rank_for_score(
    constraints: dict[str, Any],
    *,
    db: Any = None,
) -> int | None:
    province = constraints.get("province")
    score = constraints.get("score")
    if not province or score is None:
        return None
    query = """
    SELECT rank_min, rank_max
    FROM score_rank_segments
    WHERE province = %s
      AND score_min <= %s
      AND score_max >= %s
    ORDER BY year DESC
    LIMIT 1
    """
    rows = await _fetch(db, query, [province, int(score), int(score)])
    if not rows:
        return None
    rank_value = rows[0].get("rank_min") or rows[0].get("rank_max")
    if rank_value is None:
        return None
    return int(float(rank_value))


async def probe_geo_relax(
    constraints: dict[str, Any],
    db: Any = None,
    baseline_results: list[dict[str, Any]] | None = None,
    limit: int = 5,
) -> list[dict[str, Any]]:
    baseline = baseline_results
    if baseline is None:
        baseline = await run_baseline(constraints, db=db)

    where, params = _where_common(constraints)
    _add_major_filter(where, params, constraints)

    province = constraints.get("province")
    if province:
        where.append("s.province <> %s")
        params.append(province)

    _add_higher_tier_filter(where, params, baseline)
    params.append(limit)

    query = f"{BASE_SELECT}\nWHERE {' AND '.join(where)}\n{BASE_ORDER}"
    return await _fetch(db, query, params)


async def probe_major_relax(
    constraints: dict[str, Any],
    db: Any = None,
    baseline_results: list[dict[str, Any]] | None = None,
    limit: int = 5,
) -> list[dict[str, Any]]:
    baseline = baseline_results
    if baseline is None:
        baseline = await run_baseline(constraints, db=db)

    where, params = _where_common(constraints)
    _add_province_filter(where, params, constraints)

    major = constraints.get("major")
    if major:
        where.append("a.major_name_raw NOT LIKE %s")
        params.append(f"%{major}%")

    _add_higher_tier_filter(where, params, baseline)
    params.append(limit)

    query = f"{BASE_SELECT}\nWHERE {' AND '.join(where)}\n{BASE_ORDER}"
    return await _fetch(db, query, params)


async def probe_major_geo_relax(
    constraints: dict[str, Any],
    db: Any = None,
    baseline_results: list[dict[str, Any]] | None = None,
    limit: int = 5,
    recommendation_threshold: int = 10,
    max_per_school: int = 2,
    major_tree_path: str | Path | None = DEFAULT_MAJOR_TREE_PATH,
    max_major_name_length: int | None = 60,
) -> list[dict[str, Any]]:
    """Find tier gains unlocked by relaxing both province and major constraints."""

    baseline = baseline_results
    if baseline is None:
        baseline = await run_baseline(constraints, db=db)

    selection_limit = max(limit, recommendation_threshold)
    selected: list[dict[str, Any]] = []
    for stage in _major_relaxation_stages(
        constraints,
        major_tree_path=major_tree_path,
    ):
        where, params = _where_common(constraints)
        _add_undergraduate_quality_filters(where, params)
        _add_major_quality_filters(
            where,
            params,
            max_major_name_length=max_major_name_length,
        )
        _add_stage_major_filters(
            where,
            params,
            stage=stage,
            strict_major=constraints.get("major"),
        )
        _add_higher_tier_filter(where, params, baseline)
        params.append(max(selection_limit * 4, 40))

        query = f"{BASE_SELECT}\nWHERE {' AND '.join(where)}\n{MAJOR_GEO_ORDER}"
        rows = await _fetch(db, query, params)
        selected = _select_relaxation_rows(
            rows,
            limit=selection_limit,
            max_per_school=max_per_school,
        )
        if len(selected) < recommendation_threshold:
            selected = []
            continue
        if selected:
            for row in selected:
                row["relaxation_stage"] = stage.get("stage")
                row["relaxation_stage_label"] = stage.get("label")
                row["relaxation_strategy"] = stage.get("strategy")
            break

    return selected[:limit]


async def probe_risk_band_relax(
    constraints: dict[str, Any],
    db: Any = None,
    limit: int = 6,
    max_per_school: int = 2,
) -> list[dict[str, Any]]:
    """Find a chong/wen/bao portfolio under existing hard constraints."""

    risk_preference = str(constraints.get("risk_preference") or "").lower()
    if risk_preference not in {"conservative", "low", "stable"}:
        return []

    score = _score(constraints)
    student_rank = await _student_rank_for_score(constraints, db=db)
    where, params = _where_common(constraints)
    _add_province_filter(where, params, constraints)
    _add_major_filter(where, params, constraints)
    _add_undergraduate_quality_filters(where, params)
    _add_major_quality_filters(where, params, max_major_name_length=60)
    params.append(max(limit * 8, 60))

    query = f"{BASE_SELECT}\nWHERE {' AND '.join(where)}\n{MAJOR_GEO_ORDER}"
    rows = await _fetch(db, query, params)
    annotated = [
        _annotate_risk_row(row, score=score, student_rank=student_rank) for row in rows
    ]
    return _select_risk_portfolio(
        annotated,
        limit=limit,
        max_per_school=max_per_school,
    )


async def run_all_probes(
    constraints: dict[str, Any],
    db: Any = None,
) -> dict[str, list[dict[str, Any]]]:
    baseline = await run_baseline(constraints, db=db)
    geo_relax, major_relax, major_geo_relax, risk_band_relax = await asyncio.gather(
        probe_geo_relax(constraints, db=db, baseline_results=baseline),
        probe_major_relax(constraints, db=db, baseline_results=baseline),
        probe_major_geo_relax(constraints, db=db, baseline_results=baseline),
        probe_risk_band_relax(constraints, db=db),
    )
    return {
        "geo_relax": geo_relax,
        "major_relax": major_relax,
        "major_geo_relax": major_geo_relax,
        "risk_band_relax": risk_band_relax,
    }
