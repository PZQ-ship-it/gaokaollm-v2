import json
import os
import re
from typing import Any

from langchain_core.messages import SystemMessage

from app.core.llm_client import (
    ainvoke_with_timeout,
    get_structured_chat_model,
    structured_timeout_seconds,
)
from app.schemas.state import AgentState


HIDDEN_FIELD_NAMES = {
    "implicit_flexibilities",
    "volunteer_set",
    "axis_flexibilities",
}

AXIS_KEYWORDS = {
    "major": (
        "\u4e13\u4e1a",
        "\u60f3\u8bfb",
        "\u60f3\u5b66",
        "major",
    ),
    "region": (
        "\u5730\u57df",
        "\u5730\u533a",
        "\u57ce\u5e02",
        "\u5916\u7701",
        "\u522b\u592a\u8fdc",
        "\u592a\u8fdc",
        "\u9644\u8fd1",
        "\u7701\u5185",
        "\u6d59\u6c5f",
        "province",
        "city",
    ),
    "risk": (
        "\u7a33",
        "\u4fdd\u5b88",
        "\u4e0d\u8981\u51b2",
        "\u98ce\u9669",
        "risk",
    ),
    "tuition": (
        "\u5b66\u8d39",
        "\u9884\u7b97",
        "\u8d39\u7528",
        "tuition",
        "budget",
    ),
    "quality": (
        "\u5b66\u79d1",
        "\u5b9e\u529b",
        "\u6392\u540d",
        "\u5f3a\u6821",
        "quality",
        "strength",
    ),
    "employment": (
        "\u5c31\u4e1a",
        "\u85aa\u8d44",
        "\u5c97\u4f4d",
        "employment",
        "salary",
    ),
}


def _latest_user_text(state: AgentState) -> str:
    for message in reversed(state.get("messages", [])):
        if getattr(message, "type", None) == "human":
            return str(message.content)
    return ""


def _json_from_text(text: str) -> dict[str, Any]:
    match = re.search(r"\{.*\}", text, flags=re.S)
    if not match:
        return {}
    try:
        data = json.loads(match.group(0))
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def _fallback_axes(text: str) -> list[str]:
    lowered = text.lower()
    axes: list[str] = []
    for axis, keywords in AXIS_KEYWORDS.items():
        if any(keyword.lower() in lowered for keyword in keywords):
            axes.append(axis)
    return axes


def _fallback_intent(text: str) -> dict[str, Any]:
    return {
        "rewritten_query": re.sub(r"\s+", " ", text).strip(),
        "intent_axes": _fallback_axes(text),
        "ambiguities": [],
        "clarification_hint": None,
        "source": "fallback",
    }


def _sanitize_intent(data: dict[str, Any], fallback: dict[str, Any]) -> dict[str, Any]:
    rewritten = str(data.get("rewritten_query") or fallback["rewritten_query"])
    if rewritten.count("?") >= max(3, len(rewritten) // 4):
        rewritten = fallback["rewritten_query"]
    sanitized = {
        "rewritten_query": rewritten,
        "intent_axes": data.get("intent_axes") or fallback["intent_axes"],
        "ambiguities": data.get("ambiguities") or [],
        "clarification_hint": data.get("clarification_hint"),
        "source": data.get("source") or "llm",
    }
    if not isinstance(sanitized["intent_axes"], list):
        sanitized["intent_axes"] = fallback["intent_axes"]
    if not isinstance(sanitized["ambiguities"], list):
        sanitized["ambiguities"] = []
    sanitized["intent_axes"] = [
        str(axis) for axis in sanitized["intent_axes"] if str(axis) in AXIS_KEYWORDS
    ]
    for hidden_name in HIDDEN_FIELD_NAMES:
        sanitized.pop(hidden_name, None)
    return sanitized


async def semantic_normalizer_node(state: AgentState) -> dict[str, Any]:
    text = _latest_user_text(state)
    fallback = _fallback_intent(text)
    print("[semantic_normalizer] normalizing explicit user intent")

    if (
        os.getenv("GAOKAOLLM_OFFLINE_DETERMINISTIC") == "1"
        or os.getenv("GAOKAOLLM_SKIP_LLM_SEMANTIC", "1") == "1"
        or not text
    ):
        intent = fallback
    else:
        llm = get_structured_chat_model()
        prompt = [
            SystemMessage(
                content=(
                    "You are a query rewriting and intent-normalization module for "
                    "Gaokao admission advising. Only normalize explicit user input. "
                    "Do not infer hidden preferences, do not output school candidates, "
                    "and do not output implicit_flexibilities, volunteer_set, or "
                    "axis_flexibilities. Return JSON only with fields: "
                    "rewritten_query(str), intent_axes(list[str]), ambiguities(list[str]), "
                    "clarification_hint(str|null). intent_axes can only contain: "
                    "major, region, risk, tuition, quality, employment."
                )
            ),
            SystemMessage(content=f"Latest user utterance: {text}"),
        ]
        try:
            response = await ainvoke_with_timeout(
                llm,
                prompt,
                timeout=structured_timeout_seconds(),
                label="semantic_normalizer",
            )
            parsed = _json_from_text(str(response.content))
            intent = _sanitize_intent(parsed, fallback)
        except Exception as exc:
            print(
                "[semantic_normalizer] llm_normalize_failed="
                f"{type(exc).__name__}; using fallback intent"
            )
            intent = fallback

    return {
        "rewritten_query": intent["rewritten_query"],
        "intent_axes": list(intent.get("intent_axes") or []),
        "normalized_intent": intent,
    }
