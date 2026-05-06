import json
import re
from typing import Any

from langchain_core.messages import AIMessage, SystemMessage

from app.core.llm_client import get_chat_model
from app.flows.probers import run_baseline
from app.schemas.state import AgentState


DEFAULT_CONSTRAINTS = {
    "score": None,
    "province": None,
    "major": None,
    "budget": 100000,
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

    if any(token in text for token in ("外省", "全国", "地域不限", "地区不限", "哪里都可以")):
        extracted["province"] = None
        extracted["province_relaxed"] = True

    if "临床" in text:
        extracted["major"] = "临床医学"
    elif "计算机" in text:
        extracted["major"] = "计算机"
    elif "法学" in text:
        extracted["major"] = "法学"

    return extracted


def _merge_constraints(current: dict[str, Any], extracted: dict[str, Any]) -> dict[str, Any]:
    merged = {**DEFAULT_CONSTRAINTS, **(current or {})}
    if extracted.get("province_relaxed"):
        merged["province"] = None
        merged["province_relaxed"] = True
    for key in ("score", "province", "major", "budget"):
        value = extracted.get(key)
        if value not in (None, ""):
            merged[key] = value
    if extracted.get("province"):
        merged.pop("province_relaxed", None)
    return merged


async def _extract_constraints(text: str, current: dict[str, Any]) -> dict[str, Any]:
    llm = get_chat_model()
    prompt = [
        SystemMessage(
            content=(
                "你是高考志愿约束抽取器。只输出 JSON，不要解释。"
                "字段固定为 score(int|null), province(str|null), major(str|null), budget(int|null)。"
                "province 表示目标院校所在地。major 使用用户提到的专业关键词。"
                "如果用户明确表示外省、全国或地域不限，province 输出 null。"
            )
        ),
        SystemMessage(content=f"当前已知约束: {json.dumps(current or {}, ensure_ascii=False)}"),
        SystemMessage(content=f"用户最新消息: {text}"),
    ]
    response = await llm.ainvoke(prompt)
    parsed = _json_from_text(str(response.content))
    fallback = _fallback_extract(text)
    return {**fallback, **{k: v for k, v in parsed.items() if v not in (None, "")}}


async def gatekeeper_node(state: AgentState) -> dict[str, Any]:
    print("[gatekeeper] extracting constraints")
    text = _latest_user_text(state)
    current = state.get("constraints", {})
    extracted = await _extract_constraints(text, current)
    constraints = _merge_constraints(current, extracted)

    missing = [key for key in ("score", "major") if not constraints.get(key)]
    if not constraints.get("province") and not constraints.get("province_relaxed"):
        missing.append("province")
    if missing:
        message = AIMessage(content=f"我还需要补充这些硬约束：{', '.join(missing)}。")
        return {
            "messages": [message],
            "constraints": constraints,
            "baseline_results": [],
            "score_waste": 0,
            "pareto_opportunities": {},
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
    }
