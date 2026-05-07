"""Promote or roll back the default major probe with metric gates."""

from __future__ import annotations

import argparse
import json
import shutil
from datetime import datetime
from pathlib import Path


DEFAULT_FILES = [
    "best_probe.pt",
    "probe.pt",
    "label_map.json",
    "metrics.json",
    "train_history.jsonl",
    "val_classification_report.json",
]


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Promote a major probe experiment to default")
    parser.add_argument("--candidate-dir", required=True)
    parser.add_argument("--default-dir", default="gaokaollm_bench/outputs/major_training_probe")
    parser.add_argument("--archive-dir", default=None)
    parser.add_argument("--min-macro-f1", type=float, default=0.758751771732541)
    parser.add_argument("--min-accuracy", type=float, default=0.7710843373493976)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--rollback-from", default=None)
    return parser.parse_args()


def _metric_gate(candidate_dir: Path, *, min_macro_f1: float, min_accuracy: float) -> dict:
    metrics = json.loads((candidate_dir / "metrics.json").read_text(encoding="utf-8"))
    macro_f1 = float(metrics.get("best_val_macro_f1") or 0.0)
    accuracy = float(metrics.get("best_val_accuracy") or 0.0)
    return {
        "macro_f1": macro_f1,
        "accuracy": accuracy,
        "passes": macro_f1 > min_macro_f1 and accuracy >= min_accuracy,
    }


def _copy_existing_default(default_dir: Path, archive_dir: Path) -> None:
    archive_dir.mkdir(parents=True, exist_ok=True)
    for name in DEFAULT_FILES:
        src = default_dir / name
        if src.exists():
            shutil.copy2(src, archive_dir / name)


def _copy_candidate(candidate_dir: Path, default_dir: Path) -> None:
    default_dir.mkdir(parents=True, exist_ok=True)
    for name in DEFAULT_FILES:
        src = candidate_dir / name
        dst = default_dir / name
        if src.exists():
            shutil.copy2(src, dst)
        elif dst.exists():
            dst.unlink()


def main() -> None:
    args = _parse_args()
    default_dir = Path(args.default_dir)
    if args.rollback_from:
        _copy_candidate(Path(args.rollback_from), default_dir)
        print(f"Rolled back default probe from {args.rollback_from}")
        return

    candidate_dir = Path(args.candidate_dir)
    gate = _metric_gate(candidate_dir, min_macro_f1=args.min_macro_f1, min_accuracy=args.min_accuracy)
    if args.dry_run:
        print(
            json.dumps(
                {
                    "candidate_dir": str(candidate_dir),
                    "macro_f1": gate["macro_f1"],
                    "accuracy": gate["accuracy"],
                    "passes": gate["passes"],
                    "required_macro_f1_gt": args.min_macro_f1,
                    "required_accuracy_gte": args.min_accuracy,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return
    if not gate["passes"] and not args.force:
        raise SystemExit(
            "Candidate did not pass promotion gate: "
            f"macro_f1={gate['macro_f1']:.4f} accuracy={gate['accuracy']:.4f}; "
            f"required macro_f1>{args.min_macro_f1:.4f} and accuracy>={args.min_accuracy:.4f}"
        )

    archive_dir = (
        Path(args.archive_dir)
        if args.archive_dir
        else default_dir / "archive" / datetime.now().strftime("%Y%m%d_%H%M%S")
    )
    _copy_existing_default(default_dir, archive_dir)
    _copy_candidate(candidate_dir, default_dir)
    record = {
        "candidate_dir": str(candidate_dir),
        "archive_dir": str(archive_dir),
        "macro_f1": gate["macro_f1"],
        "accuracy": gate["accuracy"],
        "forced": bool(args.force),
    }
    (default_dir / "promotion_record.json").write_text(
        json.dumps(record, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps(record, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
