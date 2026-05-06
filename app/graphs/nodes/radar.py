from typing import Any

from app.flows.probers import run_all_probes
from app.schemas.state import AgentState


async def radar_node(state: AgentState) -> dict[str, Any]:
    baseline = state.get("baseline_results", [])
    score_waste = int(state.get("score_waste") or 0)

    print(f"[radar] baseline={len(baseline)} score_waste={score_waste}")
    if score_waste > 15 or not baseline:
        opportunities = await run_all_probes(state.get("constraints", {}))
    else:
        opportunities = {"geo_relax": [], "major_relax": []}

    print(
        "[radar] opportunities="
        f"geo:{len(opportunities.get('geo_relax', []))} "
        f"major:{len(opportunities.get('major_relax', []))}"
    )
    return {"pareto_opportunities": opportunities}
