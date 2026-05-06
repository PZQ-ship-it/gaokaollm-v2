"""Build an observed major tree by scanning real DB major names."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any, Iterable

from gaokaollm_bench.data_gen.db_seeder import _fetch
from gaokaollm_bench.data_gen.major_embedding import (
    EmbeddingClient,
    suggest_major_clusters_by_embedding,
)
from gaokaollm_bench.data_gen.major_tree import (
    DEFAULT_CLUSTER_PATH,
    UnknownMajorError,
    load_major_tree,
    resolve_major_node_from_tree,
)


DEFAULT_OBSERVED_TREE_PATH = Path(__file__).with_name("major_tree_observed.json")
DEFAULT_UNASSIGNED_PATH = Path(__file__).with_name("major_tree_unassigned.json")


def _row_name(row: str | dict[str, Any]) -> str:
    if isinstance(row, str):
        return row.strip()
    return str(row.get("major_name") or row.get("major_name_raw") or row.get("name") or "").strip()


def _row_count(row: str | dict[str, Any]) -> int:
    if isinstance(row, str):
        return 1
    return int(row.get("row_count") or row.get("count") or 1)


def _dedupe_sorted(names: Iterable[str]) -> list[str]:
    return sorted({name for name in names if name})


def _ancestor_ids(node_id: str, nodes: dict[str, dict[str, Any]]) -> list[str]:
    ancestors: list[str] = []
    current = nodes.get(node_id)
    while current and current.get("parent"):
        parent_id = str(current["parent"])
        ancestors.append(parent_id)
        current = nodes.get(parent_id)
    return ancestors


async def collect_major_name_counts(
    db_pool: Any,
    *,
    min_count: int = 1,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    """Collect distinct raw major names and their row counts from admission_scores."""

    if min_count < 1:
        raise ValueError("min_count must be at least 1")
    if limit is not None and limit < 1:
        raise ValueError("limit must be at least 1 when provided")

    limit_clause = "LIMIT %s" if limit is not None else ""
    params: list[Any] = [min_count]
    if limit is not None:
        params.append(limit)
    query = f"""
SELECT
    a.major_name_raw AS major_name,
    COUNT(*) AS row_count
FROM admission_scores a
WHERE a.major_name_raw IS NOT NULL
  AND TRIM(a.major_name_raw) <> ''
GROUP BY a.major_name_raw
HAVING COUNT(*) >= %s
ORDER BY row_count DESC, a.major_name_raw ASC
{limit_clause}
"""
    return await _fetch(db_pool, query, params)


def build_observed_major_tree(
    raw_major_rows: Iterable[str | dict[str, Any]],
    *,
    base_tree: dict[str, Any] | None = None,
    base_tree_path: str | Path | None = None,
    top_unassigned: int = 200,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Attach DB-observed major names to the tree and return unassigned audit rows."""

    if top_unassigned < 1:
        raise ValueError("top_unassigned must be at least 1")

    source_tree = base_tree if base_tree is not None else load_major_tree(base_tree_path)
    observed_tree = deepcopy(source_tree)
    nodes: dict[str, dict[str, Any]] = observed_tree.setdefault("nodes", {})
    assignments: dict[str, list[str]] = {}
    assignment_counts: dict[str, int] = {}
    unassigned: list[dict[str, Any]] = []
    total_rows = 0
    observed_names: list[str] = []

    for raw_row in raw_major_rows:
        major_name = _row_name(raw_row)
        if not major_name:
            continue
        row_count = _row_count(raw_row)
        total_rows += row_count
        observed_names.append(major_name)
        try:
            node = resolve_major_node_from_tree(major_name, source_tree)
        except UnknownMajorError as exc:
            unassigned.append(
                {
                    "major_name": major_name,
                    "row_count": row_count,
                    "suggestions": exc.suggestions,
                }
            )
            continue

        assignments.setdefault(node.id, []).append(major_name)
        assignment_counts[node.id] = assignment_counts.get(node.id, 0) + row_count

    for node_id, names in assignments.items():
        node = nodes[node_id]
        node["observed_names"] = _dedupe_sorted([*node.get("observed_names", []), *names])

    for node_id in sorted(assignments):
        for ancestor_id in _ancestor_ids(node_id, nodes):
            node = nodes[ancestor_id]
            node["observed_names"] = _dedupe_sorted(
                [*node.get("observed_names", []), *nodes[node_id].get("observed_names", [])]
            )

    unassigned.sort(key=lambda row: (-int(row["row_count"]), str(row["major_name"])))
    observed_tree["observed_build"] = {
        "source": "admission_scores.major_name_raw",
        "total_distinct_names": len(set(observed_names)),
        "total_rows": total_rows,
        "assigned_distinct_names": sum(len(set(names)) for names in assignments.values()),
        "unassigned_distinct_names": len(unassigned),
        "assigned_row_count": sum(assignment_counts.values()),
        "unassigned_row_count": sum(int(row["row_count"]) for row in unassigned),
        "assignment_counts": dict(sorted(assignment_counts.items())),
        "unassigned_top": unassigned[:top_unassigned],
        "base_tree": str(Path(base_tree_path) if base_tree_path else DEFAULT_CLUSTER_PATH),
    }

    return observed_tree, unassigned[:top_unassigned]


async def suggest_unassigned_major_clusters(
    unassigned_rows: list[dict[str, Any]],
    embedding_client: EmbeddingClient,
    *,
    tree: dict[str, Any],
    limit: int = 100,
    attach_threshold: float = 0.82,
    new_sibling_threshold: float = 0.68,
    major_batch_size: int | None = None,
) -> list[dict[str, Any]]:
    """Add embedding placement suggestions to high-frequency unassigned names."""

    if limit < 1:
        raise ValueError("limit must be at least 1")

    suggested: list[dict[str, Any]] = []
    rows = unassigned_rows[:limit]
    suggestions = await suggest_major_clusters_by_embedding(
        [str(row["major_name"]) for row in rows],
        embedding_client,
        tree=tree,
        attach_threshold=attach_threshold,
        new_sibling_threshold=new_sibling_threshold,
        major_batch_size=major_batch_size,
    )
    for row, suggestion in zip(rows, suggestions):
        suggested.append(
            {
                **row,
                "embedding_suggestion": {
                    "action": suggestion.action,
                    "target_node_id": suggestion.target_node_id,
                    "target_label": suggestion.target_label,
                    "parent_node_id": suggestion.parent_node_id,
                    "similarity": round(suggestion.similarity, 6),
                    "reasoning": suggestion.reasoning,
                },
            }
        )
    return suggested


async def auto_assign_unassigned_major_clusters(
    observed_tree: dict[str, Any],
    unassigned_rows: list[dict[str, Any]],
    embedding_client: EmbeddingClient,
    *,
    limit: int | None = None,
    attach_threshold: float = 0.82,
    new_sibling_threshold: float = 0.68,
    major_batch_size: int = 256,
) -> list[dict[str, Any]]:
    """Attach unassigned names to their nearest embedding leaf and keep an audit trail."""

    if limit is not None and limit < 1:
        raise ValueError("limit must be at least 1 when provided")
    if major_batch_size < 1:
        raise ValueError("major_batch_size must be at least 1")

    rows = unassigned_rows[:limit] if limit is not None else unassigned_rows
    if not rows:
        return []

    suggestions = await suggest_major_clusters_by_embedding(
        [str(row["major_name"]) for row in rows],
        embedding_client,
        tree=observed_tree,
        attach_threshold=attach_threshold,
        new_sibling_threshold=new_sibling_threshold,
        major_batch_size=major_batch_size,
    )
    nodes: dict[str, dict[str, Any]] = observed_tree.setdefault("nodes", {})
    audit_rows: list[dict[str, Any]] = []
    assigned_counts: dict[str, int] = {}

    for row, suggestion in zip(rows, suggestions):
        node = nodes[suggestion.target_node_id]
        major_name = str(row["major_name"])
        row_count = int(row["row_count"])
        node["observed_names"] = _dedupe_sorted([*node.get("observed_names", []), major_name])
        node.setdefault("embedding_auto_assigned", [])
        node["embedding_auto_assigned"].append(
            {
                "major_name": major_name,
                "row_count": row_count,
                "similarity": round(suggestion.similarity, 6),
            }
        )
        assigned_counts[suggestion.target_node_id] = (
            assigned_counts.get(suggestion.target_node_id, 0) + row_count
        )

        for ancestor_id in _ancestor_ids(suggestion.target_node_id, nodes):
            ancestor = nodes[ancestor_id]
            ancestor["observed_names"] = _dedupe_sorted(
                [*ancestor.get("observed_names", []), major_name]
            )

        audit_rows.append(
            {
                **row,
                "embedding_auto_assignment": {
                    "target_node_id": suggestion.target_node_id,
                    "target_label": suggestion.target_label,
                    "parent_node_id": suggestion.parent_node_id,
                    "similarity": round(suggestion.similarity, 6),
                    "original_action": suggestion.action,
                },
            }
        )

    build = observed_tree.setdefault("observed_build", {})
    build["embedding_auto_assign"] = {
        "assigned_distinct_names": len(audit_rows),
        "assigned_row_count": sum(int(row["row_count"]) for row in rows),
        "assignment_counts": dict(sorted(assigned_counts.items())),
    }
    build["assigned_distinct_names"] = int(build.get("assigned_distinct_names") or 0) + len(audit_rows)
    build["unassigned_distinct_names"] = max(
        0,
        int(build.get("unassigned_distinct_names") or 0) - len(audit_rows),
    )
    build["assigned_row_count"] = int(build.get("assigned_row_count") or 0) + sum(
        int(row["row_count"]) for row in rows
    )
    build["unassigned_row_count"] = max(
        0,
        int(build.get("unassigned_row_count") or 0) - sum(int(row["row_count"]) for row in rows),
    )
    for node_id, row_count in assigned_counts.items():
        current_counts = build.setdefault("assignment_counts", {})
        current_counts[node_id] = int(current_counts.get(node_id) or 0) + row_count
    build["unassigned_top"] = []

    return audit_rows
