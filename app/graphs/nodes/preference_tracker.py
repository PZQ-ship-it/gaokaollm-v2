from copy import deepcopy
import json
import math
import re
from typing import Any, Literal

from langchain_core.messages import HumanMessage, SystemMessage
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
from gaokaollm_bench.utils.trace import trace_event


PreferenceKey = Literal["school", "major", "tuition", "quality", "geo", "risk"]
IntentLabel = Literal["accept", "reject", "hesitate"]
TargetDimension = Literal[
    "school", "major", "geo", "tuition", "quality", "risk", "unknown"
]

PREFERENCE_KEYS: tuple[PreferenceKey, ...] = (
    "school",
    "major",
    "tuition",
    "quality",
    "geo",
    "risk",
)
QUESTION_KIND_TRADEOFF = "tradeoff"
QUESTION_KIND_NO_SIGNIFICANT_TRADEOFF = "no_significant_tradeoff"
NAVIGATION_FINALIZE = "finalize"
NAVIGATION_CONTINUE = "continue"
NAVIGATION_UNKNOWN = "unknown"
BT_TAU = 3.0
BT_LEARNING_RATE = 0.75
UNCERTAINTY_INFLATION_GAMMA = 0.2
UNCERTAINTY_CONTRACTION_FACTOR = 0.5
UNCERTAINTY_TOUCH_THRESHOLD = 0.05


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
        # The proposal is a relaxation of the target bottom line, so the challenger
        # is worse on that dimension regardless of whether the user accepts it.
        delta[target] = -1.0
        return delta
    if has_signal:
        return delta

    if target in PREFERENCE_KEYS:
        # Compatibility fallback for old tests/threads without a stored Pareto diff.
        delta[target] = -1.0
    else:
        delta["school"] = 1.0
        delta["geo"] = -1.0
    return delta


def _inflate_uncertainty(
    variance: dict[str, float],
    delta_phi: dict[str, Any] | None,
    analysis: FeedbackAnalysis,
) -> dict[str, float]:
    delta = _safe_delta_phi(delta_phi, analysis)
    inflated = dict(variance)
    touched = [key for key in PREFERENCE_KEYS if abs(float(delta.get(key, 0.0))) > 1e-9]
    if not touched and analysis.target_dimension in PREFERENCE_KEYS:
        touched = [analysis.target_dimension]
    for key in touched:
        inflated[key] = min(
            1.0,
            float(inflated.get(key, 1.0))
            + UNCERTAINTY_INFLATION_GAMMA * abs(float(delta.get(key, 1.0))),
        )
    return inflated


def _contract_uncertainty(
    variance: dict[str, float],
    delta_phi: dict[str, Any] | None,
    analysis: FeedbackAnalysis,
) -> dict[str, float]:
    delta = _safe_delta_phi(delta_phi, analysis)
    contracted = dict(variance)
    touched = [
        key
        for key in PREFERENCE_KEYS
        if abs(float(delta.get(key, 0.0))) >= UNCERTAINTY_TOUCH_THRESHOLD
    ]
    if not touched and analysis.target_dimension in PREFERENCE_KEYS:
        touched = [analysis.target_dimension]
    for key in touched:
        contracted[key] = (
            float(contracted.get(key, 1.0)) * UNCERTAINTY_CONTRACTION_FACTOR
        )
    return contracted


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
        token in lowered
        for token in (
            "风险",
            "冲刺",
            "冲一冲",
            "稳妥",
            "保底",
            "求稳",
            "录取弹性",
            "risk",
        )
    ):
        return "risk"
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
        r"牺牲/放宽\s*([^\s，,。！？?]{1,12})",
        r"(?:牺牲|放宽)\s*([^\s，,。！？?]{1,12})",
        r"(?:sacrifice|relax)\s+([a-z_]{2,16})",
    )
    for pattern in patterns:
        match = re.search(pattern, proposal, flags=re.I)
        if match:
            dimension = _target_dimension_from_text(match.group(1))
            if dimension != "unknown":
                return dimension
    return _target_dimension_from_text(proposal)


def _rule_based_feedback_analysis(
    proposal: str,
    user_reply: str,
    default_target_dimension: str | None = None,
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
    default_target = (
        default_target_dimension
        if default_target_dimension in PREFERENCE_KEYS
        else None
    )
    target = default_target or _tradeoff_cost_dimension(proposal)
    reply_target = _target_dimension_from_text(reply)
    if reply_target != "unknown" and any(
        word in reply for word in (*reject_words, *accept_words, *hesitate_words)
    ):
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
        # Thesis alignment: hesitant feedback keeps the posterior mean unchanged
        # and only inflates uncertainty on dimensions touched by Delta Phi.
        new_variance = _inflate_uncertainty(new_variance, delta_phi, analysis)
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
        new_variance = _contract_uncertainty(new_variance, delta, analysis)
    elif target in PREFERENCE_KEYS:
        new_variance = _inflate_uncertainty(new_variance, delta_phi, analysis)
    else:
        new_variance = _inflate_uncertainty(new_variance, delta_phi, analysis)

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


def _candidate_identity(row: dict[str, Any]) -> str:
    return "|".join(
        str(row.get(key) or "")
        for key in (
            "school_id",
            "school_name",
            "major_id",
            "major_name",
            "admission_score_id",
        )
    )


def _first_probe_candidate(state: AgentState, target_dimension: str) -> dict[str, Any]:
    pair = state.get("latest_tradeoff_pair")
    if isinstance(pair, dict):
        option_b = pair.get("option_b")
        if isinstance(option_b, dict) and option_b:
            return dict(option_b)

    opportunities = state.get("pareto_opportunities")
    if not isinstance(opportunities, dict):
        return {}
    key_by_dimension = {
        "tuition": "tuition_value_relax",
        "geo": "major_geo_relax",
        "major": "major_geo_relax",
        "quality": "major_quality_relax",
        "school": "strength_relax",
        "risk": "risk_band_relax",
    }
    ordered_keys = []
    preferred_key = key_by_dimension.get(target_dimension)
    if preferred_key:
        ordered_keys.append(preferred_key)
    rankings = state.get("opportunity_rankings")
    if isinstance(rankings, list):
        ordered_keys.extend(str(item) for item in rankings)
    ordered_keys.extend(str(key) for key in opportunities)
    for key in dict.fromkeys(ordered_keys):
        rows = opportunities.get(key)
        if isinstance(rows, dict):
            rows = [
                row
                for bucket_rows in rows.values()
                if isinstance(bucket_rows, list)
                for row in bucket_rows
            ]
        if not isinstance(rows, list):
            continue
        for row in rows:
            if isinstance(row, dict):
                candidate = dict(row)
                candidate.setdefault("_opportunity_key", key)
                return candidate
    return {}


def _accepted_relaxations_update(
    state: AgentState,
    analysis: FeedbackAnalysis,
) -> list[dict[str, Any]]:
    current = [
        dict(item)
        for item in (state.get("accepted_relaxations") or [])
        if isinstance(item, dict)
    ]
    if analysis.intent != "accept" or analysis.target_dimension == "unknown":
        return current
    candidate = _first_probe_candidate(state, analysis.target_dimension)
    accepted = {
        "dimension": analysis.target_dimension,
        "candidate": candidate,
        "candidate_identity": _candidate_identity(candidate) if candidate else "",
    }
    if analysis.target_dimension == "tuition" and candidate.get("tuition") is not None:
        accepted["accepted_budget"] = candidate.get("tuition")
    seen = {
        (
            str(item.get("dimension") or ""),
            str(item.get("candidate_identity") or ""),
        )
        for item in current
    }
    key = (
        str(accepted.get("dimension") or ""),
        str(accepted.get("candidate_identity") or ""),
    )
    if key not in seen:
        current.append(accepted)
    return current


def _navigation_intent_from_reply(reply: str) -> str:
    text = str(reply or "").strip()
    if not text:
        return NAVIGATION_UNKNOWN
    if any(
        token in text
        for token in ("最终", "终局", "推荐", "看结果", "直接看", "不用再问")
    ):
        return NAVIGATION_FINALIZE
    if any(
        token in text
        for token in ("换", "继续", "再查", "再看", "另一个", "其他方向", "方向")
    ):
        return NAVIGATION_CONTINUE
    if any(token in text for token in ("愿意", "可以", "接受")):
        return NAVIGATION_CONTINUE
    return NAVIGATION_UNKNOWN


def _is_pure_navigation_reply(reply: str, navigation_intent: str) -> bool:
    text = str(reply or "").strip()
    if not text:
        return False
    if navigation_intent == NAVIGATION_FINALIZE:
        return True
    if navigation_intent != NAVIGATION_CONTINUE:
        return False
    navigation_tokens = ("换", "继续", "再查", "再看", "另一个", "其他方向", "方向")
    preference_tokens = (
        "接受",
        "愿意",
        "可以接受",
        "不能接受",
        "不接受",
        "拒绝",
        "不行",
        "犹豫",
        "不确定",
    )
    return any(token in text for token in navigation_tokens) and not any(
        token in text for token in preference_tokens
    )


def _current_probe_key(state: AgentState) -> str:
    probe_plan = state.get("probe_plan") or []
    if not probe_plan or not isinstance(probe_plan[0], dict):
        return ""
    first = probe_plan[0]
    probe = str(first.get("probe") or first.get("probe_name") or "").strip()
    return probe.removeprefix("probe_")


def _blocked_dimensions_update(state: AgentState) -> list[str]:
    current = [
        str(item)
        for item in (state.get("factual_blocked_dimensions") or [])
        if str(item).strip()
    ]
    target = str(state.get("latest_probe_target_dimension") or "").strip()
    targets = [target] if target in PREFERENCE_KEYS else []
    if _current_probe_key(state) == "major_geo_relax" and target in {"major", "geo"}:
        targets = ["major", "geo"]
    for item in targets:
        if item not in current:
            current.append(item)
    return current


def _should_block_current_dimension(
    state: AgentState,
    analysis: FeedbackAnalysis,
    navigation_intent: str,
) -> bool:
    target = str(state.get("latest_probe_target_dimension") or "").strip()
    if target not in PREFERENCE_KEYS:
        return False
    if analysis.intent == "reject":
        return True
    if navigation_intent == NAVIGATION_CONTINUE and analysis.intent != "accept":
        return True
    return False


async def analyze_feedback_with_llm(state: AgentState) -> FeedbackAnalysis:
    user_reply = str(state.get("latest_human_feedback") or "")
    proposal = str(state.get("latest_agent_probe_question") or "").strip()
    if not proposal:
        proposal = _latest_message_text(state)

    rule_result = _rule_based_feedback_analysis(
        proposal,
        user_reply,
        default_target_dimension=state.get("latest_probe_target_dimension"),
    )
    if rule_result is not None:
        return rule_result

    prompt = [
        SystemMessage(
            content=(
                "你是高考志愿咨询中的反馈判断员。"
                "只判断用户对上一轮取舍提问的态度，不评价候选好坏，不生成新建议。"
                "intent 只能是 accept、reject、hesitate。"
                "target_dimension 只能是 school、major、geo、tuition、quality、risk、unknown。"
                "如果用户只是要求换方向或直接看结果，应使用 hesitate/unknown。"
                "请输出符合结构化字段的结果。"
            )
        ),
        HumanMessage(
            content=(
                "请判断这次反馈语义：\n"
                + json.dumps(
                    {
                        "上一轮提问": proposal,
                        "用户反馈": user_reply,
                    },
                    ensure_ascii=False,
                    default=str,
                )
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
        raise RuntimeError(
            f"LLM feedback parsing failed: {type(exc).__name__}: {exc}"
        ) from exc


async def preference_tracker_node(
    state: AgentState,
    config: RunnableConfig | None = None,
) -> dict[str, Any]:
    print("[preference_tracker] updated implicit preference state")
    trace_event(
        "preference_tracker",
        "node_start",
        {
            "ablation_mode": get_ablation_mode(config),
            "latest_human_feedback": state.get("latest_human_feedback"),
            "latest_pareto_diff": state.get("latest_pareto_diff"),
            "weights_before": state.get("implicit_weights"),
            "variance_before": state.get("weight_variance"),
        },
    )
    if get_ablation_mode(config) == "no_tracker":
        output = {
            "implicit_weights": dict(state.get("implicit_weights") or {}),
            "weight_variance": dict(state.get("weight_variance") or {}),
            "latest_human_feedback": None,
            "latest_agent_probe_question": None,
            "latest_pareto_diff": None,
            "latest_question_kind": state.get("latest_question_kind"),
            "latest_probe_target_dimension": state.get("latest_probe_target_dimension"),
            "latest_tradeoff_pair": state.get("latest_tradeoff_pair"),
            "feedback_analysis": None,
            "accepted_relaxations": state.get("accepted_relaxations") or [],
            "factual_blocked_dimensions": state.get("factual_blocked_dimensions") or [],
            "force_final_recommendation": bool(state.get("force_final_recommendation")),
            "navigation_intent": state.get("navigation_intent"),
        }
        trace_event("preference_tracker", "node_end", {"skipped": True, **output})
        return output

    question_kind = str(state.get("latest_question_kind") or "").strip()
    if question_kind == QUESTION_KIND_NO_SIGNIFICANT_TRADEOFF:
        navigation_intent = _navigation_intent_from_reply(
            str(state.get("latest_human_feedback") or "")
        )
        output = {
            "implicit_weights": dict(state.get("implicit_weights") or {}),
            "weight_variance": dict(state.get("weight_variance") or {}),
            "latest_human_feedback": None,
            "latest_agent_probe_question": None,
            "latest_pareto_diff": None,
            "latest_question_kind": None,
            "latest_probe_target_dimension": None,
            "latest_tradeoff_pair": None,
            "feedback_analysis": {
                "intent": "hesitate",
                "target_dimension": "unknown",
            },
            "accepted_relaxations": state.get("accepted_relaxations") or [],
            "factual_blocked_dimensions": _blocked_dimensions_update(state),
            "force_final_recommendation": navigation_intent == NAVIGATION_FINALIZE,
            "navigation_intent": navigation_intent,
        }
        trace_event(
            "preference_tracker",
            "node_end",
            {
                "no_significant_tradeoff": True,
                **output,
            },
        )
        return output

    navigation_intent = _navigation_intent_from_reply(
        str(state.get("latest_human_feedback") or "")
    )
    pure_navigation = _is_pure_navigation_reply(
        str(state.get("latest_human_feedback") or ""),
        navigation_intent,
    )
    if pure_navigation:
        analysis = FeedbackAnalysis(intent="hesitate", target_dimension="unknown")
        weights = dict(state.get("implicit_weights") or DEFAULT_IMPLICIT_WEIGHTS)
        variance = dict(state.get("weight_variance") or DEFAULT_WEIGHT_VARIANCE)
    else:
        analysis = await analyze_feedback_with_llm(state)
        weights, variance = apply_feedback_update(
            state.get("implicit_weights"),
            state.get("weight_variance"),
            analysis,
            state.get("latest_pareto_diff"),
        )
    blocked_dimensions = state.get("factual_blocked_dimensions") or []
    if _should_block_current_dimension(state, analysis, navigation_intent):
        blocked_dimensions = _blocked_dimensions_update(state)

    output = {
        "implicit_weights": weights,
        "weight_variance": variance,
        "latest_human_feedback": None,
        "latest_agent_probe_question": None,
        "latest_pareto_diff": state.get("latest_pareto_diff"),
        "latest_question_kind": None,
        "latest_probe_target_dimension": None,
        "latest_tradeoff_pair": state.get("latest_tradeoff_pair"),
        "feedback_analysis": analysis.model_dump()
        if hasattr(analysis, "model_dump")
        else dict(analysis),
        "accepted_relaxations": _accepted_relaxations_update(state, analysis),
        "factual_blocked_dimensions": blocked_dimensions,
        "force_final_recommendation": navigation_intent == NAVIGATION_FINALIZE,
        "navigation_intent": navigation_intent,
    }
    trace_event(
        "preference_tracker",
        "node_end",
        {
            "analysis": analysis.model_dump()
            if hasattr(analysis, "model_dump")
            else dict(analysis),
            **output,
        },
    )
    return output
