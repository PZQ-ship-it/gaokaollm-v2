"""LLM-assisted IcebergPersona synthesis from verified Pareto gaps."""

from __future__ import annotations

import json
from typing import Any

from gaokaollm_bench.schemas import IcebergPersona


SYSTEM_PROMPT = """
You generate benchmark personas for a gaokao recommendation agent.
Return only valid JSON matching this schema:
{
  "case_id": "string",
  "background": {"score": int, "province": "string", "subjects": list},
  "explicit_red_lines": {"...": "..."},
  "implicit_flexibilities": {"...": "..."},
  "initial_utterance": "string",
  "process_milestones": {"...": "..."}
}
The persona must be stubborn. The explicit red line must block Tier_B.
The implicit flexibility must only unlock when the target agent names Tier_B
and gives a truthful score comparison grounded in the supplied gap data.
Do not invent schools, scores, provinces, or tiers outside the gap data.
""".strip()


def _json_text_from_response(response: Any) -> str:
    if isinstance(response, str):
        return response
    if isinstance(response, dict):
        return json.dumps(response, ensure_ascii=False)

    content = getattr(response, "content", response)
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        for item in content:
            if isinstance(item, dict) and item.get("type") in {"text", "output_text"}:
                return str(item.get("text") or "")

    raise TypeError("llm_client response must be JSON text, a dict, or a message with content")


async def _invoke_llm(llm_client: Any, prompt: str) -> Any:
    if hasattr(llm_client, "ainvoke"):
        return await llm_client.ainvoke(prompt)
    if hasattr(llm_client, "acomplete"):
        return await llm_client.acomplete(prompt)
    if callable(llm_client):
        return await llm_client(prompt)
    raise TypeError("llm_client must provide ainvoke, acomplete, or be async callable")


async def synthesize_persona(gap_data: dict[str, Any], llm_client: Any) -> IcebergPersona:
    """Synthesize and validate a stubborn persona from verified gap data."""

    if not gap_data:
        raise ValueError("gap_data is required to synthesize an IcebergPersona")

    prompt = (
        f"{SYSTEM_PROMPT}\n\n"
        "Verified Pareto gap data:\n"
        f"{json.dumps(gap_data, ensure_ascii=False, indent=2)}"
    )
    response = await _invoke_llm(llm_client, prompt)
    payload = _json_text_from_response(response)

    return IcebergPersona.model_validate_json(payload)

