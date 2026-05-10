"""HITL review packet and v1 coverage reports for region-tree artifacts."""

from __future__ import annotations

import argparse
import copy
import csv
import hashlib
import json
from pathlib import Path
from typing import Any

from gaokaollm_bench.data_gen.region_tree import (
    DEFAULT_GEO_TREE_PATH,
    DEFAULT_JSON_REPORT_PATH,
    DEFAULT_URBAN_TREE_PATH,
    build_coverage_report,
    load_tree,
    normalize_region_name,
    validate_tree,
)


DEFAULT_REVIEW_PACKET_CSV_PATH = Path(
    "gaokaollm_bench/outputs/region_tree_review_packet.csv"
)
DEFAULT_REVIEW_PACKET_JSONL_PATH = Path(
    "gaokaollm_bench/outputs/region_tree_review_packet.jsonl"
)
DEFAULT_GEO_TREE_V1_PATH = Path(
    "gaokaollm_bench/outputs/region_geo_tree_reviewed_v1.json"
)
DEFAULT_URBAN_TREE_V1_PATH = Path(
    "gaokaollm_bench/outputs/region_urban_tier_tree_reviewed_v1.json"
)
DEFAULT_V1_JSON_REPORT_PATH = Path(
    "gaokaollm_bench/outputs/region_tree_v1_coverage_report.json"
)
DEFAULT_V1_MD_REPORT_PATH = Path(
    "gaokaollm_bench/outputs/region_tree_v1_coverage_report.md"
)

REVIEW_PACKET_FIELDS = [
    "priority_rank",
    "priority_score",
    "province",
    "city",
    "school_count",
    "current_geo_node_id",
    "current_geo_confidence",
    "current_urban_node_id",
    "current_urban_confidence",
    "review_reasons",
    "suggested_geo_parent_id",
    "suggested_geo_node_id",
    "suggested_geo_name",
    "suggested_urban_parent_id",
    "suggested_urban_node_id",
    "suggested_urban_name",
    "reviewer_geo_action",
    "reviewer_geo_parent_id",
    "reviewer_geo_node_id",
    "reviewer_geo_name",
    "reviewer_urban_action",
    "reviewer_urban_parent_id",
    "reviewer_urban_node_id",
    "reviewer_urban_name",
    "reviewer_confidence",
    "reviewer_note",
]

PROVINCE_GEO_PARENT_HINTS = {
    "内蒙古": "geo:north_china",
    "西藏": "geo:southwest_china",
    "香港": "geo:south_china",
    "澳门": "geo:south_china",
    "台湾": "geo:east_china",
}

SKIP_RULE_SEED_PROVINCES = {"芬兰", "马来西亚", "(unknown)"}

NEW_FIRST_CITY_HINTS = {
    "西安",
    "长沙",
    "郑州",
    "青岛",
    "沈阳",
    "大连",
    "厦门",
}

STRONG_CAPITAL_CITY_HINTS = {
    "济南",
    "福州",
    "哈尔滨",
    "长春",
    "昆明",
    "南昌",
    "贵阳",
    "南宁",
    "石家庄",
    "太原",
    "兰州",
    "乌鲁木齐",
    "呼和浩特",
    "海口",
    "银川",
    "西宁",
}


def _stable_node_id(prefix: str, province: str, city: str) -> str:
    digest = hashlib.sha1(f"{prefix}:{province}:{city}".encode("utf-8")).hexdigest()
    return f"{prefix}:reviewed:{digest[:10]}"


def _tree_node_ids(tree: dict[str, Any]) -> set[str]:
    return {str(node["node_id"]) for node in tree.get("nodes", [])}


def _find_node(tree: dict[str, Any], node_id: str | None) -> dict[str, Any] | None:
    if not node_id:
        return None
    for node in tree.get("nodes", []):
        if node.get("node_id") == node_id:
            return node
    return None


def _append_node_if_missing(tree: dict[str, Any], node: dict[str, Any]) -> None:
    node_ids = _tree_node_ids(tree)
    if node["node_id"] not in node_ids:
        tree.setdefault("nodes", []).append(node)


def priority_score(entry: dict[str, Any]) -> int:
    reasons = set(entry.get("review_reasons", []))
    score = int(entry.get("school_count") or 0)
    if "geo_province_or_city_unmatched" in reasons:
        score += 100_000
    if "urban_tier_unmatched" in reasons:
        score += 10_000
    if "geo_city_not_explicitly_mapped" in reasons:
        score += 1_000
    if "low_confidence_or_missing_mapping" in reasons:
        score += 100
    return score


def _suggest_geo_parent_id(entry: dict[str, Any]) -> str:
    current_geo = entry.get("geo_node_id")
    if current_geo:
        return str(current_geo)
    province = normalize_region_name(entry.get("province"))
    return PROVINCE_GEO_PARENT_HINTS.get(province, "geo:china")


def _suggest_urban_parent_id(entry: dict[str, Any]) -> str:
    current_urban = entry.get("urban_node_id")
    if current_urban:
        return str(current_urban)
    city = normalize_region_name(entry.get("city"))
    if city in NEW_FIRST_CITY_HINTS:
        return "urban:tier:new_first"
    if city in STRONG_CAPITAL_CITY_HINTS:
        return "urban:tier:strong_capital"
    return "urban:tier:prefecture"


def build_review_packet(report: dict[str, Any]) -> list[dict[str, Any]]:
    queue = sorted(
        report.get("review_queue", []),
        key=lambda entry: (-priority_score(entry), entry["province"], entry["city"]),
    )
    packet: list[dict[str, Any]] = []
    for index, entry in enumerate(queue, start=1):
        province = str(entry["province"])
        city = str(entry["city"])
        packet.append(
            {
                "priority_rank": index,
                "priority_score": priority_score(entry),
                "province": province,
                "city": city,
                "school_count": int(entry.get("school_count") or 0),
                "current_geo_node_id": entry.get("geo_node_id") or "",
                "current_geo_confidence": float(entry.get("geo_confidence") or 0.0),
                "current_urban_node_id": entry.get("urban_node_id") or "",
                "current_urban_confidence": float(entry.get("urban_confidence") or 0.0),
                "review_reasons": ";".join(entry.get("review_reasons", [])),
                "suggested_geo_parent_id": _suggest_geo_parent_id(entry),
                "suggested_geo_node_id": _stable_node_id("geo", province, city),
                "suggested_geo_name": city,
                "suggested_urban_parent_id": _suggest_urban_parent_id(entry),
                "suggested_urban_node_id": _stable_node_id("urban", province, city),
                "suggested_urban_name": city,
                "reviewer_geo_action": "",
                "reviewer_geo_parent_id": "",
                "reviewer_geo_node_id": "",
                "reviewer_geo_name": "",
                "reviewer_urban_action": "",
                "reviewer_urban_parent_id": "",
                "reviewer_urban_node_id": "",
                "reviewer_urban_name": "",
                "reviewer_confidence": "",
                "reviewer_note": "",
            }
        )
    return packet


def write_review_packet(
    packet: list[dict[str, Any]],
    csv_output: Path = DEFAULT_REVIEW_PACKET_CSV_PATH,
    jsonl_output: Path = DEFAULT_REVIEW_PACKET_JSONL_PATH,
) -> None:
    csv_output.parent.mkdir(parents=True, exist_ok=True)
    jsonl_output.parent.mkdir(parents=True, exist_ok=True)
    with csv_output.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=REVIEW_PACKET_FIELDS)
        writer.writeheader()
        writer.writerows(packet)
    with jsonl_output.open("w", encoding="utf-8") as handle:
        for row in packet:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def read_review_packet(path: Path) -> list[dict[str, Any]]:
    if path.suffix.lower() == ".jsonl":
        rows = [
            json.loads(line)
            for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
    else:
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            rows = list(csv.DictReader(handle))
    for row in rows:
        for key in (
            "priority_rank",
            "priority_score",
            "school_count",
        ):
            if row.get(key) not in (None, ""):
                row[key] = int(row[key])
        for key in (
            "current_geo_confidence",
            "current_urban_confidence",
        ):
            if row.get(key) not in (None, ""):
                row[key] = float(row[key])
    return rows


def _should_skip_rule_seed(row: dict[str, Any]) -> bool:
    province = normalize_region_name(row.get("province"))
    city = normalize_region_name(row.get("city"))
    return province in SKIP_RULE_SEED_PROVINCES or city in SKIP_RULE_SEED_PROVINCES


def _province_node(
    *,
    province: str,
    parent_id: str,
    source: str,
    reviewer_note: str,
) -> dict[str, Any]:
    return {
        "node_id": _stable_node_id("geo:province", province, ""),
        "name": province,
        "parent_id": parent_id,
        "aliases": [province, f"{province}省", f"{province}自治区"],
        "tree_type": "geo",
        "mapping_rule": "rule_seed_v1_province_attachment",
        "confidence": 0.82,
        "review_status": "reviewed",
        "source": source,
        "reviewer_note": reviewer_note,
    }


def _reviewed_city_node(
    *,
    tree_type: str,
    node_id: str,
    name: str,
    parent_id: str,
    source: str,
    mapping_rule: str,
    confidence: float,
    reviewer_note: str,
) -> dict[str, Any]:
    return {
        "node_id": node_id,
        "name": name,
        "parent_id": parent_id,
        "aliases": [name],
        "tree_type": tree_type,
        "mapping_rule": mapping_rule,
        "confidence": confidence,
        "review_status": "reviewed",
        "source": source,
        "reviewer_note": reviewer_note,
    }


def apply_seed_reviews(
    *,
    packet: list[dict[str, Any]],
    geo_tree: dict[str, Any],
    urban_tree: dict[str, Any],
    top_n: int = 50,
    require_reviewer_action: bool = False,
) -> tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]]]:
    geo_v1 = copy.deepcopy(geo_tree)
    urban_v1 = copy.deepcopy(urban_tree)
    reviewed_rows: list[dict[str, Any]] = []
    source = "region_tree_review_packet_v1"

    for row in packet:
        has_manual_action = bool(
            row.get("reviewer_geo_action") or row.get("reviewer_urban_action")
        )
        if require_reviewer_action and not has_manual_action:
            continue
        if not require_reviewer_action and _should_skip_rule_seed(row):
            continue
        if not require_reviewer_action and len(reviewed_rows) >= top_n:
            break

        province = str(row["province"])
        city = str(row["city"])
        note = (
            row.get("reviewer_note")
            or f"Rule-seeded v1 review for high-priority coverage row "
            f"{row['priority_rank']}; requires later human confirmation."
        )

        geo_action = row.get("reviewer_geo_action") or "accept_suggested_geo"
        geo_parent_id = str(
            row.get("reviewer_geo_parent_id")
            or row.get("suggested_geo_parent_id")
            or "geo:china"
        )
        if not _find_node(geo_v1, geo_parent_id):
            province_name = normalize_region_name(province) or province
            province_parent = PROVINCE_GEO_PARENT_HINTS.get(province_name, "geo:china")
            province_node = _province_node(
                province=province_name,
                parent_id=province_parent,
                source=source,
                reviewer_note=note,
            )
            _append_node_if_missing(geo_v1, province_node)
            geo_parent_id = province_node["node_id"]

        geo_node_id = str(
            row.get("reviewer_geo_node_id") or row["suggested_geo_node_id"]
        )
        geo_name = str(row.get("reviewer_geo_name") or row["suggested_geo_name"])
        if geo_action in {"accept_suggested_geo", "add_geo_node"}:
            _append_node_if_missing(
                geo_v1,
                _reviewed_city_node(
                    tree_type="geo",
                    node_id=geo_node_id,
                    name=geo_name,
                    parent_id=geo_parent_id,
                    source=source,
                    mapping_rule="rule_seed_v1_geo_city_attachment",
                    confidence=0.86,
                    reviewer_note=note,
                ),
            )

        urban_action = row.get("reviewer_urban_action")
        if not urban_action:
            urban_action = (
                "keep_current_urban"
                if row.get("current_urban_node_id")
                else "accept_suggested_urban"
            )
        if urban_action in {"accept_suggested_urban", "add_urban_node"}:
            urban_parent_id = str(
                row.get("reviewer_urban_parent_id")
                or row.get("suggested_urban_parent_id")
            )
            urban_node_id = str(
                row.get("reviewer_urban_node_id") or row["suggested_urban_node_id"]
            )
            urban_name = str(
                row.get("reviewer_urban_name") or row["suggested_urban_name"]
            )
            _append_node_if_missing(
                urban_v1,
                _reviewed_city_node(
                    tree_type="urban_tier",
                    node_id=urban_node_id,
                    name=urban_name,
                    parent_id=urban_parent_id,
                    source=source,
                    mapping_rule="rule_seed_v1_urban_tier_attachment",
                    confidence=0.82,
                    reviewer_note=note,
                ),
            )

        row["reviewer_geo_action"] = geo_action
        row["reviewer_geo_parent_id"] = geo_parent_id
        row["reviewer_geo_node_id"] = geo_node_id
        row["reviewer_geo_name"] = geo_name
        row["reviewer_urban_action"] = urban_action
        row["reviewer_urban_parent_id"] = row.get("reviewer_urban_parent_id") or str(
            row.get("current_urban_node_id") or row.get("suggested_urban_parent_id")
        )
        row["reviewer_urban_node_id"] = row.get("reviewer_urban_node_id") or str(
            row.get("current_urban_node_id") or row.get("suggested_urban_node_id")
        )
        row["reviewer_urban_name"] = row.get("reviewer_urban_name") or city
        row["reviewer_confidence"] = "0.82"
        row["reviewer_note"] = note
        reviewed_rows.append(row)

    geo_errors = validate_tree(geo_v1, "geo")
    urban_errors = validate_tree(urban_v1, "urban_tier")
    if geo_errors or urban_errors:
        raise ValueError({"geo_tree": geo_errors, "urban_tree": urban_errors})
    return geo_v1, urban_v1, reviewed_rows


def _rows_from_report(report: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "province": entry["province"],
            "city": entry["city"],
            "school_count": entry["school_count"],
        }
        for entry in report["entries"]
    ]


def compare_summaries(
    v0_summary: dict[str, Any], v1_summary: dict[str, Any]
) -> dict[str, int]:
    return {
        key: int(v1_summary[key]) - int(v0_summary[key])
        for key in v0_summary
        if isinstance(v0_summary.get(key), int) and isinstance(v1_summary.get(key), int)
    }


def build_v1_report(
    *,
    v0_report: dict[str, Any],
    geo_v1: dict[str, Any],
    urban_v1: dict[str, Any],
    reviewed_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    v1_coverage = build_coverage_report(_rows_from_report(v0_report), geo_v1, urban_v1)
    return {
        "summary": {
            "v0": v0_report["summary"],
            "v1": v1_coverage["summary"],
            "delta": compare_summaries(v0_report["summary"], v1_coverage["summary"]),
        },
        "review_batch": {
            "review_packet_total": len(v0_report.get("review_queue", [])),
            "seed_reviewed_count": len(reviewed_rows),
            "review_source": "rule_seed_v1_top_priority_rows",
        },
        "reviewed_rows": reviewed_rows,
        "v1_coverage": v1_coverage,
        "boundary": {
            "region_tree_relax_status": "not_implemented",
            "agent_benchmark_status": "not_implemented",
            "warning": "This report validates region-tree data coverage only; do not treat schools.city alone as Pareto gain.",
        },
    }


def render_v1_markdown_report(report: dict[str, Any]) -> str:
    summary = report["summary"]
    v0 = summary["v0"]
    v1 = summary["v1"]
    delta = summary["delta"]
    lines = [
        "# Region Tree v1 HITL Coverage Report",
        "",
        "本报告验收地域树 HITL 审校包与 v1 数据层覆盖改进，不表示 `region_tree_relax` 已进入 Agent 或 Benchmark 实验。",
        "",
        "## Boundary",
        "",
        "- 当前主实验仍是 `major_geo_v1 + risk_band_v1`。",
        "- 当前六组实验结果不包含地域树实验。",
        "- `region_tree_relax` 尚未实现，不得把本报告写成 Pareto gain。",
        "- 不能只凭 `schools.city` 包装城市收益。",
        "- 未来 Agent 仍不能读取 `implicit_flexibilities` 或 `volunteer_set`。",
        "",
        "## v0 / v1 Coverage Comparison",
        "",
        "| Metric | v0 | v1 | Delta |",
        "|---|---:|---:|---:|",
    ]
    for key in v0:
        lines.append(f"| `{key}` | {v0[key]} | {v1[key]} | {delta.get(key, 0)} |")

    batch = report["review_batch"]
    lines.extend(
        [
            "",
            "## Review Batch",
            "",
            f"- Review packet rows: {batch['review_packet_total']}",
            f"- Rule-seeded v1 reviewed rows: {batch['seed_reviewed_count']}",
            "- Review source: `rule_seed_v1_top_priority_rows`",
            "- 这些条目是 v1 seed，不等同于最终人工审校完成；后续可以在 CSV/JSONL 中人工修改后再次回填。",
            "",
            "## Reviewed Seed Rows",
            "",
            "| Rank | Province | City | Schools | Geo action | Urban action | Reasons |",
            "|---:|---|---|---:|---|---|---|",
        ]
    )
    for row in report["reviewed_rows"][:80]:
        lines.append(
            "| {rank} | {province} | {city} | {schools} | {geo_action} | "
            "{urban_action} | {reasons} |".format(
                rank=row["priority_rank"],
                province=row["province"],
                city=row["city"],
                schools=row["school_count"],
                geo_action=row["reviewer_geo_action"],
                urban_action=row["reviewer_urban_action"],
                reasons=row["review_reasons"],
            )
        )

    remaining = report["v1_coverage"]["review_queue"]
    lines.extend(
        [
            "",
            "## Remaining Review Queue Sample",
            "",
            "| Province | City | Schools | Geo node | Urban node | Reasons |",
            "|---|---|---:|---|---|---|",
        ]
    )
    for entry in remaining[:80]:
        lines.append(
            "| {province} | {city} | {schools} | {geo_node} | {urban_node} | "
            "{reasons} |".format(
                province=entry["province"],
                city=entry["city"],
                schools=entry["school_count"],
                geo_node=entry["geo_node_id"] or "-",
                urban_node=entry["urban_node_id"] or "-",
                reasons=", ".join(entry["review_reasons"]),
            )
        )
    return "\n".join(lines) + "\n"


def write_v1_artifacts(
    *,
    coverage_report_path: Path = DEFAULT_JSON_REPORT_PATH,
    geo_tree_path: Path = DEFAULT_GEO_TREE_PATH,
    urban_tree_path: Path = DEFAULT_URBAN_TREE_PATH,
    review_packet_csv_path: Path = DEFAULT_REVIEW_PACKET_CSV_PATH,
    review_packet_jsonl_path: Path = DEFAULT_REVIEW_PACKET_JSONL_PATH,
    geo_tree_v1_path: Path = DEFAULT_GEO_TREE_V1_PATH,
    urban_tree_v1_path: Path = DEFAULT_URBAN_TREE_V1_PATH,
    v1_json_report_path: Path = DEFAULT_V1_JSON_REPORT_PATH,
    v1_md_report_path: Path = DEFAULT_V1_MD_REPORT_PATH,
    seed_top_n: int = 50,
    reviewed_packet_path: Path | None = None,
) -> dict[str, Any]:
    v0_report = json.loads(coverage_report_path.read_text(encoding="utf-8"))
    if reviewed_packet_path:
        packet = read_review_packet(reviewed_packet_path)
        require_reviewer_action = True
    else:
        packet = build_review_packet(v0_report)
        write_review_packet(packet, review_packet_csv_path, review_packet_jsonl_path)
        require_reviewer_action = False

    geo_v1, urban_v1, reviewed_rows = apply_seed_reviews(
        packet=packet,
        geo_tree=load_tree(geo_tree_path),
        urban_tree=load_tree(urban_tree_path),
        top_n=seed_top_n,
        require_reviewer_action=require_reviewer_action,
    )
    geo_tree_v1_path.write_text(
        json.dumps(
            {
                **geo_v1,
                "version": "v1",
                "description": "Reviewed v1 seed from region_tree_review_packet; not an Agent/Benchmark result.",
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    urban_tree_v1_path.write_text(
        json.dumps(
            {
                **urban_v1,
                "version": "v1",
                "description": "Reviewed v1 seed from region_tree_review_packet; not an Agent/Benchmark result.",
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    report = build_v1_report(
        v0_report=v0_report,
        geo_v1=geo_v1,
        urban_v1=urban_v1,
        reviewed_rows=reviewed_rows,
    )
    v1_json_report_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    v1_md_report_path.write_text(render_v1_markdown_report(report), encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build HITL review packet and reviewed-v1 region tree artifacts."
    )
    parser.add_argument(
        "--coverage-report", type=Path, default=DEFAULT_JSON_REPORT_PATH
    )
    parser.add_argument("--geo-tree", type=Path, default=DEFAULT_GEO_TREE_PATH)
    parser.add_argument("--urban-tree", type=Path, default=DEFAULT_URBAN_TREE_PATH)
    parser.add_argument(
        "--review-packet-csv",
        type=Path,
        default=DEFAULT_REVIEW_PACKET_CSV_PATH,
    )
    parser.add_argument(
        "--review-packet-jsonl",
        type=Path,
        default=DEFAULT_REVIEW_PACKET_JSONL_PATH,
    )
    parser.add_argument("--geo-tree-v1", type=Path, default=DEFAULT_GEO_TREE_V1_PATH)
    parser.add_argument(
        "--urban-tree-v1", type=Path, default=DEFAULT_URBAN_TREE_V1_PATH
    )
    parser.add_argument(
        "--v1-json-report", type=Path, default=DEFAULT_V1_JSON_REPORT_PATH
    )
    parser.add_argument("--v1-md-report", type=Path, default=DEFAULT_V1_MD_REPORT_PATH)
    parser.add_argument("--seed-top-n", type=int, default=50)
    parser.add_argument(
        "--input-reviewed-packet",
        type=Path,
        default=None,
        help="Optional edited CSV/JSONL review packet to apply instead of rule seeding.",
    )
    args = parser.parse_args()

    report = write_v1_artifacts(
        coverage_report_path=args.coverage_report,
        geo_tree_path=args.geo_tree,
        urban_tree_path=args.urban_tree,
        review_packet_csv_path=args.review_packet_csv,
        review_packet_jsonl_path=args.review_packet_jsonl,
        geo_tree_v1_path=args.geo_tree_v1,
        urban_tree_v1_path=args.urban_tree_v1,
        v1_json_report_path=args.v1_json_report,
        v1_md_report_path=args.v1_md_report,
        seed_top_n=args.seed_top_n,
        reviewed_packet_path=args.input_reviewed_packet,
    )
    batch = report["review_batch"]
    v1_summary = report["summary"]["v1"]
    print(
        "Region tree v1 artifacts written: "
        f"packet_rows={batch['review_packet_total']}, "
        f"seed_reviewed={batch['seed_reviewed_count']}, "
        f"remaining_review_queue={v1_summary['review_queue_count']}"
    )


if __name__ == "__main__":
    main()
