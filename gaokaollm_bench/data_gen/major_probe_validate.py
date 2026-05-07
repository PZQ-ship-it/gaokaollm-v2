"""Validate a trained probe on a validation split using cached embeddings."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np
import torch

from gaokaollm_bench.data_gen.major_embedding import _normalize_text
from gaokaollm_bench.data_gen.major_probe_train import build_probe_model


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
    parser = argparse.ArgumentParser(description="Validate linear probe")
    parser.add_argument(
        "--input-jsonl",
        default=str(Path("gaokaollm_bench/outputs/major_training/splits/val.jsonl")),
    )
    parser.add_argument(
        "--embeddings",
        default=str(Path("gaokaollm_bench/outputs/major_training/embeddings.npz")),
    )
    parser.add_argument(
        "--label-map",
        default=str(Path("gaokaollm_bench/outputs/major_training_probe/label_map.json")),
    )
    parser.add_argument(
        "--probe",
        default=str(Path("gaokaollm_bench/outputs/major_training_probe/probe.pt")),
    )
    parser.add_argument("--label-field", default="leaf_id")
    parser.add_argument("--text-field", default="normalized_text")
    parser.add_argument(
        "--report-output",
        default=None,
        help="Optional path for full classification report JSON.",
    )
    return parser.parse_args()


def _classification_report(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    *,
    labels: list[int],
    target_names: list[str],
) -> dict[str, Any]:
    report: dict[str, Any] = {}
    total_support = int(y_true.size)
    weighted_precision = 0.0
    weighted_recall = 0.0
    weighted_f1 = 0.0
    macro_precision = 0.0
    macro_recall = 0.0
    macro_f1 = 0.0

    for label_id, target_name in zip(labels, target_names):
        true_mask = y_true == label_id
        pred_mask = y_pred == label_id
        tp = int((true_mask & pred_mask).sum())
        fp = int((~true_mask & pred_mask).sum())
        fn = int((true_mask & ~pred_mask).sum())
        support = int(true_mask.sum())
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        f1 = (2 * precision * recall / (precision + recall)) if precision + recall else 0.0

        report[target_name] = {
            "precision": precision,
            "recall": recall,
            "f1-score": f1,
            "support": support,
        }
        macro_precision += precision
        macro_recall += recall
        macro_f1 += f1
        weighted_precision += precision * support
        weighted_recall += recall * support
        weighted_f1 += f1 * support

    label_count = max(1, len(labels))
    report["accuracy"] = float((y_true == y_pred).mean()) if total_support else 0.0
    report["macro avg"] = {
        "precision": macro_precision / label_count,
        "recall": macro_recall / label_count,
        "f1-score": macro_f1 / label_count,
        "support": total_support,
    }
    report["weighted avg"] = {
        "precision": weighted_precision / total_support if total_support else 0.0,
        "recall": weighted_recall / total_support if total_support else 0.0,
        "f1-score": weighted_f1 / total_support if total_support else 0.0,
        "support": total_support,
    }
    return report


def main() -> None:
    args = _parse_args()
    rows = _read_jsonl(Path(args.input_jsonl))

    label_map = json.loads(Path(args.label_map).read_text(encoding="utf-8"))
    inv_label_map = {int(v): k for k, v in label_map.items()}

    data = np.load(Path(args.embeddings), allow_pickle=True)
    embeddings = data["embeddings"].astype(np.float32)
    texts = data["texts"].astype(object)
    index = {str(text): i for i, text in enumerate(texts)}

    X = []
    y = []
    missing = 0
    for row in rows:
        raw_text = str(row.get(args.text_field) or row.get("text") or "")
        text = _normalize_text(raw_text)
        if text not in index:
            missing += 1
            continue
        X.append(embeddings[index[text]])
        y.append(label_map[row.get(args.label_field)])

    if not X:
        raise ValueError("No validation samples matched cached embeddings")

    X = torch.from_numpy(np.asarray(X))
    y = np.asarray(y)

    state = torch.load(Path(args.probe), map_location="cpu")
    model_config = state.get("model_config")
    if model_config:
        model = build_probe_model(**model_config)
    else:
        model = torch.nn.Linear(X.shape[1], len(label_map))
    model.load_state_dict(state["state_dict"])
    model.eval()

    with torch.no_grad():
        logits = model(X)
        preds = torch.argmax(logits, dim=1).cpu().numpy()

    target_names = [inv_label_map[idx] for idx in sorted(inv_label_map)]
    report = _classification_report(
        y,
        preds,
        labels=list(range(len(label_map))),
        target_names=target_names,
    )
    metrics = {
        "total": int(len(y)),
        "missing_texts": int(missing),
        "macro_f1": report["macro avg"]["f1-score"],
        "accuracy": report["accuracy"],
        "weighted_f1": report["weighted avg"]["f1-score"],
    }

    output_path = Path(args.input_jsonl).with_suffix(".metrics.json")
    output_path.write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")
    report_path = Path(args.report_output) if args.report_output else Path(args.input_jsonl).with_suffix(
        ".classification_report.json"
    )
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps(metrics, ensure_ascii=False, indent=2))
    print("Saved metrics to", output_path)
    print("Saved classification report to", report_path)
    print("Label example:", inv_label_map.get(0))


if __name__ == "__main__":
    main()
