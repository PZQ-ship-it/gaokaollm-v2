"""Readers for unified iceberg case compatibility views."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.evaluation.schemas import IcebergProfile
from gaokaollm_bench.schemas import UnifiedIcebergCase


DEFAULT_UNIFIED_CASES = Path(
    "gaokaollm_bench/sample_data/unified_iceberg_cases_1c6c_real_db_180.jsonl"
)
DEFAULT_PROFILE_VIEW = Path(
    "app/evaluation/data/unified_iceberg_profiles_1c6c_real_db_180.jsonl"
)


def _read_jsonl(path: str | Path) -> list[dict[str, Any]]:
    source = Path(path)
    if not source.exists():
        raise FileNotFoundError(source)
    rows: list[dict[str, Any]] = []
    with source.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            parsed = json.loads(line)
            if isinstance(parsed, dict):
                rows.append(parsed)
    return rows


def read_unified_cases(
    path: str | Path = DEFAULT_UNIFIED_CASES,
) -> list[UnifiedIcebergCase]:
    return [UnifiedIcebergCase.model_validate(row) for row in _read_jsonl(path)]


def read_unified_iceberg_profiles(
    path: str | Path = DEFAULT_PROFILE_VIEW,
) -> list[IcebergProfile]:
    return [IcebergProfile.model_validate(row) for row in _read_jsonl(path)]
