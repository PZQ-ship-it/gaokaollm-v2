from langchain_core.messages import AIMessage
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph

from app.graphs.nodes.gatekeeper import gatekeeper_node
from app.graphs.nodes.negotiator import negotiator_node
from app.graphs.nodes.radar import radar_node
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
    if (
        opportunities.get("geo_relax")
        or opportunities.get("city_relax")
        or opportunities.get("major_relax")
        or opportunities.get("strength_relax")
        or opportunities.get("major_quality_relax")
        or opportunities.get("tuition_value_relax")
        or opportunities.get("major_geo_relax")
        or opportunities.get("risk_band_relax")
    ):
        return "negotiator"
    return "report"


def route_after_gatekeeper(state: AgentState) -> str:
    if state.get("missing_constraints"):
        return END
    return "radar"


def build_graph():
    graph = StateGraph(AgentState)
    graph.add_node("gatekeeper", gatekeeper_node)
    graph.add_node("radar", radar_node)
    graph.add_node("negotiator", negotiator_node)
    graph.add_node("report", report_node)

    graph.add_edge(START, "gatekeeper")
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
    graph.add_edge("negotiator", END)
    graph.add_edge("report", END)

    return graph.compile(checkpointer=InMemorySaver())
