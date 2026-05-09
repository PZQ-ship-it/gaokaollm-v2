"""LCEL chain for process-quality LLM judging."""

from __future__ import annotations

from typing import Any

from langchain_core.output_parsers import JsonOutputParser, StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable, RunnableLambda

from gaokaollm_bench.chains.json_repair import repair_json_text
from gaokaollm_bench.llm.runnable import as_lcel_chat_model
from gaokaollm_bench.prompts.evaluator_prompts import build_process_judge_prompt
from gaokaollm_bench.schemas import EvalReport, IcebergPersona, Transcript


def get_process_judge_chain(chat_model: Runnable[Any, Any]) -> Runnable[Any, Any]:
    """Build ChatPromptTemplate -> LLM -> repair -> EvalReport parser."""

    return (
        ChatPromptTemplate.from_messages([("user", "{prompt}")])
        | chat_model
        | StrOutputParser()
        | RunnableLambda(repair_json_text)
        | JsonOutputParser(pydantic_object=EvalReport)
    )


async def evaluate_process_with_chain(
    *,
    transcript: Transcript,
    persona: IcebergPersona,
    llm_client: Any,
    model: str | None = None,
) -> EvalReport:
    chat_model = as_lcel_chat_model(llm_client, model=model, temperature=0)
    chain = get_process_judge_chain(chat_model)
    parsed = await chain.ainvoke(
        {"prompt": build_process_judge_prompt(transcript, persona)}
    )
    report = EvalReport.model_validate(parsed)
    if report.case_id != persona.case_id:
        return report.model_copy(update={"case_id": persona.case_id})
    return report
