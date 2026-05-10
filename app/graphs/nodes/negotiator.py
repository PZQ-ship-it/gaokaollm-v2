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
                "city": row.get("school_city"),
                "major": row.get("major_name"),
                "min_score": row.get("min_score"),
                "min_rank": row.get("min_rank"),
                "tier": row.get("tier"),
                "ranking": row.get("ranking"),
                "risk_level": row.get("risk_level"),
                "score_margin": row.get("score_margin"),
                "rank_gap": row.get("rank_gap"),
                "tuition": row.get("tuition"),
                "tuition_delta": row.get("tuition_delta"),
                "major_strength_rank": row.get("major_strength_rank"),
                "major_strength_rating": row.get("major_strength_rating"),
                "major_strength_level": row.get("major_strength_level"),
                "quality_score": row.get("quality_score"),
                "quality_gain": row.get("quality_gain"),
                "quality_tier": row.get("quality_tier"),
                "best_major_rank": row.get("best_major_rank"),
                "best_rating": row.get("best_rating"),
                "has_key_major": row.get("has_key_major"),
                "has_featured_major": row.get("has_featured_major"),
                "quality_evidence_sources": row.get("quality_evidence_sources"),
            }
        )
    return compacted


def _fallback_reply(evidence: dict[str, Any]) -> str:
    geo = evidence.get("geo_relax") or []
    city = evidence.get("city_relax") or []
    major = evidence.get("major_relax") or []
    strength = evidence.get("strength_relax") or []
    major_quality = evidence.get("major_quality_relax") or []
    tuition = evidence.get("tuition_value_relax") or []
    joint = evidence.get("major_geo_relax") or []
    risk = evidence.get("risk_band_relax") or []

    def _line(row: dict[str, Any]) -> str:
        return (
            f"{row.get('school')}（{row.get('province')}）"
            f"{row.get('major')}，最低分 {row.get('min_score')}，"
            f"层次 {row.get('tier')}"
        )

    city_text = "暂时没有发现换到其他城市后的更高层次机会。"
    if city:
        city_text = "；".join(_line(row) for row in city[:3])

    geo_text = "暂时没有发现比当前硬约束更高层次的地域放宽机会。"
    if geo:
        geo_text = "；".join(_line(row) for row in geo[:3])

    major_text = "暂时没有发现比当前硬约束更高层次的专业放宽机会。"
    if major:
        major_text = "；".join(_line(row) for row in major[:3])

    strength_text = "暂时没有发现学科实力更强的志愿组合。"
    if strength:
        strength_text = "；".join(
            f"{row.get('school')}({row.get('province')}) "
            f"{row.get('major')} strength_rank={row.get('major_strength_rank')} "
            f"rating={row.get('major_strength_rating')} min_score={row.get('min_score')}"
            for row in strength[:3]
        )

    major_quality_text = "暂时没有发现专业质量证据更强的可达方案。"
    if major_quality:
        major_quality_text = "；".join(
            f"{row.get('school')}({row.get('province')}) "
            f"{row.get('major')} quality={row.get('quality_score')} "
            f"gain={row.get('quality_gain')} rank={row.get('best_major_rank')} "
            f"rating={row.get('best_rating')} min_score={row.get('min_score')}"
            for row in major_quality[:3]
        )
        return (
            "我先不替你做决定，只把可核验的数据摆出来。\n"
            "专业质量方案：如果你愿意比较省外同专业或近似同专业，可以重点看："
            f"{major_quality_text}\n"
            "这些候选仍需满足你的分数、专业、选科和预算约束，区别在于专业排名、学科评估、"
            "特色/重点专业或满意度证据更强。"
        )

    tuition_text = "暂时没有发现小幅增加学费后的明显性价比跃迁。"
    if tuition:
        tuition_text = "；".join(
            f"{row.get('school')}({row.get('province')}) "
            f"{row.get('major')} min_score={row.get('min_score')} "
            f"tuition={row.get('tuition')} delta={row.get('tuition_delta')} "
            f"tier={row.get('tier')} ranking={row.get('ranking')}"
            for row in tuition[:3]
        )
        return (
            "我先不替你做决定，只把可核验的数据摆出来。\n"
            "学费方案：如果每年小幅增加预算，可以比较："
            f"{tuition_text}\n"
            "这些方案仍然需要满足你的分数、专业和选科约束，你可以先看学费增量是否能接受。"
        )

    joint_text = "暂时没有发现同时放宽地域和专业后的更高层次机会。"
    if joint:
        joint_text = "；".join(_line(row) for row in joint[:5])

    risk_text = "暂时没有发现满足当前硬约束的冲稳保组合。"
    if risk:
        risk_text = "；".join(
            f"{row.get('school')}({row.get('province')}) "
            f"{row.get('major')} min_score={row.get('min_score')} "
            f"risk={row.get('risk_level')} margin={row.get('score_margin')}"
            for row in risk[:6]
        )
        return (
            "我先不替你做决定，只把可核验的数据摆出来。\n"
            "风险方案：在不改变地域、专业、选科和预算的前提下，"
            f"如果把“只求稳”放宽为冲稳保组合，可以比较：{risk_text}\n"
            "你可以先看这些风险层级是否能接受，我再继续收窄。"
        )

    return (
        "我先不替你做决定，只把可核验的数据摆出来。\n"
        f"城市方案：如果不限定当前城市，可以比较：{city_text}\n"
        f"选项A：如果只放松地域，可以比较：{geo_text}\n"
        f"选项B：如果只放松专业，可以比较：{major_text}\n"
        f"学科实力方案：如果更看重专业排名或重点学科，可以比较：{strength_text}\n"
        f"专业质量方案：如果更看重该专业本身的排名、评估或特色重点证据，可以比较：{major_quality_text}\n"
        f"学费方案：如果每年小幅增加预算，可以比较：{tuition_text}\n"
        f"联合方案：如果同时放宽地域和专业，可以重点比较：{joint_text}\n"
        f"风险方案：如果保留地域、专业、选科和预算，只把“只求稳”放宽为冲稳保组合，可以比较：{risk_text}\n"
        "你可以先挑一个最不排斥的方向，我再继续收窄。"
    )


async def negotiator_node(state: AgentState) -> dict[str, Any]:
    print("[negotiator] generating options")
    opportunities = state.get("pareto_opportunities", {})
    evidence = {
        "constraints": state.get("constraints", {}),
        "baseline_results": _compact(state.get("baseline_results", [])),
        "geo_relax": _compact(opportunities.get("geo_relax", [])),
        "city_relax": _compact(opportunities.get("city_relax", [])),
        "major_relax": _compact(opportunities.get("major_relax", [])),
        "strength_relax": _compact(opportunities.get("strength_relax", [])),
        "major_quality_relax": _compact(opportunities.get("major_quality_relax", [])),
        "tuition_value_relax": _compact(opportunities.get("tuition_value_relax", [])),
        "major_geo_relax": _compact(opportunities.get("major_geo_relax", [])),
        "risk_band_relax": _compact(opportunities.get("risk_band_relax", [])),
    }

    llm = get_chat_model()
    prompt = [
        SystemMessage(
            content=(
                "你是高考志愿谈判官。只能基于给定真实数据说话。"
                "输出一个简洁中文回复，必须包含“选项A”和“选项B”。"
                "选项A对应放松地域，选项B对应放松专业；不要替用户做最终决定。"
                "如果 evidence 中存在 city_relax，要说明这是只放宽精确城市限制后的方案，"
                "如果 evidence 中存在 major_geo_relax，要把它作为联合放宽方案重点说明，"
                "如果 evidence 中存在 strength_relax，要说明这是在保持省份和专业前提下的学科实力跃迁方案，"
                "如果 evidence 中存在 major_quality_relax，要说明这是同专业或近似同专业下的专业质量跃迁方案，"
                "如果 evidence 中存在 tuition_value_relax，要说明这是只小幅放宽每年学费预算后的性价比方案，"
                "如果 evidence 中存在 risk_band_relax，要说明这是在不改变地域、专业、选科和预算时的冲稳保组合，"
                "并给出具体学校、专业、最低分、专业排名/学科评估/特色重点或满意度证据。"
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
