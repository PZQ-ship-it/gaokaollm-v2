"""Evaluation protocol helpers for major-tree/probe ablations.

This module keeps academic ablation checks separate from one-off engineering
artifacts: every split is grouped by canonical major text, embeddings must be
complete, and reports include both leaf-level and hierarchy-level metrics.
"""

from __future__ import annotations

import argparse
import json
import math
import random
import re
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean, pstdev
from typing import Any

import numpy as np

_PAREN_PATTERN = re.compile(r"[（(][^（）()]*[）)]")


def _normalize_text(text: str) -> str:
    if not text:
        return ""
    cleaned = _PAREN_PATTERN.sub("", text)
    cleaned = cleaned.replace("校区", "")
    cleaned = cleaned.replace("\u3000", " ")
    cleaned = cleaned.strip(" 、，,;；。")
    return " ".join(cleaned.split())


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def canonical_group_key(
    row: dict[str, Any], *, group_field: str = "normalized_text"
) -> str:
    raw = row.get(group_field) or row.get("normalized_text") or row.get("text") or ""
    return _normalize_text(str(raw))


def _label(row: dict[str, Any], label_field: str) -> str:
    value = row.get(label_field)
    if value is None:
        raise ValueError(f"Missing label field {label_field!r} in row: {row}")
    return str(value)


def _grouped_rows(
    rows: list[dict[str, Any]],
    *,
    label_field: str,
    group_field: str,
) -> list[dict[str, Any]]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        key = canonical_group_key(row, group_field=group_field)
        if not key:
            continue
        groups[key].append(row)

    result = []
    for key, items in groups.items():
        labels = Counter(_label(row, label_field) for row in items)
        label, count = labels.most_common(1)[0]
        if len(labels) > 1:
            raise ValueError(f"Group {key!r} has conflicting labels: {dict(labels)}")
        result.append(
            {
                "key": key,
                "label": label,
                "rows": items,
                "size": len(items),
                "label_count": count,
            }
        )
    return result


def grouped_train_val_split(
    rows: list[dict[str, Any]],
    *,
    val_ratio: float = 0.2,
    seed: int = 42,
    label_field: str = "leaf_id",
    group_field: str = "normalized_text",
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    if not 0.0 < val_ratio < 1.0:
        raise ValueError("val_ratio must be between 0 and 1")

    groups = _grouped_rows(rows, label_field=label_field, group_field=group_field)
    buckets: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for group in groups:
        buckets[group["label"]].append(group)

    rng = random.Random(seed)
    train_groups: list[dict[str, Any]] = []
    val_groups: list[dict[str, Any]] = []
    for label, label_groups in sorted(buckets.items()):
        rng.shuffle(label_groups)
        if len(label_groups) == 1:
            train_groups.extend(label_groups)
            continue
        val_count = max(1, int(round(len(label_groups) * val_ratio)))
        val_count = min(val_count, len(label_groups) - 1)
        val_groups.extend(label_groups[:val_count])
        train_groups.extend(label_groups[val_count:])

    rng.shuffle(train_groups)
    rng.shuffle(val_groups)
    train_rows = [row for group in train_groups for row in group["rows"]]
    val_rows = [row for group in val_groups for row in group["rows"]]
    stats = split_stats(
        train_rows, val_rows, label_field=label_field, group_field=group_field
    )
    stats.update(
        {
            "split_kind": "grouped_train_val",
            "seed": seed,
            "val_ratio": val_ratio,
            "input_rows": len(rows),
            "input_groups": len(groups),
        }
    )
    return train_rows, val_rows, stats


def grouped_kfold_splits(
    rows: list[dict[str, Any]],
    *,
    n_folds: int = 5,
    seed: int = 42,
    label_field: str = "leaf_id",
    group_field: str = "normalized_text",
) -> list[dict[str, Any]]:
    if n_folds < 2:
        raise ValueError("n_folds must be at least 2")
    groups = _grouped_rows(rows, label_field=label_field, group_field=group_field)
    buckets: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for group in groups:
        buckets[group["label"]].append(group)

    rng = random.Random(seed)
    folds: list[list[dict[str, Any]]] = [[] for _ in range(n_folds)]
    for _, label_groups in sorted(buckets.items()):
        rng.shuffle(label_groups)
        for idx, group in enumerate(label_groups):
            folds[idx % n_folds].append(group)

    result: list[dict[str, Any]] = []
    all_group_ids = set(range(len(groups)))
    group_to_id = {id(group): idx for idx, group in enumerate(groups)}
    for fold_idx, val_groups in enumerate(folds):
        val_ids = {group_to_id[id(group)] for group in val_groups}
        train_groups = [groups[idx] for idx in sorted(all_group_ids - val_ids)]
        train_rows = [row for group in train_groups for row in group["rows"]]
        val_rows = [row for group in val_groups for row in group["rows"]]
        stats = split_stats(
            train_rows, val_rows, label_field=label_field, group_field=group_field
        )
        stats.update(
            {
                "split_kind": "grouped_kfold",
                "fold": fold_idx,
                "n_folds": n_folds,
                "seed": seed,
            }
        )
        result.append(
            {
                "fold": fold_idx,
                "train_rows": train_rows,
                "val_rows": val_rows,
                "stats": stats,
            }
        )
    return result


def split_stats(
    train_rows: list[dict[str, Any]],
    val_rows: list[dict[str, Any]],
    *,
    label_field: str = "leaf_id",
    group_field: str = "normalized_text",
) -> dict[str, Any]:
    train_keys = {
        canonical_group_key(row, group_field=group_field) for row in train_rows
    }
    val_keys = {canonical_group_key(row, group_field=group_field) for row in val_rows}
    overlap = sorted(key for key in train_keys & val_keys if key)
    return {
        "train_rows": len(train_rows),
        "val_rows": len(val_rows),
        "train_groups": len(train_keys),
        "val_groups": len(val_keys),
        "overlap_count": len(overlap),
        "overlap_examples": overlap[:20],
        "train_label_count": len({row.get(label_field) for row in train_rows}),
        "val_label_count": len({row.get(label_field) for row in val_rows}),
        "train_by_label": dict(
            Counter(str(row.get(label_field)) for row in train_rows)
        ),
        "val_by_label": dict(Counter(str(row.get(label_field)) for row in val_rows)),
    }


def assert_no_group_overlap(
    train_rows: list[dict[str, Any]],
    val_rows: list[dict[str, Any]],
    *,
    group_field: str = "normalized_text",
) -> None:
    stats = split_stats(train_rows, val_rows, group_field=group_field)
    if stats["overlap_count"]:
        examples = ", ".join(stats["overlap_examples"][:5])
        raise ValueError(
            f"Grouped split leakage detected: {stats['overlap_count']} overlapping keys ({examples})"
        )


def embedding_coverage(
    rows: list[dict[str, Any]],
    embeddings_path: Path,
    *,
    text_field: str = "normalized_text",
) -> dict[str, Any]:
    data = np.load(embeddings_path, allow_pickle=True)
    if "texts" not in data:
        raise ValueError(
            "Embedding cache must contain a texts array for academic ablation"
        )
    cached = {_normalize_text(str(text)) for text in data["texts"].astype(object)}
    row_keys = [canonical_group_key(row, group_field=text_field) for row in rows]
    missing = sorted({key for key in row_keys if key and key not in cached})
    return {
        "rows": len(rows),
        "unique_texts": len({key for key in row_keys if key}),
        "cached_texts": len(cached),
        "missing_count": len(missing),
        "missing_examples": missing[:50],
    }


def assert_complete_embedding_coverage(
    rows: list[dict[str, Any]],
    embeddings_path: Path,
    *,
    text_field: str = "normalized_text",
) -> None:
    coverage = embedding_coverage(rows, embeddings_path, text_field=text_field)
    if coverage["missing_count"]:
        examples = ", ".join(coverage["missing_examples"][:5])
        raise ValueError(
            f"Embedding cache is incomplete: {coverage['missing_count']} missing texts ({examples})"
        )


def parent_metrics(
    per_sample: list[dict[str, Any]],
    tree: dict[str, Any],
) -> dict[str, Any]:
    nodes = tree.get("nodes") or tree.get("clusters") or {}

    def parent(label: str | None) -> str | None:
        if not label:
            return None
        node = nodes.get(str(label)) or {}
        value = node.get("parent")
        return str(value) if value else None

    total = 0
    correct = 0
    confusion: Counter[tuple[str, str]] = Counter()
    for item in per_sample:
        gold_parent = parent(item.get("gold_label"))
        pred_parent = parent(item.get("pred_label"))
        if not gold_parent or not pred_parent:
            continue
        total += 1
        if gold_parent == pred_parent:
            correct += 1
        else:
            confusion[(gold_parent, pred_parent)] += 1
    return {
        "parent_total": total,
        "parent_accuracy": correct / total if total else 0.0,
        "parent_confusion_pairs": [
            {"gold_parent": gold, "pred_parent": pred, "count": count}
            for (gold, pred), count in confusion.most_common()
        ],
    }


def low_sample_macro_f1(
    classification_report: dict[str, Any], *, max_support: int = 5
) -> dict[str, Any]:
    items = [
        metrics
        for label, metrics in classification_report.items()
        if label not in {"accuracy", "macro avg", "weighted avg"}
        and int(metrics.get("support") or 0) <= max_support
        and int(metrics.get("support") or 0) > 0
    ]
    return {
        "max_support": max_support,
        "label_count": len(items),
        "macro_f1": mean([float(item.get("f1-score") or 0.0) for item in items])
        if items
        else 0.0,
    }


def summarize_experiment_metrics(
    metric_paths: list[Path], *, group_by: str = "experiment_family"
) -> dict[str, Any]:
    rows = []
    for path in metric_paths:
        metrics = json.loads(path.read_text(encoding="utf-8"))
        config = metrics.get("ablation_config") or {}
        model_config = metrics.get("model_config") or {}
        training_config = metrics.get("training_config") or {}
        rows.append(
            {
                "name": path.parent.name,
                "metrics_path": str(path),
                "group": str(config.get(group_by) or path.parent.parent.name),
                "best_val_macro_f1": metrics.get("best_val_macro_f1"),
                "best_val_accuracy": metrics.get("best_val_accuracy"),
                "best_val_top3_accuracy": metrics.get("best_val_top3_accuracy"),
                "best_val_loss": metrics.get("best_val_loss"),
                "best_epoch": metrics.get("best_epoch"),
                "model_kind": model_config.get("model_kind"),
                "hidden_dim": model_config.get("hidden_dim"),
                "num_hidden_layers": model_config.get("num_hidden_layers"),
                "activation": model_config.get("activation"),
                "dropout": model_config.get("dropout"),
                "fourier_grid_size": model_config.get("fourier_grid_size"),
                "class_weight": training_config.get("class_weight"),
                "seed": training_config.get("seed"),
            }
        )

    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[row["group"]].append(row)

    aggregates = []
    for group, group_rows in grouped.items():
        values = {
            key: [float(row[key]) for row in group_rows if row.get(key) is not None]
            for key in [
                "best_val_macro_f1",
                "best_val_accuracy",
                "best_val_top3_accuracy",
            ]
        }
        aggregates.append(
            {
                "group": group,
                "runs": len(group_rows),
                **{
                    f"{key}_mean": mean(vals) if vals else None
                    for key, vals in values.items()
                },
                **{
                    f"{key}_std": pstdev(vals) if len(vals) > 1 else 0.0
                    for key, vals in values.items()
                },
            }
        )
    aggregates.sort(
        key=lambda item: item.get("best_val_macro_f1_mean") or -math.inf, reverse=True
    )
    return {"runs": rows, "aggregates": aggregates}


def summarize_persona_recommendations(personas: list[dict[str, Any]]) -> dict[str, Any]:
    stage_counter: Counter[str] = Counter()
    stage5_count = 0
    volunteer_counts = []
    unique_school_counts = []
    attempts: Counter[str] = Counter()
    for persona in personas:
        background = persona.get("background") or {}
        stage = background.get("relaxation_stage")
        if stage is not None:
            stage_counter[str(stage)] += 1
            if int(stage) == 5:
                stage5_count += 1
        volunteer_set = (persona.get("implicit_flexibilities") or {}).get(
            "volunteer_set"
        ) or []
        volunteer_counts.append(len(volunteer_set))
        unique_school_counts.append(
            len(
                {
                    item.get("school_name")
                    for item in volunteer_set
                    if item.get("school_name")
                }
            )
        )
        for attempt in background.get("stage_attempts") or []:
            key = f"stage_{attempt.get('stage')}_{attempt.get('failure_reason') or 'accepted'}"
            attempts[key] += 1
    total = len(personas)
    return {
        "total_cases": total,
        "stage_distribution": dict(stage_counter),
        "stage5_rate": stage5_count / total if total else 0.0,
        "avg_volunteer_count": mean(volunteer_counts) if volunteer_counts else 0.0,
        "avg_unique_school_count": mean(unique_school_counts)
        if unique_school_counts
        else 0.0,
        "stage_attempt_outcomes": dict(attempts),
    }


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Major probe/tree evaluation protocol utilities"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    split = subparsers.add_parser("grouped-split")
    split.add_argument("--input", required=True)
    split.add_argument("--output-dir", required=True)
    split.add_argument("--val-ratio", type=float, default=0.2)
    split.add_argument("--seed", type=int, default=42)
    split.add_argument("--label-field", default="leaf_id")
    split.add_argument("--group-field", default="normalized_text")

    kfold = subparsers.add_parser("grouped-kfold")
    kfold.add_argument("--input", required=True)
    kfold.add_argument("--output-dir", required=True)
    kfold.add_argument("--folds", type=int, default=5)
    kfold.add_argument("--seed", type=int, default=42)
    kfold.add_argument("--label-field", default="leaf_id")
    kfold.add_argument("--group-field", default="normalized_text")

    coverage = subparsers.add_parser("check-embeddings")
    coverage.add_argument("--input", required=True)
    coverage.add_argument("--embeddings", required=True)
    coverage.add_argument("--text-field", default="normalized_text")

    persona = subparsers.add_parser("summarize-personas")
    persona.add_argument("--input", required=True)
    persona.add_argument("--output", required=True)

    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    if args.command == "grouped-split":
        rows = read_jsonl(Path(args.input))
        train_rows, val_rows, stats = grouped_train_val_split(
            rows,
            val_ratio=args.val_ratio,
            seed=args.seed,
            label_field=args.label_field,
            group_field=args.group_field,
        )
        output_dir = Path(args.output_dir)
        write_jsonl(output_dir / "train.jsonl", train_rows)
        write_jsonl(output_dir / "val.jsonl", val_rows)
        (output_dir / "split.stats.json").write_text(
            json.dumps(stats, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(json.dumps(stats, ensure_ascii=False, indent=2))
    elif args.command == "grouped-kfold":
        rows = read_jsonl(Path(args.input))
        output_dir = Path(args.output_dir)
        stats = []
        for fold in grouped_kfold_splits(
            rows,
            n_folds=args.folds,
            seed=args.seed,
            label_field=args.label_field,
            group_field=args.group_field,
        ):
            fold_dir = output_dir / f"fold_{fold['fold']:02d}"
            write_jsonl(fold_dir / "train.jsonl", fold["train_rows"])
            write_jsonl(fold_dir / "val.jsonl", fold["val_rows"])
            (fold_dir / "split.stats.json").write_text(
                json.dumps(fold["stats"], ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            stats.append(fold["stats"])
        (output_dir / "kfold.stats.json").write_text(
            json.dumps(stats, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(json.dumps(stats, ensure_ascii=False, indent=2))
    elif args.command == "check-embeddings":
        rows = read_jsonl(Path(args.input))
        coverage = embedding_coverage(
            rows, Path(args.embeddings), text_field=args.text_field
        )
        print(json.dumps(coverage, ensure_ascii=False, indent=2))
        if coverage["missing_count"]:
            raise SystemExit(1)
    elif args.command == "summarize-personas":
        personas = json.loads(Path(args.input).read_text(encoding="utf-8"))
        summary = summarize_persona_recommendations(personas)
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(
            json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
