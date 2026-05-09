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


def _fallback_reply(evidence: dict[str, Any]) -> str:
    geo = evidence.get("geo_relax") or []
    major = evidence.get("major_relax") or []

    def _line(row: dict[str, Any]) -> str:
        return (
            f"{row.get('school')}（{row.get('province')}）"
            f"{row.get('major')}，最低分 {row.get('min_score')}，"
            f"层次 {row.get('tier')}"
        )

    geo_text = "暂时没有发现比当前硬约束更高层次的地域放宽机会。"
    if geo:
        geo_text = "；".join(_line(row) for row in geo[:3])

    major_text = "暂时没有发现比当前硬约束更高层次的专业放宽机会。"
    if major:
        major_text = "；".join(_line(row) for row in major[:3])

    return (
        "我先不替你做决定，只把可核验的数据摆出来。\n"
        f"选项A：如果只放松地域，可以比较：{geo_text}\n"
        f"选项B：如果只放松专业，可以比较：{major_text}\n"
        "你可以先挑一个最不排斥的方向，我再继续收窄。"
    )


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
    try:
        response = await llm.ainvoke(prompt)
        content = str(response.content)
    except Exception as exc:
        print(
            "[negotiator] llm_generation_failed="
            f"{type(exc).__name__}; using fallback reply"
        )
        content = _fallback_reply(evidence)
    return {"messages": [AIMessage(content=content)]}
