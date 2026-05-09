"""LCEL chain for IcebergPersona synthesis."""

from __future__ import annotations

from typing import Any

from langchain_core.output_parsers import JsonOutputParser, StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable, RunnableLambda

from gaokaollm_bench.chains.json_repair import repair_json_text
from gaokaollm_bench.llm.runnable import as_lcel_chat_model
from gaokaollm_bench.prompts.persona_prompts import build_persona_synthesis_prompt
from gaokaollm_bench.schemas import IcebergPersona


def get_persona_synthesis_chain(chat_model: Runnable[Any, Any]) -> Runnable[Any, Any]:
    """Build ChatPromptTemplate -> LLM -> repair -> Pydantic parser."""

    return (
        ChatPromptTemplate.from_messages([("user", "{prompt}")])
        | chat_model
        | StrOutputParser()
        | RunnableLambda(repair_json_text)
        | JsonOutputParser(pydantic_object=IcebergPersona)
    )


async def synthesize_persona_with_chain(
    *,
    gap_data: dict[str, Any],
    llm_client: Any,
    model: str | None = None,
) -> IcebergPersona:
    if not gap_data:
        raise ValueError("gap_data is required to synthesize an IcebergPersona")
    chat_model = as_lcel_chat_model(llm_client, model=model, temperature=0)
    chain = get_persona_synthesis_chain(chat_model)
    parsed = await chain.ainvoke({"prompt": build_persona_synthesis_prompt(gap_data)})
    return IcebergPersona.model_validate(parsed)
