import json
import os
import re
from typing import Any

from langchain_core.messages import AIMessage, SystemMessage
from langgraph.types import interrupt

from app.core.llm_client import (
    ainvoke_with_timeout,
    get_reasoning_chat_model,
    get_structured_chat_model,
    reasoning_timeout_seconds,
    structured_timeout_seconds,
)
from app.schemas.state import DEFAULT_WEIGHT_VARIANCE, AgentState


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
PREFERENCE_KEYS = ("school", "major", "tuition", "quality", "geo")
GLOBAL_BASELINE_BUCKETS = ("reach", "match", "safety")
DIMENSION_LABELS = {
    "school": "学校层次(school)",
    "major": "专业匹配(major)",
    "tuition": "学费预算(tuition)",
    "quality": "培养质量(quality)",
    "geo": "地域距离(geo)",
}

# Backward-compatible test hook retained for older negotiator tests.
get_chat_model = get_structured_chat_model

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


def _candidate_rows(state: AgentState) -> list[dict[str, Any]]:
    explicit = state.get("candidates") or []
    if explicit:
        return _iter_rows(explicit)
    return sorted(
        _all_opportunity_rows(state.get("pareto_opportunities", {}) or {}),
        key=_utility_sort_key,
        reverse=True,
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


def _candidate_school(row: dict[str, Any]) -> str:
    return str(row.get("school_name") or row.get("school") or "").strip()


def _same_visible_candidate(a: dict[str, Any], b: dict[str, Any]) -> bool:
    school_a = _candidate_school(a)
    school_b = _candidate_school(b)
    if school_a and school_b and school_a == school_b:
        return True
    return _candidate_identity(a) == _candidate_identity(b)


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
    rows = sorted(
        [dict(row) for row in candidates if isinstance(row, dict)],
        key=_utility_sort_key,
        reverse=True,
    )
    if not rows:
        return {}, {}, {key: 0.0 for key in PREFERENCE_KEYS}
    option_a = rows[0]
    previous: dict[str, float] = {}
    if isinstance(previous_delta_phi, dict):
        for key in PREFERENCE_KEYS:
            try:
                previous[key] = float(previous_delta_phi.get(key, 0.0))
            except (TypeError, ValueError):
                previous[key] = 0.0

    best_b: dict[str, Any] = {}
    best_delta = {key: 0.0 for key in PREFERENCE_KEYS}
    best_score = -1.0
    for candidate in rows[1:top_k]:
        if _same_visible_candidate(option_a, candidate):
            continue
        delta = _phi_delta_b_minus_a(option_a, candidate)
        try:
            cost_delta = float(delta.get(cost_dimension, 0.0))
        except (TypeError, ValueError):
            cost_delta = 0.0
        positive_gain = max(
            (
                float(value)
                for key, value in delta.items()
                if key != cost_dimension
                and isinstance(value, (int, float))
                and float(value) > 0.05
            ),
            default=0.0,
        )
        if cost_delta >= -0.05 or positive_gain <= 0.05:
            continue
        if previous:
            repeat_distance = sum(
                abs(delta.get(key, 0.0) - previous.get(key, 0.0))
                for key in PREFERENCE_KEYS
            )
            if repeat_distance < 0.08:
                continue
        score = abs(cost_delta) + positive_gain + sum(abs(v) for v in delta.values())
        if score > best_score:
            best_b = candidate
            best_delta = delta
            best_score = score
    return option_a, best_b, best_delta


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
            return f"效用特征={_format_numeric(value)}"
    return "候选字段缺失"


def _dimension_value_text(row: dict[str, Any], dimension: str) -> str:
    if dimension == "school":
        school = _short_display(
            _first_present(row, ("school_name", "school")) or "未知学校",
            max_len=24,
        )
        tier = _first_present(
            row, ("school_tier", "school_level", "tier_label", "tier")
        )
        return f"{school}，层次={tier}" if tier is not None else str(school)
    if dimension == "major":
        major = _display_major(
            _first_present(row, ("major_name", "major")) or "未知专业"
        )
        level = _first_present(row, ("major_relax_level", "relaxation_stage"))
        return f"{major}，放宽层级={level}" if level is not None else str(major)
    if dimension == "geo":
        province = _short_display(
            _first_present(row, ("school_province", "province")) or "未知省份",
            max_len=16,
        )
        raw_city = _first_present(row, ("school_city", "city"))
        city = _short_display(raw_city, max_len=16) if raw_city else None
        level = _first_present(row, ("geo_relax_level", "region_relax_level"))
        location = f"{province}/{city}" if city else str(province)
        return f"{location}，地域放宽层级={level}" if level is not None else location
    if dimension == "tuition":
        tuition = _first_present(row, ("tuition", "tuition_fee"))
        delta = _first_present(row, ("tuition_delta", "budget_delta"))
        if tuition is not None and delta is not None:
            return f"学费={_format_numeric(tuition)}，预算差={_format_numeric(delta)}"
        if tuition is not None:
            return f"学费={_format_numeric(tuition)}"
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
            parts.append(f"质量分/评级={_format_numeric(quality)}")
        if ranking is not None:
            parts.append(f"排名={_format_numeric(ranking)}")
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
        return "特征差值接近 0"
    direction = "提升" if delta > 0 else "下降"
    return f"{direction} {abs(delta):.2f} 个标准化效用点"


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
    if forced_cost_dimension in PREFERENCE_KEYS:
        return str(forced_cost_dimension)
    negative = [
        (key, float(value))
        for key, value in diff.items()
        if isinstance(value, (int, float)) and float(value) < -0.05
    ]
    if negative:
        return min(negative, key=lambda item: item[1])[0]
    return "geo"


def _has_real_benefit(diff: dict[str, Any], cost: str) -> bool:
    return any(
        key != cost and isinstance(value, (int, float)) and float(value) > 0.05
        for key, value in diff.items()
    )


def _locked_preference_text(dimension: str) -> str:
    return {
        "major": "专业不偏离",
        "geo": "地域不越界",
        "tuition": "预算不突破",
        "school": "学校层次不下降",
        "quality": "培养质量不下降",
    }.get(dimension, "这项偏好不放宽")


def _alternative_tradeoff_text(dimension: str) -> str:
    return {
        "major": "地域/学校层次",
        "geo": "专业/学校层次",
        "tuition": "学校层次/培养质量",
        "school": "专业/培养质量",
        "quality": "学校层次/专业",
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
    cost_label = DIMENSION_LABELS.get(cost, cost)
    benefit_label = DIMENSION_LABELS.get(benefit, benefit)
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
    return (
        f"如果保留 {title_a}，你保留 {cost_label}：{kept_cost}；"
        f"如果改看 {title_b}，需要你牺牲/放宽 {cost_label}：{cost_transition}，"
        f"但能换取 {benefit_label}：{benefit_transition}（{benefit_effect}）。"
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
    has_real_benefit = _has_real_benefit(diff, cost)
    benefit_label = DIMENSION_LABELS.get(benefit, benefit)
    cost_label = DIMENSION_LABELS.get(cost, cost)
    school_a = _short_display((payload.get("option_a") or {}).get("school") or "方案A")
    if not option_b:
        current_cost = _dimension_value_text(option_a, cost)
        return (
            f"本轮候选不足以形成取舍。以 {school_a} 为参照，"
            f"目前只看到 {cost_label} 边界在「{current_cost}」，"
            f"但没有可验证收益维度可供换取；我不建议你牺牲/放宽 {cost_label} "
            f"去换取不存在的收益，这属于低信息量探测。"
            f"你是否先保留 {cost_label}，让我下一轮改看其他候选？"
        )
    if option_b and _same_visible_candidate(option_a, option_b):
        current_cost = _dimension_value_text(option_a, cost)
        return (
            f"本轮候选不足以形成取舍。两个候选在可见学校上过于接近，"
            f"目前只看到 {cost_label} 边界在「{current_cost}」，"
            f"但没有可验证收益维度可供换取；我不建议你牺牲/放宽 {cost_label} "
            f"去换取不存在的收益，这属于低信息量探测。"
            f"你是否先保留 {cost_label}，让我下一轮改看其他候选？"
        )
    if not has_real_benefit:
        cost_transition = _dimension_transition_text(
            option_a, option_b, cost, verb="放宽"
        )
        return (
            f"本轮候选不足以形成取舍。候选之间只显示出牺牲/放宽 {cost_label}："
            f"{cost_transition}，但没有可验证收益维度可供换取；"
            f"我不建议你用这项放宽换取不存在的收益，这属于低信息量探测。"
            f"你是否先保留 {cost_label}，让我下一轮改看其他候选？"
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
    cost_label = DIMENSION_LABELS.get(forced_cost_dimension, forced_cost_dimension)
    benefit_label = DIMENSION_LABELS.get(benefit, benefit)
    locked_text = _locked_preference_text(forced_cost_dimension)
    alternatives = _alternative_tradeoff_text(forced_cost_dimension)
    round_number = negotiation_turns + 1
    has_real_benefit = _has_real_benefit(delta_phi, forced_cost_dimension)
    reply_hint = {
        "major": "专业不能偏太远",
        "geo": "不能出省或离目标地域太远",
        "tuition": "预算不能超",
        "school": "学校层次不能降",
        "quality": "培养质量不能弱",
    }.get(forced_cost_dimension, "这条底线不能轻易动")
    if option_a and option_b and has_real_benefit:
        fact_sentence = _tradeoff_fact_sentence(
            option_a,
            option_b,
            forced_cost_dimension,
            benefit,
            delta_phi,
        )
        return (
            f"你刚才拒绝了“{reply_hint}”。第 {round_number} 轮我按“{locked_text}”先锁定，"
            f"再看这组事实取舍："
            f"{fact_sentence}"
            f"如果仍要牺牲/放宽 {cost_label} 换取 {benefit_label}，"
            f"你更不能接受哪一项？"
        )
    elif option_a:
        current = _dimension_value_text(option_a, forced_cost_dimension)
        return (
            f"你刚才拒绝了“{reply_hint}”。第 {round_number} 轮我按“{locked_text}”先锁定；"
            f"本轮候选不足以形成能牺牲/放宽 {cost_label} 换取其他收益的事实取舍，"
            f"目前只看到 {cost_label} 边界在「{current}」。"
            f"是否改看 {alternatives} 上的取舍？"
        )
    else:
        return (
            f"你刚才拒绝了“{reply_hint}”。第 {round_number} 轮我按“{locked_text}”先锁定；"
            f"本轮候选不足以形成能牺牲/放宽 {cost_label} 换取 {benefit_label} 的事实取舍。"
            f"是否改看 {alternatives} 上的取舍？"
        )


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
    weight_text = "，".join(f"{key}={value:.2f}" for key, value in sorted_weights)
    lines = [
        f"偏好解释：系统根据多轮反馈推断出的权重为 {weight_text}。这意味着最终推荐会优先尊重权重更高的维度，同时避免已识别的硬性底线。",
        "最终推荐名单：",
    ]
    matrix = recommendation_matrix or {}
    if any(matrix.get(bucket) for bucket in GLOBAL_BASELINE_BUCKETS):
        labels = {"reach": "Reach", "match": "Match", "safety": "Safety"}
        for bucket in GLOBAL_BASELINE_BUCKETS:
            bucket_rows = matrix.get(bucket) or []
            if not bucket_rows:
                continue
            lines.append(f"{labels[bucket]}:")
            for index, row in enumerate(bucket_rows[:3], start=1):
                lines.append(f"{index}. {_score_text(row)}")
    else:
        for index, row in enumerate(candidates[:5], start=1):
            lines.append(f"{index}. {_score_text(row)}")
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
            key: _iter_rows(global_result.get(key)) for key in GLOBAL_BASELINE_BUCKETS
        }
    rows = _candidate_rows(state)
    matrix: dict[str, list[dict[str, Any]]] = {
        key: [] for key in GLOBAL_BASELINE_BUCKETS
    }
    for row in rows:
        bucket = str(row.get("risk_bucket") or row.get("risk_level") or "")
        if bucket in matrix:
            matrix[bucket].append(row)
    return matrix


async def _generate_pareto_question(
    state: AgentState,
) -> tuple[str, dict[str, float]]:
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
        return question, {key: 0.0 for key in PREFERENCE_KEYS}

    forced_cost_dimension = state.get("ucb_target_dimension")
    rows = _candidate_rows(state)
    if forced_cost_dimension in PREFERENCE_KEYS:
        option_a, option_b, delta_phi = select_forced_tradeoff_pair(
            rows,
            str(forced_cost_dimension),
            previous_delta_phi=state.get("latest_pareto_diff"),
        )
    else:
        option_a, option_b, delta_phi = select_max_divergence_pair(
            rows,
            previous_delta_phi=state.get("latest_pareto_diff"),
        )
    fallback = _fallback_pareto_question(
        option_a,
        option_b,
        delta_phi,
        forced_cost_dimension=(
            str(forced_cost_dimension) if forced_cost_dimension else None
        ),
    )
    if (
        forced_cost_dimension in PREFERENCE_KEYS
        and int(state.get("negotiation_turns") or 0) > 0
    ):
        fallback = _followup_pareto_question(
            delta_phi,
            str(forced_cost_dimension),
            int(state.get("negotiation_turns") or 0),
            option_a=option_a,
            option_b=option_b,
        )
    if forced_cost_dimension in PREFERENCE_KEYS:
        # UCB-directed probes intentionally ask about the probed cost dimension.
        # Store a crisp one-dimensional counterfactual so the BT tracker updates
        # the same bottom-line dimension even when the SQL pair has unrelated
        # quality/school/tuition differences. Keeping the raw SQL residual here
        # leaks irrelevant tradeoffs into the Bradley-Terry gradient and makes the
        # no-tracker baseline look artificially strong.
        delta_phi = {key: 0.0 for key in PREFERENCE_KEYS}
        delta_phi[str(forced_cost_dimension)] = -1.0
    instruction = (
        "你是一个谈判专家。请基于方案A和B的特征差异，向用户发起一个简短的"
        "‘二选一帕累托权衡提问’。只有当方案B在代价维度真实下降、且另一个维度真实上升时，"
        "才使用‘牺牲/放宽 [代价维度] 换取 [收益维度]’这种边际替代率（MRS）句式；"
        "如果没有真实收益，必须说明候选不足以形成取舍，不能伪造收益。"
        "直接提问，绝不要寒暄或做最终推荐！"
    )
    question_factory_is_monkeypatched = get_chat_model is not get_structured_chat_model
    if (
        os.getenv("GAOKAOLLM_OFFLINE_DETERMINISTIC") == "1"
        or os.getenv("GAOKAOLLM_SKIP_LLM_PARETO_QUESTION", "1") == "1"
    ) and not question_factory_is_monkeypatched:
        return fallback, delta_phi
    llm = get_chat_model()
    prompt = [
        SystemMessage(content=instruction),
        SystemMessage(
            content=json.dumps(
                _pareto_prompt_payload(option_a, option_b, delta_phi),
                ensure_ascii=False,
                default=str,
            )
        ),
    ]
    try:
        response = await ainvoke_with_timeout(
            llm,
            prompt,
            timeout=structured_timeout_seconds(),
            label="negotiator_pareto_question",
        )
        question = str(response.content).strip()
        return question or fallback, delta_phi
    except Exception as exc:
        print(
            "[negotiator] pareto_question_failed="
            f"{type(exc).__name__}; using fallback question"
        )
        return fallback, delta_phi


async def _generate_xai_recommendation(state: AgentState) -> str:
    weights = state.get("implicit_weights") or {}
    recommendation_matrix = _global_recommendation_matrix(state)
    matrix_candidates = _iter_rows(recommendation_matrix)
    candidates = (matrix_candidates or _candidate_rows(state))[:9]
    fallback = _xai_fallback_text(weights, candidates, recommendation_matrix)
    instruction = (
        "探测已收敛，请输出最终志愿表。你必须在报告的第一段进行‘显示性偏好解释’："
        "用极具专业感和体贴的自然语言，向用户解释系统推断出的真实偏好权重"
        "（如：系统发现您极度看重核心专业，但对地域具有较高的妥协弹性）。"
        "然后再基于此模型展示最终推荐名单。"
    )
    instruction = (
        instruction
        + "\nEndgame matrix requirement: when reach/match/safety buckets are present, "
        "write the final report in three clear layers: Reach, Match, and Safety."
    )
    xai_factory_is_monkeypatched = get_chat_model is not get_structured_chat_model
    if (
        os.getenv("GAOKAOLLM_OFFLINE_DETERMINISTIC") == "1"
        or os.getenv("GAOKAOLLM_SKIP_LLM_XAI", "1") == "1"
    ) and not xai_factory_is_monkeypatched:
        return fallback
    llm = (
        get_chat_model() if xai_factory_is_monkeypatched else get_reasoning_chat_model()
    )
    prompt = [
        SystemMessage(content=instruction),
        SystemMessage(
            content=json.dumps(
                {
                    "implicit_weights": weights,
                    "recommendation_matrix": {
                        key: _compact(value)
                        for key, value in recommendation_matrix.items()
                    },
                    "final_candidates": _compact(candidates),
                },
                ensure_ascii=False,
                default=str,
            )
        ),
    ]
    try:
        response = await ainvoke_with_timeout(
            llm,
            prompt,
            timeout=reasoning_timeout_seconds(),
            label="negotiator_xai_recommendation",
        )
        content = str(response.content).strip()
        return content or fallback
    except Exception as exc:
        print(
            "[negotiator] xai_recommendation_failed="
            f"{type(exc).__name__}; using fallback recommendation"
        )
        return fallback


def _final_recommendation_text(opportunities: dict[str, Any]) -> str:
    rows = sorted(
        _all_opportunity_rows(opportunities),
        key=_utility_sort_key,
        reverse=True,
    )[:3]
    if not rows:
        return "当前没有足够的可核验证据形成最终推荐表。"

    lines = ["偏好已经基本收敛，以下是按当前隐性效用排序的 Top-3 可核验候选："]
    for index, row in enumerate(rows, start=1):
        utility = row.get("_implicit_utility")
        utility_text = ""
        if utility is not None:
            try:
                utility_text = f" utility={float(utility):.3f}"
            except (TypeError, ValueError):
                utility_text = f" utility={utility}"
        lines.append(f"{index}. {_score_text(row)}{utility_text}")
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
    tier = top.get("tier")
    tuition = top.get("tuition")
    tuition_delta = top.get("tuition_delta")

    if key in {"major_geo_relax", "geo_relax", "city_relax", "major_relax"}:
        place = f"{province}" if province else "外省/新地域"
        tier_text = f" tier={tier}" if tier is not None else ""
        return (
            f"我发现如果放宽地域或专业边界，可以看到 {school}（{place}{tier_text}）。"
            "你能接受这类跨地域/相近专业的妥协吗？"
        )
    if key == "tuition_value_relax":
        delta_text = (
            f"学费增加约 {tuition_delta}"
            if tuition_delta is not None
            else f"学费约 {tuition}"
        )
        return (
            f"我发现小幅放宽预算后会出现 {school}，{delta_text}。你能接受小幅超预算吗？"
        )
    if key == "risk_band_relax":
        return "我可以把方案从单一求稳扩展成冲稳保组合。你能接受保留少量冲刺志愿吗？"
    if key in {"major_quality_relax", "strength_relax"}:
        return f"我发现 {school} 的专业/学校质量证据更强。你愿意优先考虑质量提升吗？"
    if key == "employment_outcome_relax":
        return f"我发现 {school} 的就业结果证据更强。你愿意把就业表现作为更高优先级吗？"
    if key == "region_tree_relax":
        return "我可以按地域树放宽到相近城市圈或城市层级。你能接受这种地域替代吗？"
    return (
        "我还不确定你更愿意牺牲哪一项约束。你能接受小幅放宽地域来换取更高学校层次吗？"
    )


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
    current_probe = _current_probe_name(state)
    turns = int(state.get("negotiation_turns") or 0)
    if current_probe == GLOBAL_BASELINE_PROBE:
        content = await _generate_xai_recommendation(state)
        return {
            "messages": [AIMessage(content=content)],
            "latest_human_feedback": None,
            "latest_agent_probe_question": None,
        }

    question_text, latest_pareto_diff = await _generate_pareto_question(state)
    user_reply = interrupt(question_text)
    return {
        "latest_human_feedback": str(user_reply),
        "latest_agent_probe_question": question_text,
        "latest_pareto_diff": latest_pareto_diff,
        "negotiation_turns": turns + 1,
    }


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
                "如果存在 region_tree_relax，要说明这是按地理板块树或城市层级树的可审计地域放宽。"
                "如果存在 major_geo_relax，要重点说明专业和地域联合放宽。"
                "如果存在 risk_band_relax，要说明 chong/wen/bao 组合。"
                "必须给出具体学校、专业、最低分，并在可用时给出最低位次、树节点、学费、专业质量或就业证据。"
            )
        ),
        SystemMessage(content=json.dumps(evidence, ensure_ascii=False, default=str)),
    ]
    try:
        response = await ainvoke_with_timeout(
            llm,
            prompt,
            timeout=reasoning_timeout_seconds(),
            label="legacy_negotiator",
        )
        content = str(response.content)
    except Exception as exc:
        print(
            "[negotiator] llm_generation_failed="
            f"{type(exc).__name__}; using fallback reply"
        )
        content = _fallback_reply_v2(evidence)
    return {"messages": [AIMessage(content=content)]}
