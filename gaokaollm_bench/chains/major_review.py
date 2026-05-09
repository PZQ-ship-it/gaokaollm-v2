"""Low-confidence probe review chain."""

from __future__ import annotations

from typing import Any

from gaokaollm_bench.chains.json_repair import parse_llm_json, repair_review_payload
from gaokaollm_bench.llm.base import BaseLLMClient
from gaokaollm_bench.prompts.major_prompts import build_major_review_messages


def review_messages(items: list[dict[str, Any]]) -> list[dict[str, str]]:
    return build_major_review_messages(items)


async def review_major_candidates(
    *,
    llm_client: BaseLLMClient,
    model: str,
    items: list[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    try:
        raw = await llm_client.complete_json(
            model=model,
            messages=review_messages(items),
            response_format={"type": "json_object"},
            temperature=0,
        )
        parsed = parse_llm_json(raw)
        repaired = repair_review_payload(parsed, expected_items=items)
        for item in repaired.values():
            item["raw_content"] = raw
            item["error"] = None
        return repaired
    except Exception as exc:  # pragma: no cover - external API failure
        return {
            str(item.get("major_name") or ""): {
                "major_name": str(item.get("major_name") or ""),
                "selected_label": None,
                "reason": "",
                "label_valid": False,
                "error": f"{type(exc).__name__}: {exc}",
            }
            for item in items
        }
