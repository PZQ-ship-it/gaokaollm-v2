from typing import Any

from app.flows.probers import run_all_probes
from app.schemas.state import AgentState


async def radar_node(state: AgentState) -> dict[str, Any]:
    baseline = state.get("baseline_results", [])
    score_waste = int(state.get("score_waste") or 0)
    constraints = state.get("constraints", {})
    has_negotiable_constraint = bool(
        constraints.get("province")
        or constraints.get("major")
        or constraints.get("risk_preference")
    )

    print(f"[radar] baseline={len(baseline)} score_waste={score_waste}")
    if score_waste > 15 or not baseline or has_negotiable_constraint:
        opportunities = await run_all_probes(constraints)
    else:
        opportunities = {
            "geo_relax": [],
            "major_relax": [],
            "major_geo_relax": [],
            "risk_band_relax": [],
        }

    print(
        "[radar] opportunities="
        f"geo:{len(opportunities.get('geo_relax', []))} "
        f"major:{len(opportunities.get('major_relax', []))} "
        f"major_geo:{len(opportunities.get('major_geo_relax', []))} "
        f"risk:{len(opportunities.get('risk_band_relax', []))}"
    )
    return {"pareto_opportunities": opportunities}
