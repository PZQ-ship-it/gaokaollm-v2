import json
import os
import re
from typing import Any

from langchain_core.messages import SystemMessage

from app.core.llm_client import get_chat_model
from app.flows.probers import run_all_probes
from app.schemas.state import AgentState


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

EMPTY_OPPORTUNITIES = {
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


def _json_from_text(text: str) -> dict[str, Any]:
    match = re.search(r"\{.*\}", text, flags=re.S)
    if not match:
        return {}
    try:
        data = json.loads(match.group(0))
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


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


def _sanitize_plan(data: dict[str, Any], fallback: dict[str, Any]) -> dict[str, Any]:
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

    rankings = data.get("opportunity_rankings")
    if not isinstance(rankings, list):
        rankings = [item["probe"] for item in plan]
    rankings = [str(item) for item in rankings if str(item) in PROBE_KEYS]
    if not rankings:
        rankings = [item["probe"] for item in plan]

    hint = data.get("clarification_hint")
    if hint is not None:
        hint = str(hint).strip() or None

    return {
        "probe_plan": plan,
        "opportunity_rankings": rankings,
        "clarification_hint": hint,
        "planner_source": data.get("planner_source") or "llm",
    }


async def _build_probe_plan(state: AgentState) -> dict[str, Any]:
    fallback = _deterministic_probe_plan(state)
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
                },
                ensure_ascii=False,
                default=str,
            )
        ),
    ]
    try:
        response = await llm.ainvoke(prompt)
        parsed = _json_from_text(str(response.content))
        return _sanitize_plan(parsed, fallback)
    except Exception as exc:
        print(
            f"[radar] llm_planner_failed={type(exc).__name__}; using deterministic plan"
        )
        return fallback


async def radar_node(state: AgentState) -> dict[str, Any]:
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
    plan = await _build_probe_plan(state)
    if score_waste > 15 or not baseline or has_negotiable_constraint:
        opportunities = await run_all_probes(constraints)
    else:
        opportunities = dict(EMPTY_OPPORTUNITIES)

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
        "probe_plan": plan["probe_plan"],
        "opportunity_rankings": plan["opportunity_rankings"],
        "clarification_hint": plan.get("clarification_hint"),
    }
