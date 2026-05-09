"""OpenAI-compatible chat adapter."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from gaokaollm_bench.constrains.llm import ENV_OPENAI_API_KEY, ENV_OPENAI_BASE_URL


def sanitize_ssl_env() -> list[str]:
    removed = []
    for env_name in ("SSL_CERT_FILE", "REQUESTS_CA_BUNDLE"):
        value = os.environ.get(env_name)
        if value and not Path(value).exists():
            os.environ.pop(env_name, None)
            removed.append(env_name)
    return removed


class OpenAIChatClient:
    def __init__(
        self,
        *,
        api_key: str | None = None,
        base_url: str | None = None,
        timeout: float = 90.0,
        max_retries: int = 0,
    ) -> None:
        load_dotenv()
        sanitize_ssl_env()
        self.api_key = api_key or os.getenv(ENV_OPENAI_API_KEY)
        self.base_url = base_url or os.getenv(ENV_OPENAI_BASE_URL) or None
        self.timeout = timeout
        self.max_retries = max_retries
        if not self.api_key:
            raise RuntimeError(f"{ENV_OPENAI_API_KEY} is required")

    async def complete_json(
        self,
        *,
        model: str,
        messages: list[dict[str, str]],
        response_format: dict[str, Any] | None = None,
        max_tokens: int | None = None,
        temperature: float = 0,
    ) -> str:
        from openai import AsyncOpenAI

        client = AsyncOpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
            timeout=self.timeout,
            max_retries=self.max_retries,
        )
        kwargs: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
        }
        if response_format is not None:
            kwargs["response_format"] = response_format
        if max_tokens is not None:
            kwargs["max_tokens"] = max_tokens
        response = await client.chat.completions.create(**kwargs)
        return response.choices[0].message.content or "{}"
