from copy import deepcopy
from typing import Any, Literal

from langchain_core.messages import SystemMessage
from pydantic import BaseModel

from app.core.llm_client import get_chat_model
from app.schemas.state import (
    DEFAULT_IMPLICIT_WEIGHTS,
    DEFAULT_WEIGHT_VARIANCE,
    AgentState,
)


PreferenceKey = Literal["school", "major", "tuition", "quality", "geo"]
IntentLabel = Literal["accept", "reject", "hesitate"]
TargetDimension = Literal["school", "major", "geo", "tuition", "quality", "unknown"]

PREFERENCE_KEYS: tuple[PreferenceKey, ...] = (
    "school",
    "major",
    "tuition",
    "quality",
    "geo",
)


class FeedbackAnalysis(BaseModel):
    intent: IntentLabel
    target_dimension: TargetDimension


def _clamp(value: float, lower: float = 0.05, upper: float = 0.95) -> float:
    return max(lower, min(upper, value))


def _normalized(weights: dict[str, float]) -> dict[str, float]:
    clamped = {key: _clamp(float(weights.get(key, 0.0))) for key in PREFERENCE_KEYS}
    total = sum(clamped.values())
    if total <= 0:
        return dict(DEFAULT_IMPLICIT_WEIGHTS)
    return {key: clamped[key] / total for key in PREFERENCE_KEYS}


def _safe_weights(raw_weights: dict[str, Any] | None) -> dict[str, float]:
    weights = deepcopy(dict(DEFAULT_IMPLICIT_WEIGHTS))
    for key, value in (raw_weights or {}).items():
        if key not in PREFERENCE_KEYS:
            continue
        try:
            weights[key] = float(value)
        except (TypeError, ValueError):
            continue
    return weights


def _safe_variance(raw_variance: dict[str, Any] | None) -> dict[str, float]:
    variance = deepcopy(dict(DEFAULT_WEIGHT_VARIANCE))
    for key, value in (raw_variance or {}).items():
        if key not in PREFERENCE_KEYS:
            continue
        try:
            variance[key] = max(0.0, min(1.0, float(value)))
        except (TypeError, ValueError):
            continue
    return variance


def apply_feedback_update(
    weights: dict[str, Any] | None,
    variance: dict[str, Any] | None,
    analysis: FeedbackAnalysis,
) -> tuple[dict[str, float], dict[str, float]]:
    new_weights = _safe_weights(deepcopy(weights))
    new_variance = _safe_variance(deepcopy(variance))
    target = analysis.target_dimension

    # 这是基于用户反馈的隐性偏好信念状态（Belief State）后验更新：
    # 接受/拒绝反馈会更新对应维度的均值与方差；模糊反馈采用 D-S 理论的
    # ignorance 处理，只提高不确定性，绝不擅自改变权重均值。
    if analysis.intent == "accept" and target in PREFERENCE_KEYS:
        new_weights[target] = float(new_weights.get(target, 0.0)) + 0.15
        new_variance[target] = float(new_variance.get(target, 1.0)) * 0.5
    elif analysis.intent == "reject" and target in PREFERENCE_KEYS:
        new_weights[target] = float(new_weights.get(target, 0.0)) + 0.20
        new_variance[target] = float(new_variance.get(target, 1.0)) * 0.1
    elif analysis.intent == "hesitate" and target in PREFERENCE_KEYS:
        new_variance[target] = min(1.0, float(new_variance.get(target, 1.0)) * 1.2)
    else:
        for key in PREFERENCE_KEYS:
            new_variance[key] = min(1.0, float(new_variance.get(key, 1.0)) * 1.2)

    new_variance = {
        key: max(0.0, min(1.0, float(new_variance.get(key, 1.0))))
        for key in PREFERENCE_KEYS
    }
    return _normalized(new_weights), new_variance


def _latest_message_text(state: AgentState) -> str:
    for message in reversed(state.get("messages", [])):
        content = getattr(message, "content", None)
        if content:
            return str(content)
    return ""


async def analyze_feedback_with_llm(state: AgentState) -> FeedbackAnalysis:
    user_reply = str(state.get("latest_human_feedback") or "")
    proposal = str(state.get("latest_agent_probe_question") or "").strip()
    if not proposal:
        proposal = _latest_message_text(state)

    prompt = [
        SystemMessage(
            content=(
                "你是高考志愿 Agent 的偏好反馈解析器。"
                "请只判断用户对上一轮提案的态度，并输出结构化字段。"
                "intent 只能是 accept、reject、hesitate。"
                "target_dimension 只能是 school、major、geo、tuition、quality、unknown。"
                "如果用户反馈含糊或无法定位维度，使用 hesitate/unknown。"
            )
        ),
        SystemMessage(
            content=(
                f"上一轮系统提案: {proposal}\n"
                f"用户最新反馈: {user_reply}\n"
                "请根据语义判断用户是在接受妥协、拒绝底线，还是仍然犹豫。"
            )
        ),
    ]
    try:
        llm = get_chat_model()
        structured_llm = llm.with_structured_output(FeedbackAnalysis)
        result = await structured_llm.ainvoke(prompt)
        if isinstance(result, FeedbackAnalysis):
            return result
        if isinstance(result, dict):
            return FeedbackAnalysis.model_validate(result)
        return FeedbackAnalysis.model_validate(result)
    except Exception as exc:
        print(
            "[preference_tracker] llm_feedback_parse_failed="
            f"{type(exc).__name__}; using hesitate/unknown"
        )
        return FeedbackAnalysis(intent="hesitate", target_dimension="unknown")


async def preference_tracker_node(state: AgentState) -> dict[str, Any]:
    print("[preference_tracker] updated implicit preference state")
    analysis = await analyze_feedback_with_llm(state)
    weights, variance = apply_feedback_update(
        state.get("implicit_weights"),
        state.get("weight_variance"),
        analysis,
    )

    return {
        "implicit_weights": weights,
        "weight_variance": variance,
        "latest_human_feedback": None,
        "latest_agent_probe_question": None,
    }
