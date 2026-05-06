import json
from typing import Any

from langchain_core.messages import AIMessage, SystemMessage

from app.core.llm_client import get_chat_model
from app.schemas.state import AgentState


def _compact(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    compacted = []
    for row in rows[:5]:
        compacted.append(
            {
                "school": row.get("school_name"),
                "province": row.get("school_province"),
                "major": row.get("major_name"),
                "min_score": row.get("min_score"),
                "tier": row.get("tier"),
                "ranking": row.get("ranking"),
            }
        )
    return compacted


async def negotiator_node(state: AgentState) -> dict[str, Any]:
    print("[negotiator] generating options")
    opportunities = state.get("pareto_opportunities", {})
    evidence = {
        "constraints": state.get("constraints", {}),
        "baseline_results": _compact(state.get("baseline_results", [])),
        "geo_relax": _compact(opportunities.get("geo_relax", [])),
        "major_relax": _compact(opportunities.get("major_relax", [])),
    }

    llm = get_chat_model()
    prompt = [
        SystemMessage(
            content=(
                "你是高考志愿谈判官。只能基于给定真实数据说话。"
                "输出一个简洁中文回复，必须包含“选项A”和“选项B”。"
                "选项A对应放松地域，选项B对应放松专业；不要替用户做最终决定。"
            )
        ),
        SystemMessage(content=json.dumps(evidence, ensure_ascii=False, default=str)),
    ]
    response = await llm.ainvoke(prompt)
    return {"messages": [AIMessage(content=str(response.content))]}
