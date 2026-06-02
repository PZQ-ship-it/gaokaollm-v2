from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class KnowledgeEmbeddingTargets:
    school_ids: set[int] = field(default_factory=set)
    major_ids: set[int] = field(default_factory=set)
    major_titles: set[str] = field(default_factory=set)

    def is_empty(self) -> bool:
        return not (self.school_ids or self.major_ids or self.major_titles)

    def as_jsonable(self) -> dict[str, list[Any]]:
        return {
            "school_ids": sorted(self.school_ids),
            "major_ids": sorted(self.major_ids),
            "major_titles": sorted(self.major_titles),
        }


def _coerce_int(value: Any) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _iter_dicts(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, dict):
        rows = [value]
        for nested in value.values():
            rows.extend(_iter_dicts(nested))
        return rows
    if isinstance(value, list):
        rows: list[dict[str, Any]] = []
        for item in value:
            rows.extend(_iter_dicts(item))
        return rows
    return []


def targets_from_trace_payload(payload: dict[str, Any]) -> KnowledgeEmbeddingTargets:
    targets = KnowledgeEmbeddingTargets()
    for row in _iter_dicts(payload):
        has_candidate_marker = any(
            key in row
            for key in (
                "admission_score_id",
                "school_id",
                "school_name",
                "major_id",
                "major_name",
            )
        )
        if not has_candidate_marker:
            continue
        school_id = _coerce_int(row.get("school_id"))
        major_id = _coerce_int(row.get("major_id"))
        major_name = str(row.get("major_name") or "").strip()
        if school_id is not None:
            targets.school_ids.add(school_id)
        if major_id is not None:
            targets.major_ids.add(major_id)
        elif major_name:
            targets.major_titles.add(major_name)
    return targets


def targets_from_trace(path: str | Path) -> KnowledgeEmbeddingTargets:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    return targets_from_trace_payload(payload)
