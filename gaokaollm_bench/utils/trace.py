"""Lightweight JSONL tracing for benchmark debugging."""

from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any


MAX_STRING_LENGTH = 4000
MAX_LIST_ITEMS = 30


def trace_enabled() -> bool:
    return bool(os.getenv("GAOKAOLLM_TRACE_DIR"))


def trace_event(
    component: str, event: str, payload: dict[str, Any] | None = None
) -> None:
    trace_dir = os.getenv("GAOKAOLLM_TRACE_DIR")
    if not trace_dir:
        return
    trace_id = os.getenv("GAOKAOLLM_TRACE_ID") or "trace"
    path = Path(trace_dir)
    path.mkdir(parents=True, exist_ok=True)
    row = {
        "timestamp": datetime.now().isoformat(timespec="milliseconds"),
        "trace_id": trace_id,
        "component": component,
        "event": event,
        "payload": _safe_json(payload or {}),
    }
    with (path / f"{trace_id}.jsonl").open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")


def _safe_json(value: Any, *, depth: int = 0) -> Any:
    if depth > 6:
        return repr(value)
    if isinstance(value, dict):
        return {
            str(key): _safe_json(item, depth=depth + 1) for key, item in value.items()
        }
    if isinstance(value, (list, tuple, set)):
        items = list(value)
        output = [_safe_json(item, depth=depth + 1) for item in items[:MAX_LIST_ITEMS]]
        if len(items) > MAX_LIST_ITEMS:
            output.append(f"... {len(items) - MAX_LIST_ITEMS} more items")
        return output
    if isinstance(value, str):
        if len(value) > MAX_STRING_LENGTH:
            return value[:MAX_STRING_LENGTH] + f"... <truncated {len(value)} chars>"
        return value
    if isinstance(value, (int, float, bool)) or value is None:
        return value
    return repr(value)
