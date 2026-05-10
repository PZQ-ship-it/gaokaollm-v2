"""Build normalized major employment outcome profiles from imported raw rows."""

from __future__ import annotations

import argparse
import json
import os
import re
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import psycopg
from psycopg.types.json import Jsonb


DEFAULT_DATABASE_URL = "postgresql://postgres@127.0.0.1:55432/gaokao_recommendation"
SCHEMA_SQL = Path("db/migrations/003_employment_outcome_profiles.sql")


@dataclass(frozen=True)
class EmploymentOutcomeProfile:
    major_id: int
    major_name: str
    employment_rank: int | None
    employment_rank_desc: str | None
    top_city: str | None
    top_industry: str | None
    industry_distribution: dict[str, Any]
    city_distribution: dict[str, Any]
    job_distribution: dict[str, Any]
    salary_distribution: dict[str, Any]
    salary_history: dict[str, Any]
    outcome_score: float
    outcome_tier: str
    evidence_sources: list[str]
    raw: dict[str, Any]


def parse_employment_rank(value: Any) -> int | None:
    """Extract a comparable employment rank from imported text."""

    if value is None:
        return None
    text = str(value).strip()
    if not text or text.lower() == "nan":
        return None
    match = re.search(r"\d+", text)
    if not match:
        return None
    rank = int(match.group(0))
    return rank if rank > 0 else None


def outcome_score_from_rank(rank: int | None, evidence_count: int = 0) -> float:
    """Score is intentionally simple and monotonic: lower rank is better."""

    if rank is None:
        return min(68.0, 55.0 + evidence_count * 2.5)
    base = max(45.0, 101.0 - float(rank))
    bonus = min(6.0, evidence_count * 1.0)
    return round(min(100.0, base + bonus), 3)


def outcome_tier(score: float) -> str:
    if score >= 90:
        return "A"
    if score >= 80:
        return "B"
    if score >= 70:
        return "C"
    return "D"


def ensure_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if value in (None, ""):
        return {}
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return {"text": value}
        return parsed if isinstance(parsed, dict) else {"items": parsed}
    return {"value": value}


def evidence_sources_for_row(row: dict[str, Any]) -> list[str]:
    evidence: list[str] = []
    if parse_employment_rank(row.get("employment_rank")) is not None:
        evidence.append(
            f"employment_rank={parse_employment_rank(row.get('employment_rank'))}"
        )
    if row.get("employment_rank_desc"):
        evidence.append(f"rank_desc={row['employment_rank_desc']}")
    if row.get("top_city"):
        evidence.append(f"top_city={row['top_city']}")
    if row.get("top_industry"):
        evidence.append(f"top_industry={row['top_industry']}")
    for key, label in (
        ("industry_distribution", "industry_distribution"),
        ("city_distribution", "city_distribution"),
        ("job_distribution", "job_distribution"),
        ("salary_distribution", "salary_distribution"),
    ):
        if ensure_dict(row.get(key)):
            evidence.append(label)
    source_file = row.get("source_file")
    if source_file:
        evidence.append(f"source={source_file}")
    return evidence


def normalize_employment_rows(
    rows: list[dict[str, Any]],
) -> list[EmploymentOutcomeProfile]:
    """Collapse imported rows into one best employment profile per major."""

    by_major: dict[int, list[dict[str, Any]]] = defaultdict(list)
    major_names: dict[int, str] = {}
    for row in rows:
        major_id = row.get("major_id")
        if major_id is None:
            continue
        major_id_int = int(major_id)
        by_major[major_id_int].append(row)
        major_names[major_id_int] = str(
            row.get("major_name") or row.get("major_name_raw") or major_id_int
        )

    profiles: list[EmploymentOutcomeProfile] = []
    for major_id, grouped in by_major.items():
        best_row: dict[str, Any] | None = None
        best_score = -1.0
        best_rank: int | None = None
        for row in grouped:
            evidence = evidence_sources_for_row(row)
            rank = parse_employment_rank(row.get("employment_rank"))
            score = outcome_score_from_rank(rank, evidence_count=len(evidence))
            if score > best_score or (
                score == best_score
                and rank is not None
                and (best_rank is None or rank < best_rank)
            ):
                best_score = score
                best_rank = rank
                best_row = row

        if best_row is None:
            continue
        evidence = evidence_sources_for_row(best_row)
        score = outcome_score_from_rank(best_rank, evidence_count=len(evidence))
        raw = ensure_dict(best_row.get("raw"))
        if not raw:
            raw = dict(best_row)
        profiles.append(
            EmploymentOutcomeProfile(
                major_id=major_id,
                major_name=major_names[major_id],
                employment_rank=best_rank,
                employment_rank_desc=best_row.get("employment_rank_desc"),
                top_city=best_row.get("top_city"),
                top_industry=best_row.get("top_industry"),
                industry_distribution=ensure_dict(
                    best_row.get("industry_distribution")
                ),
                city_distribution=ensure_dict(best_row.get("city_distribution")),
                job_distribution=ensure_dict(best_row.get("job_distribution")),
                salary_distribution=ensure_dict(best_row.get("salary_distribution")),
                salary_history=ensure_dict(best_row.get("salary_history")),
                outcome_score=score,
                outcome_tier=outcome_tier(score),
                evidence_sources=evidence,
                raw=raw,
            )
        )
    return profiles


def _load_schema(conn: psycopg.Connection[Any]) -> None:
    sql = SCHEMA_SQL.read_text(encoding="utf-8")
    with conn.cursor() as cur:
        cur.execute(sql)
    conn.commit()


def _load_raw_rows(conn: psycopg.Connection[Any]) -> list[dict[str, Any]]:
    with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
        cur.execute(
            """
            SELECT
                mep.major_id,
                COALESCE(m.name, mep.major_name_raw) AS major_name,
                mep.major_name_raw,
                mep.employment_rank,
                mep.employment_rank_desc,
                mep.top_city,
                mep.top_industry,
                mep.industry_distribution,
                mep.city_distribution,
                mep.job_distribution,
                mep.salary_distribution,
                mep.salary_history,
                mep.source_file,
                mep.raw
            FROM major_employment_profiles mep
            LEFT JOIN majors m ON m.id = mep.major_id
            WHERE mep.major_id IS NOT NULL
            """
        )
        return [dict(row) for row in cur.fetchall()]


def rebuild_employment_outcome_profiles(
    database_url: str | None = None,
    *,
    ensure_schema: bool = True,
) -> dict[str, int]:
    database_url = database_url or os.getenv("DATABASE_URL") or DEFAULT_DATABASE_URL
    with psycopg.connect(database_url) as conn:
        if ensure_schema:
            _load_schema(conn)
        rows = _load_raw_rows(conn)
        profiles = normalize_employment_rows(rows)
        with conn.cursor() as cur:
            cur.execute("DELETE FROM major_employment_outcome_profiles")
            cur.executemany(
                """
                INSERT INTO major_employment_outcome_profiles (
                    major_id, major_name, employment_rank, employment_rank_desc,
                    top_city, top_industry, industry_distribution, city_distribution,
                    job_distribution, salary_distribution, salary_history,
                    outcome_score, outcome_tier, evidence_sources, raw
                )
                VALUES (
                    %s, %s, %s, %s,
                    %s, %s, %s, %s,
                    %s, %s, %s,
                    %s, %s, %s, %s
                )
                ON CONFLICT (major_id) DO UPDATE SET
                    major_name = EXCLUDED.major_name,
                    employment_rank = EXCLUDED.employment_rank,
                    employment_rank_desc = EXCLUDED.employment_rank_desc,
                    top_city = EXCLUDED.top_city,
                    top_industry = EXCLUDED.top_industry,
                    industry_distribution = EXCLUDED.industry_distribution,
                    city_distribution = EXCLUDED.city_distribution,
                    job_distribution = EXCLUDED.job_distribution,
                    salary_distribution = EXCLUDED.salary_distribution,
                    salary_history = EXCLUDED.salary_history,
                    outcome_score = EXCLUDED.outcome_score,
                    outcome_tier = EXCLUDED.outcome_tier,
                    evidence_sources = EXCLUDED.evidence_sources,
                    raw = EXCLUDED.raw
                """,
                [
                    (
                        profile.major_id,
                        profile.major_name,
                        profile.employment_rank,
                        profile.employment_rank_desc,
                        profile.top_city,
                        profile.top_industry,
                        Jsonb(profile.industry_distribution),
                        Jsonb(profile.city_distribution),
                        Jsonb(profile.job_distribution),
                        Jsonb(profile.salary_distribution),
                        Jsonb(profile.salary_history),
                        profile.outcome_score,
                        profile.outcome_tier,
                        Jsonb(profile.evidence_sources),
                        Jsonb(profile.raw),
                    )
                    for profile in profiles
                ],
            )
        conn.commit()
    return {
        "major_employment_profiles": len(rows),
        "major_employment_outcome_profiles": len(profiles),
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Rebuild normalized major employment outcome profiles."
    )
    parser.add_argument("--database-url", default=None)
    parser.add_argument("--skip-schema", action="store_true")
    args = parser.parse_args()
    result = rebuild_employment_outcome_profiles(
        args.database_url,
        ensure_schema=not args.skip_schema,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
