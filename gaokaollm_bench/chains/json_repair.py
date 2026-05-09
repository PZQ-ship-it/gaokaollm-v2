"""JSON parsing and repair helpers for structured LLM outputs."""

from __future__ import annotations

import json
from collections.abc import Sequence
from typing import Any

from gaokaollm_bench.contracts.llm_io import MajorLabelOption


def _as_option(item: MajorLabelOption | dict[str, Any]) -> MajorLabelOption:
    return (
        item
        if isinstance(item, MajorLabelOption)
        else MajorLabelOption.model_validate(item)
    )


def parse_llm_json(content: str) -> Any:
    text = (content or "").strip()
    if text.startswith("```"):
        text = text.strip("`").strip()
        if text.lower().startswith("json"):
            text = text[4:].strip()
    return json.loads(text or "{}")


def _looks_like_invalid_major_name(value: Any) -> bool:
    text = str(value or "").strip()
    if not text:
        return True
    if text in {":", "：", "-", "null", "None"}:
        return True
    return all(ch in ":：-_/\\|,.，。;； " for ch in text)


def repair_json_text(content: Any) -> str:
    """Return parseable JSON text for LangChain JsonOutputParser.

    This intentionally stays dependency-light: it handles fenced JSON and common
    extra prose by extracting the outermost object/list before falling back to
    the original text, letting JsonOutputParser raise a clear validation error.
    """

    if isinstance(content, (dict, list)):
        return json.dumps(content, ensure_ascii=False)
    text = str(content or "").strip()
    try:
        return json.dumps(parse_llm_json(text), ensure_ascii=False)
    except Exception:
        pass

    starts = [idx for idx in (text.find("{"), text.find("[")) if idx >= 0]
    if not starts:
        return text
    start = min(starts)
    end = max(text.rfind("}"), text.rfind("]"))
    if end > start:
        candidate = text[start : end + 1]
        try:
            return json.dumps(parse_llm_json(candidate), ensure_ascii=False)
        except Exception:
            return candidate
    return text


def repair_major_classification_json_text(
    state: dict[str, Any],
    *,
    label_options: Sequence[MajorLabelOption | dict[str, Any]],
    allow_null: bool = False,
) -> str:
    """Repair direct-classification output into the Pydantic parser shape."""

    raw_content = state.get("raw_content", "")
    try:
        parsed = parse_llm_json(raw_content)
    except Exception:
        parsed = {}
    repaired = repair_major_payload(
        parsed,
        major_name=str(state.get("major_name") or ""),
        label_options=label_options,
        allow_null=allow_null,
    )
    selected_label = (
        repaired.get("selected_label") if repaired.get("label_valid") else None
    )
    return json.dumps(
        {
            "major_name": repaired.get("major_name"),
            "selected_label": selected_label,
        },
        ensure_ascii=False,
    )


def repair_major_review_json_text(state: dict[str, Any]) -> str:
    """Repair review output into {"items": [...]} for Pydantic parsing."""

    raw_content = state.get("raw_content", "")
    try:
        parsed = parse_llm_json(raw_content)
    except Exception:
        parsed = {}
    repaired = repair_review_payload(
        parsed,
        expected_items=list(state.get("items") or []),
    )
    return json.dumps({"items": list(repaired.values())}, ensure_ascii=False)


def label_schema(
    label_options: Sequence[MajorLabelOption | dict[str, Any]],
    *,
    allow_null: bool = False,
) -> dict[str, Any]:
    options = [_as_option(item) for item in label_options]
    labels = [item.label for item in options]
    selected_schema: dict[str, Any] = {"type": "string", "enum": labels}
    if allow_null:
        selected_schema = {"anyOf": [selected_schema, {"type": "null"}]}
    return selected_schema


def direct_response_format(
    label_options: Sequence[MajorLabelOption | dict[str, Any]],
    *,
    allow_null: bool = False,
) -> dict[str, Any]:
    return {
        "type": "json_schema",
        "json_schema": {
            "name": "major_direct_classification",
            "strict": True,
            "schema": {
                "type": "object",
                "additionalProperties": False,
                "required": ["major_name", "selected_label"],
                "properties": {
                    "major_name": {"type": "string"},
                    "selected_label": label_schema(
                        label_options, allow_null=allow_null
                    ),
                },
            },
        },
    }


def repair_major_payload(
    payload: Any,
    *,
    major_name: str,
    label_options: Sequence[MajorLabelOption | dict[str, Any]],
    allow_null: bool = False,
) -> dict[str, Any]:
    raw_payload = payload
    notes: list[str] = []
    if (
        isinstance(payload, dict)
        and isinstance(payload.get("items"), list)
        and payload["items"]
    ):
        payload = payload["items"][0]
        notes.append("unwrapped_items")
    if isinstance(payload, dict) and isinstance(payload.get("item"), dict):
        payload = payload["item"]
        notes.append("unwrapped_item")
    if not isinstance(payload, dict):
        return {
            "major_name": major_name,
            "selected_label": None,
            "schema_valid": False,
            "label_valid": False,
            "repair_notes": ["not_object"],
            "raw_output": raw_payload,
        }

    selected = (
        payload.get("selected_label")
        or payload.get("label")
        or payload.get("leaf_id")
        or payload.get("category")
    )
    options = [_as_option(item) for item in label_options]
    label_by_name = {
        str(item.label_name): item.label for item in options if item.label_name
    }
    valid_labels = {item.label for item in options}
    if selected in label_by_name:
        selected = label_by_name[str(selected)]
        notes.append("mapped_label_name_to_label")
    if selected == "":
        selected = None
        notes.append("empty_label_to_null")

    repaired_major = payload.get("major_name") or payload.get("text") or major_name
    if _looks_like_invalid_major_name(repaired_major):
        repaired_major = major_name
        notes.append("replaced_invalid_major_name")
    label_valid = selected in valid_labels
    schema_valid = isinstance(repaired_major, str) and (
        label_valid or (allow_null and selected is None)
    )
    result = {
        "major_name": repaired_major,
        "selected_label": selected,
        "schema_valid": schema_valid,
        "label_valid": label_valid,
        "raw_output": raw_payload,
    }
    if notes:
        result["repair_notes"] = notes
    return result


def repair_review_payload(
    payload: Any,
    *,
    expected_items: list[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    if isinstance(payload, dict) and isinstance(payload.get("items"), list):
        items = payload["items"]
    elif isinstance(payload, list):
        items = payload
    elif isinstance(payload, dict):
        items = [payload]
    else:
        items = []

    expected_by_name = {
        str(item.get("major_name") or ""): item for item in expected_items
    }
    repaired: dict[str, dict[str, Any]] = {}
    for item in items:
        if not isinstance(item, dict):
            continue
        major_name = str(item.get("major_name") or "")
        if not major_name and len(expected_by_name) == 1:
            major_name = next(iter(expected_by_name))
        candidates = {
            str(candidate.get("label"))
            for candidate in (
                expected_by_name.get(major_name, {}).get("candidates") or []
            )
            if candidate.get("label")
        }
        selected = (
            item.get("selected_label") or item.get("label") or item.get("leaf_id")
        )
        if selected == "":
            selected = None
        repaired[major_name] = {
            "major_name": major_name,
            "selected_label": selected
            if selected in candidates or selected is None
            else None,
            "reason": item.get("reason") or item.get("review_notes") or "",
            "label_valid": selected in candidates if selected is not None else False,
            "raw_output": item,
        }
    return repaired
