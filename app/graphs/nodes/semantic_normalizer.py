import json
import os
import re
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from app.core.embedding_client import embed_one, ensure_embedding_dimension
from app.core.llm_client import (
    ainvoke_with_timeout,
    get_structured_chat_model,
    structured_timeout_seconds,
)
from app.schemas.state import AgentState
from gaokaollm_bench.utils.trace import trace_event


HIDDEN_FIELD_NAMES = {
    "implicit_flexibilities",
    "volunteer_set",
    "axis_flexibilities",
    "full_context_embedding",
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

DEFAULT_LEXICOGRAPHIC_EPSILON = 0.01


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


def _compact_json(value: Any, *, max_chars: int = 600) -> str:
    if value in (None, "", [], {}):
        return ""
    try:
        text = json.dumps(value, ensure_ascii=False, sort_keys=True)
    except TypeError:
        text = str(value)
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) > max_chars:
        return text[: max_chars - 1] + "…"
    return text


def _conversation_tail(state: AgentState, *, limit: int = 4) -> list[str]:
    messages = state.get("messages", []) or []
    tail: list[str] = []
    for message in messages[-limit:]:
        content = getattr(message, "content", None)
        if not content:
            continue
        role = getattr(message, "type", "") or message.__class__.__name__
        tail.append(f"{role}: {str(content)}")
    return tail


def build_full_context_query(
    state: AgentState,
    *,
    intent: dict[str, Any] | None = None,
) -> str:
    """Build the natural-language Q_full used by the semantic tie-breaker."""

    constraints = state.get("constraints") if isinstance(state, dict) else {}
    original_constraints = (
        state.get("original_constraints") if isinstance(state, dict) else {}
    )
    weights = state.get("implicit_weights") if isinstance(state, dict) else {}
    accepted = state.get("accepted_relaxations") if isinstance(state, dict) else []
    feedback = state.get("feedback_analysis") if isinstance(state, dict) else None
    latest_feedback = (
        state.get("latest_human_feedback") if isinstance(state, dict) else None
    )
    rewritten = ""
    axes: list[str] = []
    if isinstance(intent, dict):
        rewritten = str(intent.get("rewritten_query") or "")
        axes = [str(axis) for axis in intent.get("intent_axes") or []]
    if not rewritten:
        rewritten = str(state.get("rewritten_query") or _latest_user_text(state))
    if not axes:
        axes = [str(axis) for axis in state.get("intent_axes") or []]

    parts = [
        "高考志愿推荐全语境查询。",
        f"用户原始/改写诉求：{rewritten}" if rewritten else "",
        f"显性意图轴：{', '.join(axes)}" if axes else "",
        f"当前硬性与偏好约束：{_compact_json(constraints)}",
        f"初始约束：{_compact_json(original_constraints)}",
        f"当前隐式权重：{_compact_json(weights, max_chars=300)}",
        f"已接受放宽：{_compact_json(accepted)}",
        f"最近反馈分析：{_compact_json(feedback, max_chars=300)}",
        f"用户最新反馈：{latest_feedback}" if latest_feedback else "",
    ]
    conversation = _conversation_tail(state)
    if conversation:
        parts.append("最近对话：" + " | ".join(conversation))
    query = "\n".join(part for part in parts if part and not part.endswith("："))
    return re.sub(r"\n{3,}", "\n\n", query).strip()


def _semantic_rerank_enabled() -> bool:
    if os.getenv("GAOKAOLLM_DISABLE_FULL_CONTEXT_RERANK") == "1":
        return False
    if os.getenv("GAOKAOLLM_OFFLINE_DETERMINISTIC") == "1":
        return False
    if os.getenv("PYTEST_CURRENT_TEST"):
        return False
    if not os.getenv("EMBEDDING_MODEL"):
        raise RuntimeError(
            "EMBEDDING_MODEL is required for full-context semantic ranking."
        )
    return True


async def refresh_full_context_semantics(
    state: AgentState,
    *,
    intent: dict[str, Any] | None = None,
) -> dict[str, Any]:
    query = build_full_context_query(state, intent=intent)
    output: dict[str, Any] = {
        "full_context_query": query,
        "lexicographic_epsilon": float(
            state.get("lexicographic_epsilon") or DEFAULT_LEXICOGRAPHIC_EPSILON
        ),
    }
    if not _semantic_rerank_enabled() or not query:
        return output
    vector = await embed_one(query)
    ensure_embedding_dimension(vector, label="full_context_embedding")
    output["full_context_embedding"] = vector
    output["full_context_embedding_model"] = os.getenv("EMBEDDING_MODEL")
    return output


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
    trace_event(
        "semantic_normalizer",
        "node_start",
        {"latest_user_text": text, "fallback": fallback},
    )

    skip_llm = (
        os.getenv("GAOKAOLLM_OFFLINE_DETERMINISTIC") == "1"
        or os.getenv("PYTEST_CURRENT_TEST") is not None
        or os.getenv("GAOKAOLLM_SKIP_LLM_SEMANTIC") == "1"
        or not text
    )
    if skip_llm:
        intent = fallback
    else:
        llm = get_structured_chat_model()
        prompt = [
            SystemMessage(
                content=(
                    "你是高考志愿咨询中的意图归一化专员。"
                    "只整理用户明说的需求，不推断隐藏偏好，不输出学校或专业候选。"
                    "只返回 JSON，对象字段为 rewritten_query(str), intent_axes(list[str]), "
                    "ambiguities(list[str]), clarification_hint(str|null)。"
                    "intent_axes 只能包含 major, region, risk, tuition, quality, employment。"
                    "当信息足够继续检索时，clarification_hint 为 null；只有缺少关键条件时才给一句简短澄清。"
                )
            ),
            HumanMessage(content=f"请归一化这条用户输入：{text}"),
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
            raise RuntimeError(
                f"LLM semantic normalization failed: {type(exc).__name__}: {exc}"
            ) from exc

    semantic_output = await refresh_full_context_semantics(state, intent=intent)
    output = {
        "rewritten_query": intent["rewritten_query"],
        "intent_axes": list(intent.get("intent_axes") or []),
        "normalized_intent": intent,
        **semantic_output,
    }
    trace_event("semantic_normalizer", "node_end", output)
    return output
