"""Predict major leaf labels with a trained linear probe."""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

import numpy as np
import torch

from gaokaollm_bench.data_gen.major_embedding import (
    EmbeddingClient,
    OpenAIEmbeddingClient,
    _normalize_text,
)
from gaokaollm_bench.data_gen.major_probe_train import build_probe_model
from gaokaollm_bench.data_gen.major_tree import load_major_tree


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Predict major cluster labels with a probe")
    parser.add_argument(
        "--probe",
        default=str(Path("gaokaollm_bench/outputs/major_training_probe/probe.pt")),
    )
    parser.add_argument(
        "--label-map",
        default=str(Path("gaokaollm_bench/outputs/major_training_probe/label_map.json")),
    )
    parser.add_argument(
        "--major-tree",
        default=str(Path("gaokaollm_bench/data_gen/major_clusters.json")),
    )
    parser.add_argument("--text", action="append", default=[], help="Major text to classify.")
    parser.add_argument("--text-file", default=None, help="Optional UTF-8 text file, one major per line.")
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--json", action="store_true", help="Print JSON instead of readable text.")
    return parser.parse_args()


def _load_texts(args: argparse.Namespace) -> list[str]:
    texts = list(args.text)
    if args.text_file:
        with Path(args.text_file).open("r", encoding="utf-8") as f:
            texts.extend(line.strip() for line in f if line.strip())
    if not texts:
        raise ValueError("Provide at least one --text or --text-file")
    return texts


def _load_probe(
    *,
    probe_path: str | Path,
    label_map_path: str | Path,
    major_tree_path: str | Path,
) -> tuple[torch.nn.Module, dict[int, str], dict]:
    label_map = json.loads(Path(label_map_path).read_text(encoding="utf-8"))
    inv_label_map = {int(v): k for k, v in label_map.items()}
    tree = load_major_tree(major_tree_path)
    nodes = tree.get("nodes") or tree.get("clusters") or {}

    state = torch.load(Path(probe_path), map_location="cpu")
    model_config = state.get("model_config")
    if model_config:
        model = build_probe_model(**model_config)
    else:
        weight = state["state_dict"]["weight"]
        model = torch.nn.Linear(weight.shape[1], len(label_map))
    model.load_state_dict(state["state_dict"])
    model.eval()
    return model, inv_label_map, nodes


async def predict_major_labels(
    texts: list[str],
    *,
    embedding_client: EmbeddingClient | None = None,
    probe_path: str | Path = Path("gaokaollm_bench/outputs/major_training_probe/probe.pt"),
    label_map_path: str | Path = Path("gaokaollm_bench/outputs/major_training_probe/label_map.json"),
    major_tree_path: str | Path = Path("gaokaollm_bench/data_gen/major_clusters.json"),
    top_k: int = 5,
    batch_size: int = 128,
) -> list[dict]:
    """Predict top-k leaf labels for major texts."""

    if not texts:
        return []
    if top_k < 1:
        raise ValueError("top_k must be at least 1")
    if batch_size < 1:
        raise ValueError("batch_size must be at least 1")

    normalized_texts = [_normalize_text(text) for text in texts]
    model, inv_label_map, nodes = _load_probe(
        probe_path=probe_path,
        label_map_path=label_map_path,
        major_tree_path=major_tree_path,
    )
    client = embedding_client or OpenAIEmbeddingClient()

    all_probs: list[np.ndarray] = []
    for start in range(0, len(normalized_texts), batch_size):
        batch = normalized_texts[start : start + batch_size]
        embeddings = np.asarray(await client.embed(batch), dtype=np.float32)
        with torch.no_grad():
            logits = model(torch.from_numpy(embeddings))
            all_probs.extend(torch.softmax(logits, dim=1).cpu().numpy())

    results = []
    top_k = max(1, min(top_k, len(inv_label_map)))
    for text, normalized, row_probs in zip(texts, normalized_texts, all_probs):
        top_indices = np.argsort(row_probs)[::-1][:top_k]
        predictions = []
        for idx in top_indices:
            label = inv_label_map[int(idx)]
            node = nodes.get(label, {})
            predictions.append(
                {
                    "label": label,
                    "label_name": node.get("label") or label,
                    "probability": float(row_probs[idx]),
                }
            )
        results.append(
            {
                "text": text,
                "normalized_text": normalized,
                "predictions": predictions,
            }
        )
    return results


async def _predict(args: argparse.Namespace) -> list[dict]:
    texts = _load_texts(args)
    return await predict_major_labels(
        texts,
        probe_path=args.probe,
        label_map_path=args.label_map,
        major_tree_path=args.major_tree,
        top_k=args.top_k,
    )


def main() -> None:
    args = _parse_args()
    results = asyncio.run(_predict(args))
    if args.json:
        print(json.dumps(results, ensure_ascii=False, indent=2))
        return

    for result in results:
        print(f"{result['text']} -> normalized={result['normalized_text']}")
        for pred in result["predictions"]:
            print(f"  {pred['label']}\t{pred['label_name']}\t{pred['probability']:.6f}")


if __name__ == "__main__":
    main()
