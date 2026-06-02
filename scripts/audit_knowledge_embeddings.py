from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import psycopg
from dotenv import load_dotenv
from psycopg.rows import dict_row

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core.db_pg import get_database_url  # noqa: E402
from scripts.knowledge_embedding_targets import (  # noqa: E402
    KnowledgeEmbeddingTargets,
    targets_from_trace,
)


load_dotenv()


def _fetch_one(cur: Any, query: str, params: list[Any] | None = None) -> dict[str, Any]:
    cur.execute(query, params or [])
    row = cur.fetchone()
    return dict(row or {})


def _fetch_all(
    cur: Any, query: str, params: list[Any] | None = None
) -> list[dict[str, Any]]:
    cur.execute(query, params or [])
    return [dict(row) for row in cur.fetchall()]


def _coverage_row(total: int, missing: int) -> dict[str, Any]:
    covered = max(0, total - missing)
    ratio = round((covered / total), 6) if total else None
    return {
        "total": total,
        "with_embedding": covered,
        "missing_embedding": missing,
        "coverage_ratio": ratio,
    }


def _target_where(targets: KnowledgeEmbeddingTargets) -> tuple[str, list[Any]]:
    clauses: list[str] = []
    params: list[Any] = []
    if targets.school_ids:
        clauses.append("school_id = ANY(%s)")
        params.append(sorted(targets.school_ids))
    if targets.major_ids:
        clauses.append("major_id = ANY(%s)")
        params.append(sorted(targets.major_ids))
    if targets.major_titles:
        clauses.append("title = ANY(%s)")
        params.append(sorted(targets.major_titles))
    if not clauses:
        return "FALSE", []
    return "(" + " OR ".join(clauses) + ")", params


def audit(trace_path: str | None = None) -> dict[str, Any]:
    targets = (
        targets_from_trace(trace_path) if trace_path else KnowledgeEmbeddingTargets()
    )
    with psycopg.connect(get_database_url(), row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            overall_raw = _fetch_one(
                cur,
                """
                SELECT
                  count(*)::int AS total,
                  count(*) FILTER (WHERE embedding IS NULL)::int AS missing
                FROM knowledge_documents
                """,
            )
            by_type = _fetch_all(
                cur,
                """
                SELECT
                  doc_type,
                  count(*)::int AS total,
                  count(*) FILTER (WHERE embedding IS NULL)::int AS missing
                FROM knowledge_documents
                GROUP BY doc_type
                ORDER BY doc_type
                """,
            )
            target_summary: dict[str, Any] | None = None
            if not targets.is_empty():
                where_sql, params = _target_where(targets)
                target_raw = _fetch_one(
                    cur,
                    f"""
                    SELECT
                      count(*)::int AS total,
                      count(*) FILTER (WHERE embedding IS NULL)::int AS missing
                    FROM knowledge_documents
                    WHERE {where_sql}
                    """,
                    params,
                )
                target_by_type = _fetch_all(
                    cur,
                    f"""
                    SELECT
                      doc_type,
                      count(*)::int AS total,
                      count(*) FILTER (WHERE embedding IS NULL)::int AS missing
                    FROM knowledge_documents
                    WHERE {where_sql}
                    GROUP BY doc_type
                    ORDER BY doc_type
                    """,
                    params,
                )
                target_summary = {
                    "trace_path": str(trace_path),
                    "targets": targets.as_jsonable(),
                    "coverage": _coverage_row(
                        int(target_raw.get("total") or 0),
                        int(target_raw.get("missing") or 0),
                    ),
                    "by_type": [
                        {
                            "doc_type": row["doc_type"],
                            **_coverage_row(
                                int(row.get("total") or 0),
                                int(row.get("missing") or 0),
                            ),
                        }
                        for row in target_by_type
                    ],
                }
    return {
        "overall": _coverage_row(
            int(overall_raw.get("total") or 0),
            int(overall_raw.get("missing") or 0),
        ),
        "by_type": [
            {
                "doc_type": row["doc_type"],
                **_coverage_row(
                    int(row.get("total") or 0),
                    int(row.get("missing") or 0),
                ),
            }
            for row in by_type
        ],
        "targeted": target_summary,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Audit knowledge_documents embedding coverage."
    )
    parser.add_argument(
        "--trace", default="", help="Optional trace JSON to audit targeted docs."
    )
    parser.add_argument("--output", default="", help="Optional JSON output path.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = audit(args.trace or None)
    if args.output:
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(
            json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
