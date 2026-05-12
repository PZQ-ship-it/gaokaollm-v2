from langchain_core.messages import AIMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from app.graphs.nodes.gatekeeper import gatekeeper_node
from app.graphs.nodes.negotiator import negotiator_node
from app.graphs.nodes.preference_tracker import preference_tracker_node
from app.graphs.nodes.radar import radar_node
from app.graphs.nodes.semantic_normalizer import semantic_normalizer_node
from app.schemas.state import AgentState


async def report_node(state: AgentState) -> dict:
    baseline = state.get("baseline_results", [])
    if not baseline:
        content = "当前硬约束下没有找到可用基准结果，也没有发现可谈判的帕累托机会。"
    else:
        lines = ["当前硬约束下可直接考虑："]
        for row in baseline[:3]:
            lines.append(
                f"- {row['school_name']}｜{row['school_province']}｜"
                f"{row['major_name']}｜最低分 {row['min_score']}"
            )
        content = "\n".join(lines)
    return {"messages": [AIMessage(content=content)]}


def route_after_radar(state: AgentState) -> str:
    opportunities = state.get("pareto_opportunities", {})
    probe_plan = state.get("probe_plan") or []
    first_probe = (
        probe_plan[0] if probe_plan and isinstance(probe_plan[0], dict) else {}
    )
    if (
        state.get("candidates")
        or first_probe.get("probe_name") == "probe_global_baseline"
    ):
        return "negotiator"
    if (
        state.get("clarification_hint")
        or opportunities.get("geo_relax")
        or opportunities.get("city_relax")
        or opportunities.get("major_relax")
        or opportunities.get("strength_relax")
        or opportunities.get("major_quality_relax")
        or opportunities.get("tuition_value_relax")
        or opportunities.get("employment_outcome_relax")
        or opportunities.get("region_tree_relax")
        or opportunities.get("major_geo_relax")
        or opportunities.get("risk_band_relax")
    ):
        return "negotiator"
    return "report"


def route_after_gatekeeper(state: AgentState) -> str:
    if state.get("missing_constraints"):
        return END
    return "radar"


def route_after_negotiator(state: AgentState) -> str:
    if str(state.get("latest_human_feedback") or "").strip():
        return "preference_tracker"
    return END


def build_graph():
    graph = StateGraph(AgentState)
    graph.add_node("semantic_normalizer", semantic_normalizer_node)
    graph.add_node("gatekeeper", gatekeeper_node)
    graph.add_node("radar", radar_node)
    graph.add_node("negotiator", negotiator_node)
    graph.add_node("preference_tracker", preference_tracker_node)
    graph.add_node("report", report_node)

    graph.add_edge(START, "semantic_normalizer")
    graph.add_edge("semantic_normalizer", "gatekeeper")
    graph.add_conditional_edges(
        "gatekeeper",
        route_after_gatekeeper,
        {"radar": "radar", END: END},
    )
    graph.add_conditional_edges(
        "radar",
        route_after_radar,
        {"negotiator": "negotiator", "report": "report"},
    )
    graph.add_conditional_edges(
        "negotiator",
        route_after_negotiator,
        {"preference_tracker": "preference_tracker", END: END},
    )
    graph.add_edge("preference_tracker", "radar")
    graph.add_edge("report", END)

    return graph.compile(checkpointer=MemorySaver())
