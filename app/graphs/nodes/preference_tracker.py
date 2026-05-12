from copy import deepcopy
from typing import Any

from app.schemas.state import (
    DEFAULT_IMPLICIT_WEIGHTS,
    DEFAULT_WEIGHT_VARIANCE,
    AgentState,
)


ACCEPT_TERMS = ("接受", "可以", "行", "能接受")
REJECT_TERMS = ("不行", "拒绝", "绝不", "不能接受")
PREFERENCE_KEYS = ("school", "major", "tuition", "quality", "geo")


def _clamp(value: float, lower: float = 0.01, upper: float = 0.99) -> float:
    return max(lower, min(upper, value))


def _normalized(weights: dict[str, float]) -> dict[str, float]:
    clamped = {key: _clamp(float(weights.get(key, 0.0))) for key in PREFERENCE_KEYS}
    total = sum(clamped.values())
    if total <= 0:
        return dict(DEFAULT_IMPLICIT_WEIGHTS)
    return {key: clamped[key] / total for key in PREFERENCE_KEYS}


def _safe_variance(raw_variance: dict[str, Any]) -> dict[str, float]:
    variance = dict(DEFAULT_WEIGHT_VARIANCE)
    for key, value in raw_variance.items():
        if key not in PREFERENCE_KEYS:
            continue
        try:
            variance[key] = max(0.0, min(1.0, float(value)))
        except (TypeError, ValueError):
            continue
    return variance


def preference_tracker_node(state: AgentState) -> dict[str, Any]:
    print("[preference_tracker] updated implicit preference state")
    user_reply = str(state.get("latest_human_feedback") or "")
    weights = deepcopy(dict(DEFAULT_IMPLICIT_WEIGHTS))
    weights.update(deepcopy(state.get("implicit_weights") or {}))
    variance = _safe_variance(deepcopy(state.get("weight_variance") or {}))

    accepted = any(term in user_reply for term in ACCEPT_TERMS)
    rejected = any(term in user_reply for term in REJECT_TERMS)

    # 基于用户反馈的隐性偏好信念状态（Belief State）后验更新：
    # 本迭代先用硬编码 mock 近似贝叶斯更新方向，后续可替换为真实似然模型。
    if rejected:
        weights["school"] = float(weights.get("school", 0.0)) - 0.1
        weights["geo"] = float(weights.get("geo", 0.0)) + 0.15
        variance["school"] *= 0.5
        variance["geo"] *= 0.5
    elif accepted:
        weights["school"] = float(weights.get("school", 0.0)) + 0.1
        weights["geo"] = float(weights.get("geo", 0.0)) - 0.1
        variance["school"] *= 0.5
        variance["geo"] *= 0.5
    else:
        variance["school"] = min(1.0, variance.get("school", 1.0) * 1.2)
        variance["geo"] = min(1.0, variance.get("geo", 1.0) * 1.2)

    return {
        "implicit_weights": _normalized(weights),
        "weight_variance": variance,
        "latest_human_feedback": None,
    }
