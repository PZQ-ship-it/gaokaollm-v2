import json
import os
import re
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

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
    "target_provinces": None,
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

SUBJECT_COMBO_ALIASES = {
    "物化生": ["物理", "化学", "生物"],
    "物化地": ["物理", "化学", "地理"],
    "物化技": ["物理", "化学", "技术"],
    "物生地": ["物理", "生物", "地理"],
    "物生政": ["物理", "生物", "政治"],
    "物地政": ["物理", "地理", "政治"],
    "史政地": ["历史", "政治", "地理"],
    "政史地": ["政治", "历史", "地理"],
    "史地政": ["历史", "地理", "政治"],
    "历政地": ["历史", "政治", "地理"],
    "政历地": ["政治", "历史", "地理"],
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
    if "江浙沪" in text or all(name in text for name in ("江苏", "浙江", "上海")):
        extracted["target_provinces"] = ["江苏", "浙江", "上海"]
    elif "江浙" in text or all(name in text for name in ("江苏", "浙江")):
        extracted["target_provinces"] = ["江苏", "浙江"]

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
    elif "医学" in text:
        extracted["major"] = "医学"
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
        r"(?:选科|选考|科目|组合)[:：是为]*(.{0,32})",
        compact,
    )
    if window_match:
        subject_window = window_match.group(1)
        subject_window = re.split(
            r"(?:想读|想学|只看|预算|每年|学校|专业|分数|位次)",
            subject_window,
            maxsplit=1,
        )[0]

    for alias, combo_subjects in SUBJECT_COMBO_ALIASES.items():
        if alias in subject_window:
            return _dedupe_subjects(combo_subjects)

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
    if major in {"医学相关专业", "医学相关", "医学类"}:
        return "医学"
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
        "target_provinces",
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
            elif key == "target_provinces":
                merged[key] = [str(item) for item in value if str(item)]
            else:
                merged[key] = value
    if extracted.get("province"):
        merged.pop("province_relaxed", None)
    return merged


def _merge_extracted_constraints(
    base: dict[str, Any],
    override: dict[str, Any],
) -> dict[str, Any]:
    merged = dict(base or {})
    for key, value in (override or {}).items():
        if value in (None, "", []):
            continue
        if key == "target_provinces":
            existing = merged.get(key)
            if isinstance(existing, list) and len(existing) >= len(value):
                continue
        if key == "selected_subjects":
            existing = merged.get(key)
            if isinstance(existing, list) and len(existing) >= len(value):
                continue
        if key == "budget" and merged.get(key) not in (None, "", 100000):
            continue
        merged[key] = value
    return merged


async def _extract_constraints(text: str, current: dict[str, Any]) -> dict[str, Any]:
    fallback = _fallback_extract(text)
    for line in str(text).splitlines():
        line_fallback = _fallback_extract(line)
        if line_fallback:
            fallback = _merge_extracted_constraints(fallback, line_fallback)
    if fallback.get("score") and fallback.get("selected_subjects"):
        return fallback
    if os.getenv("GAOKAOLLM_OFFLINE_DETERMINISTIC") == "1":
        return fallback
    llm = get_structured_chat_model()
    prompt = [
        SystemMessage(
            content=(
                "你是高考志愿咨询中的约束抽取专员。"
                "你的任务是从用户原话中抽取已经明说的信息，只输出一个 JSON 对象，不解释、不补充候选学校。"
                "字段固定为 score(int|null), province(str|null), target_provinces(list[str]|null), major(str|null), "
                "city(str|null), strength(str|null), budget(int|null), selected_subjects(list[str]|null), "
                "risk_preference(str|null), employment_preference(str|null)。"
                'province 是考生所在省份，用于分数位次换算；target_provinces 是目标院校所在地，例如江浙沪输出["江苏","浙江","上海"]。'
                "major 使用用户明说的专业关键词；city 只记录用户明确限定的目标城市。"
                "strength 只在用户明确提到学科实力、专业排名、强校或重点学科时填写。"
                "budget 表示每年学费或费用上限。selected_subjects 只能从政治、历史、地理、物理、化学、生物、技术中抽取。"
                "用户表示外省、全国或地域不限时，target_provinces 可为空；不要把考生所在省份清空。"
                "用户表示只求稳、保守、不要冲时，risk_preference 输出 conservative。"
                "用户关注就业、薪资、行业、岗位或职业发展时，employment_preference 输出 employment_outcome。"
            )
        ),
        HumanMessage(
            content=(
                "请抽取以下输入中的高考志愿约束，只返回 JSON：\n"
                + json.dumps(
                    {
                        "当前已知约束": current or {},
                        "用户最新消息": text,
                    },
                    ensure_ascii=False,
                    default=str,
                )
            )
        ),
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
    parsed = {k: v for k, v in parsed.items() if v not in (None, "", [])}
    return _merge_extracted_constraints(fallback, parsed)


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
    original_constraints = dict(state.get("original_constraints") or {})
    for key, value in constraints.items():
        if key not in original_constraints and value not in (None, "", []):
            original_constraints[key] = value

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
            "original_constraints": original_constraints,
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
            "latest_question_kind": None,
            "latest_probe_target_dimension": None,
            "force_final_recommendation": False,
            "navigation_intent": None,
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
        "original_constraints": original_constraints,
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
        "latest_question_kind": None,
        "latest_probe_target_dimension": None,
        "force_final_recommendation": False,
        "navigation_intent": None,
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
