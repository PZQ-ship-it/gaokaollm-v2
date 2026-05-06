"""Validate a trained probe on a validation split using cached embeddings."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np
import torch
from sklearn.metrics import classification_report

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
    return parser.parse_args()


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

    model = torch.nn.Linear(X.shape[1], len(label_map))
    state = torch.load(Path(args.probe), map_location="cpu")
    model.load_state_dict(state["state_dict"])
    model.eval()

    with torch.no_grad():
        logits = model(X)
        preds = torch.argmax(logits, dim=1).cpu().numpy()

    report = classification_report(y, preds, output_dict=True, zero_division=0)
    metrics = {
        "total": int(len(y)),
        "missing_texts": int(missing),
        "macro_f1": report["macro avg"]["f1-score"],
        "accuracy": report["accuracy"],
    }

    output_path = Path(args.input_jsonl).with_suffix(".metrics.json")
    output_path.write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps(metrics, ensure_ascii=False, indent=2))
    print("Saved metrics to", output_path)
    print("Label example:", inv_label_map.get(0))


if __name__ == "__main__":
    main()
