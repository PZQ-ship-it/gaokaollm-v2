"""CLI for building an observed major tree from the PostgreSQL admissions DB."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

from gaokaollm_bench.data_gen.major_tree import DEFAULT_CLUSTER_PATH
from gaokaollm_bench.data_gen.major_tree_builder import (
    DEFAULT_OBSERVED_TREE_PATH,
    DEFAULT_UNASSIGNED_PATH,
    auto_assign_unassigned_major_clusters,
    build_observed_major_tree,
    collect_major_name_counts,
    suggest_unassigned_major_clusters,
)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Scan admission_scores.major_name_raw and build an observed major tree."
    )
    parser.add_argument(
        "--base-tree",
        default=str(DEFAULT_CLUSTER_PATH),
        help="Human-reviewed skeleton tree JSON.",
    )
    parser.add_argument(
        "--output",
        default=str(DEFAULT_OBSERVED_TREE_PATH),
        help="Output path for the observed tree JSON.",
    )
    parser.add_argument(
        "--unassigned-output",
        default=str(DEFAULT_UNASSIGNED_PATH),
        help="Output path for unmatched major-name audit JSON.",
    )
    parser.add_argument(
        "--min-count",
        type=int,
        default=1,
        help="Only include major names that appear at least this many times.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Optional cap on distinct DB major names scanned, ordered by frequency.",
    )
    parser.add_argument(
        "--top-unassigned",
        type=int,
        default=300,
        help="Number of unassigned high-frequency names to keep in the audit report.",
    )
    parser.add_argument(
        "--embedding-suggestions",
        action="store_true",
        help="Use EMBEDDING_MODEL to add semantic placement suggestions for unassigned names.",
    )
    parser.add_argument(
        "--embedding-auto-assign",
        action="store_true",
        help="Use EMBEDDING_MODEL to attach all unassigned names to their nearest leaf cluster.",
    )
    parser.add_argument(
        "--embedding-suggestion-limit",
        type=int,
        default=100,
        help="Maximum unassigned names to annotate with embedding suggestions.",
    )
    parser.add_argument(
        "--attach-threshold",
        type=float,
        default=0.82,
        help="Similarity threshold for suggesting attachment to an existing leaf.",
    )
    parser.add_argument(
        "--new-sibling-threshold",
        type=float,
        default=0.68,
        help="Similarity threshold for suggesting a new sibling leaf.",
    )
    parser.add_argument(
        "--embedding-major-batch-size",
        type=int,
        default=256,
        help="Number of unassigned major names embedded per request in auto-assign mode.",
    )
    return parser.parse_args(argv)


async def _main_async(args: argparse.Namespace) -> tuple[dict, list[dict]]:
    from app.core.db_pg import close_pool, fetch_query

    rows = await collect_major_name_counts(
        fetch_query,
        min_count=args.min_count,
        limit=args.limit,
    )
    try:
        observed_tree, unassigned = build_observed_major_tree(
            rows,
            base_tree_path=args.base_tree,
            top_unassigned=args.top_unassigned,
        )
        if args.embedding_auto_assign and unassigned:
            from gaokaollm_bench.data_gen.major_embedding import OpenAIEmbeddingClient

            unassigned = await auto_assign_unassigned_major_clusters(
                observed_tree,
                unassigned,
                OpenAIEmbeddingClient(),
                attach_threshold=args.attach_threshold,
                new_sibling_threshold=args.new_sibling_threshold,
                major_batch_size=args.embedding_major_batch_size,
            )
            observed_tree["observed_build"]["embedding_auto_assignment_audit"] = unassigned
        elif args.embedding_suggestions and unassigned:
            from gaokaollm_bench.data_gen.major_embedding import OpenAIEmbeddingClient

            unassigned = await suggest_unassigned_major_clusters(
                unassigned,
                OpenAIEmbeddingClient(),
                tree=observed_tree,
                limit=args.embedding_suggestion_limit,
                attach_threshold=args.attach_threshold,
                new_sibling_threshold=args.new_sibling_threshold,
                major_batch_size=args.embedding_major_batch_size,
            )
            observed_tree["observed_build"]["unassigned_top"] = unassigned
        return observed_tree, unassigned
    finally:
        await close_pool()


def main(argv: list[str] | None = None) -> int:
    if os.name == "nt":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    args = parse_args(argv or sys.argv[1:])
    observed_tree, unassigned = asyncio.run(_main_async(args))

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(observed_tree, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    unassigned_path = Path(args.unassigned_output)
    unassigned_path.parent.mkdir(parents=True, exist_ok=True)
    unassigned_path.write_text(
        json.dumps(unassigned, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    build = observed_tree["observed_build"]
    print(
        "Built observed major tree: "
        f"{build['assigned_distinct_names']} assigned, "
        f"{build['unassigned_distinct_names']} unassigned."
    )
    print(f"Tree: {output_path}")
    print(f"Unassigned audit: {unassigned_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
