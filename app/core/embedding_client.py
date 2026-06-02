from __future__ import annotations

import os
from math import sqrt
import re
from typing import Protocol

from dotenv import load_dotenv


load_dotenv()


ENV_EMBEDDING_MODEL = "EMBEDDING_MODEL"
ENV_OPENAI_API_KEY = "OPENAI_API_KEY"
ENV_OPENAI_BASE_URL = "OPENAI_BASE_URL"
ENV_EMBEDDING_DIMENSIONS = "EMBEDDING_DIMENSIONS"
ENV_KNOWLEDGE_EMBEDDING_DIM = "KNOWLEDGE_EMBEDDING_DIM"
DEFAULT_KNOWLEDGE_EMBEDDING_DIM = 1536

_SPACE_PATTERN = re.compile(r"\s+")


class EmbeddingClient(Protocol):
    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Return one vector per text."""


def repair_ssl_env() -> list[str]:
    """Remove broken SSL env vars before httpx/OpenAI creates its SSL context."""

    changed: list[str] = []
    for env_name in ("SSL_CERT_FILE", "REQUESTS_CA_BUNDLE"):
        value = os.getenv(env_name)
        if value and not os.path.exists(value):
            os.environ.pop(env_name, None)
            changed.append(env_name)

    if not os.getenv("SSL_CERT_FILE"):
        conda_prefix = os.getenv("CONDA_PREFIX")
        if conda_prefix:
            conda_cert = os.path.join(conda_prefix, "Library", "ssl", "cacert.pem")
            if os.path.exists(conda_cert):
                os.environ["SSL_CERT_FILE"] = conda_cert
                changed.append("SSL_CERT_FILE")
    return changed


def normalize_text(text: str) -> str:
    if not text:
        return ""
    cleaned = str(text).replace("\u3000", " ").strip(" \t\r\n。.,，;；")
    return _SPACE_PATTERN.sub(" ", cleaned)


def cosine_similarity(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = sqrt(sum(x * x for x in a))
    norm_b = sqrt(sum(y * y for y in b))
    if not norm_a or not norm_b:
        return 0.0
    return dot / (norm_a * norm_b)


def configured_embedding_dimensions() -> int | None:
    raw = os.getenv(ENV_EMBEDDING_DIMENSIONS)
    if not raw:
        return None
    try:
        value = int(raw)
    except ValueError as exc:
        raise RuntimeError(f"{ENV_EMBEDDING_DIMENSIONS} must be an integer.") from exc
    if value <= 0:
        raise RuntimeError(f"{ENV_EMBEDDING_DIMENSIONS} must be positive.")
    return value


def expected_knowledge_embedding_dim() -> int:
    raw = os.getenv(ENV_KNOWLEDGE_EMBEDDING_DIM)
    if not raw:
        return DEFAULT_KNOWLEDGE_EMBEDDING_DIM
    try:
        value = int(raw)
    except ValueError as exc:
        raise RuntimeError(
            f"{ENV_KNOWLEDGE_EMBEDDING_DIM} must be an integer."
        ) from exc
    if value <= 0:
        raise RuntimeError(f"{ENV_KNOWLEDGE_EMBEDDING_DIM} must be positive.")
    return value


def ensure_embedding_dimension(
    vector: list[float],
    *,
    expected_dim: int | None = None,
    label: str = "embedding",
) -> None:
    expected = expected_dim or expected_knowledge_embedding_dim()
    actual = len(vector)
    if actual != expected:
        raise RuntimeError(
            f"{label} dimension mismatch: got {actual}, expected {expected}. "
            f"The PostgreSQL knowledge_documents.embedding column is vector({expected})."
        )


def vector_to_pg_literal(vector: list[float]) -> str:
    if not vector:
        raise RuntimeError("Embedding vector is empty.")
    return "[" + ",".join(f"{float(value):.9g}" for value in vector) + "]"


class OpenAIEmbeddingClient:
    """OpenAI-compatible embedding client using project .env configuration."""

    def __init__(
        self,
        *,
        model: str | None = None,
        api_key: str | None = None,
        base_url: str | None = None,
        dimensions: int | None = None,
    ) -> None:
        self.model = model or os.getenv(ENV_EMBEDDING_MODEL)
        self.api_key = api_key or os.getenv(ENV_OPENAI_API_KEY)
        self.base_url = base_url or os.getenv(ENV_OPENAI_BASE_URL) or None
        self.dimensions = (
            dimensions if dimensions is not None else configured_embedding_dimensions()
        )
        if not self.model:
            raise RuntimeError(
                f"{ENV_EMBEDDING_MODEL} is required for full-context semantic ranking."
            )
        if not self.api_key:
            raise RuntimeError(
                f"{ENV_OPENAI_API_KEY} is required for full-context semantic ranking."
            )

    async def embed(self, texts: list[str]) -> list[list[float]]:
        from openai import AsyncOpenAI

        inputs = [normalize_text(text) for text in texts]
        if not inputs:
            return []
        repair_ssl_env()
        client = AsyncOpenAI(api_key=self.api_key, base_url=self.base_url)
        kwargs = {"model": self.model, "input": inputs}
        if self.dimensions is not None:
            kwargs["dimensions"] = self.dimensions
        response = await client.embeddings.create(**kwargs)
        return [list(item.embedding) for item in response.data]


async def embed_texts(texts: list[str]) -> list[list[float]]:
    client = OpenAIEmbeddingClient()
    return await client.embed(texts)


async def embed_one(text: str) -> list[float]:
    vectors = await embed_texts([text])
    if not vectors:
        raise RuntimeError("Embedding API returned no vector.")
    return vectors[0]
