from __future__ import annotations

import argparse
import asyncio
from dataclasses import dataclass
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
from app.core.embedding_client import (  # noqa: E402
    OpenAIEmbeddingClient,
    ensure_embedding_dimension,
    vector_to_pg_literal,
)
from scripts.knowledge_embedding_targets import (  # noqa: E402
    KnowledgeEmbeddingTargets,
    targets_from_trace,
)


load_dotenv()


@dataclass(frozen=True)
class KnowledgeDoc:
    id: int
    doc_type: str
    title: str
    content: str

    def embedding_text(self) -> str:
        title = self.title.strip()
        content = self.content.strip()
        if title:
            return f"{self.doc_type}｜{title}\n{content}"
        return f"{self.doc_type}\n{content}"


def _parse_int_csv(values: list[str]) -> set[int]:
    parsed: set[int] = set()
    for value in values:
        for item in str(value or "").split(","):
            item = item.strip()
            if not item:
                continue
            parsed.add(int(item))
    return parsed


def _targets_from_args(args: argparse.Namespace) -> KnowledgeEmbeddingTargets:
    targets = KnowledgeEmbeddingTargets()
    if args.trace:
        targets = targets_from_trace(args.trace)
    targets.school_ids.update(_parse_int_csv(args.school_id or []))
    targets.major_ids.update(_parse_int_csv(args.major_id or []))
    for title in args.major_title or []:
        if title.strip():
            targets.major_titles.add(title.strip())
    return targets


def _fetch_docs(
    *,
    limit: int | None,
    doc_type: str | None,
    targets: KnowledgeEmbeddingTargets | None = None,
    linked_only: bool = False,
) -> list[KnowledgeDoc]:
    where = ["embedding IS NULL"]
    params: list[Any] = []
    if doc_type:
        where.append("doc_type = %s")
        params.append(doc_type)
    if linked_only:
        where.append("(school_id IS NOT NULL OR major_id IS NOT NULL)")
    if targets and not targets.is_empty():
        target_clauses: list[str] = []
        if targets.school_ids:
            target_clauses.append("school_id = ANY(%s)")
            params.append(sorted(targets.school_ids))
        if targets.major_ids:
            target_clauses.append("major_id = ANY(%s)")
            params.append(sorted(targets.major_ids))
        if targets.major_titles:
            target_clauses.append("title = ANY(%s)")
            params.append(sorted(targets.major_titles))
        where.append("(" + " OR ".join(target_clauses) + ")")
    limit_sql = ""
    if limit is not None:
        limit_sql = "LIMIT %s"
        params.append(limit)
    query = f"""
SELECT id, doc_type, COALESCE(title, '') AS title, content
FROM knowledge_documents
WHERE {" AND ".join(where)}
ORDER BY id
{limit_sql}
"""
    with psycopg.connect(get_database_url(), row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute(query, params)
            rows = cur.fetchall()
    return [
        KnowledgeDoc(
            id=int(row["id"]),
            doc_type=str(row["doc_type"]),
            title=str(row["title"] or ""),
            content=str(row["content"] or ""),
        )
        for row in rows
    ]


def _update_vectors(docs: list[KnowledgeDoc], vectors: list[list[float]]) -> None:
    with psycopg.connect(get_database_url(), autocommit=False) as conn:
        with conn.cursor() as cur:
            for doc, vector in zip(docs, vectors):
                ensure_embedding_dimension(vector, label=f"knowledge_document:{doc.id}")
                cur.execute(
                    """
                    UPDATE knowledge_documents
                    SET embedding = %s::vector
                    WHERE id = %s
                    """,
                    (vector_to_pg_literal(vector), doc.id),
                )
        conn.commit()


async def backfill(args: argparse.Namespace) -> int:
    targets = _targets_from_args(args)
    docs = _fetch_docs(
        limit=args.limit,
        doc_type=args.doc_type,
        targets=targets,
        linked_only=bool(args.linked_only),
    )
    if args.trace:
        print("[knowledge-embedding] trace_targets=" + str(targets.as_jsonable()))
    print(f"[knowledge-embedding] pending={len(docs)}")
    if args.dry_run or args.report_only or not docs:
        return 0

    client = OpenAIEmbeddingClient()
    total = 0
    for start in range(0, len(docs), args.batch_size):
        batch = docs[start : start + args.batch_size]
        vectors = await client.embed([doc.embedding_text() for doc in batch])
        if len(vectors) != len(batch):
            raise RuntimeError(
                f"Embedding API returned {len(vectors)} vectors for {len(batch)} docs."
            )
        _update_vectors(batch, vectors)
        total += len(batch)
        print(f"[knowledge-embedding] updated={total}/{len(docs)}")
    return total


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Backfill knowledge_documents.embedding with OpenAI-compatible embeddings."
    )
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--doc-type", default=None)
    parser.add_argument("--school-id", action="append", default=[])
    parser.add_argument("--major-id", action="append", default=[])
    parser.add_argument("--major-title", action="append", default=[])
    parser.add_argument("--trace", default="")
    parser.add_argument("--linked-only", action="store_true")
    parser.add_argument("--report-only", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if args.limit is not None and args.limit < 1:
        parser.error("--limit must be positive when provided")
    if args.batch_size < 1:
        parser.error("--batch-size must be positive")
    return args


def main() -> None:
    args = parse_args()
    updated = asyncio.run(backfill(args))
    print(f"[knowledge-embedding] done updated={updated}")


if __name__ == "__main__":
    main()
