import asyncio
import time
from typing import Any

from fastapi import APIRouter, HTTPException
from langchain_core.messages import HumanMessage
from langgraph.types import Command

from app.graphs.nodes.preference_tracker import preference_tracker_node
from app.graphs.workflow import build_graph
from app.schemas.models import ChatRequest


router = APIRouter(prefix="/api/v1", tags=["chat"])
graph = build_graph()

CHAT_ACTION_FEEDBACK = "feedback"
CHAT_ACTION_CONTINUE = "continue"

_RUNS: dict[str, dict[str, Any]] = {}
_NODE_ORDER = [
    "semantic_normalizer",
    "gatekeeper",
    "radar",
    "negotiator",
    "preference_tracker",
]


def _interrupt_value(result: dict) -> object | None:
    interrupts = result.get("__interrupt__")
    if not interrupts:
        return None
    first = interrupts[0] if isinstance(interrupts, (list, tuple)) else interrupts
    value = getattr(first, "value", None)
    return value if value is not None else first


def _interrupt_text_from_value(value: object | None) -> str | None:
    if value is None:
        return None
    if isinstance(value, dict):
        text = value.get("text")
        return str(text) if text is not None else None
    return str(value)


def _interrupt_meta(value: object | None) -> dict:
    return value if isinstance(value, dict) else {}


def _interrupt_text(result: dict) -> str | None:
    return _interrupt_text_from_value(_interrupt_value(result))


def _graph_config(thread_id: str) -> dict:
    return {"configurable": {"thread_id": thread_id}}


def _snapshot(thread_id: str) -> object:
    return graph.get_state(_graph_config(thread_id))


def _pending_interrupt_value(thread_id: str) -> object | None:
    snapshot = _snapshot(thread_id)
    for task in snapshot.tasks or ():
        interrupts = getattr(task, "interrupts", None) or ()
        if not interrupts:
            continue
        value = getattr(interrupts[0], "value", None)
        return value if value is not None else interrupts[0]
    return None


async def _apply_feedback_update(req: ChatRequest, pending_value: object) -> dict:
    config = _graph_config(req.thread_id)
    snapshot = graph.get_state(config)
    values = dict(snapshot.values or {})
    pending_meta = _interrupt_meta(pending_value)
    values.update(
        {
            "latest_human_feedback": req.message,
            "latest_agent_probe_question": _interrupt_text_from_value(pending_value)
            or values.get("latest_agent_probe_question"),
            "latest_pareto_diff": pending_meta.get("latest_pareto_diff")
            if "latest_pareto_diff" in pending_meta
            else values.get("latest_pareto_diff"),
            "latest_question_kind": pending_meta.get("latest_question_kind")
            or values.get("latest_question_kind"),
            "latest_question_source": pending_meta.get("latest_question_source")
            or values.get("latest_question_source"),
            "latest_probe_target_dimension": pending_meta.get(
                "latest_probe_target_dimension"
            )
            or values.get("latest_probe_target_dimension"),
            "latest_tradeoff_pair": pending_meta.get("latest_tradeoff_pair")
            or values.get("latest_tradeoff_pair"),
        }
    )
    tracker_output = await preference_tracker_node(values)
    graph.update_state(config, tracker_output, as_node="preference_tracker")
    return dict(graph.get_state(config).values or {})


def _pending_interrupt_text(thread_id: str) -> str | None:
    return _interrupt_text_from_value(_pending_interrupt_value(thread_id))


def _question_kind_from_text(text: str | None) -> str | None:
    content = str(text or "")
    if (
        "没有看到值得" in content
        or "不把这条作为偏好调整依据" in content
        or "事实边界" in content
        or "不足以形成取舍" in content
    ):
        return "no_significant_tradeoff"
    return None


def _message_reply(result: dict) -> str | None:
    messages = result.get("messages") or []
    if not messages:
        return None
    return str(messages[-1].content)


def _node_status_from_state(
    result: dict,
    *,
    pending_interrupt: str | None,
    run_record: dict[str, Any] | None,
) -> dict[str, str]:
    completed = set(run_record.get("completed_nodes", [])) if run_record else set()
    progress = {
        "semantic_normalizer": "ok"
        if (
            "semantic_normalizer" in completed
            or result.get("rewritten_query")
            or result.get("full_context_query")
        )
        else "pending",
        "gatekeeper": "ok"
        if (
            "gatekeeper" in completed
            or bool(result.get("constraints"))
            or "missing_constraints" in result
        )
        else "pending",
        "radar": "ok"
        if (
            "radar" in completed
            or bool(result.get("probe_plan"))
            or bool(result.get("baseline_results"))
            or bool(result.get("pareto_opportunities"))
            or bool(result.get("candidates"))
        )
        else "pending",
        "negotiator": "ok"
        if (
            "negotiator" in completed
            or pending_interrupt
            or result.get("latest_agent_probe_question")
        )
        else "pending",
        "preference_tracker": "updated"
        if (
            "preference_tracker" in completed
            or int(result.get("negotiation_turns") or 0) > 0
        )
        else "waiting",
    }
    return progress


def _run_status(thread_id: str, pending_interrupt: str | None) -> str:
    record = _RUNS.get(thread_id) or {}
    status = str(record.get("status") or "idle")
    task = record.get("task")
    if task is not None and not task.done():
        return "running"
    if pending_interrupt:
        return "interrupt"
    if status in {"running", "completed", "interrupt", "error"}:
        return status
    return "idle"


def _payload_from_values(
    *,
    thread_id: str,
    result: dict,
    mode: str,
    interrupt_value: object | None = None,
    include_pending: bool = True,
) -> dict:
    pending_value = (
        interrupt_value or _pending_interrupt_value(thread_id)
        if include_pending
        else None
    )
    pending_meta = _interrupt_meta(pending_value)
    pending_interrupt = _interrupt_text_from_value(pending_value)
    reply = pending_interrupt or result.get("latest_agent_probe_question")
    if not reply:
        reply = _message_reply(result)
    if mode == "feedback":
        navigation_intent = result.get("navigation_intent")
        if navigation_intent == "finalize":
            reply = "正在基于当前偏好生成最终推荐。"
        elif navigation_intent == "continue":
            reply = "正在换一个方向继续比较。"
        else:
            reply = "偏好已更新。"
    record = _RUNS.get(thread_id)
    run_status = _run_status(thread_id, pending_interrupt)
    if record and record.get("status") == "error":
        run_status = "error"
    workflow_progress = _node_status_from_state(
        result,
        pending_interrupt=pending_interrupt,
        run_record=record,
    )
    api_status = (
        "interrupt"
        if pending_interrupt
        else "running"
        if run_status == "running"
        else "error"
        if run_status == "error"
        else "completed"
    )
    return {
        "thread_id": thread_id,
        "mode": mode,
        "status": api_status,
        "run_status": run_status,
        "run_error": record.get("error") if record else None,
        "completed_nodes": list(record.get("completed_nodes", [])) if record else [],
        "workflow_progress": workflow_progress,
        "reply": reply or "",
        "pending_interrupt": pending_interrupt,
        "constraints": result.get("constraints", {}),
        "original_constraints": result.get("original_constraints", {}),
        "baseline_results": result.get("baseline_results", []),
        "pareto_opportunities": result.get("pareto_opportunities", {}),
        "score_waste": result.get("score_waste", 0),
        "missing_constraints": result.get("missing_constraints", []),
        "rewritten_query": result.get("rewritten_query"),
        "full_context_query": result.get("full_context_query"),
        "full_context_embedding_model": result.get("full_context_embedding_model"),
        "lexicographic_epsilon": result.get("lexicographic_epsilon"),
        "intent_axes": result.get("intent_axes", []),
        "normalized_intent": result.get("normalized_intent", {}),
        "probe_plan": result.get("probe_plan", []),
        "opportunity_rankings": result.get("opportunity_rankings", []),
        "clarification_hint": result.get("clarification_hint"),
        "latest_agent_probe_question": result.get("latest_agent_probe_question"),
        "latest_pareto_diff": pending_meta.get("latest_pareto_diff")
        if "latest_pareto_diff" in pending_meta
        else result.get("latest_pareto_diff"),
        "latest_question_kind": pending_meta.get("latest_question_kind")
        or result.get("latest_question_kind")
        or _question_kind_from_text(pending_interrupt),
        "latest_question_source": pending_meta.get("latest_question_source")
        or result.get("latest_question_source"),
        "latest_probe_target_dimension": pending_meta.get(
            "latest_probe_target_dimension"
        )
        or result.get("latest_probe_target_dimension"),
        "latest_tradeoff_pair": pending_meta.get("latest_tradeoff_pair")
        or result.get("latest_tradeoff_pair"),
        "feedback_analysis": result.get("feedback_analysis"),
        "accepted_relaxations": result.get("accepted_relaxations", []),
        "factual_blocked_dimensions": result.get("factual_blocked_dimensions", []),
        "force_final_recommendation": result.get("force_final_recommendation", False),
        "navigation_intent": result.get("navigation_intent"),
        "ucb_target_dimension": result.get("ucb_target_dimension"),
        "implicit_weights": result.get("implicit_weights", {}),
        "weight_variance": result.get("weight_variance", {}),
        "negotiation_turns": result.get("negotiation_turns", 0),
        "candidates": result.get("candidates", []),
    }


def _response_payload(
    req: ChatRequest,
    result: dict,
    *,
    mode: str,
    include_pending: bool = True,
) -> dict:
    return _payload_from_values(
        thread_id=req.thread_id,
        result=result,
        mode=mode,
        interrupt_value=_interrupt_value(result),
        include_pending=include_pending,
    )


def _remember_completed_node(record: dict[str, Any], node_name: str) -> None:
    if node_name not in _NODE_ORDER:
        return
    completed = record.setdefault("completed_nodes", [])
    if node_name not in completed:
        completed.append(node_name)


async def _drain_graph_stream(
    thread_id: str,
    payload: object,
    *,
    mode: str,
) -> None:
    record = _RUNS[thread_id]
    record.update({"status": "running", "mode": mode, "error": None})
    try:
        async for event in graph.astream(payload, config=_graph_config(thread_id)):
            record["last_event_at"] = time.time()
            if not isinstance(event, dict):
                continue
            for key in event:
                if key == "__interrupt__":
                    record["status"] = "interrupt"
                    _remember_completed_node(record, "negotiator")
                else:
                    _remember_completed_node(record, key)
        pending = _pending_interrupt_value(thread_id)
        record["status"] = "interrupt" if pending else "completed"
        record["finished_at"] = time.time()
    except Exception as exc:  # pragma: no cover - exercised through API contract
        record["status"] = "error"
        record["error"] = f"{type(exc).__name__}: {exc}"
        record["finished_at"] = time.time()


def _active_task(record: dict[str, Any] | None) -> asyncio.Task | None:
    task = record.get("task") if record else None
    return task if isinstance(task, asyncio.Task) and not task.done() else None


def _start_background_run(thread_id: str, payload: object, *, mode: str) -> None:
    record = _RUNS.setdefault(thread_id, {})
    task = _active_task(record)
    if task is not None:
        return
    record.update(
        {
            "status": "running",
            "mode": mode,
            "started_at": time.time(),
            "finished_at": None,
            "error": None,
            "completed_nodes": [],
        }
    )
    record["task"] = asyncio.create_task(
        _drain_graph_stream(thread_id, payload, mode=mode)
    )


def _current_state_payload(thread_id: str, *, mode: str = "state") -> dict:
    values = dict(getattr(_snapshot(thread_id), "values", None) or {})
    record = _RUNS.get(thread_id) or {}
    hide_stale_pending = record.get("status") == "running" and record.get("mode") in {
        "continue",
        "resume",
    }
    if hide_stale_pending:
        values["latest_agent_probe_question"] = None
    return _payload_from_values(
        thread_id=thread_id,
        result=values,
        mode=mode,
        include_pending=not hide_stale_pending,
    )


@router.post("/chat/runs")
async def start_chat_run(req: ChatRequest) -> dict:
    action = str(req.action or "").strip().lower()
    try:
        pending_value = _pending_interrupt_value(req.thread_id)
        pending_interrupt = _interrupt_text_from_value(pending_value)
        if action == CHAT_ACTION_FEEDBACK:
            raise HTTPException(status_code=400, detail="反馈更新请调用 /api/v1/chat。")
        if action == CHAT_ACTION_CONTINUE:
            payload: object = Command(goto="radar")
            mode = "continue"
        elif pending_interrupt:
            payload = Command(resume=req.message)
            mode = "resume"
        else:
            payload = {"messages": [HumanMessage(content=req.message)]}
            mode = "message"
        _start_background_run(req.thread_id, payload, mode=mode)
        return _current_state_payload(req.thread_id, mode=mode)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get("/chat/state/{thread_id}")
async def chat_state(thread_id: str) -> dict:
    try:
        return _current_state_payload(thread_id)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post("/chat")
async def chat(req: ChatRequest) -> dict:
    config = _graph_config(req.thread_id)
    try:
        action = str(req.action or "").strip().lower()
        pending_value = _pending_interrupt_value(req.thread_id)
        pending_interrupt = _interrupt_text_from_value(pending_value)
        if action == CHAT_ACTION_FEEDBACK:
            if not pending_interrupt:
                raise HTTPException(
                    status_code=409, detail="当前没有待提交的取舍问题。"
                )
            result = await _apply_feedback_update(req, pending_value)
            return _response_payload(
                req,
                result,
                mode="feedback",
                include_pending=False,
            )

        if action == CHAT_ACTION_CONTINUE:
            result = await graph.ainvoke(Command(goto="radar"), config=config)
            return _response_payload(req, result, mode="continue")

        if pending_interrupt and action != CHAT_ACTION_CONTINUE:
            result = await graph.ainvoke(Command(resume=req.message), config=config)
            return _response_payload(req, result, mode="resume")

        result = await graph.ainvoke(
            {"messages": [HumanMessage(content=req.message)]},
            config=config,
        )
        return _response_payload(req, result, mode="message")
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
