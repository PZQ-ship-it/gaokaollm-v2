"""Summarize direct LLM classification outputs for extraction failures."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Analyze direct LLM output JSON")
    parser.add_argument("--input", required=True)
    parser.add_argument(
        "--label-map",
        default="gaokaollm_bench/outputs/major_training_probe/label_map.json",
        help="Optional label_map.json used to infer label_valid for legacy outputs.",
    )
    parser.add_argument("--output", default=None)
    return parser.parse_args()


def _is_placeholder_major(value: Any) -> bool:
    if value is None:
        return False
    text = str(value or "").strip()
    return (
        not text
        or text in {":", "：", "-", "null", "None"}
        or all(ch in ":：-_/\\|,.，。;； " for ch in text)
    )


def _load_label_ids(path: str | None) -> set[str]:
    if not path:
        return set()
    label_map_path = Path(path)
    if not label_map_path.exists():
        return set()
    data = json.loads(label_map_path.read_text(encoding="utf-8"))
    return set(data) if isinstance(data, dict) else set()


def _row_label_valid(row: dict[str, Any], label_ids: set[str]) -> bool:
    if "label_valid" in row:
        return bool(row.get("label_valid"))
    selected_label = row.get("selected_label")
    return isinstance(selected_label, str) and selected_label in label_ids


def analyze_outputs(
    rows: list[dict[str, Any]], label_ids: set[str] | None = None
) -> dict[str, Any]:
    label_ids = label_ids or set()
    total = len(rows)
    label_valid = 0
    schema_valid = 0
    errors = []
    placeholder_raw_major = []
    repaired_placeholder_major = []
    invalid = []
    null_labels = []

    for idx, row in enumerate(rows):
        repaired = row.get("repaired_json") or {}
        parsed = row.get("parsed_json") or {}
        raw_major = parsed.get("major_name") if isinstance(parsed, dict) else None
        if raw_major is None and not parsed:
            raw_major = row.get("major_name")
        notes = row.get("repair_notes") or repaired.get("repair_notes") or []
        row_label_valid = _row_label_valid(row, label_ids)

        if row.get("schema_valid"):
            schema_valid += 1
        if row_label_valid:
            label_valid += 1
        if row.get("error"):
            errors.append({"index": idx, "error": row.get("error")})
        if _is_placeholder_major(raw_major):
            placeholder_raw_major.append(
                {
                    "index": idx,
                    "raw_major_name": raw_major,
                    "repaired_major_name": row.get("major_name"),
                    "selected_label": row.get("selected_label"),
                    "repair_notes": notes,
                }
            )
        if "replaced_invalid_major_name" in notes:
            repaired_placeholder_major.append(idx)
        if not row_label_valid:
            invalid.append(
                {
                    "index": idx,
                    "major_name": row.get("major_name"),
                    "selected_label": row.get("selected_label"),
                    "error": row.get("error"),
                }
            )
        if row.get("selected_label") is None:
            null_labels.append(idx)

    return {
        "total": total,
        "schema_valid_count": schema_valid,
        "label_valid_count": label_valid,
        "coverage": label_valid / total if total else 0.0,
        "error_count": len(errors),
        "null_label_count": len(null_labels),
        "placeholder_raw_major_count": len(placeholder_raw_major),
        "repaired_placeholder_major_count": len(repaired_placeholder_major),
        "placeholder_raw_major_examples": placeholder_raw_major[:10],
        "invalid_examples": invalid[:10],
        "error_examples": errors[:10],
    }


def main() -> None:
    args = _parse_args()
    rows = json.loads(Path(args.input).read_text(encoding="utf-8"))
    summary = analyze_outputs(rows, _load_label_ids(args.label_map))
    text = json.dumps(summary, ensure_ascii=False, indent=2)
    if args.output:
        Path(args.output).write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
