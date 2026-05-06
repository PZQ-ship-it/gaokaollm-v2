"""Train a linear probe on cached embeddings (no fine-tuning)."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np
import torch
from sklearn.metrics import classification_report, f1_score
from sklearn.model_selection import train_test_split
from torch import nn
from torch.utils.data import DataLoader, TensorDataset


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
        "--embeddings",
        default=str(Path("gaokaollm_bench/outputs/major_training/embeddings.npz")),
    )
    parser.add_argument(
        "--output-dir",
        default=str(Path("gaokaollm_bench/outputs/major_training_probe")),
    )
    parser.add_argument("--label-field", default="leaf_id")
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument("--epochs", type=int, default=8)
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--seed", type=int, default=42)
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    rows = _read_jsonl(Path(args.input_jsonl))
    labels = [row.get(args.label_field) for row in rows]

    label_map = {label: idx for idx, label in enumerate(sorted(set(labels)))}
    y = np.asarray([label_map[label] for label in labels], dtype=np.int64)

    data = np.load(Path(args.embeddings), allow_pickle=True)
    embeddings = data["embeddings"].astype(np.float32)

    if embeddings.shape[0] != y.shape[0]:
        raise ValueError("Embeddings count does not match labels")

    X_train, X_temp, y_train, y_temp = train_test_split(
        embeddings, y, test_size=0.2, random_state=args.seed, stratify=y
    )
    X_val, X_test, y_val, y_test = train_test_split(
        X_temp, y_temp, test_size=0.5, random_state=args.seed, stratify=y_temp
    )

    torch.manual_seed(args.seed)

    train_loader = DataLoader(
        TensorDataset(torch.from_numpy(X_train), torch.from_numpy(y_train)),
        batch_size=args.batch_size,
        shuffle=True,
    )
    val_loader = DataLoader(
        TensorDataset(torch.from_numpy(X_val), torch.from_numpy(y_val)),
        batch_size=args.batch_size,
        shuffle=False,
    )
    test_loader = DataLoader(
        TensorDataset(torch.from_numpy(X_test), torch.from_numpy(y_test)),
        batch_size=args.batch_size,
        shuffle=False,
    )

    model = nn.Linear(embeddings.shape[1], len(label_map))
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.lr)
    loss_fn = nn.CrossEntropyLoss()

    best_val = 0.0
    best_state = None

    for epoch in range(1, args.epochs + 1):
        model.train()
        for xb, yb in train_loader:
            optimizer.zero_grad()
            logits = model(xb)
            loss = loss_fn(logits, yb)
            loss.backward()
            optimizer.step()

        model.eval()
        val_preds = []
        val_true = []
        with torch.no_grad():
            for xb, yb in val_loader:
                logits = model(xb)
                val_preds.extend(torch.argmax(logits, dim=1).cpu().numpy())
                val_true.extend(yb.cpu().numpy())

        val_f1 = f1_score(val_true, val_preds, average="macro")
        if val_f1 > best_val:
            best_val = val_f1
            best_state = {"state_dict": model.state_dict()}
        print(f"epoch={epoch} val_macro_f1={val_f1:.4f}")

    if best_state:
        torch.save(best_state, output_dir / "probe.pt")

    model.eval()
    test_preds = []
    test_true = []
    with torch.no_grad():
        for xb, yb in test_loader:
            logits = model(xb)
            test_preds.extend(torch.argmax(logits, dim=1).cpu().numpy())
            test_true.extend(yb.cpu().numpy())

    report = classification_report(test_true, test_preds, output_dict=True)
    metrics = {
        "val_macro_f1_best": best_val,
        "test_macro_f1": report["macro avg"]["f1-score"],
        "test_accuracy": report["accuracy"],
    }
    (output_dir / "metrics.json").write_text(
        json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (output_dir / "label_map.json").write_text(
        json.dumps(label_map, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print(f"Saved probe to {output_dir / 'probe.pt'}")


if __name__ == "__main__":
    main()
