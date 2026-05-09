"""Flow helpers for benchmark validation and diagnosis."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

from gaokaollm_bench.chains.json_repair import repair_major_payload
from gaokaollm_bench.chains.major_classification import classify_major
from gaokaollm_bench.chains.major_review import review_major_candidates
from gaokaollm_bench.contracts.llm_io import MajorLabelOption
from gaokaollm_bench.data_gen.major_embedding import _normalize_text
from gaokaollm_bench.llm.openai_chat import OpenAIChatClient


async def classify_many(
    samples: list[dict[str, Any]],
    *,
    llm_client: OpenAIChatClient,
    model: str,
    label_options: list[MajorLabelOption],
    concurrency: int,
    allow_null: bool,
) -> list[dict[str, Any]]:
    semaphore = asyncio.Semaphore(max(1, concurrency))

    async def _run(sample: dict[str, Any]) -> dict[str, Any]:
        async with semaphore:
            result = await classify_major(
                llm_client=llm_client,
                model=model,
                major_name=str(sample.get("major_name") or ""),
                normalized_text=sample.get("normalized_text"),
                label_options=label_options,
                allow_null=allow_null,
            )
            return result.model_dump()

    return list(await asyncio.gather(*[_run(sample) for sample in samples]))


def revalidate_outputs(
    outputs: list[dict[str, Any]],
    samples: list[dict[str, Any]],
    label_options: list[MajorLabelOption],
    *,
    allow_null: bool,
) -> list[dict[str, Any]]:
    return [
        {
            **repair_major_payload(
                output.get("repaired_json") or output.get("raw_output") or output,
                major_name=str(sample.get("major_name") or ""),
                label_options=label_options,
                allow_null=allow_null,
            )
        }
        for sample, output in zip(samples, outputs)
    ]


async def review_probe_rows(
    probe_rows: list[dict[str, Any]],
    *,
    threshold: float,
    llm_client: OpenAIChatClient,
    model: str,
    concurrency: int,
) -> list[dict[str, Any]]:
    rows = []
    for row in probe_rows:
        top1 = float(row["top1_probability"])
        rows.append(
            {
                "major_name": row["text"],
                "recommended_label": row["pred_label"],
                "recommended_label_name": row["predictions"][0]["label_name"],
                "recommended_probability": top1,
                "probe_predictions": row["predictions"],
                "review_status": "low_confidence" if top1 < threshold else "pending",
                "gold_label": row["gold_label"],
            }
        )
    low_conf = [row for row in rows if row["review_status"] == "low_confidence"]
    semaphore = asyncio.Semaphore(max(1, concurrency))

    async def _review(row: dict[str, Any]) -> tuple[str, dict[str, Any]]:
        candidates = [
            {"label": pred["label"], "label_name": pred["label_name"]}
            for pred in row["probe_predictions"]
        ]
        payload = {"major_name": row["major_name"], "candidates": candidates}
        async with semaphore:
            reviewed = await review_major_candidates(
                llm_client=llm_client, model=model, items=[payload]
            )
        return str(row["major_name"]), reviewed.get(str(row["major_name"])) or {}

    reviewed_map = (
        dict(await asyncio.gather(*[_review(row) for row in low_conf]))
        if low_conf
        else {}
    )
    for row in rows:
        item = reviewed_map.get(str(row["major_name"]))
        if item and item.get("selected_label"):
            row["selected_label"] = item["selected_label"]
            row["selected_label_name"] = next(
                (
                    pred["label_name"]
                    for pred in row["probe_predictions"]
                    if pred["label"] == item["selected_label"]
                ),
                None,
            )
            row["review_status"] = "llm_reviewed"
            row["llm_review"] = item
        else:
            row["selected_label"] = row["recommended_label"]
            row["selected_label_name"] = row["recommended_label_name"]
            if row["review_status"] == "low_confidence":
                row["review_status"] = "llm_failed_or_unchanged"
    return rows


async def probe_one_major(
    *,
    major_name: str,
    label_options: list[MajorLabelOption],
    small_model: str,
    llm_model: str,
    llm_client: OpenAIChatClient,
    output_dir: Path,
) -> list[dict[str, Any]]:
    variants = [
        {"variant": "allow_null_full_labels", "allow_null": True, "labels_only": False},
        {
            "variant": "enum_no_null_full_labels",
            "allow_null": False,
            "labels_only": False,
        },
        {
            "variant": "enum_no_null_label_ids_only",
            "allow_null": False,
            "labels_only": True,
        },
        {
            "variant": "enum_allow_null_full_labels",
            "allow_null": True,
            "labels_only": False,
        },
    ]
    tasks = []
    for role, model in [("small", small_model), ("kimi", llm_model)]:
        for variant in variants:
            tasks.append((role, model, variant))

    async def _run(role: str, model: str, variant: dict[str, Any]) -> dict[str, Any]:
        result = await classify_major(
            llm_client=llm_client,
            model=model,
            major_name=major_name,
            normalized_text=_normalize_text(major_name),
            label_options=label_options,
            allow_null=bool(variant["allow_null"]),
            labels_only=bool(variant["labels_only"]),
        )
        return {
            "model_role": role,
            "model": model,
            **variant,
            "output": result.model_dump(),
        }

    results = list(await asyncio.gather(*[_run(*task) for task in tasks]))
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "probe_one_major.json").write_text(
        json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return results
