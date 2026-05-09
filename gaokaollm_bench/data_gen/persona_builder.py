"""LLM-assisted IcebergPersona synthesis from verified Pareto gaps."""

from __future__ import annotations

from typing import Any

from gaokaollm_bench.llm.response_utils import invoke_text_llm, json_text_from_response
from gaokaollm_bench.prompts.persona_prompts import build_persona_synthesis_prompt
from gaokaollm_bench.schemas import IcebergPersona


async def synthesize_persona(
    gap_data: dict[str, Any], llm_client: Any
) -> IcebergPersona:
    """Synthesize and validate a stubborn persona from verified gap data."""

    if not gap_data:
        raise ValueError("gap_data is required to synthesize an IcebergPersona")

    prompt = build_persona_synthesis_prompt(gap_data)
    response = await invoke_text_llm(llm_client, prompt)
    payload = json_text_from_response(response)

    return IcebergPersona.model_validate_json(payload)
