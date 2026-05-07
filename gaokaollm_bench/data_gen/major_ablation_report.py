"""Summarize academic major-probe ablations with aggregate statistics."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from gaokaollm_bench.data_gen.major_eval_protocol import summarize_experiment_metrics


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Summarize major tree/probe ablation runs")
    parser.add_argument(
        "--root",
        action="append",
        default=[],
        help="Experiment root or metrics.json path. Can be passed multiple times.",
    )
    parser.add_argument(
        "--output-json",
        default="gaokaollm_bench/outputs/major_probe_classification_ablation/summary.json",
    )
    parser.add_argument(
        "--output-md",
        default="gaokaollm_bench/outputs/major_probe_classification_ablation/summary.md",
    )
    parser.add_argument("--group-by", default="experiment_family")
    return parser.parse_args()


def _metric_paths(roots: list[str]) -> list[Path]:
    paths: list[Path] = []
    for raw_root in roots:
        root = Path(raw_root)
        if root.is_file() and root.name == "metrics.json":
            paths.append(root)
        elif (root / "metrics.json").exists():
            paths.append(root / "metrics.json")
        elif root.exists():
            paths.extend(root.rglob("metrics.json"))
    return sorted(set(paths))


def _fmt(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float):
        return f"{value:.4f}"
    return str(value)


def _write_markdown(path: Path, payload: dict[str, Any]) -> None:
    lines = [
        "# Major Probe Academic Ablation Summary",
        "",
        "## Aggregates",
        "",
        "| Group | Runs | Macro-F1 Mean | Macro-F1 Std | Accuracy Mean | Accuracy Std | Top-3 Mean | Top-3 Std |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in payload["aggregates"]:
        lines.append(
            "| "
            + " | ".join(
                [
                    str(row["group"]),
                    str(row["runs"]),
                    _fmt(row.get("best_val_macro_f1_mean")),
                    _fmt(row.get("best_val_macro_f1_std")),
                    _fmt(row.get("best_val_accuracy_mean")),
                    _fmt(row.get("best_val_accuracy_std")),
                    _fmt(row.get("best_val_top3_accuracy_mean")),
                    _fmt(row.get("best_val_top3_accuracy_std")),
                ]
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "## Runs",
            "",
            "| Run | Group | Macro-F1 | Accuracy | Top-3 | Epoch | Model | Hidden | Class Weight | Seed |",
            "|---|---|---:|---:|---:|---:|---|---:|---|---:|",
        ]
    )
    for row in payload["runs"]:
        lines.append(
            "| "
            + " | ".join(
                [
                    str(row["name"]),
                    str(row["group"]),
                    _fmt(row.get("best_val_macro_f1")),
                    _fmt(row.get("best_val_accuracy")),
                    _fmt(row.get("best_val_top3_accuracy")),
                    _fmt(row.get("best_epoch")),
                    _fmt(row.get("model_kind")),
                    _fmt(row.get("hidden_dim")),
                    _fmt(row.get("class_weight")),
                    _fmt(row.get("seed")),
                ]
            )
            + " |"
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    args = _parse_args()
    roots = args.root or ["gaokaollm_bench/outputs/major_probe_classification_ablation"]
    metric_paths = _metric_paths(roots)
    payload = summarize_experiment_metrics(metric_paths, group_by=args.group_by)
    output_json = Path(args.output_json)
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    _write_markdown(Path(args.output_md), payload)
    print(json.dumps(payload["aggregates"], ensure_ascii=False, indent=2))
    print("Saved summary to", output_json)


if __name__ == "__main__":
    main()
