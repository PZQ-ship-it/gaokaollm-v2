"""Faithful v1-style hybrid RAG baseline for benchmark comparisons.

This module keeps the v1 baseline separate from the v2 Pareto agent.  The
baseline uses v1's retrieval recipe: explicit-intent normalization, relational
filtering, BGE-M3 dense scoring, BCEmbedding reranking, and chong/wen/bao
segmentation.  It deliberately does not emit Pareto opportunities.
"""

from __future__ import annotations

import math
import os
import re
from typing import Any, Protocol

from dotenv import load_dotenv

from app.core import db_pg
from gaokaollm_bench.constrains.llm import ENV_OPENAI_API_KEY, ENV_OPENAI_BASE_URL
from gaokaollm_bench.llm.openai_chat import sanitize_ssl_env
from gaokaollm_bench.sandbox.base_target import BaseTargetAgent


class V1HybridPreflightError(RuntimeError):
    """Raised when strict v1 hybrid dependencies are unavailable."""


ENV_EMBEDDING_MODEL = "EMBEDDING_MODEL"
ENV_RERANKING_MODEL = "RERANKING_MODEL"
ENV_RERANKER_MODEL = "RERANKER_MODEL"


class EmbedderBackend(Protocol):
    def embed_query(self, text: str) -> list[float]: ...

    def embed_documents(self, texts: list[str]) -> list[list[float]]: ...


class RerankerBackend(Protocol):
    def rerank(
        self, query: str, passages: list[str], top_k: int = 10
    ) -> list[tuple[str, float]]: ...


class V1HybridRagBaselineAgent(BaseTargetAgent):
    """Strict v1 hybrid-retrieval baseline over the current DB snapshot."""

    def __init__(
        self,
        *,
        db: Any = None,
        embedder: EmbedderBackend | None = None,
        reranker: RerankerBackend | None = None,
        candidate_pool_size: int = 120,
        per_segment_limit: int = 3,
    ) -> None:
        self.db = db
        self.embedder = embedder
        self.reranker = reranker
        self.candidate_pool_size = candidate_pool_size
        self.per_segment_limit = per_segment_limit
        self.constraints: dict[str, Any] = {}

    async def chat(self, user_input: str) -> tuple[str, dict[str, Any]]:
        normalized = normalize_v1_query(user_input)
        extracted = extract_constraints(normalized["rewritten_query"])
        self.constraints = merge_constraints(self.constraints, extracted)
        missing = missing_required_constraints(self.constraints)
        if missing:
            reply = missing_constraints_reply(missing)
            return reply, v1_hybrid_state(
                constraints=self.constraints,
                normalized_query=normalized,
                query_texts=[],
                filter_constraints={},
                dense_candidates=[],
                reranked_candidates=[],
                missing_constraints=missing,
            )

        embedder = self.embedder or load_default_bge_m3_embedder()
        reranker = self.reranker or load_default_bce_reranker()
        embedding_backend = backend_label(embedder, default="BGE-M3")
        reranker_backend = backend_label(
            reranker,
            default="BCEmbedding/Cross-Encoder",
        )
        query_texts = build_weighted_query_texts(self.constraints, normalized)
        candidates = await fetch_v1_candidate_rows(
            self.constraints,
            db=self.db,
            limit=self.candidate_pool_size,
        )
        dense_candidates = dense_score_candidates(query_texts, candidates, embedder)
        segmented_dense = segment_v1_candidates(self.constraints, dense_candidates)
        reranked_segments = rerank_segments(
            query_text=join_query_texts(query_texts),
            segmented=segmented_dense,
            reranker=reranker,
            per_segment_limit=self.per_segment_limit,
        )
        reranked_candidates = flatten_segments(reranked_segments)
        reply = v1_hybrid_reply(reranked_segments, reranked_candidates)
        return reply, v1_hybrid_state(
            constraints=self.constraints,
            normalized_query=normalized,
            query_texts=query_texts,
            filter_constraints=filter_summary(
                self.constraints,
                embedding_backend=embedding_backend,
                reranker_backend=reranker_backend,
            ),
            dense_candidates=dense_candidates[:15],
            reranked_candidates=reranked_candidates,
            missing_constraints=[],
            segmented_candidates=reranked_segments,
        )


class DefaultBgeM3Embedder:
    """Lazy BGE-M3 wrapper matching the v1 embedding behavior."""

    def __init__(self, model_path: str | None = None) -> None:
        try:
            from FlagEmbedding import BGEM3FlagModel  # type: ignore[import-not-found]
        except ImportError as exc:  # pragma: no cover - depends on local env
            raise V1HybridPreflightError(
                "v1_hybrid_rag requires FlagEmbedding for BGE-M3 dense recall. "
                "Install FlagEmbedding and configure BGE_M3_PATH or V1_BGE_M3_PATH."
            ) from exc
        resolved_path = (
            model_path or os.getenv("V1_BGE_M3_PATH") or os.getenv("BGE_M3_PATH")
        )
        if not resolved_path:
            raise V1HybridPreflightError(
                "v1_hybrid_rag requires a BGE-M3 model path. Set BGE_M3_PATH "
                "or V1_BGE_M3_PATH."
            )
        self.backend = BGEM3FlagModel(resolved_path, use_fp16=True)
        self.model_path = resolved_path
        self.backend_name = "BGE-M3"

    def embed_query(self, text: str) -> list[float]:
        return self.embed_documents([text])[0]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        output = self.backend.encode(
            texts,
            batch_size=12,
            max_length=8192,
            return_dense=True,
            return_sparse=False,
            return_colbert_vecs=False,
        )
        dense = output["dense_vecs"]
        if hasattr(dense, "tolist"):
            return dense.tolist()
        return list(dense)


class DefaultBceReranker:
    """Lazy BCE reranker wrapper matching the v1 second-stage reranking."""

    def __init__(self, model_path: str | None = None) -> None:
        try:
            from BCEmbedding import RerankerModel  # type: ignore[import-not-found]
        except ImportError as exc:  # pragma: no cover - depends on local env
            raise V1HybridPreflightError(
                "v1_hybrid_rag requires BCEmbedding for second-stage reranking. "
                "Install BCEmbedding and configure BCE_V1_PATH or "
                "V1_BCE_RERANKER_PATH."
            ) from exc
        resolved_path = (
            model_path or os.getenv("V1_BCE_RERANKER_PATH") or os.getenv("BCE_V1_PATH")
        )
        if not resolved_path:
            raise V1HybridPreflightError(
                "v1_hybrid_rag requires a BCE reranker path. Set BCE_V1_PATH "
                "or V1_BCE_RERANKER_PATH."
            )
        self.backend = RerankerModel(model_name_or_path=resolved_path, use_fp16=True)
        self.model_path = resolved_path
        self.backend_name = "BCEmbedding/Cross-Encoder"

    def rerank(
        self, query: str, passages: list[str], top_k: int = 10
    ) -> list[tuple[str, float]]:
        result = self.backend.rerank(query, passages)
        passages_out = result["rerank_passages"]
        scores_out = result["rerank_scores"]
        return list(zip(passages_out, scores_out, strict=False))[:top_k]


class OpenAICompatibleEmbeddingBackend:
    """OpenAI-compatible remote embedding backend for v1-style dense recall."""

    def __init__(
        self,
        *,
        model: str | None = None,
        api_key: str | None = None,
        base_url: str | None = None,
        timeout: float = 120.0,
    ) -> None:
        load_dotenv()
        sanitize_ssl_env()
        self.model = model or os.getenv(ENV_EMBEDDING_MODEL)
        self.api_key = api_key or os.getenv(ENV_OPENAI_API_KEY)
        self.base_url = base_url or os.getenv(ENV_OPENAI_BASE_URL) or None
        self.timeout = timeout
        if not self.model:
            raise V1HybridPreflightError(
                f"{ENV_EMBEDDING_MODEL} is required for remote dense recall."
            )
        if not self.api_key:
            raise V1HybridPreflightError(
                f"{ENV_OPENAI_API_KEY} is required for remote dense recall."
            )
        self.backend_name = f"OpenAI-compatible embedding ({self.model})"

    def embed_query(self, text: str) -> list[float]:
        return self.embed_documents([text])[0]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        from openai import OpenAI

        client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
            timeout=self.timeout,
            max_retries=1,
        )
        response = client.embeddings.create(model=self.model, input=texts)
        return [list(item.embedding) for item in response.data]


class OpenAICompatibleRerankerBackend:
    """OpenAI-compatible rerank backend using SiliconFlow's /rerank endpoint."""

    def __init__(
        self,
        *,
        model: str | None = None,
        api_key: str | None = None,
        base_url: str | None = None,
        timeout: float = 120.0,
    ) -> None:
        load_dotenv()
        sanitize_ssl_env()
        self.model = (
            model or os.getenv(ENV_RERANKING_MODEL) or os.getenv(ENV_RERANKER_MODEL)
        )
        self.api_key = api_key or os.getenv(ENV_OPENAI_API_KEY)
        self.base_url = (base_url or os.getenv(ENV_OPENAI_BASE_URL) or "").rstrip("/")
        self.timeout = timeout
        if not self.model:
            raise V1HybridPreflightError(
                f"{ENV_RERANKING_MODEL} is required for remote second-stage rerank."
            )
        if not self.api_key:
            raise V1HybridPreflightError(
                f"{ENV_OPENAI_API_KEY} is required for remote second-stage rerank."
            )
        if not self.base_url:
            raise V1HybridPreflightError(
                f"{ENV_OPENAI_BASE_URL} is required for remote second-stage rerank."
            )
        self.backend_name = f"OpenAI-compatible rerank ({self.model})"

    def rerank(
        self, query: str, passages: list[str], top_k: int = 10
    ) -> list[tuple[str, float]]:
        import httpx

        if not passages:
            return []
        payload = {
            "model": self.model,
            "query": query,
            "documents": passages,
            "top_n": min(top_k, len(passages)),
            "return_documents": True,
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        url = f"{self.base_url}/rerank"
        try:
            response = httpx.post(
                url,
                json=payload,
                headers=headers,
                timeout=self.timeout,
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise V1HybridPreflightError(
                "remote rerank request failed; verify RERANKING_MODEL and "
                f"{ENV_OPENAI_BASE_URL}."
            ) from exc

        data = response.json()
        results = data.get("results") or []
        ranked: list[tuple[str, float]] = []
        for item in results:
            index = item.get("index")
            document = item.get("document")
            if isinstance(document, dict):
                passage = str(document.get("text") or document.get("content") or "")
            elif isinstance(document, str):
                passage = document
            elif isinstance(index, int) and 0 <= index < len(passages):
                passage = passages[index]
            else:
                continue
            score = item.get("relevance_score", item.get("score", 0.0))
            try:
                ranked.append((passage, float(score)))
            except (TypeError, ValueError):
                ranked.append((passage, 0.0))

        if not ranked:
            raise V1HybridPreflightError(
                "remote rerank response did not contain usable ranked passages."
            )
        return ranked[:top_k]


def load_default_bge_m3_embedder() -> EmbedderBackend:
    load_dotenv()
    if os.getenv(ENV_EMBEDDING_MODEL):
        return OpenAICompatibleEmbeddingBackend()
    return DefaultBgeM3Embedder()


def load_default_bce_reranker() -> RerankerBackend:
    load_dotenv()
    if os.getenv(ENV_RERANKING_MODEL) or os.getenv(ENV_RERANKER_MODEL):
        return OpenAICompatibleRerankerBackend()
    return DefaultBceReranker()


def backend_label(backend: Any, *, default: str) -> str:
    label = getattr(backend, "backend_name", None)
    if isinstance(label, str) and label:
        return label
    return default


def normalize_v1_query(text: str) -> dict[str, Any]:
    compact = re.sub(r"\s+", " ", text).strip()
    for hidden_name in (
        "implicit_flexibilities",
        "volunteer_set",
        "axis_flexibilities",
    ):
        compact = compact.replace(hidden_name, "")
    compact = re.sub(r"\s+", " ", compact).strip()
    return {
        "rewritten_query": compact,
        "preference_summary": preference_summary(compact),
        "source": "deterministic_v1_query_rewrite",
    }


def preference_summary(text: str) -> list[str]:
    summary: list[str] = []
    axis_tokens = {
        "major_preference": (
            "major",
            "computer",
            "clinical",
            "law",
            "专业",
            "想读",
            "计算机",
            "临床",
            "法学",
            "璁＄畻鏈?",
            "涓村簥",
            "娉曞",
        ),
        "region_preference": (
            "region",
            "city",
            "province",
            "zhejiang",
            "hangzhou",
            "浙江",
            "杭州",
            "娴欐睙",
            "鏉窞",
        ),
        "risk_preference": (
            "stable",
            "conservative",
            "risk",
            "稳",
            "保守",
            "冲",
            "绋?",
            "淇濆畧",
            "鍐?",
        ),
    }
    lowered = text.lower()
    for label, tokens in axis_tokens.items():
        if any(token.lower() in lowered for token in tokens):
            summary.append(label)
    return summary


def extract_constraints(text: str) -> dict[str, Any]:
    extracted: dict[str, Any] = {}
    score_match = re.search(r"(\d{3})", text)
    if score_match:
        extracted["score"] = int(score_match.group(1))

    province_aliases = {
        "浙江": "浙江",
        "zhejiang": "浙江",
        "娴欐睙": "娴欐睙",
        "北京": "北京",
        "beijing": "北京",
        "鍖椾含": "鍖椾含",
    }
    lowered = text.lower()
    for alias, value in province_aliases.items():
        if alias.lower() in lowered:
            extracted["province"] = value
            break

    city_aliases = {
        "杭州": "杭州",
        "hangzhou": "杭州",
        "鏉窞": "鏉窞",
        "宁波": "宁波",
        "ningbo": "宁波",
        "瀹佹尝": "瀹佹尝",
    }
    for alias, value in city_aliases.items():
        if alias.lower() in lowered:
            extracted["city"] = value
            break

    major_aliases = {
        "computer": "Computer Science",
        "计算机": "计算机",
        "璁＄畻鏈?": "璁＄畻鏈?",
        "clinical": "Clinical Medicine",
        "临床": "临床医学",
        "涓村簥": "涓村簥鍖诲",
        "law": "Law",
        "法学": "法学",
        "娉曞": "娉曞",
    }
    for alias, value in major_aliases.items():
        if alias.lower() in lowered:
            extracted["major"] = value
            break

    subjects = extract_subjects(text)
    if subjects:
        extracted["selected_subjects"] = subjects
    return extracted


def extract_subjects(text: str) -> list[str]:
    aliases = {
        "physics": "物理",
        "物理": "物理",
        "鐗╃悊": "鐗╃悊",
        "chemistry": "化学",
        "化学": "化学",
        "鍖栧": "鍖栧",
        "biology": "生物",
        "生物": "生物",
        "鐢熺墿": "鐢熺墿",
        "history": "历史",
        "历史": "历史",
        "鍘嗗彶": "鍘嗗彶",
        "geography": "地理",
        "地理": "地理",
        "鍦扮悊": "鍦扮悊",
        "politics": "政治",
        "政治": "政治",
        "鏀挎不": "鏀挎不",
    }
    compact = re.sub(r"\s+", "", text).lower()
    subjects: list[str] = []
    for alias, subject in aliases.items():
        if alias.lower() in compact and subject not in subjects:
            subjects.append(subject)
    return subjects[:3]


def merge_constraints(
    current: dict[str, Any],
    extracted: dict[str, Any],
) -> dict[str, Any]:
    merged = {
        "score": None,
        "province": "浙江",
        "city": None,
        "major": None,
        "selected_subjects": None,
        **(current or {}),
    }
    for key in ("score", "province", "city", "major", "selected_subjects"):
        if key in extracted and extracted[key] not in ("", []):
            merged[key] = extracted[key]
    return merged


def missing_required_constraints(constraints: dict[str, Any]) -> list[str]:
    missing: list[str] = []
    if not constraints.get("score"):
        missing.append("score")
    if not constraints.get("selected_subjects"):
        missing.append("selected_subjects")
    return missing


def missing_constraints_reply(missing: list[str]) -> str:
    labels = {
        "score": "高考分数",
        "selected_subjects": "3门选考科目",
    }
    return "我还需要补充：" + "、".join(labels[item] for item in missing) + "。"


def build_weighted_query_texts(
    constraints: dict[str, Any],
    normalized_query: dict[str, Any],
) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    major = constraints.get("major")
    if major:
        items.append({"text": str(major), "weight": 4.0, "axis": "major"})
    city = constraints.get("city")
    if city:
        items.append({"text": str(city), "weight": 2.0, "axis": "city"})
    province = constraints.get("province")
    if province:
        items.append({"text": str(province), "weight": 1.5, "axis": "province"})
    rewritten = str(normalized_query.get("rewritten_query") or "").strip()
    if rewritten:
        items.append({"text": rewritten, "weight": 1.0, "axis": "full_query"})
    return items or [{"text": "大学 专业", "weight": 1.0, "axis": "fallback"}]


def join_query_texts(query_texts: list[dict[str, Any]]) -> str:
    return " ".join(str(item["text"]) for item in query_texts)


async def fetch_v1_candidate_rows(
    constraints: dict[str, Any],
    *,
    db: Any = None,
    limit: int = 120,
) -> list[dict[str, Any]]:
    score = int(constraints["score"])
    where = [
        "a.min_score IS NOT NULL",
        "a.min_score >= %s",
        "a.min_score <= %s",
    ]
    params: list[Any] = [score - 25, score + 15]
    selected_subjects = constraints.get("selected_subjects")
    if selected_subjects:
        where.append(
            """
            (
                COALESCE(sr.requirement_type, 'unknown') = 'none'
                OR COALESCE(cardinality(sr.normalized_subjects), 0) = 0
                OR (
                    sr.requirement_type = 'all_required'
                    AND sr.normalized_subjects <@ %s::text[]
                )
                OR (
                    sr.requirement_type = 'any_required'
                    AND sr.normalized_subjects && %s::text[]
                )
            )
            """
        )
        params.extend([selected_subjects, selected_subjects])

    params.append(limit)
    query = f"""
    SELECT
        a.id AS admission_score_id,
        a.year,
        a.school_id,
        s.name AS school_name,
        s.province AS school_province,
        s.city AS school_city,
        s.is_985,
        s.is_211,
        s.is_double_first_class,
        s.education_level,
        s.ranking,
        a.major_id,
        a.major_name_raw AS major_name,
        a.subject_requirement,
        COALESCE(sr.requirement_type, 'unknown') AS requirement_type,
        a.min_score,
        a.min_rank,
        plan.min_tuition AS tuition,
        CASE
            WHEN s.is_985 THEN 4
            WHEN s.is_211 OR s.is_double_first_class THEN 3
            WHEN s.education_level = '本科' OR s.education_level = '鏈' THEN 2
            ELSE 1
        END AS tier
    FROM admission_scores a
    JOIN schools s ON s.id = a.school_id
    LEFT JOIN subject_requirements sr ON sr.raw_requirement = a.subject_requirement
    LEFT JOIN LATERAL (
        SELECT min(p.tuition) AS min_tuition
        FROM admission_plans p
        WHERE p.school_id = a.school_id
          AND p.year = a.year
          AND (
              p.major_id = a.major_id
              OR p.major_code = a.major_code
              OR p.major_name_raw = a.major_name_raw
          )
    ) plan ON true
    WHERE {" AND ".join(where)}
    ORDER BY
        a.year DESC,
        abs(a.min_score - %s) ASC,
        s.ranking ASC NULLS LAST,
        s.name ASC,
        a.major_name_raw ASC
    LIMIT %s
    """
    params.insert(-1, score)
    return await fetch_rows(db, query, params)


async def fetch_rows(db: Any, query: str, params: list[Any]) -> list[dict[str, Any]]:
    if db is None:
        return await db_pg.fetch_query(query, *params)
    if hasattr(db, "fetch_query"):
        return await db.fetch_query(query, *params)
    return await db(query, *params)


def dense_score_candidates(
    query_texts: list[dict[str, Any]],
    rows: list[dict[str, Any]],
    embedder: EmbedderBackend,
) -> list[dict[str, Any]]:
    if not rows:
        return []
    query_vectors = [
        (embedder.embed_query(str(item["text"])), float(item["weight"]))
        for item in query_texts
    ]
    passages = [row_to_v1_passage(row) for row in rows]
    doc_vectors = embedder.embed_documents(passages)
    scored: list[dict[str, Any]] = []
    for row, passage, doc_vector in zip(rows, passages, doc_vectors, strict=False):
        score = sum(
            cosine_similarity(query_vector, doc_vector) * weight
            for query_vector, weight in query_vectors
        )
        item = dict(row)
        item["v1_document"] = passage
        item["dense_similarity"] = float(score)
        scored.append(item)
    scored.sort(key=lambda row: float(row.get("dense_similarity") or 0), reverse=True)
    return scored


def row_to_v1_passage(row: dict[str, Any]) -> str:
    return (
        f"学校:{row.get('school_name')}; "
        f"省份:{row.get('school_province')}; "
        f"城市:{row.get('school_city')}; "
        f"专业:{row.get('major_name')}; "
        f"最低分:{row.get('min_score')}; "
        f"最低位次:{row.get('min_rank')}; "
        f"选科:{row.get('subject_requirement')}; "
        f"批次:{row.get('admission_batch') or ''}; "
        f"层次:{row.get('education_level') or ''}; "
        f"排名:{row.get('ranking') or ''}"
    )


def cosine_similarity(vec1: list[float], vec2: list[float]) -> float:
    dot = sum(a * b for a, b in zip(vec1, vec2, strict=False))
    mag1 = math.sqrt(sum(a * a for a in vec1))
    mag2 = math.sqrt(sum(b * b for b in vec2))
    if mag1 == 0 or mag2 == 0:
        return 0.0
    return dot / (mag1 * mag2)


def segment_v1_candidates(
    constraints: dict[str, Any],
    rows: list[dict[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    score = int(constraints.get("score") or 0)
    segmented: dict[str, list[dict[str, Any]]] = {
        "chong": [],
        "wen": [],
        "bao": [],
    }
    for row in rows:
        min_score = row.get("min_score")
        if min_score is None:
            continue
        delta = int(float(min_score)) - score
        item = dict(row)
        item["score_delta"] = delta
        if 0 < delta <= 15:
            segmented["chong"].append(item)
        elif -5 <= delta <= 0:
            segmented["wen"].append(item)
        elif -25 <= delta < -5:
            segmented["bao"].append(item)
    return segmented


def rerank_segments(
    *,
    query_text: str,
    segmented: dict[str, list[dict[str, Any]]],
    reranker: RerankerBackend,
    per_segment_limit: int,
) -> dict[str, list[dict[str, Any]]]:
    output: dict[str, list[dict[str, Any]]] = {"chong": [], "wen": [], "bao": []}
    for band, rows in segmented.items():
        top_dense = rows[:30]
        passages = [
            str(row.get("v1_document") or row_to_v1_passage(row)) for row in top_dense
        ]
        if not passages:
            continue
        row_by_passage = {
            passage: row for passage, row in zip(passages, top_dense, strict=False)
        }
        ranked = reranker.rerank(query_text, passages, top_k=per_segment_limit)
        for passage, score in ranked:
            source = row_by_passage.get(passage)
            if source is None:
                continue
            item = dict(source)
            item["rerank_score"] = float(score)
            item["risk_level"] = band
            output[band].append(item)
    return output


def flatten_segments(
    segmented: dict[str, list[dict[str, Any]]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for band in ("chong", "wen", "bao"):
        rows.extend(segmented.get(band) or [])
    return rows


def v1_hybrid_reply(
    segmented: dict[str, list[dict[str, Any]]],
    rows: list[dict[str, Any]],
) -> str:
    if not rows:
        return "按 v1 混合检索基线，当前没有找到合适的冲稳保候选。"

    labels = {
        "chong": "可冲刺",
        "wen": "较稳妥",
        "bao": "可保底",
    }
    lines = ["按 v1 混合检索基线，我先给出软约束召回和二阶重排后的冲稳保候选："]
    for band in ("chong", "wen", "bao"):
        candidates = segmented.get(band) or []
        if not candidates:
            continue
        lines.append(f"{labels[band]}：")
        for row in candidates[:2]:
            lines.append(
                f"- {row.get('school_name')}｜{row.get('school_province')}｜"
                f"{row.get('major_name')}｜最低分 {row.get('min_score')}｜"
                f"v1_rerank={float(row.get('rerank_score') or 0):.3f}"
            )
    return "\n".join(lines)


def v1_hybrid_state(
    *,
    constraints: dict[str, Any],
    normalized_query: dict[str, Any],
    query_texts: list[dict[str, Any]],
    filter_constraints: dict[str, Any],
    dense_candidates: list[dict[str, Any]],
    reranked_candidates: list[dict[str, Any]],
    missing_constraints: list[str],
    segmented_candidates: dict[str, list[dict[str, Any]]] | None = None,
) -> dict[str, Any]:
    return {
        "target": "v1_hybrid_rag",
        "constraints": dict(constraints),
        "normalized_query": dict(normalized_query),
        "query_texts": list(query_texts),
        "filter_constraints": dict(filter_constraints),
        "dense_retrieval_candidates": list(dense_candidates),
        "second_stage_reranked_candidates": list(reranked_candidates),
        "risk_segments": segmented_candidates or {"chong": [], "wen": [], "bao": []},
        "baseline_results": list(reranked_candidates[:3]),
        "pareto_opportunities": empty_opportunities(),
        "score_waste": score_waste(constraints, reranked_candidates),
        "missing_constraints": list(missing_constraints),
        "recommended_schools": recommended_schools(reranked_candidates),
    }


def filter_summary(
    constraints: dict[str, Any],
    *,
    embedding_backend: str = "BGE-M3",
    reranker_backend: str = "BCEmbedding/Cross-Encoder",
) -> dict[str, Any]:
    score = constraints.get("score")
    return {
        "score_window": [int(score) - 25, int(score) + 15] if score else None,
        "selected_subjects": constraints.get("selected_subjects"),
        "candidate_source": "current_postgresql_snapshot",
        "embedding_backend": embedding_backend,
        "reranker_backend": reranker_backend,
    }


def empty_opportunities() -> dict[str, list[Any]]:
    return {
        "geo_relax": [],
        "city_relax": [],
        "major_relax": [],
        "strength_relax": [],
        "major_quality_relax": [],
        "tuition_value_relax": [],
        "employment_outcome_relax": [],
        "region_tree_relax": [],
        "major_geo_relax": [],
        "risk_band_relax": [],
    }


def recommended_schools(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    schools: list[dict[str, Any]] = []
    seen: set[str] = set()
    for row in rows:
        name = str(row.get("school_name") or "")
        if not name or name in seen:
            continue
        seen.add(name)
        item = {
            "school": name,
            "province": row.get("school_province"),
            "city": row.get("school_city"),
            "major": row.get("major_name"),
            "min_score": row.get("min_score"),
            "min_rank": row.get("min_rank"),
            "tier": row.get("tier"),
            "risk_level": row.get("risk_level"),
        }
        schools.append(item)
    return schools


def score_waste(
    constraints: dict[str, Any],
    rows: list[dict[str, Any]],
) -> int:
    if not rows or constraints.get("score") is None:
        return 0
    try:
        return int(constraints["score"]) - int(float(rows[0]["min_score"]))
    except (KeyError, TypeError, ValueError):
        return 0
