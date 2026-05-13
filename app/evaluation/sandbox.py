import asyncio
from typing import Any

from langchain_core.messages import HumanMessage
from langgraph.types import Command

from app.evaluation.schemas import IcebergProfile
from app.evaluation.simulator import UserSimulator


def _interrupt_question(snapshot: Any) -> str | None:
    tasks = getattr(snapshot, "tasks", None) or []
    for task in tasks:
        interrupts = getattr(task, "interrupts", None) or []
        if interrupts:
            value = getattr(interrupts[0], "value", None)
            if value:
                return str(value)
    values = getattr(snapshot, "values", None) or {}
    question = values.get("latest_agent_probe_question")
    return str(question) if question else None


def _final_message_text(values: dict[str, Any]) -> str:
    messages = values.get("messages") or []
    if not messages:
        return ""
    last = messages[-1]
    return str(getattr(last, "content", last) or "")


def _mae(
    inferred_weights: dict[str, Any],
    ground_truth_weights: dict[str, float],
) -> float:
    if not ground_truth_weights:
        return 0.0
    total = 0.0
    for key, truth in ground_truth_weights.items():
        try:
            inferred = float(inferred_weights.get(key, 0.0))
        except (TypeError, ValueError):
            inferred = 0.0
        total += abs(inferred - float(truth))
    return total / len(ground_truth_weights)


async def _drain_stream(
    agent_app: Any,
    payload: Any,
    config: dict[str, Any],
    *,
    timeout_seconds: float | None = None,
) -> None:
    async def _consume() -> None:
        async for _event in agent_app.astream(payload, config=config):
            pass

    if timeout_seconds is None or timeout_seconds <= 0:
        await _consume()
        return
    await asyncio.wait_for(_consume(), timeout=timeout_seconds)


async def arun_sandbox_evaluation(
    agent_app: Any,
    profile: IcebergProfile,
    simulator: UserSimulator,
    thread_id: str,
    *,
    configurable: dict[str, Any] | None = None,
    max_turns: int = 8,
    turn_timeout_seconds: float | None = None,
) -> dict[str, Any]:
    config = {"configurable": {"thread_id": thread_id, **(configurable or {})}}
    payload: Any = {
        "messages": [HumanMessage(content=profile.explicit_query)],
        "constraints": {"profile_id": profile.profile_id},
    }

    for _ in range(max_turns):
        await _drain_stream(
            agent_app,
            payload,
            config,
            timeout_seconds=turn_timeout_seconds,
        )
        snapshot = agent_app.get_state(config)
        question = _interrupt_question(snapshot)
        if not question:
            break

        print(f"[Agent]: {question}")
        reply = simulator.generate_reply(question)
        print(f"[Simulator]: {reply}")
        payload = Command(resume=reply)

    final_state = agent_app.get_state(config).values
    inferred_weights = dict(final_state.get("implicit_weights") or {})
    turns = int(final_state.get("negotiation_turns") or 0)
    return {
        "mae_error": float(_mae(inferred_weights, profile.ground_truth_weights)),
        "turns": turns,
        "inferred_weights": inferred_weights,
        "final_xai_report": _final_message_text(final_state),
    }


def run_sandbox_evaluation(
    agent_app: Any,
    profile: IcebergProfile,
    simulator: UserSimulator,
    thread_id: str,
    *,
    configurable: dict[str, Any] | None = None,
    max_turns: int = 8,
    turn_timeout_seconds: float | None = None,
) -> dict[str, Any]:
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(
            arun_sandbox_evaluation(
                agent_app,
                profile,
                simulator,
                thread_id,
                configurable=configurable,
                max_turns=max_turns,
                turn_timeout_seconds=turn_timeout_seconds,
            )
        )
    raise RuntimeError(
        "run_sandbox_evaluation cannot be called from a running event loop; "
        "use arun_sandbox_evaluation instead."
    )
