import asyncio
from collections import deque
from typing import Any

from langchain_core.messages import SystemMessage

from app.evaluation.schemas import IcebergProfile


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
