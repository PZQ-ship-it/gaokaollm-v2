"""Provider lane configuration helpers for distributed benchmark runs."""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any


DEFAULT_CONFIG_PATH = Path("app/evaluation/config/llm_lanes.local.json")
DEFAULT_RUNTIME_ROOT = Path(".runtime/distributed_unified_benchmark")


class LaneConfigError(ValueError):
    """Raised when a provider lane configuration is missing required fields."""


@dataclass(frozen=True)
class ProviderLane:
    lane_id: str
    provider: str
    api_key: str
    base_url: str
    models: tuple[str, ...]
    small_model: str
    embedding_model: str
    rerank_model: str
    rerank_base_url: str | None = None
    rerank_endpoint: str = "/rerank"

    @property
    def key_fingerprint(self) -> str:
        return hashlib.sha256(self.api_key.encode("utf-8")).hexdigest()[:12]

    @property
    def masked_key(self) -> str:
        if len(self.api_key) <= 10:
            return "***"
        return f"{self.api_key[:4]}...{self.api_key[-4:]}"

    def env(self) -> dict[str, str]:
        env = dict(os.environ)
        env.update(
            {
                "OPENAI_API_KEY": self.api_key,
                "OPENAI_BASE_URL": self.base_url,
                "SMALL_MODEL": self.small_model,
                "EMBEDDING_MODEL": self.embedding_model,
                "RERANKING_MODEL": self.rerank_model,
                "RERANKER_MODEL": self.rerank_model,
                "RERANKING_BASE_URL": self.rerank_base_url or self.base_url,
                "RERANKING_ENDPOINT": self.rerank_endpoint,
            }
        )
        return env

    def safe_summary(self) -> dict[str, Any]:
        return {
            "lane_id": self.lane_id,
            "provider": self.provider,
            "base_url": self.base_url,
            "key": self.masked_key,
            "key_fingerprint": self.key_fingerprint,
            "models": list(self.models),
            "small_model": self.small_model,
            "embedding_model": self.embedding_model,
            "rerank_model": self.rerank_model,
            "rerank_base_url": self.rerank_base_url or self.base_url,
            "rerank_endpoint": self.rerank_endpoint,
        }


def read_nonempty_lines(path: str | Path) -> list[str]:
    raw = Path(path).read_text(encoding="utf-8-sig")
    return [
        line.strip().lstrip("\ufeff")
        for line in raw.splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]


def _require_count(
    values: list[str],
    *,
    path: str,
    minimum: int,
    exact: int | None = None,
) -> list[str]:
    if len(values) < minimum:
        raise LaneConfigError(f"{path} requires at least {minimum} non-empty lines")
    if exact is not None and len(values) != exact:
        raise LaneConfigError(f"{path} requires exactly {exact} non-empty lines")
    return values


def build_default_config_from_txt(base_dir: str | Path = ".") -> dict[str, Any]:
    root = Path(base_dir)
    sf_keys = _require_count(
        read_nonempty_lines(root / "api.txt"),
        path="api.txt",
        minimum=2,
    )
    ali_keys = _require_count(
        read_nonempty_lines(root / "api_ali.txt"),
        path="api_ali.txt",
        minimum=2,
    )
    sf_url = _require_count(
        read_nonempty_lines(root / "url.txt"),
        path="url.txt",
        minimum=1,
    )[0]
    ali_url = _require_count(
        read_nonempty_lines(root / "url_ali.txt"),
        path="url_ali.txt",
        minimum=1,
    )[0]
    sf_models = _require_count(
        read_nonempty_lines(root / "models.txt"),
        path="models.txt",
        minimum=5,
        exact=5,
    )
    ali_models = _require_count(
        read_nonempty_lines(root / "models_ali.txt"),
        path="models_ali.txt",
        minimum=5,
        exact=5,
    )
    sf_small = _require_count(
        read_nonempty_lines(root / "small.txt"),
        path="small.txt",
        minimum=1,
    )[0]
    ali_small = _require_count(
        read_nonempty_lines(root / "small_ali.txt"),
        path="small_ali.txt",
        minimum=1,
    )[0]
    sf_embedding = _require_count(
        read_nonempty_lines(root / "embeddings.txt"),
        path="embeddings.txt",
        minimum=2,
    )
    ali_embedding = _require_count(
        read_nonempty_lines(root / "embeddings_ali.txt"),
        path="embeddings_ali.txt",
        minimum=2,
    )
    return {
        "version": 1,
        "lanes": [
            {
                "lane_id": "siliconflow_1",
                "provider": "siliconflow",
                "api_key": sf_keys[0],
                "base_url": sf_url,
                "models": sf_models,
                "small_model": sf_small,
                "embedding_model": sf_embedding[0],
                "rerank_model": sf_embedding[1],
                "rerank_base_url": sf_url,
                "rerank_endpoint": "/rerank",
            },
            {
                "lane_id": "siliconflow_2",
                "provider": "siliconflow",
                "api_key": sf_keys[1],
                "base_url": sf_url,
                "models": sf_models,
                "small_model": sf_small,
                "embedding_model": sf_embedding[0],
                "rerank_model": sf_embedding[1],
                "rerank_base_url": sf_url,
                "rerank_endpoint": "/rerank",
            },
            {
                "lane_id": "aliyun_1",
                "provider": "aliyun",
                "api_key": ali_keys[0],
                "base_url": ali_url,
                "models": ali_models,
                "small_model": ali_small,
                "embedding_model": ali_embedding[0],
                "rerank_model": ali_embedding[1],
                "rerank_base_url": "https://dashscope.aliyuncs.com/compatible-api/v1",
                "rerank_endpoint": "/reranks",
            },
            {
                "lane_id": "aliyun_2",
                "provider": "aliyun",
                "api_key": ali_keys[1],
                "base_url": ali_url,
                "models": ali_models,
                "small_model": ali_small,
                "embedding_model": ali_embedding[0],
                "rerank_model": ali_embedding[1],
                "rerank_base_url": "https://dashscope.aliyuncs.com/compatible-api/v1",
                "rerank_endpoint": "/reranks",
            },
        ],
    }


def write_config(config: dict[str, Any], path: str | Path) -> Path:
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")
    return out


def load_lanes(path: str | Path = DEFAULT_CONFIG_PATH) -> list[ProviderLane]:
    payload = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    raw_lanes = payload.get("lanes")
    if not isinstance(raw_lanes, list):
        raise LaneConfigError("config must contain a 'lanes' list")
    lanes: list[ProviderLane] = []
    seen: set[str] = set()
    for index, item in enumerate(raw_lanes, start=1):
        if not isinstance(item, dict):
            raise LaneConfigError(f"lane #{index} must be an object")
        lane_id = str(item.get("lane_id") or "").strip()
        if not lane_id:
            raise LaneConfigError(f"lane #{index} missing lane_id")
        if lane_id in seen:
            raise LaneConfigError(f"duplicate lane_id: {lane_id}")
        seen.add(lane_id)
        models = item.get("models")
        if not isinstance(models, list) or len(models) != 5:
            raise LaneConfigError(f"{lane_id} requires exactly 5 models")
        lane = ProviderLane(
            lane_id=lane_id,
            provider=str(item.get("provider") or "").strip(),
            api_key=str(item.get("api_key") or "").strip(),
            base_url=str(item.get("base_url") or "").strip().rstrip("/"),
            models=tuple(str(model).strip() for model in models),
            small_model=str(item.get("small_model") or "").strip(),
            embedding_model=str(item.get("embedding_model") or "").strip(),
            rerank_model=str(
                item.get("rerank_model") or item.get("reranking_model") or ""
            ).strip(),
            rerank_base_url=(
                str(item.get("rerank_base_url") or "").strip().rstrip("/") or None
            ),
            rerank_endpoint=str(item.get("rerank_endpoint") or "/rerank").strip(),
        )
        validate_lane(lane)
        lanes.append(lane)
    required = {"siliconflow_1", "siliconflow_2", "aliyun_1", "aliyun_2"}
    missing = required - {lane.lane_id for lane in lanes}
    if missing:
        raise LaneConfigError(f"missing required lanes: {', '.join(sorted(missing))}")
    return lanes


def validate_lane(lane: ProviderLane) -> None:
    if not lane.provider:
        raise LaneConfigError(f"{lane.lane_id} missing provider")
    if not lane.api_key:
        raise LaneConfigError(f"{lane.lane_id} missing api_key")
    if not lane.base_url:
        raise LaneConfigError(f"{lane.lane_id} missing base_url")
    if any(not model for model in lane.models):
        raise LaneConfigError(f"{lane.lane_id} contains an empty model name")
    if not lane.small_model:
        raise LaneConfigError(f"{lane.lane_id} missing small_model")
    if not lane.embedding_model:
        raise LaneConfigError(f"{lane.lane_id} missing embedding_model")
    if not lane.rerank_model:
        raise LaneConfigError(f"{lane.lane_id} missing rerank_model")


def lanes_by_id(lanes: list[ProviderLane]) -> dict[str, ProviderLane]:
    return {lane.lane_id: lane for lane in lanes}


def write_runtime_models_file(
    lane: ProviderLane,
    *,
    runtime_root: str | Path,
    run_id: str,
) -> Path:
    out_dir = Path(runtime_root) / run_id / lane.lane_id
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / "models.txt"
    out.write_text("\n".join(lane.models) + "\n", encoding="utf-8")
    return out
