"""Analyze major probe validation errors with top-k predictions and confusion."""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import numpy as np
import torch

from gaokaollm_bench.data_gen.major_embedding import _normalize_text
from gaokaollm_bench.data_gen.major_probe_predict import _load_probe
from gaokaollm_bench.data_gen.major_probe_validate import _classification_report
from gaokaollm_bench.data_gen.major_eval_protocol import low_sample_macro_f1, parent_metrics
from gaokaollm_bench.data_gen.major_tree import load_major_tree
from gaokaollm_bench.data_gen.major_training_set_builder import (
    detect_ambiguous_compound_major,
)


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Analyze major probe validation errors")
    parser.add_argument("--input-jsonl", default="gaokaollm_bench/outputs/major_training/splits/val.jsonl")
    parser.add_argument("--embeddings", default="gaokaollm_bench/outputs/major_training/embeddings.npz")
    parser.add_argument("--probe", default="gaokaollm_bench/outputs/major_training_probe/best_probe.pt")
    parser.add_argument("--label-map", default="gaokaollm_bench/outputs/major_training_probe/label_map.json")
    parser.add_argument("--major-tree", default="gaokaollm_bench/outputs/major_tree_final_reviewed.json")
    parser.add_argument("--output-dir", default="gaokaollm_bench/outputs/major_probe_error_analysis")
    parser.add_argument("--label-field", default="leaf_id")
    parser.add_argument("--text-field", default="normalized_text")
    parser.add_argument("--top-k", type=int, default=3)
    return parser.parse_args()


def _embedding_index(data: np.lib.npyio.NpzFile) -> dict[str, int]:
    texts = data["texts"].astype(object)
    return {_normalize_text(str(text)): i for i, text in enumerate(texts)}


def _label_name(nodes: dict[str, dict[str, Any]], label: str) -> str:
    node = nodes.get(label) or {}
    return str(node.get("label") or label)


def analyze(args: argparse.Namespace) -> dict[str, Any]:
    rows = _read_jsonl(Path(args.input_jsonl))
    label_map = json.loads(Path(args.label_map).read_text(encoding="utf-8"))
    inv_label_map = {int(v): k for k, v in label_map.items()}
    tree = load_major_tree(args.major_tree)
    nodes = tree.get("nodes") or tree.get("clusters") or {}
    model, _, _ = _load_probe(
        probe_path=args.probe,
        label_map_path=args.label_map,
        major_tree_path=args.major_tree,
    )

    data = np.load(Path(args.embeddings), allow_pickle=True)
    embeddings = data["embeddings"].astype(np.float32)
    index = _embedding_index(data)

    per_sample: list[dict[str, Any]] = []
    y_true: list[int] = []
    y_pred: list[int] = []
    missing = 0
    top_k = max(1, min(args.top_k, len(label_map)))

    for row in rows:
        label = row.get(args.label_field)
        if label not in label_map:
            continue
        raw_text = str(row.get(args.text_field) or row.get("text") or "")
        text = _normalize_text(raw_text)
        idx = index.get(text)
        if idx is None:
            missing += 1
            continue
        with torch.no_grad():
            logits = model(torch.from_numpy(embeddings[idx : idx + 1]))
            probs = torch.softmax(logits, dim=1).cpu().numpy()[0]
        top_indices = np.argsort(probs)[::-1][:top_k]
        pred_label_id = int(top_indices[0])
        gold_label_id = int(label_map[label])
        y_true.append(gold_label_id)
        y_pred.append(pred_label_id)
        predictions = [
            {
                "label": inv_label_map[int(item)],
                "label_name": _label_name(nodes, inv_label_map[int(item)]),
                "probability": float(probs[int(item)]),
            }
            for item in top_indices
        ]
        ambiguity = detect_ambiguous_compound_major(
            row.get("text") or raw_text,
            label,
            tree,
        )
        per_sample.append(
            {
                "text": row.get("text") or raw_text,
                "normalized_text": text,
                "source": row.get("source"),
                "gold_label": label,
                "gold_label_name": _label_name(nodes, str(label)),
                "pred_label": inv_label_map[pred_label_id],
                "pred_label_name": _label_name(nodes, inv_label_map[pred_label_id]),
                "top1_correct": pred_label_id == gold_label_id,
                "topk_contains_gold": gold_label_id in set(map(int, top_indices)),
                "predictions": predictions,
                "ambiguous_compound": ambiguity,
            }
        )

    y_true_array = np.asarray(y_true, dtype=np.int64)
    y_pred_array = np.asarray(y_pred, dtype=np.int64)
    labels = list(range(len(label_map)))
    target_names = [inv_label_map[idx] for idx in labels]
    report = _classification_report(y_true_array, y_pred_array, labels=labels, target_names=target_names)
    confusion: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for true_id, pred_id in zip(y_true, y_pred):
        confusion[inv_label_map[int(true_id)]][inv_label_map[int(pred_id)]] += 1
    topk_accuracy = (
        sum(1 for item in per_sample if item["topk_contains_gold"]) / len(per_sample)
        if per_sample
        else 0.0
    )
    low_f1 = sorted(
        [
            {
                "label": label,
                "label_name": _label_name(nodes, label),
                "support": metrics["support"],
                "precision": metrics["precision"],
                "recall": metrics["recall"],
                "f1": metrics["f1-score"],
            }
            for label, metrics in report.items()
            if label not in {"accuracy", "macro avg", "weighted avg"}
        ],
        key=lambda item: (item["f1"], item["support"], item["label"]),
    )
    suspicious = [
        item
        for item in per_sample
        if item["ambiguous_compound"]["is_ambiguous"] or not item["top1_correct"]
    ]
    summary = {
        "total": len(per_sample),
        "missing_texts": missing,
        "accuracy": report["accuracy"],
        "macro_f1": report["macro avg"]["f1-score"],
        "weighted_f1": report["weighted avg"]["f1-score"],
        "topk_accuracy": topk_accuracy,
        "low_sample_macro_f1": low_sample_macro_f1(report),
        "parent_metrics": parent_metrics(per_sample, tree),
        "top_k": top_k,
        "error_count": sum(1 for item in per_sample if not item["top1_correct"]),
        "topk_miss_count": sum(1 for item in per_sample if not item["topk_contains_gold"]),
        "ambiguous_count": sum(1 for item in per_sample if item["ambiguous_compound"]["is_ambiguous"]),
        "confusion_pairs": Counter(
            (item["gold_label"], item["pred_label"])
            for item in per_sample
            if not item["top1_correct"]
        ).most_common(),
    }
    return {
        "summary": summary,
        "per_sample": per_sample,
        "classification_report": report,
        "confusion": {k: dict(v) for k, v in confusion.items()},
        "low_f1": low_f1,
        "suspicious_samples": suspicious,
    }


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> None:
    args = _parse_args()
    result = analyze(args)
    output_dir = Path(args.output_dir)
    _write_json(output_dir / "summary.json", result["summary"])
    _write_json(output_dir / "per_sample.json", result["per_sample"])
    _write_json(output_dir / "classification_report.json", result["classification_report"])
    _write_json(output_dir / "confusion.json", result["confusion"])
    _write_json(output_dir / "low_f1.json", result["low_f1"])
    _write_json(output_dir / "suspicious_samples.json", result["suspicious_samples"])
    print(json.dumps(result["summary"], ensure_ascii=False, indent=2))
    print("Saved analysis to", output_dir)


if __name__ == "__main__":
    main()
