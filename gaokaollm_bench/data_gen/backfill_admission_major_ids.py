"""Backfill raw admission major IDs from normalized catalog major names."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

import psycopg
from dotenv import load_dotenv
from psycopg.rows import dict_row


DEFAULT_DATABASE_URL = "postgresql://postgres@127.0.0.1:55432/gaokao_recommendation"
DEFAULT_AUDIT = Path("gaokaollm_bench/outputs/admission_major_id_backfill_audit.json")
TABLES = ("admission_scores", "admission_plans")


CANONICAL_MAJOR_CTE = """
WITH canonical_majors AS (
    SELECT DISTINCT ON (normalized_name)
        id AS major_id,
        name AS major_name,
        normalized_name,
        level,
        major_code
    FROM majors
    WHERE normalized_name IS NOT NULL
      AND trim(normalized_name) <> ''
    ORDER BY
        normalized_name,
        CASE
            WHEN level = '本科' THEN 0
            WHEN level IS NULL THEN 1
            ELSE 2
        END,
        CASE
            WHEN major_code ~ '^0' THEN 0
            ELSE 1
        END,
        id
),
resolved AS (
    SELECT
        t.id,
        t.major_name_raw,
        cm.major_id,
        cm.major_name,
        cm.level,
        cm.major_code,
        regexp_replace(
            regexp_replace(
                regexp_replace(
                    replace(replace(coalesce(t.major_name_raw, ''), '（', '('), '）', ')'),
                    '\\(.*$',
                    ''
                ),
                '\\s+',
                '',
                'g'
            ),
            '专业$',
            ''
        ) AS normalized_raw_major
    FROM {table} t
    JOIN canonical_majors cm
      ON cm.normalized_name = regexp_replace(
            regexp_replace(
                regexp_replace(
                    replace(replace(coalesce(t.major_name_raw, ''), '（', '('), '）', ')'),
                    '\\(.*$',
                    ''
                ),
                '\\s+',
                '',
                'g'
            ),
            '专业$',
            ''
        )
    WHERE t.major_id IS NULL
      AND t.major_name_raw IS NOT NULL
)
"""


def _connect(database_url: str) -> psycopg.Connection[Any]:
    return psycopg.connect(database_url, row_factory=dict_row)


def _candidate_summary(conn: psycopg.Connection[Any], table: str) -> dict[str, Any]:
    query = (
        CANONICAL_MAJOR_CTE.format(table=table)
        + """
SELECT
    count(*) AS rows_resolvable,
    count(DISTINCT normalized_raw_major) AS distinct_raw_majors,
    count(*) FILTER (WHERE major_name_raw LIKE '%%(%%' OR major_name_raw LIKE '%%（%%') AS rows_with_parentheses
FROM resolved
"""
    )
    with conn.cursor() as cur:
        cur.execute(query)
        return dict(cur.fetchone() or {})


def _sample_rows(
    conn: psycopg.Connection[Any], table: str, limit: int
) -> list[dict[str, Any]]:
    query = (
        CANONICAL_MAJOR_CTE.format(table=table)
        + """
SELECT id, major_name_raw, normalized_raw_major, major_id, major_name, level, major_code
FROM resolved
ORDER BY id
LIMIT %s
"""
    )
    with conn.cursor() as cur:
        cur.execute(query, (limit,))
        return [dict(row) for row in cur.fetchall()]


def _apply_table(conn: psycopg.Connection[Any], table: str) -> int:
    query = (
        CANONICAL_MAJOR_CTE.format(table=table)
        + f"""
UPDATE {table} AS t
SET major_id = resolved.major_id
FROM resolved
WHERE t.id = resolved.id
  AND t.major_id IS NULL
"""
    )
    with conn.cursor() as cur:
        cur.execute(query)
        return int(cur.rowcount or 0)


def _coverage(conn: psycopg.Connection[Any]) -> dict[str, Any]:
    query = """
SELECT
    count(*) AS total_scores,
    count(*) FILTER (WHERE a.major_id IS NOT NULL) AS scores_with_major_id,
    count(*) FILTER (WHERE a.major_id IS NULL) AS scores_without_major_id,
    count(*) FILTER (
        WHERE a.major_name_raw LIKE '%%软件%%' AND a.major_id IS NOT NULL
    ) AS software_scores_with_major_id,
    count(*) FILTER (
        WHERE a.major_name_raw LIKE '%%临床%%' AND a.major_id IS NOT NULL
    ) AS clinical_scores_with_major_id,
    count(*) FILTER (
        WHERE EXISTS (
            SELECT 1
            FROM school_major_quality_profiles p
            WHERE p.school_id = a.school_id
              AND p.major_id = a.major_id
        )
    ) AS scores_joining_quality_profiles
FROM admission_scores a
"""
    with conn.cursor() as cur:
        cur.execute(query)
        return dict(cur.fetchone() or {})


def run(args: argparse.Namespace) -> dict[str, Any]:
    database_url = (
        args.database_url or os.getenv("DATABASE_URL") or DEFAULT_DATABASE_URL
    )
    tables = args.tables or list(TABLES)
    invalid = sorted(set(tables) - set(TABLES))
    if invalid:
        raise ValueError(f"Unsupported table(s): {invalid}")

    with _connect(database_url) as conn:
        before = _coverage(conn)
        table_reports = {}
        for table in tables:
            summary = _candidate_summary(conn, table)
            samples = _sample_rows(conn, table, args.sample)
            updated = _apply_table(conn, table) if args.apply else 0
            table_reports[table] = {
                "candidate_summary": summary,
                "updated_rows": updated,
                "samples": samples,
            }
        if args.apply:
            conn.commit()
        else:
            conn.rollback()
        after = _coverage(conn)

    return {
        "applied": bool(args.apply),
        "tables": table_reports,
        "coverage_before": before,
        "coverage_after": after,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--database-url", default=os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL)
    )
    parser.add_argument("--tables", nargs="+", choices=TABLES, default=list(TABLES))
    parser.add_argument("--sample", type=int, default=12)
    parser.add_argument("--audit", default=str(DEFAULT_AUDIT))
    parser.add_argument("--apply", action="store_true")
    return parser.parse_args()


def main() -> None:
    load_dotenv()
    args = parse_args()
    report = run(args)
    audit = Path(args.audit)
    audit.parent.mkdir(parents=True, exist_ok=True)
    audit.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, default=str) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, indent=2, default=str))
    print(f"Wrote audit to {audit}")


if __name__ == "__main__":
    main()
