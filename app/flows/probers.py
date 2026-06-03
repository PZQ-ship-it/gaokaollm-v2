import asyncio
import math
import os
import re
import sys
from pathlib import Path
from typing import Any

if __name__ == "__main__" and __package__ is None:
    sys.path.append(str(Path(__file__).resolve().parents[2]))

from app.core import db_pg, embedding_client
from app.core.embedding_client import (
    cosine_similarity,
    ensure_embedding_dimension,
    vector_to_pg_literal,
)
from app.schemas.state import DEFAULT_IMPLICIT_WEIGHTS
from gaokaollm_bench.data_gen.major_tree import build_relaxation_stages
from gaokaollm_bench.data_gen.region_tree_relax import (
    annotate_region_row,
    build_region_relax_targets,
    city_variants,
    load_region_trees,
)


DEFAULT_MAJOR_TREE_PATH = Path("gaokaollm_bench/outputs/major_tree_final_reviewed.json")
DEFAULT_REGION_GEO_TREE_PATH = Path(
    "gaokaollm_bench/outputs/region_geo_tree_reviewed_v1.json"
)
DEFAULT_REGION_URBAN_TREE_PATH = Path(
    "gaokaollm_bench/outputs/region_urban_tier_tree_reviewed_v1.json"
)
UTILITY_FEATURE_KEYS = ("school", "major", "tuition", "quality", "geo", "risk")
GLOBAL_BASELINE_BUCKETS = ("reach", "match", "safety")
GLOBAL_BASELINE_BUCKET_LABELS = {
    "reach": "冲",
    "match": "稳",
    "safety": "保",
}
RANK_BUCKET_RANGES = {
    "reach": (0.85, 0.98),
    "match": (0.98, 1.15),
    "safety": (1.15, 1.40),
}
RANK_WINDOW_MIN = 0.85
RANK_WINDOW_MAX = 1.40
RANK_WINDOW_RELAXED_MIN = 0.75
RISK_RELAX_MAX_RANK_RATIO = 0.95
RISK_RELAX_MIN_SCORE_DEFICIT = 5
RISK_RELAX_MIN_RANK_GAP = 2500
SPECIAL_MAJOR_TERMS = (
    "中外合作",
    "合作办学",
    "学分互认",
    "国际班",
    "国际贸易班",
    "外语成绩",
    "不低于",
    "留学",
    "双文凭",
)
MAJOR_EMBEDDING_NOISE_PATTERN = re.compile(
    r"[（(][^（）()]*?(?:校区|班|方向|合作|学分互认|外语成绩|不低于|留学|双文凭)[^（）()]*?[）)]"
)
MAJOR_SIMILARITY_WEIGHT = 0.70
MAJOR_STAGE_WEIGHT = 1.0 - MAJOR_SIMILARITY_WEIGHT
_MAJOR_VECTOR_CACHE: dict[str, list[float]] = {}
_MAJOR_SIMILARITY_CACHE: dict[tuple[str, str], float] = {}
DEFAULT_LEXICOGRAPHIC_EPSILON = 0.01
SEMANTIC_SCORE_BATCH_SIZE = 200


def _coerce_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        pass
    if not isinstance(value, str):
        return None
    text = str(value)
    match = re.search(r"-?\d+(?:\.\d+)?", text.replace(",", ""))
    if not match:
        return None
    try:
        return float(match.group(0))
    except ValueError:
        return None


def _clamp_unit(value: float) -> float:
    return max(0.0, min(1.0, value))


def _major_similarity_enabled() -> bool:
    if os.getenv("GAOKAOLLM_DISABLE_MAJOR_EMBEDDING") == "1":
        return False
    if os.getenv("PYTEST_CURRENT_TEST"):
        return False
    return bool(os.getenv("EMBEDDING_MODEL"))


def _major_similarity_text(value: Any) -> str:
    text = str(value or "")
    text = MAJOR_EMBEDDING_NOISE_PATTERN.sub("", text)
    text = (
        text.replace("（", " ").replace("）", " ").replace("(", " ").replace(")", " ")
    )
    return embedding_client.normalize_text(text)


def _major_similarity_target(user_state: dict[str, Any] | None) -> str:
    constraints = _state_constraints(user_state)
    target = constraints.get("major")
    if not target and isinstance(user_state, dict):
        original = user_state.get("original_constraints")
        if isinstance(original, dict):
            target = original.get("major")
    return _major_similarity_text(target)


def _major_similarity_label(score: float) -> str:
    if score >= 0.86:
        return "高度贴合"
    if score >= 0.74:
        return "较贴合"
    if score >= 0.62:
        return "有一定相关"
    if score >= 0.50:
        return "相关性偏弱"
    return "相关性较弱"


async def _embed_major_texts(texts: list[str]) -> None:
    missing = [text for text in texts if text and text not in _MAJOR_VECTOR_CACHE]
    if not missing:
        return
    client_cls = getattr(embedding_client, "Open" + "AIEmbeddingClient")
    client = client_cls()
    vectors = await client.embed(missing)
    for text, vector in zip(missing, vectors):
        _MAJOR_VECTOR_CACHE[text] = vector


async def annotate_major_similarity(
    candidates: list[dict[str, Any]],
    user_state: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    """Annotate candidates with continuous major-demand similarity when configured."""

    if not candidates or not _major_similarity_enabled():
        return candidates

    target = _major_similarity_target(user_state)
    if not target:
        return candidates

    rows = [
        dict(candidate) if isinstance(candidate, dict) else {}
        for candidate in candidates
    ]
    candidate_texts = [
        _major_similarity_text(row.get("major_name") or row.get("major"))
        for row in rows
    ]
    unique_texts = list(
        dict.fromkeys([target, *[text for text in candidate_texts if text]])
    )
    await _embed_major_texts(unique_texts)
    target_vector = _MAJOR_VECTOR_CACHE.get(target)
    if not target_vector:
        raise RuntimeError("Major embedding target vector is unavailable.")

    for row, candidate_text in zip(rows, candidate_texts):
        if not candidate_text:
            continue
        cache_key = (target, candidate_text)
        score = _MAJOR_SIMILARITY_CACHE.get(cache_key)
        if score is None:
            candidate_vector = _MAJOR_VECTOR_CACHE.get(candidate_text)
            if not candidate_vector:
                raise RuntimeError(
                    f"Major embedding vector is unavailable for {candidate_text!r}."
                )
            score = _clamp_unit(cosine_similarity(target_vector, candidate_vector))
            if target == candidate_text:
                score = 1.0
            elif len(target) >= 4 and target in candidate_text:
                score = max(score, 0.92)
            elif len(candidate_text) >= 4 and candidate_text in target:
                score = max(score, 0.92)
            _MAJOR_SIMILARITY_CACHE[cache_key] = score
        row["major_similarity_score"] = round(float(score), 4)
        row["major_similarity_target"] = target
        row["major_similarity_method"] = "embedding_cosine"
        row["major_similarity_label"] = _major_similarity_label(float(score))
    return rows


def _full_context_embedding(user_state: dict[str, Any] | None) -> list[float] | None:
    if not isinstance(user_state, dict):
        return None
    raw = user_state.get("full_context_embedding")
    if not isinstance(raw, list) or not raw:
        return None
    try:
        vector = [float(value) for value in raw]
    except (TypeError, ValueError):
        return None
    ensure_embedding_dimension(vector, label="full_context_embedding")
    return vector


def _candidate_semantic_key(row: dict[str, Any]) -> tuple[Any, Any, Any]:
    return (
        row.get("admission_score_id"),
        row.get("school_id"),
        row.get("major_id") or row.get("major_name"),
    )


async def _fetch_semantic_scores(
    db: Any,
    *,
    query_vector: list[float],
    rows: list[dict[str, Any]],
) -> dict[tuple[Any, Any, Any], float]:
    keyed_rows = [
        (
            index,
            row.get("admission_score_id"),
            row.get("school_id"),
            row.get("major_id"),
            row.get("major_name"),
        )
        for index, row in enumerate(rows)
    ]
    if not keyed_rows:
        return {}
    vector_literal = vector_to_pg_literal(query_vector)
    result: dict[tuple[Any, Any, Any], float] = {}
    for start in range(0, len(keyed_rows), SEMANTIC_SCORE_BATCH_SIZE):
        chunk = keyed_rows[start : start + SEMANTIC_SCORE_BATCH_SIZE]
        values_sql = ",".join(["(%s,%s,%s,%s,%s)"] * len(chunk))
        params: list[Any] = []
        for index, admission_score_id, school_id, major_id, major_name in chunk:
            params.extend([index, admission_score_id, school_id, major_id, major_name])
        params.append(vector_literal)
        query = f"""
WITH candidate(index, admission_score_id, school_id, major_id, major_name) AS (
    VALUES {values_sql}
)
SELECT
    candidate.index,
    candidate.admission_score_id,
    candidate.school_id,
    candidate.major_id,
    candidate.major_name,
    MAX(1 - (kd.embedding <=> %s::vector)) AS semantic_score
FROM candidate
LEFT JOIN knowledge_documents kd
  ON kd.embedding IS NOT NULL
 AND (
    kd.school_id = candidate.school_id
    OR kd.major_id = candidate.major_id
    OR (candidate.major_id IS NULL AND kd.title = candidate.major_name)
 )
GROUP BY
    candidate.index,
    candidate.admission_score_id,
    candidate.school_id,
    candidate.major_id,
    candidate.major_name
"""
        fetched = await _fetch(db, query, params)
        for item in fetched:
            score = _coerce_float(item.get("semantic_score"))
            if score is None:
                continue
            key = (
                item.get("admission_score_id"),
                item.get("school_id"),
                item.get("major_id") or item.get("major_name"),
            )
            result[key] = _clamp_unit(float(score))
    return result


async def annotate_full_context_semantic_score(
    candidates: list[dict[str, Any]],
    user_state: dict[str, Any] | None,
    db: Any = None,
) -> list[dict[str, Any]]:
    rows = [
        dict(candidate) if isinstance(candidate, dict) else {}
        for candidate in candidates or []
    ]
    if not rows:
        return rows
    query_vector = _full_context_embedding(user_state)
    if query_vector is None:
        for row in rows:
            row.setdefault("semantic_score", None)
            row.setdefault("semantic_score_source", "missing_full_context_embedding")
        return rows
    scores = await _fetch_semantic_scores(
        db,
        query_vector=query_vector,
        rows=rows,
    )
    for row in rows:
        score = scores.get(_candidate_semantic_key(row))
        if score is None:
            row["semantic_score"] = None
            row["semantic_score_source"] = "missing_knowledge_embedding"
            continue
        row["semantic_score"] = round(float(score), 6)
        row["semantic_score_source"] = "knowledge_documents_pgvector"
    return rows


def _state_constraints(user_state: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(user_state, dict):
        return {}
    constraints = user_state.get("constraints")
    if isinstance(constraints, dict):
        return dict(constraints)
    return dict(user_state)


def _accepted_relaxed_dimensions(user_state: dict[str, Any] | None) -> set[str]:
    if not isinstance(user_state, dict):
        return set()
    accepted = user_state.get("accepted_relaxations")
    if not isinstance(accepted, list):
        return set()
    dimensions: set[str] = set()
    for item in accepted:
        if not isinstance(item, dict):
            continue
        dimension = str(item.get("dimension") or "").strip()
        if dimension:
            dimensions.add(dimension)
    return dimensions


def _has_accepted_relaxation(
    user_state: dict[str, Any] | None,
    *dimensions: str,
) -> bool:
    accepted = _accepted_relaxed_dimensions(user_state)
    return any(dimension in accepted for dimension in dimensions)


def _apply_accepted_relaxations(
    constraints: dict[str, Any],
    user_state: dict[str, Any] | None,
) -> dict[str, Any]:
    if not isinstance(user_state, dict):
        return constraints
    accepted = user_state.get("accepted_relaxations")
    if not isinstance(accepted, list):
        return constraints
    adjusted = dict(constraints)
    for item in accepted:
        if not isinstance(item, dict):
            continue
        dimension = str(item.get("dimension") or "")
        if dimension == "geo":
            adjusted.pop("target_provinces", None)
            adjusted.pop("city", None)
            adjusted["school_region_relaxed"] = True
        elif dimension == "major":
            adjusted.pop("major", None)
        elif dimension == "tuition":
            accepted_budget = _coerce_float(item.get("accepted_budget"))
            current_budget = _coerce_float(adjusted.get("budget"))
            if accepted_budget is None:
                continue
            if current_budget is None or accepted_budget > current_budget:
                adjusted["budget"] = int(round(accepted_budget))
        elif dimension in {"school", "quality"}:
            adjusted.pop("strength", None)
        elif dimension == "risk":
            adjusted.pop("risk_preference", None)
    return adjusted


def _terminal_search_constraints(
    constraints: dict[str, Any],
    user_state: dict[str, Any] | None,
) -> dict[str, Any]:
    """Keep immutable exam facts, but drop preference filters the user accepted relaxing."""

    adjusted = dict(constraints)
    if _has_accepted_relaxation(user_state, "geo"):
        adjusted.pop("target_provinces", None)
        adjusted.pop("city", None)
        adjusted["school_region_relaxed"] = True
    if _has_accepted_relaxation(user_state, "major"):
        adjusted.pop("major", None)
    if _has_accepted_relaxation(user_state, "tuition"):
        adjusted.pop("budget", None)
    if _has_accepted_relaxation(user_state, "school", "quality"):
        adjusted.pop("strength", None)
    if _has_accepted_relaxation(user_state, "risk"):
        adjusted.pop("risk_preference", None)
    return adjusted


def _city_values_for_match(city: Any) -> set[str]:
    if not city:
        return set()
    try:
        return {str(item) for item in city_variants(str(city)) if str(item)}
    except Exception:
        return {str(city)}


def _candidate_matches_geo(
    candidate: dict[str, Any], constraints: dict[str, Any]
) -> bool:
    target_provinces = constraints.get("target_provinces")
    province = str(candidate.get("school_province") or candidate.get("province") or "")
    if isinstance(target_provinces, list) and target_provinces:
        allowed = {str(item) for item in target_provinces if str(item)}
        if province and province not in allowed:
            return False
    elif constraints.get("province"):
        if province and province != str(constraints.get("province")):
            return False

    city = constraints.get("city")
    if city:
        candidate_city = str(
            candidate.get("school_city") or candidate.get("city") or ""
        )
        if candidate_city and candidate_city not in _city_values_for_match(city):
            return False
    return True


def _rank_ratio_for_candidate(candidate: dict[str, Any]) -> float | None:
    student_rank = _coerce_float(candidate.get("student_rank"))
    min_rank = _coerce_float(candidate.get("min_rank"))
    if student_rank is None or student_rank <= 0 or min_rank is None:
        return None
    return min_rank / student_rank


def _risk_phi(candidate: dict[str, Any]) -> float:
    ratio = _rank_ratio_for_candidate(candidate)
    if ratio is None:
        return 0.5
    if ratio < 0.85:
        return 0.0
    if ratio < 0.98:
        return 0.25
    if ratio <= 1.15:
        return 0.70
    if ratio <= 1.40:
        return 1.0
    return 0.5


def _annotate_terminal_relaxation_features(
    candidate: dict[str, Any],
    constraints: dict[str, Any],
    user_state: dict[str, Any] | None,
) -> dict[str, Any]:
    row = dict(candidate)
    if _has_accepted_relaxation(user_state, "geo") and not _candidate_matches_geo(
        row, constraints
    ):
        row.setdefault("geo_relax_level", 1)
    major = constraints.get("major")
    major_name = str(row.get("major_name") or row.get("major") or "")
    if (
        _has_accepted_relaxation(user_state, "major")
        and major
        and str(major) not in major_name
    ):
        row.setdefault("major_relax_level", 1)
    if _has_accepted_relaxation(user_state, "risk"):
        ratio = _rank_ratio_for_candidate(row)
        if ratio is not None and ratio < 0.98:
            row.setdefault("risk_relax_level", 1)
    return row


def _annotate_major_geo_probe_features(
    candidate: dict[str, Any],
    constraints: dict[str, Any],
    stage: dict[str, Any],
) -> dict[str, Any]:
    row = dict(candidate)
    if not _candidate_matches_geo(row, constraints):
        row.setdefault("geo_relax_level", 1)

    strict_major = constraints.get("major")
    major_name = str(row.get("major_name") or row.get("major") or "")
    if strict_major and str(strict_major) not in major_name:
        stage_level = _coerce_float(stage.get("stage"))
        if stage_level is None or stage_level <= 0:
            stage_level = 1.0
        row.setdefault("major_relax_level", stage_level)
    return row


def _utility_weights(user_state: dict[str, Any] | None) -> dict[str, float]:
    weights = dict(DEFAULT_IMPLICIT_WEIGHTS)
    raw_weights = (
        user_state.get("implicit_weights") if isinstance(user_state, dict) else None
    )
    if not isinstance(raw_weights, dict):
        return weights
    for key in UTILITY_FEATURE_KEYS:
        coerced = _coerce_float(raw_weights.get(key))
        if coerced is not None:
            weights[key] = coerced
    return weights


def _quality_bounds(candidates: list[dict[str, Any]]) -> tuple[float, float] | None:
    scores: list[float] = []
    for candidate in candidates or []:
        if not isinstance(candidate, dict):
            continue
        score = _coerce_float(candidate.get("quality_score"))
        if score is not None:
            scores.append(score)
    if not scores:
        return None
    return min(scores), max(scores)


def _school_phi(candidate_dict: dict[str, Any]) -> float:
    tier_text = " ".join(
        str(candidate_dict.get(key) or "")
        for key in (
            "school_tier",
            "school_level",
            "tier_label",
            "education_tier",
            "school_type",
            "education_level",
        )
    )
    if "C9" in tier_text or "顶尖985" in tier_text:
        return 1.0
    if "985" in tier_text:
        return 0.85
    if "211" in tier_text or "双一流" in tier_text:
        return 0.70
    if "一本" in tier_text or "重点" in tier_text:
        return 0.40

    if bool(candidate_dict.get("is_985")):
        return 0.85
    if bool(candidate_dict.get("is_211")) or bool(
        candidate_dict.get("is_double_first_class")
    ):
        return 0.70

    tier = _coerce_float(candidate_dict.get("tier"))
    if tier is not None:
        if tier >= 4:
            return 0.85
        if tier >= 3:
            return 0.70
        if tier >= 2:
            return 0.40
    return 0.10


def extract_phi_features(
    candidate_dict: dict[str, Any],
    user_state: dict[str, Any] | None,
    quality_bounds: tuple[float, float] | None = None,
) -> dict[str, float]:
    """Map a physical SQL row to dimensionless MAUT feature values."""

    candidate = candidate_dict if isinstance(candidate_dict, dict) else {}
    constraints = _state_constraints(user_state)
    features = {
        "school": 0.10,
        "major": 1.0,
        "tuition": 1.0,
        "quality": 0.5,
        "geo": 1.0,
        "risk": 0.5,
    }

    try:
        features["school"] = _school_phi(candidate)
    except Exception:
        features["school"] = 0.10

    try:
        major_level = _coerce_float(candidate.get("major_relax_level"))
        if major_level is None:
            major_level = 0.0
        stage_major_phi = max(0.0, 1.0 - 0.35 * major_level)
        features["major"] = stage_major_phi
    except Exception:
        features["major"] = 1.0

    try:
        geo_level = _coerce_float(candidate.get("geo_relax_level"))
        if geo_level is None:
            geo_level = 0.0
        features["geo"] = max(0.0, 1.0 - 0.30 * geo_level)
    except Exception:
        features["geo"] = 1.0

    try:
        features["risk"] = _risk_phi(candidate)
    except Exception:
        features["risk"] = 0.5

    try:
        quality_score = _coerce_float(candidate.get("quality_score"))
        if quality_score is None:
            features["quality"] = 0.5
        elif quality_bounds is not None:
            q_min, q_max = quality_bounds
            if q_max <= q_min:
                features["quality"] = 0.5
            else:
                # 候选池局部 Min-Max 归一化：把本轮探测池内的质量差距拉开，
                # 避免固定除以 100 后高低质量方案在效用空间里过度同质化。
                features["quality"] = _clamp_unit(
                    (quality_score - q_min) / (q_max - q_min)
                )
        else:
            features["quality"] = _clamp_unit(quality_score / 100.0)
    except Exception:
        features["quality"] = 0.5

    try:
        tuition = _coerce_float(candidate.get("tuition"))
        budget = _coerce_float(constraints.get("budget"))
        if tuition is None or budget is None or budget <= 0 or tuition <= budget:
            features["tuition"] = 1.0
        else:
            excess_ratio = (tuition - budget) / budget
            tuition_relaxed = _has_accepted_relaxation(user_state, "tuition")
            # 防止“线性补偿陷阱”：当学费严重超预算时，不能让名校光环
            # 或质量分通过线性加权把该方案重新抬到前排，因此触发非补偿性否决。
            if excess_ratio >= 0.30 and not tuition_relaxed:
                features["tuition"] = -9999.0
            else:
                features["tuition"] = max(0.0, 1.0 - 2.0 * excess_ratio)
    except Exception:
        features["tuition"] = 1.0

    return features


def _lexicographic_epsilon(user_state: dict[str, Any] | None) -> float:
    raw = (
        user_state.get("lexicographic_epsilon")
        if isinstance(user_state, dict)
        else None
    )
    try:
        epsilon = float(raw)
    except (TypeError, ValueError):
        epsilon = DEFAULT_LEXICOGRAPHIC_EPSILON
    if epsilon <= 0:
        return DEFAULT_LEXICOGRAPHIC_EPSILON
    return epsilon


def _lexicographic_tier(utility: float, epsilon: float) -> int:
    if epsilon <= 0:
        epsilon = DEFAULT_LEXICOGRAPHIC_EPSILON
    return math.floor(float(utility) / epsilon)


def _semantic_score(row: dict[str, Any]) -> float:
    score = _coerce_float(row.get("semantic_score"))
    if score is None:
        return 0.0
    return _clamp_unit(score)


def _stable_sort_token(row: dict[str, Any]) -> str:
    return "|".join(
        str(row.get(key) or "")
        for key in (
            "admission_score_id",
            "school_id",
            "school_name",
            "major_id",
            "major_name",
        )
    )


def _lexicographic_sort_key(row: dict[str, Any]) -> tuple[Any, ...]:
    utility = float(row.get("_implicit_utility") or -999999.0)
    epsilon = float(row.get("_lexicographic_epsilon") or DEFAULT_LEXICOGRAPHIC_EPSILON)
    tier = int(row.get("_lexicographic_tier") or _lexicographic_tier(utility, epsilon))
    return (
        tier,
        float(row.get("_semantic_score") or 0.0),
        utility,
        -int(row.get("ranking") or 999999),
        int(row.get("year") or 0),
        _stable_sort_token(row),
    )


def rank_by_implicit_utility(
    candidates: list[dict[str, Any]],
    user_state: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    weights = _utility_weights(user_state)
    rows = [
        dict(candidate) if isinstance(candidate, dict) else {}
        for candidate in candidates or []
    ]
    quality_bounds = _quality_bounds(rows)
    ranked: list[dict[str, Any]] = []
    epsilon = _lexicographic_epsilon(user_state)
    for row in rows:
        try:
            features = extract_phi_features(row, user_state, quality_bounds)
            utility = sum(
                weights.get(key, 0.0) * features.get(key, 0.0)
                for key in UTILITY_FEATURE_KEYS
            )
        except Exception:
            features = {
                "school": 0.10,
                "major": 0.0,
                "tuition": -9999.0,
                "quality": 0.5,
                "geo": 0.0,
                "risk": 0.0,
            }
            utility = -9999.0
        row["_phi_features"] = features
        row["_implicit_utility"] = float(utility)
        row["_semantic_score"] = _semantic_score(row)
        row["_lexicographic_epsilon"] = epsilon
        row["_lexicographic_tier"] = _lexicographic_tier(float(utility), epsilon)
        ranked.append(row)
    return sorted(
        ranked,
        key=_lexicographic_sort_key,
        reverse=True,
    )


async def rank_by_implicit_utility_async(
    candidates: list[dict[str, Any]],
    user_state: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    annotated = await annotate_major_similarity(candidates, user_state)
    annotated = await annotate_full_context_semantic_score(annotated, user_state)
    return rank_by_implicit_utility(annotated, user_state)


PLAN_TUITION_JOIN = """
LEFT JOIN LATERAL (
    SELECT p.tuition AS min_tuition
    FROM admission_plans p
    WHERE p.school_id = a.school_id
      AND (
          p.major_id = a.major_id
          OR p.major_code = a.major_code
          OR p.major_name_raw = a.major_name_raw
      )
      AND p.tuition IS NOT NULL
    ORDER BY
      CASE WHEN p.year = a.year THEN 0 ELSE 1 END,
      CASE WHEN p.year IS NULL THEN 9999 ELSE abs(p.year - a.year) END,
      p.tuition ASC
    LIMIT 1
) plan ON true
"""


BASE_SELECT = f"""
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
    a.requirement_normalized,
    COALESCE(sr.requirement_type, 'unknown') AS requirement_type,
    a.min_score,
    a.min_rank,
    plan.min_tuition AS tuition,
    CASE
        WHEN s.is_985 THEN 4
        WHEN s.is_211 OR s.is_double_first_class THEN 3
        WHEN s.education_level = '本科' THEN 2
        ELSE 1
    END AS tier
FROM admission_scores a
JOIN schools s ON s.id = a.school_id
LEFT JOIN subject_requirements sr ON sr.raw_requirement = a.subject_requirement
{PLAN_TUITION_JOIN}
"""

BASE_ORDER = """
ORDER BY
    tier DESC,
    s.ranking ASC NULLS LAST,
    a.min_score DESC NULLS LAST,
    a.year DESC,
    s.name ASC,
    a.major_name_raw ASC
LIMIT %s
"""

MAJOR_GEO_ORDER = """
ORDER BY
    a.year DESC,
    tier DESC,
    s.ranking ASC NULLS LAST,
    a.min_score DESC NULLS LAST,
    s.name ASC,
    a.major_name_raw ASC
LIMIT %s
"""

STRENGTH_SELECT = f"""
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
    a.requirement_normalized,
    COALESCE(sr.requirement_type, 'unknown') AS requirement_type,
    a.min_score,
    a.min_rank,
    plan.min_tuition AS tuition,
    sms.major_strength_rank AS major_strength_rank,
    sms.major_strength_rating AS major_strength_rating,
    sms.major_strength_level AS major_strength_level,
    sms.major_strength_source_type AS major_strength_source_type,
    sms.discipline_name AS discipline_name,
    CASE
        WHEN s.is_985 THEN 4
        WHEN s.is_211 OR s.is_double_first_class THEN 3
        WHEN s.education_level = '本科' THEN 2
        ELSE 1
    END AS tier
FROM admission_scores a
JOIN schools s ON s.id = a.school_id
LEFT JOIN subject_requirements sr ON sr.raw_requirement = a.subject_requirement
{PLAN_TUITION_JOIN}
LEFT JOIN (
    SELECT DISTINCT ON (sms.school_id)
        sms.school_id,
        sms.rank AS major_strength_rank,
        sms.rating AS major_strength_rating,
        sms.level AS major_strength_level,
        sms.source_type AS major_strength_source_type,
        sms.discipline_name AS discipline_name
    FROM school_major_strengths sms
    WHERE sms.source_type = 'major_ranking'
      AND sms.rank IS NOT NULL
    ORDER BY
        sms.school_id,
        sms.rank ASC NULLS LAST,
        sms.rating ASC NULLS LAST
) sms ON sms.school_id = a.school_id
"""

MAJOR_QUALITY_SELECT = f"""
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
    a.requirement_normalized,
    COALESCE(sr.requirement_type, 'unknown') AS requirement_type,
    a.min_score,
    a.min_rank,
    plan.min_tuition AS tuition,
    mq.quality_score,
    mq.quality_tier,
    mq.best_major_rank,
    mq.best_rating,
    mq.has_key_major,
    mq.has_featured_major,
    mq.satisfaction_score,
    mq.vote_count AS satisfaction_vote_count,
    mq.evidence_sources AS quality_evidence_sources,
    CASE
        WHEN s.is_985 THEN 4
        WHEN s.is_211 OR s.is_double_first_class THEN 3
        WHEN s.education_level = '本科' THEN 2
        ELSE 1
    END AS tier
FROM admission_scores a
JOIN schools s ON s.id = a.school_id
LEFT JOIN subject_requirements sr ON sr.raw_requirement = a.subject_requirement
{PLAN_TUITION_JOIN}
LEFT JOIN LATERAL (
    SELECT
        profile.quality_score,
        profile.quality_tier,
        profile.best_major_rank,
        profile.best_rating,
        profile.has_key_major,
        profile.has_featured_major,
        profile.satisfaction_score,
        profile.vote_count,
        profile.evidence_sources
    FROM school_major_quality_profiles profile
    WHERE profile.school_id = a.school_id
      AND profile.major_id = a.major_id
    ORDER BY
        profile.quality_score DESC,
        profile.best_major_rank ASC NULLS LAST
    LIMIT 1
) mq ON true
"""

EMPLOYMENT_OUTCOME_SELECT = f"""
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
    a.requirement_normalized,
    COALESCE(sr.requirement_type, 'unknown') AS requirement_type,
    a.min_score,
    a.min_rank,
    plan.min_tuition AS tuition,
    me.outcome_score,
    me.outcome_tier,
    me.employment_rank,
    me.employment_rank_desc,
    me.top_city AS employment_top_city,
    me.top_industry,
    me.industry_distribution,
    me.city_distribution AS employment_city_distribution,
    me.job_distribution,
    me.salary_distribution,
    me.evidence_sources AS employment_evidence_sources,
    CASE
        WHEN s.is_985 THEN 4
        WHEN s.is_211 OR s.is_double_first_class THEN 3
        WHEN s.education_level = '本科' THEN 2
        ELSE 1
    END AS tier
FROM admission_scores a
JOIN schools s ON s.id = a.school_id
LEFT JOIN subject_requirements sr ON sr.raw_requirement = a.subject_requirement
{PLAN_TUITION_JOIN}
LEFT JOIN LATERAL (
    SELECT
        profile.outcome_score,
        profile.outcome_tier,
        profile.employment_rank,
        profile.employment_rank_desc,
        profile.top_city,
        profile.top_industry,
        profile.industry_distribution,
        profile.city_distribution,
        profile.job_distribution,
        profile.salary_distribution,
        profile.evidence_sources
    FROM major_employment_outcome_profiles profile
    WHERE profile.major_id = a.major_id
      OR profile.major_name = trim(replace(a.major_name_raw, '专业', ''))
    ORDER BY
        CASE WHEN profile.major_id = a.major_id THEN 0 ELSE 1 END,
        profile.outcome_score DESC,
        profile.employment_rank ASC NULLS LAST
    LIMIT 1
) me ON true
"""


async def _fetch(db: Any, query: str, params: list[Any]) -> list[dict[str, Any]]:
    if db is None:
        return await db_pg.fetch_query(query, *params)
    if hasattr(db, "fetch_query"):
        return await db.fetch_query(query, *params)
    return await db(query, *params)


def _score(constraints: dict[str, Any]) -> int:
    score = constraints.get("score")
    if score is None:
        raise ValueError("constraints['score'] is required")
    return int(str(score))


def _budget(constraints: dict[str, Any]) -> int | None:
    budget = constraints.get("budget")
    if budget in (None, ""):
        return None
    return int(str(budget))


def _max_tier(rows: list[dict[str, Any]]) -> int:
    if not rows:
        return 0
    return max(int(row.get("tier") or 0) for row in rows)


def _best_ranking(rows: list[dict[str, Any]]) -> int | None:
    rankings = []
    for row in rows:
        ranking = row.get("ranking")
        if ranking is None:
            continue
        try:
            rankings.append(int(ranking))
        except (TypeError, ValueError):
            continue
    return min(rankings) if rankings else None


async def _tuition_value_anchor(
    constraints: dict[str, Any],
    *,
    db: Any = None,
    budget: int,
    limit: int = 3,
) -> list[dict[str, Any]]:
    where, params = _where_common({**constraints, "budget": None})
    _add_province_filter(where, params, constraints)
    _add_city_filter(where, params, constraints)
    _add_major_filter(where, params, constraints)
    _add_undergraduate_quality_filters(where, params)
    _add_major_quality_filters(where, params, max_major_name_length=60)
    where.extend(
        [
            "plan.min_tuition IS NOT NULL",
            "plan.min_tuition <= %s",
            "s.ranking IS NOT NULL",
        ]
    )
    params.extend([budget, limit])
    query = (
        f"{BASE_SELECT}\n"
        f"WHERE {' AND '.join(where)}\n"
        "ORDER BY\n"
        "    s.ranking ASC NULLS LAST,\n"
        "    tier DESC,\n"
        "    plan.min_tuition ASC NULLS LAST,\n"
        "    a.min_score DESC NULLS LAST,\n"
        "    a.year DESC,\n"
        "    s.name ASC,\n"
        "    a.major_name_raw ASC\n"
        "LIMIT %s"
    )
    return await _fetch(db, query, params)


def classify_risk_band(
    *,
    score_margin: int | float | None,
    rank_gap: int | float | None = None,
    rank_ratio: int | float | None = None,
) -> str:
    """Classify admission risk using the paper's c / r rank-ratio windows."""

    ratio = _coerce_float(rank_ratio)
    if ratio is not None:
        bucket = _risk_bucket_from_rank_ratio(ratio)
        if bucket == "reach":
            return "chong"
        if bucket == "match":
            return "wen"
        if bucket == "safety":
            return "bao"
        return "dian"

    if rank_gap is not None:
        # Legacy fallback for synthetic rows without a student-rank mapping.
        try:
            gap = float(rank_gap)
        except (TypeError, ValueError):
            gap = 999999.0
        if gap < 0:
            return "chong"
        if gap <= 12000:
            return "wen"
        if gap <= 30000:
            return "bao"
        return "dian"

    if score_margin is None:
        return "unknown"
    margin = float(score_margin)
    if margin <= 5:
        return "chong"
    if margin <= 20:
        return "wen"
    if margin <= 45:
        return "bao"
    return "dian"


def _risk_band_order(risk_level: str | None) -> int:
    order = {
        "chong": 0,
        "wen": 1,
        "bao": 2,
        "dian": 3,
        "unknown": 4,
    }
    return order.get(str(risk_level or "unknown"), 4)


def _annotate_risk_row(
    row: dict[str, Any],
    *,
    score: int,
    student_rank: int | None,
) -> dict[str, Any]:
    annotated = dict(row)
    min_score = row.get("min_score")
    min_rank = row.get("min_rank")
    score_margin = None
    rank_gap = None
    if min_score is not None:
        score_margin = score - int(float(min_score))
    if student_rank is not None and min_rank is not None:
        rank_gap = int(float(min_rank)) - student_rank
    rank_ratio = None
    if student_rank is not None and student_rank > 0 and min_rank is not None:
        rank_ratio = float(min_rank) / float(student_rank)
    annotated["score_margin"] = score_margin
    annotated["student_rank"] = student_rank
    annotated["rank_gap"] = rank_gap
    annotated["rank_ratio"] = round(rank_ratio, 4) if rank_ratio is not None else None
    annotated["risk_level"] = classify_risk_band(
        score_margin=score_margin,
        rank_gap=rank_gap,
        rank_ratio=rank_ratio,
    )
    return annotated


def _is_material_risk_relaxation(row: dict[str, Any]) -> bool:
    rank_ratio = _coerce_float(row.get("rank_ratio"))
    if rank_ratio is not None:
        return rank_ratio <= RISK_RELAX_MAX_RANK_RATIO
    rank_gap = _coerce_float(row.get("rank_gap"))
    if rank_gap is not None:
        return rank_gap <= -RISK_RELAX_MIN_RANK_GAP
    score_margin = _coerce_float(row.get("score_margin"))
    if score_margin is not None:
        return score_margin <= -RISK_RELAX_MIN_SCORE_DEFICIT
    return False


def _risk_selection_key(row: dict[str, Any]) -> tuple[Any, ...]:
    ranking = row.get("ranking")
    score_margin = row.get("score_margin")
    return (
        _risk_band_order(row.get("risk_level")),
        int(ranking) if ranking is not None else 999999,
        abs(float(score_margin)) if score_margin is not None else 9999.0,
        -int(row.get("tier") or 0),
        -int(row.get("year") or 0),
        str(row.get("school_name") or ""),
        str(row.get("major_name") or ""),
    )


def _select_risk_portfolio(
    rows: list[dict[str, Any]],
    *,
    limit: int,
    max_per_school: int,
) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    school_counts: dict[Any, int] = {}
    seen_options: set[tuple[Any, Any]] = set()

    for required_band in ("chong", "wen", "bao"):
        for row in sorted(rows, key=_risk_selection_key):
            if row.get("risk_level") != required_band:
                continue
            if _append_unique_option(
                selected,
                row,
                seen_options=seen_options,
                school_counts=school_counts,
                max_per_school=max_per_school,
            ):
                break

    for row in sorted(rows, key=_risk_selection_key):
        if len(selected) >= limit:
            break
        _append_unique_option(
            selected,
            row,
            seen_options=seen_options,
            school_counts=school_counts,
            max_per_school=max_per_school,
        )

    return selected[:limit]


def _append_unique_option(
    selected: list[dict[str, Any]],
    row: dict[str, Any],
    *,
    seen_options: set[tuple[Any, Any]],
    school_counts: dict[Any, int],
    max_per_school: int,
) -> bool:
    option_key = (
        row.get("school_id"),
        row.get("major_id") or row.get("major_name"),
    )
    if option_key in seen_options:
        return False
    school_key = row.get("school_id") or row.get("school_name")
    if school_counts.get(school_key, 0) >= max_per_school:
        return False
    seen_options.add(option_key)
    school_counts[school_key] = school_counts.get(school_key, 0) + 1
    selected.append(row)
    return True


def _tier_sql() -> str:
    return """
    CASE
        WHEN s.is_985 THEN 4
        WHEN s.is_211 OR s.is_double_first_class THEN 3
        WHEN s.education_level = '本科' THEN 2
        ELSE 1
    END
    """


def _where_common(
    constraints: dict[str, Any],
    *,
    include_score_ceiling: bool = True,
) -> tuple[list[str], list[Any]]:
    where = ["a.min_score IS NOT NULL"]
    params: list[Any] = []
    if include_score_ceiling:
        where.append("a.min_score <= %s")
        params.append(_score(constraints))

    budget = _budget(constraints)
    if budget is not None:
        where.append("plan.min_tuition IS NOT NULL")
        where.append("plan.min_tuition <= %s")
        params.append(budget)

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

    return where, params


def _add_province_filter(
    where: list[str],
    params: list[Any],
    constraints: dict[str, Any],
) -> None:
    if constraints.get("school_region_relaxed") or constraints.get("province_relaxed"):
        return
    target_provinces = constraints.get("target_provinces")
    if isinstance(target_provinces, list) and target_provinces:
        where.append("s.province = ANY(%s::text[])")
        params.append([str(item) for item in target_provinces if str(item)])
        return
    province = constraints.get("province")
    if province:
        where.append("s.province = %s")
        params.append(province)


def _add_city_filter(
    where: list[str],
    params: list[Any],
    constraints: dict[str, Any],
) -> None:
    if constraints.get("school_region_relaxed") or constraints.get("province_relaxed"):
        return
    city = constraints.get("city")
    if city:
        where.append("s.city = ANY(%s::text[])")
        params.append(city_variants(city))


def _add_major_filter(
    where: list[str],
    params: list[Any],
    constraints: dict[str, Any],
) -> None:
    major = constraints.get("major")
    if major:
        where.append("a.major_name_raw LIKE %s")
        params.append(f"%{major}%")


def _add_higher_tier_filter(
    where: list[str],
    params: list[Any],
    baseline: list[dict[str, Any]],
) -> None:
    where.append(f"{_tier_sql()} > %s")
    params.append(_max_tier(baseline))


def _add_school_gain_filter(
    where: list[str],
    params: list[Any],
    baseline: list[dict[str, Any]],
) -> None:
    clauses = [f"{_tier_sql()} > %s"]
    params.append(_max_tier(baseline))
    best_ranking = _best_ranking(baseline)
    if best_ranking is not None:
        clauses.append("s.ranking IS NOT NULL AND s.ranking < %s")
        params.append(best_ranking)
    where.append("(" + " OR ".join(clauses) + ")")


def _add_undergraduate_quality_filters(
    where: list[str],
    params: list[Any],
) -> None:
    where.extend(
        [
            "s.education_level = '本科'",
            "(s.name LIKE %s OR s.name LIKE %s)",
            "NOT (s.name LIKE %s AND s.name NOT LIKE %s)",
        ]
    )
    params.extend(["%大学%", "%医学院%", "%大学%学院%", "%医学院%"])


def _add_major_quality_filters(
    where: list[str],
    params: list[Any],
    *,
    max_major_name_length: int | None,
) -> None:
    if max_major_name_length is not None:
        where.append("char_length(a.major_name_raw) <= %s")
        params.append(max_major_name_length)
    for term in SPECIAL_MAJOR_TERMS:
        where.append("a.major_name_raw NOT LIKE %s")
        params.append(f"%{term}%")


def _stage_major_patterns(
    stage: dict[str, Any],
    strict_major: str | None,
) -> tuple[list[str], list[str]]:
    strategy = stage.get("strategy")
    include_patterns = list(stage.get("include_patterns") or [])
    exclude_patterns = list(stage.get("exclude_patterns") or [])
    if strategy == "any_major" or not include_patterns:
        if strict_major:
            exclude_patterns.append(f"%{strict_major}%")
        return [], list(dict.fromkeys(exclude_patterns))
    return list(dict.fromkeys(include_patterns)), list(dict.fromkeys(exclude_patterns))


def _add_stage_major_filters(
    where: list[str],
    params: list[Any],
    *,
    stage: dict[str, Any],
    strict_major: str | None,
) -> None:
    include_patterns, exclude_patterns = _stage_major_patterns(stage, strict_major)
    if include_patterns:
        where.append(
            "("
            + " OR ".join(["a.major_name_raw LIKE %s"] * len(include_patterns))
            + ")"
        )
        params.extend(include_patterns)
    for pattern in exclude_patterns:
        where.append("a.major_name_raw NOT LIKE %s")
        params.append(pattern)


def _fallback_any_major_stage() -> dict[str, Any]:
    return {
        "stage": 5,
        "label": "去除专业限制",
        "strategy": "any_major",
        "include_patterns": [],
        "exclude_patterns": [],
    }


def _major_relaxation_stages(
    constraints: dict[str, Any],
    *,
    major_tree_path: str | Path | None,
) -> list[dict[str, Any]]:
    major = constraints.get("major")
    if not major:
        return [_fallback_any_major_stage()]
    tree_path = Path(major_tree_path or DEFAULT_MAJOR_TREE_PATH)
    if not tree_path.exists():
        return [_fallback_any_major_stage()]
    try:
        stages = build_relaxation_stages(
            str(major),
            path=tree_path,
            include_any_major_stage=True,
        )
    except Exception:
        return [_fallback_any_major_stage()]
    return stages or [_fallback_any_major_stage()]


def _selection_key(row: dict[str, Any]) -> tuple[Any, ...]:
    ranking = row.get("ranking")
    min_score = row.get("min_score")
    return (
        -int(row.get("year") or 0),
        -int(row.get("tier") or 0),
        int(ranking) if ranking is not None else 999999,
        -float(min_score) if min_score is not None else 0.0,
        str(row.get("school_name") or ""),
        str(row.get("major_name") or ""),
    )


def _visible_option_key(row: dict[str, Any]) -> tuple[Any, Any, Any]:
    return (
        row.get("school_id") or row.get("school_name"),
        row.get("major_id") or row.get("major_name"),
        row.get("major_name"),
    )


def _dedupe_visible_options(
    rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    seen: set[tuple[Any, Any, Any]] = set()
    for row in rows:
        option_key = _visible_option_key(row)
        if option_key in seen:
            continue
        seen.add(option_key)
        selected.append(row)
    return selected


def _flatten_probe_rows(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, list):
        return [row for row in value if isinstance(row, dict)]
    if isinstance(value, dict):
        rows: list[dict[str, Any]] = []
        for nested in value.values():
            rows.extend(_flatten_probe_rows(nested))
        return rows
    return []


def _select_relaxation_rows(
    rows: list[dict[str, Any]],
    *,
    limit: int,
    max_per_school: int,
) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    seen_options: set[tuple[Any, Any]] = set()
    school_counts: dict[Any, int] = {}
    for row in sorted(rows, key=_selection_key):
        option_key = (
            row.get("school_id"),
            row.get("major_id") or row.get("major_name"),
        )
        if option_key in seen_options:
            continue
        school_key = row.get("school_id") or row.get("school_name")
        if school_counts.get(school_key, 0) >= max_per_school:
            continue
        seen_options.add(option_key)
        school_counts[school_key] = school_counts.get(school_key, 0) + 1
        selected.append(row)
        if len(selected) >= limit:
            break
    return selected


def _outcome_sort_key(row: dict[str, Any]) -> tuple[Any, ...]:
    score = row.get("outcome_score")
    rank = row.get("employment_rank")
    return (
        -float(score) if score is not None else 0.0,
        int(rank) if rank is not None else 999999,
        -int(row.get("tier") or 0),
        int(row.get("ranking") or 999999),
        -int(row.get("year") or 0),
        str(row.get("school_name") or ""),
        str(row.get("major_name") or ""),
    )


async def run_baseline(
    constraints: dict[str, Any],
    db: Any = None,
    limit: int = 3,
) -> list[dict[str, Any]]:
    where, params = _where_common(constraints)
    _add_province_filter(where, params, constraints)
    _add_city_filter(where, params, constraints)
    _add_major_filter(where, params, constraints)
    params.append(limit)

    query = f"{BASE_SELECT}\nWHERE {' AND '.join(where)}\n{BASE_ORDER}"
    return await _fetch(db, query, params)


def _risk_bucket_from_rank_ratio(ratio: float | None) -> str | None:
    if ratio is None:
        return None
    for bucket, (lower, upper) in RANK_BUCKET_RANGES.items():
        if bucket == "reach":
            if lower <= ratio < upper:
                return bucket
            continue
        if lower <= ratio <= upper:
            return bucket
    return None


def _rank_ratio_for_bucket(
    row: dict[str, Any],
) -> float | None:
    student_rank = _coerce_float(row.get("student_rank"))
    min_rank = _coerce_float(row.get("min_rank"))
    if student_rank is None or student_rank <= 0 or min_rank is None:
        return None
    return min_rank / student_rank


def build_recommendation_matrix(
    ranked_candidates: list[dict[str, Any]],
    user_state: dict[str, Any] | None,
    *,
    limit_per_bucket: int = 3,
    total_limit: int | None = None,
) -> dict[str, list[dict[str, Any]]]:
    matrix: dict[str, list[dict[str, Any]]] = {
        key: [] for key in GLOBAL_BASELINE_BUCKETS
    }
    risk_relaxed = _has_accepted_relaxation(user_state or {}, "risk")
    for candidate in ranked_candidates or []:
        if not isinstance(candidate, dict):
            continue
        row = dict(candidate)
        rank_ratio = _rank_ratio_for_bucket(row)
        bucket = _risk_bucket_from_rank_ratio(rank_ratio)
        if (
            bucket is None
            and risk_relaxed
            and rank_ratio is not None
            and RANK_WINDOW_RELAXED_MIN <= rank_ratio < RANK_WINDOW_MIN
        ):
            bucket = "reach"
        if bucket is None:
            continue
        row["rank_ratio"] = round(float(rank_ratio), 4)
        row["risk_bucket"] = bucket
        row["risk_label"] = GLOBAL_BASELINE_BUCKET_LABELS[bucket]
        matrix[bucket].append(row)

    for bucket in GLOBAL_BASELINE_BUCKETS:
        matrix[bucket] = sorted(
            matrix[bucket],
            key=_lexicographic_sort_key,
            reverse=True,
        )[:limit_per_bucket]
    if total_limit is not None:
        matrix = _limit_recommendation_matrix_total(matrix, total_limit)
    return matrix


def _limit_recommendation_matrix_total(
    matrix: dict[str, list[dict[str, Any]]],
    total_limit: int,
) -> dict[str, list[dict[str, Any]]]:
    total_limit = max(0, int(total_limit))
    if total_limit <= 0:
        return {key: [] for key in GLOBAL_BASELINE_BUCKETS}
    total_count = sum(
        len(matrix.get(bucket) or []) for bucket in GLOBAL_BASELINE_BUCKETS
    )
    if total_count <= total_limit:
        return {
            bucket: list(matrix.get(bucket) or []) for bucket in GLOBAL_BASELINE_BUCKETS
        }

    base_quota = total_limit // len(GLOBAL_BASELINE_BUCKETS)
    remainder = total_limit % len(GLOBAL_BASELINE_BUCKETS)
    limited: dict[str, list[dict[str, Any]]] = {
        bucket: [] for bucket in GLOBAL_BASELINE_BUCKETS
    }
    for index, bucket in enumerate(GLOBAL_BASELINE_BUCKETS):
        quota = base_quota + (1 if index < remainder else 0)
        rows = matrix.get(bucket) or []
        limited[bucket] = list(rows[:quota])

    remaining = total_limit - sum(len(rows) for rows in limited.values())
    while remaining > 0:
        progressed = False
        for bucket in GLOBAL_BASELINE_BUCKETS:
            rows = matrix.get(bucket) or []
            if len(limited[bucket]) >= len(rows):
                continue
            limited[bucket].append(rows[len(limited[bucket])])
            remaining -= 1
            progressed = True
            if remaining <= 0:
                break
        if not progressed:
            break
    return limited


async def probe_global_baseline(
    user_state: dict[str, Any],
    db: Any = None,
    limit: int = 5,
    pool_size: int = 500,
    total_limit: int | None = None,
) -> dict[str, list[dict[str, Any]]]:
    """Search hard constraints, bucket by rank ratio, then rank by implicit utility."""

    constraints = _state_constraints(user_state)
    search_constraints = _terminal_search_constraints(constraints, user_state)
    student_rank = await _student_rank_for_score(constraints, db=db)
    if student_rank is None:
        return {key: [] for key in GLOBAL_BASELINE_BUCKETS}

    where, params = _where_common(search_constraints, include_score_ceiling=False)
    _add_province_filter(where, params, search_constraints)
    _add_city_filter(where, params, search_constraints)
    _add_major_filter(where, params, search_constraints)
    _add_undergraduate_quality_filters(where, params)
    where.extend(
        [
            "a.min_rank IS NOT NULL",
            "a.min_rank >= %s",
            "a.min_rank <= %s",
        ]
    )
    params.extend(
        [
            int(
                student_rank
                * (
                    RANK_WINDOW_RELAXED_MIN
                    if _has_accepted_relaxation(user_state, "risk")
                    else RANK_WINDOW_MIN
                )
            ),
            int(student_rank * RANK_WINDOW_MAX),
        ]
    )
    params.append(max(pool_size, limit * 10))

    query = f"{BASE_SELECT}\nWHERE {' AND '.join(where)}\n{BASE_ORDER}"
    candidates = await _fetch(db, query, params)
    candidates = [
        _annotate_terminal_relaxation_features(
            dict(row, student_rank=student_rank),
            constraints,
            user_state,
        )
        for row in candidates
    ]
    ranked = await rank_by_implicit_utility_async(candidates, user_state)
    ranked = _dedupe_visible_options(ranked)
    limit_per_bucket = (
        max(1, limit) if total_limit is not None else max(1, min(3, limit))
    )
    return build_recommendation_matrix(
        ranked,
        user_state,
        limit_per_bucket=limit_per_bucket,
        total_limit=total_limit,
    )


async def probe_comparison_baseline(
    constraints: dict[str, Any],
    db: Any = None,
    user_state: dict[str, Any] | None = None,
    limit: int = 3,
) -> list[dict[str, Any]]:
    """Return realistic display-level anchors for relaxation probes."""

    state = dict(user_state or {})
    state["constraints"] = dict(constraints)
    matrix = await probe_global_baseline(state, db=db, limit=limit)
    rows = _dedupe_visible_options(_flatten_probe_rows(matrix))
    if rows:
        return rows
    return await run_baseline(constraints, db=db, limit=limit)


async def _student_rank_for_score(
    constraints: dict[str, Any],
    *,
    db: Any = None,
) -> int | None:
    province = constraints.get("province")
    score = constraints.get("score")
    if not province or score is None:
        return None
    query = """
    SELECT rank_min, rank_max
    FROM score_rank_segments
    WHERE province = %s
      AND score_min <= %s
      AND score_max >= %s
    ORDER BY year DESC
    LIMIT 1
    """
    rows = await _fetch(db, query, [province, int(score), int(score)])
    if not rows:
        return None
    rank_value = rows[0].get("rank_max") or rows[0].get("rank_min")
    if rank_value is None:
        return None
    return int(float(rank_value))


async def probe_geo_relax(
    constraints: dict[str, Any],
    db: Any = None,
    baseline_results: list[dict[str, Any]] | None = None,
    user_state: dict[str, Any] | None = None,
    limit: int = 5,
) -> list[dict[str, Any]]:
    if constraints.get("school_region_relaxed") or constraints.get("province_relaxed"):
        return []

    baseline = baseline_results
    if baseline is None:
        baseline = await run_baseline(constraints, db=db)

    where, params = _where_common(constraints)
    _add_major_filter(where, params, constraints)

    province = constraints.get("province")
    if province:
        where.append("s.province <> %s")
        params.append(province)

    _add_higher_tier_filter(where, params, baseline)
    params.append(limit)

    query = f"{BASE_SELECT}\nWHERE {' AND '.join(where)}\n{BASE_ORDER}"
    rows = await _fetch(db, query, params)
    ranked = await rank_by_implicit_utility_async(rows, user_state or constraints)
    return ranked[:limit]


async def probe_city_relax(
    constraints: dict[str, Any],
    db: Any = None,
    baseline_results: list[dict[str, Any]] | None = None,
    user_state: dict[str, Any] | None = None,
    limit: int = 5,
) -> list[dict[str, Any]]:
    """Find tier gains unlocked by relaxing only the exact city constraint."""

    if constraints.get("school_region_relaxed") or constraints.get("province_relaxed"):
        return []

    city = constraints.get("city")
    if not city:
        return []

    baseline = baseline_results
    if baseline is None:
        baseline = await run_baseline(constraints, db=db)

    where, params = _where_common(constraints)
    _add_province_filter(where, params, constraints)
    _add_major_filter(where, params, constraints)
    where.append("s.city <> ALL(%s::text[])")
    params.append(city_variants(city))
    _add_higher_tier_filter(where, params, baseline)
    params.append(limit)

    query = f"{BASE_SELECT}\nWHERE {' AND '.join(where)}\n{BASE_ORDER}"
    rows = await _fetch(db, query, params)
    ranked = await rank_by_implicit_utility_async(rows, user_state or constraints)
    return ranked[:limit]


async def probe_region_tree_relax(
    constraints: dict[str, Any],
    db: Any = None,
    baseline_results: list[dict[str, Any]] | None = None,
    user_state: dict[str, Any] | None = None,
    limit: int = 5,
    max_per_school: int = 2,
    geo_tree_path: str | Path | None = DEFAULT_REGION_GEO_TREE_PATH,
    urban_tree_path: str | Path | None = DEFAULT_REGION_URBAN_TREE_PATH,
) -> list[dict[str, Any]]:
    """Find tier gains unlocked by reviewed region-tree relaxations."""

    if constraints.get("school_region_relaxed") or constraints.get("province_relaxed"):
        return []

    if not constraints.get("city") and not constraints.get("province"):
        return []

    baseline = baseline_results
    if baseline is None:
        baseline = await run_baseline(constraints, db=db)

    try:
        geo_tree, urban_tree = load_region_trees(
            geo_tree_path=geo_tree_path,
            urban_tree_path=urban_tree_path,
        )
    except (FileNotFoundError, ValueError, KeyError):
        return []

    targets = build_region_relax_targets(
        province=constraints.get("province"),
        city=constraints.get("city"),
        geo_tree=geo_tree,
        urban_tree=urban_tree,
    )
    if not targets:
        return []

    source_city_values = city_variants(constraints.get("city"))
    selected: list[dict[str, Any]] = []
    seen_options: set[tuple[Any, Any]] = set()
    school_counts: dict[Any, int] = {}

    for target in targets:
        target_cities = list(target.get("target_city_values") or [])
        if not target_cities:
            continue

        where, params = _where_common(constraints)
        _add_major_filter(where, params, constraints)
        _add_undergraduate_quality_filters(where, params)
        _add_major_quality_filters(where, params, max_major_name_length=60)
        where.append("s.city = ANY(%s::text[])")
        params.append(target_cities)
        if target.get("region_relax_strategy") == "geo_block_relax":
            _add_province_filter(where, params, constraints)
        if source_city_values:
            where.append("s.city <> ALL(%s::text[])")
            params.append(source_city_values)
        _add_higher_tier_filter(where, params, baseline)
        params.append(max(limit * 4, 20))

        query = f"{BASE_SELECT}\nWHERE {' AND '.join(where)}\n{BASE_ORDER}"
        rows = await _fetch(db, query, params)
        for row in rows:
            candidate = annotate_region_row(row, target)
            if not _append_unique_option(
                selected,
                candidate,
                seen_options=seen_options,
                school_counts=school_counts,
                max_per_school=max_per_school,
            ):
                continue
            if len(selected) >= limit:
                ranked = await rank_by_implicit_utility_async(
                    selected, user_state or constraints
                )
                return ranked[:limit]
    ranked = await rank_by_implicit_utility_async(selected, user_state or constraints)
    return ranked[:limit]


async def probe_strength_relax(
    constraints: dict[str, Any],
    db: Any = None,
    baseline_results: list[dict[str, Any]] | None = None,
    user_state: dict[str, Any] | None = None,
    limit: int = 5,
) -> list[dict[str, Any]]:
    """Find school-strength gains unlocked by relaxing the strength preference."""

    strength = constraints.get("strength")
    if not strength:
        return []

    anchor_where, anchor_params = _where_common(constraints)
    _add_province_filter(anchor_where, anchor_params, constraints)
    _add_major_filter(anchor_where, anchor_params, constraints)

    anchor_query = (
        f"{STRENGTH_SELECT}\n"
        f"WHERE {' AND '.join(anchor_where)}\n"
        "  AND sms.major_strength_rank IS NOT NULL\n"
        "ORDER BY\n"
        "    major_strength_rank DESC NULLS LAST,\n"
        "    tier DESC,\n"
        "    s.ranking DESC NULLS LAST,\n"
        "    a.min_score DESC NULLS LAST,\n"
        "    a.year DESC,\n"
        "    s.name ASC,\n"
        "    a.major_name_raw ASC\n"
        "LIMIT %s"
    )
    anchor_rows = await _fetch(db, anchor_query, [*anchor_params, 1])
    anchor = anchor_rows[0] if anchor_rows else None
    if not anchor or anchor.get("major_strength_rank") is None:
        return []

    anchor_rank = int(float(anchor["major_strength_rank"]))

    relaxed_where, relaxed_params = _where_common(constraints)
    _add_major_filter(relaxed_where, relaxed_params, constraints)
    _add_undergraduate_quality_filters(relaxed_where, relaxed_params)
    _add_major_quality_filters(relaxed_where, relaxed_params, max_major_name_length=60)
    relaxed_query = (
        f"{STRENGTH_SELECT}\n"
        f"WHERE {' AND '.join(relaxed_where)}\n"
        "  AND sms.major_strength_rank IS NOT NULL\n"
        "  AND sms.major_strength_rank < %s\n"
        "ORDER BY\n"
        "    major_strength_rank ASC NULLS LAST,\n"
        "    tier DESC,\n"
        "    s.ranking ASC NULLS LAST,\n"
        "    a.min_score DESC NULLS LAST,\n"
        "    a.year DESC,\n"
        "    s.name ASC,\n"
        "    a.major_name_raw ASC\n"
        "LIMIT %s"
    )
    rows = await _fetch(db, relaxed_query, [*relaxed_params, anchor_rank, limit])
    selected: list[dict[str, Any]] = []
    for row in rows:
        if row.get("major_strength_rank") is None:
            continue
        candidate_rank = int(float(row["major_strength_rank"]))
        if candidate_rank >= anchor_rank:
            continue
        selected.append(row)
    ranked = await rank_by_implicit_utility_async(selected, user_state or constraints)
    return ranked[:limit]


async def probe_major_quality_relax(
    constraints: dict[str, Any],
    db: Any = None,
    baseline_results: list[dict[str, Any]] | None = None,
    user_state: dict[str, Any] | None = None,
    limit: int = 5,
    min_quality_gain: int = 10,
) -> list[dict[str, Any]]:
    """Find same-major options with stronger school-major quality evidence."""

    strength = constraints.get("strength")
    if not strength:
        return []

    anchor_where, anchor_params = _where_common(constraints)
    _add_province_filter(anchor_where, anchor_params, constraints)
    _add_major_filter(anchor_where, anchor_params, constraints)
    anchor_query = (
        f"{MAJOR_QUALITY_SELECT}\n"
        f"WHERE {' AND '.join(anchor_where)}\n"
        "  AND mq.quality_score IS NOT NULL\n"
        "ORDER BY\n"
        "    mq.quality_score DESC NULLS LAST,\n"
        "    mq.best_major_rank ASC NULLS LAST,\n"
        "    tier DESC,\n"
        "    s.ranking ASC NULLS LAST,\n"
        "    a.min_score DESC NULLS LAST,\n"
        "    a.year DESC,\n"
        "    s.name ASC,\n"
        "    a.major_name_raw ASC\n"
        "LIMIT %s"
    )
    anchor_rows = await _fetch(db, anchor_query, [*anchor_params, 1])
    anchor = anchor_rows[0] if anchor_rows else None
    anchor_score = float(anchor.get("quality_score") or 0) if anchor else 0.0

    relaxed_where, relaxed_params = _where_common(constraints)
    _add_major_filter(relaxed_where, relaxed_params, constraints)
    _add_undergraduate_quality_filters(relaxed_where, relaxed_params)
    _add_major_quality_filters(relaxed_where, relaxed_params, max_major_name_length=60)
    province = constraints.get("province")
    if province:
        relaxed_where.append("s.province <> %s")
        relaxed_params.append(province)
    relaxed_where.extend(
        [
            "mq.quality_score IS NOT NULL",
            "mq.quality_score >= %s",
        ]
    )
    relaxed_params.extend([anchor_score + min_quality_gain, max(limit * 4, 20)])
    relaxed_query = (
        f"{MAJOR_QUALITY_SELECT}\n"
        f"WHERE {' AND '.join(relaxed_where)}\n"
        "ORDER BY\n"
        "    mq.quality_score DESC NULLS LAST,\n"
        "    mq.best_major_rank ASC NULLS LAST,\n"
        "    tier DESC,\n"
        "    s.ranking ASC NULLS LAST,\n"
        "    a.min_score DESC NULLS LAST,\n"
        "    a.year DESC,\n"
        "    s.name ASC,\n"
        "    a.major_name_raw ASC\n"
        "LIMIT %s"
    )
    rows = await _fetch(db, relaxed_query, relaxed_params)
    selected: list[dict[str, Any]] = []
    seen_options: set[tuple[Any, Any]] = set()
    for row in rows:
        quality_score = row.get("quality_score")
        if quality_score is None:
            continue
        candidate = dict(row)
        candidate["quality_score"] = float(quality_score)
        candidate["quality_gain"] = round(candidate["quality_score"] - anchor_score, 3)
        candidate["quality_anchor_score"] = round(anchor_score, 3)
        if anchor:
            candidate["quality_anchor_school"] = anchor.get("school_name")
            candidate["quality_anchor_major"] = anchor.get("major_name")
        option_key = (
            candidate.get("school_id"),
            candidate.get("major_id") or candidate.get("major_name"),
        )
        if option_key in seen_options:
            continue
        seen_options.add(option_key)
        selected.append(candidate)
        if len(selected) >= limit:
            break
    ranked = await rank_by_implicit_utility_async(selected, user_state or constraints)
    return ranked[:limit]


async def probe_tuition_value_relax(
    constraints: dict[str, Any],
    db: Any = None,
    baseline_results: list[dict[str, Any]] | None = None,
    user_state: dict[str, Any] | None = None,
    limit: int = 5,
    budget_window: int = 10000,
) -> list[dict[str, Any]]:
    """Find value gains unlocked by a small tuition-budget relaxation."""

    budget = _budget(constraints)
    if budget is None:
        return []

    baseline = baseline_results
    if baseline is None:
        baseline = await run_baseline(constraints, db=db)
    if not baseline:
        return []

    value_anchor = [
        row
        for row in baseline
        if row.get("ranking") is not None
        and row.get("tuition") is not None
        and str(row.get("education_level") or "") == "本科"
    ]
    if not value_anchor:
        value_anchor = await _tuition_value_anchor(
            constraints,
            db=db,
            budget=budget,
            limit=max(3, limit),
        )
    if not value_anchor:
        value_anchor = baseline

    relaxed_constraints = dict(constraints)
    relaxed_constraints["budget"] = None
    where, params = _where_common(relaxed_constraints)
    _add_province_filter(where, params, constraints)
    _add_city_filter(where, params, constraints)
    _add_major_filter(where, params, constraints)
    _add_undergraduate_quality_filters(where, params)
    _add_major_quality_filters(where, params, max_major_name_length=60)
    where.extend(
        [
            "plan.min_tuition IS NOT NULL",
            "s.ranking IS NOT NULL",
            "plan.min_tuition > %s",
            "plan.min_tuition <= %s",
        ]
    )
    params.extend([budget, budget + budget_window])

    improvement_clauses = [f"{_tier_sql()} > %s"]
    params.append(_max_tier(value_anchor))
    best_ranking = _best_ranking(value_anchor)
    if best_ranking is not None:
        improvement_clauses.append("s.ranking IS NOT NULL AND s.ranking <= %s")
        params.append(best_ranking - 50)
    where.append("(" + " OR ".join(improvement_clauses) + ")")
    params.append(max(limit * 4, 20))

    query = (
        f"{BASE_SELECT}\n"
        f"WHERE {' AND '.join(where)}\n"
        "ORDER BY\n"
        "    s.ranking ASC NULLS LAST,\n"
        "    tier DESC,\n"
        "    plan.min_tuition ASC NULLS LAST,\n"
        "    a.min_score DESC NULLS LAST,\n"
        "    a.year DESC,\n"
        "    s.name ASC,\n"
        "    a.major_name_raw ASC\n"
        "LIMIT %s"
    )
    rows = await _fetch(db, query, params)
    selected: list[dict[str, Any]] = []
    seen_options: set[tuple[Any, Any]] = set()
    for row in rows:
        tuition = row.get("tuition")
        if tuition is None:
            continue
        candidate = dict(row)
        candidate["tuition"] = int(float(tuition))
        candidate["tuition_delta"] = candidate["tuition"] - budget
        option_key = (
            candidate.get("school_id"),
            candidate.get("major_id") or candidate.get("major_name"),
        )
        if option_key in seen_options:
            continue
        seen_options.add(option_key)
        selected.append(candidate)
        if len(selected) >= limit:
            break
    ranked = await rank_by_implicit_utility_async(selected, user_state or constraints)
    return ranked[:limit]


async def probe_employment_outcome_relax(
    constraints: dict[str, Any],
    db: Any = None,
    baseline_results: list[dict[str, Any]] | None = None,
    user_state: dict[str, Any] | None = None,
    limit: int = 5,
    min_outcome_gain: int = 10,
    major_tree_path: str | Path | None = DEFAULT_MAJOR_TREE_PATH,
    max_per_school: int = 2,
) -> list[dict[str, Any]]:
    """Find reachable options with stronger employment outcome evidence."""

    if not constraints.get("employment_preference"):
        return []

    anchor_where, anchor_params = _where_common(constraints)
    _add_province_filter(anchor_where, anchor_params, constraints)
    _add_major_filter(anchor_where, anchor_params, constraints)
    anchor_query = (
        f"{EMPLOYMENT_OUTCOME_SELECT}\n"
        f"WHERE {' AND '.join(anchor_where)}\n"
        "  AND me.outcome_score IS NOT NULL\n"
        "ORDER BY\n"
        "    me.outcome_score DESC NULLS LAST,\n"
        "    me.employment_rank ASC NULLS LAST,\n"
        "    tier DESC,\n"
        "    s.ranking ASC NULLS LAST,\n"
        "    a.min_score DESC NULLS LAST,\n"
        "    a.year DESC,\n"
        "    s.name ASC,\n"
        "    a.major_name_raw ASC\n"
        "LIMIT %s"
    )
    anchor_rows = await _fetch(db, anchor_query, [*anchor_params, 1])
    anchor = anchor_rows[0] if anchor_rows else None
    anchor_score = float(anchor.get("outcome_score") or 0) if anchor else 0.0

    selected: list[dict[str, Any]] = []
    seen_options: set[tuple[Any, Any]] = set()
    school_counts: dict[Any, int] = {}
    selection_limit = max(limit * 4, 20)
    for stage in _major_relaxation_stages(
        constraints,
        major_tree_path=major_tree_path,
    ):
        relaxed_where, relaxed_params = _where_common(constraints)
        _add_undergraduate_quality_filters(relaxed_where, relaxed_params)
        _add_major_quality_filters(
            relaxed_where,
            relaxed_params,
            max_major_name_length=60,
        )
        _add_stage_major_filters(
            relaxed_where,
            relaxed_params,
            stage=stage,
            strict_major=constraints.get("major"),
        )
        province = constraints.get("province")
        if province:
            relaxed_where.append("s.province <> %s")
            relaxed_params.append(province)
        relaxed_where.extend(
            [
                "me.outcome_score IS NOT NULL",
                "me.outcome_score >= %s",
            ]
        )
        relaxed_params.extend([anchor_score + min_outcome_gain, selection_limit])
        relaxed_query = (
            f"{EMPLOYMENT_OUTCOME_SELECT}\n"
            f"WHERE {' AND '.join(relaxed_where)}\n"
            "ORDER BY\n"
            "    me.outcome_score DESC NULLS LAST,\n"
            "    me.employment_rank ASC NULLS LAST,\n"
            "    tier DESC,\n"
            "    s.ranking ASC NULLS LAST,\n"
            "    a.min_score DESC NULLS LAST,\n"
            "    a.year DESC,\n"
            "    s.name ASC,\n"
            "    a.major_name_raw ASC\n"
            "LIMIT %s"
        )
        rows = await _fetch(db, relaxed_query, relaxed_params)
        for row in sorted(rows, key=_outcome_sort_key):
            outcome_score = row.get("outcome_score")
            if outcome_score is None:
                continue
            candidate = dict(row)
            candidate["outcome_score"] = float(outcome_score)
            candidate["outcome_gain"] = round(
                candidate["outcome_score"] - anchor_score,
                3,
            )
            candidate["outcome_anchor_score"] = round(anchor_score, 3)
            if anchor:
                candidate["outcome_anchor_school"] = anchor.get("school_name")
                candidate["outcome_anchor_major"] = anchor.get("major_name")
            candidate["relaxation_stage"] = stage.get("stage")
            candidate["relaxation_stage_label"] = stage.get("label")
            candidate["relaxation_strategy"] = stage.get("strategy")
            if not _append_unique_option(
                selected,
                candidate,
                seen_options=seen_options,
                school_counts=school_counts,
                max_per_school=max_per_school,
            ):
                continue
            if len(selected) >= limit:
                ranked = await rank_by_implicit_utility_async(
                    selected,
                    user_state or constraints,
                )
                return ranked[:limit]
        if selected:
            break
    ranked = await rank_by_implicit_utility_async(selected, user_state or constraints)
    return ranked[:limit]


async def probe_major_relax(
    constraints: dict[str, Any],
    db: Any = None,
    baseline_results: list[dict[str, Any]] | None = None,
    user_state: dict[str, Any] | None = None,
    limit: int = 5,
) -> list[dict[str, Any]]:
    baseline = baseline_results
    if baseline is None:
        baseline = await run_baseline(constraints, db=db)

    where, params = _where_common(constraints)
    _add_province_filter(where, params, constraints)

    major = constraints.get("major")
    if major:
        where.append("a.major_name_raw NOT LIKE %s")
        params.append(f"%{major}%")

    _add_higher_tier_filter(where, params, baseline)
    params.append(limit)

    query = f"{BASE_SELECT}\nWHERE {' AND '.join(where)}\n{BASE_ORDER}"
    rows = await _fetch(db, query, params)
    ranked = await rank_by_implicit_utility_async(rows, user_state or constraints)
    return ranked[:limit]


async def probe_major_geo_relax(
    constraints: dict[str, Any],
    db: Any = None,
    baseline_results: list[dict[str, Any]] | None = None,
    user_state: dict[str, Any] | None = None,
    limit: int = 5,
    recommendation_threshold: int = 10,
    max_per_school: int = 2,
    major_tree_path: str | Path | None = DEFAULT_MAJOR_TREE_PATH,
    max_major_name_length: int | None = 60,
) -> list[dict[str, Any]]:
    """Find tier gains unlocked by relaxing both province and major constraints."""

    baseline = baseline_results
    if baseline is None:
        baseline = await run_baseline(constraints, db=db)

    selection_limit = max(limit, recommendation_threshold)
    selected: list[dict[str, Any]] = []
    for stage in _major_relaxation_stages(
        constraints,
        major_tree_path=major_tree_path,
    ):
        where, params = _where_common(constraints)
        _add_undergraduate_quality_filters(where, params)
        _add_major_quality_filters(
            where,
            params,
            max_major_name_length=max_major_name_length,
        )
        _add_stage_major_filters(
            where,
            params,
            stage=stage,
            strict_major=constraints.get("major"),
        )
        _add_school_gain_filter(where, params, baseline)
        params.append(max(selection_limit * 4, 40))

        query = f"{BASE_SELECT}\nWHERE {' AND '.join(where)}\n{MAJOR_GEO_ORDER}"
        rows = await _fetch(db, query, params)
        selected = _select_relaxation_rows(
            rows,
            limit=selection_limit,
            max_per_school=max_per_school,
        )
        if len(selected) < recommendation_threshold:
            selected = []
            continue
        if selected:
            for row in selected:
                row["relaxation_stage"] = stage.get("stage")
                row["relaxation_stage_label"] = stage.get("label")
                row["relaxation_strategy"] = stage.get("strategy")
                annotated = _annotate_major_geo_probe_features(row, constraints, stage)
                row.update(annotated)
            break

    ranked = await rank_by_implicit_utility_async(selected, user_state or constraints)
    return ranked[:limit]


async def probe_risk_band_relax(
    constraints: dict[str, Any],
    db: Any = None,
    user_state: dict[str, Any] | None = None,
    limit: int = 6,
    max_per_school: int = 2,
) -> list[dict[str, Any]]:
    """Find a chong/wen/bao portfolio under existing hard constraints."""

    risk_preference = str(constraints.get("risk_preference") or "").lower()
    include_aggressive = risk_preference in {
        "",
        "none",
        "null",
        "conservative",
        "low",
        "stable",
    }
    if not include_aggressive:
        return []

    score = _score(constraints)
    student_rank = await _student_rank_for_score(constraints, db=db)
    where, params = _where_common(constraints, include_score_ceiling=False)
    _add_province_filter(where, params, constraints)
    _add_major_filter(where, params, constraints)
    _add_undergraduate_quality_filters(where, params)
    _add_major_quality_filters(where, params, max_major_name_length=60)
    if student_rank is not None:
        where.extend(
            [
                "a.min_rank IS NOT NULL",
                "a.min_rank >= %s",
                "a.min_rank <= %s",
            ]
        )
        params.extend(
            [
                int(student_rank * RANK_WINDOW_MIN),
                int(student_rank * RANK_WINDOW_MAX),
            ]
        )
    params.append(max(limit * 8, 60))

    query = f"{BASE_SELECT}\nWHERE {' AND '.join(where)}\n{MAJOR_GEO_ORDER}"
    rows = await _fetch(db, query, params)
    annotated = [
        _annotate_risk_row(row, score=score, student_rank=student_rank) for row in rows
    ]
    annotated = [
        row
        for row in annotated
        if str(row.get("risk_level") or "") in {"chong", "wen", "bao"}
        and _is_material_risk_relaxation(row)
    ]
    selected = _select_risk_portfolio(
        annotated,
        limit=limit,
        max_per_school=max_per_school,
    )
    for row in selected:
        row["risk_relax_level"] = 1
    ranked = await rank_by_implicit_utility_async(selected, user_state or constraints)
    ranked_by_key = {_visible_option_key(row): row for row in ranked}
    return [ranked_by_key.get(_visible_option_key(row), row) for row in selected][
        :limit
    ]


async def run_all_probes(
    constraints: dict[str, Any],
    db: Any = None,
    user_state: dict[str, Any] | None = None,
) -> dict[str, list[dict[str, Any]]]:
    constraints = _apply_accepted_relaxations(dict(constraints), user_state)
    if isinstance(user_state, dict):
        user_state = {**user_state, "constraints": constraints}
    baseline = await probe_comparison_baseline(
        constraints,
        db=db,
        user_state=user_state or constraints,
    )
    (
        geo_relax,
        city_relax,
        major_relax,
        strength_relax,
        major_quality_relax,
        tuition_value_relax,
        employment_outcome_relax,
        region_tree_relax,
        major_geo_relax,
        risk_band_relax,
    ) = await asyncio.gather(
        probe_geo_relax(
            constraints,
            db=db,
            baseline_results=baseline,
            user_state=user_state or constraints,
        ),
        probe_city_relax(
            constraints,
            db=db,
            baseline_results=baseline,
            user_state=user_state or constraints,
        ),
        probe_major_relax(
            constraints,
            db=db,
            baseline_results=baseline,
            user_state=user_state or constraints,
        ),
        probe_strength_relax(
            constraints,
            db=db,
            baseline_results=baseline,
            user_state=user_state or constraints,
        ),
        probe_major_quality_relax(
            constraints,
            db=db,
            baseline_results=baseline,
            user_state=user_state or constraints,
        ),
        probe_tuition_value_relax(
            constraints,
            db=db,
            baseline_results=baseline,
            user_state=user_state or constraints,
        ),
        probe_employment_outcome_relax(
            constraints,
            db=db,
            baseline_results=baseline,
            user_state=user_state or constraints,
        ),
        probe_region_tree_relax(
            constraints,
            db=db,
            baseline_results=baseline,
            user_state=user_state or constraints,
        ),
        probe_major_geo_relax(
            constraints,
            db=db,
            baseline_results=baseline,
            user_state=user_state or constraints,
        ),
        probe_risk_band_relax(
            constraints,
            db=db,
            user_state=user_state or constraints,
        ),
    )
    return {
        "geo_relax": geo_relax,
        "city_relax": city_relax,
        "major_relax": major_relax,
        "strength_relax": strength_relax,
        "major_quality_relax": major_quality_relax,
        "tuition_value_relax": tuition_value_relax,
        "employment_outcome_relax": employment_outcome_relax,
        "region_tree_relax": region_tree_relax,
        "major_geo_relax": major_geo_relax,
        "risk_band_relax": risk_band_relax,
    }


if __name__ == "__main__":
    mock_user_state = {
        "constraints": {"budget": 10000},
        "implicit_weights": DEFAULT_IMPLICIT_WEIGHTS,
    }
    mock_candidates = [
        {
            "school_name": "高性价比一本大学",
            "school_tier": "一本重点",
            "major_name": "计算机科学与技术",
            "major_relax_level": 0,
            "geo_relax_level": 0,
            "quality_score": 75,
            "tuition": "8000元/年",
        },
        {
            "school_name": "幽灵陷阱C9大学",
            "school_tier": "C9",
            "major_name": "计算机科学与技术",
            "major_relax_level": 0,
            "geo_relax_level": 0,
            "quality_score": 95,
            "tuition": "15000元/年",
        },
    ]
    for row in rank_by_implicit_utility(mock_candidates, mock_user_state):
        print(
            row.get("school_name"),
            "utility=",
            round(row.get("_implicit_utility", 0.0), 4),
            "tuition_phi=",
            row.get("_phi_features", {}).get("tuition"),
        )
