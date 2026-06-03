from typing import Annotated, Any, NotRequired, TypedDict

from langgraph.graph.message import add_messages


DEFAULT_IMPLICIT_WEIGHTS: dict[str, float] = {
    "school": 1 / 6,
    "major": 1 / 6,
    "tuition": 1 / 6,
    "quality": 1 / 6,
    "geo": 1 / 6,
    "risk": 1 / 6,
}

DEFAULT_WEIGHT_VARIANCE: dict[str, float] = {
    "school": 1.0,
    "major": 1.0,
    "tuition": 1.0,
    "quality": 1.0,
    "geo": 1.0,
    "risk": 1.0,
}


class AgentState(TypedDict, total=False):
    messages: Annotated[list, add_messages]
    constraints: dict
    original_constraints: NotRequired[dict[str, Any]]
    baseline_results: list
    score_waste: int
    pareto_opportunities: dict
    candidates: list[dict[str, Any]]
    missing_constraints: list[str]
    rewritten_query: str
    intent_axes: list[str]
    normalized_intent: dict[str, Any]
    full_context_query: NotRequired[str]
    full_context_embedding: NotRequired[list[float]]
    full_context_embedding_model: NotRequired[str]
    lexicographic_epsilon: NotRequired[float]
    probe_plan: list[dict[str, Any]]
    opportunity_rankings: list[str]
    planner_source: str | None
    ucb_target_dimension: str | None
    implicit_weights: dict[str, float]
    weight_variance: dict[str, float]
    negotiation_turns: int
    latest_human_feedback: str | None
    latest_agent_probe_question: str | None
    latest_pareto_diff: dict[str, float] | None
    latest_question_kind: str | None
    latest_question_source: str | None
    latest_probe_target_dimension: str | None
    latest_tradeoff_pair: NotRequired[dict[str, Any] | None]
    feedback_analysis: NotRequired[dict[str, Any] | None]
    accepted_relaxations: NotRequired[list[dict[str, Any]]]
    factual_blocked_dimensions: NotRequired[list[str]]
    force_final_recommendation: NotRequired[bool]
    final_recommendation_matrix: NotRequired[dict[str, list[dict[str, Any]]]]
    final_recommendation_highlights: NotRequired[dict[str, list[dict[str, Any]]]]
    final_recommendation_count: NotRequired[int]
    navigation_intent: NotRequired[str | None]
    clarification_hint: NotRequired[str | None]
