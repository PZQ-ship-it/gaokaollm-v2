"""Provider-neutral helpers for simple text/JSON LLM responses."""

from __future__ import annotations

import json
from typing import Any


def json_text_from_response(response: Any) -> str:
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

    raise TypeError("LLM response must be JSON text, a dict, or a message with content")


async def invoke_text_llm(llm_client: Any, prompt: str) -> Any:
    if hasattr(llm_client, "ainvoke"):
        return await llm_client.ainvoke(prompt)
    if hasattr(llm_client, "acomplete"):
        return await llm_client.acomplete(prompt)
    if callable(llm_client):
        return await llm_client(prompt)
    raise TypeError("llm_client must provide ainvoke, acomplete, or be async callable")
