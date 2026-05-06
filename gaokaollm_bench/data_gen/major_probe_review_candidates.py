"""Generate review candidates for unassigned majors using a trained probe."""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path
from typing import Any

from gaokaollm_bench.data_gen.major_probe_predict import predict_major_labels


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Classify unassigned major names with a probe and save pending review candidates."
    )
    parser.add_argument(
        "--unassigned",
        default=str(Path("gaokaollm_bench/sample_data/major_tree_unassigned_full.json")),
        help="Unassigned-major JSON file from the major tree builder.",
    )
    parser.add_argument(
        "--output",
        default=str(Path("gaokaollm_bench/outputs/major_probe_review_candidates.json")),
        help="Output JSON file containing pending review candidates.",
    )
    parser.add_argument(
        "--probe",
        default=str(Path("gaokaollm_bench/outputs/major_training_probe/best_probe.pt")),
    )
    parser.add_argument(
        "--label-map",
        default=str(Path("gaokaollm_bench/outputs/major_training_probe/label_map.json")),
    )
    parser.add_argument(
        "--major-tree",
        default=str(Path("gaokaollm_bench/data_gen/major_clusters.json")),
    )
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--batch-size", type=int, default=128)
    parser.add_argument(
        "--min-confidence",
        type=float,
        default=0.0,
        help="Mark candidates below this top-1 probability as low_confidence.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Optional maximum number of unassigned majors to classify.",
    )
    return parser.parse_args()


def _load_unassigned(path: Path) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, list):
        rows = data
    elif isinstance(data, dict):
        rows = data.get("unassigned_top") or data.get("unassigned") or []
    else:
        raise ValueError("Unsupported unassigned JSON format")

    normalized_rows: list[dict[str, Any]] = []
    for row in rows:
        if isinstance(row, str):
            normalized_rows.append({"major_name": row, "row_count": None, "suggestions": []})
        elif isinstance(row, dict):
            name = row.get("major_name") or row.get("name")
            if name:
                normalized_rows.append({**row, "major_name": str(name)})
    return normalized_rows


async def _main_async(args: argparse.Namespace) -> list[dict[str, Any]]:
    rows = _load_unassigned(Path(args.unassigned))
    if args.limit is not None:
        if args.limit < 1:
            raise ValueError("--limit must be at least 1")
        rows = rows[: args.limit]

    predictions = await predict_major_labels(
        [str(row["major_name"]) for row in rows],
        probe_path=args.probe,
        label_map_path=args.label_map,
        major_tree_path=args.major_tree,
        top_k=args.top_k,
        batch_size=args.batch_size,
    )

    candidates: list[dict[str, Any]] = []
    for row, pred in zip(rows, predictions):
        probe_predictions = pred["predictions"]
        top_prediction = probe_predictions[0] if probe_predictions else None
        top_probability = float(top_prediction["probability"]) if top_prediction else 0.0
        confidence_flag = (
            "low_confidence" if top_probability < args.min_confidence else "pending"
        )
        candidates.append(
            {
                "major_name": row["major_name"],
                "normalized_text": pred["normalized_text"],
                "row_count": row.get("row_count"),
                "rule_suggestions": row.get("suggestions", []),
                "recommended_label": top_prediction["label"] if top_prediction else None,
                "recommended_label_name": top_prediction["label_name"] if top_prediction else None,
                "recommended_probability": top_probability,
                "probe_predictions": probe_predictions,
                "review_status": confidence_flag,
                "review_decision": None,
                "review_notes": "",
            }
        )
    return candidates


def main() -> None:
    args = _parse_args()
    candidates = asyncio.run(_main_async(args))
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(candidates, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    low_confidence = sum(1 for row in candidates if row["review_status"] == "low_confidence")
    print(f"Wrote {len(candidates)} review candidates to {output_path}")
    print(f"low_confidence={low_confidence}")
    for row in candidates[:10]:
        print(
            f"{row['major_name']} -> {row['recommended_label']} "
            f"p={row['recommended_probability']:.4f} status={row['review_status']}"
        )


if __name__ == "__main__":
    main()
