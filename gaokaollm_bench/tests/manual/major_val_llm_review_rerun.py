"""Rerun low-confidence major validation review on existing probe outputs.

The script only reads the existing clean validation benchmark summary and calls
the configured LLM for the low-confidence subset. It does not connect to the
database or rerun any Agent benchmark.
"""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from gaokaollm_bench.constrains.llm import DEFAULT_OPENAI_MODEL
from gaokaollm_bench.flows.major_validation_flow import review_probe_rows
from gaokaollm_bench.llm.openai_chat import OpenAIChatClient
from gaokaollm_bench.tests.manual.major_val_benchmark import (
    DEFAULT_LABEL_MAP,
    DEFAULT_OUTPUT_DIR,
    _load_label_map,
    _metrics,
)


DEFAULT_INPUT = DEFAULT_OUTPUT_DIR / "summary.json"
DEFAULT_OUTPUT_DIR_RERUN = Path("gaokaollm_bench/outputs/major_val_llm_review_rerun")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Rerun LLM review for low-confidence major probe validation rows."
    )
    parser.add_argument("--input-summary", default=str(DEFAULT_INPUT))
    parser.add_argument("--label-map", default=str(DEFAULT_LABEL_MAP))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR_RERUN))
    parser.add_argument("--threshold", type=float, default=0.35)
    parser.add_argument("--model", default=DEFAULT_OPENAI_MODEL)
    parser.add_argument("--concurrency", type=int, default=4)
    parser.add_argument("--request-timeout", type=float, default=90.0)
    return parser.parse_args()


def _top3_hit(row: dict[str, Any]) -> bool:
    return str(row["gold_label"]) in {
        str(pred["label"]) for pred in row.get("probe_predictions", [])
    }


def _build_summary(
    *,
    reviewed_rows: list[dict[str, Any]],
    threshold: float,
    label_map: dict[str, int],
    inv_label_map: dict[int, str],
) -> dict[str, Any]:
    y_true: list[int] = []
    y_pred: list[int] = []
    for row in reviewed_rows:
        gold = str(row["gold_label"])
        pred = str(row["selected_label"])
        if gold in label_map and pred in label_map:
            y_true.append(label_map[gold])
            y_pred.append(label_map[pred])

    low_conf = [
        row
        for row in reviewed_rows
        if float(row["recommended_probability"]) < threshold
    ]
    changed = [
        row
        for row in low_conf
        if row.get("selected_label")
        and row["selected_label"] != row["recommended_label"]
    ]
    corrected = [
        row
        for row in changed
        if row["recommended_label"] != row["gold_label"]
        and row["selected_label"] == row["gold_label"]
    ]
    regressed = [
        row
        for row in changed
        if row["recommended_label"] == row["gold_label"]
        and row["selected_label"] != row["gold_label"]
    ]
    wrong_low_conf = [
        row for row in low_conf if row["recommended_label"] != row["gold_label"]
    ]

    return {
        "threshold": threshold,
        "reviewed_count": len(low_conf),
        "changed_count": len(changed),
        "corrected_count": len(corrected),
        "regressed_count": len(regressed),
        "wrong_low_conf_count": len(wrong_low_conf),
        "wrong_low_conf_gold_in_top3_count": sum(
            _top3_hit(row) for row in wrong_low_conf
        ),
        "metrics": _metrics(
            y_true,
            y_pred,
            labels=list(range(len(label_map))),
            target_names=[inv_label_map[i] for i in sorted(inv_label_map)],
        ),
        "changed_examples": [
            {
                "major_name": row["major_name"],
                "gold_label": row["gold_label"],
                "recommended_label": row["recommended_label"],
                "selected_label": row["selected_label"],
                "selected_label_name": row.get("selected_label_name"),
                "reason": (row.get("llm_review") or {}).get("reason"),
            }
            for row in changed[:20]
        ],
    }


async def main_async(args: argparse.Namespace) -> dict[str, Any]:
    load_dotenv()
    input_summary = Path(args.input_summary)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    label_map, inv_label_map = _load_label_map(Path(args.label_map))
    summary = json.loads(input_summary.read_text(encoding="utf-8"))
    probe_rows = summary["probe"]["per_sample"]

    llm_client = OpenAIChatClient(timeout=args.request_timeout, max_retries=0)
    reviewed_rows = await review_probe_rows(
        probe_rows,
        threshold=args.threshold,
        llm_client=llm_client,
        model=args.model,
        concurrency=args.concurrency,
    )
    result = _build_summary(
        reviewed_rows=reviewed_rows,
        threshold=args.threshold,
        label_map=label_map,
        inv_label_map=inv_label_map,
    )

    (output_dir / "reviewed_rows.json").write_text(
        json.dumps(reviewed_rows, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (output_dir / "summary.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return result


def main() -> None:
    args = _parse_args()
    result = asyncio.run(main_async(args))
    brief = {
        "threshold": result["threshold"],
        "reviewed_count": result["reviewed_count"],
        "changed_count": result["changed_count"],
        "corrected_count": result["corrected_count"],
        "regressed_count": result["regressed_count"],
        "accuracy": result["metrics"]["accuracy"],
        "macro_f1": result["metrics"]["macro_f1"],
    }
    print(json.dumps(brief, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
