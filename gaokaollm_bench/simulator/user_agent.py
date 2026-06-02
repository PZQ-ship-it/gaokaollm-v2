"""LLM-backed stubborn user simulator for multi-turn benchmark episodes."""

from __future__ import annotations

import json
from typing import Any

from langchain_core.output_parsers import JsonOutputParser, StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableLambda
from pydantic import BaseModel, ConfigDict

from gaokaollm_bench.chains.json_repair import repair_json_text
from gaokaollm_bench.evaluator.candidate_set_oracle import (
    agent_supplied_candidate_evidence,
    protected_candidate_tokens,
)
from gaokaollm_bench.llm.runnable import as_lcel_chat_model
from gaokaollm_bench.schemas import IcebergPersona
from gaokaollm_bench.utils.trace import trace_event


class SimulatorStep(BaseModel):
    """Structured output expected from the user-simulator LLM."""

    model_config = ConfigDict(extra="ignore")

    thought: str = ""
    is_persuaded: bool = False
    utterance: str = ""


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
            "严禁你主动泄露隐性妥协条件、volunteer_set、acceptable_candidates、隐藏候选学校、隐藏专业或隐藏最低分；"
            "如果被测系统没有先说出这些证据，你只能要求它给出具体学校、专业、年份、最低分和位次。\n"
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
        trace_event(
            "UserSimulator",
            "simulator_call_start",
            {
                "case_id": self.persona.case_id,
                "turn_count": self.internal_state.get("turn_count"),
                "agent_reply": agent_reply,
            },
        )
        parsed = await self._chain().ainvoke({"prompt": prompt})
        step = SimulatorStep.model_validate(parsed)
        if not step.utterance.strip():
            step.utterance = "请继续给出更具体的学校名称和分数对比。"
        raw_step = step.model_dump()
        step = self._apply_leakage_guard(step, agent_reply)
        trace_event(
            "UserSimulator",
            "simulator_call_end",
            {
                "case_id": self.persona.case_id,
                "raw_step": raw_step,
                "guarded_step": step.model_dump(),
                "leakage_guard_applied": raw_step != step.model_dump(),
            },
        )

        self.internal_state.update(
            {
                "is_persuaded": step.is_persuaded,
                "turn_count": int(self.internal_state.get("turn_count", 0)) + 1,
                "last_thought": step.thought,
            }
        )
        return step.utterance

    def _apply_leakage_guard(
        self,
        step: SimulatorStep,
        agent_reply: str,
    ) -> SimulatorStep:
        hidden = _hidden_candidate_tokens(self.persona.implicit_flexibilities)
        if not hidden:
            return step
        if _agent_supplied_hidden_evidence(agent_reply, hidden):
            return step
        leaked = [
            token
            for token in hidden["protected_tokens"]
            if token and token in step.utterance
        ]
        if not leaked:
            return step
        return SimulatorStep(
            thought=(
                f"{step.thought} | simulator leakage guard removed hidden tokens: "
                f"{', '.join(leaked[:3])}"
            ),
            is_persuaded=False,
            utterance=(
                "你现在还没有给出能让我改口的具体证据。"
                "请直接给出真实学校、专业、年份最低分、位次和优势对比，我再判断能不能接受。"
            ),
        )


def _hidden_candidate_tokens(flex: dict[str, Any]) -> dict[str, list[str]]:
    return protected_candidate_tokens(flex)


def _agent_supplied_hidden_evidence(
    agent_reply: str,
    hidden: dict[str, list[str]],
) -> bool:
    return agent_supplied_candidate_evidence(agent_reply, hidden)
