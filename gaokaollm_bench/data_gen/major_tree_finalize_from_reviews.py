"""Build a final observed major tree from reviewed probe candidates."""

from __future__ import annotations

import argparse
import json
from copy import deepcopy
from pathlib import Path
from typing import Any, Iterable

from gaokaollm_bench.data_gen.major_tree import load_major_tree


DEFAULT_BASE_TREE = Path("gaokaollm_bench/sample_data/major_tree_observed_full.json")
DEFAULT_REVIEWS = Path("gaokaollm_bench/outputs/major_probe_review_candidates_llm_reviewed.json")
DEFAULT_OUTPUT = Path("gaokaollm_bench/outputs/major_tree_final_reviewed.json")
DEFAULT_AUDIT = Path("gaokaollm_bench/outputs/major_tree_final_reviewed_audit.json")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Attach reviewed unassigned majors to an observed major tree."
    )
    parser.add_argument("--base-tree", default=str(DEFAULT_BASE_TREE))
    parser.add_argument("--reviews", default=str(DEFAULT_REVIEWS))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--audit-output", default=str(DEFAULT_AUDIT))
    parser.add_argument(
        "--statuses",
        nargs="+",
        default=["pending", "llm_reviewed", "low_confidence"],
        help="Review statuses to apply. Defaults to all reviewed-candidate statuses.",
    )
    parser.add_argument(
        "--skip-null-label",
        action="store_true",
        default=True,
        help="Skip rows without recommended_label.",
    )
    parser.add_argument(
        "--fail-on-unknown-label",
        action="store_true",
        help="Raise instead of skipping rows whose recommended_label is not in the tree.",
    )
    return parser.parse_args()


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


def _load_reviews(path: Path) -> list[dict[str, Any]]:
    rows = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(rows, list):
        raise ValueError("Review JSON must be a list")
    return rows


def _review_source(row: dict[str, Any]) -> str:
    if row.get("llm_review"):
        return "llm"
    if row.get("review_decision"):
        return "manual_or_llm_decision"
    return "probe"


def finalize_tree(
    *,
    base_tree: dict[str, Any],
    review_rows: list[dict[str, Any]],
    statuses: set[str],
    fail_on_unknown_label: bool = False,
) -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, Any]]:
    final_tree = deepcopy(base_tree)
    nodes: dict[str, dict[str, Any]] = final_tree.setdefault("nodes", {})
    audit_rows: list[dict[str, Any]] = []
    skipped_rows: list[dict[str, Any]] = []
    assignment_counts: dict[str, int] = {}

    for row in review_rows:
        status = row.get("review_status")
        if status not in statuses:
            continue

        major_name = str(row.get("major_name") or "").strip()
        target_label = row.get("recommended_label")
        if not major_name or not target_label:
            skipped_rows.append({"major_name": major_name, "reason": "missing recommended_label"})
            continue

        target_label = str(target_label)
        if target_label not in nodes:
            skipped = {
                "major_name": major_name,
                "recommended_label": target_label,
                "reason": "unknown recommended_label",
            }
            if fail_on_unknown_label:
                raise KeyError(json.dumps(skipped, ensure_ascii=False))
            skipped_rows.append(skipped)
            continue

        row_count = int(row.get("row_count") or 0)
        node = nodes[target_label]
        node["observed_names"] = _dedupe_sorted([*node.get("observed_names", []), major_name])
        node.setdefault("probe_review_assigned", [])
        node["probe_review_assigned"].append(
            {
                "major_name": major_name,
                "row_count": row_count,
                "review_status": status,
                "source": _review_source(row),
                "recommended_probability": row.get("recommended_probability"),
                "review_decision": row.get("review_decision"),
                "review_notes": row.get("review_notes") or "",
            }
        )

        for ancestor_id in _ancestor_ids(target_label, nodes):
            ancestor = nodes[ancestor_id]
            ancestor["observed_names"] = _dedupe_sorted(
                [*ancestor.get("observed_names", []), major_name]
            )

        assignment_counts[target_label] = assignment_counts.get(target_label, 0) + row_count
        audit_rows.append(
            {
                "major_name": major_name,
                "row_count": row_count,
                "target_label": target_label,
                "target_label_name": node.get("label") or target_label,
                "review_status": status,
                "source": _review_source(row),
                "recommended_probability": row.get("recommended_probability"),
                "review_decision": row.get("review_decision"),
                "review_notes": row.get("review_notes") or "",
            }
        )

    build = final_tree.setdefault("observed_build", {})
    assigned_distinct = len(audit_rows)
    assigned_rows = sum(int(row["row_count"]) for row in audit_rows)
    build["probe_review_finalize"] = {
        "assigned_distinct_names": assigned_distinct,
        "assigned_row_count": assigned_rows,
        "assignment_counts": dict(sorted(assignment_counts.items())),
        "statuses": sorted(statuses),
        "skipped_count": len(skipped_rows),
        "skipped_rows": skipped_rows[:200],
    }
    build["assigned_distinct_names"] = int(build.get("assigned_distinct_names") or 0) + assigned_distinct
    build["unassigned_distinct_names"] = max(
        0,
        int(build.get("unassigned_distinct_names") or 0) - assigned_distinct,
    )
    build["assigned_row_count"] = int(build.get("assigned_row_count") or 0) + assigned_rows
    build["unassigned_row_count"] = max(
        0,
        int(build.get("unassigned_row_count") or 0) - assigned_rows,
    )
    current_counts = build.setdefault("assignment_counts", {})
    for node_id, row_count in assignment_counts.items():
        current_counts[node_id] = int(current_counts.get(node_id) or 0) + row_count
    build["unassigned_top"] = []

    summary = {
        "assigned_distinct_names": assigned_distinct,
        "assigned_row_count": assigned_rows,
        "skipped_count": len(skipped_rows),
        "remaining_unassigned_distinct_names": build["unassigned_distinct_names"],
        "remaining_unassigned_row_count": build["unassigned_row_count"],
    }
    return final_tree, audit_rows, summary


def main() -> None:
    args = _parse_args()
    base_tree = load_major_tree(args.base_tree)
    review_rows = _load_reviews(Path(args.reviews))
    final_tree, audit_rows, summary = finalize_tree(
        base_tree=base_tree,
        review_rows=review_rows,
        statuses=set(args.statuses),
        fail_on_unknown_label=args.fail_on_unknown_label,
    )

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(final_tree, ensure_ascii=False, indent=2), encoding="utf-8")

    audit_path = Path(args.audit_output)
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    audit_path.write_text(json.dumps(audit_rows, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"Wrote final tree to {output_path}")
    print(f"Wrote finalization audit to {audit_path}")


if __name__ == "__main__":
    main()
