import os
import argparse
import asyncio
from typing import Any

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI


load_dotenv()

DEFAULT_MODEL = "gpt-5.2"
DEFAULT_STRUCTURED_MODEL = "deepseek-ai/DeepSeek-V4-Flash"
DEFAULT_TIMEOUT_SECONDS = 60.0
DEFAULT_STRUCTURED_TIMEOUT_SECONDS = 45.0
DEFAULT_REASONING_TIMEOUT_SECONDS = 180.0
DEFAULT_MAX_RETRIES = 2
DEFAULT_STRUCTURED_MAX_RETRIES = 0
DEFAULT_STRUCTURED_MAX_COMPLETION_TOKENS = 256


def _float_env(name: str, default: float) -> float:
    try:
        return float(os.getenv(name) or default)
    except (TypeError, ValueError):
        return default


def _int_env(name: str, default: int) -> int:
    try:
        return int(os.getenv(name) or default)
    except (TypeError, ValueError):
        return default


def describe_llm_config() -> dict[str, Any]:
    """Return non-sensitive LLM connection metadata for diagnostics."""
    api_key = os.getenv("OPENAI_API_KEY")
    return {
        "api_key_present": bool(api_key),
        "base_url": os.getenv("OPENAI_BASE_URL") or None,
        "model": os.getenv("OPENAI_MODEL") or DEFAULT_MODEL,
        "reasoning_model": os.getenv("OPENAI_MODEL") or DEFAULT_MODEL,
        "structured_model": os.getenv("SMALL_MODEL") or DEFAULT_STRUCTURED_MODEL,
        "timeout": _float_env("OPENAI_TIMEOUT", DEFAULT_TIMEOUT_SECONDS),
        "structured_timeout": structured_timeout_seconds(),
        "reasoning_timeout": reasoning_timeout_seconds(),
        "max_retries": _int_env("OPENAI_MAX_RETRIES", DEFAULT_MAX_RETRIES),
        "structured_max_retries": _int_env(
            "OPENAI_STRUCTURED_MAX_RETRIES",
            DEFAULT_STRUCTURED_MAX_RETRIES,
        ),
        "structured_max_completion_tokens": _int_env(
            "OPENAI_STRUCTURED_MAX_COMPLETION_TOKENS",
            DEFAULT_STRUCTURED_MAX_COMPLETION_TOKENS,
        ),
    }


def structured_timeout_seconds() -> float:
    return _float_env(
        "OPENAI_STRUCTURED_TIMEOUT",
        _float_env("OPENAI_TIMEOUT", DEFAULT_STRUCTURED_TIMEOUT_SECONDS),
    )


def reasoning_timeout_seconds() -> float:
    return _float_env(
        "OPENAI_REASONING_TIMEOUT",
        _float_env("OPENAI_TIMEOUT", DEFAULT_REASONING_TIMEOUT_SECONDS),
    )


def get_chat_model(
    model: str | None = None,
    *,
    timeout: float | None = None,
    max_retries: int | None = None,
    max_completion_tokens: int | None = None,
    extra_body: dict[str, Any] | None = None,
    model_kwargs: dict[str, Any] | None = None,
) -> ChatOpenAI:
    api_key = os.getenv("OPENAI_API_KEY")
    base_url = os.getenv("OPENAI_BASE_URL") or None
    model_name = model or os.getenv("OPENAI_MODEL") or DEFAULT_MODEL
    request_timeout = timeout or _float_env("OPENAI_TIMEOUT", DEFAULT_TIMEOUT_SECONDS)
    request_retries = (
        max_retries
        if max_retries is not None
        else _int_env("OPENAI_MAX_RETRIES", DEFAULT_MAX_RETRIES)
    )

    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is required in .env for LLM calls.")

    return ChatOpenAI(
        model=model_name,
        api_key=api_key,
        base_url=base_url,
        timeout=request_timeout,
        max_retries=request_retries,
        max_completion_tokens=max_completion_tokens,
        extra_body=extra_body,
        model_kwargs=model_kwargs or {},
    )


def get_structured_chat_model(
    *,
    timeout: float | None = None,
    max_retries: int | None = None,
) -> ChatOpenAI:
    return get_chat_model(
        model=os.getenv("SMALL_MODEL") or DEFAULT_STRUCTURED_MODEL,
        timeout=timeout or structured_timeout_seconds(),
        max_retries=(
            max_retries
            if max_retries is not None
            else _int_env(
                "OPENAI_STRUCTURED_MAX_RETRIES", DEFAULT_STRUCTURED_MAX_RETRIES
            )
        ),
        max_completion_tokens=_int_env(
            "OPENAI_STRUCTURED_MAX_COMPLETION_TOKENS",
            DEFAULT_STRUCTURED_MAX_COMPLETION_TOKENS,
        ),
        extra_body={"enable_thinking": False},
    )


def get_reasoning_chat_model(
    *,
    timeout: float | None = None,
    max_retries: int | None = None,
) -> ChatOpenAI:
    return get_chat_model(
        model=os.getenv("OPENAI_MODEL") or DEFAULT_MODEL,
        timeout=timeout or reasoning_timeout_seconds(),
        max_retries=max_retries,
    )


async def ainvoke_with_timeout(
    runnable: Any,
    messages: Any,
    *,
    timeout: float,
    label: str,
) -> Any:
    try:
        return await asyncio.wait_for(runnable.ainvoke(messages), timeout=timeout)
    except asyncio.TimeoutError as exc:
        raise TimeoutError(f"{label} timed out after {timeout:.1f}s") from exc


def ping_chat_model(kind: str = "reasoning") -> str:
    """Run a minimal real API request and return the response text."""
    if kind == "structured":
        llm = get_structured_chat_model(max_retries=1)
    elif kind == "reasoning":
        llm = get_reasoning_chat_model(max_retries=1)
    else:
        llm = get_chat_model(max_retries=1)
    response = llm.invoke([HumanMessage(content="请只回复 OK，用于连通性测试。")])
    return str(getattr(response, "content", response)).strip()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--kind",
        choices=("structured", "reasoning", "default"),
        default="reasoning",
    )
    args = parser.parse_args()
    print(f"[api] config={describe_llm_config()}")
    print(f"[api] response={ping_chat_model(args.kind)}")
