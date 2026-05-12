from typing import Annotated, Any, NotRequired, TypedDict

from langgraph.graph.message import add_messages


DEFAULT_IMPLICIT_WEIGHTS: dict[str, float] = {
    "school": 0.25,
    "major": 0.25,
    "tuition": 0.25,
    "quality": 0.25,
    "geo": 0.25,
}

DEFAULT_WEIGHT_VARIANCE: dict[str, float] = {
    "school": 1.0,
    "major": 1.0,
    "tuition": 1.0,
    "quality": 1.0,
    "geo": 1.0,
}


class AgentState(TypedDict, total=False):
    messages: Annotated[list, add_messages]
    constraints: dict
    baseline_results: list
    score_waste: int
    pareto_opportunities: dict
    candidates: list[dict[str, Any]]
    missing_constraints: list[str]
    rewritten_query: str
    intent_axes: list[str]
    normalized_intent: dict[str, Any]
    probe_plan: list[dict[str, Any]]
    opportunity_rankings: list[str]
    implicit_weights: dict[str, float]
    weight_variance: dict[str, float]
    negotiation_turns: int
    latest_human_feedback: str | None
    latest_agent_probe_question: str | None
    latest_pareto_diff: dict[str, float] | None
    clarification_hint: NotRequired[str | None]
