from fastapi import APIRouter
from langchain_core.messages import HumanMessage

from app.graphs.workflow import build_graph
from app.schemas.models import ChatRequest


router = APIRouter(prefix="/api/v1", tags=["chat"])
graph = build_graph()


@router.post("/chat")
async def chat(req: ChatRequest) -> dict:
    result = await graph.ainvoke(
        {"messages": [HumanMessage(content=req.message)]},
        config={"configurable": {"thread_id": req.thread_id}},
    )
    last_message = result["messages"][-1]
    return {
        "thread_id": req.thread_id,
        "reply": str(last_message.content),
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
    }
