"""Adapters that let project LLM clients participate in LCEL chains."""

from __future__ import annotations

from typing import Any

from langchain_core.runnables import Runnable, RunnableLambda

from gaokaollm_bench.llm.response_utils import invoke_text_llm


def prompt_value_to_text(prompt_value: Any) -> str:
    """Render a LangChain PromptValue or message-like object as plain text."""

    if isinstance(prompt_value, str):
        return prompt_value
    if hasattr(prompt_value, "to_string"):
        return str(prompt_value.to_string())
    if hasattr(prompt_value, "messages"):
        parts = []
        for message in prompt_value.messages:
            content = getattr(message, "content", message)
            parts.append(str(content))
        return "\n".join(parts)
    return str(prompt_value)


def as_lcel_chat_model(
    llm_client: Any,
    *,
    model: str | None = None,
    temperature: float = 0,
    max_tokens: int | None = None,
) -> Runnable[Any, Any]:
    """Return a Runnable-compatible chat model for LCEL composition.

    Real OpenAI-compatible clients expose ``as_chat_model``. Test doubles often
    only expose ``ainvoke(prompt: str)``; those are wrapped in RunnableLambda so
    the production chain shape remains the same under tests.
    """

    if hasattr(llm_client, "as_chat_model"):
        return llm_client.as_chat_model(
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
        )
    if hasattr(llm_client, "invoke") and hasattr(llm_client, "ainvoke"):
        return llm_client

    async def _invoke(prompt_value: Any, **_: Any) -> Any:
        return await invoke_text_llm(llm_client, prompt_value_to_text(prompt_value))

    return RunnableLambda(_invoke)
