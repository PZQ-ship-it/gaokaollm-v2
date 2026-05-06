"""Compatibility wrappers for the generic major tree API."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from gaokaollm_bench.data_gen.major_tree import (
    DEFAULT_CLUSTER_PATH,
    build_relaxation_stages,
    get_major_cluster_patterns,
    load_major_tree,
)


def load_major_clusters(path: str | Path | None = None) -> dict[str, Any]:
    return load_major_tree(path)


def get_relaxation_path(
    source_cluster_id: str,
    *,
    path: str | Path | None = None,
) -> list[dict[str, Any]]:
    return build_relaxation_stages(source_node_id=source_cluster_id, path=path)

