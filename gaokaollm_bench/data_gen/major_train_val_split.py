"""Split training data into train/val sets (stratified)."""

from __future__ import annotations

import argparse
import json
import random
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def _write_stats(path: Path, rows: list[dict[str, Any]], label_field: str) -> None:
    counts = Counter(row.get(label_field) for row in rows)
    payload = {"total": len(rows), "by_label": dict(counts)}
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Split train.jsonl into train/val")
    parser.add_argument(
        "--input",
        default=str(Path("gaokaollm_bench/outputs/major_training/train.jsonl")),
    )
    parser.add_argument(
        "--output-dir",
        default=str(Path("gaokaollm_bench/outputs/major_training/splits")),
    )
    parser.add_argument("--label-field", default="leaf_id")
    parser.add_argument("--val-ratio", type=float, default=0.1)
    parser.add_argument("--seed", type=int, default=42)
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    rows = _read_jsonl(Path(args.input))
    buckets: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        label = str(row.get(args.label_field))
        buckets[label].append(row)

    rng = random.Random(args.seed)
    train_rows: list[dict[str, Any]] = []
    val_rows: list[dict[str, Any]] = []

    for label, items in buckets.items():
        rng.shuffle(items)
        split_at = max(1, int(len(items) * (1 - args.val_ratio)))
        train_rows.extend(items[:split_at])
        val_rows.extend(items[split_at:])

    rng.shuffle(train_rows)
    rng.shuffle(val_rows)

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    train_path = output_dir / "train.jsonl"
    val_path = output_dir / "val.jsonl"

    _write_jsonl(train_path, train_rows)
    _write_jsonl(val_path, val_rows)

    _write_stats(output_dir / "train.stats.json", train_rows, args.label_field)
    _write_stats(output_dir / "val.stats.json", val_rows, args.label_field)

    print(f"Wrote {len(train_rows)} train rows to {train_path}")
    print(f"Wrote {len(val_rows)} val rows to {val_path}")


if __name__ == "__main__":
    main()
