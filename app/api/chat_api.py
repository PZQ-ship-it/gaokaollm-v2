from fastapi import APIRouter
from langchain_core.messages import HumanMessage

from app.graphs.workflow import build_graph
from app.schemas.models import ChatRequest


router = APIRouter(prefix="/api/v1", tags=["chat"])
graph = build_graph()


def _interrupt_text(result: dict) -> str | None:
    interrupts = result.get("__interrupt__")
    if not interrupts:
        return None
    first = interrupts[0] if isinstance(interrupts, (list, tuple)) else interrupts
    value = getattr(first, "value", None)
    return str(value if value is not None else first)


@router.post("/chat")
async def chat(req: ChatRequest) -> dict:
    result = await graph.ainvoke(
        {"messages": [HumanMessage(content=req.message)]},
        config={"configurable": {"thread_id": req.thread_id}},
    )
    last_message = result["messages"][-1]
    reply = _interrupt_text(result) or result.get("latest_agent_probe_question")
    if not reply:
        reply = str(last_message.content)
    return {
        "thread_id": req.thread_id,
        "reply": reply,
        "constraints": result.get("constraints", {}),
        "baseline_results": result.get("baseline_results", []),
        "pareto_opportunities": result.get("pareto_opportunities", {}),
        "score_waste": result.get("score_waste", 0),
        "missing_constraints": result.get("missing_constraints", []),
        "rewritten_query": result.get("rewritten_query"),
        "intent_axes": result.get("intent_axes", []),
        "probe_plan": result.get("probe_plan", []),
        "opportunity_rankings": result.get("opportunity_rankings", []),
        "clarification_hint": result.get("clarification_hint"),
        "latest_agent_probe_question": result.get("latest_agent_probe_question"),
    }
