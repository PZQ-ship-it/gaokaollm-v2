"""Target-agent adapters used by offline benchmark runs."""

from __future__ import annotations

import re
from typing import Any

from app.flows.probers import run_baseline
from gaokaollm_bench.sandbox.base_target import BaseTargetAgent


class AppGraphTargetAgent(BaseTargetAgent):
    """Expose the production LangGraph app through the benchmark target contract."""

    def __init__(self, *, thread_id: str, graph: Any | None = None) -> None:
        self.thread_id = thread_id
        if graph is None:
            from app.graphs.workflow import build_graph

            graph = build_graph()
        self.graph = graph

    async def chat(self, user_input: str) -> tuple[str, dict[str, Any]]:
        try:
            from langchain_core.messages import HumanMessage

            message: Any = HumanMessage(content=user_input)
        except ImportError:
            message = _HumanMessageFallback(content=user_input)

        result = await self.graph.ainvoke(
            {"messages": [message]},
            config={"configurable": {"thread_id": self.thread_id}},
        )
        messages = result.get("messages", [])
        reply = str(getattr(messages[-1], "content", "")) if messages else ""
        return reply, _state_from_graph_result(result)


class HardConstraintBaselineAgent(BaseTargetAgent):
    """A non-negotiating baseline that only reports hard-constraint results."""

    def __init__(self, *, db: Any = None, limit: int = 3) -> None:
        self.db = db
        self.limit = limit
        self.constraints: dict[str, Any] = {}

    async def chat(self, user_input: str) -> tuple[str, dict[str, Any]]:
        extracted = _fallback_extract_constraints(user_input)
        self.constraints = _merge_constraints(self.constraints, extracted)
        missing = _missing_required_constraints(self.constraints)
        if missing:
            reply = _missing_constraints_reply(missing)
            return reply, {
                "target": "hard_constraint",
                "constraints": dict(self.constraints),
                "baseline_results": [],
                "pareto_opportunities": {
                    "geo_relax": [],
                    "city_relax": [],
                    "major_relax": [],
                    "strength_relax": [],
                    "major_quality_relax": [],
                    "tuition_value_relax": [],
                    "employment_outcome_relax": [],
                    "region_tree_relax": [],
                    "major_geo_relax": [],
                    "risk_band_relax": [],
                },
                "score_waste": 0,
                "missing_constraints": missing,
                "recommended_schools": [],
            }

        baseline = await run_baseline(self.constraints, db=self.db, limit=self.limit)
        reply = _baseline_reply(baseline)
        return reply, {
            "target": "hard_constraint",
            "constraints": dict(self.constraints),
            "baseline_results": baseline,
            "pareto_opportunities": {
                "geo_relax": [],
                "city_relax": [],
                "major_relax": [],
                "strength_relax": [],
                "major_quality_relax": [],
                "tuition_value_relax": [],
                "employment_outcome_relax": [],
                "region_tree_relax": [],
                "major_geo_relax": [],
                "risk_band_relax": [],
            },
            "score_waste": _score_waste(self.constraints, baseline),
            "missing_constraints": [],
            "recommended_schools": _recommended_schools(baseline),
        }


class _HumanMessageFallback:
    def __init__(self, *, content: str) -> None:
        self.content = content
        self.type = "human"


def _state_from_graph_result(result: dict[str, Any]) -> dict[str, Any]:
    baseline = list(result.get("baseline_results") or [])
    opportunities = result.get("pareto_opportunities") or {}
    return {
        "target": "app_pareto",
        "constraints": dict(result.get("constraints") or {}),
        "baseline_results": baseline,
        "pareto_opportunities": {
            "geo_relax": list(opportunities.get("geo_relax") or []),
            "city_relax": list(opportunities.get("city_relax") or []),
            "major_relax": list(opportunities.get("major_relax") or []),
            "strength_relax": list(opportunities.get("strength_relax") or []),
            "major_quality_relax": list(opportunities.get("major_quality_relax") or []),
            "tuition_value_relax": list(opportunities.get("tuition_value_relax") or []),
            "employment_outcome_relax": list(
                opportunities.get("employment_outcome_relax") or []
            ),
            "region_tree_relax": list(opportunities.get("region_tree_relax") or []),
            "major_geo_relax": list(opportunities.get("major_geo_relax") or []),
            "risk_band_relax": list(opportunities.get("risk_band_relax") or []),
        },
        "score_waste": int(result.get("score_waste") or 0),
        "missing_constraints": list(result.get("missing_constraints") or []),
        "rewritten_query": result.get("rewritten_query"),
        "intent_axes": list(result.get("intent_axes") or []),
        "probe_plan": list(result.get("probe_plan") or []),
        "opportunity_rankings": list(result.get("opportunity_rankings") or []),
        "clarification_hint": result.get("clarification_hint"),
        "recommended_schools": _recommended_schools(
            baseline,
            opportunities.get("geo_relax") or [],
            opportunities.get("city_relax") or [],
            opportunities.get("major_relax") or [],
            opportunities.get("strength_relax") or [],
            opportunities.get("major_quality_relax") or [],
            opportunities.get("tuition_value_relax") or [],
            opportunities.get("employment_outcome_relax") or [],
            opportunities.get("major_geo_relax") or [],
            opportunities.get("risk_band_relax") or [],
            opportunities.get("region_tree_relax") or [],
        ),
    }


def _recommended_schools(*groups: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    schools: list[dict[str, Any]] = []
    for rows in groups:
        for row in rows:
            name = str(row.get("school_name") or row.get("school") or "")
            if not name or name in seen:
                continue
            seen.add(name)
            item = {
                "school": name,
                "province": row.get("school_province") or row.get("province"),
                "major": row.get("major_name") or row.get("major"),
                "min_score": row.get("min_score"),
                "tier": row.get("tier"),
            }
            city = row.get("school_city") or row.get("city")
            if city is not None:
                item["city"] = city
            for key in ("risk_level", "score_margin", "rank_gap", "min_rank"):
                if row.get(key) is not None:
                    item[key] = row.get(key)
            for key in ("tuition", "tuition_delta"):
                if row.get(key) is not None:
                    item[key] = row.get(key)
            for key in (
                "major_strength_rank",
                "major_strength_rating",
                "major_strength_level",
            ):
                if row.get(key) is not None:
                    item[key] = row.get(key)
            for key in (
                "quality_score",
                "quality_gain",
                "quality_tier",
                "best_major_rank",
                "best_rating",
                "has_key_major",
                "has_featured_major",
                "quality_evidence_sources",
            ):
                if row.get(key) is not None:
                    item[key] = row.get(key)
            for key in (
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
            ):
                if row.get(key) is not None:
                    item[key] = row.get(key)
            schools.append(item)
    return schools


def _score_waste(
    constraints: dict[str, Any],
    baseline: list[dict[str, Any]],
) -> int:
    if not baseline or constraints.get("score") is None:
        return 0
    try:
        return int(constraints["score"]) - int(float(baseline[0]["min_score"]))
    except (KeyError, TypeError, ValueError):
        return 0


def _fallback_extract_constraints(text: str) -> dict[str, Any]:
    extracted: dict[str, Any] = {}
    score_match = re.search(r"(\d{3})", text)
    if score_match:
        extracted["score"] = int(score_match.group(1))

    budget_patterns = (
        r"(?:预算|学费|费用|一年|每年)[^\d]{0,8}(\d{4,6})",
        r"(\d{4,6})\s*(?:元)?\s*(?:以内|以下|封顶)",
    )
    for pattern in budget_patterns:
        budget_match = re.search(pattern, text)
        if budget_match:
            extracted["budget"] = int(budget_match.group(1))
            break

    province_names = (
        "北京",
        "上海",
        "天津",
        "重庆",
        "浙江",
        "江苏",
        "广东",
        "山东",
        "湖北",
        "湖南",
        "四川",
        "陕西",
        "新疆",
        "西藏",
    )
    for province in province_names:
        if province in text:
            extracted["province"] = province
            break

    city_names = (
        "杭州",
        "宁波",
        "温州",
        "嘉兴",
        "湖州",
        "绍兴",
        "金华",
        "台州",
        "南京",
        "苏州",
        "无锡",
        "上海",
        "北京",
    )
    for city in city_names:
        if city in text:
            extracted["city"] = city
            break

    if any(
        token in text
        for token in (
            "全国",
            "地域不限",
            "地区不限",
            "外省也可以",
            "外省也可考虑",
            "可以出省",
            "接受外省",
        )
    ):
        extracted["province"] = None

    if "临床" in text:
        extracted["major"] = "临床医学"
    elif "计算机" in text:
        extracted["major"] = "计算机"
    elif "法学" in text:
        extracted["major"] = "法学"
    else:
        major_match = re.search(r"(?:想读|想学|报考|读)([^，,。；;\s]{2,30})", text)
        if major_match:
            major = re.split(
                r"(?:每年|学费|预算|以内|以下|太贵|地域|地区)",
                major_match.group(1),
                maxsplit=1,
            )[0].strip("，,。；; ")
            if major:
                extracted["major"] = major

    subjects = _extract_subjects(text)
    if subjects:
        extracted["selected_subjects"] = subjects

    compact = re.sub(r"\s+", "", text).lower()
    conservative_tokens = (
        "conservative",
        "lowrisk",
        "稳妥",
        "保守",
        "只求稳",
        "不要冲",
        "不接受冲",
    )
    if any(token in compact for token in conservative_tokens):
        extracted["risk_preference"] = "conservative"

    if any(
        token in text
        for token in (
            "就业",
            "好就业",
            "薪资",
            "工资",
            "行业",
            "岗位",
            "职业",
            "就业去向",
            "employment",
            "salary",
            "job",
            "career",
        )
    ):
        extracted["employment_preference"] = "employment_outcome"

    return extracted


def _extract_subjects(text: str) -> list[str]:
    aliases = {
        "政": "政治",
        "政治": "政治",
        "史": "历史",
        "历": "历史",
        "历史": "历史",
        "地": "地理",
        "地理": "地理",
        "物": "物理",
        "物理": "物理",
        "化": "化学",
        "化学": "化学",
        "生": "生物",
        "生物": "生物",
        "技": "技术",
        "技术": "技术",
    }
    compact = re.sub(r"\s+", "", text)
    compact = (
        compact.replace("地域不限", "")
        .replace("地区不限", "")
        .replace("地域不限制", "")
        .replace("地区不限制", "")
    )
    subjects: list[str] = []
    for alias, subject in aliases.items():
        if alias in compact and subject not in subjects:
            subjects.append(subject)
    return subjects[:3]


def _merge_constraints(
    current: dict[str, Any],
    extracted: dict[str, Any],
) -> dict[str, Any]:
    merged = {
        "score": None,
        "province": "浙江",
        "city": None,
        "major": None,
        "budget": 100000,
        "selected_subjects": None,
        "risk_preference": None,
        "employment_preference": None,
        **(current or {}),
    }
    for key in (
        "score",
        "province",
        "city",
        "major",
        "budget",
        "selected_subjects",
        "risk_preference",
        "employment_preference",
    ):
        if key in extracted and extracted[key] not in ("", []):
            merged[key] = extracted[key]
    return merged


def _missing_required_constraints(constraints: dict[str, Any]) -> list[str]:
    missing = []
    if not constraints.get("score"):
        missing.append("score")
    if not constraints.get("selected_subjects"):
        missing.append("selected_subjects")
    return missing


def _missing_constraints_reply(missing: list[str]) -> str:
    labels = {
        "score": "高考分数",
        "selected_subjects": "3门选考科目",
    }
    return "我还需要补充：" + "；".join(labels[item] for item in missing) + "。"


def _baseline_reply(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return "按你当前坚持的硬约束，我暂时没有找到可直接推荐的志愿。"
    lines = ["按你当前坚持的硬约束，可直接考虑："]
    for row in rows[:3]:
        lines.append(
            f"- {row.get('school_name')}｜{row.get('school_province')}｜"
            f"{row.get('major_name')}｜最低分 {row.get('min_score')}"
        )
    return "\n".join(lines)
