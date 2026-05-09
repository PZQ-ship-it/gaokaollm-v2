"""No-training, multi-iteration major clustering pipeline."""

from __future__ import annotations

import argparse
import asyncio
import csv
import json
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

from gaokaollm_bench.data_gen.major_embedding import (
    OpenAIEmbeddingClient,
    suggest_major_clusters_by_embedding,
)
from gaokaollm_bench.data_gen.major_tree import (
    UnknownMajorError,
    load_major_tree,
    resolve_major_node_from_tree,
)


def _node_map(tree: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return tree.get("nodes") or tree.get("clusters") or {}


def _leaf_nodes(nodes: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    parent_ids = {node.get("parent") for node in nodes.values() if node.get("parent")}
    return [node for node_id, node in nodes.items() if node_id not in parent_ids]


def _observed_names(node: dict[str, Any]) -> list[str]:
    return list(node.get("observed_names") or node.get("real_names") or [])


def _collect_observed(nodes: dict[str, dict[str, Any]]) -> set[str]:
    observed: set[str] = set()
    for node in nodes.values():
        observed.update(_observed_names(node))
    return observed


def _load_unassigned(path: Path) -> list[str]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("Unassigned data must be a list")
    if not data:
        return []
    if isinstance(data[0], str):
        return [str(item) for item in data]
    if isinstance(data[0], dict):
        return [str(item["major_name"]) for item in data if "major_name" in item]
    raise ValueError("Unsupported unassigned data format")


def _write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _write_csv(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    rows = list(rows)
    if not rows:
        return
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def _timestamped_output_dir(root: Path) -> Path:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = root / stamp
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def _iter1_baseline(
    tree: dict[str, Any], unassigned: list[str], *, filter_observed: bool
) -> dict[str, Any]:
    nodes = _node_map(tree)
    leaves = _leaf_nodes(nodes)
    observed = _collect_observed(nodes) if filter_observed else set()
    unassigned_filtered = [name for name in unassigned if name and name not in observed]

    leaf_stats = []
    for node in leaves:
        leaf_stats.append(
            {
                "id": node.get("id"),
                "label": node.get("label"),
                "level": node.get("level"),
                "parent": node.get("parent"),
                "observed_count": len(_observed_names(node)),
                "include_keywords_count": len(node.get("include_keywords", [])),
            }
        )

    return {
        "leaf_count": len(leaves),
        "unassigned_count": len(unassigned_filtered),
        "leaf_stats": leaf_stats,
        "unassigned": unassigned_filtered,
    }


async def _iter2_suggest(
    tree: dict[str, Any],
    majors: list[str],
    *,
    attach_threshold: float,
    new_sibling_threshold: float,
    major_batch_size: int | None,
) -> list[dict[str, Any]]:
    if not majors:
        return []
    embedding_client = OpenAIEmbeddingClient()
    suggestions = await suggest_major_clusters_by_embedding(
        majors,
        embedding_client,
        tree=tree,
        attach_threshold=attach_threshold,
        new_sibling_threshold=new_sibling_threshold,
        major_batch_size=major_batch_size,
    )
    return [asdict(item) for item in suggestions]


def _iter3_consistency(
    tree: dict[str, Any], suggestions: list[dict[str, Any]], *, high_sim: float
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for suggestion in suggestions:
        major_name = suggestion["major_name"]
        similarity = suggestion["similarity"]
        target_node_id = suggestion["target_node_id"]
        target_label = suggestion["target_label"]
        try:
            rule_node = resolve_major_node_from_tree(major_name, tree)
            rule_node_id = rule_node.id
            rule_label = rule_node.label
            match = rule_node_id == target_node_id
            rule_status = "match" if match else "mismatch"
        except UnknownMajorError:
            rule_node_id = None
            rule_label = None
            rule_status = "rule_unknown"

        rows.append(
            {
                "major_name": major_name,
                "rule_status": rule_status,
                "rule_node_id": rule_node_id,
                "rule_label": rule_label,
                "suggested_node_id": target_node_id,
                "suggested_label": target_label,
                "similarity": similarity,
                "high_similarity_mismatch": bool(
                    similarity >= high_sim and rule_status == "mismatch"
                ),
            }
        )
    return rows


async def _iter4_threshold_sweep(
    tree: dict[str, Any],
    majors: list[str],
    *,
    sweep: list[tuple[float, float]],
    major_batch_size: int | None,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not majors:
        return rows
    for attach_threshold, new_sibling_threshold in sweep:
        suggestions = await _iter2_suggest(
            tree,
            majors,
            attach_threshold=attach_threshold,
            new_sibling_threshold=new_sibling_threshold,
            major_batch_size=major_batch_size,
        )
        counts = {
            "attach_to_leaf": 0,
            "suggest_new_sibling_leaf": 0,
            "manual_review": 0,
        }
        for item in suggestions:
            counts[item["action"]] = counts.get(item["action"], 0) + 1
        rows.append(
            {
                "attach_threshold": attach_threshold,
                "new_sibling_threshold": new_sibling_threshold,
                "attach_to_leaf": counts.get("attach_to_leaf", 0),
                "suggest_new_sibling_leaf": counts.get("suggest_new_sibling_leaf", 0),
                "manual_review": counts.get("manual_review", 0),
                "total": len(suggestions),
            }
        )
    return rows


def _parse_sweep(raw: str) -> list[tuple[float, float]]:
    if not raw:
        return []
    pairs = []
    for part in raw.split(";"):
        part = part.strip()
        if not part:
            continue
        attach, sibling = part.split(",")
        pairs.append((float(attach), float(sibling)))
    return pairs


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Major clustering pipeline (no training)"
    )
    parser.add_argument(
        "--tree-path",
        default=str(Path("gaokaollm_bench/sample_data/major_tree_observed_full.json")),
    )
    parser.add_argument(
        "--unassigned-path",
        default=str(
            Path("gaokaollm_bench/sample_data/major_tree_unassigned_full.json")
        ),
    )
    parser.add_argument(
        "--output-root",
        default=str(Path("gaokaollm_bench/outputs/major_cluster_runs")),
    )
    parser.add_argument("--sample-size", type=int, default=200)
    parser.add_argument("--filter-observed", action="store_true")
    parser.add_argument("--attach-threshold", type=float, default=0.82)
    parser.add_argument("--new-sibling-threshold", type=float, default=0.68)
    parser.add_argument("--major-batch-size", type=int, default=64)
    parser.add_argument("--high-sim-threshold", type=float, default=0.8)
    parser.add_argument(
        "--threshold-sweep",
        default="0.82,0.68;0.85,0.70",
        help="Semicolon-separated pairs: attach,sibling;attach,sibling",
    )
    return parser.parse_args()


async def main() -> None:
    args = _parse_args()
    tree_path = Path(args.tree_path)
    unassigned_path = Path(args.unassigned_path)
    output_root = Path(args.output_root)
    output_dir = _timestamped_output_dir(output_root)

    tree = load_major_tree(tree_path)
    unassigned = _load_unassigned(unassigned_path)

    baseline = _iter1_baseline(tree, unassigned, filter_observed=args.filter_observed)
    sample = (
        baseline["unassigned"][: args.sample_size]
        if args.sample_size
        else baseline["unassigned"]
    )

    _write_json(output_dir / "iter1_baseline.json", baseline)

    suggestions = await _iter2_suggest(
        tree,
        sample,
        attach_threshold=args.attach_threshold,
        new_sibling_threshold=args.new_sibling_threshold,
        major_batch_size=args.major_batch_size,
    )
    _write_json(output_dir / "iter2_suggestions.json", suggestions)

    consistency = _iter3_consistency(
        tree,
        suggestions,
        high_sim=args.high_sim_threshold,
    )
    _write_json(output_dir / "iter3_consistency.json", consistency)
    _write_csv(output_dir / "iter3_consistency.csv", consistency)

    sweep = _parse_sweep(args.threshold_sweep)
    if sweep:
        sweep_rows = await _iter4_threshold_sweep(
            tree,
            sample,
            sweep=sweep,
            major_batch_size=args.major_batch_size,
        )
        _write_json(output_dir / "iter4_threshold_sweep.json", sweep_rows)
        _write_csv(output_dir / "iter4_threshold_sweep.csv", sweep_rows)

    print(f"Outputs written to: {output_dir}")


if __name__ == "__main__":
    asyncio.run(main())
