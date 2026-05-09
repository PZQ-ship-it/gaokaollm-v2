"""Run FR-KAN probe trials against the current shallow MLP baseline."""

from __future__ import annotations

import argparse
import json
import statistics
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from gaokaollm_bench.constrains.enums import ProbeClassWeight, ProbeModelKind
from gaokaollm_bench.constrains.metrics import (
    STRICT_ABLATION_PROMOTION_ACCURACY,
    STRICT_ABLATION_PROMOTION_MACRO_F1,
)
from gaokaollm_bench.constrains.paths import (
    MAJOR_EMBEDDINGS_UNION_VAL_FILLED,
    MAJOR_PROBE_FRKAN_TRIALS_DIR,
    MAJOR_RAW_TRAIN_ONLY_JSONL,
    MAJOR_VAL_JSONL,
)
from gaokaollm_bench.data_gen.major_eval_protocol import (
    assert_complete_embedding_coverage,
    assert_no_group_overlap,
    read_jsonl,
)


DEFAULT_OUTPUT_ROOT = MAJOR_PROBE_FRKAN_TRIALS_DIR
DEFAULT_TRAIN_PATH = MAJOR_RAW_TRAIN_ONLY_JSONL
DEFAULT_VAL_PATH = MAJOR_VAL_JSONL
DEFAULT_EMBEDDINGS_PATH = MAJOR_EMBEDDINGS_UNION_VAL_FILLED
PROMOTION_MACRO_F1 = STRICT_ABLATION_PROMOTION_MACRO_F1
PROMOTION_ACCURACY = STRICT_ABLATION_PROMOTION_ACCURACY


@dataclass(frozen=True)
class FRKANConfig:
    name: str
    protocol: str
    model_kind: str
    fourier_grid_size: int
    lr: float
    epochs: int
    early_stopping_patience: int | None
    hidden_dim: int = 256
    dropout: float = 0.1
    class_weight: str = ProbeClassWeight.SQRT_BALANCED.value


@dataclass(frozen=True)
class TrialConfig:
    config: FRKANConfig
    seed: int
    weight_decay: float
    batch_size: int

    @property
    def name(self) -> str:
        return f"{self.config.name}_s{self.seed}"


TRIAL_CONFIGS = [
    FRKANConfig(
        name="baseline_mlp_h256_sqrt_fair",
        protocol="fair_probe",
        model_kind=ProbeModelKind.MLP.value,
        fourier_grid_size=5,
        lr=0.001,
        epochs=100,
        early_stopping_patience=20,
    ),
    FRKANConfig(
        name="frkan_g3_fair",
        protocol="fair_probe",
        model_kind=ProbeModelKind.FR_KAN.value,
        fourier_grid_size=3,
        lr=0.001,
        epochs=100,
        early_stopping_patience=20,
    ),
    FRKANConfig(
        name="frkan_g5_fair",
        protocol="fair_probe",
        model_kind=ProbeModelKind.FR_KAN.value,
        fourier_grid_size=5,
        lr=0.001,
        epochs=100,
        early_stopping_patience=20,
    ),
    FRKANConfig(
        name="frkan_g7_fair",
        protocol="fair_probe",
        model_kind=ProbeModelKind.FR_KAN.value,
        fourier_grid_size=7,
        lr=0.001,
        epochs=100,
        early_stopping_patience=20,
    ),
    FRKANConfig(
        name="frkan_g5_paper_lr2e5_e5",
        protocol="paper_suggested",
        model_kind=ProbeModelKind.FR_KAN.value,
        fourier_grid_size=5,
        lr=0.00002,
        epochs=5,
        early_stopping_patience=None,
    ),
]
DEFAULT_SEEDS = [42, 43, 44]


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run FR-KAN major probe trials")
    parser.add_argument("--output-root", default=str(DEFAULT_OUTPUT_ROOT))
    parser.add_argument("--train-jsonl", default=str(DEFAULT_TRAIN_PATH))
    parser.add_argument("--val-jsonl", default=str(DEFAULT_VAL_PATH))
    parser.add_argument("--embeddings", default=str(DEFAULT_EMBEDDINGS_PATH))
    parser.add_argument("--seed", action="append", type=int, default=[])
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument("--weight-decay", type=float, default=0.0001)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--skip-existing", action="store_true")
    parser.add_argument("--summarize-only", action="store_true")
    return parser.parse_args()


def build_trial_matrix(args: argparse.Namespace) -> list[TrialConfig]:
    seeds = args.seed or DEFAULT_SEEDS
    return [
        TrialConfig(
            config=config,
            seed=seed,
            weight_decay=args.weight_decay,
            batch_size=args.batch_size,
        )
        for config in TRIAL_CONFIGS
        for seed in seeds
    ]


def _validate_inputs(
    train_path: Path, val_path: Path, embeddings_path: Path
) -> dict[str, Any]:
    train_rows = read_jsonl(train_path)
    val_rows = read_jsonl(val_path)
    assert_no_group_overlap(train_rows, val_rows)
    assert_complete_embedding_coverage(train_rows + val_rows, embeddings_path)
    return {
        "train_rows": len(train_rows),
        "val_rows": len(val_rows),
        "train_path": str(train_path),
        "val_path": str(val_path),
        "embeddings_path": str(embeddings_path),
    }


def build_command(
    trial: TrialConfig,
    *,
    output_root: Path,
    train_path: Path,
    val_path: Path,
    embeddings_path: Path,
    input_stats: dict[str, Any],
) -> list[str]:
    config = trial.config
    ablation_config = {
        "experiment_family": config.name,
        "method_family": "frkan_probe",
        "trial_name": config.name,
        "trial_protocol": config.protocol,
        "protocol": "frkan_probe_fixed_val_train_only_no_text_overlap",
        "tree_basis": "db_observed_tree",
        "promotion_macro_f1_threshold": PROMOTION_MACRO_F1,
        "promotion_accuracy_threshold": PROMOTION_ACCURACY,
        **input_stats,
    }
    command = [
        sys.executable,
        "-m",
        "gaokaollm_bench.data_gen.major_probe_train",
        "--input-jsonl",
        str(train_path),
        "--val-jsonl",
        str(val_path),
        "--embeddings",
        str(embeddings_path),
        "--output-dir",
        str(output_root / trial.name),
        "--label-field",
        "leaf_id",
        "--batch-size",
        str(trial.batch_size),
        "--epochs",
        str(config.epochs),
        "--lr",
        str(config.lr),
        "--weight-decay",
        str(trial.weight_decay),
        "--model-kind",
        config.model_kind,
        "--hidden-dim",
        str(config.hidden_dim),
        "--dropout",
        str(config.dropout),
        "--fourier-grid-size",
        str(config.fourier_grid_size),
        "--class-weight",
        config.class_weight,
        "--selection-metric",
        "val_macro_f1",
        "--seed",
        str(trial.seed),
        "--ablation-config-json",
        json.dumps(ablation_config, ensure_ascii=False),
    ]
    if config.early_stopping_patience is not None:
        command.extend(
            ["--early-stopping-patience", str(config.early_stopping_patience)]
        )
    return command


def _metric_paths(output_root: Path) -> list[Path]:
    return sorted(path for path in output_root.glob("*/metrics.json") if path.is_file())


def _mean(values: list[float]) -> float | None:
    return statistics.fmean(values) if values else None


def _std(values: list[float]) -> float | None:
    return statistics.stdev(values) if len(values) > 1 else 0.0 if values else None


def _fmt(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float):
        return f"{value:.4f}"
    return str(value)


def summarize_trials(output_root: Path) -> dict[str, Any]:
    runs = []
    for path in _metric_paths(output_root):
        metrics = json.loads(path.read_text(encoding="utf-8"))
        model_config = metrics.get("model_config") or {}
        training_config = metrics.get("training_config") or {}
        ablation_config = metrics.get("ablation_config") or {}
        runs.append(
            {
                "name": path.parent.name,
                "metrics_path": str(path),
                "trial_name": ablation_config.get("trial_name")
                or path.parent.name.rsplit("_s", 1)[0],
                "trial_protocol": ablation_config.get("trial_protocol"),
                "best_val_macro_f1": metrics.get("best_val_macro_f1"),
                "best_val_accuracy": metrics.get("best_val_accuracy"),
                "best_val_top3_accuracy": metrics.get("best_val_top3_accuracy"),
                "best_val_loss": metrics.get("best_val_loss"),
                "best_epoch": metrics.get("best_epoch"),
                "missing_train_texts": metrics.get("missing_train_texts"),
                "missing_val_texts": metrics.get("missing_val_texts"),
                "model_kind": model_config.get("model_kind"),
                "fourier_grid_size": model_config.get("fourier_grid_size"),
                "hidden_dim": model_config.get("hidden_dim"),
                "dropout": model_config.get("dropout"),
                "lr": training_config.get("lr"),
                "epochs": metrics.get("epochs"),
                "epochs_completed": metrics.get("epochs_completed"),
                "class_weight": training_config.get("class_weight"),
                "seed": training_config.get("seed"),
            }
        )

    grouped: dict[str, list[dict[str, Any]]] = {}
    for run in runs:
        grouped.setdefault(str(run["trial_name"]), []).append(run)

    aggregates = []
    for trial_name, group_runs in grouped.items():
        macro_values = [
            float(row["best_val_macro_f1"])
            for row in group_runs
            if row.get("best_val_macro_f1") is not None
        ]
        accuracy_values = [
            float(row["best_val_accuracy"])
            for row in group_runs
            if row.get("best_val_accuracy") is not None
        ]
        top3_values = [
            float(row["best_val_top3_accuracy"])
            for row in group_runs
            if row.get("best_val_top3_accuracy") is not None
        ]
        macro_mean = _mean(macro_values)
        accuracy_mean = _mean(accuracy_values)
        aggregates.append(
            {
                "trial_name": trial_name,
                "trial_protocol": group_runs[0].get("trial_protocol"),
                "runs": len(group_runs),
                "model_kind": group_runs[0].get("model_kind"),
                "fourier_grid_size": group_runs[0].get("fourier_grid_size"),
                "lr": group_runs[0].get("lr"),
                "epochs": group_runs[0].get("epochs"),
                "best_val_macro_f1_mean": macro_mean,
                "best_val_macro_f1_std": _std(macro_values),
                "best_val_accuracy_mean": accuracy_mean,
                "best_val_accuracy_std": _std(accuracy_values),
                "best_val_top3_accuracy_mean": _mean(top3_values),
                "best_val_top3_accuracy_std": _std(top3_values),
                "promotion_candidate": bool(
                    macro_mean is not None
                    and accuracy_mean is not None
                    and macro_mean > PROMOTION_MACRO_F1
                    and accuracy_mean >= PROMOTION_ACCURACY
                ),
            }
        )
    aggregates.sort(
        key=lambda row: (
            float("-inf")
            if row["best_val_macro_f1_mean"] is None
            else float(row["best_val_macro_f1_mean"]),
            float("-inf")
            if row["best_val_accuracy_mean"] is None
            else float(row["best_val_accuracy_mean"]),
        ),
        reverse=True,
    )
    return {
        "promotion_thresholds": {
            "macro_f1": PROMOTION_MACRO_F1,
            "accuracy": PROMOTION_ACCURACY,
        },
        "aggregates": aggregates,
        "runs": sorted(runs, key=lambda row: str(row["name"])),
    }


def write_summary(output_root: Path, payload: dict[str, Any]) -> None:
    json_path = output_root / "frkan_trials_summary.json"
    md_path = output_root / "frkan_trials_summary.md"
    json_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    lines = [
        "# Major Probe FR-KAN Trials",
        "",
        f"Promotion gate: Macro-F1 > {PROMOTION_MACRO_F1:.4f} and Accuracy >= {PROMOTION_ACCURACY:.4f}.",
        "",
        "| Trial | Protocol | Runs | Grid | LR | Epochs | Macro-F1 Mean | Macro-F1 Std | Accuracy Mean | Top-3 Mean | Promotion Candidate |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for row in payload["aggregates"]:
        lines.append(
            "| "
            + " | ".join(
                [
                    str(row["trial_name"]),
                    str(row.get("trial_protocol") or ""),
                    str(row["runs"]),
                    _fmt(row.get("fourier_grid_size")),
                    _fmt(row.get("lr")),
                    _fmt(row.get("epochs")),
                    _fmt(row.get("best_val_macro_f1_mean")),
                    _fmt(row.get("best_val_macro_f1_std")),
                    _fmt(row.get("best_val_accuracy_mean")),
                    _fmt(row.get("best_val_top3_accuracy_mean")),
                    "yes" if row.get("promotion_candidate") else "no",
                ]
            )
            + " |"
        )

    candidates = [
        row for row in payload["aggregates"] if row.get("promotion_candidate")
    ]
    lines.extend(["", "## Conclusion", ""])
    if candidates:
        best = candidates[0]
        lines.append(
            f"`{best['trial_name']}` passes the dual gate and is a promotion candidate for separate review."
        )
    else:
        lines.append(
            "No FR-KAN trial passes the dual gate; keep the current MLP default unless a later protocol changes the evidence."
        )
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    args = _parse_args()
    output_root = Path(args.output_root)
    train_path = Path(args.train_jsonl)
    val_path = Path(args.val_jsonl)
    embeddings_path = Path(args.embeddings)
    output_root.mkdir(parents=True, exist_ok=True)

    if not args.summarize_only:
        input_stats = _validate_inputs(train_path, val_path, embeddings_path)
        planned = []
        for trial in build_trial_matrix(args):
            output_dir = output_root / trial.name
            if args.skip_existing and (output_dir / "metrics.json").exists():
                continue
            planned.append(
                {
                    "name": trial.name,
                    "command": build_command(
                        trial,
                        output_root=output_root,
                        train_path=train_path,
                        val_path=val_path,
                        embeddings_path=embeddings_path,
                        input_stats=input_stats,
                    ),
                }
            )

        (output_root / "run_plan.json").write_text(
            json.dumps(planned, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(f"Planned {len(planned)} runs")
        if args.dry_run:
            print(json.dumps(planned[:6], ensure_ascii=False, indent=2))
            return

        for idx, item in enumerate(planned, start=1):
            print(f"[{idx}/{len(planned)}] {item['name']}", flush=True)
            subprocess.run(item["command"], check=True)

    payload = summarize_trials(output_root)
    write_summary(output_root, payload)
    print(json.dumps(payload["aggregates"], ensure_ascii=False, indent=2))
    print("Saved FR-KAN summary to", output_root / "frkan_trials_summary.json")


if __name__ == "__main__":
    main()
