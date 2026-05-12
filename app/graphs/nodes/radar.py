import json
import math
import os
import random
import re
from typing import Any

from langchain_core.messages import SystemMessage
from langchain_core.runnables import RunnableConfig

from app.core.llm_client import get_chat_model
from app.evaluation.ablation import get_ablation_mode
from app.flows.probers import probe_global_baseline, run_all_probes
from app.schemas.state import (
    DEFAULT_IMPLICIT_WEIGHTS,
    DEFAULT_WEIGHT_VARIANCE,
    AgentState,
)


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

PREFERENCE_KEYS = ("school", "major", "tuition", "quality", "geo")
UCB_EXPLORATION_COEF = 1.5
HALTING_VARIANCE_THRESHOLD = 1.0
MAX_NEGOTIATION_TURNS = 3
GLOBAL_BASELINE_PROBE = "probe_global_baseline"
PROBE_MAPPING: dict[str, str] = {
    "school": "strength_relax",
    "major": "major_geo_relax",
    "tuition": "tuition_value_relax",
    "quality": "major_quality_relax",
    "geo": "major_geo_relax",
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
    return total_weight_variance(state) < HALTING_VARIANCE_THRESHOLD or (
        turns >= MAX_NEGOTIATION_TURNS
    )


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
) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    seen: set[tuple[Any, Any, Any]] = set()
    ordered_keys = [
        *[key for key in rankings if key in opportunities],
        *[key for key in EMPTY_OPPORTUNITIES if key in opportunities],
    ]
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


def calculate_ucb_scores(state: AgentState) -> dict[str, float]:
    raw_weights = state.get("implicit_weights") or {}
    raw_variance = state.get("weight_variance") or {}
    scores: dict[str, float] = {}
    for key in PREFERENCE_KEYS:
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


def select_ucb_dimension(state: AgentState) -> tuple[str, float]:
    scores = calculate_ucb_scores(state)
    if not scores:
        return "geo", 0.0
    dimension = max(scores, key=lambda key: scores[key])
    return dimension, scores[dimension]


def target_probe_for_dimension(dimension: str) -> str:
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
    probe = target_probe_for_dimension(dimension)
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
    probe = random.choice(PROBE_KEYS)
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
    if os.getenv("GAOKAOLLM_OFFLINE_DETERMINISTIC") == "1":
        return fallback

    constraints = state.get("constraints", {})
    normalized_intent = state.get("normalized_intent", {})
    llm = get_chat_model()
    prompt = [
        SystemMessage(
            content=(
                "你是高考志愿 Pareto 机会探测规划器。"
                "你只能规划接下来应调用哪些确定性探针，不得编造学校、专业、分数或候选。"
                "输出 JSON，字段为 probe_plan(list), opportunity_rankings(list[str]), "
                "clarification_hint(str|null)。"
                "probe 只能从以下集合中选择: "
                + ", ".join(PROBE_KEYS)
                + "。如果需要澄清，只给短 clarification_hint；事实候选必须由 SQL probes 产生。"
                "禁止输出 implicit_flexibilities, volunteer_set, axis_flexibilities。"
                + (
                    str(required_context["instruction"])
                    if required_context["instruction"]
                    else ""
                )
            )
        ),
        SystemMessage(
            content=json.dumps(
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
        ),
    ]
    try:
        response = await llm.ainvoke(prompt)
        parsed = _json_from_text(str(response.content))
        return _sanitize_plan(
            parsed,
            fallback,
            required_probe=required_probe,
            required_reason=required_reason,
        )
    except Exception as exc:
        print(
            f"[radar] llm_planner_failed={type(exc).__name__}; using deterministic plan"
        )
        return fallback


async def radar_node(
    state: AgentState,
    config: RunnableConfig | None = None,
) -> dict[str, Any]:
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
    plan = await _build_probe_plan(state, config)

    if _is_global_baseline_plan(plan):
        global_result: Any = await probe_global_baseline(dict(state))
        opportunities: dict[str, Any] = {"global_baseline": global_result}
        candidates = _iter_rows(global_result)
        print(f"[radar] global_baseline={len(candidates)}")
        return {
            "pareto_opportunities": opportunities,
            "candidates": candidates,
            "probe_plan": plan["probe_plan"],
            "opportunity_rankings": plan["opportunity_rankings"],
            "clarification_hint": plan.get("clarification_hint"),
        }

    if score_waste > 15 or not baseline or has_negotiable_constraint:
        opportunities = await run_all_probes(constraints, user_state=dict(state))
    else:
        opportunities = dict(EMPTY_OPPORTUNITIES)
    candidates = _flatten_candidates(
        opportunities,
        [str(item) for item in plan.get("opportunity_rankings", [])],
    )

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
        f"risk:{len(opportunities.get('risk_band_relax', []))}"
    )
    return {
        "pareto_opportunities": opportunities,
        "candidates": candidates,
        "probe_plan": plan["probe_plan"],
        "opportunity_rankings": plan["opportunity_rankings"],
        "clarification_hint": plan.get("clarification_hint"),
    }
