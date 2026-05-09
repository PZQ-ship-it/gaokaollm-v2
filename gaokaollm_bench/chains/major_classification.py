"""Direct LLM major classification chain."""

from __future__ import annotations

from typing import Any

from pydantic import ValidationError

from gaokaollm_bench.chains.graph import JsonChainState, build_json_chain
from gaokaollm_bench.chains.json_repair import (
    direct_response_format,
    parse_llm_json,
    repair_major_payload,
)
from gaokaollm_bench.contracts.llm_io import (
    ChainResult,
    MajorClassificationInput,
    MajorClassificationOutput,
    MajorLabelOption,
)
from gaokaollm_bench.llm.base import BaseLLMClient
from gaokaollm_bench.prompts.major_prompts import build_major_classification_messages


def build_label_options(rows: list[dict[str, Any]]) -> list[MajorLabelOption]:
    return [MajorLabelOption.model_validate(row) for row in rows]


def direct_prompt(input_data: MajorClassificationInput) -> list[dict[str, str]]:
    return build_major_classification_messages(input_data)


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

    async def _call_llm(state: JsonChainState) -> dict[str, Any]:
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

    def _build_prompt(_: JsonChainState) -> dict[str, Any]:
        return {
            "messages": direct_prompt(chain_input),
            "response_format": direct_response_format(
                label_options, allow_null=allow_null
            ),
        }

    def _parse_json(state: JsonChainState) -> dict[str, Any]:
        try:
            return {"parsed_json": parse_llm_json(state.get("raw_content", "{}"))}
        except Exception as exc:
            return {
                "parsed_json": {},
                "error": state.get("error") or f"{type(exc).__name__}: {exc}",
            }

    def _repair_json(state: JsonChainState) -> dict[str, Any]:
        return {
            "repaired_json": repair_major_payload(
                state.get("parsed_json"),
                major_name=chain_input.major_name,
                label_options=label_options,
                allow_null=allow_null,
            )
        }

    def _validate(state: JsonChainState) -> dict[str, Any]:
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

    chain = build_json_chain(
        build_prompt=_build_prompt,
        call_llm=_call_llm,
        parse_json=_parse_json,
        repair_json=_repair_json,
        validate=_validate,
    )
    state = await chain.ainvoke({"input": chain_input.model_dump()})
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
