"""Low-confidence probe review chain."""

from __future__ import annotations

from typing import Any

from langchain_core.output_parsers import JsonOutputParser, StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable, RunnableLambda, RunnablePassthrough

from gaokaollm_bench.chains.json_repair import (
    parse_llm_json,
    repair_major_review_json_text,
    repair_review_payload,
)
from gaokaollm_bench.contracts.llm_io import MajorReviewOutput
from gaokaollm_bench.llm.base import BaseLLMClient
from gaokaollm_bench.llm.runnable import as_lcel_chat_model
from gaokaollm_bench.prompts.major_prompts import build_major_review_messages


def review_messages(items: list[dict[str, Any]]) -> list[dict[str, str]]:
    return build_major_review_messages(items)


def _review_prompt_vars(state: dict[str, Any]) -> dict[str, Any]:
    messages = review_messages(list(state.get("items") or []))
    return {
        "system_prompt": messages[0]["content"],
        "payload": messages[1]["content"],
    }


def _bind_json_object(chat_model: Runnable[Any, Any]) -> Runnable[Any, Any]:
    if hasattr(chat_model, "bind"):
        return chat_model.bind(response_format={"type": "json_object"})
    return chat_model


def get_major_review_chain(chat_model: Runnable[Any, Any]) -> Runnable[Any, Any]:
    """Build the LCEL low-confidence review chain."""

    prompt = ChatPromptTemplate.from_messages(
        [("system", "{system_prompt}"), ("user", "{payload}")]
    )
    raw_chain = (
        RunnableLambda(_review_prompt_vars)
        | prompt
        | _bind_json_object(chat_model)
        | StrOutputParser()
    )
    return (
        RunnablePassthrough.assign(raw_content=raw_chain)
        | RunnableLambda(repair_major_review_json_text)
        | JsonOutputParser(pydantic_object=MajorReviewOutput)
    )


async def _review_with_lcel(
    *,
    chat_model: Runnable[Any, Any],
    items: list[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    messages = review_messages(items)
    raw_chain = (
        ChatPromptTemplate.from_messages(
            [("system", "{system_prompt}"), ("user", "{payload}")]
        )
        | _bind_json_object(chat_model)
        | StrOutputParser()
    )
    raw = await raw_chain.ainvoke(
        {"system_prompt": messages[0]["content"], "payload": messages[1]["content"]}
    )
    parser_chain = RunnableLambda(repair_major_review_json_text) | JsonOutputParser(
        pydantic_object=MajorReviewOutput
    )
    await parser_chain.ainvoke({"items": items, "raw_content": raw})
    try:
        parsed = parse_llm_json(raw)
    except Exception:
        parsed = {}
    repaired = repair_review_payload(parsed, expected_items=items)
    for item in repaired.values():
        item["raw_content"] = raw
        item["error"] = None
    return repaired


async def review_major_candidates(
    *,
    llm_client: BaseLLMClient,
    model: str,
    items: list[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    try:
        if hasattr(llm_client, "as_chat_model") or (
            hasattr(llm_client, "ainvoke") and not hasattr(llm_client, "complete_json")
        ):
            chat_model = as_lcel_chat_model(
                llm_client,
                model=model,
                temperature=0,
            )
            return await _review_with_lcel(chat_model=chat_model, items=items)
        raw = await llm_client.complete_json(
            model=model,
            messages=review_messages(items),
            response_format={"type": "json_object"},
            temperature=0,
        )
        parsed = parse_llm_json(raw)
        repaired = repair_review_payload(parsed, expected_items=items)
        for item in repaired.values():
            item["raw_content"] = raw
            item["error"] = None
        return repaired
    except Exception as exc:  # pragma: no cover - external API failure
        return {
            str(item.get("major_name") or ""): {
                "major_name": str(item.get("major_name") or ""),
                "selected_label": None,
                "reason": "",
                "label_valid": False,
                "error": f"{type(exc).__name__}: {exc}",
            }
            for item in items
        }
