"""LangGraph helpers for JSON-validated LLM pipelines."""

from __future__ import annotations

from typing import Any, Awaitable, Callable, TypedDict

from langgraph.graph import END, StateGraph


class JsonChainState(TypedDict, total=False):
    input: Any
    messages: list[dict[str, str]]
    response_format: dict[str, Any] | None
    raw_content: str
    parsed_json: Any
    repaired_json: dict[str, Any]
    validated_output: dict[str, Any] | None
    error: str | None


def build_json_chain(
    *,
    build_prompt: Callable[[JsonChainState], dict[str, Any]],
    call_llm: Callable[[JsonChainState], Awaitable[dict[str, Any]]],
    parse_json: Callable[[JsonChainState], dict[str, Any]],
    repair_json: Callable[[JsonChainState], dict[str, Any]],
    validate: Callable[[JsonChainState], dict[str, Any]],
):
    graph = StateGraph(JsonChainState)
    graph.add_node("build_prompt", build_prompt)
    graph.add_node("call_llm", call_llm)
    graph.add_node("parse_json", parse_json)
    graph.add_node("repair_json", repair_json)
    graph.add_node("validate", validate)
    graph.set_entry_point("build_prompt")
    graph.add_edge("build_prompt", "call_llm")
    graph.add_edge("call_llm", "parse_json")
    graph.add_edge("parse_json", "repair_json")
    graph.add_edge("repair_json", "validate")
    graph.add_edge("validate", END)
    return graph.compile()
