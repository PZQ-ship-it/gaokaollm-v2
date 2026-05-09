"""LLM-backed stubborn user simulator for multi-turn benchmark episodes."""

from __future__ import annotations

import json
from typing import Any

from langchain_core.output_parsers import JsonOutputParser, StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableLambda
from pydantic import BaseModel, ConfigDict

from gaokaollm_bench.chains.json_repair import repair_json_text
from gaokaollm_bench.llm.runnable import as_lcel_chat_model
from gaokaollm_bench.schemas import IcebergPersona


class SimulatorStep(BaseModel):
    """Structured output expected from the user-simulator LLM."""

    model_config = ConfigDict(extra="forbid")

    thought: str
    is_persuaded: bool
    utterance: str


class UserSimulator:
    """Role-play an IcebergPersona and update persuasion state turn by turn."""

    def __init__(self, persona: IcebergPersona, llm_client: Any):
        self.persona = persona
        self.llm_client = llm_client
        self.internal_state: dict[str, Any] = {
            "is_persuaded": False,
            "turn_count": 0,
            "last_thought": "",
        }

    def _system_prompt(self) -> str:
        return (
            "你是一个高考生模拟器，必须严格扮演给定画像。\n"
            f"考生属性: {json.dumps(self.persona.background, ensure_ascii=False)}\n"
            f"显性死守红线: {json.dumps(self.persona.explicit_red_lines, ensure_ascii=False)}\n"
            f"隐性妥协条件: {json.dumps(self.persona.implicit_flexibilities, ensure_ascii=False)}\n"
            "如果被测系统只是空洞说教、泛泛建议、情绪安慰或没有真实学校名称和分数对比，你必须拒绝妥协。\n"
            "只有当被测系统准确抛出符合隐性妥协条件的具体学校名称，并给出真实分数对比时，"
            "你才可以表现出惊喜并同意妥协。\n"
            "必须只返回 JSON，格式为: "
            '{"thought": "内部内心戏", "is_persuaded": false, "utterance": "对外口语化回复"}'
        )

    def _build_prompt(self, agent_reply: str) -> str:
        return (
            f"{self._system_prompt()}\n\n"
            f"当前内部状态: {json.dumps(self.internal_state, ensure_ascii=False)}\n"
            f"被测系统回复: {agent_reply}\n"
            "请输出本轮 JSON。"
        )

    def _chain(self):
        chat_model = as_lcel_chat_model(self.llm_client, temperature=0)
        return (
            ChatPromptTemplate.from_messages([("user", "{prompt}")])
            | chat_model
            | StrOutputParser()
            | RunnableLambda(repair_json_text)
            | JsonOutputParser(pydantic_object=SimulatorStep)
        )

    async def chat(self, agent_reply: str) -> str:
        """Return the simulated user's public utterance and update internal state."""

        prompt = self._build_prompt(agent_reply)
        parsed = await self._chain().ainvoke({"prompt": prompt})
        step = SimulatorStep.model_validate(parsed)

        self.internal_state.update(
            {
                "is_persuaded": step.is_persuaded,
                "turn_count": int(self.internal_state.get("turn_count", 0)) + 1,
                "last_thought": step.thought,
            }
        )
        return step.utterance
