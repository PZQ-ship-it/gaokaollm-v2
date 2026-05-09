"""Direct LLM major classification chain."""

from __future__ import annotations

from typing import Any

from langchain_core.output_parsers import JsonOutputParser, StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable, RunnableLambda, RunnablePassthrough
from pydantic import ValidationError

from gaokaollm_bench.chains.json_repair import (
    direct_response_format,
    parse_llm_json,
    repair_major_classification_json_text,
    repair_major_payload,
)
from gaokaollm_bench.contracts.llm_io import (
    ChainResult,
    MajorClassificationInput,
    MajorClassificationOutput,
    MajorLabelOption,
)
from gaokaollm_bench.llm.base import BaseLLMClient
from gaokaollm_bench.llm.runnable import as_lcel_chat_model
from gaokaollm_bench.prompts.major_prompts import build_major_classification_messages


def build_label_options(rows: list[dict[str, Any]]) -> list[MajorLabelOption]:
    return [MajorLabelOption.model_validate(row) for row in rows]


def direct_prompt(input_data: MajorClassificationInput) -> list[dict[str, str]]:
    return build_major_classification_messages(input_data)


def _prompt_vars(
    state: dict[str, Any],
    *,
    label_options: list[MajorLabelOption],
    allow_null: bool,
) -> dict[str, Any]:
    input_data = MajorClassificationInput(
        major_name=str(state.get("major_name") or ""),
        normalized_text=state.get("normalized_text"),
        labels=label_options,
        allow_null=allow_null,
        labels_only=bool(state.get("labels_only", False)),
    )
    messages = direct_prompt(input_data)
    return {
        "system_prompt": messages[0]["content"],
        "payload": messages[1]["content"],
    }


def _bind_response_format(
    chat_model: Runnable[Any, Any],
    response_format: dict[str, Any],
) -> Runnable[Any, Any]:
    if hasattr(chat_model, "bind"):
        return chat_model.bind(response_format=response_format)
    return chat_model


def get_major_classification_chain(
    chat_model: Runnable[Any, Any],
    *,
    label_options: list[MajorLabelOption],
    allow_null: bool = False,
) -> Runnable[Any, Any]:
    """Build the LCEL direct-classification chain.

    Shape mirrors the article-generation convention:
    ChatPromptTemplate -> chat model -> StrOutputParser -> repair -> Pydantic JSON parser.
    """

    prompt = ChatPromptTemplate.from_messages(
        [("system", "{system_prompt}"), ("user", "{payload}")]
    )
    response_format = direct_response_format(label_options, allow_null=allow_null)
    bound_model = _bind_response_format(chat_model, response_format)
    raw_chain = (
        RunnableLambda(
            lambda state: _prompt_vars(
                state,
                label_options=label_options,
                allow_null=allow_null,
            )
        )
        | prompt
        | bound_model
        | StrOutputParser()
    )
    return (
        RunnablePassthrough.assign(raw_content=raw_chain)
        | RunnableLambda(
            lambda state: repair_major_classification_json_text(
                state,
                label_options=label_options,
                allow_null=allow_null,
            )
        )
        | JsonOutputParser(pydantic_object=MajorClassificationOutput)
    )


async def _classify_with_lcel(
    *,
    chat_model: Runnable[Any, Any],
    chain_input: MajorClassificationInput,
) -> ChainResult:
    state = {
        "major_name": chain_input.major_name,
        "normalized_text": chain_input.normalized_text,
        "labels_only": chain_input.labels_only,
    }
    messages = direct_prompt(chain_input)
    prompt = ChatPromptTemplate.from_messages(
        [("system", "{system_prompt}"), ("user", "{payload}")]
    )
    prompt_payload = {
        "system_prompt": messages[0]["content"],
        "payload": messages[1]["content"],
    }
    response_mode = "lcel_json_schema"
    try:
        raw_chain = (
            prompt
            | _bind_response_format(
                chat_model,
                direct_response_format(
                    chain_input.labels, allow_null=chain_input.allow_null
                ),
            )
            | StrOutputParser()
        )
        raw_content = await raw_chain.ainvoke(prompt_payload)
    except Exception as schema_exc:
        response_mode = "lcel_json_object_fallback"
        try:
            raw_chain = (
                prompt
                | _bind_response_format(chat_model, {"type": "json_object"})
                | StrOutputParser()
            )
            raw_content = await raw_chain.ainvoke(prompt_payload)
        except Exception:
            return ChainResult(
                major_name=chain_input.major_name,
                selected_label=None,
                raw_content="{}",
                parsed_json={},
                repaired_json={
                    "major_name": chain_input.major_name,
                    "selected_label": None,
                    "schema_valid": False,
                    "label_valid": False,
                    "raw_output": {},
                },
                validated_output=None,
                schema_valid=False,
                label_valid=False,
                repair_notes=[],
                response_mode="lcel_error",
                error=f"{type(schema_exc).__name__}: {schema_exc}",
            )
    parser_chain = RunnableLambda(
        lambda parser_state: repair_major_classification_json_text(
            parser_state,
            label_options=chain_input.labels,
            allow_null=chain_input.allow_null,
        )
    ) | JsonOutputParser(pydantic_object=MajorClassificationOutput)
    parsed_output = await parser_chain.ainvoke({**state, "raw_content": raw_content})
    try:
        parsed_json = parse_llm_json(raw_content)
    except Exception:
        parsed_json = {}
    repaired = repair_major_payload(
        parsed_json,
        major_name=chain_input.major_name,
        label_options=chain_input.labels,
        allow_null=chain_input.allow_null,
    )
    validated: dict[str, Any] | None = None
    error = None
    try:
        validated = MajorClassificationOutput.model_validate(parsed_output).model_dump()
    except ValidationError as exc:
        error = str(exc)
    return ChainResult(
        major_name=str(repaired.get("major_name") or chain_input.major_name),
        selected_label=repaired.get("selected_label"),
        raw_content=raw_content,
        parsed_json=parsed_json,
        repaired_json=repaired,
        validated_output=validated,
        schema_valid=bool(repaired.get("schema_valid")),
        label_valid=bool(repaired.get("label_valid")),
        repair_notes=list(repaired.get("repair_notes") or []),
        response_mode=response_mode,
        error=error,
    )


async def classify_major(
    *,
    llm_client: BaseLLMClient,
    model: str,
    major_name: str,
    label_options: list[MajorLabelOption],
    normalized_text: str | None = None,
    allow_null: bool = False,
    labels_only: bool = False,
) -> ChainResult:
    chain_input = MajorClassificationInput(
        major_name=major_name,
        normalized_text=normalized_text,
        labels=label_options,
        allow_null=allow_null,
        labels_only=labels_only,
    )

    if hasattr(llm_client, "as_chat_model") or (
        hasattr(llm_client, "ainvoke") and not hasattr(llm_client, "complete_json")
    ):
        chat_model = as_lcel_chat_model(
            llm_client,
            model=model,
            temperature=0,
            max_tokens=128,
        )
        return await _classify_with_lcel(
            chat_model=chat_model,
            chain_input=chain_input,
        )

    async def _call_llm(state: dict[str, Any]) -> dict[str, Any]:
        try:
            raw = await llm_client.complete_json(
                model=model,
                messages=state["messages"],
                response_format=state["response_format"],
                max_tokens=128,
                temperature=0,
            )
            return {"raw_content": raw, "response_mode": "json_schema"}
        except Exception as schema_exc:
            try:
                raw = await llm_client.complete_json(
                    model=model,
                    messages=state["messages"],
                    response_format={"type": "json_object"},
                    max_tokens=128,
                    temperature=0,
                )
                return {"raw_content": raw, "response_mode": "json_object_fallback"}
            except Exception:
                return {
                    "raw_content": "{}",
                    "error": f"{type(schema_exc).__name__}: {schema_exc}",
                    "response_mode": "error",
                }

    def _build_prompt(_: dict[str, Any]) -> dict[str, Any]:
        return {
            "messages": direct_prompt(chain_input),
            "response_format": direct_response_format(
                label_options, allow_null=allow_null
            ),
        }

    def _parse_json(state: dict[str, Any]) -> dict[str, Any]:
        try:
            return {"parsed_json": parse_llm_json(state.get("raw_content", "{}"))}
        except Exception as exc:
            return {
                "parsed_json": {},
                "error": state.get("error") or f"{type(exc).__name__}: {exc}",
            }

    def _repair_json(state: dict[str, Any]) -> dict[str, Any]:
        return {
            "repaired_json": repair_major_payload(
                state.get("parsed_json"),
                major_name=chain_input.major_name,
                label_options=label_options,
                allow_null=allow_null,
            )
        }

    def _validate(state: dict[str, Any]) -> dict[str, Any]:
        repaired = state["repaired_json"]
        validated: dict[str, Any] | None = None
        error = state.get("error")
        try:
            if repaired.get("schema_valid"):
                validated = MajorClassificationOutput(
                    major_name=str(repaired["major_name"]),
                    selected_label=repaired.get("selected_label"),
                ).model_dump()
        except ValidationError as exc:
            error = error or str(exc)
        return {"validated_output": validated, "error": error}

    state: dict[str, Any] = {"input": chain_input.model_dump()}
    state.update(_build_prompt(state))
    state.update(await _call_llm(state))
    state.update(_parse_json(state))
    state.update(_repair_json(state))
    state.update(_validate(state))
    repaired = state.get("repaired_json") or {}
    return ChainResult(
        major_name=str(repaired.get("major_name") or major_name),
        selected_label=repaired.get("selected_label"),
        raw_content=state.get("raw_content", ""),
        parsed_json=state.get("parsed_json"),
        repaired_json=repaired,
        validated_output=state.get("validated_output"),
        schema_valid=bool(repaired.get("schema_valid")),
        label_valid=bool(repaired.get("label_valid")),
        repair_notes=list(repaired.get("repair_notes") or []),
        response_mode=state.get("response_mode"),
        error=state.get("error"),
    )
