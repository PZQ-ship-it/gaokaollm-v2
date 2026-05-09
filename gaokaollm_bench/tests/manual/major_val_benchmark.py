"""Unified validation benchmark for embedding, probe, and LLM stages."""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path
from typing import Any

import numpy as np
import torch
from dotenv import load_dotenv

from gaokaollm_bench.chains.major_classification import build_label_options
from gaokaollm_bench.constrains.llm import DEFAULT_OPENAI_MODEL, DEFAULT_SMALL_MODEL
from gaokaollm_bench.constrains.metrics import (
    DEFAULT_VAL_BENCHMARK_REVIEW_THRESHOLD,
    VAL_BENCHMARK_THRESHOLD_SWEEP,
)
from gaokaollm_bench.constrains.paths import (
    MAJOR_ABLATION_BEST_LABEL_MAP,
    MAJOR_ABLATION_BEST_PROBE,
    MAJOR_EMBEDDINGS_UNION_VAL_FILLED,
    MAJOR_FINAL_TREE,
    MAJOR_RAW_TRAIN_ONLY_JSONL,
    MAJOR_VAL_BENCHMARK_DIR,
    MAJOR_VAL_JSONL,
)
from gaokaollm_bench.data_gen.major_embedding import _normalize_text
from gaokaollm_bench.data_gen.major_probe_validate import _classification_report
from gaokaollm_bench.data_gen.major_tree import load_major_tree
from gaokaollm_bench.data_gen.major_probe_predict import _load_probe
from gaokaollm_bench.flows.major_validation_flow import (
    classify_many,
    probe_one_major,
    revalidate_outputs,
    review_probe_rows,
)
from gaokaollm_bench.llm.openai_chat import OpenAIChatClient


DEFAULT_VAL_PATH = MAJOR_VAL_JSONL
DEFAULT_TRAIN_PATH = MAJOR_RAW_TRAIN_ONLY_JSONL
DEFAULT_EMBEDDINGS = MAJOR_EMBEDDINGS_UNION_VAL_FILLED
DEFAULT_PROBE = MAJOR_ABLATION_BEST_PROBE
DEFAULT_LABEL_MAP = MAJOR_ABLATION_BEST_LABEL_MAP
DEFAULT_TREE = MAJOR_FINAL_TREE
DEFAULT_OUTPUT_DIR = MAJOR_VAL_BENCHMARK_DIR


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run unified val benchmark")
    parser.add_argument("--val-jsonl", default=str(DEFAULT_VAL_PATH))
    parser.add_argument("--train-jsonl", default=str(DEFAULT_TRAIN_PATH))
    parser.add_argument("--embeddings", default=str(DEFAULT_EMBEDDINGS))
    parser.add_argument("--probe", default=str(DEFAULT_PROBE))
    parser.add_argument("--label-map", default=str(DEFAULT_LABEL_MAP))
    parser.add_argument("--major-tree", default=str(DEFAULT_TREE))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument(
        "--threshold", type=float, default=DEFAULT_VAL_BENCHMARK_REVIEW_THRESHOLD
    )
    parser.add_argument("--small-model", default=DEFAULT_SMALL_MODEL)
    parser.add_argument("--llm-model", default=DEFAULT_OPENAI_MODEL)
    parser.add_argument("--direct-batch-size", type=int, default=1)
    parser.add_argument("--direct-concurrency", type=int, default=20)
    parser.add_argument("--review-batch-size", type=int, default=4)
    parser.add_argument("--review-concurrency", type=int, default=20)
    parser.add_argument("--request-timeout", type=float, default=90.0)
    parser.add_argument("--allow-null-direct", action="store_true")
    parser.add_argument("--probe-one-major", default=None)
    parser.add_argument("--skip-llm", action="store_true")
    parser.add_argument("--reuse-direct-outputs", action="store_true")
    return parser.parse_args()


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def _load_label_map(path: Path) -> tuple[dict[str, int], dict[int, str]]:
    label_map = json.loads(path.read_text(encoding="utf-8"))
    return label_map, {int(v): k for k, v in label_map.items()}


def _node_name(tree: dict[str, Any], label: str) -> str:
    node = (tree.get("nodes") or {}).get(label) or {}
    return str(node.get("label") or label)


def _embedding_index(data: np.lib.npyio.NpzFile) -> dict[str, int]:
    return {
        _normalize_text(str(text)): idx
        for idx, text in enumerate(data["texts"].astype(object))
    }


def _load_embeddings(
    rows: list[dict[str, Any]], path: Path
) -> tuple[np.ndarray, list[dict[str, Any]]]:
    data = np.load(path, allow_pickle=True)
    embeddings = data["embeddings"].astype(np.float32)
    index = _embedding_index(data)
    matched = []
    for row in rows:
        text = _normalize_text(str(row.get("normalized_text") or row.get("text") or ""))
        idx = index.get(text)
        if idx is not None:
            matched.append({**row, "_embedding_index": idx, "_normalized_text": text})
    return embeddings, matched


def _metrics(
    y_true: list[int], y_pred: list[int], *, labels: list[int], target_names: list[str]
) -> dict[str, Any]:
    y_true_arr = np.asarray(y_true, dtype=np.int64)
    y_pred_arr = np.asarray(y_pred, dtype=np.int64)
    report = _classification_report(
        y_true_arr, y_pred_arr, labels=labels, target_names=target_names
    )
    return {
        "total": int(y_true_arr.size),
        "accuracy": float((y_true_arr == y_pred_arr).mean())
        if y_true_arr.size
        else 0.0,
        "macro_f1": report["macro avg"]["f1-score"],
        "weighted_f1": report["weighted avg"]["f1-score"],
        "classification_report": report,
    }


def _normalize_centroid(vec: np.ndarray) -> np.ndarray:
    norm = float(np.linalg.norm(vec))
    return vec / norm if norm else vec


def _embedding_only_baseline(
    train_rows: list[dict[str, Any]],
    val_rows: list[dict[str, Any]],
    embeddings: np.ndarray,
    label_map: dict[str, int],
    inv_label_map: dict[int, str],
) -> dict[str, Any]:
    label_vectors: dict[str, list[np.ndarray]] = {}
    for row in train_rows:
        label_vectors.setdefault(str(row["leaf_id"]), []).append(
            embeddings[int(row["_embedding_index"])]
        )

    ordered_labels = [inv_label_map[idx] for idx in sorted(inv_label_map)]
    centroids = []
    for label in ordered_labels:
        vectors = label_vectors.get(label, [])
        centroids.append(
            _normalize_centroid(np.mean(np.asarray(vectors, dtype=np.float32), axis=0))
            if vectors
            else np.zeros(embeddings.shape[1], dtype=np.float32)
        )
    centroid_matrix = np.asarray(centroids, dtype=np.float32)

    y_true: list[int] = []
    y_pred: list[int] = []
    top3_hit = 0
    for row in val_rows:
        label = str(row["leaf_id"])
        scores = centroid_matrix @ _normalize_centroid(
            embeddings[int(row["_embedding_index"])]
        )
        top_indices = np.argsort(scores)[::-1][:3]
        pred_label = ordered_labels[int(top_indices[0])]
        y_true.append(label_map[label])
        y_pred.append(label_map[pred_label])
        top3_hit += int(label in {ordered_labels[int(i)] for i in top_indices})

    result = _metrics(
        y_true,
        y_pred,
        labels=list(range(len(label_map))),
        target_names=[inv_label_map[i] for i in sorted(inv_label_map)],
    )
    result["top3_accuracy"] = top3_hit / len(val_rows) if val_rows else 0.0
    result["stage"] = "embedding_only"
    return result


def _probe_baseline(
    val_rows: list[dict[str, Any]],
    embeddings: np.ndarray,
    *,
    probe_path: Path,
    label_map_path: Path,
    major_tree_path: Path,
) -> dict[str, Any]:
    label_map, inv_label_map = _load_label_map(label_map_path)
    tree = load_major_tree(major_tree_path)
    model, _, _ = _load_probe(
        probe_path=probe_path,
        label_map_path=label_map_path,
        major_tree_path=major_tree_path,
    )
    y_true: list[int] = []
    y_pred: list[int] = []
    top3_hit = 0
    per_sample = []
    for row in val_rows:
        label = str(row["leaf_id"])
        vec = torch.from_numpy(
            embeddings[int(row["_embedding_index"]) : int(row["_embedding_index"]) + 1]
        )
        with torch.no_grad():
            probs = torch.softmax(model(vec), dim=1).cpu().numpy()[0]
        top_indices = np.argsort(probs)[::-1][:3]
        pred_label = inv_label_map[int(top_indices[0])]
        y_true.append(label_map[label])
        y_pred.append(int(top_indices[0]))
        top3_hit += int(label in {inv_label_map[int(i)] for i in top_indices})
        per_sample.append(
            {
                "text": row.get("text") or row.get("normalized_text"),
                "normalized_text": row["_normalized_text"],
                "gold_label": label,
                "pred_label": pred_label,
                "top1_probability": float(probs[int(top_indices[0])]),
                "predictions": [
                    {
                        "label": inv_label_map[int(i)],
                        "label_name": _node_name(tree, inv_label_map[int(i)]),
                        "probability": float(probs[int(i)]),
                    }
                    for i in top_indices
                ],
            }
        )
    result = _metrics(
        y_true,
        y_pred,
        labels=list(range(len(label_map))),
        target_names=[inv_label_map[i] for i in sorted(inv_label_map)],
    )
    result["top3_accuracy"] = top3_hit / len(val_rows) if val_rows else 0.0
    result["per_sample"] = per_sample
    result["stage"] = "probe"
    return result


def _direct_metrics(
    rows: list[dict[str, Any]],
    outputs: list[dict[str, Any]],
    *,
    label_map: dict[str, int],
    inv_label_map: dict[int, str],
) -> dict[str, Any]:
    y_true: list[int] = []
    y_pred: list[int] = []
    invalid_outputs = []
    errors = []
    correct = 0
    for row, item in zip(rows, outputs):
        gold = str(row["leaf_id"])
        pred = item.get("selected_label")
        if item.get("error"):
            errors.append({"major_name": row.get("text"), "error": item.get("error")})
        if not pred or pred not in label_map:
            invalid_outputs.append(
                {
                    "major_name": row.get("text"),
                    "gold_label": gold,
                    "selected_label": pred,
                    "raw_output": item,
                }
            )
            continue
        pred_id = label_map[str(pred)]
        y_true.append(label_map[gold])
        y_pred.append(pred_id)
        correct += int(pred_id == label_map[gold])
    result = _metrics(
        y_true,
        y_pred,
        labels=list(range(len(label_map))),
        target_names=[inv_label_map[i] for i in sorted(inv_label_map)],
    )
    result["evaluated_total"] = len(rows)
    result["valid_prediction_count"] = len(y_true)
    result["invalid_prediction_count"] = len(invalid_outputs)
    result["error_count"] = len(errors)
    result["coverage"] = len(y_true) / len(rows) if rows else 0.0
    result["valid_accuracy"] = result["accuracy"]
    result["strict_accuracy"] = correct / len(rows) if rows else 0.0
    result["invalid_examples"] = invalid_outputs[:10]
    result["error_examples"] = errors[:10]
    return result


async def main_async(args: argparse.Namespace) -> dict[str, Any]:
    load_dotenv()
    val_rows = _read_jsonl(Path(args.val_jsonl))
    train_rows = _read_jsonl(Path(args.train_jsonl))
    embeddings, val_matched = _load_embeddings(val_rows, Path(args.embeddings))
    _, train_matched = _load_embeddings(train_rows, Path(args.embeddings))
    label_map, inv_label_map = _load_label_map(Path(args.label_map))
    tree = load_major_tree(args.major_tree)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    embedding_only = _embedding_only_baseline(
        train_matched, val_matched, embeddings, label_map, inv_label_map
    )
    probe = _probe_baseline(
        val_matched,
        embeddings,
        probe_path=Path(args.probe),
        label_map_path=Path(args.label_map),
        major_tree_path=Path(args.major_tree),
    )

    label_options = build_label_options(
        [
            {
                "label": inv_label_map[idx],
                "label_name": _node_name(tree, inv_label_map[idx]),
            }
            for idx in sorted(inv_label_map)
        ]
    )
    if args.skip_llm:
        result = {
            "embedding_only": embedding_only,
            "probe": probe,
            "direct_small": {"status": "skipped"},
            "direct_kimi": {"status": "skipped"},
            "threshold_sweep": [],
        }
        (output_dir / "summary_local_only.json").write_text(
            json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        return result

    llm_client = OpenAIChatClient(timeout=args.request_timeout, max_retries=0)
    if args.probe_one_major:
        diagnosis = await probe_one_major(
            major_name=args.probe_one_major,
            label_options=label_options,
            small_model=args.small_model,
            llm_model=args.llm_model,
            llm_client=llm_client,
            output_dir=output_dir,
        )
        return {
            "probe_one_major": diagnosis,
            "embedding_only": embedding_only,
            "probe": probe,
        }

    direct_samples = [
        {
            "major_name": row.get("text") or row.get("normalized_text") or "",
            "normalized_text": row["_normalized_text"],
        }
        for row in val_matched
    ]
    suffix = "allow_null" if args.allow_null_direct else "enum"
    small_path = output_dir / f"direct_small_outputs_{suffix}.json"
    kimi_path = output_dir / f"direct_kimi_outputs_{suffix}.json"
    if args.reuse_direct_outputs:
        fallback_small = output_dir / "direct_small_outputs.json"
        fallback_kimi = output_dir / "direct_kimi_outputs.json"
        direct_small = revalidate_outputs(
            json.loads(
                (small_path if small_path.exists() else fallback_small).read_text(
                    encoding="utf-8"
                )
            ),
            direct_samples,
            label_options,
            allow_null=args.allow_null_direct,
        )
        direct_kimi = revalidate_outputs(
            json.loads(
                (kimi_path if kimi_path.exists() else fallback_kimi).read_text(
                    encoding="utf-8"
                )
            ),
            direct_samples,
            label_options,
            allow_null=args.allow_null_direct,
        )
    else:
        direct_small = await classify_many(
            direct_samples,
            llm_client=llm_client,
            model=args.small_model,
            label_options=label_options,
            concurrency=args.direct_concurrency,
            allow_null=args.allow_null_direct,
        )
        direct_kimi = await classify_many(
            direct_samples,
            llm_client=llm_client,
            model=args.llm_model,
            label_options=label_options,
            concurrency=args.direct_concurrency,
            allow_null=args.allow_null_direct,
        )
        small_path.write_text(
            json.dumps(direct_small, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        kimi_path.write_text(
            json.dumps(direct_kimi, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    direct_small_metrics = _direct_metrics(
        val_matched, direct_small, label_map=label_map, inv_label_map=inv_label_map
    )
    direct_kimi_metrics = _direct_metrics(
        val_matched, direct_kimi, label_map=label_map, inv_label_map=inv_label_map
    )

    threshold_sweep = []
    for threshold in VAL_BENCHMARK_THRESHOLD_SWEEP:
        reviewed_rows = await review_probe_rows(
            probe["per_sample"],
            threshold=threshold,
            llm_client=llm_client,
            model=args.llm_model,
            concurrency=args.review_concurrency,
        )
        y_true: list[int] = []
        y_pred: list[int] = []
        for row in reviewed_rows:
            gold = str(row["gold_label"])
            pred = str(row["selected_label"])
            if gold in label_map and pred in label_map:
                y_true.append(label_map[gold])
                y_pred.append(label_map[pred])
        threshold_sweep.append(
            {
                "threshold": threshold,
                "llm_review_rate": sum(
                    1
                    for row in probe["per_sample"]
                    if float(row["top1_probability"]) < threshold
                )
                / len(probe["per_sample"])
                if probe["per_sample"]
                else 0.0,
                "metrics": _metrics(
                    y_true,
                    y_pred,
                    labels=list(range(len(label_map))),
                    target_names=[inv_label_map[i] for i in sorted(inv_label_map)],
                ),
            }
        )

    result = {
        "embedding_only": embedding_only,
        "probe": probe,
        "direct_small": direct_small_metrics,
        "direct_kimi": direct_kimi_metrics,
        "threshold_sweep": threshold_sweep,
    }
    (output_dir / "summary.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return result


def _brief(result: dict[str, Any]) -> dict[str, Any]:
    if "probe_one_major" in result:
        return {"probe_one_major": result["probe_one_major"]}
    direct_small = result["direct_small"]
    direct_kimi = result["direct_kimi"]
    return {
        "embedding_only": {
            key: result["embedding_only"][key]
            for key in ("accuracy", "macro_f1", "top3_accuracy")
        },
        "probe": {
            key: result["probe"][key]
            for key in ("accuracy", "macro_f1", "top3_accuracy")
        },
        "direct_small": {
            key: direct_small.get(key)
            for key in ("accuracy", "macro_f1", "coverage", "strict_accuracy")
        }
        if "accuracy" in direct_small
        else direct_small,
        "direct_kimi": {
            key: direct_kimi.get(key)
            for key in ("accuracy", "macro_f1", "coverage", "strict_accuracy")
        }
        if "accuracy" in direct_kimi
        else direct_kimi,
        "threshold_sweep": [
            {
                "threshold": item["threshold"],
                "llm_review_rate": item["llm_review_rate"],
                "accuracy": item["metrics"]["accuracy"],
                "macro_f1": item["metrics"]["macro_f1"],
            }
            for item in result.get("threshold_sweep", [])
        ],
    }


def main() -> None:
    args = _parse_args()
    result = asyncio.run(main_async(args))
    print(json.dumps(_brief(result), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
