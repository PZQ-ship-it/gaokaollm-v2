"""Build a labeled training set from the major tree (observed_names + keywords)."""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from gaokaollm_bench.constrains.paths import MAJOR_OBSERVED_TREE, MAJOR_TRAIN_JSONL
from gaokaollm_bench.data_gen.major_embedding import _normalize_text
from gaokaollm_bench.data_gen.major_tree import load_major_tree

DEFAULT_TREE_PATH = MAJOR_OBSERVED_TREE
DEFAULT_OUTPUT_PATH = MAJOR_TRAIN_JSONL


@dataclass(frozen=True)
class TrainingRow:
    text: str
    normalized_text: str
    leaf_id: str
    leaf_label: str
    parent_id: str | None
    parent_label: str | None
    source: str


AMBIGUOUS_MARKERS = ("含", "专业", "类", "试验班", "实验班", "方向", "双学位", "复合")


def _node_map(tree: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return tree.get("nodes") or tree.get("clusters") or {}


def _leaf_nodes(nodes: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    parent_ids = {node.get("parent") for node in nodes.values() if node.get("parent")}
    return [node for node_id, node in nodes.items() if node_id not in parent_ids]


def _observed_names(node: dict[str, Any]) -> list[str]:
    return list(node.get("observed_names") or node.get("real_names") or [])


def _include_keywords(node: dict[str, Any]) -> list[str]:
    return list(node.get("include_keywords") or [])


def _parent_info(
    nodes: dict[str, dict[str, Any]], parent_id: str | None
) -> tuple[str | None, str | None]:
    if not parent_id:
        return None, None
    parent = nodes.get(parent_id)
    if not parent:
        return parent_id, None
    return parent_id, str(parent.get("label") or parent_id)


def _ancestor_at_or_above_leaf_parent(
    nodes: dict[str, dict[str, Any]],
    node_id: str | None,
) -> str | None:
    current_id = node_id
    best_id = node_id
    while current_id and current_id in nodes:
        node = nodes[current_id]
        if int(node.get("level") or 0) <= 1:
            return str(node.get("id") or current_id)
        best_id = current_id
        current_id = node.get("parent")
    return str(best_id) if best_id else None


def _keyword_parent_index(tree: dict[str, Any]) -> dict[str, set[str]]:
    nodes = _node_map(tree)
    index: dict[str, set[str]] = defaultdict(set)
    for node in _leaf_nodes(nodes):
        leaf_id = str(node.get("id") or "")
        parent_group = _ancestor_at_or_above_leaf_parent(nodes, leaf_id)
        if not parent_group:
            continue
        for keyword in _include_keywords(node):
            keyword = str(keyword).strip()
            if len(keyword) >= 2:
                index[keyword].add(parent_group)
    return index


def detect_ambiguous_compound_major(
    text: str,
    leaf_id: str,
    tree: dict[str, Any],
) -> dict[str, Any]:
    text = str(text or "")
    if not text:
        return {"is_ambiguous": False, "reason": "empty_text", "matched_keywords": []}
    if not any(marker in text for marker in AMBIGUOUS_MARKERS):
        return {
            "is_ambiguous": False,
            "reason": "no_compound_marker",
            "matched_keywords": [],
        }

    nodes = _node_map(tree)
    own_parent = _ancestor_at_or_above_leaf_parent(nodes, leaf_id)
    keyword_index = _keyword_parent_index(tree)
    matched = []
    matched_parents: set[str] = set()
    for keyword, parent_ids in keyword_index.items():
        if keyword in text:
            matched.append({"keyword": keyword, "parent_ids": sorted(parent_ids)})
            matched_parents.update(parent_ids)

    cross_parent_ids = sorted(
        parent_id for parent_id in matched_parents if parent_id != own_parent
    )
    is_ambiguous = bool(cross_parent_ids and len(matched) >= 2)
    return {
        "is_ambiguous": is_ambiguous,
        "reason": "cross_parent_compound"
        if is_ambiguous
        else "same_parent_or_weak_signal",
        "own_parent_id": own_parent,
        "cross_parent_ids": cross_parent_ids,
        "matched_keywords": matched,
    }


def _iter_rows(tree: dict[str, Any]) -> Iterable[TrainingRow]:
    nodes = _node_map(tree)
    for node in _leaf_nodes(nodes):
        leaf_id = str(node.get("id") or "")
        leaf_label = str(node.get("label") or leaf_id)
        parent_id = node.get("parent")
        parent_id, parent_label = _parent_info(nodes, parent_id)

        for name in _observed_names(node):
            text = str(name)
            yield TrainingRow(
                text=text,
                normalized_text=_normalize_text(text),
                leaf_id=leaf_id,
                leaf_label=leaf_label,
                parent_id=parent_id,
                parent_label=parent_label,
                source="observed_names",
            )

        for keyword in _include_keywords(node):
            text = str(keyword)
            yield TrainingRow(
                text=text,
                normalized_text=_normalize_text(text),
                leaf_id=leaf_id,
                leaf_label=leaf_label,
                parent_id=parent_id,
                parent_label=parent_label,
                source="include_keywords",
            )


def _dedupe(rows: Iterable[TrainingRow], *, dedupe_on: str) -> list[TrainingRow]:
    dedupe_on = dedupe_on.lower()
    if dedupe_on not in {"text", "normalized_text"}:
        raise ValueError("dedupe_on must be 'text' or 'normalized_text'")

    seen: dict[str, TrainingRow] = {}
    for row in rows:
        key = getattr(row, dedupe_on)
        if not key:
            continue
        if key in seen:
            continue
        seen[key] = row
    return list(seen.values())


def _filter_ambiguous_rows(
    rows: list[TrainingRow],
    *,
    tree: dict[str, Any],
) -> tuple[list[TrainingRow], list[dict[str, Any]]]:
    kept = []
    audit = []
    for row in rows:
        if row.source != "observed_names":
            kept.append(row)
            continue
        detection = detect_ambiguous_compound_major(row.text, row.leaf_id, tree)
        if detection["is_ambiguous"]:
            audit.append({**row.__dict__, "ambiguity": detection})
        else:
            kept.append(row)
    return kept, audit


def _write_jsonl(path: Path, rows: Iterable[TrainingRow]) -> None:
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row.__dict__, ensure_ascii=False) + "\n")


def _write_stats(path: Path, rows: list[TrainingRow]) -> None:
    stats = defaultdict(int)
    for row in rows:
        stats[row.leaf_id] += 1
    payload = {
        "total": len(rows),
        "by_leaf": dict(sorted(stats.items(), key=lambda item: item[1], reverse=True)),
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _write_audit(path: Path, rows: list[dict[str, Any]]) -> None:
    path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build labeled major training set")
    parser.add_argument(
        "--tree-path",
        default=str(DEFAULT_TREE_PATH),
        help=(
            "Clean observed major tree used as rule-labeled training source. "
            "Do not use embedding auto-assigned trees unless explicitly allowed."
        ),
    )
    parser.add_argument(
        "--output",
        default=str(DEFAULT_OUTPUT_PATH),
    )
    parser.add_argument(
        "--allow-auto-assigned-tree",
        action="store_true",
        help="Allow training-set generation from an embedding auto-assigned tree.",
    )
    parser.add_argument(
        "--dedupe-on",
        choices=["text", "normalized_text"],
        default="normalized_text",
    )
    parser.add_argument(
        "--exclude-ambiguous-compound-majors",
        action="store_true",
        help="Drop observed-name rows that mix keywords from multiple top-level parent groups.",
    )
    parser.add_argument(
        "--ambiguity-audit-output",
        default=None,
        help="Optional JSON audit path for rows dropped by --exclude-ambiguous-compound-majors.",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    tree_path = Path(args.tree_path)
    if "auto_assigned" in tree_path.name and not args.allow_auto_assigned_tree:
        raise SystemExit(
            "Refusing to build rule-labeled training data from an auto-assigned tree. "
            "Use gaokaollm_bench/sample_data/major_tree_observed_full.json or pass "
            "--allow-auto-assigned-tree if this is an intentional experiment."
        )

    tree = load_major_tree(tree_path)
    rows = list(_iter_rows(tree))
    ambiguity_audit: list[dict[str, Any]] = []
    if args.exclude_ambiguous_compound_majors:
        rows, ambiguity_audit = _filter_ambiguous_rows(rows, tree=tree)
    rows = _dedupe(rows, dedupe_on=args.dedupe_on)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    _write_jsonl(output_path, rows)
    _write_stats(output_path.with_suffix(".stats.json"), rows)
    audit_path = (
        Path(args.ambiguity_audit_output)
        if args.ambiguity_audit_output
        else output_path.with_suffix(".ambiguity_audit.json")
    )
    if args.exclude_ambiguous_compound_majors:
        _write_audit(audit_path, ambiguity_audit)
        print(
            f"Dropped {len(ambiguity_audit)} ambiguous rows; audit written to {audit_path}"
        )

    print(f"Wrote {len(rows)} rows to {output_path}")


if __name__ == "__main__":
    main()
