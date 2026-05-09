import json
import re
from typing import Any

from langchain_core.messages import AIMessage, SystemMessage

from app.core.llm_client import get_chat_model
from app.flows.probers import run_baseline
from app.schemas.state import AgentState


DEFAULT_CONSTRAINTS = {
    "score": None,
    "province": "浙江",
    "major": None,
    "budget": 100000,
    "selected_subjects": None,
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

    score_match = re.search(r"(\d{3})\s*分", text)
    if score_match:
        extracted["score"] = int(score_match.group(1))

    budget_match = re.search(r"预算\s*(\d+)", text)
    if budget_match:
        extracted["budget"] = int(budget_match.group(1))

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

    subjects = _extract_subjects(text)
    if subjects:
        extracted["selected_subjects"] = subjects

    return extracted


def _extract_subjects(text: str) -> list[str]:
    subjects: list[str] = []
    compact = re.sub(r"\s+", "", text)

    for alias, subject in SUBJECT_ALIASES.items():
        if alias in compact and subject not in subjects:
            subjects.append(subject)

    return subjects[:3]


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
    for key in ("score", "province", "major", "budget", "selected_subjects"):
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
    llm = get_chat_model()
    prompt = [
        SystemMessage(
            content=(
                "你是高考志愿约束抽取器。只输出 JSON，不要解释。"
                "字段固定为 score(int|null), province(str|null), major(str|null), "
                "budget(int|null), selected_subjects(list[str]|null)。"
                "province 表示目标院校所在地。major 使用用户提到的专业关键词。"
                "如果用户明确表示外省、全国或地域不限，province 输出 null。"
                "selected_subjects 只能从政治、历史、地理、物理、化学、生物、技术中抽取。"
            )
        ),
        SystemMessage(
            content=f"当前已知约束: {json.dumps(current or {}, ensure_ascii=False)}"
        ),
        SystemMessage(content=f"用户最新消息: {text}"),
    ]
    try:
        response = await llm.ainvoke(prompt)
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
    text = _latest_user_text(state)
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
        return {
            "messages": [message],
            "constraints": constraints,
            "baseline_results": [],
            "score_waste": 0,
            "pareto_opportunities": {},
            "missing_constraints": missing,
        }

    baseline = await run_baseline(constraints)
    score = int(constraints["score"])
    score_waste = 0
    if baseline:
        score_waste = score - int(float(baseline[0]["min_score"]))

    print(f"[gatekeeper] baseline={len(baseline)} score_waste={score_waste}")
    return {
        "constraints": constraints,
        "baseline_results": baseline,
        "score_waste": score_waste,
        "pareto_opportunities": {},
        "missing_constraints": [],
    }
