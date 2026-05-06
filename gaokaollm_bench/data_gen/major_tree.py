"""Generic major-cluster tree parsing and traversal."""

from __future__ import annotations

import json
from dataclasses import dataclass
from difflib import get_close_matches
from pathlib import Path
from typing import Any


DEFAULT_CLUSTER_PATH = Path(__file__).with_name("major_clusters.json")


class UnknownMajorError(ValueError):
    """Raised when a major cannot be mapped to any cluster node."""

    def __init__(self, major_name: str, suggestions: list[str]):
        self.major_name = major_name
        self.suggestions = suggestions
        super().__init__(
            f"Unknown major: {major_name}. Suggestions: {', '.join(suggestions) or 'none'}"
        )


@dataclass(frozen=True)
class MajorNode:
    id: str
    label: str
    parent: str | None
    level: int
    include_keywords: tuple[str, ...]
    exclude_keywords: tuple[str, ...]
    observed_names: tuple[str, ...]


def load_major_tree(path: str | Path | None = None) -> dict[str, Any]:
    cluster_path = Path(path) if path else DEFAULT_CLUSTER_PATH
    return json.loads(cluster_path.read_text(encoding="utf-8"))


def _nodes(data: dict[str, Any]) -> dict[str, MajorNode]:
    raw_nodes = data.get("nodes", {})
    if not raw_nodes and data.get("clusters"):
        raw_nodes = data["clusters"]

    nodes: dict[str, MajorNode] = {}
    for node_id, node in raw_nodes.items():
        nodes[node_id] = MajorNode(
            id=node.get("id") or node_id,
            label=node.get("label") or node_id,
            parent=node.get("parent"),
            level=int(node.get("level") or 0),
            include_keywords=tuple(node.get("include_keywords", [])),
            exclude_keywords=tuple(node.get("exclude_keywords", [])),
            observed_names=tuple(node.get("observed_names") or node.get("real_names") or []),
        )
    return nodes


def get_node(node_id: str, *, path: str | Path | None = None) -> MajorNode:
    nodes = _nodes(load_major_tree(path))
    if node_id not in nodes:
        raise KeyError(f"Unknown major tree node: {node_id}")
    return nodes[node_id]


def _matches_node(major_name: str, node: MajorNode) -> bool:
    if any(term and term in major_name for term in node.exclude_keywords):
        return False
    if any(name and name == major_name for name in node.observed_names):
        return True
    return any(term and term in major_name for term in node.include_keywords)


def _leaf_nodes(nodes: dict[str, MajorNode]) -> list[MajorNode]:
    parent_ids = {node.parent for node in nodes.values() if node.parent}
    return [node for node in nodes.values() if node.id not in parent_ids]


def _suggestions(major_name: str, nodes: dict[str, MajorNode]) -> list[str]:
    names: list[str] = []
    for node in nodes.values():
        names.extend(node.observed_names)
        names.extend(node.include_keywords)
    return get_close_matches(major_name, list(dict.fromkeys(names)), n=5, cutoff=0.2)


def resolve_major_node(major_name: str, *, path: str | Path | None = None) -> MajorNode:
    """Resolve a raw major name to the most specific matching leaf node."""

    return resolve_major_node_from_tree(major_name, load_major_tree(path))


def resolve_major_node_from_tree(major_name: str, tree: dict[str, Any]) -> MajorNode:
    """Resolve a raw major name against an in-memory major tree."""

    nodes = _nodes(tree)
    exact = [
        node
        for node in _leaf_nodes(nodes)
        if any(name and (major_name == name or major_name.startswith(f"{name}(")) for name in node.observed_names)
    ]
    if exact:
        return max(exact, key=lambda node: node.level)

    keyword_matches = [node for node in _leaf_nodes(nodes) if _matches_node(major_name, node)]
    if keyword_matches:
        return max(keyword_matches, key=lambda node: node.level)

    raise UnknownMajorError(major_name, _suggestions(major_name, nodes))


def get_major_cluster_patterns(
    node_ids: list[str],
    *,
    path: str | Path | None = None,
) -> tuple[list[str], list[str]]:
    """Return SQL LIKE include and exclude patterns for one or more tree nodes."""

    nodes = _nodes(load_major_tree(path))
    include_terms: list[str] = []
    exclude_terms: list[str] = []

    for node_id in node_ids:
        if node_id not in nodes:
            raise KeyError(f"Unknown major tree node: {node_id}")
        node = nodes[node_id]
        include_terms.extend(node.observed_names)
        include_terms.extend(node.include_keywords)
        exclude_terms.extend(node.exclude_keywords)

    include_patterns = [f"%{term}%" for term in dict.fromkeys(include_terms) if term]
    exclude_patterns = [f"%{term}%" for term in dict.fromkeys(exclude_terms) if term]
    return include_patterns, exclude_patterns


def _children(parent_id: str, nodes: dict[str, MajorNode]) -> list[MajorNode]:
    return [node for node in nodes.values() if node.parent == parent_id]


def _descendant_leaves(node_id: str, nodes: dict[str, MajorNode]) -> list[MajorNode]:
    children = _children(node_id, nodes)
    if not children:
        return [nodes[node_id]]

    leaves: list[MajorNode] = []
    for child in children:
        leaves.extend(_descendant_leaves(child.id, nodes))
    return leaves


def _ancestor_chain(node: MajorNode, nodes: dict[str, MajorNode]) -> list[MajorNode]:
    chain = [node]
    current = node
    while current.parent:
        current = nodes[current.parent]
        chain.append(current)
    return chain


def _ancestor_at_level(node: MajorNode, nodes: dict[str, MajorNode], level: int) -> MajorNode | None:
    for ancestor in _ancestor_chain(node, nodes):
        if ancestor.level == level:
            return ancestor
    return None


def build_relaxation_stages(
    source_major: str | None = None,
    *,
    source_node_id: str | None = None,
    path: str | Path | None = None,
    neighbor_node_ids: list[str] | None = None,
    neighbor_limit: int = 3,
    neighbor_category_level: int = 1,
    skip_ancestor_category: bool = False,
    include_any_major_stage: bool = False,
) -> list[dict[str, Any]]:
    """Build generic staged relaxations from any source major or source node."""

    data = load_major_tree(path)
    nodes = _nodes(data)
    source = nodes[source_node_id] if source_node_id else resolve_major_node(source_major or "", path=path)
    chain = _ancestor_chain(source, nodes)
    parent = nodes[source.parent] if source.parent else None
    grandparent = nodes[parent.parent] if parent and parent.parent else None
    root = chain[-1]
    policy = data.get("tree_policy", {}).get("stages", [])

    stages: list[dict[str, Any]] = []
    for policy_stage in policy:
        strategy = policy_stage.get("strategy")
        if strategy == "same_leaf_variants":
            target_nodes = [source]
        elif strategy == "sibling_leaf_clusters" and parent:
            target_nodes = [
                node for node in _descendant_leaves(parent.id, nodes) if node.id != source.id
            ]
        elif strategy == "cousin_leaf_clusters" and grandparent:
            source_branch = parent.id if parent else source.id
            target_nodes = [
                leaf
                for child in _children(grandparent.id, nodes)
                if child.id != source_branch
                for leaf in _descendant_leaves(child.id, nodes)
            ]
        elif strategy == "ancestor_category":
            target_nodes = [root]
        else:
            target_nodes = []

        if not target_nodes:
            continue
        if strategy == "ancestor_category" and skip_ancestor_category:
            continue

        cluster_ids = [node.id for node in target_nodes]
        include_patterns, exclude_patterns = get_major_cluster_patterns(cluster_ids, path=path)
        stages.append(
            {
                "stage": policy_stage["stage"],
                "label": policy_stage["label"],
                "strategy": strategy,
                "source_cluster": source.id,
                "cluster_ids": cluster_ids,
                "psychological_distance": policy_stage.get("psychological_distance"),
                "include_patterns": include_patterns,
                "exclude_patterns": exclude_patterns,
            }
        )

    used_cluster_ids = {
        cluster_id
        for stage in stages
        for cluster_id in stage.get("cluster_ids", [])
    }
    if neighbor_node_ids:
        if neighbor_limit < 1:
            raise ValueError("neighbor_limit must be at least 1")
        neighbor_category_ids: list[str] = []
        for node_id in dict.fromkeys(neighbor_node_ids):
            if node_id not in nodes or node_id == source.id or node_id in used_cluster_ids:
                continue
            category = _ancestor_at_level(nodes[node_id], nodes, neighbor_category_level)
            if not category or category.id in used_cluster_ids or category.id in neighbor_category_ids:
                continue
            neighbor_category_ids.append(category.id)
            if len(neighbor_category_ids) >= neighbor_limit:
                break

        cluster_ids = [
            leaf.id
            for category_id in neighbor_category_ids
            for leaf in _descendant_leaves(category_id, nodes)
            if leaf.id != source.id and leaf.id not in used_cluster_ids
        ]
        if cluster_ids:
            include_patterns, exclude_patterns = get_major_cluster_patterns(cluster_ids, path=path)
            stages.append(
                {
                    "stage": 4,
                    "label": "Probe相邻大类",
                    "strategy": "probe_neighbor_categories",
                    "source_cluster": source.id,
                    "category_ids": neighbor_category_ids,
                    "cluster_ids": cluster_ids,
                    "psychological_distance": "probe_near",
                    "include_patterns": include_patterns,
                    "exclude_patterns": exclude_patterns,
                    "relaxation_kind": "clinical_to_medtech",
                }
            )

    if include_any_major_stage:
        stages.append(
            {
                "stage": 5,
                "label": "去除专业限制",
                "strategy": "any_major",
                "source_cluster": source.id,
                "cluster_ids": [],
                "psychological_distance": "far",
                "include_patterns": [],
                "exclude_patterns": [],
                "relaxation_kind": "any_major",
            }
        )

    return stages


def collect_observed_major_names(
    raw_names: list[str],
    *,
    path: str | Path | None = None,
) -> dict[str, list[str]]:
    """Assign observed DB major names to leaf nodes without mutating the tree file."""

    return collect_observed_major_names_from_tree(raw_names, load_major_tree(path))


def collect_observed_major_names_from_tree(
    raw_names: list[str],
    tree: dict[str, Any],
) -> dict[str, list[str]]:
    """Assign observed DB major names to leaf nodes in an in-memory tree."""

    assignments: dict[str, list[str]] = {}
    for raw_name in raw_names:
        try:
            node = resolve_major_node_from_tree(raw_name, tree)
        except UnknownMajorError:
            continue
        assignments.setdefault(node.id, [])
        if raw_name not in assignments[node.id]:
            assignments[node.id].append(raw_name)
    return assignments
