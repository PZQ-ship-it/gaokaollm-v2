from copy import deepcopy
import math
import re
from typing import Any, Literal

from langchain_core.messages import SystemMessage
from langchain_core.runnables import RunnableConfig
from pydantic import BaseModel

from app.core.llm_client import (
    ainvoke_with_timeout,
    get_structured_chat_model,
    structured_timeout_seconds,
)
from app.evaluation.ablation import get_ablation_mode
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
BT_LEARNING_RATE = 0.75


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
    target = analysis.target_dimension
    has_signal = any(abs(value) > 1e-9 for value in delta.values())
    if target in PREFERENCE_KEYS and (
        not has_signal or abs(delta.get(target, 0.0)) < 0.05
    ):
        # When the stored Pareto residual is missing, too small, or does not touch
        # the parsed bottom-line dimension, inject a one-dimensional counterfactual.
        # Rejecting B means B violated that dimension, so delta_B-A is negative.
        delta[target] = 1.0 if analysis.intent == "accept" else -1.0
        return delta
    if has_signal:
        return delta

    if target in PREFERENCE_KEYS:
        # Compatibility fallback for old tests/threads without a stored Pareto diff.
        delta[target] = 1.0 if analysis.intent == "accept" else -1.0
    else:
        delta["school"] = 1.0
        delta["geo"] = -1.0
    return delta


def _target_dimension_from_text(text: str) -> TargetDimension:
    lowered = text.lower()
    if any(
        token in lowered
        for token in ("专业", "专业匹配", "调剂", "major", "computer", "计算机")
    ):
        return "major"
    if any(token in lowered for token in ("学费", "预算", "费用", "tuition", "budget")):
        return "tuition"
    if any(
        token in lowered
        for token in ("地域", "外省", "出省", "跨省", "省内", "geo", "城市")
    ):
        return "geo"
    if any(
        token in lowered for token in ("学校", "985", "211", "层次", "名校", "school")
    ):
        return "school"
    if any(
        token in lowered for token in ("质量", "实力", "排名", "quality", "strength")
    ):
        return "quality"
    return "unknown"


def _tradeoff_cost_dimension(proposal: str) -> TargetDimension:
    patterns = (
        r"(?:牺牲|放宽)\s*([^\s，,。！？?]{1,12})",
        r"牺牲/放宽\s*([^\s，,。！？?]{1,12})",
    )
    for pattern in patterns:
        match = re.search(pattern, proposal)
        if match:
            dimension = _target_dimension_from_text(match.group(1))
            if dimension != "unknown":
                return dimension
    return _target_dimension_from_text(proposal)


def _rule_based_feedback_analysis(
    proposal: str,
    user_reply: str,
) -> FeedbackAnalysis | None:
    reply = user_reply.strip()
    if not reply:
        return FeedbackAnalysis(intent="hesitate", target_dimension="unknown")

    reject_words = (
        "不行",
        "拒绝",
        "绝不",
        "不能接受",
        "不接受",
        "不换",
        "不调剂",
        "不能偏",
        "太远",
        "太贵",
        "不能超",
        "必须压住",
    )
    accept_words = ("接受", "可以", "能接受", "愿意")
    hesitate_words = ("犹豫", "不确定", "再看看", "关系不大", "还想", "保留")
    target = _tradeoff_cost_dimension(proposal)
    reply_target = _target_dimension_from_text(reply)
    if reply_target != "unknown" and any(word in reply for word in reject_words):
        target = reply_target
    elif target == "unknown":
        target = _target_dimension_from_text(reply)

    if any(word in reply for word in reject_words):
        return FeedbackAnalysis(intent="reject", target_dimension=target)
    if any(word in reply for word in hesitate_words):
        return FeedbackAnalysis(intent="hesitate", target_dimension=target)
    if any(word in reply for word in accept_words):
        return FeedbackAnalysis(intent="accept", target_dimension=target)
    return None


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

    rule_result = _rule_based_feedback_analysis(proposal, user_reply)
    if rule_result is not None:
        return rule_result

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
        llm = get_structured_chat_model()
        structured_llm = llm.with_structured_output(FeedbackAnalysis)
        result = await ainvoke_with_timeout(
            structured_llm,
            prompt,
            timeout=structured_timeout_seconds(),
            label="preference_tracker",
        )
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


async def preference_tracker_node(
    state: AgentState,
    config: RunnableConfig | None = None,
) -> dict[str, Any]:
    print("[preference_tracker] updated implicit preference state")
    if get_ablation_mode(config) == "no_tracker":
        return {
            "implicit_weights": dict(state.get("implicit_weights") or {}),
            "weight_variance": dict(state.get("weight_variance") or {}),
            "latest_human_feedback": None,
            "latest_agent_probe_question": None,
            "latest_pareto_diff": None,
        }

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
