"""Shared helpers for region-tree relaxation probes and persona generation."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from gaokaollm_bench.data_gen.region_tree import (
    DEFAULT_GEO_TREE_PATH,
    DEFAULT_URBAN_TREE_PATH,
    alias_index,
    load_tree,
    match_geo_node,
    match_urban_node,
    normalize_region_name,
)
from gaokaollm_bench.data_gen.region_tree_review import (
    DEFAULT_GEO_TREE_V1_PATH,
    DEFAULT_URBAN_TREE_V1_PATH,
)


URBAN_TIER_ORDER = {
    "urban:tier:first": 1,
    "urban:tier:new_first": 2,
    "urban:tier:strong_capital": 3,
    "urban:tier:provincial_capital": 4,
    "urban:tier:prefecture": 5,
    "urban:tier:county": 6,
}


def city_variants(city: Any) -> list[str]:
    """Return conservative DB matching variants for city names."""

    raw = "" if city is None else str(city).strip()
    if not raw:
        return []
    variants = [raw]
    if raw.endswith("市"):
        variants.append(raw[:-1])
    else:
        variants.append(f"{raw}市")
    return list(dict.fromkeys(item for item in variants if item))


def _artifact_path(path: str | Path | None, fallback: Path, default: Path) -> Path:
    if path:
        return Path(path)
    if fallback.exists():
        return fallback
    return default


def load_region_trees(
    *,
    geo_tree_path: str | Path | None = None,
    urban_tree_path: str | Path | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Load reviewed v1 trees when available, otherwise fall back to v0."""

    geo_path = _artifact_path(
        geo_tree_path, DEFAULT_GEO_TREE_V1_PATH, DEFAULT_GEO_TREE_PATH
    )
    urban_path = _artifact_path(
        urban_tree_path,
        DEFAULT_URBAN_TREE_V1_PATH,
        DEFAULT_URBAN_TREE_PATH,
    )
    return load_tree(geo_path), load_tree(urban_path)


def _nodes_by_id(tree: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {str(node["node_id"]): node for node in tree.get("nodes", [])}


def _children_by_parent(tree: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    children: dict[str, list[dict[str, Any]]] = {}
    for node in tree.get("nodes", []):
        parent_id = node.get("parent_id")
        if parent_id:
            children.setdefault(str(parent_id), []).append(node)
    return children


def _node_aliases(node: dict[str, Any]) -> list[str]:
    return list(dict.fromkeys([str(node.get("name") or ""), *node.get("aliases", [])]))


def _city_values_for_node(node: dict[str, Any]) -> list[str]:
    values: list[str] = []
    for alias in _node_aliases(node):
        values.extend(city_variants(alias))
    return list(dict.fromkeys(item for item in values if item))


def _confidence(*nodes: dict[str, Any] | None) -> float:
    values = []
    for node in nodes:
        if not node:
            continue
        try:
            values.append(float(node.get("confidence", 0.0)))
        except (TypeError, ValueError):
            values.append(0.0)
    return round(min(values), 3) if values else 0.0


def _target_record(
    *,
    strategy: str,
    tree_type: str,
    source_node: dict[str, Any],
    target_node: dict[str, Any],
) -> dict[str, Any]:
    return {
        "region_relax_strategy": strategy,
        "region_tree_type": tree_type,
        "source_region_node_id": source_node.get("node_id"),
        "source_region_name": source_node.get("name"),
        "target_region_node_id": target_node.get("node_id"),
        "target_region_name": target_node.get("name"),
        "target_region_parent_id": target_node.get("parent_id"),
        "target_city_values": _city_values_for_node(target_node),
        "region_tree_confidence": _confidence(source_node, target_node),
        "region_tree_mapping_rule": target_node.get("mapping_rule"),
        "region_tree_review_status": target_node.get("review_status"),
    }


def build_region_relax_targets(
    *,
    province: str | None,
    city: str | None,
    geo_tree: dict[str, Any],
    urban_tree: dict[str, Any],
    max_targets_per_strategy: int = 80,
) -> list[dict[str, Any]]:
    """Build candidate target city nodes from reviewed region trees."""

    if not province and not city:
        return []

    province_value = province or ""
    city_value = city or province or ""
    current_city_keys = {
        normalize_region_name(item) for item in city_variants(city_value)
    }

    targets: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()

    geo_index = alias_index(geo_tree)
    geo_node, _, _, _ = match_geo_node(province_value, city_value, geo_index)
    if geo_node:
        geo_children = _children_by_parent(geo_tree)
        source_parent_id = geo_node.get("parent_id")
        direct_children = geo_children.get(str(geo_node.get("node_id")), [])
        if direct_children:
            geo_candidate_nodes = direct_children
        elif source_parent_id:
            geo_candidate_nodes = geo_children.get(str(source_parent_id), [])
        else:
            geo_candidate_nodes = []
        for node in geo_candidate_nodes:
            if node.get("node_id") == geo_node.get("node_id"):
                continue
            if normalize_region_name(node.get("name")) in current_city_keys:
                continue
            target = _target_record(
                strategy="geo_block_relax",
                tree_type="geo",
                source_node=geo_node,
                target_node=node,
            )
            if not target["target_city_values"]:
                continue
            key = (
                target["region_relax_strategy"],
                str(target["target_region_node_id"]),
            )
            if key in seen:
                continue
            seen.add(key)
            targets.append(target)
            if (
                len(
                    [
                        item
                        for item in targets
                        if item["region_relax_strategy"] == "geo_block_relax"
                    ]
                )
                >= max_targets_per_strategy
            ):
                break

    urban_index = alias_index(urban_tree)
    urban_node, _, _, _ = match_urban_node(province_value, city_value, urban_index)
    if urban_node:
        urban_children = _children_by_parent(urban_tree)
        source_parent_id = str(urban_node.get("parent_id") or urban_node.get("node_id"))
        source_order = URBAN_TIER_ORDER.get(source_parent_id, 99)
        eligible_tiers = [
            tier_id
            for tier_id, order in URBAN_TIER_ORDER.items()
            if order <= source_order
        ]
        urban_count = 0
        for tier_id in eligible_tiers:
            for node in urban_children.get(tier_id, []):
                if node.get("node_id") == urban_node.get("node_id"):
                    continue
                if normalize_region_name(node.get("name")) in current_city_keys:
                    continue
                target = _target_record(
                    strategy="urban_tier_relax",
                    tree_type="urban_tier",
                    source_node=urban_node,
                    target_node=node,
                )
                if not target["target_city_values"]:
                    continue
                key = (
                    target["region_relax_strategy"],
                    str(target["target_region_node_id"]),
                )
                if key in seen:
                    continue
                seen.add(key)
                targets.append(target)
                urban_count += 1
                if urban_count >= max_targets_per_strategy:
                    break
            if urban_count >= max_targets_per_strategy:
                break

    return targets


def annotate_region_row(row: dict[str, Any], target: dict[str, Any]) -> dict[str, Any]:
    annotated = dict(row)
    for key in (
        "region_relax_strategy",
        "region_tree_type",
        "source_region_node_id",
        "source_region_name",
        "target_region_node_id",
        "target_region_name",
        "target_region_parent_id",
        "region_tree_confidence",
        "region_tree_mapping_rule",
        "region_tree_review_status",
    ):
        annotated[key] = target.get(key)
    annotated["region_tree_evidence"] = (
        f"{target.get('region_relax_strategy')} "
        f"{target.get('source_region_name')} -> {target.get('target_region_name')}"
    )
    return annotated
