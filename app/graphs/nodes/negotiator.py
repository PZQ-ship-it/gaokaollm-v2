import ast
import json
import os
import re
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langgraph.types import interrupt

from app.core.llm_client import (
    ainvoke_text_with_timeout,
    get_reasoning_chat_model,
    get_structured_chat_model,
    reasoning_timeout_seconds,
    user_visible_timeout_seconds,
)
from app.schemas.state import DEFAULT_WEIGHT_VARIANCE, AgentState
from gaokaollm_bench.utils.trace import trace_event


COMPACT_FIELDS = (
    "school_name",
    "school_province",
    "school_city",
    "major_name",
    "min_score",
    "min_rank",
    "subject_requirement",
    "requirement_normalized",
    "requirement_type",
    "is_985",
    "is_211",
    "is_double_first_class",
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
    "major_similarity_score",
    "major_similarity_target",
    "major_similarity_method",
    "major_similarity_label",
)
NEGOTIATION_VARIANCE_THRESHOLD = 1.5
MAX_NEGOTIATION_TURNS = 3
OPPORTUNITY_KEYS = (
    "global_baseline",
    "major_geo_relax",
    "tuition_value_relax",
    "major_quality_relax",
    "employment_outcome_relax",
    "region_tree_relax",
    "risk_band_relax",
    "strength_relax",
    "geo_relax",
    "city_relax",
    "major_relax",
)

GLOBAL_BASELINE_PROBE = "probe_global_baseline"
PREFERENCE_KEYS = ("school", "major", "tuition", "quality", "geo", "risk")
RELAXABLE_COST_DIMENSIONS = ("geo", "major", "tuition", "risk")
BENEFIT_ONLY_DIMENSIONS = ("school", "quality")
PROBE_COST_DIMENSIONS = {
    "major_geo_relax": ("geo", "major"),
    "geo_relax": ("geo",),
    "city_relax": ("geo",),
    "region_tree_relax": ("geo",),
    "major_relax": ("major",),
    "tuition_value_relax": ("tuition",),
    "risk_band_relax": ("risk",),
    "major_quality_relax": ("major", "geo", "tuition"),
    "employment_outcome_relax": ("major", "geo"),
    "strength_relax": ("geo", "major", "tuition", "risk"),
}
PROBE_BENEFIT_DIMENSIONS = {
    "major_geo_relax": ("school", "quality", "risk"),
    "geo_relax": ("school", "quality", "major", "risk"),
    "city_relax": ("school", "quality", "major", "risk"),
    "region_tree_relax": ("school", "quality", "major", "risk"),
    "major_relax": ("school", "quality", "geo", "risk"),
    "tuition_value_relax": ("school", "quality", "major", "risk"),
    "risk_band_relax": ("school", "quality", "major"),
    "major_quality_relax": ("quality", "school", "risk"),
    "employment_outcome_relax": ("quality", "school", "major"),
    "strength_relax": ("school", "quality", "major", "risk"),
}
QUESTION_KIND_TRADEOFF = "tradeoff"
QUESTION_KIND_NO_SIGNIFICANT_TRADEOFF = "no_significant_tradeoff"
QUESTION_KIND_FINALIZE_OFFER = "finalize_offer"
GLOBAL_BASELINE_BUCKETS = ("reach", "match", "safety")
GLOBAL_BASELINE_BUCKET_LABELS = {
    "reach": "冲",
    "match": "稳",
    "safety": "保",
}
FINAL_RECOMMENDATION_TABLE_LIMIT = 80
FINAL_EXPLANATION_PER_BUCKET = 2
AGGRESSIVE_RISK_BUCKET_WEIGHTS = {
    "reach": 5,
    "match": 2,
    "safety": 2,
}
DIMENSION_LABELS = {
    "school": "学校层次",
    "major": "专业匹配",
    "tuition": "学费预算",
    "quality": "学科与培养质量",
    "geo": "地域范围",
    "risk": "录取风险弹性",
}
USER_DIMENSION_LABELS = {
    **DIMENSION_LABELS,
    "school": "学校平台与综合排名证据",
}


def _user_dimension_label(dimension: str) -> str:
    return USER_DIMENSION_LABELS.get(
        dimension, DIMENSION_LABELS.get(dimension, dimension)
    )


OPPORTUNITY_RELAXATION_LABELS = {
    "major_geo_relax": "专业或地域边界",
    "tuition_value_relax": "学费预算",
    "major_quality_relax": "地域或专业细分",
    "employment_outcome_relax": "专业/地域细节",
    "region_tree_relax": "地域圈层",
    "risk_band_relax": "风险偏好",
    "strength_relax": "非核心条件",
    "geo_relax": "地域范围",
    "city_relax": "城市范围",
    "major_relax": "专业邻近度",
}
OPPORTUNITY_RELAXATION_BENEFITS = {
    "major_geo_relax": "学校平台标签、综合排名或培养质量上的可比变化",
    "tuition_value_relax": "学校平台标签、综合排名或培养质量上的可比变化",
    "major_quality_relax": "更高学科质量、评级或专业排名",
    "employment_outcome_relax": "更强就业画像",
    "region_tree_relax": "学校平台标签、综合排名或地域替代上的可比变化",
    "risk_band_relax": "更完整的冲稳保组合",
    "strength_relax": "学校平台标签或综合排名上的可比变化",
    "geo_relax": "学校平台标签、综合排名或录取余量",
    "city_relax": "更多可比较候选",
    "major_relax": "学校平台标签、综合排名或风险收益",
}

# Backward-compatible test hook retained for older negotiator tests.
get_chat_model = get_structured_chat_model


async def _ainvoke_text_required(
    llm: Any,
    prompt: list[Any],
    *,
    timeout: float,
    label: str,
) -> str:
    content = (
        await ainvoke_text_with_timeout(
            llm,
            prompt,
            timeout=timeout,
            label=label,
        )
    ).strip()
    if content:
        return content
    raise RuntimeError(f"{label} returned empty content.")


async def _ainvoke_text_optional(
    llm: Any,
    prompt: list[Any],
    *,
    timeout: float,
    label: str,
) -> str:
    return await ainvoke_text_with_timeout(
        llm,
        prompt,
        timeout=timeout,
        label=label,
    )


MAJOR_NOTE_PATTERN = re.compile(
    r"[\(（][^()（）]*(?:学院|校区|班|方向)[^()（）]*[\)）]"
)
MAX_DISPLAY_VALUE_LEN = 48


def _display_major(value: Any) -> str:
    text = str(value or "")
    cleaned = MAJOR_NOTE_PATTERN.sub("", text).strip()
    return _short_display(cleaned or text, max_len=MAX_DISPLAY_VALUE_LEN)


def _short_display(value: Any, *, max_len: int = MAX_DISPLAY_VALUE_LEN) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    if len(text) <= max_len:
        return text
    return text[: max_len - 1] + "..."


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
    return _candidate_evidence_text(row, compact=True)


def _join(rows: list[dict[str, Any]], *, limit: int = 3) -> str:
    if not rows:
        return "暂无可核验候选"
    return "；".join(_candidate_evidence_text(row) for row in rows[:limit])


def _location_text(row: dict[str, Any]) -> str:
    province = _short_display(
        _first_present(row, ("school_province", "province")) or "",
        max_len=16,
    )
    city = _short_display(
        _first_present(row, ("school_city", "city")) or "", max_len=16
    )
    if province and city:
        return f"{province}/{city}"
    return province or city or "所在地待确认"


def _school_level_text(row: dict[str, Any]) -> str:
    tags: list[str] = []
    explicit = _first_present(
        row, ("school_tier", "school_level", "tier_label", "education_tier")
    )
    if explicit is not None:
        text = str(explicit).strip()
        if (
            text
            and text not in {"未给出", "None", "null"}
            and "tier" not in text.lower()
        ):
            tags.append(text)
    if bool(row.get("is_985")):
        tags.append("985")
    if bool(row.get("is_211")):
        tags.append("211")
    if bool(row.get("is_double_first_class")):
        tags.append("双一流")
    if not tags and row.get("tier") is not None:
        try:
            tier = int(float(row["tier"]))
        except (TypeError, ValueError):
            tier = 0
        if tier >= 4:
            tags.append("985 层次")
        elif tier >= 3:
            tags.append("211/双一流层次")
        elif tier >= 2:
            tags.append("重点本科层次")
        elif tier >= 1:
            tags.append("普通本科层次")
    return " / ".join(dict.fromkeys(tags)) if tags else "学校层级待确认"


def _safe_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _ranking_value(row: dict[str, Any]) -> float | None:
    return _safe_float(_first_present(row, ("ranking",)))


def _school_tier_value(row: dict[str, Any]) -> float | None:
    if bool(row.get("is_985")):
        return 4.0
    if bool(row.get("is_211")) or bool(row.get("is_double_first_class")):
        return 3.0
    return _safe_float(row.get("tier"))


def _school_evidence_comparison(
    option_a: dict[str, Any],
    option_b: dict[str, Any],
) -> dict[str, Any]:
    title_a = _option_title(option_a, "当前候选")
    title_b = _option_title(option_b, "放宽候选")
    level_a = _school_level_text(option_a)
    level_b = _school_level_text(option_b)
    tier_a = _school_tier_value(option_a)
    tier_b = _school_tier_value(option_b)
    ranking_a = _ranking_value(option_a)
    ranking_b = _ranking_value(option_b)

    platform_relation = "insufficient"
    if tier_a is not None and tier_b is not None:
        if tier_b > tier_a:
            platform_relation = "b_higher"
        elif tier_b < tier_a:
            platform_relation = "b_lower"
        else:
            platform_relation = "similar"
    elif level_a != "学校层级待确认" or level_b != "学校层级待确认":
        platform_relation = "evidence_only"

    ranking_relation = "insufficient"
    if ranking_a is not None and ranking_b is not None:
        if ranking_b < ranking_a:
            ranking_relation = "b_better"
        elif ranking_b > ranking_a:
            ranking_relation = "b_worse"
        else:
            ranking_relation = "similar"
    elif ranking_a is not None or ranking_b is not None:
        ranking_relation = "evidence_only"

    parts: list[str] = []
    if platform_relation == "b_higher":
        parts.append(
            f"{title_b} 的学校平台标签更突出（{level_b}；参照项为 {level_a}）。"
        )
    elif platform_relation == "b_lower":
        parts.append(
            f"{title_b} 的学校平台标签不占优（{level_b}；参照项为 {level_a}）。"
        )
    elif platform_relation == "similar":
        parts.append(f"两边学校平台标签接近（{level_a}）。")
    elif platform_relation == "evidence_only":
        parts.append(f"学校平台标签：{title_a} 为 {level_a}，{title_b} 为 {level_b}。")

    if ranking_relation == "b_better":
        parts.append(
            f"{title_b} 的综合排名参考更靠前（第 {_format_numeric(ranking_b)} 名；参照项约第 {_format_numeric(ranking_a)} 名）。"
        )
    elif ranking_relation == "b_worse":
        parts.append(
            f"{title_b} 的综合排名参考不比参照项靠前（第 {_format_numeric(ranking_b)} 名；参照项约第 {_format_numeric(ranking_a)} 名）。"
        )
    elif ranking_relation == "similar":
        parts.append(f"两边综合排名参考接近（约第 {_format_numeric(ranking_a)} 名）。")
    elif ranking_relation == "evidence_only":
        if ranking_a is not None:
            parts.append(f"{title_a} 综合排名参考第 {_format_numeric(ranking_a)} 名。")
        if ranking_b is not None:
            parts.append(f"{title_b} 综合排名参考第 {_format_numeric(ranking_b)} 名。")

    caution = ""
    if platform_relation == "b_higher" and ranking_relation == "b_worse":
        caution = (
            "这里不能说成“综合排名更好”；更准确的是平台标签更突出，但排名参考不占优。"
        )
    elif platform_relation == "b_higher" and ranking_relation in {
        "insufficient",
        "evidence_only",
    }:
        caution = "这里只能说平台标签更突出，不能推断综合排名也更好。"
    elif ranking_relation == "b_better" and platform_relation not in {
        "b_higher",
        "similar",
    }:
        caution = "这里主要是综合排名参考更靠前，不等同于学校平台标签更高。"

    brief = (
        "".join(parts)
        if parts
        else "学校平台标签与综合排名证据不足，不能作强收益表述。"
    )
    if caution:
        brief = f"{brief}{caution}"
    return {
        "platform_relation": platform_relation,
        "ranking_relation": ranking_relation,
        "platform_a": level_a,
        "platform_b": level_b,
        "ranking_a": ranking_a,
        "ranking_b": ranking_b,
        "brief": brief,
        "caution": caution,
    }


def _subject_requirement_text(row: dict[str, Any]) -> str:
    value = _first_present(row, ("subject_requirement", "requirement_normalized"))
    return str(value).strip() if value is not None else "选科要求待确认"


def _tuition_text(row: dict[str, Any]) -> str:
    tuition = _first_present(row, ("tuition", "tuition_fee"))
    if tuition is None:
        return "学费待确认"
    return f"约 {_format_numeric(tuition)} 元/年"


def _ranking_text(row: dict[str, Any]) -> str | None:
    ranking = _first_present(row, ("ranking",))
    if ranking is None:
        return None
    return f"综合排名参考第 {_format_numeric(ranking)} 名"


def _major_quality_text(row: dict[str, Any]) -> str | None:
    parts: list[str] = []
    rating = _first_present(row, ("major_strength_rating", "best_rating"))
    rank = _first_present(row, ("major_strength_rank", "best_major_rank"))
    level = _first_present(row, ("major_strength_level", "quality_tier"))
    if rating is not None:
        parts.append(f"评级 {rating}")
    if rank is not None:
        parts.append(f"学科/专业排名参考第 {_format_numeric(rank)} 名")
    if level is not None:
        parts.append(f"层级 {level}")
    if not parts and row.get("quality_score") is not None:
        parts.append("培养质量画像有可比证据")
    if row.get("has_key_major"):
        parts.append("含重点专业证据")
    if row.get("has_featured_major"):
        parts.append("含特色专业证据")
    return "，".join(parts) if parts else None


def _major_fit_text(row: dict[str, Any]) -> str | None:
    score = _safe_float(row.get("major_similarity_score"))
    if score is None:
        return None
    target = str(row.get("major_similarity_target") or "").strip()
    label = str(row.get("major_similarity_label") or "").strip()
    score_text = f"约 {round(max(0.0, min(1.0, score)) * 100)}%"
    parts = [f"专业贴合度{score_text}"]
    if label:
        parts.append(label)
    if target:
        parts.append(f"相对“{_short_display(target, max_len=18)}”")
    return "，".join(parts)


def _employment_text(row: dict[str, Any]) -> str | None:
    parts: list[str] = []
    if row.get("employment_rank_desc"):
        parts.append(str(row["employment_rank_desc"]))
    elif row.get("employment_rank") is not None:
        parts.append(f"就业排名参考第 {_format_numeric(row['employment_rank'])} 名")
    if row.get("top_industry"):
        parts.append(f"主要行业：{row['top_industry']}")
    if row.get("salary_distribution"):
        parts.append(f"薪资画像：{row['salary_distribution']}")
    if not parts and row.get("outcome_score") is not None:
        parts.append("就业画像有可比证据")
    return "，".join(parts) if parts else None


def _budget_delta_text(row: dict[str, Any]) -> str | None:
    delta = _first_present(row, ("tuition_delta", "budget_delta"))
    if delta is None:
        return None
    try:
        number = float(delta)
    except (TypeError, ValueError):
        return f"相对预算差额约 {delta} 元/年"
    if abs(number) < 1e-9:
        return "学费与预算基本持平"
    direction = "高于" if number > 0 else "低于"
    return f"学费约{direction}预算 {_format_numeric(abs(number))} 元/年"


def _candidate_evidence_text(row: dict[str, Any], *, compact: bool = False) -> str:
    school = _short_display(
        _first_present(row, ("school_name", "school")) or "未知学校",
        max_len=26,
    )
    major = _display_major(_first_present(row, ("major_name", "major")) or "专业待确认")
    parts: list[str] = [f"{school}，{major}"]
    parts.append(f"所在地 {_location_text(row)}")
    if row.get("min_score") is not None:
        parts.append(f"最低录取分 {_format_numeric(row['min_score'])}")
    if row.get("min_rank") is not None:
        parts.append(f"最低录取位次 {_format_numeric(row['min_rank'])}")
    if not compact:
        parts.append(_subject_requirement_text(row))
    if row.get("tuition") is not None or row.get("tuition_fee") is not None:
        parts.append(f"学费{_tuition_text(row)}")
    if not compact:
        parts.append(f"学校平台/标签 {_school_level_text(row)}")
    ranking = _ranking_text(row)
    if ranking:
        parts.append(ranking)
    if not compact:
        quality = _major_quality_text(row)
        if quality:
            parts.append(f"学科/专业证据：{quality}")
        major_fit = _major_fit_text(row)
        if major_fit:
            parts.append(major_fit)
        employment = _employment_text(row)
        if employment:
            parts.append(f"就业画像：{employment}")
    budget_delta = _budget_delta_text(row)
    if budget_delta:
        parts.append(budget_delta)
    risk = _first_present(row, ("risk_label", "risk_level", "risk_bucket"))
    if risk and str(risk) in {"reach", "match", "safety"}:
        risk = {"reach": "冲", "match": "稳", "safety": "保"}[str(risk)]
    if risk:
        parts.append(f"风险标签 {risk}")
    return "，".join(str(part) for part in parts if part)


RAW_OUTPUT_REPLACEMENTS = {
    "min_score": "最低录取分",
    "min_rank": "最低录取位次",
    "ranking": "综合排名参考",
    "tuition_delta": "相对预算差额",
    "quality_score": "培养质量画像参考",
    "quality_gain": "培养质量提升",
    "outcome_score": "就业画像参考",
    "outcome_gain": "就业画像提升",
    "score_margin": "分数余量",
    "rank_gap": "位次差距",
}


def _extract_user_text_from_llm_output(value: Any) -> str:
    if isinstance(value, dict):
        for key in ("text", "question", "content", "message"):
            text = value.get(key)
            if isinstance(text, str) and text.strip():
                return text
        return str(value)
    cleaned = str(value).strip()
    if cleaned.startswith("{") and cleaned.endswith("}"):
        for parser in (json.loads, ast.literal_eval):
            try:
                parsed = parser(cleaned)
            except Exception:
                continue
            if isinstance(parsed, dict):
                for key in ("text", "question", "content", "message"):
                    text = parsed.get(key)
                    if isinstance(text, str) and text.strip():
                        return text
                return str(parsed)
        match = re.search(
            r"""['"](?:text|question|content|message)['"]\s*:\s*(['"])(.*?)\1""",
            cleaned,
            flags=re.DOTALL,
        )
        if match:
            return match.group(2).strip()
    return cleaned


def _sanitize_user_output(text: str) -> str:
    cleaned = _extract_user_text_from_llm_output(text)
    cleaned = cleaned.replace("\\n", "\n")

    def replace_tier(match: re.Match[str]) -> str:
        tier_value = match.group(1)
        return f"学校平台/标签：{_school_level_text({'tier': tier_value})}"

    cleaned = re.sub(r"\btier\s*=\s*([0-9.]+)", replace_tier, cleaned)
    cleaned = re.sub(r"\btier\s+([0-9.]+)", replace_tier, cleaned)
    cleaned = re.sub(
        r"\b(?:_implicit_utility|_semantic_score|_lexicographic_tier|"
        r"_lexicographic_epsilon|semantic_score|utility|rank_ratio)\s*=\s*"
        r"[-+]?\d+(?:\.\d+)?",
        "",
        cleaned,
    )
    cleaned = re.sub(
        r"\bc/r\s*[:=]?\s*[-+]?\d+(?:\.\d+)?",
        "",
        cleaned,
        flags=re.IGNORECASE,
    )
    for raw, label in RAW_OUTPUT_REPLACEMENTS.items():
        cleaned = re.sub(rf"\b{re.escape(raw)}\s*=\s*", f"{label} ", cleaned)
    cleaned = cleaned.replace("major_geo_relax", "专业或地域边界放宽")
    cleaned = cleaned.replace("risk_band_relax", "冲稳保组合")
    cleaned = cleaned.replace("tuition_value_relax", "学费预算放宽")
    cleaned = cleaned.replace("major_quality_relax", "学科质量放宽")
    cleaned = cleaned.replace("employment_outcome_relax", "就业结果放宽")
    cleaned = cleaned.replace("region_tree_relax", "区域圈层放宽")
    cleaned = cleaned.replace("geo_relax", "地域范围放宽")
    cleaned = cleaned.replace("city_relax", "城市范围放宽")
    cleaned = cleaned.replace("major_relax", "专业邻近度放宽")
    cleaned = cleaned.replace("strength_relax", "学校实力优先放宽")
    cleaned = cleaned.replace("chong/wen/bao", "冲稳保")
    return cleaned


def _total_variance(state: AgentState) -> float:
    variance = dict(DEFAULT_WEIGHT_VARIANCE)
    raw_variance = state.get("weight_variance") or {}
    if isinstance(raw_variance, dict):
        variance.update(raw_variance)
    total = 0.0
    for value in variance.values():
        try:
            total += float(value)
        except (TypeError, ValueError):
            total += 1.0
    return total


def _iter_rows(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, list):
        return [dict(row) for row in value if isinstance(row, dict)]
    if isinstance(value, dict):
        rows: list[dict[str, Any]] = []
        for bucket, bucket_rows in value.items():
            if not isinstance(bucket_rows, list):
                continue
            for row in bucket_rows:
                if isinstance(row, dict):
                    item = dict(row)
                    item.setdefault("risk_bucket", str(bucket))
                    rows.append(item)
        return rows
    return []


def _all_opportunity_rows(opportunities: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for key in OPPORTUNITY_KEYS:
        for row in _iter_rows(opportunities.get(key)):
            if isinstance(row, dict):
                enriched = dict(row)
                enriched.setdefault("_opportunity_key", key)
                rows.append(enriched)
    return rows


def _row_has_value(row: dict[str, Any], key: str) -> bool:
    value = row.get(key)
    return value is not None and str(value).strip() != ""


def _merge_candidate_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    merged: dict[tuple[str, str], dict[str, Any]] = {}
    order: list[tuple[str, str]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        key = _candidate_identity(row)
        if not any(key):
            continue
        current = merged.get(key)
        if current is None:
            merged[key] = dict(row)
            order.append(key)
            continue
        for field, value in row.items():
            if value is None or str(value).strip() == "":
                continue
            if (
                field == "_opportunity_key"
                and current.get(field) == GLOBAL_BASELINE_PROBE
            ):
                current[field] = value
                continue
            if not _row_has_value(current, field):
                current[field] = value
                continue
            if field == "tuition" and not _row_has_value(current, "tuition"):
                current[field] = value
        current_utility = current.get("_implicit_utility")
        row_utility = row.get("_implicit_utility")
        try:
            if row_utility is not None and (
                current_utility is None or float(row_utility) > float(current_utility)
            ):
                current["_implicit_utility"] = row_utility
                if isinstance(row.get("_phi_features"), dict):
                    current["_phi_features"] = row["_phi_features"]
        except (TypeError, ValueError):
            pass
    return [merged[key] for key in order]


def _utility_sort_key(row: dict[str, Any]) -> tuple[float, int, str]:
    utility = row.get("_implicit_utility")
    try:
        utility_value = float(utility if utility is not None else -999999.0)
    except (TypeError, ValueError):
        utility_value = -999999.0
    try:
        tier = int(row.get("tier") or 0)
    except (TypeError, ValueError):
        tier = 0
    return (
        utility_value,
        tier,
        str(row.get("school_name") or row.get("school") or ""),
    )


def _current_probe_name(state: AgentState) -> str:
    probe_plan = state.get("probe_plan") or []
    if not probe_plan or not isinstance(probe_plan[0], dict):
        return ""
    first = probe_plan[0]
    probe_name = str(first.get("probe_name") or "").strip()
    if probe_name:
        return probe_name
    probe = str(first.get("probe") or "").strip()
    return f"probe_{probe}" if probe else ""


def _current_opportunity_key(state: AgentState) -> str:
    probe_name = _current_probe_name(state)
    if probe_name.startswith("probe_"):
        return probe_name.removeprefix("probe_")
    return probe_name


def _accepted_dimensions(state: AgentState | dict[str, Any] | None) -> set[str]:
    if not isinstance(state, dict):
        return set()
    accepted: set[str] = set()
    for item in state.get("accepted_relaxations") or []:
        if not isinstance(item, dict):
            continue
        dimension = str(item.get("dimension") or "").strip()
        if dimension == "risk_band_relax":
            dimension = "risk"
        if dimension:
            accepted.add(dimension)
    return accepted


def _opportunity_rows_for_key(
    opportunities: dict[str, Any],
    key: str,
) -> list[dict[str, Any]]:
    if not key:
        return []
    rows: list[dict[str, Any]] = []
    for row in _iter_rows(opportunities.get(key)):
        if isinstance(row, dict):
            enriched = dict(row)
            enriched.setdefault("_opportunity_key", key)
            rows.append(enriched)
    return sorted(_merge_candidate_rows(rows), key=_utility_sort_key, reverse=True)


def _candidate_rows(state: AgentState) -> list[dict[str, Any]]:
    explicit = state.get("candidates") or []
    global_rows = _iter_rows(
        (state.get("pareto_opportunities", {}) or {}).get("global_baseline")
    )
    baseline_rows = _iter_rows(state.get("baseline_results") or [])
    if explicit:
        rows = [*_iter_rows(explicit), *global_rows, *baseline_rows]
        deduped = _merge_candidate_rows(rows)
        return sorted(deduped, key=_utility_sort_key, reverse=True)
    rows = [
        *_all_opportunity_rows(state.get("pareto_opportunities", {}) or {}),
        *baseline_rows,
    ]
    deduped = _merge_candidate_rows(rows)
    return sorted(deduped, key=_utility_sort_key, reverse=True)


def _focused_candidate_rows(state: AgentState) -> list[dict[str, Any]]:
    opportunities = state.get("pareto_opportunities", {}) or {}
    if not isinstance(opportunities, dict):
        return []
    return _opportunity_rows_for_key(opportunities, _current_opportunity_key(state))


def _anchor_candidate_rows(state: AgentState) -> list[dict[str, Any]]:
    opportunities = state.get("pareto_opportunities", {}) or {}
    accepted_rows = [
        row
        for row in _iter_rows(state.get("candidates") or [])
        if row.get("_accepted_relaxation")
    ]
    global_rows: list[dict[str, Any]] = []
    global_result = (
        opportunities.get("global_baseline")
        if isinstance(opportunities, dict)
        else None
    )
    if isinstance(global_result, dict):
        for bucket in GLOBAL_BASELINE_BUCKETS:
            for row in _iter_rows(global_result.get(bucket) or []):
                enriched = dict(row)
                enriched.setdefault("risk_bucket", bucket)
                global_rows.append(enriched)

    current_rows = global_rows or _iter_rows(state.get("baseline_results") or [])
    rows = [*accepted_rows, *current_rows]
    deduped = _merge_candidate_rows([row for row in rows if isinstance(row, dict)])
    return deduped[:9]


def _new_challenger_rows(
    challenger_rows: list[dict[str, Any]],
    anchor_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    anchor_keys = {
        _candidate_identity(row)
        for row in anchor_rows
        if isinstance(row, dict) and any(_candidate_identity(row))
    }
    return [
        row
        for row in challenger_rows
        if isinstance(row, dict) and _candidate_identity(row) not in anchor_keys
    ]


def _unique_dimensions(dimensions: tuple[str, ...] | list[str]) -> tuple[str, ...]:
    ordered: list[str] = []
    for dimension in dimensions:
        key = str(dimension or "").strip()
        if key in PREFERENCE_KEYS and key not in ordered:
            ordered.append(key)
    return tuple(ordered)


def _cost_dimensions_for_probe(
    opportunity_key: str,
    target_dimension: str | None,
) -> tuple[str, ...]:
    if opportunity_key in PROBE_COST_DIMENSIONS:
        configured = PROBE_COST_DIMENSIONS[opportunity_key]
        if target_dimension in configured:
            return (str(target_dimension),)
        return configured
    if target_dimension in RELAXABLE_COST_DIMENSIONS:
        return (str(target_dimension),)
    return RELAXABLE_COST_DIMENSIONS


def _available_cost_dimensions_for_state(
    state: AgentState,
    opportunity_key: str,
    target_dimension: str | None,
) -> tuple[str, ...]:
    costs = _cost_dimensions_for_probe(opportunity_key, target_dimension)
    blocked = {
        str(item)
        for item in (state.get("factual_blocked_dimensions") or [])
        if str(item) in RELAXABLE_COST_DIMENSIONS
    }
    filtered = tuple(item for item in costs if item not in blocked)
    return filtered or costs


def _benefit_dimensions_for_probe(
    opportunity_key: str,
    target_dimension: str | None,
    cost_dimensions: tuple[str, ...],
) -> tuple[str, ...]:
    preferred: list[str] = []
    if target_dimension in BENEFIT_ONLY_DIMENSIONS:
        preferred.append(str(target_dimension))
    elif target_dimension in ("major", "risk"):
        preferred.append(str(target_dimension))
    preferred.extend(PROBE_BENEFIT_DIMENSIONS.get(opportunity_key, ()))
    preferred.extend(("school", "quality", "major", "risk", "geo"))
    return _unique_dimensions(
        [dimension for dimension in preferred if dimension not in cost_dimensions]
    )


def _phi_diff(a: dict[str, Any], b: dict[str, Any]) -> dict[str, float]:
    a_features = (
        a.get("_phi_features") if isinstance(a.get("_phi_features"), dict) else {}
    )
    b_features = (
        b.get("_phi_features") if isinstance(b.get("_phi_features"), dict) else {}
    )
    if not isinstance(a_features, dict):
        a_features = {}
    if not isinstance(b_features, dict):
        b_features = {}
    diff: dict[str, float] = {}
    for key in PREFERENCE_KEYS:
        try:
            diff[key] = float(a_features.get(key, 0.0)) - float(
                b_features.get(key, 0.0)
            )
        except (TypeError, ValueError):
            diff[key] = 0.0
    return diff


def _phi_delta_b_minus_a(a: dict[str, Any], b: dict[str, Any]) -> dict[str, float]:
    raw_a_features = a.get("_phi_features")
    raw_b_features = b.get("_phi_features")
    a_features = raw_a_features if isinstance(raw_a_features, dict) else {}
    b_features = raw_b_features if isinstance(raw_b_features, dict) else {}
    diff: dict[str, float] = {}
    for key in PREFERENCE_KEYS:
        try:
            diff[key] = float(b_features.get(key, 0.0)) - float(
                a_features.get(key, 0.0)
            )
        except (TypeError, ValueError):
            diff[key] = 0.0
    return diff


def _candidate_identity(row: dict[str, Any]) -> tuple[str, str]:
    school = str(row.get("school_name") or row.get("school") or "").strip()
    major = str(row.get("major_name") or row.get("major") or "").strip()
    return school, major


def _same_display_option(a: dict[str, Any], b: dict[str, Any]) -> bool:
    return bool(a and b and _candidate_identity(a) == _candidate_identity(b))


def _candidate_school(row: dict[str, Any]) -> str:
    return str(row.get("school_name") or row.get("school") or "").strip()


def _same_visible_candidate(a: dict[str, Any], b: dict[str, Any]) -> bool:
    school_a = _candidate_school(a)
    school_b = _candidate_school(b)
    if school_a and school_b and school_a == school_b:
        return True
    return _same_display_option(a, b)


def select_max_divergence_pair(
    candidates: list[dict[str, Any]],
    *,
    top_k: int = 10,
    previous_delta_phi: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, float]]:
    rows = sorted(
        [dict(row) for row in candidates if isinstance(row, dict)],
        key=_utility_sort_key,
        reverse=True,
    )
    if not rows:
        return {}, {}, {key: 0.0 for key in PREFERENCE_KEYS}
    option_a = rows[0]
    if len(rows) == 1:
        return option_a, {}, {key: 0.0 for key in PREFERENCE_KEYS}

    best_b: dict[str, Any] = {}
    best_delta = {key: 0.0 for key in PREFERENCE_KEYS}
    best_distance = 0.0
    previous: dict[str, float] = {}
    if isinstance(previous_delta_phi, dict):
        for key in PREFERENCE_KEYS:
            try:
                previous[key] = float(previous_delta_phi.get(key, 0.0))
            except (TypeError, ValueError):
                previous[key] = 0.0

    fallback_candidate: dict[str, Any] = {}
    fallback_delta = {key: 0.0 for key in PREFERENCE_KEYS}
    fallback_distance = 0.0
    for candidate in rows[1:top_k]:
        if _same_visible_candidate(option_a, candidate):
            continue
        delta = _phi_delta_b_minus_a(option_a, candidate)
        distance = sum(abs(value) for value in delta.values())
        if distance <= 0.05:
            continue
        if distance > fallback_distance:
            fallback_candidate = candidate
            fallback_delta = delta
            fallback_distance = distance
        if previous:
            repeat_distance = sum(
                abs(delta.get(key, 0.0) - previous.get(key, 0.0))
                for key in PREFERENCE_KEYS
            )
            if repeat_distance < 0.08:
                continue
        if distance > best_distance:
            best_b = candidate
            best_delta = delta
            best_distance = distance
    if best_distance <= 1e-9 and fallback_distance > best_distance:
        best_b = fallback_candidate
        best_delta = fallback_delta
    if not best_b:
        for candidate in rows[1:top_k]:
            if not _same_visible_candidate(option_a, candidate):
                return option_a, candidate, _phi_delta_b_minus_a(option_a, candidate)
    return option_a, best_b, best_delta


def select_forced_tradeoff_pair(
    candidates: list[dict[str, Any]],
    cost_dimension: str,
    *,
    top_k: int = 10,
    previous_delta_phi: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, float]]:
    option_a, option_b, delta_phi, _cost, _benefit = select_constrained_tradeoff_pair(
        candidates,
        cost_dimensions=(cost_dimension,),
        benefit_dimensions=tuple(
            key for key in PREFERENCE_KEYS if key != cost_dimension
        ),
        top_k=top_k,
        previous_delta_phi=previous_delta_phi,
    )
    return option_a, option_b, delta_phi


def select_constrained_tradeoff_pair(
    candidates: list[dict[str, Any]],
    *,
    cost_dimensions: tuple[str, ...],
    benefit_dimensions: tuple[str, ...],
    challenger_rows: list[dict[str, Any]] | None = None,
    anchor_rows: list[dict[str, Any]] | None = None,
    top_k: int = 10,
    previous_delta_phi: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, float], str | None, str | None]:
    rows = sorted(
        [dict(row) for row in candidates if isinstance(row, dict)],
        key=_utility_sort_key,
        reverse=True,
    )
    if not rows:
        return {}, {}, {key: 0.0 for key in PREFERENCE_KEYS}, None, None
    costs = _unique_dimensions(
        [
            dimension
            for dimension in cost_dimensions
            if dimension in RELAXABLE_COST_DIMENSIONS
        ]
    )
    if not costs:
        costs = RELAXABLE_COST_DIMENSIONS
    benefits = _unique_dimensions(
        [dimension for dimension in benefit_dimensions if dimension not in costs]
    )
    if not benefits:
        benefits = tuple(key for key in PREFERENCE_KEYS if key not in costs)

    anchors = sorted(
        [dict(row) for row in (anchor_rows or rows) if isinstance(row, dict)],
        key=_utility_sort_key,
        reverse=True,
    )[:top_k]
    challengers = sorted(
        [dict(row) for row in (challenger_rows or rows) if isinstance(row, dict)],
        key=_utility_sort_key,
        reverse=True,
    )[:top_k]
    if not anchors:
        anchors = rows[:top_k]
    if not challengers:
        challengers = rows[:top_k]

    default_a = anchors[0] if anchors else rows[0]
    previous: dict[str, float] = {}
    if isinstance(previous_delta_phi, dict):
        for key in PREFERENCE_KEYS:
            try:
                previous[key] = float(previous_delta_phi.get(key, 0.0))
            except (TypeError, ValueError):
                previous[key] = 0.0

    best_b: dict[str, Any] = {}
    best_delta = {key: 0.0 for key in PREFERENCE_KEYS}
    best_cost: str | None = None
    best_benefit: str | None = None
    best_score = -1.0
    option_a = default_a
    for baseline in anchors:
        for candidate in challengers:
            if baseline is candidate or _same_visible_candidate(baseline, candidate):
                continue
            delta = _phi_delta_b_minus_a(baseline, candidate)
            if previous:
                repeat_distance = sum(
                    abs(delta.get(key, 0.0) - previous.get(key, 0.0))
                    for key in PREFERENCE_KEYS
                )
                if repeat_distance < 0.08:
                    continue
            for cost_dimension in costs:
                if not (
                    _has_dimension_evidence(baseline, cost_dimension)
                    and _has_dimension_evidence(candidate, cost_dimension)
                ):
                    continue
                try:
                    cost_delta = float(delta.get(cost_dimension, 0.0))
                except (TypeError, ValueError):
                    cost_delta = 0.0
                if cost_delta >= -0.05:
                    continue
                gains: list[tuple[str, float]] = []
                for benefit_dimension in benefits:
                    if benefit_dimension == cost_dimension:
                        continue
                    if not (
                        _has_dimension_evidence(baseline, benefit_dimension)
                        and _has_dimension_evidence(candidate, benefit_dimension)
                    ):
                        continue
                    try:
                        gain = float(delta.get(benefit_dimension, 0.0))
                    except (TypeError, ValueError):
                        gain = 0.0
                    if gain > 0.05:
                        gains.append((benefit_dimension, gain))
                if not gains:
                    continue
                benefit_dimension, positive_gain = max(gains, key=lambda item: item[1])
                baseline_utility = 0.0
                candidate_utility = 0.0
                try:
                    baseline_utility = float(baseline.get("_implicit_utility") or 0.0)
                except (TypeError, ValueError):
                    baseline_utility = 0.0
                try:
                    candidate_utility = float(candidate.get("_implicit_utility") or 0.0)
                except (TypeError, ValueError):
                    candidate_utility = 0.0
                score = (
                    candidate_utility
                    + 0.25 * baseline_utility
                    + 2.0 * positive_gain
                    + abs(cost_delta)
                    + 0.05 * sum(abs(v) for v in delta.values())
                )
                if score > best_score:
                    option_a = baseline
                    best_b = candidate
                    best_delta = delta
                    best_cost = cost_dimension
                    best_benefit = benefit_dimension
                    best_score = score
    return option_a, best_b, best_delta, best_cost, best_benefit


def _pareto_prompt_payload(
    option_a: dict[str, Any],
    option_b: dict[str, Any],
    delta_phi: dict[str, float],
) -> dict[str, Any]:
    return {
        "option_a": _compact([option_a])[0] if option_a else {},
        "option_b": _compact([option_b])[0] if option_b else {},
        "delta_phi_b_minus_a": delta_phi,
    }


def _tradeoff_pair_payload(
    option_a: dict[str, Any],
    option_b: dict[str, Any],
    delta_phi: dict[str, float] | None,
    *,
    opportunity_key: str | None = None,
    cost_dimension: str | None = None,
    question_kind: str | None = None,
) -> dict[str, Any] | None:
    if not option_a and not option_b:
        return None
    diff = {key: float((delta_phi or {}).get(key, 0.0)) for key in PREFERENCE_KEYS}
    pair = {
        "option_a": dict(option_a) if option_a else {},
        "option_b": dict(option_b) if option_b else {},
        "delta_phi_b_minus_a": diff,
        "opportunity_key": opportunity_key or option_b.get("_opportunity_key") or "",
        "cost_dimension": cost_dimension,
        "question_kind": question_kind,
    }
    if pair["option_b"] and pair["opportunity_key"]:
        pair["option_b"].setdefault("_opportunity_key", pair["opportunity_key"])
    return pair


def _first_present(row: dict[str, Any], keys: tuple[str, ...]) -> Any:
    for key in keys:
        value = row.get(key)
        if value is not None and str(value).strip() != "":
            return value
    return None


def _format_numeric(value: Any) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return str(value)
    if number.is_integer():
        return str(int(number))
    return f"{number:.2f}"


def _phi_text(row: dict[str, Any], dimension: str) -> str:
    features = row.get("_phi_features")
    if isinstance(features, dict):
        value = features.get(dimension)
        if value is not None:
            label = _user_dimension_label(dimension)
            return f"{label}有可比较证据"
    return "该项证据待确认"


def _dimension_value_text(row: dict[str, Any], dimension: str) -> str:
    if dimension == "school":
        school = _short_display(
            _first_present(row, ("school_name", "school")) or "未知学校",
            max_len=24,
        )
        level = _school_level_text(row)
        return f"{school}，{level}" if level != "学校层级待确认" else str(school)
    if dimension == "major":
        major = _display_major(
            _first_present(row, ("major_name", "major")) or "未知专业"
        )
        return str(major)
    if dimension == "geo":
        province = _short_display(
            _first_present(row, ("school_province", "province")) or "未知省份",
            max_len=16,
        )
        raw_city = _first_present(row, ("school_city", "city"))
        city = _short_display(raw_city, max_len=16) if raw_city else None
        location = f"{province}/{city}" if city else str(province)
        return location
    if dimension == "tuition":
        tuition = _first_present(row, ("tuition", "tuition_fee"))
        delta = _first_present(row, ("tuition_delta", "budget_delta"))
        if tuition is not None and delta is not None:
            return f"{_tuition_text(row)}，{_budget_delta_text(row)}"
        if tuition is not None:
            return _tuition_text(row)
        return _phi_text(row, dimension)
    if dimension == "quality":
        quality = _first_present(
            row, ("quality_score", "major_strength_rating", "best_rating")
        )
        ranking = _first_present(
            row, ("ranking", "major_strength_rank", "best_major_rank")
        )
        parts = []
        if quality is not None:
            parts.append(f"质量或评级参考 {_format_numeric(quality)}")
        if ranking is not None:
            parts.append(f"排名参考第 {_format_numeric(ranking)} 名")
        return "，".join(parts) if parts else _phi_text(row, dimension)
    return _phi_text(row, dimension)


def _option_title(row: dict[str, Any], fallback: str) -> str:
    school = _short_display(
        _first_present(row, ("school_name", "school")) or fallback,
        max_len=24,
    )
    major = _display_major(_first_present(row, ("major_name", "major")) or "")
    if major:
        return f"{school} / {major}"
    return school


def _dimension_transition_text(
    option_a: dict[str, Any],
    option_b: dict[str, Any],
    dimension: str,
    *,
    verb: str,
) -> str:
    before = _dimension_value_text(option_a, dimension)
    after = _dimension_value_text(option_b, dimension)
    return f"从「{before}」{verb}到「{after}」"


def _delta_effect_text(delta_phi: dict[str, float], dimension: str) -> str:
    try:
        delta = float(delta_phi.get(dimension, 0.0))
    except (TypeError, ValueError):
        delta = 0.0
    if abs(delta) < 0.005:
        return "两边差异不明显"
    return "这一维度吸引力更强" if delta > 0 else "这一维度需要让步"


def _choose_benefit_dimension(
    diff: dict[str, Any],
    cost: str,
    *,
    fallback: str = "quality",
) -> str:
    positive = [
        (key, float(value))
        for key, value in diff.items()
        if key != cost and isinstance(value, (int, float)) and float(value) > 0.05
    ]
    if positive:
        return max(positive, key=lambda item: item[1])[0]
    if fallback != cost:
        return fallback
    return "school" if cost != "school" else "quality"


def _choose_cost_dimension(
    diff: dict[str, Any],
    forced_cost_dimension: str | None,
) -> str:
    if forced_cost_dimension in RELAXABLE_COST_DIMENSIONS:
        return str(forced_cost_dimension)
    negative = [
        (key, float(value))
        for key, value in diff.items()
        if key in RELAXABLE_COST_DIMENSIONS
        and isinstance(value, (int, float))
        and float(value) < -0.05
    ]
    if negative:
        return min(negative, key=lambda item: item[1])[0]
    return "geo"


def _fallback_cost_dimension_for_probe(
    opportunity_key: str,
    target_dimension: str | None,
) -> str:
    costs = _cost_dimensions_for_probe(opportunity_key, target_dimension)
    if costs:
        return costs[0]
    if target_dimension in RELAXABLE_COST_DIMENSIONS:
        return str(target_dimension)
    return "geo"


def _has_real_benefit(diff: dict[str, Any], cost: str) -> bool:
    return any(
        key != cost and isinstance(value, (int, float)) and float(value) > 0.05
        for key, value in diff.items()
    )


def _has_dimension_evidence(row: dict[str, Any], dimension: str) -> bool:
    if not isinstance(row, dict):
        return False
    if dimension == "tuition":
        return _first_present(row, ("tuition", "tuition_fee")) is not None
    if dimension == "school":
        return bool(
            _first_present(
                row,
                (
                    "school_name",
                    "school",
                    "school_tier",
                    "school_level",
                    "tier_label",
                    "education_tier",
                    "tier",
                    "ranking",
                ),
            )
            is not None
        )
    if dimension == "major":
        return bool(_first_present(row, ("major_name", "major")) is not None)
    if dimension == "geo":
        return bool(
            _first_present(row, ("school_province", "province", "school_city", "city"))
            is not None
        )
    if dimension == "quality":
        return bool(
            _first_present(
                row,
                (
                    "quality_score",
                    "major_strength_rating",
                    "best_rating",
                    "major_strength_rank",
                    "best_major_rank",
                ),
            )
            is not None
        )
    if dimension == "risk":
        return bool(
            _first_present(
                row,
                ("risk_label", "risk_level", "risk_bucket", "min_rank", "rank_gap"),
            )
            is not None
        )
    return True


def _has_real_tradeoff(
    option_a: dict[str, Any],
    option_b: dict[str, Any],
    diff: dict[str, Any],
    cost: str,
) -> bool:
    if not option_a or not option_b or _same_display_option(option_a, option_b):
        return False
    if not (
        _has_dimension_evidence(option_a, cost)
        and _has_dimension_evidence(option_b, cost)
    ):
        return False
    try:
        cost_delta = float(diff.get(cost, 0.0))
    except (TypeError, ValueError):
        cost_delta = 0.0
    if cost_delta > -0.05:
        return False
    return any(
        key != cost
        and isinstance(value, (int, float))
        and float(value) > 0.05
        and _has_dimension_evidence(option_a, key)
        and _has_dimension_evidence(option_b, key)
        for key, value in diff.items()
    )


def _classify_question_kind(
    option_a: dict[str, Any],
    option_b: dict[str, Any],
    delta_phi: dict[str, float],
    forced_cost_dimension: str | None,
) -> str:
    cost = _choose_cost_dimension(delta_phi or {}, forced_cost_dimension)
    if _has_real_tradeoff(option_a, option_b, delta_phi or {}, cost):
        return QUESTION_KIND_TRADEOFF
    return QUESTION_KIND_NO_SIGNIFICANT_TRADEOFF


def _no_significant_tradeoff_question(
    option_a: dict[str, Any],
    option_b: dict[str, Any],
    delta_phi: dict[str, float],
    *,
    forced_cost_dimension: str | None = None,
    feedback_analysis: dict[str, Any] | None = None,
) -> str:
    diff = delta_phi or {}
    cost = _choose_cost_dimension(diff, forced_cost_dimension)
    cost_label = _user_dimension_label(cost)
    alternatives = _alternative_tradeoff_text(cost)
    evidence = ""
    if option_a:
        current = _dimension_value_text(option_a, cost)
        title = _option_title(option_a, "当前候选")
        evidence = f"以 {title} 为参照，当前只看到{cost_label}边界在「{current}」。"
    if option_b and not _same_visible_candidate(option_a, option_b):
        title_b = _option_title(option_b, "另一候选")
        transition = _dimension_transition_text(option_a, option_b, cost, verb="变化")
        evidence = f"对照 {title_b} 后，主要变化仍集中在{cost_label}：{transition}。"
    feedback = feedback_analysis if isinstance(feedback_analysis, dict) else {}
    prior_intent = str(feedback.get("intent") or "").strip().lower()
    prior_sentence = ""
    if prior_intent == "accept":
        prior_dimension = str(feedback.get("target_dimension") or "").strip()
        prior_label = _user_dimension_label(prior_dimension)
        if prior_label:
            prior_sentence = f"你刚才接受的“{prior_label}”放宽会继续保留在当前比较里。"
    elif prior_intent == "reject":
        prior_dimension = str(feedback.get("target_dimension") or cost).strip()
        prior_label = _user_dimension_label(prior_dimension)
        prior_sentence = f"你刚才保留的“{prior_label}”底线我会继续尊重。"
    return (
        f"{prior_sentence}"
        f"这一轮没有看到值得为了{cost_label}让步的明显收益。"
        f"{evidence}"
        "我建议先不把这条作为偏好调整依据。"
        f"要直接看最终推荐，还是换到{alternatives}方向再查一轮？"
    )


def _locked_preference_text(dimension: str) -> str:
    return {
        "major": "专业不偏离",
        "geo": "地域不越界",
        "tuition": "预算不突破",
        "school": "学校平台与排名证据不下降",
        "quality": "培养质量不下降",
    }.get(dimension, "这项偏好不放宽")


def _alternative_tradeoff_text(dimension: str) -> str:
    return {
        "major": "地域/学校平台与排名证据",
        "geo": "专业/学校平台与排名证据",
        "tuition": "学校平台与排名证据/培养质量",
        "school": "专业/培养质量",
        "quality": "学校平台与排名证据/专业",
    }.get(dimension, "其他维度")


def _tradeoff_fact_sentence(
    option_a: dict[str, Any],
    option_b: dict[str, Any],
    cost: str,
    benefit: str,
    delta_phi: dict[str, float],
) -> str:
    title_a = _option_title(option_a, "方案A")
    title_b = _option_title(option_b, "方案B")
    cost_label = _user_dimension_label(cost)
    benefit_label = _user_dimension_label(benefit)
    cost_transition = _dimension_transition_text(
        option_a,
        option_b,
        cost,
        verb="放宽",
    )
    benefit_transition = _dimension_transition_text(
        option_a,
        option_b,
        benefit,
        verb="提升",
    )
    kept_cost = _dimension_value_text(option_a, cost)
    benefit_effect = _delta_effect_text(delta_phi, benefit)
    school_note = ""
    if benefit == "school" or cost == "school":
        school_note = _school_evidence_comparison(option_a, option_b)["brief"]
    return (
        f"如果保留 {title_a}，你保留 {cost_label}：{kept_cost}；"
        f"如果改看 {title_b}，需要你牺牲/放宽 {cost_label}：{cost_transition}，"
        f"可比较的 {benefit_label} 变化是：{benefit_transition}（{benefit_effect}）。"
        f"{school_note}"
    )


def _single_option_probe_question(
    option: dict[str, Any],
    cost: str,
) -> str:
    opportunity_key = str(option.get("_opportunity_key") or "")
    cost_label = OPPORTUNITY_RELAXATION_LABELS.get(
        opportunity_key
    ) or _user_dimension_label(cost)
    benefit_label = OPPORTUNITY_RELAXATION_BENEFITS.get(opportunity_key)
    evidence = _candidate_evidence_text(option)
    benefit_text = (
        f"可能换来{benefit_label}。"
        if benefit_label
        else "可以作为一条有分数、位次和费用依据的对照方案。"
    )
    return (
        f"在你当前条件内，系统已经列出冲稳保候选。为了判断边界值不值得调整，我再拿一条对照方案给你看：{evidence}。"
        f"这条方案需要小幅放宽{cost_label}，但{benefit_text}"
        f"如果这个收益对你有吸引力，你愿意继续比较这类放宽方案吗？"
    )


def _fallback_pareto_question(
    option_a: dict[str, Any],
    option_b: dict[str, Any],
    delta_phi: dict[str, float],
    *,
    forced_cost_dimension: str | None = None,
) -> str:
    payload = _pareto_prompt_payload(option_a, option_b, delta_phi)
    diff = payload.get("delta_phi_b_minus_a") or {}
    cost = _choose_cost_dimension(diff, forced_cost_dimension)
    benefit = _choose_benefit_dimension(diff, cost)
    has_real_tradeoff = _has_real_tradeoff(option_a, option_b, diff, cost)
    benefit_label = _user_dimension_label(benefit)
    cost_label = _user_dimension_label(cost)
    if not option_b:
        return _no_significant_tradeoff_question(
            option_a,
            option_b,
            delta_phi,
            forced_cost_dimension=forced_cost_dimension,
        )
    if option_b and _same_visible_candidate(option_a, option_b):
        return _no_significant_tradeoff_question(
            option_a,
            option_b,
            delta_phi,
            forced_cost_dimension=forced_cost_dimension,
        )
    if not has_real_tradeoff:
        return _no_significant_tradeoff_question(
            option_a,
            option_b,
            delta_phi,
            forced_cost_dimension=forced_cost_dimension,
        )
    fact_sentence = _tradeoff_fact_sentence(
        option_a, option_b, cost, benefit, delta_phi
    )
    return (
        f"{fact_sentence}"
        f"这笔取舍里，你更不能接受的是放宽 {cost_label}，"
        f"还是愿意为了 {benefit_label} 接受它？"
    )


def _followup_pareto_question(
    delta_phi: dict[str, float],
    forced_cost_dimension: str,
    negotiation_turns: int,
    *,
    option_a: dict[str, Any] | None = None,
    option_b: dict[str, Any] | None = None,
    feedback_analysis: dict[str, Any] | None = None,
) -> str:
    positive = [
        (key, value)
        for key, value in delta_phi.items()
        if isinstance(value, (int, float)) and value > 0.05
    ]
    benefit = max(positive, key=lambda item: item[1])[0] if positive else "school"
    if benefit == forced_cost_dimension:
        benefit = next(
            (key for key, _value in positive if key != forced_cost_dimension),
            "quality" if forced_cost_dimension != "quality" else "school",
        )
    cost_label = _user_dimension_label(forced_cost_dimension)
    benefit_label = _user_dimension_label(benefit)
    locked_text = _locked_preference_text(forced_cost_dimension)
    round_number = negotiation_turns + 1
    reply_hint = {
        "major": "专业不能偏太远",
        "geo": "不能出省或离目标地域太远",
        "tuition": "预算不能超",
        "school": "学校平台与排名证据不能降",
        "quality": "培养质量不能弱",
    }.get(forced_cost_dimension, "这条底线不能轻易动")
    feedback = feedback_analysis if isinstance(feedback_analysis, dict) else {}
    prior_intent = str(feedback.get("intent") or "").strip().lower()
    prior_dimension = str(feedback.get("target_dimension") or "").strip()
    prior_label = (
        _user_dimension_label(prior_dimension) if prior_dimension else cost_label
    )
    if prior_intent == "accept":
        prior_sentence = (
            f"你刚才接受了围绕“{prior_label}”的小幅放宽。"
            f"第 {round_number} 轮我会先把这类方案纳入当前比较范围，"
        )
    elif prior_intent == "hesitate":
        prior_sentence = (
            f"你刚才对“{prior_label}”还没有完全定下来。"
            f"第 {round_number} 轮我先继续用事实对照帮你判断，"
        )
    else:
        prior_sentence = f"你刚才拒绝了“{reply_hint}”。第 {round_number} 轮我按“{locked_text}”先锁定，"
    if (
        option_a
        and option_b
        and _has_real_tradeoff(
            option_a,
            option_b,
            delta_phi,
            forced_cost_dimension,
        )
    ):
        fact_sentence = _tradeoff_fact_sentence(
            option_a,
            option_b,
            forced_cost_dimension,
            benefit,
            delta_phi,
        )
        return (
            f"{prior_sentence}再看这组事实取舍："
            f"{fact_sentence}"
            f"如果仍要牺牲/放宽 {cost_label} 换取 {benefit_label}，"
            f"你更不能接受哪一项？"
        )
    return prior_sentence + _no_significant_tradeoff_question(
        option_a or {},
        option_b or {},
        delta_phi,
        forced_cost_dimension=forced_cost_dimension,
    )


def _feedback_analysis_payload(state: AgentState) -> dict[str, Any]:
    analysis = state.get("feedback_analysis")
    if isinstance(analysis, dict):
        return {
            "intent": str(analysis.get("intent") or "unknown"),
            "target_dimension": str(analysis.get("target_dimension") or "unknown"),
        }
    return {"intent": "unknown", "target_dimension": "unknown"}


def _pareto_generation_instruction(state: AgentState) -> str:
    negotiation_turns = int(state.get("negotiation_turns") or 0)
    question_kind = str(state.get("latest_question_kind") or "").strip()
    if question_kind == QUESTION_KIND_NO_SIGNIFICANT_TRADEOFF:
        return (
            "你是面向浙江高考考生的志愿咨询顾问。"
            "当前底层事实探针没有找到显著的代价-收益跃迁。"
            "请把它表达成事实边界诊断，而不是偏好取舍题。"
            "说明本轮没有足够证据支持继续放宽，不诱导用户接受放宽。"
            "可以建议用户直接看最终推荐，或换一个方向继续查。"
            "不要输出 tier、c/r、utility、phi、MRS、rank_ratio、semantic_score、"
            "_semantic_score、_lexicographic_tier、_implicit_utility 等内部字段名。"
            "回复控制在 160 字以内。"
        )
    if negotiation_turns <= 0:
        return (
            "你是面向浙江高考考生的志愿咨询顾问。"
            "请基于候选事实，向用户发起一轮自然、克制、可解释的边界确认。"
            "首轮也要写成真实咨询对话，不要拼接模板；"
            "不要照抄 payload.user_visible_fact_sentence，不要使用“如果保留……如果改看……”句式。"
            "你要像真实系统现场沟通，不要说内部术语，不要输出 tier、c/r、utility、phi、MRS、"
            "rank_ratio、semantic_score、_semantic_score、_lexicographic_tier、_implicit_utility 等字段名。"
            "学校相关证据必须拆开说：学校平台标签和综合排名是两条不同证据。"
            "只有同时有证据支持时，才可以说学校整体更占优；"
            "如果只是 985、211、双一流等平台标签更突出，但综合排名不靠前或未知，"
            "就说“平台标签更突出/更明确”，不要说“排名更好”“学校更好”“学校层次比某校更高”。"
            "如果专业方向明显变化，要把专业贴合度一起说清楚，不要只谈学校。"
            "如果有可验证收益，可以说明放宽的具体维度和换来的优势；"
            "如果没有可验证收益，不要编造收益。"
            "语气要像真实咨询：先把两个候选的核心差异讲明白，再问用户更看重哪一边。"
            "避免“极度、精准、更好学校、换取更强、牌子更好”等推销式措辞；"
            "优先说“平台标签更明确、专业贴合度变化、地域变化、学费变化、录取余量变化”。"
            "回复控制在 180 字以内，最后给出一个明确问题。"
        )
    return (
        "你是面向浙江高考考生的志愿咨询顾问。"
        "现在是用户反馈后的下一轮追问，必须严格依据 payload.previous_feedback 复述上一轮用户态度："
        "intent=accept 时说用户已接受该放宽，并说明会把这类方案纳入当前比较；"
        "intent=reject 时说会保留对应底线；"
        "intent=hesitate 或 unknown 时说先继续用事实对照帮助判断。"
        "不要把接受说成拒绝，也不要把拒绝说成接受。"
        "请基于候选事实生成自然语言追问，不要使用写死模板口吻；"
        "不要输出 tier、c/r、utility、phi、MRS、rank_ratio、semantic_score、"
        "_semantic_score、_lexicographic_tier、_implicit_utility 等内部字段名。"
        "学校相关证据必须拆开说：学校平台标签和综合排名是两条不同证据。"
        "如果只是平台标签更突出，不能说成综合排名更好；如果排名不占优，要明说排名参考不占优或另作参考。"
        "如果专业或地域也变了，要把这些代价放进问题里，而不是只问用户是否接受“更好学校”。"
        "如果候选事实不足以支撑取舍，就直接说明证据不足，不要把它包装成放宽建议。"
        "避免“极度、精准、更好学校、换取更强、牌子更好”等推销式措辞；优先使用候选事实本身。"
        "回复控制在 200 字以内，最后给出一个明确问题。"
    )


def _pareto_generation_payload(
    state: AgentState,
    option_a: dict[str, Any],
    option_b: dict[str, Any],
    delta_phi: dict[str, float],
    *,
    forced_cost_dimension: str | None,
) -> dict[str, Any]:
    payload = _pareto_prompt_payload(option_a, option_b, delta_phi)
    cost = _choose_cost_dimension(
        payload.get("delta_phi_b_minus_a") or {},
        forced_cost_dimension,
    )
    benefit = _choose_benefit_dimension(
        payload.get("delta_phi_b_minus_a") or {},
        cost,
    )
    has_real_tradeoff = _has_real_tradeoff(
        option_a,
        option_b,
        payload.get("delta_phi_b_minus_a") or {},
        cost,
    )
    school_evidence = (
        _school_evidence_comparison(option_a, option_b) if option_b else {}
    )
    return {
        "round": int(state.get("negotiation_turns") or 0) + 1,
        "previous_feedback": _feedback_analysis_payload(state),
        "focus_dimension": forced_cost_dimension or cost,
        "focus_dimension_label": USER_DIMENSION_LABELS.get(
            forced_cost_dimension or cost,
            forced_cost_dimension or cost,
        ),
        "candidate_a_user_facing": _candidate_evidence_text(option_a)
        if option_a
        else "",
        "candidate_b_user_facing": _candidate_evidence_text(option_b)
        if option_b
        else "",
        "option_a": payload.get("option_a") or {},
        "option_b": payload.get("option_b") or {},
        "suggested_cost_dimension": cost,
        "suggested_benefit_dimension": benefit,
        "suggested_cost_label": _user_dimension_label(cost),
        "suggested_benefit_label": _user_dimension_label(benefit),
        "school_evidence_comparison": school_evidence,
        "speaking_rules": [
            "学校平台标签与综合排名必须分开表达，不得互相替代。",
            "平台标签更突出但综合排名不占优时，只能说平台标签更突出，不能说排名更好或学校整体更好。",
            "专业贴合度来自候选与用户专业需求的语义相近程度，只能作为辅助排序和解释证据，不要说成硬性录取条件。",
            "专业贴合度下降时，必须把它作为代价说出来；不能只强调学校平台标签或学费变化。",
            "若放宽候选的专业方向、地域或学费也有变化，必须同时呈现这些代价。",
            "问题应让用户在具体事实之间取舍，而不是劝用户接受一个抽象的更好学校。",
        ],
        "has_real_benefit": has_real_tradeoff,
        "user_visible_fact_sentence": _tradeoff_fact_sentence(
            option_a,
            option_b,
            cost,
            benefit,
            delta_phi,
        )
        if has_real_tradeoff
        else "",
        "delta_phi_b_minus_a": payload.get("delta_phi_b_minus_a") or {},
    }


def _xai_fallback_text(
    weights: dict[str, Any],
    candidates: list[dict[str, Any]],
    recommendation_matrix: dict[str, list[dict[str, Any]]] | None = None,
) -> str:
    sorted_weights = sorted(
        ((key, float(weights.get(key, 0.0))) for key in PREFERENCE_KEYS),
        key=lambda item: item[1],
        reverse=True,
    )
    weight_text = "、".join(
        f"{_user_dimension_label(key)}相对更重要"
        for key, value in sorted_weights
        if value > 0
    )
    lines = [
        f"偏好解释：系统会按你当前表达出的取舍偏好重新排序；这一轮主要体现为{weight_text or '各维度均衡'}，同时保留已经识别的硬性底线。",
        "最终推荐名单：",
    ]
    matrix = recommendation_matrix or {}
    if any(matrix.get(bucket) for bucket in GLOBAL_BASELINE_BUCKETS):
        labels = {"reach": "冲", "match": "稳", "safety": "保"}
        for bucket in GLOBAL_BASELINE_BUCKETS:
            bucket_rows = matrix.get(bucket) or []
            if not bucket_rows:
                continue
            lines.append(f"{labels[bucket]}:")
            for index, row in enumerate(bucket_rows[:3], start=1):
                lines.append(f"{index}. {_candidate_evidence_text(row)}")
    else:
        for index, row in enumerate(candidates[:5], start=1):
            lines.append(f"{index}. {_candidate_evidence_text(row)}")
    return "\n".join(lines)


def _global_recommendation_matrix(state: AgentState) -> dict[str, list[dict[str, Any]]]:
    opportunities = state.get("pareto_opportunities", {}) or {}
    global_result = (
        opportunities.get("global_baseline")
        if isinstance(opportunities, dict)
        else None
    )
    if isinstance(global_result, dict):
        return {
            key: sorted(
                _iter_rows(global_result.get(key)),
                key=_utility_sort_key,
                reverse=True,
            )
            for key in GLOBAL_BASELINE_BUCKETS
        }
    rows = _candidate_rows(state)
    matrix: dict[str, list[dict[str, Any]]] = {
        key: [] for key in GLOBAL_BASELINE_BUCKETS
    }
    for row in rows:
        bucket = str(row.get("risk_bucket") or row.get("risk_level") or "")
        if bucket in matrix:
            matrix[bucket].append(row)
    for bucket in GLOBAL_BASELINE_BUCKETS:
        matrix[bucket] = sorted(matrix[bucket], key=_utility_sort_key, reverse=True)
    return matrix


def _limit_final_recommendation_matrix(
    matrix: dict[str, list[dict[str, Any]]],
    *,
    total_limit: int = FINAL_RECOMMENDATION_TABLE_LIMIT,
    aggressive_risk: bool = False,
) -> dict[str, list[dict[str, Any]]]:
    total_limit = max(0, int(total_limit))
    if total_limit <= 0:
        return {bucket: [] for bucket in GLOBAL_BASELINE_BUCKETS}
    total_count = sum(
        len(matrix.get(bucket) or []) for bucket in GLOBAL_BASELINE_BUCKETS
    )
    if total_count <= total_limit:
        return {
            bucket: list(matrix.get(bucket) or []) for bucket in GLOBAL_BASELINE_BUCKETS
        }
    weights = (
        AGGRESSIVE_RISK_BUCKET_WEIGHTS
        if aggressive_risk
        else {bucket: 1 for bucket in GLOBAL_BASELINE_BUCKETS}
    )
    total_weight = sum(
        max(0, int(weights.get(bucket, 0))) for bucket in GLOBAL_BASELINE_BUCKETS
    )
    if total_weight <= 0:
        weights = {bucket: 1 for bucket in GLOBAL_BASELINE_BUCKETS}
        total_weight = len(GLOBAL_BASELINE_BUCKETS)
    raw_quotas = {
        bucket: total_limit * max(0, int(weights.get(bucket, 0))) / total_weight
        for bucket in GLOBAL_BASELINE_BUCKETS
    }
    quotas = {bucket: int(raw_quotas[bucket]) for bucket in GLOBAL_BASELINE_BUCKETS}
    remainder = total_limit - sum(quotas.values())
    quota_order = sorted(
        GLOBAL_BASELINE_BUCKETS,
        key=lambda bucket: (
            int(weights.get(bucket, 0)),
            raw_quotas[bucket] - quotas[bucket],
            -GLOBAL_BASELINE_BUCKETS.index(bucket),
        ),
        reverse=True,
    )
    for bucket in quota_order[:remainder]:
        quotas[bucket] += 1

    limited: dict[str, list[dict[str, Any]]] = {
        bucket: [] for bucket in GLOBAL_BASELINE_BUCKETS
    }
    for bucket in GLOBAL_BASELINE_BUCKETS:
        quota = quotas.get(bucket, 0)
        limited[bucket] = list((matrix.get(bucket) or [])[:quota])
    remaining = total_limit - sum(len(rows) for rows in limited.values())
    fill_order = tuple(quota_order) if aggressive_risk else GLOBAL_BASELINE_BUCKETS
    while remaining > 0:
        progressed = False
        for bucket in fill_order:
            rows = matrix.get(bucket) or []
            if len(limited[bucket]) >= len(rows):
                continue
            limited[bucket].append(rows[len(limited[bucket])])
            remaining -= 1
            progressed = True
            if remaining <= 0:
                break
        if not progressed:
            break
    return limited


def _admission_text(row: dict[str, Any]) -> str:
    parts: list[str] = []
    if row.get("min_score") is not None:
        parts.append(f"{_format_numeric(row['min_score'])} 分")
    if row.get("min_rank") is not None:
        parts.append(f"位次 {_format_numeric(row['min_rank'])}")
    return " / ".join(parts) if parts else "待确认"


def _final_evidence_text(row: dict[str, Any]) -> str:
    parts = [
        item
        for item in (
            _ranking_text(row),
            _major_quality_text(row),
            _major_fit_text(row),
            _employment_text(row),
        )
        if item
    ]
    return "；".join(parts[:2]) if parts else "暂无额外证据"


def _final_reason_text(row: dict[str, Any]) -> str:
    parts: list[str] = []
    major_fit = _major_fit_text(row)
    if major_fit:
        parts.append(major_fit)
    level = _school_level_text(row)
    if level != "学校层级待确认":
        parts.append(level)
    ranking = _ranking_text(row)
    if ranking:
        parts.append(ranking)
    quality = _major_quality_text(row)
    if quality:
        parts.append(quality)
    budget_delta = _budget_delta_text(row)
    if budget_delta:
        parts.append(budget_delta)
    return "；".join(dict.fromkeys(parts[:3])) or "按当前偏好权重排序靠前"


def _final_table_row(row: dict[str, Any], bucket: str, index: int) -> dict[str, Any]:
    return {
        "bucket": bucket,
        "bucket_label": GLOBAL_BASELINE_BUCKET_LABELS.get(bucket, bucket),
        "order": index,
        "school": _short_display(
            _first_present(row, ("school_name", "school")) or "学校待确认",
            max_len=36,
        ),
        "major": _display_major(
            _first_present(row, ("major_name", "major")) or "专业待确认"
        ),
        "location": _location_text(row),
        "admission": _admission_text(row),
        "subjects": _subject_requirement_text(row),
        "tuition": _tuition_text(row),
        "school_level": _school_level_text(row),
        "evidence": _final_evidence_text(row),
        "reason": _final_reason_text(row),
    }


def _final_recommendation_table_matrix(
    state: AgentState,
) -> dict[str, list[dict[str, Any]]]:
    matrix = _limit_final_recommendation_matrix(
        _global_recommendation_matrix(state),
        aggressive_risk="risk" in _accepted_dimensions(state),
    )
    return {
        bucket: [
            _final_table_row(row, bucket, index)
            for index, row in enumerate(matrix.get(bucket) or [], start=1)
        ]
        for bucket in GLOBAL_BASELINE_BUCKETS
    }


def _final_recommendation_highlights(
    matrix: dict[str, list[dict[str, Any]]],
) -> dict[str, list[dict[str, Any]]]:
    return {
        bucket: list((matrix.get(bucket) or [])[:FINAL_EXPLANATION_PER_BUCKET])
        for bucket in GLOBAL_BASELINE_BUCKETS
    }


def _final_recommendation_count(matrix: dict[str, list[dict[str, Any]]]) -> int:
    return sum(len(matrix.get(bucket) or []) for bucket in GLOBAL_BASELINE_BUCKETS)


def _should_use_pareto_fallback(
    state: AgentState,
    *,
    question_factory_is_monkeypatched: bool,
) -> bool:
    del state
    if question_factory_is_monkeypatched:
        return False
    if os.getenv("GAOKAOLLM_OFFLINE_DETERMINISTIC") == "1":
        raise RuntimeError(
            "LLM question generation is required; "
            "GAOKAOLLM_OFFLINE_DETERMINISTIC=1 disables it."
        )
    if os.getenv("GAOKAOLLM_SKIP_LLM_PARETO_QUESTION") != "1":
        return False
    raise RuntimeError(
        "LLM question generation is required; "
        "GAOKAOLLM_SKIP_LLM_PARETO_QUESTION=1 disables it."
    )


async def _generate_pareto_question(
    state: AgentState,
) -> tuple[
    str,
    dict[str, float] | None,
    str,
    str | None,
    dict[str, Any] | None,
    str,
]:
    if str(state.get("planner_source") or "").startswith("ablation:no_ucb"):
        probe = _current_probe_name(state)
        generic_questions = {
            "probe_risk_band_relax": (
                "我先随机看一个组合编排方向：你愿意接受更高录取风险吗？"
            ),
            "probe_major_quality_relax": (
                "我先随机看一个证据丰富度方向：你愿意接受这个方案的不确定性吗？"
            ),
            "probe_employment_outcome_relax": (
                "我先随机看一个结果导向方向：你愿意接受这个方案的取舍吗？"
            ),
            "probe_region_tree_relax": (
                "我先随机看一个相邻范围方向：你愿意考虑不完全相同的选择范围吗？"
            ),
            "probe_strength_relax": (
                "我先随机看一个综合声誉方向：你愿意先比较整体吸引力吗？"
            ),
        }
        question = generic_questions.get(
            probe,
            "我先随机看一个非定向方案：你愿意接受这个方向上的小幅妥协吗？",
        )
        return (
            question,
            {key: 0.0 for key in PREFERENCE_KEYS},
            QUESTION_KIND_TRADEOFF,
            None,
            None,
            "ablation",
        )

    target_dimension = state.get("ucb_target_dimension")
    opportunity_key = _current_opportunity_key(state)
    focused_rows = _focused_candidate_rows(state)
    anchor_rows = _anchor_candidate_rows(state)
    focused_challengers = _new_challenger_rows(focused_rows, anchor_rows)
    rows = _candidate_rows(state)
    candidate_pool = _merge_candidate_rows([*anchor_rows, *focused_challengers, *rows])
    cost_dimensions = _available_cost_dimensions_for_state(
        state,
        opportunity_key,
        str(target_dimension) if target_dimension else None,
    )
    benefit_dimensions = _benefit_dimensions_for_probe(
        opportunity_key,
        str(target_dimension) if target_dimension else None,
        cost_dimensions,
    )
    forced_cost_dimension: str | None = None
    if focused_challengers and anchor_rows:
        (
            option_a,
            option_b,
            delta_phi,
            selected_cost_dimension,
            _selected_benefit_dimension,
        ) = select_constrained_tradeoff_pair(
            candidate_pool,
            cost_dimensions=cost_dimensions,
            benefit_dimensions=benefit_dimensions,
            challenger_rows=focused_challengers,
            anchor_rows=anchor_rows or rows,
            previous_delta_phi=state.get("latest_pareto_diff"),
        )
        forced_cost_dimension = selected_cost_dimension
    elif focused_rows:
        option_a = anchor_rows[0] if anchor_rows else {}
        option_b = {}
        delta_phi = {key: 0.0 for key in PREFERENCE_KEYS}
        forced_cost_dimension = _cost_dimensions_for_probe(
            opportunity_key,
            str(target_dimension) if target_dimension else None,
        )[0]
    elif target_dimension in RELAXABLE_COST_DIMENSIONS:
        forced_cost_dimension = str(target_dimension)
        option_a, option_b, delta_phi = select_forced_tradeoff_pair(
            rows,
            forced_cost_dimension,
            previous_delta_phi=state.get("latest_pareto_diff"),
        )
    else:
        option_a, option_b, delta_phi = select_max_divergence_pair(
            rows,
            previous_delta_phi=state.get("latest_pareto_diff"),
        )
        forced_cost_dimension = _choose_cost_dimension(delta_phi, None)
    if forced_cost_dimension is None:
        forced_cost_dimension = _fallback_cost_dimension_for_probe(
            opportunity_key,
            str(target_dimension) if target_dimension else None,
        )
    question_kind = _classify_question_kind(
        option_a,
        option_b,
        delta_phi,
        forced_cost_dimension,
    )
    learning_delta: dict[str, float] | None = None
    if question_kind == QUESTION_KIND_TRADEOFF:
        learning_delta = {
            key: float(delta_phi.get(key, 0.0)) for key in PREFERENCE_KEYS
        }
    else:
        learning_delta = None

    transient_state = dict(state)
    transient_state["latest_question_kind"] = question_kind
    transient_state["latest_probe_target_dimension"] = forced_cost_dimension
    instruction = _pareto_generation_instruction(transient_state)
    question_factory_is_monkeypatched = get_chat_model is not get_structured_chat_model
    _should_use_pareto_fallback(
        state,
        question_factory_is_monkeypatched=question_factory_is_monkeypatched,
    )
    text_timeout = user_visible_timeout_seconds()
    llm = (
        get_chat_model()
        if question_factory_is_monkeypatched
        else get_structured_chat_model(timeout=text_timeout, max_retries=1)
    )
    payload_text = json.dumps(
        _pareto_generation_payload(
            transient_state,
            option_a,
            option_b,
            delta_phi,
            forced_cost_dimension=forced_cost_dimension,
        ),
        ensure_ascii=False,
        default=str,
    )
    prompt = [
        SystemMessage(content=instruction),
        HumanMessage(
            content=(
                "请严格依据以下 JSON 中的真实候选事实，生成给用户看的中文追问：\n"
                f"{payload_text}"
            )
        ),
    ]
    try:
        try:
            question = await _ainvoke_text_required(
                llm,
                prompt,
                timeout=text_timeout,
                label="negotiator_pareto_question",
            )
        except RuntimeError:
            if question_factory_is_monkeypatched:
                raise
            retry_prompt = [
                SystemMessage(content=instruction),
                HumanMessage(
                    content=(
                        "上一轮模型没有输出内容。请必须输出 80 到 180 字中文，"
                        "只使用 JSON 里的学校和专业，不要编造候选：\n"
                        f"{payload_text}"
                    )
                ),
            ]
            question = await _ainvoke_text_required(
                get_reasoning_chat_model(max_retries=1),
                retry_prompt,
                timeout=reasoning_timeout_seconds(),
                label="negotiator_pareto_question_retry",
            )
        return (
            _sanitize_user_output(question),
            learning_delta,
            question_kind,
            forced_cost_dimension,
            _tradeoff_pair_payload(
                option_a,
                option_b,
                delta_phi,
                opportunity_key=opportunity_key,
                cost_dimension=forced_cost_dimension,
                question_kind=question_kind,
            ),
            "llm",
        )
    except Exception as exc:
        raise RuntimeError(
            f"LLM Pareto question generation failed: {type(exc).__name__}: {exc}"
        ) from exc


async def _generate_xai_recommendation(
    state: AgentState,
    *,
    final_recommendation_matrix: dict[str, list[dict[str, Any]]],
    final_recommendation_highlights: dict[str, list[dict[str, Any]]],
) -> str:
    weights = state.get("implicit_weights") or {}
    table_count = _final_recommendation_count(final_recommendation_matrix)
    instruction = (
        "你是面向浙江高考考生的志愿咨询顾问。"
        "探测已收敛，请输出一份可直接给考生看的最终推荐。"
        "第一段做简短的显示性偏好解释：只说明从多轮取舍中观察到的偏好倾向，"
        "不要说“精准推断”“真实权重”“极度看重”，不要写口号式总结。"
        "表达要克制、可核验，例如“目前排序更偏向专业贴合和录取稳妥，同时保留已接受的放宽条件”。"
        "随后只讲解每个冲、稳、保分桶中最值得关注的前 1 到 2 个重点项。"
        "完整志愿表会由系统界面单独展示，你不要复制完整名单，不要输出 Markdown 表格。"
        "\n当 reach/match/safety 分桶存在时，必须按 冲、稳、保 三层组织重点解释。"
        "只能引用 final_recommendation_highlights 中出现的学校和专业；"
        "可以说明完整志愿表共有多少条，但不要逐条重写。"
        "\n不要暴露内部字段名，例如 tier、c/r、utility、min_score、min_rank、tuition_delta、"
        "rank_ratio、semantic_score、_semantic_score、_lexicographic_tier、_implicit_utility。"
        "不要编造 JSON 中没有的学校、专业、分数、位次或结论。"
        "学校平台标签和综合排名分开说；平台标签更明确但排名不占优时，不要说学校整体更好。"
    )
    xai_factory_is_monkeypatched = get_chat_model is not get_structured_chat_model
    if (
        os.getenv("GAOKAOLLM_OFFLINE_DETERMINISTIC") == "1"
        and not xai_factory_is_monkeypatched
    ):
        raise RuntimeError(
            "LLM final recommendation generation is required; "
            "GAOKAOLLM_OFFLINE_DETERMINISTIC=1 disables it."
        )
    if os.getenv("GAOKAOLLM_SKIP_LLM_XAI") == "1" and not xai_factory_is_monkeypatched:
        raise RuntimeError(
            "LLM final recommendation generation is required; "
            "GAOKAOLLM_SKIP_LLM_XAI=1 disables it."
        )
    llm = (
        get_chat_model() if xai_factory_is_monkeypatched else get_reasoning_chat_model()
    )
    final_payload = json.dumps(
        {
            "implicit_weights": weights,
            "final_recommendation_count": table_count,
            "final_recommendation_highlights": final_recommendation_highlights,
        },
        ensure_ascii=False,
        default=str,
    )
    prompt = [
        SystemMessage(content=instruction),
        HumanMessage(
            content=(
                "请严格依据以下 JSON 中的真实候选事实，生成给用户看的最终推荐正文。"
                "要求语气稳妥、像真实咨询系统，不要营销腔；不要输出空内容，不要编造 JSON 之外的学校或专业。\n"
                f"{final_payload}"
            )
        ),
    ]
    try:
        try:
            content = await _ainvoke_text_required(
                llm,
                prompt,
                timeout=reasoning_timeout_seconds(),
                label="negotiator_xai_recommendation",
            )
        except RuntimeError:
            retry_prompt = [
                SystemMessage(content=instruction),
                HumanMessage(
                    content=(
                        "上一轮模型没有返回正文。请必须输出中文最终推荐正文："
                        "先用一小段克制地解释当前偏好，再按 冲、稳、保 三层讲每层前 1 到 2 个重点项。"
                        "不要输出完整表格；只能使用下面 JSON 中出现的学校、专业和字段。\n"
                        f"{final_payload}"
                    )
                ),
            ]
            content = await _ainvoke_text_required(
                get_reasoning_chat_model(max_retries=1),
                retry_prompt,
                timeout=reasoning_timeout_seconds(),
                label="negotiator_xai_recommendation_retry",
            )
        return _sanitize_user_output(content)
    except Exception as exc:
        raise RuntimeError(
            f"LLM final recommendation generation failed: {type(exc).__name__}: {exc}"
        ) from exc


def _final_recommendation_text(opportunities: dict[str, Any]) -> str:
    rows = sorted(
        _all_opportunity_rows(opportunities),
        key=_utility_sort_key,
        reverse=True,
    )[:3]
    if not rows:
        return "当前没有足够的可核验证据形成最终推荐表。"

    lines = ["偏好已经基本收敛，以下是按当前偏好重新排序后的 Top-3 可核验候选："]
    for index, row in enumerate(rows, start=1):
        lines.append(f"{index}. {_candidate_evidence_text(row)}")
    return "\n".join(lines)


def _first_available_axis(state: AgentState) -> tuple[str, list[dict[str, Any]]]:
    opportunities = state.get("pareto_opportunities", {}) or {}
    rankings = [
        str(item)
        for item in state.get("opportunity_rankings", [])
        if isinstance(item, str)
    ]
    for key in [*rankings, *OPPORTUNITY_KEYS]:
        rows = opportunities.get(key) or []
        if rows:
            return key, rows
    return "", []


def _question_for_axis(state: AgentState) -> str:
    key, rows = _first_available_axis(state)
    top = rows[0] if rows and isinstance(rows[0], dict) else {}
    school = top.get("school_name") or top.get("school") or "更高收益方案"
    province = top.get("school_province") or top.get("province") or ""
    tuition = top.get("tuition")
    tuition_delta = top.get("tuition_delta")

    if key in {"major_geo_relax", "geo_relax", "city_relax", "major_relax"}:
        place = f"{province}" if province else "外省/新地域"
        level = _school_level_text(top)
        level_text = f"，{level}" if level != "学校层级待确认" else ""
        return (
            f"我发现如果放宽地域或专业边界，可以看到 {school}（{place}{level_text}）。"
            "你能接受这类跨地域/相近专业的对照吗？"
        )
    if key == "tuition_value_relax":
        delta_text = (
            _budget_delta_text(top) or f"学费约 {tuition}"
            if tuition_delta is not None
            else f"学费约 {tuition}"
        )
        return (
            f"我发现小幅放宽预算后会出现 {school}，{delta_text}。你能接受小幅超预算吗？"
        )
    if key == "risk_band_relax":
        return "我可以只把冲刺上探边界向前打开，同时保留稳妥和保底候选。你能接受更高一些的冲刺风险吗？"
    if key in {"major_quality_relax", "strength_relax"}:
        return f"我发现 {school} 的专业或学校证据有可比变化。你愿意优先看质量证据吗？"
    if key == "employment_outcome_relax":
        return f"我发现 {school} 的就业结果证据更强。你愿意把就业表现作为更高优先级吗？"
    if key == "region_tree_relax":
        return "我可以按地域树放宽到相近城市圈或城市层级。你能接受这种地域替代吗？"
    return "我还不确定你更愿意调整哪一项约束。你想先比较地域、专业、预算，还是录取风险弹性？"


def _fallback_reply(evidence: dict[str, Any]) -> str:
    major_quality = evidence.get("major_quality_relax") or []
    tuition = evidence.get("tuition_value_relax") or []
    employment = evidence.get("employment_outcome_relax") or []
    region_tree = evidence.get("region_tree_relax") or []
    risk = evidence.get("risk_band_relax") or []

    if major_quality:
        text = "；".join(_candidate_evidence_text(row) for row in major_quality[:3])
        return (
            "我先不替你做决定，只给出可核验的专业质量证据。\n"
            f"学科质量放宽：{text}\n"
            "这些候选仍需满足分数、选科和预算等硬约束，差异在于专业排名、学科评估、特色重点或满意度证据更强。"
        )

    if tuition:
        text = "；".join(_candidate_evidence_text(row) for row in tuition[:3])
        return (
            "我先不替你做决定，只给出可核验的学费性价比证据。\n"
            f"学费预算放宽：{text}\n"
            "这些方案只是在原预算附近小幅放宽学费，重点把学校平台标签、综合排名、最低分和最低位次拆开比较。"
        )

    if employment:
        text = "；".join(_candidate_evidence_text(row) for row in employment[:3])
        return (
            "我先不替你做决定，只给出可核验的就业结果证据。\n"
            f"就业结果放宽：{text}\n"
            "这些候选仍需满足分数、选科和预算等硬约束，差异在于就业排名、行业、岗位或薪资证据更清楚。"
        )

    if region_tree:
        text = "；".join(_candidate_evidence_text(row) for row in region_tree[:3])
        return (
            "我先不替你做决定，只给出可核验的地域树证据。\n"
            f"区域圈层放宽：{text}\n"
            "这里的地域证据来自已审核的区域关系；城市层级本身不直接作为收益，仍要结合学校平台标签、综合排名和录取证据判断。"
        )

    if risk:
        text = "；".join(_candidate_evidence_text(row) for row in risk[:6])
        return (
            "我先不替你做决定，只给出可核验的冲稳保证据。\n"
            f"冲稳保组合：{text}\n"
            "这些方案保留地域、专业、选科和预算，只把单一保守偏好扩展成冲、稳、保组合。"
        )

    sections = {
        "city_relax": _join(evidence.get("city_relax") or []),
        "geo_relax": _join(evidence.get("geo_relax") or []),
        "major_relax": _join(evidence.get("major_relax") or []),
        "strength_relax": _join(evidence.get("strength_relax") or []),
        "major_geo_relax": _join(evidence.get("major_geo_relax") or [], limit=5),
    }
    return (
        "我先不替你做决定，只给出可核验的放宽证据。\n"
        + "\n".join(
            f"{_sanitize_user_output(name)}：{_sanitize_user_output(value)}"
            for name, value in sections.items()
        )
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
            "专业或地域边界放宽："
            + _join(rows, limit=5)
            + "\n这组候选用于判断：专业邻近度或地域边界是否值得小幅调整。"
        )

    def section_risk() -> str:
        text = "; ".join(_candidate_evidence_text(row) for row in risk[:6])
        return (
            "冲稳保组合："
            + text
            + "\n这组候选把单一保守偏好展开为冲、稳、保，便于比较风险层次。"
        )

    def section_quality() -> str:
        text = "; ".join(_candidate_evidence_text(row) for row in major_quality[:3])
        return (
            "学科质量放宽："
            + text
            + "\n这组候选强调学科、专业质量证据，分数和选科约束仍需同时满足。"
        )

    def section_tuition() -> str:
        text = "; ".join(_candidate_evidence_text(row) for row in tuition[:3])
        return (
            "学费预算放宽："
            + text
            + "\n这组候选只在预算附近小幅放宽，并把学校平台标签、综合排名和录取证据拆开比较。"
        )

    def section_employment() -> str:
        text = "; ".join(_candidate_evidence_text(row) for row in employment[:3])
        return (
            "就业结果放宽："
            + text
            + "\n这组候选强调就业画像，例如就业排名、行业去向、岗位或薪资证据。"
        )

    def section_region() -> str:
        text = "; ".join(_candidate_evidence_text(row) for row in region_tree[:3])
        return (
            "区域圈层放宽："
            + text
            + "\n这组候选来自已审核的区域关系，用来判断相近城市圈或区域替代是否可接受。"
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
            "学校实力优先放宽：" + _join(strength) if strength else ""
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
        selected = ["当前硬性条件之外还没有找到可核验的放宽机会。"]

    option_labels = ["选项A", "选项B"]
    labelled_selected = [
        f"{option_labels[index]}: {section}" if index < len(option_labels) else section
        for index, section in enumerate(selected)
    ]
    prefix = ""
    if clarification_hint:
        prefix = f"澄清提示：{clarification_hint}\n\n"

    return (
        prefix
        + "我不会替你直接拍板，只展示可核验的候选证据。\n"
        + "\n\n".join(labelled_selected)
        + "\n\n以上只使用你明确给出的约束和数据库中可核验的候选信息。"
    )


async def negotiator_node(state: AgentState) -> dict[str, Any]:
    print("[negotiator] generating options")
    current_probe = _current_probe_name(state)
    turns = int(state.get("negotiation_turns") or 0)
    trace_event(
        "negotiator",
        "node_start",
        {
            "current_probe": current_probe,
            "current_opportunity_key": _current_opportunity_key(state),
            "negotiation_turns": turns,
            "ucb_target_dimension": state.get("ucb_target_dimension"),
            "candidate_count": len(state.get("candidates") or []),
            "focused_candidate_count": len(_focused_candidate_rows(state)),
            "opportunity_rankings": state.get("opportunity_rankings"),
        },
    )
    if current_probe == GLOBAL_BASELINE_PROBE:
        final_recommendation_matrix = _final_recommendation_table_matrix(state)
        final_recommendation_highlights = _final_recommendation_highlights(
            final_recommendation_matrix
        )
        content = _sanitize_user_output(
            await _generate_xai_recommendation(
                state,
                final_recommendation_matrix=final_recommendation_matrix,
                final_recommendation_highlights=final_recommendation_highlights,
            )
        )
        output = {
            "messages": [AIMessage(content=content)],
            "latest_human_feedback": None,
            "latest_agent_probe_question": None,
            "latest_pareto_diff": None,
            "latest_question_kind": QUESTION_KIND_FINALIZE_OFFER,
            "latest_question_source": "llm",
            "latest_probe_target_dimension": None,
            "latest_tradeoff_pair": None,
            "final_recommendation_matrix": final_recommendation_matrix,
            "final_recommendation_highlights": final_recommendation_highlights,
            "final_recommendation_count": _final_recommendation_count(
                final_recommendation_matrix
            ),
        }
        trace_event(
            "negotiator",
            "node_end",
            {
                "mode": "final_recommendation",
                "content": content,
                "final_recommendation_count": output["final_recommendation_count"],
            },
        )
        return output

    (
        question_text,
        latest_pareto_diff,
        latest_question_kind,
        latest_probe_target_dimension,
        latest_tradeoff_pair,
        latest_question_source,
    ) = await _generate_pareto_question(state)
    question_text = _sanitize_user_output(question_text)
    trace_event(
        "negotiator",
        "interrupt_question",
        {
            "current_probe": current_probe,
            "question_text": question_text,
            "latest_pareto_diff": latest_pareto_diff,
            "latest_question_kind": latest_question_kind,
            "latest_question_source": latest_question_source,
            "latest_probe_target_dimension": latest_probe_target_dimension,
            "latest_tradeoff_pair": latest_tradeoff_pair,
        },
    )
    interrupt_payload = {
        "text": question_text,
        "latest_tradeoff_pair": latest_tradeoff_pair,
        "latest_pareto_diff": latest_pareto_diff,
        "latest_question_kind": latest_question_kind,
        "latest_question_source": latest_question_source,
        "latest_probe_target_dimension": latest_probe_target_dimension,
    }
    user_reply = interrupt(interrupt_payload)
    output = {
        "latest_human_feedback": str(user_reply),
        "latest_agent_probe_question": question_text,
        "latest_pareto_diff": latest_pareto_diff,
        "latest_question_kind": latest_question_kind,
        "latest_question_source": latest_question_source,
        "latest_probe_target_dimension": latest_probe_target_dimension,
        "latest_tradeoff_pair": latest_tradeoff_pair,
        "negotiation_turns": turns + 1,
    }
    trace_event("negotiator", "node_end", {"mode": "resumed", **output})
    return output


async def legacy_negotiator_node(state: AgentState) -> dict[str, Any]:
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

    llm = get_reasoning_chat_model()
    prompt = [
        SystemMessage(
            content=(
                "你是高考志愿谈判 Agent。只能基于给定真实数据说话。"
                "输出简洁中文，不替用户做最终决定。"
                "不要向用户输出内部字段名，例如 tier、c/r、utility、min_score、min_rank、tuition_delta 或 probe key。"
                "如果存在区域圈层放宽，要说明这是按地理板块树或城市层级树的可审计地域放宽。"
                "如果存在专业或地域边界放宽，要重点说明专业和地域联合放宽。"
                "如果存在风险带放宽，要说明冲、稳、保组合。"
                "必须给出具体学校、专业、最低分，并在可用时给出最低位次、树节点、学费、专业质量或就业证据。"
            )
        ),
        SystemMessage(content=json.dumps(evidence, ensure_ascii=False, default=str)),
    ]
    try:
        content = await _ainvoke_text_optional(
            llm,
            prompt,
            timeout=reasoning_timeout_seconds(),
            label="legacy_negotiator",
        )
    except Exception as exc:
        print(
            "[negotiator] llm_generation_failed="
            f"{type(exc).__name__}; using fallback reply"
        )
        content = _fallback_reply_v2(evidence)
    return {"messages": [AIMessage(content=_sanitize_user_output(content))]}
