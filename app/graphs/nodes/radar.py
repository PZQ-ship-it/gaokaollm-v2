from typing import Any

from app.flows.probers import run_all_probes
from app.schemas.state import AgentState


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
    if score_waste > 15 or not baseline or has_negotiable_constraint:
        opportunities = await run_all_probes(constraints)
    else:
        opportunities = {
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
    return {"pareto_opportunities": opportunities}
