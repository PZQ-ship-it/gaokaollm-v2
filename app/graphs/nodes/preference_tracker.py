from copy import deepcopy
import math
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
BT_TAU = 3.0
BT_LEARNING_RATE = 0.3


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


def _safe_delta_phi(
    delta_phi: dict[str, Any] | None,
    analysis: FeedbackAnalysis,
) -> dict[str, float]:
    delta: dict[str, float] = {key: 0.0 for key in PREFERENCE_KEYS}
    if isinstance(delta_phi, dict):
        for key in PREFERENCE_KEYS:
            try:
                delta[key] = float(delta_phi.get(key, 0.0))
            except (TypeError, ValueError):
                delta[key] = 0.0
    if any(abs(value) > 1e-9 for value in delta.values()):
        return delta

    target = analysis.target_dimension
    if target in PREFERENCE_KEYS:
        # Compatibility fallback for old tests/threads without a stored Pareto diff.
        delta[target] = 1.0 if analysis.intent == "accept" else -1.0
    else:
        delta["school"] = 1.0
        delta["geo"] = -1.0
    return delta


def apply_feedback_update(
    weights: dict[str, Any] | None,
    variance: dict[str, Any] | None,
    analysis: FeedbackAnalysis,
    delta_phi: dict[str, Any] | None = None,
) -> tuple[dict[str, float], dict[str, float]]:
    old_weights = _normalized(_safe_weights(deepcopy(weights)))
    new_weights = dict(old_weights)
    new_variance = _safe_variance(deepcopy(variance))
    target = analysis.target_dimension

    if analysis.intent == "hesitate":
        # 应对模糊意图的 D-S 理论更新：均值绝对不动，只把不确定性推高。
        if target in PREFERENCE_KEYS:
            new_variance[target] = min(
                1.0,
                float(new_variance.get(target, 1.0)) * 1.2,
            )
        else:
            for key in PREFERENCE_KEYS:
                new_variance[key] = min(
                    1.0,
                    float(new_variance.get(key, 1.0)) * 1.2,
                )
    elif analysis.intent in {"accept", "reject"}:
        delta = _safe_delta_phi(delta_phi, analysis)
        delta_u = sum(old_weights[key] * delta.get(key, 0.0) for key in PREFERENCE_KEYS)
        delta_u = max(-10.0, min(10.0, float(delta_u)))
        p_choose_b = 1.0 / (1.0 + math.exp(-BT_TAU * delta_u))
        label = 1.0 if analysis.intent == "accept" else 0.0

        # Logistic Regression Gradient Ascent based on Bradley-Terry Choice Model
        # (基于随机效用的离散梯度近似)：把用户对 A/B 的选择反馈转化为
        # delta_phi 方向上的对数似然梯度，而不是固定步长的启发式调整。
        for key in PREFERENCE_KEYS:
            new_weights[key] = old_weights[key] + (
                BT_LEARNING_RATE * (label - p_choose_b) * delta.get(key, 0.0)
            )
            new_variance[key] = float(new_variance.get(key, 1.0)) * 0.5
    elif target in PREFERENCE_KEYS:
        new_variance[target] = min(
            1.0,
            float(new_variance.get(target, 1.0)) * 1.2,
        )
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
        state.get("latest_pareto_diff"),
    )

    return {
        "implicit_weights": weights,
        "weight_variance": variance,
        "latest_human_feedback": None,
        "latest_agent_probe_question": None,
        "latest_pareto_diff": None,
    }
