"""Create an embedding cache for a derived dataset from an existing cache."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np

from gaokaollm_bench.data_gen.major_embedding import OpenAIEmbeddingClient, _normalize_text


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Reuse cached embeddings for a derived JSONL dataset")
    parser.add_argument("--input", required=True)
    parser.add_argument(
        "--extra-input",
        action="append",
        default=[],
        help="Optional extra JSONL files whose texts should also be included in the output cache.",
    )
    parser.add_argument("--source-embeddings", default="gaokaollm_bench/outputs/major_training/embeddings.npz")
    parser.add_argument("--output", required=True)
    parser.add_argument("--missing-output", default=None)
    parser.add_argument("--text-field", default="normalized_text")
    parser.add_argument("--allow-missing", action="store_true")
    parser.add_argument("--fetch-missing", action="store_true")
    parser.add_argument("--batch-size", type=int, default=128)
    return parser.parse_args()


def _chunk(items: list[str], size: int) -> list[list[str]]:
    return [items[start : start + size] for start in range(0, len(items), size)]


async def _fetch_missing(texts: list[str], batch_size: int) -> dict[str, np.ndarray]:
    if not texts:
        return {}
    client = OpenAIEmbeddingClient()
    vectors = []
    for batch in _chunk(texts, batch_size):
        vectors.extend(await client.embed(batch))
    return {text: np.asarray(vector, dtype=np.float32) for text, vector in zip(texts, vectors)}


async def main_async() -> None:
    args = _parse_args()
    rows = _read_jsonl(Path(args.input))
    for extra_input in args.extra_input:
        rows.extend(_read_jsonl(Path(extra_input)))
    data = np.load(Path(args.source_embeddings), allow_pickle=True)
    source_texts = [_normalize_text(str(text)) for text in data["texts"].astype(object)]
    source_embeddings = data["embeddings"].astype(np.float32)
    source_index = {text: idx for idx, text in enumerate(source_texts)}

    output_texts = []
    output_embeddings = []
    missing = []
    missing_texts: list[str] = []
    for row in rows:
        text = _normalize_text(str(row.get(args.text_field) or row.get("text") or ""))
        idx = source_index.get(text)
        if idx is None:
            missing.append({"text": row.get("text"), "normalized_text": text, "leaf_id": row.get("leaf_id")})
            if text:
                missing_texts.append(text)
            continue
        output_texts.append(text)
        output_embeddings.append(source_embeddings[idx])

    fetched = await _fetch_missing(sorted(set(missing_texts)), args.batch_size) if args.fetch_missing else {}
    if fetched:
        missing = [item for item in missing if item["normalized_text"] not in fetched]
        for row in rows:
            raw_text = str(row.get(args.text_field) or row.get("text") or "")
            text = _normalize_text(raw_text)
            if text in source_index:
                continue
            vector = fetched.get(text)
            if vector is None:
                continue
            # Keep the original lookup field for fetched vectors. Some nested
            # major names normalize differently after a second pass; the trainer
            # builds its text index by normalizing cache texts once.
            output_texts.append(raw_text)
            output_embeddings.append(vector)

    missing_path = Path(args.missing_output) if args.missing_output else Path(args.output).with_suffix(
        ".missing.json"
    )
    missing_path.parent.mkdir(parents=True, exist_ok=True)
    missing_path.write_text(json.dumps(missing, ensure_ascii=False, indent=2), encoding="utf-8")
    if missing and not args.allow_missing:
        raise SystemExit(
            f"Missing {len(missing)} embeddings. See {missing_path}. "
            "Run with --fetch-missing or pass --allow-missing for diagnostic experiments."
        )

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        output_path,
        embeddings=np.asarray(output_embeddings, dtype=np.float32),
        texts=np.asarray(output_texts, dtype=object),
    )
    print(f"Wrote {len(output_texts)} embeddings to {output_path}; missing={len(missing)}")


if __name__ == "__main__":
    import asyncio

    asyncio.run(main_async())
