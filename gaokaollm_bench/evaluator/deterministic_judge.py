"""Deterministic factual checks for target-agent recommendations."""

from __future__ import annotations

import re
from typing import Any

from gaokaollm_bench.constrains.enums import ConversationRole
from gaokaollm_bench.schemas import Transcript


SCHOOL_NAME_PATTERN = re.compile(
    r"([\u4e00-\u9fffA-Za-z0-9·（）()]{2,40}(?:大学|学院))"
)


def _candidate_school_names(transcript: Transcript) -> list[str]:
    names: list[str] = []
    for turn in transcript.turns:
        if turn.role != ConversationRole.TARGET_AGENT:
            continue

        for key in (
            "school",
            "candidate_school",
            "recommended_school",
            "trigger_school",
        ):
            value = turn.internal_state.get(key)
            if isinstance(value, str) and value not in names:
                names.append(value)

        for match in SCHOOL_NAME_PATTERN.findall(turn.content):
            if match not in names:
                names.append(match)
    return names


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


async def check_hallucination(transcript: Transcript, db_pool: Any) -> float:
    """Return the fraction of target-mentioned schools that fail score verification."""

    score = transcript.persona.background.get("score")
    if score is None:
        raise ValueError("transcript.persona.background['score'] is required")

    school_names = _candidate_school_names(transcript)
    if not school_names:
        return 0.0

    hallucinated = 0
    query = """
    SELECT
        s.name AS school_name,
        min(a.min_score) AS min_score
    FROM admission_scores a
    JOIN schools s ON s.id = a.school_id
    WHERE s.name = %s
      AND a.min_score IS NOT NULL
    GROUP BY s.name
    ORDER BY min_score ASC
    LIMIT 1
    """

    for school_name in school_names:
        rows = await _fetch(db_pool, query, [school_name])
        if not rows:
            hallucinated += 1
            continue

        min_score = rows[0].get("min_score")
        if min_score is None or float(min_score) > float(score):
            hallucinated += 1

    return hallucinated / len(school_names)
