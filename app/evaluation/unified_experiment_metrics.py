"""Summarize unified iceberg baseline and ablation benchmark outputs."""

from __future__ import annotations

import argparse
import csv
import json
import math
import re
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable

from gaokaollm_bench.evaluator.candidate_set_oracle import (
    default_acceptable_probe_dims,
    default_acceptable_probe_keys,
    valid_probe_metrics_from_turns,
)
from gaokaollm_bench.schemas import UnifiedIcebergCase
from app.evaluation.reference_baselines import (
    _geo_signal,
    _major_signal,
    _quality_signal,
    _risk_signal,
    _school_signal,
    _tuition_signal,
    infer_weights_from_v1_candidates,
)


DIMENSIONS = ("school", "major", "tuition", "quality", "geo", "risk")
RECOMMENDATION_TOP_N = 3
RECOMMENDATION_TOP_NS = (1, 3, 5, 10)
STATIC_RECALL_FIELDS = (
    "second_stage_reranked_candidates",
    "soft_retrieval_candidates",
    "baseline_results",
    "recommended_schools",
)
APP_RECALL_FIELDS = (
    "recommended_schools",
    "final_recommendations",
    "recommendations",
    "second_stage_reranked_candidates",
    "soft_retrieval_candidates",
    "baseline_results",
)
TARGET_TO_MODE = {
    "app_pareto": "full",
    "app_pareto_full": "full",
    "app_pareto_no_ucb": "no_ucb",
    "app_pareto_no_tracker": "no_tracker",
}
TRANSCRIPT_DIAGNOSTIC_FIELDS = (
    "target_turn_count",
    "echo_rate",
    "probe_question_rate",
    "pareto_diff_rate",
    "uniform_weight_rate",
    "constant_variance_rate",
    "golden_first_mention_role",
    "golden_first_mention_turn",
    "golden_first_mention_school",
    "target_supplied_golden_evidence",
    "target_golden_evidence_count",
    "golden_echo_target_count",
    "acceptable_candidate_count",
    "acceptable_candidate_hit",
    "acceptable_candidate_hit_ids",
    "acceptable_first_mention_role",
    "acceptable_first_mention_turn",
    "acceptable_first_mention_school",
    "target_supplied_acceptable_evidence",
    "target_acceptable_evidence_count",
    "acceptable_echo_target_count",
    "exact_golden_hit",
)
DEFAULT_CASES = Path(
    "gaokaollm_bench/sample_data/unified_iceberg_cases_1c6c_real_db_180.jsonl"
)
DEFAULT_BASELINE_ROOT = Path("gaokaollm_bench/outputs/unified_baseline_arena")
DEFAULT_ABLATION_ROOT = Path("gaokaollm_bench/outputs/unified_ablation_arena")
DEFAULT_RESULTS_DIR = Path("app/evaluation/results")
MODEL_ALIASES = {
    "Pro/zai-org/GLM-5.1": "GLM-5.1",
    "glm-5.1": "GLM-5.1",
    "Pro/deepseek-ai/DeepSeek-V3.2": "DeepSeek-V3.2",
    "deepseek-v3.2": "DeepSeek-V3.2",
    "Pro/MiniMaxAI/MiniMax-M2.5": "MiniMax-M2.5",
    "MiniMax-M2.5": "MiniMax-M2.5",
    "Pro/moonshotai/Kimi-K2.6": "Kimi-K2.6",
    "kimi-k2.6": "Kimi-K2.6",
    "Qwen/Qwen3.6-35B-A3B": "Qwen3.6",
    "qwen3.6-plus": "Qwen3.6",
}


def model_alias(model: Any) -> str:
    value = str(model or "")
    return MODEL_ALIASES.get(value, value)


def read_cases(path: str | Path) -> dict[str, UnifiedIcebergCase]:
    cases: dict[str, UnifiedIcebergCase] = {}
    with Path(path).open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            case = UnifiedIcebergCase.model_validate(json.loads(line))
            cases[case.case_id] = case
    return cases


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def iter_run_dirs(root: str | Path) -> Iterable[tuple[Path, dict[str, Any]]]:
    base = Path(root)
    if not base.exists():
        return
    seen: set[Path] = set()
    for meta_path in sorted(base.glob("**/run_meta.json")):
        if meta_path in seen:
            continue
        seen.add(meta_path)
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        yield meta_path.parent, meta


def read_transcript(path_value: Any) -> dict[str, Any] | None:
    if not path_value:
        return None
    path = Path(str(path_value))
    if not path.exists():
        return None
    try:
        parsed = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return parsed if isinstance(parsed, dict) else None


def numeric_map(value: Any) -> dict[str, float]:
    if not isinstance(value, dict):
        return {}
    result: dict[str, float] = {}
    for key, raw in value.items():
        try:
            result[str(key)] = float(raw)
        except (TypeError, ValueError):
            continue
    return result


def mean(values: Iterable[float]) -> float:
    items = [value for value in values if math.isfinite(value)]
    return sum(items) / len(items) if items else 0.0


def std(values: Iterable[float]) -> float:
    items = [value for value in values if math.isfinite(value)]
    if len(items) <= 1:
        return 0.0
    avg = sum(items) / len(items)
    return math.sqrt(sum((value - avg) ** 2 for value in items) / (len(items) - 1))


def f1_score(predicted: set[str], gold: set[str]) -> float:
    if not predicted and not gold:
        return 1.0
    if not predicted or not gold:
        return 0.0
    tp = len(predicted & gold)
    precision = tp / len(predicted) if predicted else 0.0
    recall = tp / len(gold) if gold else 0.0
    if precision + recall == 0:
        return 0.0
    return 2 * precision * recall / (precision + recall)


def topk_f1(weights: dict[str, float], gold_dims: list[str]) -> float:
    gold = {dim for dim in gold_dims if dim in DIMENSIONS}
    if not gold:
        return 0.0
    ordered = sorted(DIMENSIONS, key=lambda dim: (-float(weights.get(dim, 0.0)), dim))
    predicted = set(ordered[: len(gold)])
    return f1_score(predicted, gold)


def normalize_text(value: Any) -> str:
    return re.sub(r"\s+", "", str(value or "")).lower()


def candidate_school(row: dict[str, Any]) -> str:
    return str(row.get("school_name") or row.get("school") or row.get("学校") or "")


def candidate_major(row: dict[str, Any]) -> str:
    return str(row.get("major_name") or row.get("major") or row.get("专业") or "")


def candidate_identity_keys(row: dict[str, Any]) -> set[str]:
    keys: set[str] = set()
    if not isinstance(row, dict):
        return keys
    candidate_id = str(row.get("candidate_id") or "").strip()
    if candidate_id:
        keys.add(f"id:{candidate_id}")
    school_id = row.get("school_id")
    major_id = row.get("major_id")
    if school_id not in (None, "") and major_id not in (None, ""):
        keys.add(f"ids:{school_id}:{major_id}")
    school = normalize_text(candidate_school(row))
    major = normalize_text(candidate_major(row))
    if school and major:
        keys.add(f"name:{school}:{major}")
    return keys


def primary_candidate_key(row: dict[str, Any]) -> str:
    keys = candidate_identity_keys(row)
    for prefix in ("name:", "ids:", "id:"):
        selected = sorted(key for key in keys if key.startswith(prefix))
        if selected:
            return selected[0]
    return json.dumps(row, ensure_ascii=False, sort_keys=True)


def acceptable_candidates(case: UnifiedIcebergCase) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for source in (
        case.acceptable_candidates,
        case.volunteer_set,
        [case.golden_candidate_b],
    ):
        for row in source or []:
            if isinstance(row, dict):
                rows.append(dict(row))
    deduped: list[dict[str, Any]] = []
    seen: set[str] = set()
    for row in rows:
        key = primary_candidate_key(row)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(row)
    return deduped


def state_candidate_list(state: dict[str, Any]) -> list[dict[str, Any]]:
    for key in (
        "recommended_schools",
        "final_recommendations",
        "recommendations",
        "second_stage_reranked_candidates",
        "soft_retrieval_candidates",
        "candidates",
        "baseline_results",
    ):
        value = state.get(key)
        if isinstance(value, list):
            cleaned = [dict(row) for row in value if isinstance(row, dict)]
            if cleaned:
                return cleaned
    return []


def state_candidate_pool(state: dict[str, Any]) -> list[dict[str, Any]]:
    rows = state_candidate_list(state)
    opportunities = state.get("pareto_opportunities")
    if isinstance(opportunities, dict):
        for value in opportunities.values():
            if isinstance(value, list):
                rows.extend(dict(row) for row in value if isinstance(row, dict))
    return rows


def final_recommendations_from_transcript(
    transcript: dict[str, Any] | None,
    *,
    limit: int = RECOMMENDATION_TOP_N,
) -> list[dict[str, Any]]:
    for turn in reversed(target_turns(transcript)):
        rows = state_candidate_list(turn.get("internal_state") or {})
        if not rows:
            continue
        deduped: list[dict[str, Any]] = []
        seen: set[str] = set()
        for row in rows:
            key = primary_candidate_key(row)
            if key in seen:
                continue
            seen.add(key)
            deduped.append(row)
            if len(deduped) >= limit:
                break
        return deduped
    return []


def dedupe_candidate_rows(rows: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    seen: set[str] = set()
    for row in rows:
        if not isinstance(row, dict):
            continue
        key = primary_candidate_key(row)
        if key in seen:
            continue
        seen.add(key)
        output.append(row)
    return output


def collect_candidate_pools(
    *,
    roots: list[Path],
    cases: dict[str, UnifiedIcebergCase],
) -> dict[str, list[dict[str, Any]]]:
    pools: dict[str, list[dict[str, Any]]] = {
        case_id: [case.baseline_candidate_a, *acceptable_candidates(case)]
        for case_id, case in cases.items()
    }
    for root in roots:
        for run_dir, meta in iter_run_dirs(root):
            target = str(meta.get("target") or "")
            report_path = run_dir / "reports" / f"{target}.jsonl"
            for report in read_jsonl(report_path):
                case_id = str(report.get("case_id") or "")
                if case_id not in cases:
                    continue
                transcript = read_transcript(report.get("transcript_path"))
                for turn in target_turns(transcript):
                    pools.setdefault(case_id, []).extend(
                        state_candidate_pool(turn.get("internal_state") or {})
                    )
    return {case_id: dedupe_candidate_rows(rows) for case_id, rows in pools.items()}


def candidate_feature_vector(row: dict[str, Any], query_text: str) -> dict[str, float]:
    phi = row.get("_phi_features")
    if isinstance(phi, dict):
        values = numeric_map(phi)
        if all(dim in values for dim in DIMENSIONS):
            return {dim: float(values.get(dim, 0.0)) for dim in DIMENSIONS}
    return {
        "school": _school_signal(row),
        "major": _major_signal(row, query_text),
        "tuition": _tuition_signal(row, query_text),
        "quality": _quality_signal(row),
        "geo": _geo_signal(row, query_text),
        "risk": _risk_signal(row),
    }


def candidate_utility(
    row: dict[str, Any],
    weights: dict[str, float],
    query_text: str,
) -> float:
    features = candidate_feature_vector(row, query_text)
    return sum(
        float(weights.get(dim, 0.0)) * float(features.get(dim, 0.0))
        for dim in DIMENSIONS
    )


def top_recommendation_keys(
    rows: list[dict[str, Any]],
    weights: dict[str, float],
    query_text: str,
    *,
    limit: int,
) -> set[str]:
    ordered = sorted(
        dedupe_candidate_rows(rows),
        key=lambda row: (
            -candidate_utility(row, weights, query_text),
            primary_candidate_key(row),
        ),
    )
    return {primary_candidate_key(row) for row in ordered[: max(1, limit)]}


def recommendation_set_metrics(
    weights: dict[str, float],
    case: UnifiedIcebergCase,
    candidate_pool: list[dict[str, Any]],
    *,
    limit: int = RECOMMENDATION_TOP_N,
) -> dict[str, Any]:
    pool = dedupe_candidate_rows(
        [
            case.baseline_candidate_a,
            *acceptable_candidates(case),
            *(candidate_pool or []),
        ]
    )
    predicted = top_recommendation_keys(
        pool,
        weights or {dim: 1.0 / len(DIMENSIONS) for dim in DIMENSIONS},
        case.initial_utterance,
        limit=limit,
    )
    gold = top_recommendation_keys(
        pool,
        case.ground_truth_weights,
        case.initial_utterance,
        limit=limit,
    )
    matched = predicted & gold
    precision = len(matched) / len(predicted) if predicted else 0.0
    recall = len(matched) / len(gold) if gold else 0.0
    score = (
        0.0
        if precision + recall == 0
        else 2 * precision * recall / (precision + recall)
    )
    return {
        f"recommendation_precision_at_{limit}": precision,
        f"recommendation_recall_at_{limit}": recall,
        f"recommendation_f1_at_{limit}": score,
        f"recommendation_hit_at_{limit}": bool(matched),
        f"recommendation_match_count_at_{limit}": len(matched),
        "recommendation_count": len(predicted),
        "reference_recommendation_count": len(gold),
        "candidate_pool_size": len(pool),
        f"recommendation_matched_ids_at_{limit}": ",".join(sorted(matched)),
    }


def recommendation_set_metrics_for_limits(
    weights: dict[str, float],
    case: UnifiedIcebergCase,
    candidate_pool: list[dict[str, Any]],
    *,
    limits: Iterable[int] = RECOMMENDATION_TOP_NS,
) -> dict[str, Any]:
    output: dict[str, Any] = {}
    for limit in limits:
        output.update(
            recommendation_set_metrics(
                weights,
                case,
                candidate_pool,
                limit=int(limit),
            )
        )
    return output


def ordered_candidate_rows_from_state(
    state: dict[str, Any], target: str
) -> list[dict[str, Any]]:
    fields = STATIC_RECALL_FIELDS if target.startswith("v1_") else APP_RECALL_FIELDS
    for key in fields:
        value = state.get(key)
        if isinstance(value, list):
            cleaned = [dict(row) for row in value if isinstance(row, dict)]
            if cleaned:
                return dedupe_candidate_rows(cleaned)
    return []


def first_recall_rows_from_transcript(
    transcript: dict[str, Any] | None,
    target: str,
) -> list[dict[str, Any]]:
    for turn in target_turns(transcript):
        rows = ordered_candidate_rows_from_state(
            turn.get("internal_state") or {}, target
        )
        if rows:
            return rows
    return []


def retrieval_topn_metrics_for_limits(
    transcript: dict[str, Any] | None,
    target: str,
    case: UnifiedIcebergCase,
    candidate_pool: list[dict[str, Any]],
    *,
    limits: Iterable[int] = RECOMMENDATION_TOP_NS,
) -> dict[str, Any]:
    ordered_rows = first_recall_rows_from_transcript(transcript, target)
    pool = dedupe_candidate_rows(
        [
            case.baseline_candidate_a,
            *acceptable_candidates(case),
            *(candidate_pool or []),
        ]
    )
    output: dict[str, Any] = {
        "retrieval_candidate_count": len(ordered_rows),
    }
    for raw_limit in limits:
        limit = int(raw_limit)
        predicted = {
            primary_candidate_key(row) for row in ordered_rows[: max(1, limit)]
        }
        gold = top_recommendation_keys(
            pool,
            case.ground_truth_weights,
            case.initial_utterance,
            limit=limit,
        )
        matched = predicted & gold
        precision = len(matched) / len(predicted) if predicted else 0.0
        recall = len(matched) / len(gold) if gold else 0.0
        score = (
            0.0
            if precision + recall == 0
            else 2 * precision * recall / (precision + recall)
        )
        output.update(
            {
                f"retrieval_precision_at_{limit}": precision,
                f"retrieval_recall_at_{limit}": recall,
                f"retrieval_f1_at_{limit}": score,
                f"retrieval_hit_at_{limit}": bool(matched),
                f"retrieval_match_count_at_{limit}": len(matched),
                f"retrieval_matched_ids_at_{limit}": ",".join(sorted(matched)),
            }
        )
    return output


def mae(weights: dict[str, float], truth: dict[str, float]) -> float:
    if not truth:
        return 0.0
    return mean(
        abs(float(weights.get(dim, 0.0)) - float(truth.get(dim, 0.0)))
        for dim in DIMENSIONS
    )


def l2_delta(a: dict[str, float], b: dict[str, float]) -> float:
    return math.sqrt(
        sum(
            (float(a.get(dim, 0.0)) - float(b.get(dim, 0.0))) ** 2 for dim in DIMENSIONS
        )
    )


def boi(weights_trajectory: list[dict[str, float]]) -> float:
    if len(weights_trajectory) < 2:
        return 0.0
    step_sum = sum(
        l2_delta(weights_trajectory[index], weights_trajectory[index - 1])
        for index in range(1, len(weights_trajectory))
    )
    global_delta = l2_delta(weights_trajectory[-1], weights_trajectory[0])
    if global_delta <= 1e-9:
        return 0.0 if step_sum <= 1e-9 else float("nan")
    return step_sum / global_delta


def target_turns(transcript: dict[str, Any] | None) -> list[dict[str, Any]]:
    turns = list((transcript or {}).get("turns") or [])
    return [turn for turn in turns if str(turn.get("role")) == "target_agent"]


def following_user_turns(
    transcript: dict[str, Any] | None,
) -> list[tuple[dict[str, Any], dict[str, Any] | None]]:
    turns = list((transcript or {}).get("turns") or [])
    pairs: list[tuple[dict[str, Any], dict[str, Any] | None]] = []
    for index, turn in enumerate(turns):
        if str(turn.get("role")) != "target_agent":
            continue
        follower = None
        if index + 1 < len(turns) and str(turns[index + 1].get("role")) == "user":
            follower = turns[index + 1]
        pairs.append((turn, follower))
    return pairs


def final_weights_from_transcript(
    transcript: dict[str, Any] | None,
) -> dict[str, float]:
    for turn in reversed(target_turns(transcript)):
        weights = numeric_map(
            (turn.get("internal_state") or {}).get("implicit_weights")
        )
        if weights:
            return weights
    return {}


def equivalent_final_weights(
    transcript: dict[str, Any] | None,
    case: UnifiedIcebergCase,
) -> dict[str, float]:
    """Return final comparable weights for both EDMIE and static baselines."""
    weights = final_weights_from_transcript(transcript)
    if weights:
        return weights

    state: dict[str, Any] = {}
    for turn in reversed(target_turns(transcript)):
        candidate_state = turn.get("internal_state") or {}
        if isinstance(candidate_state, dict) and candidate_state:
            state = candidate_state
            break
    candidates = (
        state.get("second_stage_reranked_candidates")
        or state.get("soft_retrieval_candidates")
        or state.get("baseline_results")
        or state.get("recommended_schools")
        or []
    )
    if isinstance(candidates, list):
        cleaned = [dict(row) for row in candidates if isinstance(row, dict)]
        if cleaned:
            try:
                return infer_weights_from_v1_candidates(
                    cleaned,
                    query_text=case.initial_utterance,
                )
            except Exception:
                pass
    return {dim: 1.0 / len(DIMENSIONS) for dim in DIMENSIONS}


def variance_trajectory(transcript: dict[str, Any] | None) -> list[float]:
    values: list[float] = []
    for turn in target_turns(transcript):
        state = turn.get("internal_state") or {}
        variance = numeric_map(state.get("weight_variance"))
        if variance:
            values.append(sum(float(variance.get(dim, 0.0)) for dim in DIMENSIONS))
    return values


def weight_trajectory(transcript: dict[str, Any] | None) -> list[dict[str, float]]:
    values: list[dict[str, float]] = []
    for turn in target_turns(transcript):
        weights = numeric_map(
            (turn.get("internal_state") or {}).get("implicit_weights")
        )
        if weights:
            values.append(weights)
    return values


def eudr(sum_var: list[float]) -> tuple[float, float]:
    if len(sum_var) < 2:
        return 0.0, 0.0
    decay = float(sum_var[0]) - float(sum_var[-1])
    slope = decay / (len(sum_var) - 1)
    ratio = decay / float(sum_var[0]) if float(sum_var[0]) else 0.0
    return slope, ratio


def pcg_metrics(
    transcript: dict[str, Any] | None, gold_dims: list[str]
) -> dict[str, Any]:
    gold = {dim for dim in gold_dims if dim}
    if not gold:
        return {
            "pcg_first_hit_turn": "",
            "pcg_final_coverage": 0.0,
            "pcg_hit_count": 0,
        }
    seen: set[str] = set()
    first_hit: int | None = None
    hit_count = 0
    for index, turn in enumerate(target_turns(transcript), start=1):
        state = turn.get("internal_state") or {}
        selected = str(
            state.get("selected_probe_dim") or state.get("ucb_target_dimension") or ""
        )
        if selected in gold:
            hit_count += 1
            seen.add(selected)
            if first_hit is None:
                first_hit = index
    return {
        "pcg_first_hit_turn": first_hit if first_hit is not None else "",
        "pcg_final_coverage": len(seen) / len(gold),
        "pcg_hit_count": hit_count,
    }


def valid_probe_metrics(
    transcript: dict[str, Any] | None,
    case: UnifiedIcebergCase,
) -> dict[str, Any]:
    dims = case.acceptable_probe_dims or default_acceptable_probe_dims(
        case.diagnostic_axis,
        case.probe_gold_dims,
    )
    keys = case.acceptable_probe_keys or default_acceptable_probe_keys(
        case.diagnostic_axis
    )
    return valid_probe_metrics_from_turns(
        target_turns(transcript),
        acceptable_dims=dims,
        acceptable_keys=keys,
    )


def msti_metrics(
    transcript: dict[str, Any] | None, case: UnifiedIcebergCase
) -> dict[str, float]:
    values: list[float] = []
    for turn in target_turns(transcript):
        diff = numeric_map((turn.get("internal_state") or {}).get("latest_pareto_diff"))
        if diff:
            values.append(sum(abs(value) for value in diff.values()))
    fallback = float(case.expected_msti)
    return {
        "msti_mean": mean(values) if values else fallback,
        "msti_max": max(values) if values else fallback,
        "msti_observed_count": len(values),
    }


ACCEPT_RE = re.compile(r"接受|可以考虑|愿意|纳入|同意|认真考虑")
REJECT_RE = re.compile(r"不接受|不行|不能接受|拒绝|不考虑|不太能|还是不")


def ctr_metrics(transcript: dict[str, Any] | None) -> dict[str, float]:
    opportunities = 0
    clear = 0
    accept = 0
    reject = 0
    for _agent, user in following_user_turns(transcript):
        if not user:
            continue
        opportunities += 1
        content = str(user.get("content") or "")
        state = user.get("internal_state") or {}
        persuaded = state.get("is_persuaded")
        is_accept = persuaded is True or bool(ACCEPT_RE.search(content))
        is_reject = bool(REJECT_RE.search(content))
        if is_accept:
            accept += 1
        if is_reject:
            reject += 1
        if is_accept or is_reject:
            clear += 1
    return {
        "ctr_opportunities": opportunities,
        "cardinal_trigger_count": clear,
        "cardinal_trigger_rate": clear / opportunities if opportunities else 0.0,
        "accept_count": accept,
        "reject_count": reject,
    }


def kbv_metrics(
    transcript: dict[str, Any] | None, case: UnifiedIcebergCase
) -> dict[str, Any]:
    candidate_names = {
        str(case.golden_candidate_b.get("school_name") or ""),
        str(case.golden_candidate_b.get("major_name") or ""),
    }
    for row in case.volunteer_set:
        if isinstance(row, dict):
            candidate_names.add(str(row.get("school_name") or ""))
            candidate_names.add(str(row.get("major_name") or ""))
    candidate_names = {name for name in candidate_names if name}
    turns = list((transcript or {}).get("turns") or [])
    rejection_turn_id: int | None = None
    for turn in turns:
        if str(turn.get("role")) != "user":
            continue
        content = str(turn.get("content") or "")
        if REJECT_RE.search(content):
            rejection_turn_id = int(turn.get("turn_id") or 0)
            break
    if rejection_turn_id is None:
        return {
            "rejection_turn": "",
            "kbv_opportunities": 0,
            "kbv_violations": 0,
            "kbv_rate": 0.0,
        }
    opportunities = 0
    violations = 0
    for turn in turns:
        if str(turn.get("role")) != "target_agent":
            continue
        if int(turn.get("turn_id") or 0) <= rejection_turn_id:
            continue
        opportunities += 1
        content = str(turn.get("content") or "")
        if any(name and name in content for name in candidate_names):
            violations += 1
    return {
        "rejection_turn": rejection_turn_id,
        "kbv_opportunities": opportunities,
        "kbv_violations": violations,
        "kbv_rate": violations / opportunities if opportunities else 0.0,
    }


def enrich_common(row: dict[str, Any], case: UnifiedIcebergCase) -> dict[str, Any]:
    background = case.background
    return {
        **row,
        "constraint_count": case.constraint_count,
        "diagnostic_axis": case.diagnostic_axis,
        "score_band": background.get("score_band"),
        "probe_gold_dims": ",".join(case.probe_gold_dims),
        "weight_gold_dims": ",".join(case.weight_gold_dims),
        "expected_msti": case.expected_msti,
    }


def build_baseline_rows(
    *,
    roots: list[Path],
    cases: dict[str, UnifiedIcebergCase],
    candidate_pools: dict[str, list[dict[str, Any]]],
) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for root in roots:
        for run_dir, meta in iter_run_dirs(root):
            target = str(meta.get("target") or "")
            report_path = run_dir / "reports" / f"{target}.jsonl"
            for report in read_jsonl(report_path):
                case = cases.get(str(report.get("case_id") or ""))
                if case is None:
                    continue
                transcript = read_transcript(report.get("transcript_path"))
                weights = equivalent_final_weights(transcript, case)
                rec_metrics = recommendation_set_metrics_for_limits(
                    weights,
                    case,
                    candidate_pools.get(case.case_id, []),
                )
                retrieval_metrics = retrieval_topn_metrics_for_limits(
                    transcript,
                    target,
                    case,
                    candidate_pools.get(case.case_id, []),
                )
                row = {
                    "suite": str(meta.get("suite") or "baseline"),
                    "model": str(meta.get("model") or run_dir.parent.name),
                    "model_alias": model_alias(
                        meta.get("model") or run_dir.parent.name
                    ),
                    "target": target,
                    "case_id": case.case_id,
                    "status": report.get("status"),
                    "elicitation_success": bool(report.get("elicitation_success")),
                    "pareto_gain": float(report.get("pareto_gain") or 0.0),
                    "hallucination_rate": (
                        float(report.get("hallucination_rate") or 0.0)
                        if report.get("hallucination_rate") is not None
                        else ""
                    ),
                    "turns": int(report.get("turns") or 0),
                    "transcript_path": report.get("transcript_path") or "",
                    "mae": mae(weights, case.ground_truth_weights),
                    "topk_f1": topk_f1(weights, case.weight_gold_dims),
                    **rec_metrics,
                    **retrieval_metrics,
                    "final_weights_json": json.dumps(weights, ensure_ascii=False),
                    "error_type": report.get("error_type") or "",
                    "error": report.get("error") or "",
                }
                for field in TRANSCRIPT_DIAGNOSTIC_FIELDS:
                    row[field] = report.get(field, "")
                output.append(enrich_common(row, case))
    return output


def build_ablation_rows(
    *,
    roots: list[Path],
    cases: dict[str, UnifiedIcebergCase],
    candidate_pools: dict[str, list[dict[str, Any]]],
) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for root in roots:
        for run_dir, meta in iter_run_dirs(root):
            target = str(meta.get("target") or "")
            report_path = run_dir / "reports" / f"{target}.jsonl"
            for report in read_jsonl(report_path):
                case = cases.get(str(report.get("case_id") or ""))
                if case is None:
                    continue
                transcript = read_transcript(report.get("transcript_path"))
                weights = final_weights_from_transcript(transcript)
                rec_metrics = recommendation_set_metrics_for_limits(
                    weights,
                    case,
                    candidate_pools.get(case.case_id, []),
                )
                retrieval_metrics = retrieval_topn_metrics_for_limits(
                    transcript,
                    target,
                    case,
                    candidate_pools.get(case.case_id, []),
                )
                sum_var = variance_trajectory(transcript)
                eudr_slope, eudr_ratio = eudr(sum_var)
                pcg = pcg_metrics(transcript, case.probe_gold_dims)
                valid_probe = valid_probe_metrics(transcript, case)
                msti = msti_metrics(transcript, case)
                ctr = ctr_metrics(transcript)
                kbv = kbv_metrics(transcript, case)
                trajectory = weight_trajectory(transcript)
                row = {
                    "suite": str(meta.get("suite") or "ablation"),
                    "model": str(meta.get("model") or run_dir.parent.name),
                    "model_alias": model_alias(
                        meta.get("model") or run_dir.parent.name
                    ),
                    "target": target,
                    "ablation_mode": TARGET_TO_MODE.get(target, target),
                    "case_id": case.case_id,
                    "status": report.get("status"),
                    "elicitation_success": bool(report.get("elicitation_success")),
                    "pareto_gain": float(report.get("pareto_gain") or 0.0),
                    "hallucination_rate": (
                        float(report.get("hallucination_rate") or 0.0)
                        if report.get("hallucination_rate") is not None
                        else ""
                    ),
                    "turns": int(report.get("turns") or 0),
                    "transcript_path": report.get("transcript_path") or "",
                    "mae": mae(weights, case.ground_truth_weights),
                    "topk_f1": topk_f1(weights, case.weight_gold_dims),
                    **rec_metrics,
                    **retrieval_metrics,
                    "boi": boi(trajectory),
                    "sum_var_start": sum_var[0] if sum_var else "",
                    "sum_var_end": sum_var[-1] if sum_var else "",
                    "eudr_slope": eudr_slope,
                    "eudr_ratio": eudr_ratio,
                    **pcg,
                    **valid_probe,
                    **msti,
                    **ctr,
                    **kbv,
                    "final_weights_json": json.dumps(weights, ensure_ascii=False),
                    "error_type": report.get("error_type") or "",
                    "error": report.get("error") or "",
                }
                for field in TRANSCRIPT_DIAGNOSTIC_FIELDS:
                    row[field] = report.get(field, "")
                output.append(enrich_common(row, case))
    return output


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames: list[str] = []
    seen: set[str] = set()
    for row in rows:
        for key in row:
            if key not in seen:
                seen.add(key)
                fieldnames.append(key)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def group_rows(
    rows: list[dict[str, Any]], keys: tuple[str, ...]
) -> list[dict[str, Any]]:
    groups: dict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[tuple(row.get(key) for key in keys)].append(row)
    output: list[dict[str, Any]] = []
    for group_key, group_rows_value in sorted(
        groups.items(), key=lambda item: tuple(str(x) for x in item[0])
    ):
        item = {key: value for key, value in zip(keys, group_key)}
        item["n"] = len(group_rows_value)
        item["completed"] = sum(
            1 for row in group_rows_value if row.get("status") == "ok"
        )
        item["failed"] = item["n"] - item["completed"]
        for metric in (
            "elicitation_success",
            "pareto_gain",
            "hallucination_rate",
            "turns",
            "mae",
            "topk_f1",
            "recommendation_precision_at_1",
            "recommendation_recall_at_1",
            "recommendation_f1_at_1",
            "recommendation_precision_at_3",
            "recommendation_recall_at_3",
            "recommendation_f1_at_3",
            "recommendation_f1_at_5",
            "recommendation_f1_at_10",
            "recommendation_hit_at_1",
            "recommendation_hit_at_3",
            "retrieval_candidate_count",
            "retrieval_f1_at_1",
            "retrieval_f1_at_3",
            "retrieval_f1_at_5",
            "retrieval_f1_at_10",
            "retrieval_hit_at_1",
            "retrieval_hit_at_3",
            "boi",
            "eudr_slope",
            "eudr_ratio",
            "pcg_final_coverage",
            "valid_probe_hit_rate",
            "valid_probe_coverage",
            "msti_mean",
            "cardinal_trigger_rate",
            "kbv_rate",
        ):
            values = []
            for row in group_rows_value:
                value = row.get(metric)
                if isinstance(value, bool):
                    values.append(1.0 if value else 0.0)
                else:
                    try:
                        values.append(float(value))
                    except (TypeError, ValueError):
                        pass
            if values:
                item[f"{metric}_mean"] = mean(values)
                item[f"{metric}_std"] = std(values)
        output.append(item)
    return output


def markdown_table(
    rows: list[dict[str, Any]], columns: list[str], *, limit: int | None = None
) -> list[str]:
    selected = rows[:limit] if limit is not None else rows
    lines = [
        "| " + " | ".join(columns) + " |",
        "| " + " | ".join("---" for _ in columns) + " |",
    ]
    for row in selected:
        cells = []
        for column in columns:
            value = row.get(column, "")
            if isinstance(value, float):
                cells.append(f"{value:.3f}")
            else:
                cells.append(str(value))
        lines.append("| " + " | ".join(cells) + " |")
    return lines


def write_summary(
    path: Path,
    *,
    baseline_rows: list[dict[str, Any]],
    ablation_rows: list[dict[str, Any]],
) -> None:
    baseline_by_target = group_rows(baseline_rows, ("model_alias", "target"))
    baseline_by_constraint = group_rows(
        baseline_rows,
        ("target", "constraint_count"),
    )
    ablation_by_mode = group_rows(ablation_rows, ("ablation_mode",))
    ablation_by_constraint = group_rows(
        ablation_rows,
        ("ablation_mode", "constraint_count"),
    )
    lines = [
        "# Unified Iceberg Experiment Summary",
        "",
        f"Baseline rows: {len(baseline_rows)}.",
        f"Ablation rows: {len(ablation_rows)}.",
        "",
        "## Baseline By Model And Target",
        "",
        *markdown_table(
            baseline_by_target,
            [
                "model_alias",
                "target",
                "n",
                "completed",
                "failed",
                "elicitation_success_mean",
                "pareto_gain_mean",
                "hallucination_rate_mean",
                "turns_mean",
                "recommendation_f1_at_1_mean",
                "recommendation_f1_at_3_mean",
                "recommendation_f1_at_5_mean",
                "recommendation_f1_at_10_mean",
                "retrieval_f1_at_1_mean",
                "retrieval_f1_at_3_mean",
                "retrieval_f1_at_5_mean",
                "retrieval_f1_at_10_mean",
            ],
        ),
        "",
        "## Baseline Constraint Gradient",
        "",
        *markdown_table(
            baseline_by_constraint,
            [
                "target",
                "constraint_count",
                "n",
                "completed",
                "failed",
                "elicitation_success_mean",
                "pareto_gain_mean",
                "turns_mean",
                "recommendation_f1_at_1_mean",
                "recommendation_f1_at_3_mean",
                "recommendation_f1_at_5_mean",
                "recommendation_f1_at_10_mean",
                "retrieval_f1_at_1_mean",
                "retrieval_f1_at_3_mean",
                "retrieval_f1_at_5_mean",
                "retrieval_f1_at_10_mean",
            ],
        ),
        "",
        "## Ablation By Mode",
        "",
        *markdown_table(
            ablation_by_mode,
            [
                "ablation_mode",
                "n",
                "completed",
                "failed",
                "mae_mean",
                "topk_f1_mean",
                "recommendation_f1_at_1_mean",
                "recommendation_f1_at_3_mean",
                "recommendation_f1_at_5_mean",
                "recommendation_f1_at_10_mean",
                "retrieval_f1_at_1_mean",
                "retrieval_f1_at_3_mean",
                "retrieval_f1_at_5_mean",
                "retrieval_f1_at_10_mean",
                "boi_mean",
                "eudr_slope_mean",
                "pcg_final_coverage_mean",
                "valid_probe_hit_rate_mean",
                "valid_probe_coverage_mean",
                "msti_mean_mean",
                "cardinal_trigger_rate_mean",
                "kbv_rate_mean",
            ],
        ),
        "",
        "## Ablation Constraint Gradient",
        "",
        *markdown_table(
            ablation_by_constraint,
            [
                "ablation_mode",
                "constraint_count",
                "n",
                "completed",
                "failed",
                "mae_mean",
                "topk_f1_mean",
                "recommendation_f1_at_1_mean",
                "recommendation_f1_at_3_mean",
                "recommendation_f1_at_5_mean",
                "recommendation_f1_at_10_mean",
                "retrieval_f1_at_1_mean",
                "retrieval_f1_at_3_mean",
                "retrieval_f1_at_5_mean",
                "retrieval_f1_at_10_mean",
                "eudr_slope_mean",
                "pcg_final_coverage_mean",
                "valid_probe_hit_rate_mean",
                "valid_probe_coverage_mean",
            ],
        ),
        "",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def parse_roots(values: list[str] | None, default: Path) -> list[Path]:
    if not values:
        return [default]
    return [Path(value) for value in values]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Summarize unified iceberg benchmark outputs."
    )
    parser.add_argument("--cases", default=str(DEFAULT_CASES))
    parser.add_argument("--baseline-root", nargs="*", default=None)
    parser.add_argument("--ablation-root", nargs="*", default=None)
    parser.add_argument(
        "--baseline-csv",
        default=str(DEFAULT_RESULTS_DIR / "unified_baseline_results.csv"),
    )
    parser.add_argument(
        "--ablation-csv",
        default=str(DEFAULT_RESULTS_DIR / "unified_ablation_results.csv"),
    )
    parser.add_argument(
        "--summary",
        default=str(DEFAULT_RESULTS_DIR / "unified_experiment_summary.md"),
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    cases = read_cases(args.cases)
    baseline_roots = parse_roots(args.baseline_root, DEFAULT_BASELINE_ROOT)
    ablation_roots = parse_roots(args.ablation_root, DEFAULT_ABLATION_ROOT)
    candidate_pools = collect_candidate_pools(
        roots=[*baseline_roots, *ablation_roots],
        cases=cases,
    )
    baseline_rows = build_baseline_rows(
        roots=baseline_roots,
        cases=cases,
        candidate_pools=candidate_pools,
    )
    ablation_rows = build_ablation_rows(
        roots=ablation_roots,
        cases=cases,
        candidate_pools=candidate_pools,
    )
    write_csv(Path(args.baseline_csv), baseline_rows)
    write_csv(Path(args.ablation_csv), ablation_rows)
    write_summary(
        Path(args.summary),
        baseline_rows=baseline_rows,
        ablation_rows=ablation_rows,
    )
    print(f"[unified_metrics] wrote {args.baseline_csv}")
    print(f"[unified_metrics] wrote {args.ablation_csv}")
    print(f"[unified_metrics] wrote {args.summary}")


if __name__ == "__main__":
    main()
