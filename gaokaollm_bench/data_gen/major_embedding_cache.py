"""Cache embeddings for linear-probe training (API-based, no training here)."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Iterable

import numpy as np

from gaokaollm_bench.data_gen.major_embedding import OpenAIEmbeddingClient, _normalize_text


def _read_jsonl(path: Path) -> list[dict]:
    rows = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def _chunk(items: list[str], size: int) -> Iterable[list[str]]:
    for start in range(0, len(items), size):
        yield items[start : start + size]


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Cache embeddings for training")
    parser.add_argument(
        "--input",
        default=str(Path("gaokaollm_bench/outputs/major_training/train.jsonl")),
    )
    parser.add_argument(
        "--output",
        default=str(Path("gaokaollm_bench/outputs/major_training/embeddings.npz")),
    )
    parser.add_argument("--text-field", default="normalized_text")
    parser.add_argument("--batch-size", type=int, default=128)
    return parser.parse_args()


async def main() -> None:
    args = _parse_args()
    input_path = Path(args.input)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    rows = _read_jsonl(input_path)
    texts = []
    for row in rows:
        text = str(row.get(args.text_field) or row.get("text") or "").strip()
        texts.append(_normalize_text(text))

    client = OpenAIEmbeddingClient()
    vectors: list[list[float]] = []

    for batch in _chunk(texts, args.batch_size):
        vectors.extend(await client.embed(batch))

    embeddings = np.asarray(vectors, dtype=np.float32)
    np.savez_compressed(
        output_path,
        embeddings=embeddings,
        texts=np.asarray(texts, dtype=object),
    )

    print(f"Cached {len(texts)} embeddings to {output_path}")


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
