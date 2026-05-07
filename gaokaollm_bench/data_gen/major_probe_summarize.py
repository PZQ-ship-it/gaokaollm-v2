"""Summarize probe experiment metrics across output directories."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Summarize major probe experiment metrics")
    parser.add_argument(
        "--root",
        action="append",
        default=[],
        help="Experiment root or output directory. Can be passed multiple times.",
    )
    parser.add_argument(
        "--output-json",
        default=str(Path("gaokaollm_bench/outputs/major_probe_experiments/summary.json")),
    )
    parser.add_argument(
        "--output-md",
        default=str(Path("gaokaollm_bench/outputs/major_probe_experiments/summary.md")),
    )
    parser.add_argument(
        "--sort-by",
        choices=["best_val_macro_f1", "best_val_accuracy", "best_val_loss"],
        default="best_val_macro_f1",
    )
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


def _row(path: Path) -> dict[str, Any]:
    metrics = json.loads(path.read_text(encoding="utf-8"))
    model_config = metrics.get("model_config") or {}
    training_config = metrics.get("training_config") or {}
    return {
        "name": str(path.parent),
        "metrics_path": str(path),
        "best_epoch": metrics.get("best_epoch"),
        "epochs_completed": metrics.get("epochs_completed", metrics.get("epochs")),
        "stopped_early": metrics.get("stopped_early", False),
        "best_val_macro_f1": metrics.get("best_val_macro_f1"),
        "best_val_accuracy": metrics.get("best_val_accuracy"),
        "best_val_top3_accuracy": metrics.get("best_val_top3_accuracy"),
        "best_val_loss": metrics.get("best_val_loss"),
        "missing_train_texts": metrics.get("missing_train_texts"),
        "model_kind": model_config.get("model_kind", "linear"),
        "hidden_dim": model_config.get("hidden_dim"),
        "num_hidden_layers": model_config.get("num_hidden_layers"),
        "activation": model_config.get("activation"),
        "dropout": model_config.get("dropout"),
        "lr": training_config.get("lr"),
        "weight_decay": training_config.get("weight_decay"),
        "class_weight": training_config.get("class_weight"),
        "selection_metric": training_config.get("selection_metric", metrics.get("selection_metric")),
    }


def _sort_rows(rows: list[dict[str, Any]], sort_by: str) -> list[dict[str, Any]]:
    reverse = sort_by != "best_val_loss"
    return sorted(
        rows,
        key=lambda row: (
            float("-inf") if row.get(sort_by) is None else float(row[sort_by])
        ),
        reverse=reverse,
    )


def _fmt(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float):
        return f"{value:.4f}"
    return str(value)


def _write_markdown(path: Path, rows: list[dict[str, Any]]) -> None:
    headers = [
        "rank",
        "name",
        "macro_f1",
        "accuracy",
        "top3",
        "val_loss",
        "epoch",
        "missing_train",
        "model",
        "layers",
        "activation",
        "lr",
        "wd",
        "class_weight",
    ]
    lines = ["| " + " | ".join(headers) + " |", "|" + "|".join(["---"] * len(headers)) + "|"]
    for idx, row in enumerate(rows, start=1):
        lines.append(
            "| "
            + " | ".join(
                [
                    str(idx),
                    Path(row["name"]).name,
                    _fmt(row.get("best_val_macro_f1")),
                    _fmt(row.get("best_val_accuracy")),
                    _fmt(row.get("best_val_top3_accuracy")),
                    _fmt(row.get("best_val_loss")),
                    _fmt(row.get("best_epoch")),
                    _fmt(row.get("missing_train_texts")),
                    _fmt(row.get("model_kind")),
                    _fmt(row.get("num_hidden_layers")),
                    _fmt(row.get("activation")),
                    _fmt(row.get("lr")),
                    _fmt(row.get("weight_decay")),
                    _fmt(row.get("class_weight")),
                ]
            )
            + " |"
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    args = _parse_args()
    roots = args.root or ["gaokaollm_bench/outputs/major_probe_experiments"]
    rows = [_row(path) for path in _metric_paths(roots)]
    rows = _sort_rows(rows, args.sort_by)

    output_json = Path(args.output_json)
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    _write_markdown(Path(args.output_md), rows)

    print(json.dumps(rows[:10], ensure_ascii=False, indent=2))
    print("Saved summary to", output_json)
    print("Saved markdown to", args.output_md)


if __name__ == "__main__":
    main()
