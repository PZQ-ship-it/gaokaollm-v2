"""Database-backed seed discovery for benchmark persona generation."""

from __future__ import annotations

from typing import Any


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
LIMIT 1
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
        raise TypeError("db_pool must provide fetch_query, fetch, connection, or be callable")

    return [dict(row) for row in rows]


def _tier(row: dict[str, Any] | None) -> int:
    if not row:
        return 0
    return int(row.get("tier") or 0)


async def find_pareto_gaps(db_pool: Any, score: int, prov: str) -> dict[str, Any]:
    """Find a real school-tier jump unlocked by relaxing the province constraint."""

    local_query = f"{BASE_SELECT}  AND s.province = %s\n{BASE_ORDER}"
    national_query = f"{BASE_SELECT}\n{BASE_ORDER}"

    local_rows = await _fetch(db_pool, local_query, [score, prov])
    national_rows = await _fetch(db_pool, national_query, [score])

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

