"""Region-tree artifacts and coverage checks for future region relaxation."""

from __future__ import annotations

import argparse
import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


DEFAULT_DATABASE_URL = "postgresql://postgres@127.0.0.1:55432/gaokao_recommendation"
DEFAULT_GEO_TREE_PATH = Path("gaokaollm_bench/outputs/region_geo_tree.json")
DEFAULT_URBAN_TREE_PATH = Path("gaokaollm_bench/outputs/region_urban_tier_tree.json")
DEFAULT_JSON_REPORT_PATH = Path(
    "gaokaollm_bench/outputs/region_tree_coverage_report.json"
)
DEFAULT_MD_REPORT_PATH = Path("gaokaollm_bench/outputs/region_tree_coverage_report.md")

REQUIRED_NODE_FIELDS = {
    "node_id",
    "name",
    "parent_id",
    "aliases",
    "tree_type",
    "mapping_rule",
    "confidence",
    "review_status",
    "source",
}


@dataclass(frozen=True)
class CoverageEntry:
    province: str
    city: str
    school_count: int
    geo_node_id: str | None
    geo_match_rule: str | None
    geo_confidence: float
    urban_node_id: str | None
    urban_match_rule: str | None
    urban_confidence: float
    review_status: str
    review_reasons: list[str]


def normalize_region_name(value: Any) -> str:
    text = "" if value is None else str(value).strip()
    for suffix in (
        "省",
        "市",
        "特别行政区",
        "壮族自治区",
        "回族自治区",
        "维吾尔自治区",
        "自治区",
    ):
        if text.endswith(suffix):
            text = text[: -len(suffix)]
    return text.replace(" ", "").replace("\u3000", "")


def load_tree(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_tree(
    tree: dict[str, Any], expected_tree_type: str | None = None
) -> list[str]:
    errors: list[str] = []
    nodes = tree.get("nodes")
    if not isinstance(nodes, list) or not nodes:
        return ["tree.nodes must be a non-empty list"]

    node_ids: set[str] = set()
    for index, node in enumerate(nodes):
        if not isinstance(node, dict):
            errors.append(f"nodes[{index}] must be an object")
            continue
        missing = REQUIRED_NODE_FIELDS - set(node)
        if missing:
            errors.append(
                f"{node.get('node_id', index)} missing fields: {sorted(missing)}"
            )
        node_id = str(node.get("node_id", ""))
        if not node_id:
            errors.append(f"nodes[{index}] has empty node_id")
        if node_id in node_ids:
            errors.append(f"duplicate node_id: {node_id}")
        node_ids.add(node_id)
        if expected_tree_type and node.get("tree_type") != expected_tree_type:
            errors.append(f"{node_id} tree_type should be {expected_tree_type}")
        if not isinstance(node.get("aliases"), list):
            errors.append(f"{node_id} aliases must be a list")
        try:
            confidence = float(node.get("confidence"))
        except (TypeError, ValueError):
            errors.append(f"{node_id} confidence must be numeric")
        else:
            if not 0.0 <= confidence <= 1.0:
                errors.append(f"{node_id} confidence must be in [0, 1]")

    for node in nodes:
        parent_id = node.get("parent_id")
        if parent_id is not None and parent_id not in node_ids:
            errors.append(f"{node.get('node_id')} parent_id not found: {parent_id}")
    return errors


def alias_index(tree: dict[str, Any]) -> dict[str, dict[str, Any]]:
    index: dict[str, dict[str, Any]] = {}
    for node in tree["nodes"]:
        names = [node["name"], *node.get("aliases", [])]
        for name in names:
            normalized = normalize_region_name(name)
            if normalized:
                index.setdefault(normalized, node)
    return index


def _node_confidence(node: dict[str, Any] | None) -> float:
    if not node:
        return 0.0
    return round(float(node.get("confidence", 0.0)), 3)


def match_geo_node(
    province: str, city: str, geo_index: dict[str, dict[str, Any]]
) -> tuple[dict[str, Any] | None, str | None, float, list[str]]:
    city_key = normalize_region_name(city)
    province_key = normalize_region_name(province)
    if city_key and city_key in geo_index:
        node = geo_index[city_key]
        return node, "exact_city_alias", _node_confidence(node), []
    if province_key and province_key in geo_index:
        node = geo_index[province_key]
        return (
            node,
            "fallback_to_province_for_unlisted_city",
            min(_node_confidence(node), 0.6),
            ["geo_city_not_explicitly_mapped"],
        )
    return None, None, 0.0, ["geo_province_or_city_unmatched"]


def match_urban_node(
    province: str, city: str, urban_index: dict[str, dict[str, Any]]
) -> tuple[dict[str, Any] | None, str | None, float, list[str]]:
    city_key = normalize_region_name(city)
    province_key = normalize_region_name(province)
    if city_key and city_key in urban_index:
        node = urban_index[city_key]
        return node, "exact_city_alias", _node_confidence(node), []
    if province_key in {"北京", "上海", "天津", "重庆"} and province_key in urban_index:
        node = urban_index[province_key]
        return node, "direct_municipality_alias", _node_confidence(node), []
    return None, None, 0.0, ["urban_tier_unmatched"]


def build_coverage_report(
    rows: list[dict[str, Any]],
    geo_tree: dict[str, Any],
    urban_tree: dict[str, Any],
) -> dict[str, Any]:
    geo_errors = validate_tree(geo_tree, "geo")
    urban_errors = validate_tree(urban_tree, "urban_tier")
    if geo_errors or urban_errors:
        raise ValueError({"geo_tree": geo_errors, "urban_tree": urban_errors})

    geo_index = alias_index(geo_tree)
    urban_index = alias_index(urban_tree)
    entries: list[CoverageEntry] = []
    province_keys = {normalize_region_name(row.get("province")) for row in rows}
    province_mapped = {key for key in province_keys if key and key in geo_index}

    for row in sorted(
        rows,
        key=lambda item: (
            str(item.get("province") or ""),
            str(item.get("city") or ""),
        ),
    ):
        province = str(row.get("province") or "").strip()
        city = str(row.get("city") or "").strip()
        school_count = int(row.get("school_count") or 0)
        geo_node, geo_rule, geo_conf, geo_reasons = match_geo_node(
            province, city, geo_index
        )
        urban_node, urban_rule, urban_conf, urban_reasons = match_urban_node(
            province, city, urban_index
        )
        reasons = [*geo_reasons, *urban_reasons]
        low_conf = geo_conf < 0.8 or urban_conf < 0.8
        if low_conf:
            reasons.append("low_confidence_or_missing_mapping")
        review_status = "needs_review" if reasons else "reviewed"
        entries.append(
            CoverageEntry(
                province=province,
                city=city,
                school_count=school_count,
                geo_node_id=geo_node.get("node_id") if geo_node else None,
                geo_match_rule=geo_rule,
                geo_confidence=geo_conf,
                urban_node_id=urban_node.get("node_id") if urban_node else None,
                urban_match_rule=urban_rule,
                urban_confidence=urban_conf,
                review_status=review_status,
                review_reasons=sorted(set(reasons)),
            )
        )

    total_city_pairs = len(entries)
    total_schools = sum(entry.school_count for entry in entries)
    geo_mapped = [entry for entry in entries if entry.geo_node_id]
    geo_high_conf = [entry for entry in entries if entry.geo_confidence >= 0.8]
    urban_mapped = [entry for entry in entries if entry.urban_node_id]
    urban_high_conf = [entry for entry in entries if entry.urban_confidence >= 0.8]
    review_queue = [entry for entry in entries if entry.review_status != "reviewed"]

    return {
        "summary": {
            "total_city_pairs": total_city_pairs,
            "total_schools": total_schools,
            "province_count": len([key for key in province_keys if key]),
            "province_mapped_count": len(province_mapped),
            "geo_city_pair_mapped_count": len(geo_mapped),
            "geo_city_pair_high_confidence_count": len(geo_high_conf),
            "urban_city_pair_mapped_count": len(urban_mapped),
            "urban_city_pair_high_confidence_count": len(urban_high_conf),
            "review_queue_count": len(review_queue),
        },
        "entries": [asdict(entry) for entry in entries],
        "review_queue": [asdict(entry) for entry in review_queue],
        "boundary": {
            "region_tree_relax_status": "data_layer_v0_only",
            "agent_benchmark_status": "not_implemented",
            "warning": "Do not treat schools.city alone as urban benefit or Pareto gain.",
        },
    }


def render_markdown_report(report: dict[str, Any]) -> str:
    summary = report["summary"]
    review_queue = report["review_queue"]
    lines = [
        "# Region Tree v0 Coverage Report",
        "",
        "本报告只验收地域树数据层覆盖情况，不表示 `region_tree_relax` 已进入 Agent 或 Benchmark 实验。",
        "",
        "## Summary",
        "",
        "| Metric | Value |",
        "|---|---:|",
    ]
    for key, value in summary.items():
        lines.append(f"| `{key}` | {value} |")
    lines.extend(
        [
            "",
            "## Boundary",
            "",
            "- 当前产物是 `region_geo_tree` 与 `region_urban_tier_tree` 的 v0 数据层。",
            "- `region_tree_relax` 尚未实现，不进入当前六组实验结果表。",
            "- 不能只凭 `schools.city` 包装城市收益或 Pareto gain。",
            "- 未来 Agent 仍不能读取 `implicit_flexibilities` 或 `volunteer_set`。",
            "",
            "## Review Queue",
            "",
            "| Province | City | Schools | Geo node | Geo conf. | Urban node | Urban conf. | Reasons |",
            "|---|---|---:|---|---:|---|---:|---|",
        ]
    )
    if not review_queue:
        lines.append("| - | - | 0 | - | 0.000 | - | 0.000 | none |")
    else:
        for entry in review_queue[:200]:
            reasons = ", ".join(entry["review_reasons"])
            lines.append(
                "| {province} | {city} | {school_count} | {geo_node_id} | "
                "{geo_confidence:.3f} | {urban_node_id} | {urban_confidence:.3f} | "
                "{reasons} |".format(
                    province=entry["province"],
                    city=entry["city"],
                    school_count=entry["school_count"],
                    geo_node_id=entry["geo_node_id"] or "-",
                    geo_confidence=float(entry["geo_confidence"]),
                    urban_node_id=entry["urban_node_id"] or "-",
                    urban_confidence=float(entry["urban_confidence"]),
                    reasons=reasons,
                )
            )
    lines.extend(
        [
            "",
            "## Human Review Suggestions",
            "",
            "1. 优先审校 `urban_tier_unmatched` 城市，确认是否需要加入城市层级树。",
            "2. 对 `fallback_to_province_for_unlisted_city` 的地理挂载补充城市或都市圈节点。",
            "3. 城市层级应保留 `source`、`mapping_rule`、`confidence` 和 `review_status`，避免把主观城市偏好伪装成事实收益。",
        ]
    )
    return "\n".join(lines) + "\n"


def load_school_region_rows(database_url: str) -> list[dict[str, Any]]:
    import psycopg
    from psycopg.rows import dict_row

    query = """
        SELECT
            COALESCE(NULLIF(TRIM(province), ''), '(unknown)') AS province,
            COALESCE(NULLIF(TRIM(city), ''), '(unknown)') AS city,
            COUNT(*)::int AS school_count
        FROM schools
        GROUP BY province, city
        ORDER BY province, city
    """
    with psycopg.connect(database_url, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute(query)
            return [dict(row) for row in cur.fetchall()]


def write_report(
    *,
    database_url: str,
    geo_tree_path: Path = DEFAULT_GEO_TREE_PATH,
    urban_tree_path: Path = DEFAULT_URBAN_TREE_PATH,
    json_output: Path = DEFAULT_JSON_REPORT_PATH,
    md_output: Path = DEFAULT_MD_REPORT_PATH,
) -> dict[str, Any]:
    rows = load_school_region_rows(database_url)
    report = build_coverage_report(
        rows, load_tree(geo_tree_path), load_tree(urban_tree_path)
    )
    json_output.parent.mkdir(parents=True, exist_ok=True)
    md_output.parent.mkdir(parents=True, exist_ok=True)
    json_output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    md_output.write_text(render_markdown_report(report), encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Check v0 region-tree coverage against schools.province/city."
    )
    parser.add_argument(
        "--database-url",
        default=os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL),
    )
    parser.add_argument("--geo-tree", type=Path, default=DEFAULT_GEO_TREE_PATH)
    parser.add_argument("--urban-tree", type=Path, default=DEFAULT_URBAN_TREE_PATH)
    parser.add_argument("--json-output", type=Path, default=DEFAULT_JSON_REPORT_PATH)
    parser.add_argument("--md-output", type=Path, default=DEFAULT_MD_REPORT_PATH)
    args = parser.parse_args()
    report = write_report(
        database_url=args.database_url,
        geo_tree_path=args.geo_tree,
        urban_tree_path=args.urban_tree,
        json_output=args.json_output,
        md_output=args.md_output,
    )
    summary = report["summary"]
    print(
        "Region tree coverage written: "
        f"{args.json_output} / {args.md_output}; "
        f"review_queue={summary['review_queue_count']}"
    )


if __name__ == "__main__":
    main()
