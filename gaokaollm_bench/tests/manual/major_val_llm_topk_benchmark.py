"""Evaluate top-k probe candidates and LLM relabeling on the clean validation set.

This manual runner reads existing validation/probe artifacts, computes Top-k
candidate pools, and optionally calls the configured LLM for constrained and
direct relabeling. It does not connect to the database or run Agent benchmarks.
"""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path
from typing import Any

import numpy as np
import torch
from dotenv import load_dotenv

from gaokaollm_bench.chains.json_repair import parse_llm_json
from gaokaollm_bench.constrains.llm import DEFAULT_OPENAI_MODEL
from gaokaollm_bench.data_gen.major_probe_predict import _load_probe
from gaokaollm_bench.data_gen.major_tree import load_major_tree
from gaokaollm_bench.llm.openai_chat import OpenAIChatClient
from gaokaollm_bench.tests.manual.major_val_benchmark import (
    DEFAULT_EMBEDDINGS,
    DEFAULT_LABEL_MAP,
    DEFAULT_PROBE,
    DEFAULT_TREE,
    DEFAULT_VAL_PATH,
    _load_embeddings,
    _load_label_map,
    _metrics,
    _read_jsonl,
)


DEFAULT_OUTPUT_DIR = Path("gaokaollm_bench/outputs/major_val_llm_topk_benchmark")
TOP_K_VALUES = (1, 3, 5, 10)
CONFIDENCE_THRESHOLDS = (0.20, 0.35, 0.50, 0.65)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Evaluate major-tree Top-k candidate pools and LLM relabeling."
    )
    parser.add_argument("--val-jsonl", default=str(DEFAULT_VAL_PATH))
    parser.add_argument("--embeddings", default=str(DEFAULT_EMBEDDINGS))
    parser.add_argument("--probe", default=str(DEFAULT_PROBE))
    parser.add_argument("--label-map", default=str(DEFAULT_LABEL_MAP))
    parser.add_argument("--major-tree", default=str(DEFAULT_TREE))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--model", default=DEFAULT_OPENAI_MODEL)
    parser.add_argument("--concurrency", type=int, default=4)
    parser.add_argument("--candidate-batch-size", type=int, default=6)
    parser.add_argument("--direct-batch-size", type=int, default=3)
    parser.add_argument("--request-timeout", type=float, default=120.0)
    parser.add_argument(
        "--skip-llm",
        action="store_true",
        help="Only compute probe Top-k statistics without LLM calls.",
    )
    return parser.parse_args()


def _node_name(nodes: dict[str, Any], label: str) -> str:
    node = nodes.get(label) or {}
    return str(node.get("label") or label)


def _compute_probe_topk(
    args: argparse.Namespace,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    val_rows = _read_jsonl(Path(args.val_jsonl))
    embeddings, val_matched = _load_embeddings(val_rows, Path(args.embeddings))
    label_map, inv_label_map = _load_label_map(Path(args.label_map))
    model, _, nodes = _load_probe(
        probe_path=Path(args.probe),
        label_map_path=Path(args.label_map),
        major_tree_path=Path(args.major_tree),
    )

    rows: list[dict[str, Any]] = []
    y_true: list[int] = []
    y_pred: list[int] = []
    hit_counts = {k: 0 for k in TOP_K_VALUES}
    max_k = max(TOP_K_VALUES)

    for idx, row in enumerate(val_matched):
        label = str(row["leaf_id"])
        vec = torch.from_numpy(
            embeddings[int(row["_embedding_index"]) : int(row["_embedding_index"]) + 1]
        )
        with torch.no_grad():
            probs = torch.softmax(model(vec), dim=1).cpu().numpy()[0]
        top_indices = np.argsort(probs)[::-1][:max_k]
        predictions = [
            {
                "label": inv_label_map[int(item_idx)],
                "label_name": _node_name(nodes, inv_label_map[int(item_idx)]),
                "probability": float(probs[int(item_idx)]),
            }
            for item_idx in top_indices
        ]
        pred_label = predictions[0]["label"]
        y_true.append(label_map[label])
        y_pred.append(label_map[pred_label])
        for k in TOP_K_VALUES:
            hit_counts[k] += int(label in {pred["label"] for pred in predictions[:k]})
        rows.append(
            {
                "item_id": f"val-{idx + 1:03d}",
                "major_name": row.get("text") or row.get("normalized_text") or "",
                "normalized_text": row["_normalized_text"],
                "gold_label": label,
                "gold_label_name": _node_name(nodes, label),
                "pred_label": pred_label,
                "pred_label_name": predictions[0]["label_name"],
                "top1_probability": predictions[0]["probability"],
                "predictions": predictions,
            }
        )

    probe_metrics = _metrics(
        y_true,
        y_pred,
        labels=list(range(len(label_map))),
        target_names=[inv_label_map[i] for i in sorted(inv_label_map)],
    )
    probe_metrics["hit_at_k"] = {
        f"hit@{k}": hit_counts[k] / len(rows) if rows else 0.0 for k in TOP_K_VALUES
    }
    return rows, probe_metrics


def _safe_parse(raw: str) -> Any:
    try:
        return parse_llm_json(raw)
    except Exception:
        text = raw.strip()
        starts = [idx for idx in (text.find("{"), text.find("[")) if idx >= 0]
        end = max(text.rfind("}"), text.rfind("]"))
        if starts and end > min(starts):
            try:
                return json.loads(text[min(starts) : end + 1])
            except Exception:
                return {}
    return {}


def _items_from_payload(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, dict) and isinstance(payload.get("items"), list):
        return [item for item in payload["items"] if isinstance(item, dict)]
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if isinstance(payload, dict):
        return [payload]
    return []


def _repair_outputs(
    *,
    rows: list[dict[str, Any]],
    raw_batches: list[dict[str, Any]],
    candidate_k: int | None,
    all_labels: set[str],
) -> list[dict[str, Any]]:
    by_id: dict[str, dict[str, Any]] = {}
    for batch in raw_batches:
        parsed = _safe_parse(str(batch.get("raw_content") or ""))
        for item in _items_from_payload(parsed):
            item_id = str(item.get("item_id") or "")
            selected = (
                item.get("selected_label") or item.get("label") or item.get("leaf_id")
            )
            reason = str(item.get("reason") or "")
            by_id[item_id] = {
                "item_id": item_id,
                "selected_label": str(selected) if selected is not None else None,
                "reason": reason,
                "raw_batch_index": batch.get("batch_index"),
            }

    repaired: list[dict[str, Any]] = []
    for row in rows:
        item = by_id.get(row["item_id"]) or {}
        selected = item.get("selected_label")
        if candidate_k is None:
            valid_labels = all_labels
        else:
            valid_labels = {pred["label"] for pred in row["predictions"][:candidate_k]}
        label_valid = selected in valid_labels
        selected_label = selected if label_valid else row["pred_label"]
        selected_name = next(
            (
                pred["label_name"]
                for pred in row["predictions"]
                if pred["label"] == selected_label
            ),
            None,
        )
        repaired.append(
            {
                **row,
                "selected_label": selected_label,
                "selected_label_name": selected_name,
                "llm_selected_label": selected,
                "label_valid": label_valid,
                "llm_reason": item.get("reason") or "",
                "raw_batch_index": item.get("raw_batch_index"),
            }
        )
    return repaired


def _result_metrics(
    rows: list[dict[str, Any]],
    *,
    label_map: dict[str, int],
    inv_label_map: dict[int, str],
    reviewed_subset: set[str] | None = None,
) -> dict[str, Any]:
    y_true: list[int] = []
    y_pred: list[int] = []
    changed = corrected = regressed = invalid = 0
    for row in rows:
        gold = str(row["gold_label"])
        pred = str(row.get("selected_label") or row["pred_label"])
        is_reviewed = reviewed_subset is None or row["item_id"] in reviewed_subset
        if is_reviewed and row.get("label_valid") is False:
            invalid += 1
        if gold not in label_map or pred not in label_map:
            continue
        y_true.append(label_map[gold])
        y_pred.append(label_map[pred])
        if is_reviewed and pred != row["pred_label"]:
            changed += 1
            if pred == gold and row["pred_label"] != gold:
                corrected += 1
            if pred != gold and row["pred_label"] == gold:
                regressed += 1

    metrics = _metrics(
        y_true,
        y_pred,
        labels=list(range(len(label_map))),
        target_names=[inv_label_map[i] for i in sorted(inv_label_map)],
    )
    metrics.update(
        {
            "invalid_count": invalid,
            "changed_count": changed,
            "corrected_count": corrected,
            "regressed_count": regressed,
        }
    )
    return metrics


def _direct_llm_metrics(
    rows: list[dict[str, Any]],
    *,
    label_map: dict[str, int],
    inv_label_map: dict[int, str],
) -> dict[str, Any]:
    y_true: list[int] = []
    y_pred: list[int] = []
    changed = corrected = regressed = 0
    valid_count = strict_correct = 0
    for row in rows:
        gold = str(row["gold_label"])
        selected = row.get("llm_selected_label")
        if (
            not row.get("label_valid")
            or selected not in label_map
            or gold not in label_map
        ):
            continue
        valid_count += 1
        pred = str(selected)
        y_true.append(label_map[gold])
        y_pred.append(label_map[pred])
        strict_correct += int(pred == gold)
        if pred != row["pred_label"]:
            changed += 1
            if pred == gold and row["pred_label"] != gold:
                corrected += 1
            if pred != gold and row["pred_label"] == gold:
                regressed += 1

    metrics = _metrics(
        y_true,
        y_pred,
        labels=list(range(len(label_map))),
        target_names=[inv_label_map[i] for i in sorted(inv_label_map)],
    )
    total = len(rows)
    metrics.update(
        {
            "valid_coverage": valid_count / total if total else 0.0,
            "strict_accuracy": strict_correct / total if total else 0.0,
            "valid_accuracy": metrics["accuracy"],
            "invalid_count": total - valid_count,
            "changed_count": changed,
            "corrected_count": corrected,
            "regressed_count": regressed,
        }
    )
    return metrics


def _threshold_analysis(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result = []
    for threshold in CONFIDENCE_THRESHOLDS:
        subset = [row for row in rows if float(row["top1_probability"]) < threshold]
        wrong = [row for row in subset if row["pred_label"] != row["gold_label"]]
        result.append(
            {
                "threshold": threshold,
                "review_count": len(subset),
                "review_rate": len(subset) / len(rows) if rows else 0.0,
                "wrong_count": len(wrong),
                "wrong_gold_in_top3": sum(
                    row["gold_label"]
                    in {pred["label"] for pred in row["predictions"][:3]}
                    for row in wrong
                ),
                "wrong_gold_in_top5": sum(
                    row["gold_label"]
                    in {pred["label"] for pred in row["predictions"][:5]}
                    for row in wrong
                ),
                "wrong_gold_in_top10": sum(
                    row["gold_label"]
                    in {pred["label"] for pred in row["predictions"][:10]}
                    for row in wrong
                ),
            }
        )
    return result


def _candidate_messages(
    batch: list[dict[str, Any]], *, top_k: int
) -> list[dict[str, str]]:
    payload = {
        "items": [
            {
                "item_id": row["item_id"],
                "major_name": row["major_name"],
                "candidates": [
                    {"label": pred["label"], "label_name": pred["label_name"]}
                    for pred in row["predictions"][:top_k]
                ],
            }
            for row in batch
        ]
    }
    system = (
        "你是高考专业标注复核员。每个 item 都有稳定 item_id、major_name 和候选标签。"
        "候选顺序来自模型概率，只能作为参考；请根据专业名称语义独立判断。"
        "你只能从 candidates 中选择一个 selected_label，不要扩展候选范围。"
        '输出 JSON: {"items":[{"item_id":...,"selected_label":...,"reason":...}]}'
    )
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
    ]


def _direct_messages(
    batch: list[dict[str, Any]], labels: list[dict[str, str]]
) -> list[dict[str, str]]:
    payload = {
        "items": [
            {"item_id": row["item_id"], "major_name": row["major_name"]}
            for row in batch
        ],
        "labels": labels,
    }
    system = (
        "你是高考专业叶子簇分类器。请只从 labels 的 label 字段中选择一个 "
        "selected_label。不要输出 label_name，不要创造新标签。"
        '输出 JSON: {"items":[{"item_id":...,"selected_label":...,"reason":...}]}'
    )
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
    ]


async def _run_llm_batches(
    *,
    client: OpenAIChatClient,
    model: str,
    rows: list[dict[str, Any]],
    output_path: Path,
    batch_size: int,
    concurrency: int,
    mode: str,
    top_k: int | None = None,
    labels: list[dict[str, str]] | None = None,
) -> list[dict[str, Any]]:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    batches = [rows[i : i + batch_size] for i in range(0, len(rows), batch_size)]
    existing_by_index: dict[int, dict[str, Any]] = {}
    if output_path.exists():
        for item in json.loads(output_path.read_text(encoding="utf-8")):
            existing_by_index[int(item["batch_index"])] = item
    completed = [
        item
        for item in existing_by_index.values()
        if not item.get("error") and str(item.get("raw_content") or "").strip()
    ]
    pending = [
        (batch_index, batch)
        for batch_index, batch in enumerate(batches)
        if batch_index not in {int(item["batch_index"]) for item in completed}
    ]
    if not pending:
        return [existing_by_index[idx] for idx in sorted(existing_by_index)]

    semaphore = asyncio.Semaphore(max(1, concurrency))

    async def _one(batch_index: int, batch: list[dict[str, Any]]) -> dict[str, Any]:
        if mode == "candidate":
            assert top_k is not None
            messages = _candidate_messages(batch, top_k=top_k)
        else:
            assert labels is not None
            messages = _direct_messages(batch, labels)
        async with semaphore:
            try:
                raw = await client.complete_json(
                    model=model,
                    messages=messages,
                    response_format={"type": "json_object"},
                    temperature=0,
                )
                return {
                    "batch_index": batch_index,
                    "item_ids": [row["item_id"] for row in batch],
                    "raw_content": raw,
                    "error": None,
                }
            except Exception as exc:  # pragma: no cover - external API
                return {
                    "batch_index": batch_index,
                    "item_ids": [row["item_id"] for row in batch],
                    "raw_content": "",
                    "error": f"{type(exc).__name__}: {exc}",
                }

    new_batches = await asyncio.gather(
        *[_one(batch_index, batch) for batch_index, batch in pending]
    )
    for item in new_batches:
        existing_by_index[int(item["batch_index"])] = item
    raw_batches = [existing_by_index[idx] for idx in sorted(existing_by_index)]
    output_path.write_text(
        json.dumps(raw_batches, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return raw_batches


def _apply_threshold_review(
    base_rows: list[dict[str, Any]],
    llm_rows: list[dict[str, Any]],
    *,
    threshold: float,
) -> tuple[list[dict[str, Any]], set[str]]:
    selected_by_id = {row["item_id"]: row for row in llm_rows}
    reviewed_ids = {
        row["item_id"]
        for row in base_rows
        if float(row["top1_probability"]) < threshold
    }
    merged = []
    for row in base_rows:
        if row["item_id"] in reviewed_ids:
            merged.append(selected_by_id[row["item_id"]])
        else:
            merged.append(
                {
                    **row,
                    "selected_label": row["pred_label"],
                    "selected_label_name": row["pred_label_name"],
                    "label_valid": True,
                }
            )
    return merged, reviewed_ids


def _render_markdown(summary: dict[str, Any]) -> str:
    lines = [
        "# 专业树 Top-k 候选池与 LLM 重标注评估",
        "",
        "本报告只评估专业层级本体 clean validation set，不运行 Agent/Benchmark。",
        "",
        "## Top-k 候选池上限",
        "",
        "| 指标 | 数值 |",
        "|---|---:|",
    ]
    for key, value in summary["probe_metrics"]["hit_at_k"].items():
        lines.append(f"| {key} | {value:.4f} |")

    lines.extend(
        [
            "",
            "## LLM 评估结果",
            "",
            "| 方案 | Accuracy | Macro-F1 | changed | corrected | regressed | invalid |",
            "|---|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for row in summary["llm_results"]:
        metrics = row["metrics"]
        lines.append(
            "| {name} | {accuracy:.4f} | {macro_f1:.4f} | {changed} | {corrected} | {regressed} | {invalid} |".format(
                name=row["name"],
                accuracy=metrics["accuracy"],
                macro_f1=metrics["macro_f1"],
                changed=metrics["changed_count"],
                corrected=metrics["corrected_count"],
                regressed=metrics["regressed_count"],
                invalid=metrics["invalid_count"],
            )
        )

    lines.extend(
        [
            "",
            "## 低置信区间",
            "",
            "| 阈值 | 审校数 | 错误数 | 错误且 gold@5 | 错误且 gold@10 |",
            "|---:|---:|---:|---:|---:|",
        ]
    )
    for row in summary["threshold_analysis"]:
        lines.append(
            f"| {row['threshold']:.2f} | {row['review_count']} | {row['wrong_count']} | "
            f"{row['wrong_gold_in_top5']} | {row['wrong_gold_in_top10']} |"
        )

    best = summary["recommended_threshold"]
    lines.extend(
        [
            "",
            "## 推荐论文口径",
            "",
            f"- 推荐区间：{best['name']}，Accuracy={best['metrics']['accuracy']:.4f}，"
            f"Macro-F1={best['metrics']['macro_f1']:.4f}。",
            "- 若 Macro-F1 未超过 MLP 单模型，应写作候选池与审校机制分析，"
            "不包装为自动重标注全面提升。",
            "",
        ]
    )
    return "\n".join(lines)


async def main_async(args: argparse.Namespace) -> dict[str, Any]:
    load_dotenv()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    label_map, inv_label_map = _load_label_map(Path(args.label_map))
    tree = load_major_tree(args.major_tree)
    nodes = tree.get("nodes") or tree.get("clusters") or {}
    all_labels = set(label_map)
    label_options = [
        {
            "label": inv_label_map[idx],
            "label_name": _node_name(nodes, inv_label_map[idx]),
        }
        for idx in sorted(inv_label_map)
    ]

    rows, probe_metrics = _compute_probe_topk(args)
    (output_dir / "probe_topk_rows.json").write_text(
        json.dumps(rows, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    llm_results: list[dict[str, Any]] = []
    topk_reviewed: dict[int, list[dict[str, Any]]] = {}
    if not args.skip_llm:
        client = OpenAIChatClient(timeout=args.request_timeout, max_retries=0)
        for top_k in (5, 10):
            raw_batches = await _run_llm_batches(
                client=client,
                model=args.model,
                rows=rows,
                output_path=output_dir / f"llm_candidate_top{top_k}_raw.json",
                batch_size=args.candidate_batch_size,
                concurrency=args.concurrency,
                mode="candidate",
                top_k=top_k,
            )
            repaired = _repair_outputs(
                rows=rows,
                raw_batches=raw_batches,
                candidate_k=top_k,
                all_labels=all_labels,
            )
            topk_reviewed[top_k] = repaired
            (output_dir / f"llm_candidate_top{top_k}_rows.json").write_text(
                json.dumps(repaired, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            llm_results.append(
                {
                    "name": f"candidate_top{top_k}_full",
                    "metrics": _result_metrics(
                        repaired,
                        label_map=label_map,
                        inv_label_map=inv_label_map,
                    ),
                }
            )

        raw_direct = await _run_llm_batches(
            client=client,
            model=args.model,
            rows=rows,
            output_path=output_dir / "llm_direct_raw.json",
            batch_size=args.direct_batch_size,
            concurrency=args.concurrency,
            mode="direct",
            labels=label_options,
        )
        direct_rows = _repair_outputs(
            rows=rows,
            raw_batches=raw_direct,
            candidate_k=None,
            all_labels=all_labels,
        )
        (output_dir / "llm_direct_rows.json").write_text(
            json.dumps(direct_rows, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        direct_metrics = _direct_llm_metrics(
            direct_rows,
            label_map=label_map,
            inv_label_map=inv_label_map,
        )
        llm_results.append({"name": "direct_llm_full", "metrics": direct_metrics})

        for top_k, reviewed_rows in topk_reviewed.items():
            for threshold in CONFIDENCE_THRESHOLDS:
                threshold_rows, reviewed_ids = _apply_threshold_review(
                    rows, reviewed_rows, threshold=threshold
                )
                llm_results.append(
                    {
                        "name": f"candidate_top{top_k}_threshold_{threshold:.2f}",
                        "metrics": _result_metrics(
                            threshold_rows,
                            label_map=label_map,
                            inv_label_map=inv_label_map,
                            reviewed_subset=reviewed_ids,
                        ),
                        "review_count": len(reviewed_ids),
                        "review_rate": len(reviewed_ids) / len(rows) if rows else 0.0,
                    }
                )

    candidates_for_best = [
        row
        for row in llm_results
        if row["name"].startswith("candidate_top") and "_threshold_" in row["name"]
    ]
    recommended = (
        max(
            candidates_for_best or llm_results,
            key=lambda row: (
                float(row["metrics"]["macro_f1"]),
                float(row["metrics"]["accuracy"]),
            ),
        )
        if llm_results
        else {
            "name": "probe_only",
            "metrics": {
                "accuracy": probe_metrics["accuracy"],
                "macro_f1": probe_metrics["macro_f1"],
            },
        }
    )

    summary = {
        "clean_validation_set": {"rows": len(rows), "labels": len(label_map)},
        "probe_metrics": probe_metrics,
        "threshold_analysis": _threshold_analysis(rows),
        "llm_results": llm_results,
        "recommended_threshold": recommended,
    }
    (output_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (output_dir / "summary.md").write_text(_render_markdown(summary), encoding="utf-8")
    return summary


def main() -> None:
    args = _parse_args()
    summary = asyncio.run(main_async(args))
    brief = {
        "hit_at_k": summary["probe_metrics"]["hit_at_k"],
        "recommended": {
            "name": summary["recommended_threshold"]["name"],
            "accuracy": summary["recommended_threshold"]["metrics"]["accuracy"],
            "macro_f1": summary["recommended_threshold"]["metrics"]["macro_f1"],
        },
    }
    print(json.dumps(brief, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
