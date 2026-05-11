from typing import Annotated, Any, NotRequired, TypedDict

from langgraph.graph.message import add_messages


class AgentState(TypedDict, total=False):
    messages: Annotated[list, add_messages]
    constraints: dict
    baseline_results: list
    score_waste: int
    pareto_opportunities: dict
    missing_constraints: list[str]
    rewritten_query: str
    intent_axes: list[str]
    normalized_intent: dict[str, Any]
    probe_plan: list[dict[str, Any]]
    opportunity_rankings: list[str]
    clarification_hint: NotRequired[str | None]
