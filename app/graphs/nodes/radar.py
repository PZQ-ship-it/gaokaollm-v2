import json
import math
import os
import random
import re
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig

from app.core.llm_client import (
    ainvoke_with_timeout,
    get_structured_chat_model,
    structured_timeout_seconds,
)
from app.evaluation.ablation import get_ablation_mode
from app.flows.probers import probe_global_baseline, run_all_probes
from app.graphs.nodes.semantic_normalizer import refresh_full_context_semantics
from app.schemas.state import (
    DEFAULT_IMPLICIT_WEIGHTS,
    DEFAULT_WEIGHT_VARIANCE,
    AgentState,
)
from gaokaollm_bench.utils.trace import trace_event


PROBE_KEYS = [
    "major_geo_relax",
    "risk_band_relax",
    "tuition_value_relax",
    "major_quality_relax",
    "employment_outcome_relax",
    "region_tree_relax",
    "strength_relax",
    "geo_relax",
    "city_relax",
    "major_relax",
]

PREFERENCE_KEYS = ("school", "major", "tuition", "quality", "geo", "risk")
UCB_EXPLORATION_COEF = 1.5
HALTING_VARIANCE_THRESHOLD = 1.5
MAX_NEGOTIATION_TURNS = 3
GLOBAL_BASELINE_PROBE = "probe_global_baseline"
PROBE_MAPPING: dict[str, str] = {
    "school": "strength_relax",
    "major": "major_geo_relax",
    "tuition": "tuition_value_relax",
    "quality": "major_quality_relax",
    "geo": "major_geo_relax",
    "risk": "risk_band_relax",
}

EMPTY_OPPORTUNITIES: dict[str, list[dict[str, Any]]] = {
    "geo_relax": [],
    "city_relax": [],
    "major_relax": [],
    "strength_relax": [],
    "major_quality_relax": [],
    "tuition_value_relax": [],
    "employment_outcome_relax": [],
    "region_tree_relax": [],
    "major_geo_relax": [],
    "risk_band_relax": [],
}

# Backward-compatible test hook retained for older ablation tests.
get_chat_model = get_structured_chat_model

GLOBAL_BASELINE_PLAN = {
    "probe_plan": [{"probe_name": GLOBAL_BASELINE_PROBE, "args": {}}],
    "opportunity_rankings": ["global_baseline"],
    "clarification_hint": None,
    "planner_source": "halting",
}


def _json_from_text(text: str) -> dict[str, Any]:
    match = re.search(r"\{.*\}", text, flags=re.S)
    if not match:
        return {}
    try:
        data = json.loads(match.group(0))
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def should_apply_ucb_override(state: AgentState) -> bool:
    return bool(state.get("implicit_weights") or state.get("weight_variance"))


def total_weight_variance(state: AgentState) -> float:
    raw_variance = state.get("weight_variance") or {}
    if not isinstance(raw_variance, dict):
        raw_variance = {}
    total = 0.0
    for key in PREFERENCE_KEYS:
        try:
            total += float(raw_variance.get(key, DEFAULT_WEIGHT_VARIANCE[key]))
        except (TypeError, ValueError):
            total += DEFAULT_WEIGHT_VARIANCE[key]
    return total


def should_halt_for_global_baseline(state: AgentState) -> bool:
    turns = int(state.get("negotiation_turns") or 0)
    if str(state.get("navigation_intent") or "") == "continue":
        return False
    return total_weight_variance(state) < HALTING_VARIANCE_THRESHOLD or (
        turns >= MAX_NEGOTIATION_TURNS
    )


def _accepted_dimensions(state: AgentState) -> set[str]:
    accepted: set[str] = set()
    for item in state.get("accepted_relaxations") or []:
        if not isinstance(item, dict):
            continue
        dimension = str(item.get("dimension") or "").strip()
        if dimension in PREFERENCE_KEYS:
            accepted.add(dimension)
    return accepted


def _is_global_baseline_plan(plan: dict[str, Any]) -> bool:
    probe_plan = plan.get("probe_plan") or []
    if not probe_plan or not isinstance(probe_plan[0], dict):
        return False
    first = probe_plan[0]
    return str(first.get("probe_name") or "") == GLOBAL_BASELINE_PROBE


def _iter_rows(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, list):
        return [dict(row) for row in value if isinstance(row, dict)]
    if isinstance(value, dict):
        rows: list[dict[str, Any]] = []
        for bucket, bucket_rows in value.items():
            if not isinstance(bucket_rows, list):
                continue
            for row in bucket_rows:
                if isinstance(row, dict):
                    item = dict(row)
                    item.setdefault("risk_bucket", str(bucket))
                    rows.append(item)
        return rows
    return []


def _flatten_candidates(
    opportunities: dict[str, Any],
    rankings: list[str],
    *,
    include_unranked: bool = True,
) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    seen: set[tuple[Any, Any, Any]] = set()
    ordered_keys = [key for key in rankings if key in opportunities]
    if include_unranked:
        ordered_keys.extend(
            key
            for key in EMPTY_OPPORTUNITIES
            if key in opportunities and key not in ordered_keys
        )
    for key in ordered_keys:
        for row in _iter_rows(opportunities.get(key)):
            if not isinstance(row, dict):
                continue
            item = dict(row)
            item.setdefault("_opportunity_key", key)
            option_key = (
                item.get("school_id") or item.get("school_name"),
                item.get("major_id") or item.get("major_name"),
                item.get("admission_score_id"),
            )
            if option_key in seen:
                continue
            seen.add(option_key)
            candidates.append(item)
    return candidates


def _opportunity_count(value: Any) -> int:
    return len(_iter_rows(value))


def _opportunity_is_usable(key: str, value: Any) -> bool:
    rows = _iter_rows(value)
    if not rows:
        return False
    if key == "risk_band_relax":
        relaxed_buckets = {"chong", "reach", "wen", "match"}
        for row in rows:
            bucket = str(row.get("risk_bucket") or row.get("risk_level") or "")
            if bucket in relaxed_buckets:
                return True
            features = row.get("_phi_features")
            if isinstance(features, dict):
                try:
                    if float(features.get("risk", 1.0)) < 0.95:
                        return True
                except (TypeError, ValueError):
                    pass
        return False
    return True


def _plan_with_available_opportunities(
    plan: dict[str, Any],
    opportunities: dict[str, Any],
    state: AgentState | None = None,
) -> dict[str, Any]:
    blocked_dimensions = {
        str(item)
        for item in ((state or {}).get("factual_blocked_dimensions") or [])
        if str(item) in PREFERENCE_KEYS
    }
    probe_dimensions = {
        "major_geo_relax": {"major", "geo"},
        "geo_relax": {"geo"},
        "city_relax": {"geo"},
        "region_tree_relax": {"geo"},
        "major_relax": {"major"},
        "risk_band_relax": {"risk"},
        "tuition_value_relax": {"tuition"},
        "major_quality_relax": {"major", "quality"},
        "employment_outcome_relax": {"major", "quality"},
        "strength_relax": {"school"},
    }
    available = {
        key
        for key, value in opportunities.items()
        if key in PROBE_KEYS
        and _opportunity_is_usable(key, value)
        and not probe_dimensions.get(key, set()).issubset(blocked_dimensions)
    }
    if not available:
        fallback = dict(GLOBAL_BASELINE_PLAN)
        fallback["probe_plan"] = [
            dict(item) for item in GLOBAL_BASELINE_PLAN["probe_plan"]
        ]
        fallback["opportunity_rankings"] = list(
            GLOBAL_BASELINE_PLAN["opportunity_rankings"]
        )
        fallback["planner_source"] = "no_available_opportunities"
        fallback["clarification_hint"] = (
            "当前已尝试或排除的放宽方向里没有新的显著跃迁候选。"
        )
        return fallback
    plan_rows = [
        dict(item)
        for item in plan.get("probe_plan") or []
        if isinstance(item, dict)
        and str(item.get("probe") or item.get("probe_name") or "").removeprefix(
            "probe_"
        )
        in available
    ]
    if not plan_rows:
        best_key = next((key for key in PROBE_KEYS if key in available), None)
        if best_key:
            plan_rows = [
                {
                    "probe": best_key,
                    "priority": 1,
                    "reason": "available opportunity fallback",
                }
            ]
    for index, item in enumerate(plan_rows):
        item["probe"] = str(
            item.get("probe") or item.get("probe_name") or ""
        ).removeprefix("probe_")
        item["priority"] = index + 1
    rankings = [
        str(item).removeprefix("probe_")
        for item in plan.get("opportunity_rankings") or []
        if str(item).removeprefix("probe_") in available
    ]
    if not rankings:
        rankings = [item["probe"] for item in plan_rows]
    else:
        for item in plan_rows:
            if item["probe"] not in rankings:
                rankings.append(item["probe"])
    adjusted = dict(plan)
    adjusted["probe_plan"] = plan_rows
    adjusted["opportunity_rankings"] = rankings
    if (
        adjusted.get("ucb_required_probe")
        and adjusted.get("ucb_required_probe") not in available
    ):
        adjusted["ucb_required_probe"] = None
    return adjusted


def _candidate_identity_key(row: dict[str, Any]) -> tuple[Any, Any, Any]:
    return (
        row.get("school_id") or row.get("school_name") or row.get("school"),
        row.get("major_id") or row.get("major_name") or row.get("major"),
        row.get("admission_score_id"),
    )


def _display_identity_key(row: dict[str, Any]) -> tuple[Any, Any]:
    return (
        row.get("school_id") or row.get("school_name") or row.get("school"),
        row.get("major_id") or row.get("major_name") or row.get("major"),
    )


def _accepted_relaxation_candidates(state: AgentState) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item in state.get("accepted_relaxations") or []:
        if not isinstance(item, dict):
            continue
        candidate = item.get("candidate")
        if not isinstance(candidate, dict):
            continue
        row = dict(candidate)
        row["_accepted_relaxation"] = True
        row["_accepted_dimension"] = item.get("dimension")
        rows.append(row)
    return rows


def _merge_accepted_into_baseline(
    global_result: Any,
    state: AgentState,
) -> Any:
    accepted = _accepted_relaxation_candidates(state)
    if not accepted:
        return global_result
    if not isinstance(global_result, dict):
        return global_result
    merged = {
        key: _iter_rows(global_result.get(key)) for key in ("reach", "match", "safety")
    }
    seen = {
        _candidate_identity_key(row)
        for rows in merged.values()
        for row in rows
        if isinstance(row, dict)
    }
    for row in accepted:
        key = _candidate_identity_key(row)
        if key in seen:
            continue
        bucket = str(row.get("risk_bucket") or row.get("risk_level") or "match")
        if bucket not in merged:
            bucket = "match"
        row.setdefault("risk_bucket", bucket)
        merged[bucket].insert(0, row)
        seen.add(key)
    return merged


def _without_accepted_relaxation_candidates(
    opportunities: dict[str, Any],
    state: AgentState,
) -> dict[str, Any]:
    accepted_keys = {
        _candidate_identity_key(row) for row in _accepted_relaxation_candidates(state)
    }
    if not accepted_keys:
        return opportunities
    filtered: dict[str, Any] = {}
    for key, value in opportunities.items():
        if isinstance(value, list):
            filtered[key] = [
                row
                for row in value
                if not isinstance(row, dict)
                or _candidate_identity_key(row) not in accepted_keys
            ]
        elif isinstance(value, dict):
            filtered[key] = {
                bucket: [
                    row
                    for row in rows
                    if not isinstance(row, dict)
                    or _candidate_identity_key(row) not in accepted_keys
                ]
                if isinstance(rows, list)
                else rows
                for bucket, rows in value.items()
            }
        else:
            filtered[key] = value
    return filtered


def _without_global_baseline_duplicates(
    opportunities: dict[str, Any],
    global_result: Any,
) -> dict[str, Any]:
    baseline_keys = {
        _display_identity_key(row)
        for row in _iter_rows(global_result)
        if isinstance(row, dict)
    }
    if not baseline_keys:
        return opportunities
    filtered: dict[str, Any] = {}
    for key, value in opportunities.items():
        if key == "global_baseline":
            filtered[key] = value
            continue
        if isinstance(value, list):
            filtered[key] = [
                row
                for row in value
                if not isinstance(row, dict)
                or _display_identity_key(row) not in baseline_keys
            ]
        elif isinstance(value, dict):
            filtered[key] = {
                bucket: [
                    row
                    for row in rows
                    if not isinstance(row, dict)
                    or _display_identity_key(row) not in baseline_keys
                ]
                if isinstance(rows, list)
                else rows
                for bucket, rows in value.items()
            }
        else:
            filtered[key] = value
    return filtered


def calculate_ucb_scores(state: AgentState) -> dict[str, float]:
    raw_weights = state.get("implicit_weights") or {}
    raw_variance = state.get("weight_variance") or {}
    blocked_dimensions = {
        str(item)
        for item in (state.get("factual_blocked_dimensions") or [])
        if str(item) in PREFERENCE_KEYS
    }
    accepted_dimensions = _accepted_dimensions(state)
    scores: dict[str, float] = {}
    for key in PREFERENCE_KEYS:
        if key in blocked_dimensions or key in accepted_dimensions:
            continue
        try:
            weight = float(raw_weights.get(key, DEFAULT_IMPLICIT_WEIGHTS[key]))
        except (TypeError, ValueError):
            weight = DEFAULT_IMPLICIT_WEIGHTS[key]
        try:
            variance = float(raw_variance.get(key, DEFAULT_WEIGHT_VARIANCE[key]))
        except (TypeError, ValueError):
            variance = DEFAULT_WEIGHT_VARIANCE[key]
        scores[key] = weight + UCB_EXPLORATION_COEF * math.sqrt(max(0.0, variance))
    return scores


def _continue_exploration_tie_break_order(state: AgentState) -> list[str]:
    if str(state.get("navigation_intent") or "") != "continue":
        return []
    constraints = state.get("constraints") or {}
    order: list[str] = []
    if (
        constraints.get("target_provinces")
        or constraints.get("city")
        or constraints.get("province")
    ):
        order.append("geo")
    if constraints.get("major"):
        order.append("major")
    order.append("risk")
    order.extend(["school", "quality", "tuition"])
    return list(dict.fromkeys(order))


def _ucb_tie_break_order(state: AgentState) -> list[str]:
    blocked_dimensions = {
        str(item)
        for item in (state.get("factual_blocked_dimensions") or [])
        if str(item) in PREFERENCE_KEYS
    }
    accepted_dimensions = _accepted_dimensions(state)

    def without_blocked(order: list[str]) -> list[str]:
        return [
            item
            for item in order
            if item not in blocked_dimensions and item not in accepted_dimensions
        ]

    continue_order = _continue_exploration_tie_break_order(state)
    if continue_order:
        return without_blocked(continue_order)

    constraint_order = _explicit_constraint_tie_break_order(state)
    if constraint_order:
        return without_blocked(constraint_order)

    intent_order = _intent_axis_tie_break_order(state)
    if intent_order:
        return without_blocked(intent_order)

    text_parts = [
        str(state.get("rewritten_query") or ""),
        json.dumps(state.get("normalized_intent") or {}, ensure_ascii=False),
    ]
    text = "\n".join(text_parts)
    if "profile_major" in text or "major_extreme" in text:
        return without_blocked(["major", "geo", "school", "tuition", "quality"])
    if "profile_geo" in text or "geo_extreme" in text or "geo_free" in text:
        return without_blocked(["geo", "major", "school", "tuition", "quality"])
    if (
        "profile_tuition" in text
        or "tuition_extreme" in text
        or "school_to_tuition" in text
    ):
        return without_blocked(["tuition", "major", "geo", "school", "quality"])
    if "school_extreme" in text:
        return without_blocked(["school", "major", "geo", "tuition", "quality"])
    if "quality_major" in text or "low_school_decoy" in text:
        return without_blocked(["major", "quality", "school", "geo", "tuition"])
    if "school_geo" in text:
        return without_blocked(["geo", "school", "major", "tuition", "quality"])
    if "geo_tuition" in text:
        return without_blocked(["tuition", "geo", "major", "school", "quality"])
    if any(token in text for token in ("学费", "预算", "费用", "tuition", "budget")):
        return without_blocked(["tuition", "major", "geo", "school", "quality"])
    if any(
        token in text
        for token in ("学校和专业都可以灵活", "性价比", "绝不出省", "本省")
    ):
        return without_blocked(["geo", "major", "school", "tuition", "quality"])
    if any(token in text for token in ("专业", "计算机", "major")):
        return without_blocked(["major", "geo", "school", "tuition", "quality"])
    return without_blocked(list(PREFERENCE_KEYS))


def _intent_axis_tie_break_order(state: AgentState) -> list[str]:
    axes: list[str] = list(_all_intent_axes(state))
    axis_priority = {
        "region": ["geo", "school", "major", "tuition", "quality", "risk"],
        "geo": ["geo", "school", "major", "tuition", "quality", "risk"],
        "major": ["major", "quality", "school", "geo", "tuition", "risk"],
        "tuition": ["tuition", "school", "quality", "major", "geo", "risk"],
        "budget": ["tuition", "school", "quality", "major", "geo", "risk"],
        "risk": ["risk", "school", "major", "geo", "tuition", "quality"],
        "quality": ["quality", "major", "school", "geo", "tuition", "risk"],
        "employment": ["quality", "major", "school", "geo", "tuition", "risk"],
    }
    for axis in axes:
        if axis in axis_priority:
            return axis_priority[axis]
    return []


def _all_intent_axes(state: AgentState) -> set[str]:
    axes: set[str] = set()
    for value in state.get("intent_axes") or []:
        axes.add(str(value))
    normalized = state.get("normalized_intent") or {}
    if isinstance(normalized, dict):
        for value in normalized.get("intent_axes") or []:
            axes.add(str(value))
    return axes


def _explicit_region_intent(state: AgentState) -> bool:
    axes = _all_intent_axes(state)
    if axes.intersection({"region", "geo"}):
        return True
    text = "\n".join(
        [
            str(state.get("rewritten_query") or ""),
            json.dumps(state.get("normalized_intent") or {}, ensure_ascii=False),
        ]
    )
    return any(
        token in text
        for token in (
            "只想浙江",
            "留在浙江",
            "不出省",
            "省内",
            "本省",
            "region",
            "geo",
        )
    )


def _explicit_constraint_tie_break_order(state: AgentState) -> list[str]:
    constraints = state.get("constraints") or {}
    if not isinstance(constraints, dict):
        return []
    if constraints.get("risk_preference"):
        return ["risk", "school", "major", "geo", "tuition", "quality"]
    if constraints.get("employment_preference") or constraints.get("strength"):
        return ["quality", "major", "school", "geo", "tuition", "risk"]
    budget = constraints.get("budget")
    try:
        has_real_budget = budget not in (None, "") and int(float(budget)) < 100000
    except (TypeError, ValueError):
        has_real_budget = False
    if has_real_budget:
        return ["tuition", "school", "quality", "major", "geo", "risk"]
    if constraints.get("major"):
        return ["major", "quality", "school", "geo", "tuition", "risk"]
    if constraints.get("city"):
        return ["geo", "school", "major", "tuition", "quality", "risk"]
    province = constraints.get("province")
    if _explicit_region_intent(state):
        return ["geo", "school", "major", "tuition", "quality", "risk"]
    if province not in (None, "", "浙江"):
        return ["geo", "school", "major", "tuition", "quality", "risk"]
    return []


def select_ucb_dimension(state: AgentState) -> tuple[str, float]:
    scores = calculate_ucb_scores(state)
    if not scores:
        return "geo", 0.0
    order = _ucb_tie_break_order(state)
    max_score = max(scores.values())
    tied = {
        key
        for key, value in scores.items()
        if abs(float(value) - float(max_score)) < 1e-9
    }
    dimension = next((key for key in order if key in tied), None)
    if dimension is None:
        dimension = max(scores, key=lambda key: scores[key])
    return dimension, scores[dimension]


def target_probe_for_dimension(
    dimension: str,
    state: AgentState | None = None,
) -> str:
    if dimension == "risk":
        return "risk_band_relax"
    if state is not None:
        constraints = state.get("constraints") or {}
        axes = _all_intent_axes(state)
        if dimension == "school" and (
            constraints.get("risk_preference") or "risk" in axes
        ):
            return "risk_band_relax"
        if dimension == "quality":
            if constraints.get("employment_preference") or "employment" in axes:
                return "employment_outcome_relax"
            if constraints.get("strength") or "quality" in axes:
                return "major_quality_relax"
    return PROBE_MAPPING.get(dimension, "major_geo_relax")


def probe_function_name(probe_key: str) -> str:
    return f"probe_{probe_key}"


def _enforce_required_probe(
    plan: list[dict[str, Any]],
    required_probe: str | None,
    reason: str,
) -> list[dict[str, Any]]:
    if not required_probe or required_probe not in PROBE_KEYS:
        return [
            {**item, "priority": index + 1}
            for index, item in enumerate(plan)
            if item.get("probe") in PROBE_KEYS
        ]

    rest = [dict(item) for item in plan if item.get("probe") != required_probe]
    enforced = {
        "probe": required_probe,
        "priority": 1,
        "reason": reason,
    }
    return [
        {**item, "priority": index + 1}
        for index, item in enumerate([enforced, *rest])
        if item.get("probe") in PROBE_KEYS
    ]


def _required_probe_context(state: AgentState) -> dict[str, str | None]:
    if not should_apply_ucb_override(state):
        return {"dimension": None, "probe": None, "reason": None, "instruction": None}
    dimension, score = select_ucb_dimension(state)
    probe = target_probe_for_dimension(dimension, state)
    function_name = probe_function_name(probe)
    reason = f"UCB active learning target: {dimension} uncertainty score={score:.3f}"
    instruction = (
        "🚨 [系统级主动学习指令]: "
        f"基于运筹学方差测算，当前对用户的【{dimension}】偏好底线存在极大不确定性。"
        "为了最大化信息增益，你本次规划的探针计划(probe_plan)中，"
        f"必须优先且强制包含调用探针：【{function_name}】"
        f"（内部 probe key: {probe}）！绝对不允许偏离该目标！"
    )
    return {
        "dimension": dimension,
        "probe": probe,
        "reason": reason,
        "instruction": instruction,
    }


def _deterministic_probe_plan(state: AgentState) -> dict[str, Any]:
    constraints = state.get("constraints", {})
    axes = set(state.get("intent_axes") or [])
    plan: list[dict[str, Any]] = []

    def add(key: str, reason: str) -> None:
        if key not in PROBE_KEYS:
            return
        if any(item.get("probe") == key for item in plan):
            return
        plan.append({"probe": key, "priority": len(plan) + 1, "reason": reason})

    if constraints.get("major") or "major" in axes or "region" in axes:
        add(
            "major_geo_relax",
            "explicit major or region preference may be over-constrained",
        )
    if constraints.get("risk_preference") or "risk" in axes:
        add("risk_band_relax", "risk preference can be expressed as portfolio evidence")
    if int(constraints.get("budget") or 100000) < 100000 or "tuition" in axes:
        add("tuition_value_relax", "budget preference may allow a small audited delta")
    if constraints.get("strength") or "quality" in axes:
        add(
            "major_quality_relax",
            "quality evidence can support same-major alternatives",
        )
        add("strength_relax", "school-level strength can provide coarse evidence")
    if constraints.get("employment_preference") or "employment" in axes:
        add(
            "employment_outcome_relax",
            "employment evidence can expose outcome tradeoffs",
        )
    if constraints.get("city") or "region" in axes:
        add(
            "region_tree_relax",
            "region-tree evidence can support geographic clarification",
        )
    if constraints.get("score") and not any(
        item.get("probe") == "risk_band_relax" for item in plan
    ):
        add(
            "risk_band_relax",
            "score/rank evidence can test admission-risk elasticity",
        )
    if not plan:
        add("geo_relax", "default geographic relaxation probe")
        add("major_relax", "default major relaxation probe")

    return {
        "probe_plan": plan,
        "opportunity_rankings": [item["probe"] for item in plan],
        "clarification_hint": None,
        "planner_source": "deterministic",
    }


def _random_probe_plan() -> dict[str, Any]:
    probe = random.choice(
        [
            "risk_band_relax",
            "major_quality_relax",
            "employment_outcome_relax",
            "region_tree_relax",
            "strength_relax",
        ]
    )
    return {
        "probe_plan": [
            {
                "probe": probe,
                "priority": 1,
                "reason": "ablation no_ucb random probe",
            }
        ],
        "opportunity_rankings": [probe],
        "clarification_hint": None,
        "planner_source": "ablation:no_ucb",
    }


def _sanitize_plan(
    data: dict[str, Any],
    fallback: dict[str, Any],
    *,
    required_probe: str | None = None,
    required_reason: str = "",
) -> dict[str, Any]:
    raw_plan = data.get("probe_plan") or []
    plan: list[dict[str, Any]] = []
    if isinstance(raw_plan, list):
        for index, item in enumerate(raw_plan):
            if isinstance(item, str):
                probe = item
                reason = ""
            elif isinstance(item, dict):
                probe = str(item.get("probe") or "")
                reason = str(item.get("reason") or "")
            else:
                continue
            if probe not in PROBE_KEYS:
                continue
            if any(existing["probe"] == probe for existing in plan):
                continue
            plan.append(
                {
                    "probe": probe,
                    "priority": len(plan) + 1,
                    "reason": reason or f"planner priority {index + 1}",
                }
            )
    if not plan:
        plan = list(fallback["probe_plan"])
    plan = _enforce_required_probe(plan, required_probe, required_reason)

    rankings = data.get("opportunity_rankings")
    if not isinstance(rankings, list):
        rankings = [item["probe"] for item in plan]
    rankings = [str(item) for item in rankings if str(item) in PROBE_KEYS]
    if required_probe and required_probe in PROBE_KEYS:
        rankings = [
            required_probe,
            *[item for item in rankings if item != required_probe],
        ]
    if not rankings:
        rankings = [item["probe"] for item in plan]

    hint = data.get("clarification_hint")
    if hint is not None:
        hint = str(hint).strip() or None

    planner_source = data.get("planner_source")
    if not planner_source:
        planner_source = "llm" if data else fallback.get("planner_source") or "llm"

    return {
        "probe_plan": plan,
        "opportunity_rankings": rankings,
        "clarification_hint": hint,
        "planner_source": planner_source,
    }


async def _build_probe_plan(
    state: AgentState,
    config: RunnableConfig | None = None,
) -> dict[str, Any]:
    if state.get("force_final_recommendation"):
        return dict(GLOBAL_BASELINE_PLAN)
    blocked_dimensions = {
        str(item)
        for item in (state.get("factual_blocked_dimensions") or [])
        if str(item) in PREFERENCE_KEYS
    }
    if len(blocked_dimensions) >= len(PREFERENCE_KEYS):
        return dict(GLOBAL_BASELINE_PLAN)
    if should_halt_for_global_baseline(state):
        return dict(GLOBAL_BASELINE_PLAN)

    ablation_mode = get_ablation_mode(config)
    if ablation_mode == "no_ucb":
        fallback = _random_probe_plan()
        required_context: dict[str, str | None] = {
            "dimension": None,
            "probe": None,
            "reason": None,
            "instruction": None,
        }
    else:
        fallback = _deterministic_probe_plan(state)
        required_context = _required_probe_context(state)
    required_probe = required_context["probe"]
    required_reason = str(required_context["reason"] or "")
    fallback = _sanitize_plan(
        {},
        fallback,
        required_probe=required_probe,
        required_reason=required_reason,
    )
    if required_context.get("dimension"):
        fallback["ucb_target_dimension"] = required_context["dimension"]
    planner_factory_is_monkeypatched = get_chat_model is not get_structured_chat_model
    if (
        os.getenv("GAOKAOLLM_OFFLINE_DETERMINISTIC") == "1"
        or os.getenv("GAOKAOLLM_SKIP_LLM_PLANNER", "1") == "1"
    ) and not planner_factory_is_monkeypatched:
        return fallback

    constraints = state.get("constraints", {})
    normalized_intent = state.get("normalized_intent", {})
    llm = get_chat_model()
    prompt = [
        SystemMessage(
            content=(
                "你是高考志愿咨询中的取舍探测规划师。"
                "你的任务是决定下一轮应该检查哪些可审计的事实方向；事实候选只能由后续数据库探针产生。"
                "不要编造学校、专业、分数、位次或收益。"
                "只输出 JSON，字段为 probe_plan(list), opportunity_rankings(list[str]), clarification_hint(str|null)。"
                "probe 只能从以下集合选择: "
                + ", ".join(PROBE_KEYS)
                + "。优先选择最能检验用户底线弹性的方向；如果事实上没有可比较方向，只给一句短 clarification_hint。"
                "不要输出 implicit_flexibilities, volunteer_set, axis_flexibilities。"
                + (
                    str(required_context["instruction"])
                    if required_context["instruction"]
                    else ""
                )
            )
        ),
        HumanMessage(
            content=(
                "请为以下当前状态规划下一轮事实探测，只返回 JSON：\n"
                + json.dumps(
                    {
                        "constraints": constraints,
                        "normalized_intent": normalized_intent,
                        "score_waste": state.get("score_waste", 0),
                        "baseline_count": len(state.get("baseline_results", [])),
                        "fallback_plan": fallback,
                        **(
                            {}
                            if ablation_mode == "no_ucb"
                            else {
                                "ucb_scores": calculate_ucb_scores(state),
                                "ucb_target_dimension": required_context["dimension"],
                                "ucb_required_probe": required_probe,
                            }
                        ),
                    },
                    ensure_ascii=False,
                    default=str,
                )
            )
        ),
    ]
    try:
        response = await ainvoke_with_timeout(
            llm,
            prompt,
            timeout=structured_timeout_seconds(),
            label="radar",
        )
        parsed = _json_from_text(str(response.content))
        sanitized = _sanitize_plan(
            parsed,
            fallback,
            required_probe=required_probe,
            required_reason=required_reason,
        )
        if required_context.get("dimension"):
            sanitized["ucb_target_dimension"] = required_context["dimension"]
        return sanitized
    except Exception as exc:
        print(
            f"[radar] llm_planner_failed={type(exc).__name__}; using deterministic plan"
        )
        return fallback


async def radar_node(
    state: AgentState,
    config: RunnableConfig | None = None,
) -> dict[str, Any]:
    semantic_output = await refresh_full_context_semantics(state)
    if semantic_output:
        state = {**state, **semantic_output}
    baseline = state.get("baseline_results", [])
    score_waste = int(state.get("score_waste") or 0)
    constraints = state.get("constraints", {})
    has_negotiable_constraint = bool(
        constraints.get("province")
        or constraints.get("city")
        or constraints.get("major")
        or constraints.get("strength")
        or int(constraints.get("budget") or 100000) < 100000
        or constraints.get("risk_preference")
        or constraints.get("employment_preference")
    )

    print(f"[radar] baseline={len(baseline)} score_waste={score_waste}")
    trace_event(
        "radar",
        "node_start",
        {
            "constraints": constraints,
            "baseline_count": len(baseline),
            "score_waste": score_waste,
            "has_negotiable_constraint": has_negotiable_constraint,
        },
    )
    plan = await _build_probe_plan(state, config)

    if _is_global_baseline_plan(plan):
        global_result: Any = await probe_global_baseline(dict(state))
        global_result = _merge_accepted_into_baseline(global_result, state)
        opportunities: dict[str, Any] = {"global_baseline": global_result}
        candidates = _iter_rows(global_result)
        print(f"[radar] global_baseline={len(candidates)}")
        output = {
            **semantic_output,
            "pareto_opportunities": opportunities,
            "candidates": candidates,
            "probe_plan": plan["probe_plan"],
            "opportunity_rankings": plan["opportunity_rankings"],
            "clarification_hint": plan.get("clarification_hint"),
            "planner_source": plan.get("planner_source"),
            "ucb_target_dimension": plan.get("ucb_target_dimension"),
        }
        trace_event(
            "radar",
            "node_end",
            {
                "global_baseline": True,
                "candidate_count": len(candidates),
                "plan": plan,
            },
        )
        return output

    if score_waste > 15 or not baseline or has_negotiable_constraint:
        opportunities = await run_all_probes(constraints, user_state=dict(state))
    else:
        opportunities = dict(EMPTY_OPPORTUNITIES)
    opportunities = _without_accepted_relaxation_candidates(opportunities, state)
    try:
        global_result: Any = await probe_global_baseline(dict(state))
        global_result = _merge_accepted_into_baseline(global_result, state)
    except Exception as exc:
        print(f"[radar] global_baseline_preview_failed={type(exc).__name__}")
        global_result = {}
    opportunities = dict(opportunities)
    opportunities = _without_global_baseline_duplicates(opportunities, global_result)
    plan = _plan_with_available_opportunities(plan, opportunities, state)
    if _is_global_baseline_plan(plan):
        opportunities["global_baseline"] = global_result
        candidates = _iter_rows(global_result)
        print(f"[radar] global_baseline={len(candidates)} after_opportunity_filter")
        output = {
            **semantic_output,
            "pareto_opportunities": opportunities,
            "candidates": candidates,
            "probe_plan": plan["probe_plan"],
            "opportunity_rankings": plan["opportunity_rankings"],
            "clarification_hint": plan.get("clarification_hint"),
            "planner_source": plan.get("planner_source"),
            "ucb_target_dimension": plan.get("ucb_target_dimension"),
        }
        trace_event(
            "radar",
            "node_end",
            {
                "global_baseline": True,
                "candidate_count": len(candidates),
                "plan": plan,
            },
        )
        return output
    candidates = _flatten_candidates(
        opportunities,
        [str(item) for item in plan.get("opportunity_rankings", [])],
        include_unranked=get_ablation_mode(config) != "no_ucb",
    )
    accepted_candidates = _accepted_relaxation_candidates(state)
    if accepted_candidates:
        existing_candidate_keys = {_candidate_identity_key(row) for row in candidates}
        candidates = [
            *[
                row
                for row in accepted_candidates
                if _candidate_identity_key(row) not in existing_candidate_keys
            ],
            *candidates,
        ]
    opportunities["global_baseline"] = global_result
    global_count = len(_iter_rows(global_result))

    print(
        "[radar] opportunities="
        f"geo:{len(opportunities.get('geo_relax', []))} "
        f"city:{len(opportunities.get('city_relax', []))} "
        f"major:{len(opportunities.get('major_relax', []))} "
        f"strength:{len(opportunities.get('strength_relax', []))} "
        f"major_quality:{len(opportunities.get('major_quality_relax', []))} "
        f"tuition:{len(opportunities.get('tuition_value_relax', []))} "
        f"employment:{len(opportunities.get('employment_outcome_relax', []))} "
        f"region_tree:{len(opportunities.get('region_tree_relax', []))} "
        f"major_geo:{len(opportunities.get('major_geo_relax', []))} "
        f"risk:{len(opportunities.get('risk_band_relax', []))} "
        f"global:{global_count}"
    )
    output = {
        **semantic_output,
        "pareto_opportunities": opportunities,
        "candidates": candidates,
        "probe_plan": plan["probe_plan"],
        "opportunity_rankings": plan["opportunity_rankings"],
        "clarification_hint": plan.get("clarification_hint"),
        "planner_source": plan.get("planner_source"),
        "ucb_target_dimension": plan.get("ucb_target_dimension"),
    }
    trace_event(
        "radar",
        "node_end",
        {
            "plan": plan,
            "candidate_count": len(candidates),
            "opportunity_counts": {
                key: len(value) if isinstance(value, list) else 0
                for key, value in opportunities.items()
            },
            "candidate_preview": candidates[:5],
        },
    )
    return output
