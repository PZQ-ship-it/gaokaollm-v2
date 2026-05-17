import json
import os
import re
from typing import Any

from langchain_core.messages import AIMessage, SystemMessage

from app.core.llm_client import (
    ainvoke_with_timeout,
    get_structured_chat_model,
    structured_timeout_seconds,
)
from app.flows.probers import run_baseline
from app.schemas.state import (
    DEFAULT_IMPLICIT_WEIGHTS,
    DEFAULT_WEIGHT_VARIANCE,
    AgentState,
)
from gaokaollm_bench.utils.trace import trace_event


DEFAULT_CONSTRAINTS = {
    "score": None,
    "province": "浙江",
    "city": None,
    "major": None,
    "strength": None,
    "budget": 100000,
    "selected_subjects": None,
    "risk_preference": None,
    "employment_preference": None,
}

VALID_SUBJECTS = ["政治", "历史", "地理", "物理", "化学", "生物", "技术"]
SUBJECT_ALIASES = {
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


def _latest_user_text(state: AgentState) -> str:
    for message in reversed(state.get("messages", [])):
        if getattr(message, "type", None) == "human":
            return str(message.content)
    return ""


def _json_from_text(text: str) -> dict[str, Any]:
    match = re.search(r"\{.*\}", text, flags=re.S)
    if not match:
        return {}
    try:
        data = json.loads(match.group(0))
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def _fallback_extract(text: str) -> dict[str, Any]:
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
    if "budget" not in extracted and any(
        token in text for token in ("学费别太贵", "学费不要太贵", "费用别太高")
    ):
        extracted["budget"] = 6000

    province_names = [
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
    ]
    for province in province_names:
        if province in text:
            extracted["province"] = province
            break

    city_names = [
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
    ]
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
            "哪里都可以",
            "外省也可以",
            "外省也可考虑",
            "可以出省",
            "接受外省",
        )
    ):
        extracted["province"] = None
        extracted["province_relaxed"] = True

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

    if any(
        token in text
        for token in (
            "学科实力",
            "学科评估",
            "专业排名",
            "重点学科",
            "强校",
            "学校实力",
            "discipline",
            "ranking",
        )
    ):
        extracted["strength"] = "school_strength"

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

    return extracted


def _dedupe_subjects(subjects: list[str]) -> list[str]:
    deduped: list[str] = []
    for subject in subjects:
        if subject not in deduped:
            deduped.append(subject)
    return deduped[:3]


def _extract_subjects(text: str) -> list[str]:
    subjects: list[str] = []
    compact = re.sub(r"\s+", "", text)
    compact = (
        compact.replace("地域不限", "")
        .replace("地区不限", "")
        .replace("地域不限制", "")
        .replace("地区不限制", "")
    )

    subject_window = compact
    window_match = re.search(
        r"(?:选科|选考|科目|组合)[:：是为]*(.{0,16})",
        compact,
    )
    if window_match:
        subject_window = window_match.group(1)

    for subject in VALID_SUBJECTS:
        if subject in subject_window and subject not in subjects:
            subjects.append(subject)

    for alias, subject in SUBJECT_ALIASES.items():
        if alias in subject_window and subject not in subjects:
            subjects.append(subject)

    return _dedupe_subjects(subjects)


def _normalize_subjects(value: Any) -> list[str] | None:
    if value in (None, ""):
        return None
    raw_subjects = value if isinstance(value, list) else [value]
    subjects: list[str] = []
    for raw in raw_subjects:
        text = str(raw)
        matched = SUBJECT_ALIASES.get(text)
        if not matched:
            extracted = _extract_subjects(text)
            for subject in extracted:
                if subject not in subjects:
                    subjects.append(subject)
            continue
        if matched not in subjects:
            subjects.append(matched)
    return subjects[:3] or None


def _normalize_major(value: Any) -> str:
    major = str(value)
    if major == "临床":
        return "临床医学"
    return major


def _merge_constraints(
    current: dict[str, Any], extracted: dict[str, Any]
) -> dict[str, Any]:
    merged = {**DEFAULT_CONSTRAINTS, **(current or {})}
    if extracted.get("province_relaxed"):
        merged["province"] = None
        merged["province_relaxed"] = True
    for key in (
        "score",
        "province",
        "city",
        "major",
        "strength",
        "budget",
        "selected_subjects",
        "risk_preference",
        "employment_preference",
    ):
        value = extracted.get(key)
        if value not in (None, ""):
            if key == "selected_subjects":
                merged[key] = _normalize_subjects(value)
            elif key == "major":
                merged[key] = _normalize_major(value)
            else:
                merged[key] = value
    if extracted.get("province"):
        merged.pop("province_relaxed", None)
    return merged


async def _extract_constraints(text: str, current: dict[str, Any]) -> dict[str, Any]:
    fallback = _fallback_extract(text)
    if fallback.get("score") and fallback.get("selected_subjects"):
        return fallback
    if os.getenv("GAOKAOLLM_OFFLINE_DETERMINISTIC") == "1":
        return fallback
    llm = get_structured_chat_model()
    prompt = [
        SystemMessage(
            content=(
                "你是高考志愿约束抽取器。只输出 JSON，不要解释。"
                "字段固定为 score(int|null), province(str|null), major(str|null), "
                "city(str|null), strength(str|null), budget(int|null), selected_subjects(list[str]|null), "
                "risk_preference(str|null), employment_preference(str|null)。"
                "province 表示目标院校所在地。major 使用用户提到的专业关键词。"
                "city 表示用户明确限定的目标学校城市，例如杭州、宁波、南京。"
                "strength 表示用户明确关注学科实力、专业排名、强校或重点学科时的偏好。"
                "budget 表示用户明确提出的每年学费或费用上限，例如6000以内。"
                "如果用户明确表示外省、全国或地域不限，province 输出 null。"
                "如果用户明确表示只求稳、保守、不要冲，risk_preference 输出 conservative。"
                "如果用户明确关注就业、薪资、行业、岗位或职业发展，employment_preference 输出 employment_outcome。"
                "selected_subjects 只能从政治、历史、地理、物理、化学、生物、技术中抽取。"
            )
        ),
        SystemMessage(
            content=f"当前已知约束: {json.dumps(current or {}, ensure_ascii=False)}"
        ),
        SystemMessage(content=f"用户最新消息: {text}"),
    ]
    try:
        response = await ainvoke_with_timeout(
            llm,
            prompt,
            timeout=structured_timeout_seconds(),
            label="gatekeeper",
        )
        parsed = _json_from_text(str(response.content))
    except Exception as exc:
        print(
            "[gatekeeper] llm_extract_failed="
            f"{type(exc).__name__}; using fallback extractor"
        )
        parsed = {}
    return {**fallback, **{k: v for k, v in parsed.items() if v not in (None, "")}}


async def gatekeeper_node(state: AgentState) -> dict[str, Any]:
    print("[gatekeeper] extracting constraints")
    trace_event(
        "gatekeeper",
        "node_start",
        {
            "rewritten_query": state.get("rewritten_query"),
            "current_constraints": state.get("constraints", {}),
        },
    )
    implicit_weights = dict(DEFAULT_IMPLICIT_WEIGHTS)
    implicit_weights.update(state.get("implicit_weights") or {})
    weight_variance = dict(DEFAULT_WEIGHT_VARIANCE)
    weight_variance.update(state.get("weight_variance") or {})
    negotiation_turns = int(state.get("negotiation_turns") or 0)
    original_text = _latest_user_text(state)
    rewritten_text = str(state.get("rewritten_query") or "").strip()
    if rewritten_text and rewritten_text != original_text:
        text = f"{original_text}\n{rewritten_text}"
    else:
        text = original_text
    current = state.get("constraints", {})
    extracted = await _extract_constraints(text, current)
    constraints = _merge_constraints(current, extracted)

    missing = []
    if not constraints.get("score"):
        missing.append("score")
    if not constraints.get("selected_subjects"):
        missing.append("selected_subjects")
    if missing:
        ask_parts = []
        if "score" in missing:
            ask_parts.append("高考分数")
        if "selected_subjects" in missing:
            ask_parts.append(
                "3门选考科目（政治、历史、地理、物理、化学、生物、技术中任选3门）"
            )
        message = AIMessage(content=f"我还需要补充：{'；'.join(ask_parts)}。")
        output = {
            "messages": [message],
            "constraints": constraints,
            "baseline_results": [],
            "score_waste": 0,
            "pareto_opportunities": {},
            "missing_constraints": missing,
            "implicit_weights": implicit_weights,
            "weight_variance": weight_variance,
            "negotiation_turns": negotiation_turns,
            "latest_human_feedback": None,
            "latest_agent_probe_question": None,
            "latest_pareto_diff": None,
        }
        trace_event(
            "gatekeeper",
            "node_end",
            {
                "missing_constraints": missing,
                "constraints": constraints,
                "baseline_count": 0,
            },
        )
        return output

    baseline = await run_baseline(constraints)
    score = int(constraints["score"])
    score_waste = 0
    if baseline:
        score_waste = score - int(float(baseline[0]["min_score"]))

    print(f"[gatekeeper] baseline={len(baseline)} score_waste={score_waste}")
    output = {
        "constraints": constraints,
        "baseline_results": baseline,
        "score_waste": score_waste,
        "pareto_opportunities": {},
        "missing_constraints": [],
        "implicit_weights": implicit_weights,
        "weight_variance": weight_variance,
        "negotiation_turns": negotiation_turns,
        "latest_human_feedback": None,
        "latest_agent_probe_question": None,
        "latest_pareto_diff": None,
    }
    trace_event(
        "gatekeeper",
        "node_end",
        {
            "missing_constraints": [],
            "constraints": constraints,
            "baseline_count": len(baseline),
            "score_waste": score_waste,
            "baseline_preview": baseline[:3],
        },
    )
    return output
