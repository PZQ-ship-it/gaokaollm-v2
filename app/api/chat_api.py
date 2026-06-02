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


def _pending_interrupt_value(thread_id: str) -> object | None:
    snapshot = graph.get_state({"configurable": {"thread_id": thread_id}})
    for task in snapshot.tasks or ():
        interrupts = getattr(task, "interrupts", None) or ()
        if not interrupts:
            continue
        value = getattr(interrupts[0], "value", None)
        return value if value is not None else interrupts[0]
    return None


async def _apply_feedback_update(req: ChatRequest, pending_value: object) -> dict:
    config = {"configurable": {"thread_id": req.thread_id}}
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


def _response_payload(
    req: ChatRequest,
    result: dict,
    *,
    mode: str,
    include_pending: bool = True,
) -> dict:
    interrupt_value = _interrupt_value(result)
    pending_value = (
        interrupt_value or _pending_interrupt_value(req.thread_id)
        if include_pending
        else None
    )
    pending_meta = _interrupt_meta(pending_value)
    pending_interrupt = _interrupt_text_from_value(pending_value)
    reply = pending_interrupt or result.get("latest_agent_probe_question")
    messages = result.get("messages") or []
    if not reply and messages:
        reply = str(messages[-1].content)
    if mode == "feedback":
        navigation_intent = result.get("navigation_intent")
        if navigation_intent == "finalize":
            reply = "正在基于当前偏好生成最终推荐。"
        elif navigation_intent == "continue":
            reply = "正在换一个方向继续比较。"
        else:
            reply = "偏好已更新。"
    return {
        "thread_id": req.thread_id,
        "mode": mode,
        "status": "interrupt" if pending_interrupt else "completed",
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


@router.post("/chat")
async def chat(req: ChatRequest) -> dict:
    config = {"configurable": {"thread_id": req.thread_id}}
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
