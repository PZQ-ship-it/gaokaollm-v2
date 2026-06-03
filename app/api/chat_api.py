import asyncio
import contextlib
import json
import time
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from langchain_core.messages import HumanMessage
from langgraph.types import Command

from app.core.llm_client import reset_text_stream_callback, set_text_stream_callback
from app.graphs.nodes.negotiator import _sanitize_user_output
from app.graphs.nodes.preference_tracker import preference_tracker_node
from app.graphs.workflow import build_graph
from app.schemas.models import ChatRequest


router = APIRouter(prefix="/api/v1", tags=["chat"])
graph = build_graph()

CHAT_ACTION_FEEDBACK = "feedback"
CHAT_ACTION_CONTINUE = "continue"
FEEDBACK_SIGNALS = {
    "ACCEPT",
    "REJECT",
    "REJECT_TARGET",
    "REJECT_SIDE",
    "HESITATE",
    "FINALIZE",
}

_RUNS: dict[str, dict[str, Any]] = {}
_STREAM_DONE = object()
STREAM_FLUSH_BOUNDARIES = "\n。！？；.!?;"
STREAM_INCREMENTAL_FLUSH_CHARS = 32
STREAM_INCREMENTAL_HOLDBACK_CHARS = 8
STREAM_STATE_HEARTBEAT_SECONDS = 2.0
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


def _feedback_signal(message: str) -> str:
    signal = str(message or "").strip().upper()
    if signal not in FEEDBACK_SIGNALS:
        raise HTTPException(
            status_code=400,
            detail=(
                "反馈必须是 ACCEPT、REJECT、REJECT_TARGET、REJECT_SIDE、"
                "HESITATE 或 FINALIZE。"
            ),
        )
    return signal


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
    feedback_signal = _feedback_signal(req.message)
    values.update(
        {
            "latest_human_feedback": feedback_signal,
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
            "latest_intent_mask": pending_meta.get("latest_intent_mask")
            or values.get("latest_intent_mask"),
            "latest_residual_noise": pending_meta.get("latest_residual_noise")
            or values.get("latest_residual_noise"),
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


def _has_confirmed_user_visible_output(
    result: dict,
    *,
    pending_interrupt: str | None,
) -> bool:
    if pending_interrupt or result.get("latest_agent_probe_question"):
        return True
    if int(result.get("final_recommendation_count") or 0) > 0:
        return True
    matrix = result.get("final_recommendation_matrix")
    return isinstance(matrix, dict) and any(matrix.values())


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
    hide_draft_candidates = run_status in {
        "running",
        "error",
    } and not _has_confirmed_user_visible_output(
        result,
        pending_interrupt=pending_interrupt,
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
        "baseline_results": []
        if hide_draft_candidates
        else result.get("baseline_results", []),
        "pareto_opportunities": {}
        if hide_draft_candidates
        else result.get("pareto_opportunities", {}),
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
        "latest_intent_mask": pending_meta.get("latest_intent_mask")
        or result.get("latest_intent_mask"),
        "latest_residual_noise": pending_meta.get("latest_residual_noise")
        or result.get("latest_residual_noise"),
        "feedback_analysis": result.get("feedback_analysis"),
        "accepted_relaxations": result.get("accepted_relaxations", []),
        "factual_blocked_dimensions": result.get("factual_blocked_dimensions", []),
        "force_final_recommendation": result.get("force_final_recommendation", False),
        "final_recommendation_matrix": result.get("final_recommendation_matrix", {}),
        "final_recommendation_highlights": result.get(
            "final_recommendation_highlights", {}
        ),
        "final_recommendation_count": result.get("final_recommendation_count", 0),
        "navigation_intent": result.get("navigation_intent"),
        "ucb_target_dimension": result.get("ucb_target_dimension"),
        "implicit_weights": result.get("implicit_weights", {}),
        "weight_variance": result.get("weight_variance", {}),
        "negotiation_turns": result.get("negotiation_turns", 0),
        "candidates": [] if hide_draft_candidates else result.get("candidates", []),
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


def _stream_queue(record: dict[str, Any]) -> asyncio.Queue:
    queue = record.get("stream_queue")
    if not isinstance(queue, asyncio.Queue):
        queue = asyncio.Queue()
        record["stream_queue"] = queue
    return queue


async def _publish_stream_event(
    thread_id: str,
    event_type: str,
    data: dict[str, Any],
) -> None:
    record = _RUNS.get(thread_id)
    if record is None:
        return
    await _stream_queue(record).put({"event": event_type, "data": data})


async def _publish_text_delta(
    thread_id: str,
    delta: str,
    label: str,
) -> None:
    await _publish_stream_event(
        thread_id,
        "delta",
        {
            "text": delta,
            "label": label,
        },
    )


async def _publish_state_event(thread_id: str, *, mode: str) -> None:
    await _publish_stream_event(
        thread_id,
        "state",
        _current_state_payload(thread_id, mode=mode),
    )


async def _stream_state_heartbeat(thread_id: str, *, mode: str) -> None:
    while True:
        await asyncio.sleep(STREAM_STATE_HEARTBEAT_SECONDS)
        record = _RUNS.get(thread_id) or {}
        if record.get("status") != "running":
            return
        await _publish_state_event(thread_id, mode=mode)


def _safe_stream_flush_index(text: str) -> int:
    return max(
        (text.rfind(mark) + len(mark) for mark in STREAM_FLUSH_BOUNDARIES),
        default=0,
    )


def _stream_flush_index(text: str, emitted_len: int) -> int:
    boundary_index = _safe_stream_flush_index(text)
    if boundary_index > emitted_len:
        return boundary_index
    pending_len = len(text) - emitted_len
    if pending_len < STREAM_INCREMENTAL_FLUSH_CHARS:
        return emitted_len
    return max(emitted_len, len(text) - STREAM_INCREMENTAL_HOLDBACK_CHARS)


class _UserVisibleTextStream:
    def __init__(self, thread_id: str) -> None:
        self.thread_id = thread_id
        self._raw = ""
        self._emitted = ""

    async def __call__(self, delta: str, label: str) -> None:
        if not delta:
            return
        self._raw += delta
        sanitized = _sanitize_user_output(self._raw)
        flush_index = _stream_flush_index(sanitized, len(self._emitted))
        if flush_index <= len(self._emitted):
            return
        chunk = sanitized[len(self._emitted) : flush_index]
        self._emitted = sanitized[:flush_index]
        await _publish_text_delta(self.thread_id, chunk, label)

    async def flush(self) -> None:
        sanitized = _sanitize_user_output(self._raw)
        if len(sanitized) <= len(self._emitted):
            return
        chunk = sanitized[len(self._emitted) :]
        self._emitted = sanitized
        await _publish_text_delta(self.thread_id, chunk, "final_flush")


async def _drain_graph_stream(
    thread_id: str,
    payload: object,
    *,
    mode: str,
) -> None:
    record = _RUNS[thread_id]
    record.update({"status": "running", "mode": mode, "error": None})
    visible_stream = _UserVisibleTextStream(thread_id)
    token = set_text_stream_callback(visible_stream)
    heartbeat_task = asyncio.create_task(_stream_state_heartbeat(thread_id, mode=mode))
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
            await _publish_state_event(thread_id, mode=mode)
        pending = _pending_interrupt_value(thread_id)
        record["status"] = "interrupt" if pending else "completed"
        record["finished_at"] = time.time()
    except Exception as exc:  # pragma: no cover - exercised through API contract
        record["status"] = "error"
        record["error"] = f"{type(exc).__name__}: {exc}"
        record["finished_at"] = time.time()
    finally:
        heartbeat_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await heartbeat_task
        reset_text_stream_callback(token)
        await visible_stream.flush()
        await _stream_queue(record).put(_STREAM_DONE)


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
    record["stream_queue"] = asyncio.Queue()
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
            payload = Command(resume=_feedback_signal(req.message))
            mode = "resume"
        else:
            payload = {"messages": [HumanMessage(content=req.message)]}
            mode = "message"
        _start_background_run(req.thread_id, payload, mode=mode)
        return _current_state_payload(req.thread_id, mode=mode)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


def _sse_event(event_type: str, data: dict[str, Any]) -> str:
    payload = json.dumps(data, ensure_ascii=False, default=str)
    return f"event: {event_type}\ndata: {payload}\n\n"


async def _stream_run_events(thread_id: str, mode: str):
    yield _sse_event("state", _current_state_payload(thread_id, mode=mode))
    record = _RUNS.get(thread_id) or {}
    queue = _stream_queue(record)
    while True:
        item = await queue.get()
        if item is _STREAM_DONE:
            break
        if not isinstance(item, dict):
            continue
        event_type = str(item.get("event") or "message")
        data = item.get("data") if isinstance(item.get("data"), dict) else {}
        yield _sse_event(event_type, data)
    final_payload = _current_state_payload(thread_id, mode=mode)
    event_type = "error" if final_payload.get("status") == "error" else "final"
    yield _sse_event(event_type, final_payload)


@router.post("/chat/runs/stream")
async def start_chat_run_stream(req: ChatRequest) -> StreamingResponse:
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
            payload = Command(resume=_feedback_signal(req.message))
            mode = "resume"
        else:
            payload = {"messages": [HumanMessage(content=req.message)]}
            mode = "message"
        _start_background_run(req.thread_id, payload, mode=mode)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return StreamingResponse(
        _stream_run_events(req.thread_id, mode),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


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
            result = await graph.ainvoke(
                Command(resume=_feedback_signal(req.message)), config=config
            )
            return _response_payload(req, result, mode="resume")

        result = await graph.ainvoke(
            {"messages": [HumanMessage(content=req.message)]},
            config=config,
        )
        return _response_payload(req, result, mode="message")
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
