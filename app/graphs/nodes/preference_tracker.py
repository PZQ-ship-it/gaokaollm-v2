from copy import deepcopy
import math
from typing import Any, Literal

from langchain_core.runnables import RunnableConfig
from pydantic import BaseModel

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
FEEDBACK_SIGNAL_ACCEPT = "ACCEPT"
FEEDBACK_SIGNAL_REJECT = "REJECT"
FEEDBACK_SIGNAL_HESITATE = "HESITATE"
FEEDBACK_SIGNALS = {
    FEEDBACK_SIGNAL_ACCEPT,
    FEEDBACK_SIGNAL_REJECT,
    FEEDBACK_SIGNAL_HESITATE,
}
BT_TAU = 3.0
BT_LEARNING_RATE = 0.75
UNCERTAINTY_INFLATION_GAMMA = 0.2
UNCERTAINTY_CONTRACTION_FACTOR = 0.5
UNCERTAINTY_TOUCH_THRESHOLD = 0.05
LEARNING_DELTA_CLIP = 1.0


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
        return _clip_learning_delta(delta)
    if has_signal:
        return _clip_learning_delta(delta)

    if target in PREFERENCE_KEYS:
        # Compatibility fallback for old tests/threads without a stored Pareto diff.
        delta[target] = -1.0
    else:
        delta["school"] = 1.0
        delta["geo"] = -1.0
    return _clip_learning_delta(delta)


def _clip_learning_delta(delta: dict[str, float]) -> dict[str, float]:
    """Project physical Pareto residuals into the BT learning feature space."""

    return {
        key: max(-LEARNING_DELTA_CLIP, min(LEARNING_DELTA_CLIP, float(delta[key])))
        for key in PREFERENCE_KEYS
    }


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


def _feedback_analysis_from_signal(state: AgentState) -> FeedbackAnalysis:
    signal = str(state.get("latest_human_feedback") or "").strip().upper()
    if signal not in FEEDBACK_SIGNALS:
        raise ValueError("feedback_signal_must_be_accept_reject_or_hesitate")
    target = str(state.get("latest_probe_target_dimension") or "").strip()
    target_dimension: TargetDimension = (
        target if target in PREFERENCE_KEYS else "unknown"
    )  # type: ignore[assignment]
    intent_by_signal: dict[str, IntentLabel] = {
        FEEDBACK_SIGNAL_ACCEPT: "accept",
        FEEDBACK_SIGNAL_REJECT: "reject",
        FEEDBACK_SIGNAL_HESITATE: "hesitate",
    }
    return FeedbackAnalysis(
        intent=intent_by_signal[signal],
        target_dimension=target_dimension,
    )


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
    return False


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
        signal = str(state.get("latest_human_feedback") or "").strip().upper()
        if signal not in FEEDBACK_SIGNALS:
            raise ValueError("feedback_signal_must_be_accept_reject_or_hesitate")
        navigation_intent = (
            NAVIGATION_FINALIZE
            if signal == FEEDBACK_SIGNAL_ACCEPT
            else NAVIGATION_CONTINUE
            if signal == FEEDBACK_SIGNAL_REJECT
            else NAVIGATION_UNKNOWN
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

    navigation_intent = NAVIGATION_CONTINUE
    analysis = _feedback_analysis_from_signal(state)
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
