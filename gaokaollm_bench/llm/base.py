"""Provider-neutral LLM client interfaces."""

from __future__ import annotations

from typing import Any, Protocol


class BaseLLMClient(Protocol):
    async def complete_json(
        self,
        *,
        model: str,
        messages: list[dict[str, str]],
        response_format: dict[str, Any] | None = None,
        max_tokens: int | None = None,
        temperature: float = 0,
    ) -> str:
        """Return the raw text content for a JSON-oriented chat completion."""
