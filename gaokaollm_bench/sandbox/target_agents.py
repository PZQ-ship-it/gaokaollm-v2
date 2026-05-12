"""Target-agent adapters used by offline benchmark runs."""

from __future__ import annotations

import re
from typing import Any

from app.flows.probers import run_baseline
from app.core import db_pg
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


class V1SoftRagBaselineAgent(BaseTargetAgent):
    """A v1-style soft-constraint RAG baseline over the current DB snapshot."""

    def __init__(self, *, db: Any = None, limit: int = 9) -> None:
        self.db = db
        self.limit = limit
        self.constraints: dict[str, Any] = {}

    async def chat(self, user_input: str) -> tuple[str, dict[str, Any]]:
        normalized = _normalize_v1_query(user_input)
        extracted = _fallback_extract_constraints(normalized["rewritten_query"])
        self.constraints = _merge_constraints(self.constraints, extracted)
        missing = _missing_required_constraints(self.constraints)
        if missing:
            reply = _missing_constraints_reply(missing)
            return reply, _v1_state(
                constraints=self.constraints,
                normalized_query=normalized,
                soft_candidates=[],
                missing_constraints=missing,
            )

        soft_candidates = await _run_v1_soft_retrieval(
            self.constraints,
            db=self.db,
            limit=self.limit,
        )
        segmented = _segment_v1_candidates(self.constraints, soft_candidates)
        reply = _v1_soft_rag_reply(segmented, soft_candidates)
        return reply, _v1_state(
            constraints=self.constraints,
            normalized_query=normalized,
            soft_candidates=soft_candidates,
            segmented_candidates=segmented,
            missing_constraints=[],
        )


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


def _empty_opportunities() -> dict[str, list[Any]]:
    return {
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
    }


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


def _normalize_v1_query(text: str) -> dict[str, Any]:
    compact = re.sub(r"\s+", " ", text).strip()
    for hidden_name in (
        "implicit_flexibilities",
        "volunteer_set",
        "axis_flexibilities",
    ):
        compact = compact.replace(hidden_name, "")
    compact = re.sub(r"\s+", " ", compact).strip()
    return {
        "rewritten_query": compact,
        "preference_summary": _v1_preference_summary(compact),
        "source": "deterministic_v1_rewrite",
    }


def _v1_preference_summary(text: str) -> list[str]:
    summary: list[str] = []
    for label, tokens in {
        "专业偏好": ("专业", "想读", "想学", "计算机", "临床", "法学"),
        "地域偏好": ("省内", "浙江", "杭州", "别太远", "城市", "外省"),
        "风险偏好": ("稳", "保守", "冲", "风险"),
        "费用偏好": ("预算", "学费", "费用"),
        "就业偏好": ("就业", "薪资", "岗位", "行业"),
    }.items():
        if any(token in text for token in tokens):
            summary.append(label)
    return summary


async def _fetch_v1_rows(
    db: Any,
    query: str,
    params: list[Any],
) -> list[dict[str, Any]]:
    if db is None:
        return await db_pg.fetch_query(query, *params)
    if hasattr(db, "fetch_query"):
        return await db.fetch_query(query, *params)
    return await db(query, *params)


async def _run_v1_soft_retrieval(
    constraints: dict[str, Any],
    *,
    db: Any = None,
    limit: int = 9,
) -> list[dict[str, Any]]:
    score = int(constraints["score"])
    where = [
        "a.min_score IS NOT NULL",
        "a.min_score >= %s",
        "a.min_score <= %s",
    ]
    where_params: list[Any] = [score - 25, score + 15]
    select_params: list[Any] = []

    selected_subjects = constraints.get("selected_subjects")
    if selected_subjects:
        where.append(
            """
            (
                COALESCE(sr.requirement_type, 'unknown') = 'none'
                OR COALESCE(cardinality(sr.normalized_subjects), 0) = 0
                OR (
                    sr.requirement_type = 'all_required'
                    AND sr.normalized_subjects <@ %s::text[]
                )
                OR (
                    sr.requirement_type = 'any_required'
                    AND sr.normalized_subjects && %s::text[]
                )
            )
            """
        )
        where_params.extend([selected_subjects, selected_subjects])

    province = constraints.get("province")
    if province:
        where.append("(s.province = %s OR s.province IS NOT NULL)")
        where_params.append(province)

    major = constraints.get("major")
    major_score = "0"
    if major:
        major_score = "CASE WHEN a.major_name_raw LIKE %s THEN 4 ELSE 0 END"
        select_params.append(f"%{major}%")

    city = constraints.get("city")
    city_score = "0"
    if city:
        city_score = "CASE WHEN s.city LIKE %s THEN 2 ELSE 0 END"
        select_params.append(f"%{city}%")

    province_score = "0"
    if province:
        province_score = "CASE WHEN s.province = %s THEN 2 ELSE 0 END"
        select_params.append(province)
    query = f"""
    SELECT
        a.id AS admission_score_id,
        a.year,
        a.school_id,
        s.name AS school_name,
        s.province AS school_province,
        s.city AS school_city,
        s.is_985,
        s.is_211,
        s.is_double_first_class,
        s.education_level,
        s.ranking,
        a.major_id,
        a.major_name_raw AS major_name,
        a.subject_requirement,
        COALESCE(sr.requirement_type, 'unknown') AS requirement_type,
        a.min_score,
        a.min_rank,
        plan.min_tuition AS tuition,
        CASE
            WHEN s.is_985 THEN 4
            WHEN s.is_211 OR s.is_double_first_class THEN 3
            WHEN s.education_level = '本科' THEN 2
            ELSE 1
        END AS tier,
        ({major_score}) + ({city_score}) + ({province_score}) AS soft_match_score
    FROM admission_scores a
    JOIN schools s ON s.id = a.school_id
    LEFT JOIN subject_requirements sr ON sr.raw_requirement = a.subject_requirement
    LEFT JOIN LATERAL (
        SELECT min(p.tuition) AS min_tuition
        FROM admission_plans p
        WHERE p.school_id = a.school_id
          AND p.year = a.year
          AND (
              p.major_id = a.major_id
              OR p.major_code = a.major_code
              OR p.major_name_raw = a.major_name_raw
          )
    ) plan ON true
    WHERE {" AND ".join(where)}
    ORDER BY
        soft_match_score DESC,
        CASE
            WHEN a.min_score > %s THEN 0
            WHEN a.min_score >= %s THEN 1
            ELSE 2
        END ASC,
        tier DESC,
        s.ranking ASC NULLS LAST,
        abs(a.min_score - %s) ASC,
        a.year DESC,
        s.name ASC,
        a.major_name_raw ASC
    LIMIT %s
    """
    params = [*select_params, *where_params, score, score - 5, score, limit]
    return await _fetch_v1_rows(db, query, params)


def _segment_v1_candidates(
    constraints: dict[str, Any],
    rows: list[dict[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    score = int(constraints.get("score") or 0)
    segmented: dict[str, list[dict[str, Any]]] = {
        "chong": [],
        "wen": [],
        "bao": [],
    }
    for row in rows:
        min_score = row.get("min_score")
        if min_score is None:
            continue
        delta = int(float(min_score)) - score
        item = dict(row)
        item["score_delta"] = delta
        if 0 < delta <= 15:
            segmented["chong"].append(item)
        elif -5 <= delta <= 0:
            segmented["wen"].append(item)
        elif -25 <= delta < -5:
            segmented["bao"].append(item)
    return segmented


def _v1_soft_rag_reply(
    segmented: dict[str, list[dict[str, Any]]],
    rows: list[dict[str, Any]],
) -> str:
    if not rows:
        return "按 v1 软约束召回方式，当前没有找到合适的冲稳保候选。"

    labels = {
        "chong": "可冲击",
        "wen": "较稳妥",
        "bao": "可保底",
    }
    lines = ["按 v1 软约束召回方式，我先给出冲稳保候选："]
    for band in ("chong", "wen", "bao"):
        candidates = segmented.get(band) or []
        if not candidates:
            continue
        lines.append(f"{labels[band]}：")
        for row in candidates[:2]:
            lines.append(
                f"- {row.get('school_name')}｜{row.get('school_province')}｜"
                f"{row.get('major_name')}｜最低分 {row.get('min_score')}"
            )
    if len(lines) == 1:
        for row in rows[:3]:
            lines.append(
                f"- {row.get('school_name')}｜{row.get('school_province')}｜"
                f"{row.get('major_name')}｜最低分 {row.get('min_score')}"
            )
    return "\n".join(lines)


def _v1_state(
    *,
    constraints: dict[str, Any],
    normalized_query: dict[str, Any],
    soft_candidates: list[dict[str, Any]],
    missing_constraints: list[str],
    segmented_candidates: dict[str, list[dict[str, Any]]] | None = None,
) -> dict[str, Any]:
    return {
        "target": "v1_soft_rag",
        "constraints": dict(constraints),
        "normalized_query": dict(normalized_query),
        "soft_retrieval_candidates": list(soft_candidates),
        "risk_segments": segmented_candidates or {"chong": [], "wen": [], "bao": []},
        "baseline_results": list(soft_candidates[:3]),
        "pareto_opportunities": _empty_opportunities(),
        "score_waste": _score_waste(constraints, soft_candidates),
        "missing_constraints": list(missing_constraints),
        "recommended_schools": _recommended_schools(soft_candidates),
    }


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
