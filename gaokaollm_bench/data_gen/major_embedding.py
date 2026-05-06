"""Embedding-assisted major-cluster suggestions."""

from __future__ import annotations

import os
from dataclasses import dataclass
from math import sqrt
import re
from typing import Any, Protocol

from dotenv import load_dotenv

from gaokaollm_bench.data_gen.major_tree import load_major_tree


load_dotenv()


_PAREN_PATTERN = re.compile(r"[（(][^（）()]*[）)]")
_LANGUAGE_HINTS = (
    "语言",
    "外语",
    "语文",
    "翻译",
    "英语",
    "日语",
    "俄语",
    "法语",
    "德语",
    "西班牙语",
    "葡萄牙语",
    "阿拉伯语",
    "朝鲜语",
    "韩语",
    "泰语",
    "越南语",
    "印地语",
    "乌尔都语",
    "马来语",
    "波斯语",
    "希腊语",
    "捷克语",
    "匈牙利语",
    "乌克兰语",
    "塞尔维亚语",
    "希伯来语",
    "白俄罗斯语",
    "芬兰语",
    "保加利亚语",
    "斯瓦希里语",
    "土耳其语",
    "孟加拉语",
    "尼泊尔语",
    "菲律宾语",
    "柬埔寨语",
    "拉脱维亚语",
    "语",
)


def _normalize_text(text: str) -> str:
    if not text:
        return ""
    cleaned = _PAREN_PATTERN.sub("", text)
    cleaned = cleaned.replace("校区", "")
    cleaned = cleaned.replace("　", " ")
    cleaned = cleaned.strip(" 。.，,;；")
    return " ".join(cleaned.split())


def _is_language_like(text: str) -> bool:
    return any(hint in text for hint in _LANGUAGE_HINTS)


class EmbeddingClient(Protocol):
    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Return one vector per text."""


@dataclass(frozen=True)
class ClusterSuggestion:
    major_name: str
    action: str
    target_node_id: str
    target_label: str
    parent_node_id: str | None
    similarity: float
    reasoning: str


class OpenAIEmbeddingClient:
    """Small OpenAI-compatible embedding client using .env configuration."""

    def __init__(
        self,
        *,
        model: str | None = None,
        api_key: str | None = None,
        base_url: str | None = None,
    ) -> None:
        self.model = model or os.getenv("EMBEDDING_MODEL")
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.base_url = base_url or os.getenv("OPENAI_BASE_URL") or None
        if not self.model:
            raise RuntimeError("EMBEDDING_MODEL is required in .env for embedding suggestions.")
        if not self.api_key:
            raise RuntimeError("OPENAI_API_KEY is required in .env for embedding suggestions.")

    async def embed(self, texts: list[str]) -> list[list[float]]:
        from openai import AsyncOpenAI

        client = AsyncOpenAI(api_key=self.api_key, base_url=self.base_url)
        response = await client.embeddings.create(model=self.model, input=texts)
        return [item.embedding for item in response.data]


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = sqrt(sum(x * x for x in a))
    norm_b = sqrt(sum(y * y for y in b))
    if not norm_a or not norm_b:
        return 0.0
    return dot / (norm_a * norm_b)


def _leaf_nodes(tree: dict[str, Any]) -> list[dict[str, Any]]:
    nodes = tree.get("nodes", {})
    parent_ids = {node.get("parent") for node in nodes.values() if node.get("parent")}
    return [node for node_id, node in nodes.items() if node_id not in parent_ids]


def _node_profile(node: dict[str, Any], *, nodes: dict[str, Any]) -> str:
    node_id = str(node.get("id") or "")
    label = _normalize_text(str(node.get("label") or node.get("id") or ""))
    include_terms = [
        _normalize_text(str(term))
        for term in node.get("include_keywords", [])
        if term
    ]
    observed_terms = [
        _normalize_text(str(term))
        for term in node.get("observed_names", [])
        if term
    ]

    if node_id == "education_psychology":
        observed_terms = [term for term in observed_terms if term and not _is_language_like(term)]

    if node_id == "languages_literature":
        source = nodes.get("education_psychology") or {}
        source_terms = [
            _normalize_text(str(term))
            for term in source.get("observed_names", [])
            if term
        ]
        observed_terms.extend(term for term in source_terms if term and _is_language_like(term))

    weighted_terms = [
        label,
        label,
        *include_terms,
        *include_terms,
        *include_terms,
        *observed_terms[:20],
    ]
    return "; ".join(dict.fromkeys(term for term in weighted_terms if term))


def _classify_suggestion(
    major_name: str,
    node: dict[str, Any],
    similarity: float,
    *,
    attach_threshold: float,
    new_sibling_threshold: float,
) -> ClusterSuggestion:
    parent_id = node.get("parent")
    if similarity >= attach_threshold:
        action = "attach_to_leaf"
        reasoning = "semantic similarity is high enough to add the observed name to this leaf"
    elif similarity >= new_sibling_threshold:
        action = "suggest_new_sibling_leaf"
        reasoning = "semantic similarity points to this neighborhood, but a new sibling leaf is safer"
    else:
        action = "manual_review"
        reasoning = "semantic similarity is too weak for automatic placement"

    return ClusterSuggestion(
        major_name=major_name,
        action=action,
        target_node_id=str(node["id"]),
        target_label=str(node.get("label") or node["id"]),
        parent_node_id=str(parent_id) if parent_id else None,
        similarity=similarity,
        reasoning=reasoning,
    )


def _nearest_suggestions(
    major_names: list[str],
    leaves: list[dict[str, Any]],
    major_vectors: list[list[float]],
    profile_vectors: list[list[float]],
    *,
    attach_threshold: float,
    new_sibling_threshold: float,
) -> list[ClusterSuggestion]:
    suggestions: list[ClusterSuggestion] = []
    for major_name, major_vector in zip(major_names, major_vectors):
        scored = [
            (_cosine(major_vector, vector), node)
            for vector, node in zip(profile_vectors, leaves)
        ]
        similarity, node = max(scored, key=lambda item: item[0])
        suggestions.append(
            _classify_suggestion(
                major_name,
                node,
                similarity,
                attach_threshold=attach_threshold,
                new_sibling_threshold=new_sibling_threshold,
            )
        )
    return suggestions


async def suggest_major_cluster_by_embedding(
    major_name: str,
    embedding_client: EmbeddingClient,
    *,
    tree: dict[str, Any] | None = None,
    tree_path: str | None = None,
    attach_threshold: float = 0.82,
    new_sibling_threshold: float = 0.68,
) -> ClusterSuggestion:
    """Suggest how to place an unknown major using semantic similarity."""

    suggestions = await suggest_major_clusters_by_embedding(
        [major_name],
        embedding_client,
        tree=tree,
        tree_path=tree_path,
        attach_threshold=attach_threshold,
        new_sibling_threshold=new_sibling_threshold,
    )
    return suggestions[0]


async def suggest_major_clusters_by_embedding(
    major_names: list[str],
    embedding_client: EmbeddingClient,
    *,
    tree: dict[str, Any] | None = None,
    tree_path: str | None = None,
    attach_threshold: float = 0.82,
    new_sibling_threshold: float = 0.68,
    major_batch_size: int | None = None,
) -> list[ClusterSuggestion]:
    """Suggest placements for many majors with one shared leaf-profile embedding pass."""

    if attach_threshold <= new_sibling_threshold:
        raise ValueError("attach_threshold must be greater than new_sibling_threshold")
    if major_batch_size is not None and major_batch_size < 1:
        raise ValueError("major_batch_size must be at least 1 when provided")
    if not major_names:
        return []

    data = tree or load_major_tree(tree_path)
    leaves = _leaf_nodes(data)
    if not leaves:
        raise ValueError("major tree must contain at least one leaf node")

    nodes = data.get("nodes") or data.get("clusters") or {}
    profiles = [_node_profile(node, nodes=nodes) for node in leaves]
    normalized_major_names = [_normalize_text(name) for name in major_names]
    if major_batch_size is None:
        vectors = await embedding_client.embed([*normalized_major_names, *profiles])
        major_vectors = vectors[: len(normalized_major_names)]
        profile_vectors = vectors[len(major_names) :]
        return _nearest_suggestions(
            major_names,
            leaves,
            major_vectors,
            profile_vectors,
            attach_threshold=attach_threshold,
            new_sibling_threshold=new_sibling_threshold,
        )

    profile_vectors = await embedding_client.embed(profiles)
    suggestions: list[ClusterSuggestion] = []
    for start in range(0, len(major_names), major_batch_size):
        chunk = major_names[start : start + major_batch_size]
        normalized_chunk = [_normalize_text(name) for name in chunk]
        major_vectors = await embedding_client.embed(normalized_chunk)
        suggestions.extend(
            _nearest_suggestions(
                chunk,
                leaves,
                major_vectors,
                profile_vectors,
                attach_threshold=attach_threshold,
                new_sibling_threshold=new_sibling_threshold,
            )
        )
    return suggestions
