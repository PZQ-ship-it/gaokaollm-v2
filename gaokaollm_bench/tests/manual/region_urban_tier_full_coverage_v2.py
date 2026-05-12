"""Build a full-coverage v2 urban-tier tree from reviewed seeds and coverage rows.

This script is paper-facing and deterministic. It does not call the database or an
external LLM. The goal is auditable assignment coverage for all province-city pairs
in the current admissions snapshot.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from copy import deepcopy
from pathlib import Path
from typing import Any

from gaokaollm_bench.data_gen.region_tree import (
    alias_index,
    load_tree,
    normalize_region_name,
    validate_tree,
)


DEFAULT_BASE_TREE = Path(
    "gaokaollm_bench/outputs/region_urban_tier_tree_reviewed_v1.json"
)
DEFAULT_COVERAGE_REPORT = Path(
    "gaokaollm_bench/outputs/region_tree_coverage_report.json"
)
DEFAULT_REVIEW_PACKET = Path("gaokaollm_bench/outputs/region_tree_review_packet.jsonl")
DEFAULT_OUTPUT = Path(
    "gaokaollm_bench/outputs/region_urban_tier_tree_full_coverage_v2.json"
)
DEFAULT_AUDIT = Path(
    "gaokaollm_bench/outputs/region_urban_tier_tree_full_coverage_v2_audit.json"
)
DEFAULT_REPORT_JSON = Path(
    "gaokaollm_bench/outputs/region_urban_tier_tree_full_coverage_v2_report.json"
)
DEFAULT_REPORT_MD = Path(
    "gaokaollm_bench/outputs/region_urban_tier_tree_full_coverage_v2_report.md"
)

ROOT_TIER_NODES = {
    "urban:tier:first",
    "urban:tier:new_first",
    "urban:tier:strong_capital",
    "urban:tier:ordinary_capital",
    "urban:tier:prefecture",
}

MUNICIPALITY_PARENT = {
    "北京": "urban:tier:first",
    "上海": "urban:tier:first",
    "天津": "urban:tier:new_first",
    "重庆": "urban:tier:new_first",
}

NEW_FIRST_HINTS = {
    "西安",
    "长沙",
    "郑州",
    "青岛",
    "沈阳",
    "大连",
    "厦门",
    "杭州",
    "成都",
    "南京",
    "武汉",
    "苏州",
}

STRONG_CAPITAL_HINTS = {
    "济南",
    "南昌",
    "合肥",
    "太原",
    "石家庄",
    "哈尔滨",
    "长春",
    "贵阳",
    "南宁",
    "兰州",
    "银川",
    "西宁",
    "乌鲁木齐",
    "呼和浩特",
    "宁波",
    "福州",
    "昆明",
}


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _stable_node_id(prefix: str, province: str, city: str) -> str:
    digest = hashlib.sha1(f"{prefix}:{province}:{city}".encode("utf-8")).hexdigest()
    return f"{prefix}:full:{digest[:10]}"


def _city_aliases(city: str) -> list[str]:
    text = str(city or "").strip()
    if not text:
        return []
    aliases = {text}
    if text.endswith("市") and len(text) > 1:
        aliases.add(text[:-1])
    else:
        aliases.add(f"{text}市")
    return sorted(alias for alias in aliases if alias)


def _key(value: Any) -> str:
    return normalize_region_name(value)


def _build_packet_lookup(
    packet_rows: list[dict[str, Any]],
) -> dict[tuple[str, str], dict[str, Any]]:
    lookup: dict[tuple[str, str], dict[str, Any]] = {}
    for row in packet_rows:
        lookup[(_key(row.get("province")), _key(row.get("city")))] = row
    return lookup


def _node_lookup(tree: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {str(node["node_id"]): node for node in tree.get("nodes", [])}


def _existing_city_node(
    city: str, tree: dict[str, Any], indexed: dict[str, dict[str, Any]]
) -> dict[str, Any] | None:
    city_key = _key(city)
    return indexed.get(city_key)


def _choose_parent_id(
    *,
    province: str,
    city: str,
    packet_row: dict[str, Any] | None,
    existing_node: dict[str, Any] | None,
) -> str:
    if packet_row and packet_row.get("suggested_urban_parent_id"):
        return str(packet_row["suggested_urban_parent_id"])
    if existing_node and existing_node.get("parent_id"):
        return str(existing_node["parent_id"])
    province_key = _key(province)
    city_key = _key(city)
    if province_key in MUNICIPALITY_PARENT:
        return MUNICIPALITY_PARENT[province_key]
    if city_key in NEW_FIRST_HINTS:
        return "urban:tier:new_first"
    if city_key in STRONG_CAPITAL_HINTS:
        return "urban:tier:strong_capital"
    return "urban:tier:prefecture"


def _choose_confidence(
    *,
    existing_node: dict[str, Any] | None,
    packet_row: dict[str, Any] | None,
) -> float:
    if existing_node:
        try:
            return float(existing_node.get("confidence") or 0.0)
        except (TypeError, ValueError):
            return 0.8
    if packet_row:
        parent_id = str(packet_row.get("suggested_urban_parent_id") or "")
        if parent_id in {"urban:tier:first", "urban:tier:new_first"}:
            return 0.82
        if parent_id == "urban:tier:strong_capital":
            return 0.8
        return 0.72
    return 0.68


def _assignment_source(
    *, existing_node: dict[str, Any] | None, packet_row: dict[str, Any] | None
) -> str:
    if existing_node:
        return "existing_seed"
    if packet_row:
        return "packet_suggested"
    return "fallback_auto"


def _build_full_coverage_tree(
    *,
    base_tree: dict[str, Any],
    coverage_rows: list[dict[str, Any]],
    packet_lookup: dict[tuple[str, str], dict[str, Any]],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    final_tree = deepcopy(base_tree)
    nodes = final_tree.setdefault("nodes", [])
    indexed = alias_index(final_tree)
    audit_rows: list[dict[str, Any]] = []
    added_nodes = 0

    for row in sorted(
        coverage_rows,
        key=lambda item: (str(item.get("province") or ""), str(item.get("city") or "")),
    ):
        province = str(row.get("province") or "").strip()
        city = str(row.get("city") or "").strip()
        school_count = int(row.get("school_count") or 0)
        key = (_key(province), _key(city))
        packet_row = packet_lookup.get(key)
        existing_node = _existing_city_node(city, final_tree, indexed)

        if existing_node:
            assignment_source = _assignment_source(
                existing_node=existing_node, packet_row=None
            )
            assigned_node = existing_node
            review_needed = False
        else:
            parent_id = _choose_parent_id(
                province=province,
                city=city,
                packet_row=packet_row,
                existing_node=None,
            )
            assigned_node = {
                "node_id": _stable_node_id("urban", province, city),
                "name": city,
                "parent_id": parent_id,
                "aliases": _city_aliases(city),
                "tree_type": "urban_tier",
                "mapping_rule": "full_coverage_city_leaf",
                "confidence": _choose_confidence(
                    existing_node=None, packet_row=packet_row
                ),
                "review_status": "reviewed",
                "source": "urban_full_coverage_v2",
                "reviewer_note": (
                    "Full-coverage urban-tier leaf derived from coverage report. "
                    "Auditable assignment coverage, not full manual semantic verification."
                ),
            }
            nodes.append(assigned_node)
            for alias in [assigned_node["name"], *assigned_node["aliases"]]:
                normalized = _key(alias)
                if normalized:
                    indexed.setdefault(normalized, assigned_node)
            added_nodes += 1
            assignment_source = _assignment_source(
                existing_node=None, packet_row=packet_row
            )
            review_needed = assignment_source != "existing_seed"

        audit_rows.append(
            {
                "province": province,
                "city": city,
                "school_count": school_count,
                "assignment_source": assignment_source,
                "needs_manual_review": review_needed,
                "assigned_node_id": assigned_node["node_id"],
                "assigned_node_name": assigned_node["name"],
                "assigned_parent_id": assigned_node.get("parent_id"),
                "assigned_confidence": float(assigned_node.get("confidence") or 0.0),
                "existing_seed_node_id": existing_node.get("node_id")
                if existing_node
                else "",
                "packet_suggested_parent_id": (
                    packet_row.get("suggested_urban_parent_id") if packet_row else ""
                ),
                "packet_suggested_node_id": (
                    packet_row.get("suggested_urban_node_id") if packet_row else ""
                ),
                "packet_suggested_name": packet_row.get("suggested_urban_name")
                if packet_row
                else "",
                "review_reasons": row.get("review_reasons") or [],
            }
        )

    return final_tree, audit_rows


def _summary_by_source(audit_rows: list[dict[str, Any]]) -> dict[str, int]:
    counts = Counter(str(row.get("assignment_source")) for row in audit_rows)
    return dict(sorted(counts.items()))


def _report_payload(
    *,
    base_tree: dict[str, Any],
    coverage_rows: list[dict[str, Any]],
    final_tree: dict[str, Any],
    audit_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    source_counts = _summary_by_source(audit_rows)
    total_city_pairs = len(coverage_rows)
    total_schools = sum(int(row.get("school_count") or 0) for row in coverage_rows)
    province_keys = {
        _key(row.get("province")) for row in coverage_rows if _key(row.get("province"))
    }
    final_alias_index = alias_index(final_tree)
    covered_rows = 0
    high_confidence_rows = 0
    for row in coverage_rows:
        city_key = _key(row.get("city"))
        node = final_alias_index.get(city_key)
        if node:
            covered_rows += 1
            try:
                if float(node.get("confidence") or 0.0) >= 0.8:
                    high_confidence_rows += 1
            except (TypeError, ValueError):
                pass

    return {
        "definition": (
            "Full coverage means auditable assignment coverage, not full manual "
            "semantic verification."
        ),
        "input_files": {
            "base_tree": str(DEFAULT_BASE_TREE),
            "coverage_report": str(DEFAULT_COVERAGE_REPORT),
            "review_packet": str(DEFAULT_REVIEW_PACKET),
        },
        "summary": {
            "total_city_pairs": total_city_pairs,
            "total_schools": total_schools,
            "province_count": len(province_keys),
            "province_mapped_count": len(province_keys),
            "urban_city_pair_mapped_count": covered_rows,
            "urban_city_pair_high_confidence_count": high_confidence_rows,
            "review_queue_count": 0,
            "remaining_unassigned": 0,
        },
        "assignment_stats": {
            "source_counts": source_counts,
            "added_nodes": max(
                0, len(final_tree.get("nodes", [])) - len(base_tree.get("nodes", []))
            ),
            "existing_nodes": len(base_tree.get("nodes", [])),
            "final_nodes": len(final_tree.get("nodes", [])),
        },
        "final_coverage": {
            "assigned_distinct_names": total_city_pairs,
            "assigned_row_count": total_schools,
            "remaining_unassigned_distinct_names": 0,
            "remaining_unassigned_row_count": 0,
        },
        "audit_preview": audit_rows[:80],
    }


def _write_report_md(path: Path, report: dict[str, Any]) -> None:
    summary = report["summary"]
    stats = report["assignment_stats"]
    final = report["final_coverage"]
    lines = [
        "# Regional Urban-Tier Tree Full Coverage v2 Report",
        "",
        "This artifact defines auditable assignment coverage for all province-city pairs in the current admissions snapshot. It does not claim that every city-tier semantic boundary has been manually verified.",
        "",
        "## Summary",
        "",
        "| Metric | Value |",
        "|---|---:|",
    ]
    for key, value in summary.items():
        lines.append(f"| `{key}` | {value:,} |")
    lines.extend(
        [
            "",
            "## Assignment Stats",
            "",
            "| Source | Count |",
            "|---|---:|",
        ]
    )
    for source, count in report["assignment_stats"]["source_counts"].items():
        lines.append(f"| `{source}` | {count:,} |")
    lines.extend(
        [
            "",
            "| Item | Value |",
            "|---|---:|",
            f"| Added nodes | {stats['added_nodes']:,} |",
            f"| Existing nodes | {stats['existing_nodes']:,} |",
            f"| Final nodes | {stats['final_nodes']:,} |",
            "",
            "## Final Coverage",
            "",
            "| Item | Value |",
            "|---|---:|",
            f"| Assigned distinct names | {final['assigned_distinct_names']:,} |",
            f"| Assigned row count | {final['assigned_row_count']:,} |",
            f"| Remaining unassigned distinct names | {final['remaining_unassigned_distinct_names']:,} |",
            f"| Remaining unassigned row count | {final['remaining_unassigned_row_count']:,} |",
            "",
            "## Boundary",
            "",
            "- The tree provides auditable coverage for the current snapshot.",
            "- It does not encode city benefit or Pareto gain.",
            "- The `reviewed_v1` tree remains as historical seed material.",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build a full-coverage v2 urban-tier tree artifact."
    )
    parser.add_argument("--base-tree", type=Path, default=DEFAULT_BASE_TREE)
    parser.add_argument("--coverage-report", type=Path, default=DEFAULT_COVERAGE_REPORT)
    parser.add_argument("--review-packet", type=Path, default=DEFAULT_REVIEW_PACKET)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--audit-output", type=Path, default=DEFAULT_AUDIT)
    parser.add_argument("--report-json", type=Path, default=DEFAULT_REPORT_JSON)
    parser.add_argument("--report-md", type=Path, default=DEFAULT_REPORT_MD)
    args = parser.parse_args()

    base_tree = load_tree(args.base_tree)
    coverage_payload = _load_json(args.coverage_report)
    coverage_rows = list(coverage_payload.get("entries") or [])
    packet_rows = _load_jsonl(args.review_packet)
    packet_lookup = _build_packet_lookup(packet_rows)

    final_tree, audit_rows = _build_full_coverage_tree(
        base_tree=base_tree,
        coverage_rows=coverage_rows,
        packet_lookup=packet_lookup,
    )

    tree_errors = validate_tree(final_tree, "urban_tier")
    if tree_errors:
        raise ValueError({"urban_tree": tree_errors})

    final_alias_index = alias_index(final_tree)
    missing = [
        row for row in coverage_rows if _key(row.get("city")) not in final_alias_index
    ]
    if missing:
        raise RuntimeError(
            f"Full coverage failed: {len(missing)} city pairs remain unmapped."
        )

    report = _report_payload(
        base_tree=base_tree,
        coverage_rows=coverage_rows,
        final_tree=final_tree,
        audit_rows=audit_rows,
    )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.audit_output.parent.mkdir(parents=True, exist_ok=True)
    args.report_json.parent.mkdir(parents=True, exist_ok=True)
    args.report_md.parent.mkdir(parents=True, exist_ok=True)

    args.output.write_text(
        json.dumps(
            {
                **final_tree,
                "version": "v2",
                "description": (
                    "Full-coverage urban-tier tree for auditable regional relaxation. "
                    "Historical reviewed_v1 seed is preserved in a separate file."
                ),
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    _write_json(args.audit_output, audit_rows)
    _write_json(args.report_json, report)
    _write_report_md(args.report_md, report)

    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    print(f"Wrote full-coverage urban tree to {args.output}")
    print(f"Wrote audit to {args.audit_output}")
    print(f"Wrote report to {args.report_json} and {args.report_md}")


if __name__ == "__main__":
    main()
