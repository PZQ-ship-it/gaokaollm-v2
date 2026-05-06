"""Build a labeled training set from the major tree (observed_names + keywords)."""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from gaokaollm_bench.data_gen.major_embedding import _normalize_text
from gaokaollm_bench.data_gen.major_tree import load_major_tree


@dataclass(frozen=True)
class TrainingRow:
    text: str
    normalized_text: str
    leaf_id: str
    leaf_label: str
    parent_id: str | None
    parent_label: str | None
    source: str


def _node_map(tree: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return tree.get("nodes") or tree.get("clusters") or {}


def _leaf_nodes(nodes: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    parent_ids = {node.get("parent") for node in nodes.values() if node.get("parent")}
    return [node for node_id, node in nodes.items() if node_id not in parent_ids]


def _observed_names(node: dict[str, Any]) -> list[str]:
    return list(node.get("observed_names") or node.get("real_names") or [])


def _include_keywords(node: dict[str, Any]) -> list[str]:
    return list(node.get("include_keywords") or [])


def _parent_info(nodes: dict[str, dict[str, Any]], parent_id: str | None) -> tuple[str | None, str | None]:
    if not parent_id:
        return None, None
    parent = nodes.get(parent_id)
    if not parent:
        return parent_id, None
    return parent_id, str(parent.get("label") or parent_id)


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


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build labeled major training set")
    parser.add_argument(
        "--tree-path",
        default=str(Path("gaokaollm_bench/sample_data/major_tree_observed_auto_assigned_full.json")),
    )
    parser.add_argument(
        "--output",
        default=str(Path("gaokaollm_bench/outputs/major_training/train.jsonl")),
    )
    parser.add_argument(
        "--dedupe-on",
        choices=["text", "normalized_text"],
        default="normalized_text",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    tree = load_major_tree(Path(args.tree_path))
    rows = list(_iter_rows(tree))
    rows = _dedupe(rows, dedupe_on=args.dedupe_on)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    _write_jsonl(output_path, rows)
    _write_stats(output_path.with_suffix(".stats.json"), rows)

    print(f"Wrote {len(rows)} rows to {output_path}")


if __name__ == "__main__":
    main()
