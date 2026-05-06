"""Train a linear probe on cached embeddings (no fine-tuning)."""

from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
from typing import Any

import numpy as np
import torch
from torch import nn
from torch.utils.data import DataLoader, TensorDataset

from gaokaollm_bench.data_gen.major_embedding import _normalize_text


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Linear probe training")
    parser.add_argument(
        "--input-jsonl",
        default=str(Path("gaokaollm_bench/outputs/major_training/train.jsonl")),
    )
    parser.add_argument(
        "--val-jsonl",
        default=None,
        help="Optional validation JSONL. If omitted, tries sibling val.jsonl.",
    )
    parser.add_argument(
        "--embeddings",
        default=str(Path("gaokaollm_bench/outputs/major_training/embeddings.npz")),
    )
    parser.add_argument(
        "--output-dir",
        default=str(Path("gaokaollm_bench/outputs/major_training_probe")),
    )
    parser.add_argument("--label-field", default="leaf_id")
    parser.add_argument("--text-field", default="normalized_text")
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument("--epochs", type=int, default=8)
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--eval-every",
        type=int,
        default=1,
        help="Evaluate validation metrics every N epochs when val data is available.",
    )
    parser.add_argument(
        "--history-output",
        default=None,
        help="Optional JSONL path for per-epoch training history.",
    )
    parser.add_argument(
        "--selection-metric",
        choices=["val_accuracy", "val_macro_f1", "val_loss", "train_accuracy", "train_loss"],
        default="val_accuracy",
        help="Metric used to select the final best probe when available.",
    )
    parser.add_argument(
        "--save-epoch-checkpoints",
        action="store_true",
        help="Save checkpoint_epoch_XXXX.pt for every epoch.",
    )
    parser.add_argument(
        "--checkpoint-dir",
        default=None,
        help="Optional directory for epoch checkpoints. Defaults to output-dir/checkpoints.",
    )
    return parser.parse_args()


def _embedding_index(data: np.lib.npyio.NpzFile) -> dict[str, int]:
    if "texts" not in data:
        return {}
    texts = data["texts"].astype(object)
    return {_normalize_text(str(text)): i for i, text in enumerate(texts)}


def _filter_train_rows(
    rows: list[dict[str, Any]],
    label_field: str,
) -> tuple[list[dict[str, Any]], list[Any], list[int], dict[str, int]]:
    labels = [row.get(label_field) for row in rows]
    label_counts: dict[Any, int] = {}
    for label in labels:
        label_counts[label] = label_counts.get(label, 0) + 1

    keep_labels = {label for label, count in label_counts.items() if label is not None and count >= 2}
    if len(keep_labels) < len(label_counts):
        dropped = len(label_counts) - len(keep_labels)
        print(f"Dropping {dropped} labels with <2 samples")

    filtered_indices = [idx for idx, row in enumerate(rows) if row.get(label_field) in keep_labels]
    filtered_rows = [rows[idx] for idx in filtered_indices]
    filtered_labels = [row.get(label_field) for row in filtered_rows]
    return filtered_rows, filtered_labels, filtered_indices, label_counts


def _build_train_dataset(
    rows: list[dict[str, Any]],
    labels: list[Any],
    *,
    embeddings: np.ndarray,
    text_index: dict[str, int],
    label_map: dict[Any, int],
    text_field: str,
    original_row_count: int,
    filtered_indices: list[int],
) -> tuple[np.ndarray, np.ndarray, int]:
    if text_index:
        X = []
        y = []
        missing = 0
        for row, label in zip(rows, labels):
            text = _normalize_text(str(row.get(text_field) or row.get("text") or ""))
            idx = text_index.get(text)
            if idx is None:
                missing += 1
                continue
            X.append(embeddings[idx])
            y.append(label_map[label])
        if not X:
            raise ValueError("No training samples matched cached embeddings")
        return np.asarray(X, dtype=np.float32), np.asarray(y, dtype=np.int64), missing

    if embeddings.shape[0] == original_row_count:
        X = embeddings[filtered_indices]
        y = np.asarray([label_map[label] for label in labels], dtype=np.int64)
        return X, y, 0

    raise ValueError("Embeddings count does not match rows and no texts index is present")


def _build_eval_dataset(
    rows: list[dict[str, Any]],
    *,
    embeddings: np.ndarray,
    text_index: dict[str, int],
    label_map: dict[Any, int],
    label_field: str,
    text_field: str,
) -> tuple[np.ndarray, np.ndarray, int, int]:
    X = []
    y = []
    missing = 0
    skipped_unknown_label = 0
    for row in rows:
        label = row.get(label_field)
        if label not in label_map:
            skipped_unknown_label += 1
            continue
        text = _normalize_text(str(row.get(text_field) or row.get("text") or ""))
        idx = text_index.get(text)
        if idx is None:
            missing += 1
            continue
        X.append(embeddings[idx])
        y.append(label_map[label])
    if not X:
        return np.empty((0, embeddings.shape[1]), dtype=np.float32), np.empty((0,), dtype=np.int64), missing, skipped_unknown_label
    return (
        np.asarray(X, dtype=np.float32),
        np.asarray(y, dtype=np.int64),
        missing,
        skipped_unknown_label,
    )


def _accuracy(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    if y_true.size == 0:
        return 0.0
    return float((y_true == y_pred).mean())


def _macro_f1(y_true: np.ndarray, y_pred: np.ndarray, num_classes: int) -> float:
    if y_true.size == 0:
        return 0.0
    f1s = []
    for label_id in range(num_classes):
        tp = int(((y_true == label_id) & (y_pred == label_id)).sum())
        fp = int(((y_true != label_id) & (y_pred == label_id)).sum())
        fn = int(((y_true == label_id) & (y_pred != label_id)).sum())
        denom = (2 * tp) + fp + fn
        f1s.append((2 * tp / denom) if denom else 0.0)
    return float(np.mean(f1s))


def _evaluate(
    model: nn.Module,
    X: np.ndarray,
    y: np.ndarray,
    *,
    num_classes: int,
) -> dict[str, float]:
    if X.shape[0] == 0:
        return {"loss": 0.0, "accuracy": 0.0, "macro_f1": 0.0}
    loss_fn = nn.CrossEntropyLoss()
    model.eval()
    with torch.no_grad():
        logits = model(torch.from_numpy(X))
        loss = float(loss_fn(logits, torch.from_numpy(y)).item())
        preds = torch.argmax(logits, dim=1).cpu().numpy()
    return {
        "loss": loss,
        "accuracy": _accuracy(y, preds),
        "macro_f1": _macro_f1(y, preds, num_classes),
    }


def _auto_val_path(train_path: Path) -> Path | None:
    candidate = train_path.with_name("val.jsonl")
    return candidate if candidate.exists() else None


def _metric_is_better(metric_name: str, score: float, best_score: float) -> bool:
    if metric_name in {"val_loss", "train_loss"}:
        return score <= best_score
    return score >= best_score


def _initial_best_score(metric_name: str) -> float:
    if metric_name in {"val_loss", "train_loss"}:
        return float("inf")
    return -float("inf")


def _copy_state_dict(model: nn.Module) -> dict[str, torch.Tensor]:
    return {key: value.detach().cpu().clone() for key, value in model.state_dict().items()}


def main() -> None:
    args = _parse_args()
    if args.eval_every < 1:
        raise ValueError("--eval-every must be at least 1")

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    train_path = Path(args.input_jsonl)
    rows = _read_jsonl(train_path)
    filtered_rows, filtered_labels, filtered_indices, label_counts = _filter_train_rows(
        rows, args.label_field
    )
    label_map = {label: idx for idx, label in enumerate(sorted(set(filtered_labels)))}

    data = np.load(Path(args.embeddings), allow_pickle=True)
    embeddings = data["embeddings"].astype(np.float32)
    text_index = _embedding_index(data)

    if embeddings.shape[0] != len(rows) and not text_index:
        raise ValueError("Embeddings count does not match rows and no texts index is present")

    X_train, y_train, missing_train = _build_train_dataset(
        filtered_rows,
        filtered_labels,
        embeddings=embeddings,
        text_index=text_index,
        label_map=label_map,
        text_field=args.text_field,
        original_row_count=len(rows),
        filtered_indices=filtered_indices,
    )
    if X_train.shape[0] != y_train.shape[0]:
        raise ValueError("Training embeddings count does not match labels")

    val_path = Path(args.val_jsonl) if args.val_jsonl else _auto_val_path(train_path)
    X_val = np.empty((0, X_train.shape[1]), dtype=np.float32)
    y_val = np.empty((0,), dtype=np.int64)
    missing_val = 0
    skipped_val_unknown_label = 0
    if val_path and val_path.exists():
        val_rows = _read_jsonl(val_path)
        X_val, y_val, missing_val, skipped_val_unknown_label = _build_eval_dataset(
            val_rows,
            embeddings=embeddings,
            text_index=text_index,
            label_map=label_map,
            label_field=args.label_field,
            text_field=args.text_field,
        )
        print(
            f"Loaded val set: matched={len(y_val)} missing_texts={missing_val} "
            f"unknown_labels={skipped_val_unknown_label}"
        )

    torch.manual_seed(args.seed)
    np.random.seed(args.seed)

    train_loader = DataLoader(
        TensorDataset(torch.from_numpy(X_train), torch.from_numpy(y_train)),
        batch_size=args.batch_size,
        shuffle=True,
    )
    model = nn.Linear(X_train.shape[1], len(label_map))
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.lr)
    loss_fn = nn.CrossEntropyLoss()

    history_path = Path(args.history_output) if args.history_output else output_dir / "train_history.jsonl"
    history_path.parent.mkdir(parents=True, exist_ok=True)
    if history_path.exists():
        history_path.unlink()

    checkpoint_dir = Path(args.checkpoint_dir) if args.checkpoint_dir else output_dir / "checkpoints"
    if args.save_epoch_checkpoints:
        checkpoint_dir.mkdir(parents=True, exist_ok=True)

    best_state = None
    best_score = _initial_best_score(args.selection_metric)
    best_metric_name = args.selection_metric
    history: list[dict[str, Any]] = []

    for epoch in range(1, args.epochs + 1):
        model.train()
        total_loss = 0.0
        total_seen = 0
        train_correct = 0
        for xb, yb in train_loader:
            optimizer.zero_grad()
            logits = model(xb)
            loss = loss_fn(logits, yb)
            loss.backward()
            optimizer.step()

            batch_size = int(yb.shape[0])
            total_loss += float(loss.item()) * batch_size
            total_seen += batch_size
            train_correct += int((torch.argmax(logits.detach(), dim=1) == yb).sum().item())

        train_loss = total_loss / total_seen if total_seen else 0.0
        train_acc = train_correct / total_seen if total_seen else 0.0
        epoch_log: dict[str, Any] = {
            "epoch": epoch,
            "train_loss": train_loss,
            "train_accuracy": train_acc,
            "train_samples": int(total_seen),
            "missing_train_texts": int(missing_train),
        }

        has_val_metrics = bool(y_val.size and epoch % args.eval_every == 0)
        if has_val_metrics:
            val_metrics = _evaluate(model, X_val, y_val, num_classes=len(label_map))
            epoch_log.update(
                {
                    "val_loss": val_metrics["loss"],
                    "val_accuracy": val_metrics["accuracy"],
                    "val_macro_f1": val_metrics["macro_f1"],
                    "val_samples": int(y_val.size),
                    "missing_val_texts": int(missing_val),
                    "unknown_val_labels": int(skipped_val_unknown_label),
                }
            )
        if args.selection_metric in epoch_log:
            metric_name = args.selection_metric
            score = float(epoch_log[metric_name])
        elif args.selection_metric.startswith("val_") and has_val_metrics:
            metric_name = args.selection_metric
            score = float(epoch_log[metric_name])
        elif args.selection_metric.startswith("val_") and not y_val.size:
            metric_name = "train_accuracy"
            score = train_acc
        elif args.selection_metric.startswith("val_") and not has_val_metrics:
            metric_name = best_metric_name
            score = best_score
        else:
            metric_name = args.selection_metric
            score = float(epoch_log[metric_name])

        is_evaluated_epoch = metric_name in epoch_log
        is_best = is_evaluated_epoch and _metric_is_better(metric_name, score, best_score)
        if is_best:
            best_score = score
            best_metric_name = metric_name
            best_state = {
                "state_dict": _copy_state_dict(model),
                "epoch": epoch,
                "score": score,
                "selection_metric": metric_name,
                "epoch_log": copy.deepcopy(epoch_log),
            }

        epoch_log["selection_metric"] = metric_name
        epoch_log["selection_score"] = None if not is_evaluated_epoch else score
        epoch_log["is_best"] = bool(is_best)

        if args.save_epoch_checkpoints:
            torch.save(
                {
                    "state_dict": _copy_state_dict(model),
                    "epoch": epoch,
                    "selection_metric": metric_name,
                    "selection_score": None if not is_evaluated_epoch else score,
                    "epoch_log": epoch_log,
                },
                checkpoint_dir / f"checkpoint_epoch_{epoch:04d}.pt",
            )

        history.append(epoch_log)
        with history_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(epoch_log, ensure_ascii=False) + "\n")

        parts = [
            f"epoch={epoch}",
            f"train_loss={train_loss:.6f}",
            f"train_acc={train_acc:.4f}",
        ]
        if "val_accuracy" in epoch_log:
            parts.extend(
                [
                    f"val_acc={epoch_log['val_accuracy']:.4f}",
                    f"val_macro_f1={epoch_log['val_macro_f1']:.4f}",
                    f"missing_val={missing_val}",
                ]
            )
        if is_best:
            parts.append(f"best_{metric_name}={score:.4f}")
        print(" ".join(parts))

    if best_state:
        torch.save(best_state, output_dir / "probe.pt")
        torch.save(best_state, output_dir / "best_probe.pt")

    (output_dir / "label_map.json").write_text(
        json.dumps(label_map, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    metrics = {
        "epochs": args.epochs,
        "best_epoch": int(best_state["epoch"]) if best_state else None,
        "best_score": float(best_score),
        "selection_metric": best_metric_name,
        "best_epoch_log": best_state.get("epoch_log") if best_state else None,
        "label_count": len(label_map),
        "input_rows": len(rows),
        "train_samples": int(X_train.shape[0]),
        "missing_train_texts": int(missing_train),
        "val_path": str(val_path) if val_path else None,
        "val_samples": int(y_val.size),
        "missing_val_texts": int(missing_val),
        "unknown_val_labels": int(skipped_val_unknown_label),
        "label_counts": dict(sorted(label_counts.items(), key=lambda item: str(item[0]))),
        "history": history,
    }
    (output_dir / "metrics.json").write_text(
        json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print(f"Saved probe to {output_dir / 'probe.pt'}")
    print(f"Saved best probe to {output_dir / 'best_probe.pt'}")
    print(f"Saved history to {history_path}")
    print(f"Saved metrics to {output_dir / 'metrics.json'}")


if __name__ == "__main__":
    main()