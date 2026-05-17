import asyncio
from collections import deque
import re
from typing import Any

from langchain_core.messages import SystemMessage

from app.evaluation.schemas import IcebergProfile


DIMENSION_TOKENS = {
    "major": ("专业匹配", "专业", "调剂", "major"),
    "geo": ("地域距离", "地域", "外省", "出省", "跨省", "城市", "geo"),
    "tuition": ("学费预算", "学费", "预算", "费用", "tuition"),
    "school": ("学校层次", "学校", "名校", "985", "211", "school"),
    "quality": ("培养质量", "质量", "实力", "学科", "quality", "strength"),
}


def dimension_from_text(text: str) -> str | None:
    lowered = text.lower()
    for dimension, tokens in DIMENSION_TOKENS.items():
        if any(token.lower() in lowered for token in tokens):
            return dimension
    return None


def extract_cost_dimension(agent_question: str) -> str | None:
    patterns = (
        r"(?:牺牲/放宽|牺牲|放宽)\s*([^\s，,。！？?]{1,24})",
        r"(?:sacrifice|relax)\s+([a-z_]{2,16})",
    )
    for pattern in patterns:
        match = re.search(pattern, agent_question, flags=re.I)
        if match:
            dimension = dimension_from_text(match.group(1))
            if dimension:
                return dimension
    return dimension_from_text(agent_question)


class UserSimulator:
    def __init__(
        self,
        profile: IcebergProfile,
        llm: Any = None,
        mock_replies: list[str] | None = None,
    ) -> None:
        self.profile = profile
        self.llm = llm
        self._mock_replies = deque(mock_replies or [])

    def generate_reply(self, agent_question: str) -> str:
        if self._mock_replies:
            return self._mock_replies.popleft()
        deterministic = self._deterministic_reply(agent_question)
        if deterministic:
            return deterministic
        if self.llm is None:
            return "我有点犹豫，还想再看看。"

        prompt = [
            SystemMessage(
                content=(
                    "你正在扮演一个填报高考志愿的考生。"
                    f"你最初的对外显式说辞是：【{self.profile.explicit_query}】。"
                    f"但你内心真实的底线是：【{self.profile.hidden_bottom_line}】。"
                    "现在 AI 志愿助手向你抛出了一个基于真实数据的妥协谈判方案："
                    f"【{agent_question}】。"
                    "请严格基于你的内心底线做出反应。如果提案满足底线，请表示接受；"
                    "如果触碰底线，请果断拒绝；如果勉强或不确定，请表示犹豫。"
                    "你的回复必须是极其简短、口语化的自然语言单句。"
                    "绝对不要主动暴露你的底层规则文本！"
                )
            )
        ]
        try:
            if hasattr(self.llm, "invoke"):
                response = self.llm.invoke(prompt)
            elif hasattr(self.llm, "ainvoke"):
                response = asyncio.run(self.llm.ainvoke(prompt))
            else:
                return "我有点犹豫，还想再看看。"
            return str(getattr(response, "content", response)).strip() or "我有点犹豫。"
        except Exception:
            return "我有点犹豫，还想再看看。"

    def _deterministic_reply(self, agent_question: str) -> str:
        """Deterministic policy for reproducible no-fallback benchmark episodes."""

        question = agent_question.lower()
        profile_id = self.profile.profile_id
        bottom_line = self.profile.hidden_bottom_line

        def mentions(*tokens: str) -> bool:
            haystack = f"{question}\n{profile_id.lower()}"
            return any(token.lower() in haystack for token in tokens)

        def cost_dimension() -> str | None:
            patterns = (
                r"(?:牺牲/放宽|牺牲|放宽)\s*([^\s，,。！？?]{1,24})",
                r"sacrifice\s+([a-z_]{2,16})",
            )
            for pattern in patterns:
                match = re.search(pattern, agent_question, flags=re.I)
                if not match:
                    continue
                text = match.group(1).lower()
                if any(token in text for token in ("专业", "major", "调剂")):
                    return "major"
                if any(
                    token in text for token in ("地域", "外省", "出省", "geo", "城市")
                ):
                    return "geo"
                if any(token in text for token in ("学费", "预算", "费用", "tuition")):
                    return "tuition"
                if any(
                    token in text for token in ("学校", "层次", "985", "school", "名校")
                ):
                    return "school"
                if any(
                    token in text
                    for token in ("质量", "实力", "学科", "quality", "strength")
                ):
                    return "quality"
            return None

        cost = extract_cost_dimension(agent_question)
        if cost is None:
            cost = cost_dimension()

        asks = {
            "major": cost == "major"
            or (
                cost is None
                and any(
                    token in question for token in ("专业", "major", "调剂", "专业匹配")
                )
            ),
            "geo": cost == "geo"
            or (
                cost is None
                and any(
                    token in question
                    for token in ("地域", "外省", "出省", "geo", "跨省")
                )
            ),
            "tuition": cost == "tuition"
            or (
                cost is None
                and any(
                    token in question for token in ("学费", "预算", "费用", "tuition")
                )
            ),
            "school": cost == "school"
            or (
                cost is None
                and any(
                    token in question
                    for token in ("学校", "985", "211", "层次", "school", "名校")
                )
            ),
            "quality": cost == "quality"
            or (
                cost is None
                and any(
                    token in question
                    for token in ("质量", "实力", "学科", "quality", "strength")
                )
            ),
        }

        if profile_id.startswith("robust_") or profile_id.startswith(
            "synthetic_pressure_"
        ):
            bottom = bottom_line.lower()
            strict_major = "专业" in bottom or "major" in profile_id
            strict_geo = "出省" in bottom or "地域" in bottom or "geo" in profile_id
            strict_tuition = (
                "学费" in bottom or "预算" in bottom or "tuition" in profile_id
            )
            strict_school = (
                "学校层次" in bottom
                or "强校" in bottom
                or "school_extreme" in profile_id
            )
            strict_quality = "培养质量" in bottom or "quality" in profile_id

            if asks["major"] and strict_major:
                return "专业不能偏太远，这个我不接受。"
            if asks["geo"] and strict_geo:
                return "不行，我绝对不出省。"
            if asks["tuition"] and strict_tuition:
                return "预算不能超，学费太贵绝对不行。"
            if asks["school"] and strict_school:
                return "如果学校层次不够硬，我不能接受。"
            if asks["quality"] and strict_quality:
                return "培养质量必须够强，否则我不接受。"
            if "balanced" in profile_id:
                return "这个方向可以考虑，但我不想单独牺牲某一项。"
            return "这个问题没问到我的真正底线，我先保留。"

        if profile_id == "profile_major_bottom_line":
            if mentions("专业", "major", "调剂", "专业匹配"):
                return "专业不能偏太远，这个我不接受。"
            if mentions("学校", "985", "层次", "school", "名校"):
                return "我得先确认专业还是计算机大类，这个问题我有点犹豫。"
            if mentions("地域", "外省", "出省", "geo"):
                return "如果专业对口我才会考虑跨省，现在还不确定。"
            return "这个方向我有点犹豫，还想再看看。"

        if profile_id == "profile_geo_bottom_line":
            if mentions("地域", "外省", "出省", "geo", "跨省"):
                return "不行，我绝对不出省。"
            if mentions("学校", "专业", "学费", "预算", "school", "major", "tuition"):
                return "只要不出省这些都能谈，但这个问题没问到地域，我先保留。"
            return "这个问题和我的底线关系不大，我有点犹豫。"

        if profile_id == "profile_tuition_bottom_line":
            if mentions("学费", "预算", "费用", "tuition"):
                return "预算不能超，学费太贵绝对不行。"
            if mentions("学校", "985", "层次", "school", "名校"):
                return "名校可以考虑，但如果没说费用我还是不确定。"
            if mentions("地域", "专业", "geo", "major"):
                return "地域和专业可以灵活一点，但我主要还是要看费用。"
            return "这个方向我还不确定，想再看看费用。"

        return ""
