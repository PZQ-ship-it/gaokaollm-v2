"""Run probe-only academic ablations for major classification.

This runner intentionally excludes tree-coverage, LLM-review, downstream
recommendation variables, validation-overlap protocols, and data variants that
failed strict ablation. The matrix keeps only the paper-facing factors after
trial cleanup: raw train-only data, probe architecture, and none/sqrt-balanced
class weighting.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from gaokaollm_bench.data_gen.major_eval_protocol import (
    assert_complete_embedding_coverage,
    assert_no_group_overlap,
    read_jsonl,
)


DEFAULT_VAL_PATH = Path("gaokaollm_bench/outputs/major_training/splits/val.jsonl")


@dataclass(frozen=True)
class DatasetConfig:
    name: str
    train_path: Path
    embeddings_path: Path
    method_family: str


DATASETS = {
    "raw": DatasetConfig(
        name="raw",
        train_path=Path("gaokaollm_bench/outputs/major_probe_classification_ablation/data/raw_train_only.jsonl"),
        embeddings_path=Path("gaokaollm_bench/outputs/major_training/embeddings_union_val_filled.npz"),
        method_family="training_data",
    ),
}
DEFAULT_DATASETS = ["raw"]
DEFAULT_MODEL_KINDS = ["linear", "mlp"]
DEFAULT_CLASS_WEIGHTS = ["none", "sqrt_balanced"]
DEFAULT_SEEDS = [42, 43, 44]


@dataclass(frozen=True)
class RunConfig:
    dataset: DatasetConfig
    model_kind: str
    class_weight: str
    seed: int
    hidden_dim: int
    dropout: float
    lr: float
    weight_decay: float

    @property
    def name(self) -> str:
        model_part = "linear" if self.model_kind == "linear" else f"mlp_h{self.hidden_dim}"
        return f"{self.dataset.name}_{model_part}_{self.class_weight}_s{self.seed}"

    @property
    def experiment_family(self) -> str:
        return f"{self.dataset.name}__{self.model_kind}__{self.class_weight}"


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run probe-only major classification ablations")
    parser.add_argument("--output-root", default="gaokaollm_bench/outputs/major_probe_classification_ablation")
    parser.add_argument("--val-jsonl", default=str(DEFAULT_VAL_PATH))
    parser.add_argument(
        "--dataset",
        action="append",
        choices=sorted(DATASETS),
        default=[],
        help="Defaults to raw only; cleaned paper-facing ablations do not include negative data variants.",
    )
    parser.add_argument("--model-kind", action="append", choices=["linear", "mlp"], default=[])
    parser.add_argument(
        "--class-weight",
        action="append",
        choices=["none", "sqrt_balanced", "balanced"],
        default=[],
        help="Defaults to none and sqrt_balanced. balanced is retained only for explicit reruns.",
    )
    parser.add_argument("--seed", action="append", type=int, default=[])
    parser.add_argument("--epochs", type=int, default=80)
    parser.add_argument("--early-stopping-patience", type=int, default=15)
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument("--hidden-dim", type=int, default=256)
    parser.add_argument("--dropout", type=float, default=0.1)
    parser.add_argument("--lr", type=float, default=0.001)
    parser.add_argument("--weight-decay", type=float, default=0.0001)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--skip-existing", action="store_true")
    return parser.parse_args()


def build_run_matrix(args: argparse.Namespace) -> list[RunConfig]:
    datasets = args.dataset or DEFAULT_DATASETS
    model_kinds = args.model_kind or DEFAULT_MODEL_KINDS
    class_weights = args.class_weight or DEFAULT_CLASS_WEIGHTS
    seeds = args.seed or DEFAULT_SEEDS
    runs: list[RunConfig] = []
    for dataset_name in datasets:
        for model_kind in model_kinds:
            for class_weight in class_weights:
                for seed in seeds:
                    runs.append(
                        RunConfig(
                            dataset=DATASETS[dataset_name],
                            model_kind=model_kind,
                            class_weight=class_weight,
                            seed=seed,
                            hidden_dim=args.hidden_dim,
                            dropout=args.dropout,
                            lr=args.lr,
                            weight_decay=args.weight_decay,
                        )
                    )
    return runs


def validate_run_inputs(run: RunConfig, val_path: Path) -> dict[str, Any]:
    train_rows = read_jsonl(run.dataset.train_path)
    val_rows = read_jsonl(val_path)
    assert_no_group_overlap(train_rows, val_rows)
    assert_complete_embedding_coverage(train_rows + val_rows, run.dataset.embeddings_path)
    return {
        "train_rows": len(train_rows),
        "val_rows": len(val_rows),
        "train_path": str(run.dataset.train_path),
        "val_path": str(val_path),
        "embeddings_path": str(run.dataset.embeddings_path),
    }


def build_command(
    run: RunConfig,
    *,
    output_root: Path,
    val_path: Path,
    epochs: int,
    early_stopping_patience: int,
    batch_size: int,
    input_stats: dict[str, Any],
) -> list[str]:
    output_dir = output_root / run.name
    ablation_config = {
        "experiment_family": run.experiment_family,
        "method_family": run.dataset.method_family,
        "dataset": run.dataset.name,
        "model_kind": run.model_kind,
        "class_weight": run.class_weight,
        "seed": run.seed,
        "protocol": "probe_classification_fixed_val_train_only_no_text_overlap",
        "tree_basis": "db_observed_tree",
        **input_stats,
    }
    return [
        sys.executable,
        "-m",
        "gaokaollm_bench.data_gen.major_probe_train",
        "--input-jsonl",
        str(run.dataset.train_path),
        "--val-jsonl",
        str(val_path),
        "--embeddings",
        str(run.dataset.embeddings_path),
        "--output-dir",
        str(output_dir),
        "--label-field",
        "leaf_id",
        "--batch-size",
        str(batch_size),
        "--epochs",
        str(epochs),
        "--lr",
        str(run.lr),
        "--weight-decay",
        str(run.weight_decay),
        "--model-kind",
        run.model_kind,
        "--hidden-dim",
        str(run.hidden_dim),
        "--dropout",
        str(run.dropout),
        "--class-weight",
        run.class_weight,
        "--selection-metric",
        "val_macro_f1",
        "--early-stopping-patience",
        str(early_stopping_patience),
        "--seed",
        str(run.seed),
        "--ablation-config-json",
        json.dumps(ablation_config, ensure_ascii=False),
    ]


def main() -> None:
    args = _parse_args()
    output_root = Path(args.output_root)
    val_path = Path(args.val_jsonl)
    runs = build_run_matrix(args)
    output_root.mkdir(parents=True, exist_ok=True)

    planned = []
    for run in runs:
        output_dir = output_root / run.name
        if args.skip_existing and (output_dir / "metrics.json").exists():
            continue
        input_stats = validate_run_inputs(run, val_path)
        command = build_command(
            run,
            output_root=output_root,
            val_path=val_path,
            epochs=args.epochs,
            early_stopping_patience=args.early_stopping_patience,
            batch_size=args.batch_size,
            input_stats=input_stats,
        )
        planned.append({"name": run.name, "command": command})

    (output_root / "run_plan.json").write_text(json.dumps(planned, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Planned {len(planned)} runs")
    if args.dry_run:
        print(json.dumps(planned[:5], ensure_ascii=False, indent=2))
        return

    for idx, item in enumerate(planned, start=1):
        print(f"[{idx}/{len(planned)}] {item['name']}", flush=True)
        subprocess.run(item["command"], check=True)


if __name__ == "__main__":
    main()
