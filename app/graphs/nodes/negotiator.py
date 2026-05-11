import json
import os
import re
from typing import Any

from langchain_core.messages import AIMessage, SystemMessage

from app.core.llm_client import get_chat_model
from app.schemas.state import AgentState


COMPACT_FIELDS = (
    "school_name",
    "school_province",
    "school_city",
    "major_name",
    "min_score",
    "min_rank",
    "tier",
    "ranking",
    "risk_level",
    "score_margin",
    "rank_gap",
    "tuition",
    "tuition_delta",
    "major_strength_rank",
    "major_strength_rating",
    "major_strength_level",
    "quality_score",
    "quality_gain",
    "quality_tier",
    "best_major_rank",
    "best_rating",
    "has_key_major",
    "has_featured_major",
    "quality_evidence_sources",
    "outcome_score",
    "outcome_gain",
    "outcome_tier",
    "employment_rank",
    "employment_rank_desc",
    "employment_top_city",
    "top_industry",
    "job_distribution",
    "salary_distribution",
    "employment_evidence_sources",
    "region_relax_strategy",
    "region_tree_type",
    "source_region_node_id",
    "source_region_name",
    "target_region_node_id",
    "target_region_name",
    "region_tree_confidence",
    "region_tree_evidence",
)

MAJOR_NOTE_PATTERN = re.compile(
    r"[\(（][^()（）]*(?:学院|校区|班|方向)[^()（）]*[\)）]"
)


def _display_major(value: Any) -> str:
    text = str(value or "")
    cleaned = MAJOR_NOTE_PATTERN.sub("", text).strip()
    return cleaned or text


def _compact(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    compacted = []
    for row in rows[:5]:
        item = {
            "school": row.get("school_name") or row.get("school"),
            "province": row.get("school_province") or row.get("province"),
            "city": row.get("school_city") or row.get("city"),
            "major": row.get("major_name") or row.get("major"),
        }
        for key in COMPACT_FIELDS:
            value = row.get(key)
            if value is not None:
                item[key] = value
        compacted.append(item)
    return compacted


def _score_text(row: dict[str, Any]) -> str:
    parts = [
        str(row.get("school") or row.get("school_name") or ""),
        f"({row.get('province') or row.get('school_province') or ''}/{row.get('city') or row.get('school_city') or ''})",
        _display_major(row.get("major") or row.get("major_name") or ""),
        f"min_score={row.get('min_score')}",
    ]
    if row.get("min_rank") is not None:
        parts.append(f"min_rank={row.get('min_rank')}")
    if row.get("tier") is not None:
        parts.append(f"tier={row.get('tier')}")
    if row.get("ranking") is not None:
        parts.append(f"ranking={row.get('ranking')}")
    return " ".join(part for part in parts if part)


def _join(rows: list[dict[str, Any]], *, limit: int = 3) -> str:
    if not rows:
        return "no verified option"
    return "；".join(_score_text(row) for row in rows[:limit])


def _fallback_reply(evidence: dict[str, Any]) -> str:
    major_quality = evidence.get("major_quality_relax") or []
    tuition = evidence.get("tuition_value_relax") or []
    employment = evidence.get("employment_outcome_relax") or []
    region_tree = evidence.get("region_tree_relax") or []
    risk = evidence.get("risk_band_relax") or []

    if major_quality:
        text = "；".join(
            f"{_score_text(row)} quality_score={row.get('quality_score')} "
            f"quality_gain={row.get('quality_gain')} best_major_rank={row.get('best_major_rank')} "
            f"best_rating={row.get('best_rating')}"
            for row in major_quality[:3]
        )
        return (
            "我先不替你做决定，只给出可核验的专业质量证据。\n"
            f"major_quality_relax：{text}\n"
            "这些候选仍需满足分数、选科和预算等硬约束，差异在于专业排名、学科评估、特色重点或满意度证据更强。"
        )

    if tuition:
        text = "；".join(
            f"{_score_text(row)} tuition={row.get('tuition')} "
            f"tuition_delta={row.get('tuition_delta')}"
            for row in tuition[:3]
        )
        return (
            "我先不替你做决定，只给出可核验的学费性价比证据。\n"
            f"tuition_value_relax：{text}\n"
            "这些方案只是在原预算附近小幅放宽学费，学校收益仍按 tier/ranking 与最低分证据判断。"
        )

    if employment:
        text = "；".join(
            f"{_score_text(row)} outcome_score={row.get('outcome_score')} "
            f"outcome_gain={row.get('outcome_gain')} employment_rank={row.get('employment_rank')} "
            f"top_industry={row.get('top_industry')} salary={row.get('salary_distribution')}"
            for row in employment[:3]
        )
        return (
            "我先不替你做决定，只给出可核验的就业结果证据。\n"
            f"employment_outcome_relax：{text}\n"
            "这些候选仍需满足分数、选科和预算等硬约束，差异在于就业排名、行业、岗位或薪资证据更清楚。"
        )

    if region_tree:
        text = "；".join(
            f"{_score_text(row)} strategy={row.get('region_relax_strategy')} "
            f"region={row.get('source_region_name')}->{row.get('target_region_name')} "
            f"confidence={row.get('region_tree_confidence')}"
            for row in region_tree[:3]
        )
        return (
            "我先不替你做决定，只给出可核验的地域树证据。\n"
            f"region_tree_relax：{text}\n"
            "这里的地域证据来自 reviewed region tree；城市层级本身不直接计入收益，学校收益仍按 tier/ranking 改善计算。"
        )

    if risk:
        text = "；".join(
            f"{_score_text(row)} risk={row.get('risk_level')} "
            f"score_margin={row.get('score_margin')} rank_gap={row.get('rank_gap')}"
            for row in risk[:6]
        )
        return (
            "我先不替你做决定，只给出可核验的冲稳保证据。\n"
            f"risk_band_relax：{text}\n"
            "这些方案保留地域、专业、选科和预算，只把单一保守偏好放宽成 chong/wen/bao 组合。"
        )

    sections = {
        "city_relax": _join(evidence.get("city_relax") or []),
        "geo_relax": _join(evidence.get("geo_relax") or []),
        "major_relax": _join(evidence.get("major_relax") or []),
        "strength_relax": _join(evidence.get("strength_relax") or []),
        "major_geo_relax": _join(evidence.get("major_geo_relax") or [], limit=5),
    }
    return (
        "我先不替你做决定，只给出可核验的 Pareto 放宽证据。\n"
        + "\n".join(f"{name}：{value}" for name, value in sections.items())
        + "\n你可以先挑一个最不排斥的方向，我再继续收窄。"
    )


def _fallback_reply_v2(evidence: dict[str, Any]) -> str:
    """Fallback reply that can expose two opportunity axes in one turn."""

    major_quality = evidence.get("major_quality_relax") or []
    tuition = evidence.get("tuition_value_relax") or []
    employment = evidence.get("employment_outcome_relax") or []
    region_tree = evidence.get("region_tree_relax") or []
    risk = evidence.get("risk_band_relax") or []
    major_geo = evidence.get("major_geo_relax") or []
    city = evidence.get("city_relax") or []
    geo = evidence.get("geo_relax") or []
    major = evidence.get("major_relax") or []
    strength = evidence.get("strength_relax") or []
    rankings = [
        str(item)
        for item in evidence.get("opportunity_rankings", [])
        if isinstance(item, str)
    ]
    clarification_hint = evidence.get("clarification_hint")

    def section_major_geo() -> str:
        rows = major_geo or geo or major or city
        return (
            "major_geo_relax: "
            + _join(rows, limit=5)
            + "\nThis is a joint major/region Pareto opportunity with real min_score evidence."
        )

    def section_risk() -> str:
        text = "; ".join(
            f"{_score_text(row)} risk={row.get('risk_level')} "
            f"score_margin={row.get('score_margin')} rank_gap={row.get('rank_gap')}"
            for row in risk[:6]
        )
        return (
            "risk_band_relax: "
            + text
            + "\nThese options expand one conservative preference into a chong/wen/bao portfolio."
        )

    def section_quality() -> str:
        text = "; ".join(
            f"{_score_text(row)} quality_score={row.get('quality_score')} "
            f"quality_gain={row.get('quality_gain')} best_major_rank={row.get('best_major_rank')} "
            f"best_rating={row.get('best_rating')}"
            for row in major_quality[:3]
        )
        return (
            "major_quality_relax: "
            + text
            + "\nThis section uses school-major quality evidence while score constraints remain checked."
        )

    def section_tuition() -> str:
        text = "; ".join(
            f"{_score_text(row)} tuition={row.get('tuition')} "
            f"tuition_delta={row.get('tuition_delta')}"
            for row in tuition[:3]
        )
        return (
            "tuition_value_relax: "
            + text
            + "\nThe budget is relaxed only in a small audited window with school/ranking evidence."
        )

    def section_employment() -> str:
        text = "; ".join(
            f"{_score_text(row)} outcome_score={row.get('outcome_score')} "
            f"outcome_gain={row.get('outcome_gain')} employment_rank={row.get('employment_rank')} "
            f"top_industry={row.get('top_industry')} salary={row.get('salary_distribution')}"
            for row in employment[:3]
        )
        return (
            "employment_outcome_relax: "
            + text
            + "\nThis section uses structured employment outcome evidence: rank, industry, job, or salary."
        )

    def section_region() -> str:
        text = "; ".join(
            f"{_score_text(row)} strategy={row.get('region_relax_strategy')} "
            f"region={row.get('source_region_name')}->{row.get('target_region_name')} "
            f"confidence={row.get('region_tree_confidence')}"
            for row in region_tree[:3]
        )
        return (
            "region_tree_relax: "
            + text
            + "\nRegion nodes come from reviewed region trees; city tier itself is not counted as Pareto gain."
        )

    sections_by_key = {
        "major_geo_relax": lambda: (
            section_major_geo() if (major_geo or geo or major or city) else ""
        ),
        "geo_relax": lambda: (
            section_major_geo() if (major_geo or geo or major or city) else ""
        ),
        "major_relax": lambda: (
            section_major_geo() if (major_geo or geo or major or city) else ""
        ),
        "city_relax": lambda: (
            section_major_geo() if (major_geo or geo or major or city) else ""
        ),
        "risk_band_relax": lambda: section_risk() if risk else "",
        "major_quality_relax": lambda: section_quality() if major_quality else "",
        "tuition_value_relax": lambda: section_tuition() if tuition else "",
        "employment_outcome_relax": lambda: section_employment() if employment else "",
        "region_tree_relax": lambda: section_region() if region_tree else "",
        "strength_relax": lambda: (
            "strength_relax: " + _join(strength) if strength else ""
        ),
    }
    ranked_sections: list[str] = []
    for key in rankings:
        factory = sections_by_key.get(key)
        if factory is None:
            continue
        section = factory()
        if section and section not in ranked_sections:
            ranked_sections.append(section)

    if len(ranked_sections) >= 2:
        selected = ranked_sections[:2]
    elif (major_geo or geo or major or city) and risk:
        selected = [section_major_geo(), section_risk()]
    elif major_quality and tuition:
        selected = [section_quality(), section_tuition()]
    elif employment and region_tree:
        selected = [section_employment(), section_region()]
    else:
        candidates = [
            (bool(major_quality), section_quality),
            (bool(tuition), section_tuition),
            (bool(employment), section_employment),
            (bool(region_tree), section_region),
            (bool(risk), section_risk),
            (bool(major_geo or geo or major or city), section_major_geo),
            (bool(strength), lambda: "strength_relax: " + _join(strength)),
        ]
        selected = [factory() for present, factory in candidates if present][:2]

    if not selected:
        selected = [
            "No verified Pareto opportunity was found beyond the current hard constraints."
        ]

    option_labels = ["\u9009\u9879A", "\u9009\u9879B"]
    labelled_selected = [
        f"{option_labels[index]}: {section}" if index < len(option_labels) else section
        for index, section in enumerate(selected)
    ]
    prefix = ""
    if clarification_hint:
        prefix = f"Clarification hint: {clarification_hint}\n\n"

    return (
        prefix
        + "I will not decide for you; I will only expose auditable Pareto evidence.\n"
        + "\n\n".join(labelled_selected)
        + "\n\nAgent input is limited to explicit user constraints and verified DB evidence."
    )


async def negotiator_node(state: AgentState) -> dict[str, Any]:
    print("[negotiator] generating options")
    opportunities = state.get("pareto_opportunities", {})
    evidence = {
        "constraints": state.get("constraints", {}),
        "normalized_intent": state.get("normalized_intent", {}),
        "probe_plan": state.get("probe_plan", []),
        "opportunity_rankings": state.get("opportunity_rankings", []),
        "clarification_hint": state.get("clarification_hint"),
        "baseline_results": _compact(state.get("baseline_results", [])),
        "geo_relax": _compact(opportunities.get("geo_relax", [])),
        "city_relax": _compact(opportunities.get("city_relax", [])),
        "major_relax": _compact(opportunities.get("major_relax", [])),
        "strength_relax": _compact(opportunities.get("strength_relax", [])),
        "major_quality_relax": _compact(opportunities.get("major_quality_relax", [])),
        "tuition_value_relax": _compact(opportunities.get("tuition_value_relax", [])),
        "employment_outcome_relax": _compact(
            opportunities.get("employment_outcome_relax", [])
        ),
        "region_tree_relax": _compact(opportunities.get("region_tree_relax", [])),
        "major_geo_relax": _compact(opportunities.get("major_geo_relax", [])),
        "risk_band_relax": _compact(opportunities.get("risk_band_relax", [])),
    }

    if os.getenv("GAOKAOLLM_OFFLINE_DETERMINISTIC") == "1":
        return {"messages": [AIMessage(content=_fallback_reply_v2(evidence))]}

    llm = get_chat_model()
    prompt = [
        SystemMessage(
            content=(
                "你是高考志愿谈判 Agent。只能基于给定真实数据说话。"
                "输出简洁中文，不替用户做最终决定。"
                "如果存在 region_tree_relax，要说明这是按地理板块树或城市层级树的可审计地域放宽。"
                "如果存在 major_geo_relax，要重点说明专业和地域联合放宽。"
                "如果存在 risk_band_relax，要说明 chong/wen/bao 组合。"
                "必须给出具体学校、专业、最低分，并在可用时给出最低位次、树节点、学费、专业质量或就业证据。"
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
        content = _fallback_reply_v2(evidence)
    return {"messages": [AIMessage(content=content)]}
