"""Build the full-coverage v2 major tree and audit report.

This script is intentionally paper-facing and deterministic after the LLM review
file has been produced. It does not call the database or an external LLM.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from copy import deepcopy
from pathlib import Path
from typing import Any

from gaokaollm_bench.data_gen.major_tree import load_major_tree
from gaokaollm_bench.data_gen.major_tree_finalize_from_reviews import finalize_tree


DEFAULT_BASE_TREE = (
    "gaokaollm_bench/outputs/major_tree_observed_full_unassigned_all_v2.json"
)
DEFAULT_REVIEWS = (
    "gaokaollm_bench/outputs/"
    "major_probe_review_candidates_full_v2_deepseek_r1_reviewed.json"
)
DEFAULT_OUTPUT = "gaokaollm_bench/outputs/major_tree_final_full_coverage_v2.json"
DEFAULT_AUDIT = "gaokaollm_bench/outputs/major_tree_final_full_coverage_v2_audit.json"
DEFAULT_REPORT_JSON = "gaokaollm_bench/outputs/major_tree_full_coverage_v2_report.json"
DEFAULT_REPORT_MD = "gaokaollm_bench/outputs/major_tree_full_coverage_v2_report.md"


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create full-coverage v2 major tree artifacts from reviewed rows."
    )
    parser.add_argument("--base-tree", default=DEFAULT_BASE_TREE)
    parser.add_argument("--reviews", default=DEFAULT_REVIEWS)
    parser.add_argument("--output", default=DEFAULT_OUTPUT)
    parser.add_argument("--audit-output", default=DEFAULT_AUDIT)
    parser.add_argument("--report-json", default=DEFAULT_REPORT_JSON)
    parser.add_argument("--report-md", default=DEFAULT_REPORT_MD)
    return parser.parse_args()


def _load_json(path: str | Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _write_json(path: str | Path, payload: Any) -> None:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def _candidate_labels(row: dict[str, Any]) -> set[str]:
    return {
        str(pred.get("label"))
        for pred in row.get("probe_predictions") or []
        if pred.get("label")
    }


def _normalize_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for row in rows:
        item = deepcopy(row)
        review_status = str(item.get("review_status") or "")
        llm_review = item.get("llm_review") or {}
        invalid_label = llm_review.get("invalid_selected_label")
        selected_label = llm_review.get("selected_label")
        recommended_label = item.get("recommended_label")
        top1_label = None
        predictions = item.get("probe_predictions") or []
        if predictions:
            top1_label = predictions[0].get("label")

        if review_status == "pending":
            item["coverage_assignment_source"] = "probe_auto_assigned"
            item["needs_manual_review"] = False
        elif review_status == "llm_reviewed":
            item["coverage_assignment_source"] = "deepseek_r1_reviewed"
            item["needs_manual_review"] = False
        elif invalid_label:
            item["coverage_assignment_source"] = "llm_invalid_probe_fallback"
            item["needs_manual_review"] = True
            item["review_status"] = "llm_invalid_probe_fallback"
        elif not selected_label and recommended_label:
            item["coverage_assignment_source"] = "llm_abstain_probe_fallback"
            item["needs_manual_review"] = True
            item["review_status"] = "llm_abstain_probe_fallback"
        elif recommended_label not in _candidate_labels(item) and top1_label:
            item["recommended_label"] = top1_label
            item["coverage_assignment_source"] = "unknown_label_probe_fallback"
            item["needs_manual_review"] = True
            item["review_status"] = "unknown_label_probe_fallback"
        else:
            item["coverage_assignment_source"] = "probe_fallback"
            item["needs_manual_review"] = True
            item["review_status"] = "probe_fallback"

        normalized.append(item)
    return normalized


def _leaf_observed_name_count(tree: dict[str, Any]) -> int:
    nodes = tree.get("nodes") or {}
    names: set[str] = set()
    for node in nodes.values():
        if node.get("children"):
            continue
        names.update(str(name) for name in node.get("observed_names") or [] if name)
    return len(names)


def _review_stats(rows: list[dict[str, Any]]) -> dict[str, Any]:
    source_counts = Counter(str(row.get("coverage_assignment_source")) for row in rows)
    status_counts = Counter(str(row.get("review_status")) for row in rows)
    low_confidence_total = sum(1 for row in rows if row.get("llm_review"))
    llm_changed = sum(
        1 for row in rows if (row.get("llm_review") or {}).get("changed") is True
    )
    needs_manual_review = sum(1 for row in rows if row.get("needs_manual_review"))
    invalid = sum(
        1 for row in rows if (row.get("llm_review") or {}).get("invalid_selected_label")
    )
    abstain = sum(
        1
        for row in rows
        if row.get("coverage_assignment_source") == "llm_abstain_probe_fallback"
    )
    return {
        "total_review_candidates": len(rows),
        "source_counts": dict(sorted(source_counts.items())),
        "status_counts": dict(sorted(status_counts.items())),
        "low_confidence_llm_reviewed_or_abstained": low_confidence_total,
        "deepseek_r1_changed_recommendation": llm_changed,
        "llm_invalid_probe_fallback": invalid,
        "llm_abstain_probe_fallback": abstain,
        "needs_manual_review": needs_manual_review,
    }


def _enrich_audit(
    audit_rows: list[dict[str, Any]], normalized_rows: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    by_name = {str(row.get("major_name")): row for row in normalized_rows}
    enriched: list[dict[str, Any]] = []
    for audit in audit_rows:
        row = by_name.get(str(audit.get("major_name"))) or {}
        merged = dict(audit)
        merged["coverage_assignment_source"] = row.get("coverage_assignment_source")
        merged["needs_manual_review"] = bool(row.get("needs_manual_review"))
        merged["llm_review"] = row.get("llm_review")
        merged["probe_top1_label"] = (
            (row.get("probe_predictions") or [{}])[0].get("label")
            if row.get("probe_predictions")
            else None
        )
        merged["probe_top1_probability"] = (
            (row.get("probe_predictions") or [{}])[0].get("probability")
            if row.get("probe_predictions")
            else None
        )
        enriched.append(merged)
    return enriched


def _write_report_md(path: str | Path, report: dict[str, Any]) -> None:
    build = report["observed_build"]
    review = report["review_stats"]
    final = report["final_coverage"]
    lines = [
        "# 专业树全量覆盖 v2 报告",
        "",
        "本报告定义的“全覆盖”是可审计挂载覆盖：每个原始去重专业名都进入专业层级本体的某个叶子簇，并保留 probe、DeepSeek-R1 复核或 fallback 来源；它不等价于全部语义已经人工确认正确。",
        "",
        "## 覆盖结果",
        "",
        "| 指标 | 数值 |",
        "| --- | ---: |",
        f"| 原始去重专业名 | {build['total_distinct_names']:,} |",
        f"| 原始录取记录 | {build['total_rows']:,} |",
        f"| 规则阶段已挂载专业名 | {build['assigned_distinct_names']:,} |",
        f"| 规则阶段未挂载专业名 | {build['unassigned_distinct_names']:,} |",
        f"| v2 最终已挂载专业名 | {final['assigned_distinct_names']:,} / {build['total_distinct_names']:,} |",
        f"| v2 最终已挂载记录 | {final['assigned_row_count']:,} / {build['total_rows']:,} |",
        f"| v2 剩余未挂载专业名 | {final['remaining_unassigned_distinct_names']:,} |",
        f"| v2 剩余未挂载记录 | {final['remaining_unassigned_row_count']:,} |",
        f"| 叶子 observed names 去重条目 | {final['leaf_observed_name_count']:,} |",
        "",
        "## 全量候选与复核来源",
        "",
        "| 来源 | 数量 |",
        "| --- | ---: |",
    ]
    for source, count in review["source_counts"].items():
        lines.append(f"| {source} | {count:,} |")
    lines.extend(
        [
            "",
            "## DeepSeek-R1 低置信复核诊断",
            "",
            "| 指标 | 数值 |",
            "| --- | ---: |",
            f"| 低置信复核/弃权样本 | {review['low_confidence_llm_reviewed_or_abstained']:,} |",
            f"| DeepSeek-R1 改变 probe 建议 | {review['deepseek_r1_changed_recommendation']:,} |",
            f"| LLM 候选外无效输出 fallback | {review['llm_invalid_probe_fallback']:,} |",
            f"| LLM 弃权后 probe fallback | {review['llm_abstain_probe_fallback']:,} |",
            f"| 需后续人工抽检样本 | {review['needs_manual_review']:,} |",
            "",
        ]
    )
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    args = _parse_args()
    base_tree = load_major_tree(args.base_tree)
    rows = _normalize_rows(_load_json(args.reviews))
    statuses = {str(row.get("review_status")) for row in rows}
    final_tree, audit_rows, summary = finalize_tree(
        base_tree=base_tree,
        review_rows=rows,
        statuses=statuses,
    )
    enriched_audit = _enrich_audit(audit_rows, rows)
    build = final_tree.get("observed_build") or {}
    final_coverage = {
        "assigned_distinct_names": int(build.get("assigned_distinct_names") or 0),
        "assigned_row_count": int(build.get("assigned_row_count") or 0),
        "remaining_unassigned_distinct_names": int(
            build.get("unassigned_distinct_names") or 0
        ),
        "remaining_unassigned_row_count": int(build.get("unassigned_row_count") or 0),
        "leaf_observed_name_count": _leaf_observed_name_count(final_tree),
        "finalized_from_candidates": summary,
    }
    report = {
        "definition": (
            "Full coverage means auditable assignment coverage, not full manual "
            "semantic verification."
        ),
        "input_files": {
            "base_tree": args.base_tree,
            "reviews": args.reviews,
        },
        "observed_build": base_tree.get("observed_build") or {},
        "review_stats": _review_stats(rows),
        "final_coverage": final_coverage,
    }
    if final_coverage["remaining_unassigned_distinct_names"] != 0:
        raise RuntimeError(
            "Full coverage failed: "
            f"{final_coverage['remaining_unassigned_distinct_names']} names remain."
        )

    _write_json(args.output, final_tree)
    _write_json(args.audit_output, enriched_audit)
    _write_json(args.report_json, report)
    _write_report_md(args.report_md, report)

    print(json.dumps(report["final_coverage"], ensure_ascii=False, indent=2))
    print(f"Wrote full-coverage tree to {args.output}")
    print(f"Wrote full-coverage audit to {args.audit_output}")
    print(f"Wrote report to {args.report_json} and {args.report_md}")


if __name__ == "__main__":
    main()
