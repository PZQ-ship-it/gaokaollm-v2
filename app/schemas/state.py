from typing import Annotated, TypedDict

from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    messages: Annotated[list, add_messages]
    constraints: dict
    baseline_results: list
    score_waste: int
    pareto_opportunities: dict
    missing_constraints: list[str]
