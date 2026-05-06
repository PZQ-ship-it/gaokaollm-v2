import asyncio
from typing import Any

from app.core import db_pg


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


def _where_common(constraints: dict[str, Any]) -> tuple[list[str], list[Any]]:
    where = ["a.min_score IS NOT NULL", "a.min_score <= %s"]
    params: list[Any] = [_score(constraints)]

    budget = _budget(constraints)
    if budget is not None:
        where.append("(plan.min_tuition IS NULL OR plan.min_tuition <= %s)")
        params.append(budget)

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

    where.append("""
    CASE
        WHEN s.is_985 THEN 4
        WHEN s.is_211 OR s.is_double_first_class THEN 3
        WHEN s.education_level = '本科' THEN 2
        ELSE 1
    END > %s
    """)
    params.append(_max_tier(baseline))
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

    where.append("""
    CASE
        WHEN s.is_985 THEN 4
        WHEN s.is_211 OR s.is_double_first_class THEN 3
        WHEN s.education_level = '本科' THEN 2
        ELSE 1
    END > %s
    """)
    params.append(_max_tier(baseline))
    params.append(limit)

    query = f"{BASE_SELECT}\nWHERE {' AND '.join(where)}\n{BASE_ORDER}"
    return await _fetch(db, query, params)


async def run_all_probes(
    constraints: dict[str, Any],
    db: Any = None,
) -> dict[str, list[dict[str, Any]]]:
    baseline = await run_baseline(constraints, db=db)
    geo_relax, major_relax = await asyncio.gather(
        probe_geo_relax(constraints, db=db, baseline_results=baseline),
        probe_major_relax(constraints, db=db, baseline_results=baseline),
    )
    return {
        "geo_relax": geo_relax,
        "major_relax": major_relax,
    }
