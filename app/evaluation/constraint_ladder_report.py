"""Summarize constraint-ladder benchmark results by constraint count."""

from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path
from typing import Any


DEFAULT_PERSONAS = Path(
    "gaokaollm_bench/sample_data/iceberg_personas_constraint_ladder_real_db_9.json"
)
DEFAULT_OUTPUT_ROOT = Path(
    "gaokaollm_bench/outputs/method_score_arena_constraint_ladder"
)
DEFAULT_CSV = Path("app/evaluation/results/constraint_ladder_summary.csv")
DEFAULT_MD = Path("app/evaluation/results/constraint_ladder_summary.md")


def _load_persona_meta(path: Path) -> dict[str, dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, dict):
        data = data.get("items", [])
    meta = {}
    for item in data:
        background = item.get("background") or {}
        meta[str(item["case_id"])] = {
            "constraint_count": int(background.get("constraint_count") or 0),
            "diagnostic_level": str(background.get("diagnostic_level") or ""),
            "relax_axis": str(background.get("relax_axis") or ""),
            "benefit_axis": str(background.get("benefit_axis") or ""),
        }
    return meta


def _float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def build_rows(personas: Path, output_root: Path) -> list[dict[str, Any]]:
    meta = _load_persona_meta(personas)
    grouped: dict[tuple[str, str, int], list[dict[str, Any]]] = defaultdict(list)
    for summary_path in sorted(output_root.glob("*/summary.json")):
        model = summary_path.parent.name
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        for row in summary.get("rows") or []:
            case_meta = meta.get(str(row.get("case_id")))
            if not case_meta:
                continue
            grouped[
                (
                    model,
                    str(row.get("target") or ""),
                    int(case_meta["constraint_count"]),
                )
            ].append({**row, **case_meta})

    rows = []
    for (model, target, constraint_count), items in sorted(grouped.items()):
        ok_items = [item for item in items if item.get("status") == "ok"]
        rows.append(
            {
                "model": model,
                "target": target,
                "constraint_count": constraint_count,
                "cases": len(items),
                "completed_cases": len(ok_items),
                "failed_cases": len(items) - len(ok_items),
                "elicitation_success_rate": _mean(
                    1.0 if item.get("elicitation_success") else 0.0 for item in ok_items
                ),
                "mean_pareto_gain": _mean(
                    _float(item.get("pareto_gain")) for item in ok_items
                ),
                "mean_hallucination_rate": _mean(
                    _float(item.get("hallucination_rate")) for item in ok_items
                ),
                "avg_turns": _mean(_float(item.get("turns")) for item in ok_items),
            }
        )
    return rows


def _mean(values: Any) -> float:
    collected = list(values)
    return sum(collected) / len(collected) if collected else 0.0


def write_csv(rows: list[dict[str, Any]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        fieldnames = [
            "model",
            "target",
            "constraint_count",
            "cases",
            "completed_cases",
            "failed_cases",
            "elicitation_success_rate",
            "mean_pareto_gain",
            "mean_hallucination_rate",
            "avg_turns",
        ]
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_markdown(rows: list[dict[str, Any]], path: Path) -> None:
    lines = [
        "# Constraint Ladder Summary",
        "",
        "Grouped by model, target, and explicit constraint count.",
        "",
        "| Model | Target | Constraints | Cases | Completed | Failed | Success | Gain | Hallucination | Turns |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in rows:
        lines.append(
            f"| {row['model']} | {row['target']} | {row['constraint_count']} | "
            f"{row['cases']} | {row['completed_cases']} | {row['failed_cases']} | "
            f"{row['elicitation_success_rate']:.3f} | {row['mean_pareto_gain']:.3f} | "
            f"{row['mean_hallucination_rate']:.3f} | {row['avg_turns']:.2f} |"
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--personas", default=str(DEFAULT_PERSONAS))
    parser.add_argument("--output-root", default=str(DEFAULT_OUTPUT_ROOT))
    parser.add_argument("--csv", default=str(DEFAULT_CSV))
    parser.add_argument("--markdown", default=str(DEFAULT_MD))
    args = parser.parse_args()

    rows = build_rows(Path(args.personas), Path(args.output_root))
    write_csv(rows, Path(args.csv))
    write_markdown(rows, Path(args.markdown))
    print(f"Wrote {len(rows)} grouped rows to {args.csv}")
    print(f"Wrote markdown summary to {args.markdown}")


if __name__ == "__main__":
    main()
