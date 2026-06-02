import argparse
import csv
import json
import math
import os
import random
import re
from pathlib import Path
from typing import Any

from langchain_core.messages import SystemMessage
from openai import AsyncOpenAI
from pydantic import BaseModel

from app.core.llm_client import (
    DEFAULT_STRUCTURED_MODEL,
    ainvoke_with_timeout,
    get_structured_chat_model,
    structured_timeout_seconds,
)
from app.evaluation.benchmark import get_dataset
from app.evaluation.classification_metrics import (
    REFERENCE_SOURCE,
    compute_prf,
    classification_rows_from_reference_rows,
    merge_classification_metrics,
)
from app.evaluation.schemas import IcebergProfile


PREFERENCE_KEYS = ("school", "major", "tuition", "quality", "geo", "risk")
RESULTS_DIR = Path(__file__).parent / "results"
REFERENCE_FIELDS = (
    "dataset",
    "profile_id",
    "baseline_type",
    "mae_error",
    "weights",
    "status",
    "error_message",
)
RANDOM_BASELINE = "random_dirichlet_expected"
INITIAL_LLM_BASELINE = "initial_query_llm"
V1_HYBRID_BASELINE = "v1_hybrid_candidate_proxy"


class InitialPreferenceWeights(BaseModel):
    school: float = 1 / 6
    major: float = 1 / 6
    tuition: float = 1 / 6
    quality: float = 1 / 6
    geo: float = 1 / 6
    risk: float = 1 / 6
    rationale: str = ""


def _json_from_text(text: str) -> dict[str, Any]:
    match = re.search(r"\{.*\}", text, flags=re.S)
    if not match:
        return {}
    try:
        data = json.loads(match.group(0))
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def compute_mae(
    weights: dict[str, Any],
    ground_truth_weights: dict[str, float],
) -> float:
    if not ground_truth_weights:
        return 0.0
    total = 0.0
    for key, truth in ground_truth_weights.items():
        try:
            inferred = float(weights.get(key, 0.0))
        except (TypeError, ValueError):
            inferred = 0.0
        total += abs(inferred - float(truth))
    return total / len(ground_truth_weights)


def normalize_weights(
    weights: dict[str, Any] | InitialPreferenceWeights,
) -> dict[str, float]:
    raw = (
        weights.model_dump()
        if isinstance(weights, InitialPreferenceWeights)
        else dict(weights)
    )
    values: dict[str, float] = {}
    for key in PREFERENCE_KEYS:
        try:
            value = float(raw.get(key, 1.0 / len(PREFERENCE_KEYS)))
        except (TypeError, ValueError):
            value = 1.0 / len(PREFERENCE_KEYS)
        values[key] = max(0.0, min(1.0, value))
    total = sum(values.values())
    if not math.isfinite(total) or total <= 0.0:
        return {key: 1.0 / len(PREFERENCE_KEYS) for key in PREFERENCE_KEYS}
    return {key: values[key] / total for key in PREFERENCE_KEYS}


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    return number if math.isfinite(number) else default


def _contains_any(text: str, tokens: tuple[str, ...]) -> bool:
    lowered = text.lower()
    return any(token.lower() in lowered for token in tokens)


def _extract_budget_from_text(text: str) -> float | None:
    patterns = (
        r"(?:预算|学费|费用)[^\d]{0,8}(\d+(?:\.\d+)?)\s*(?:万|w|W)",
        r"(\d+(?:\.\d+)?)\s*(?:万|w|W)[^\n，。；;]{0,8}(?:预算|学费|费用)",
        r"(?:预算|学费|费用)[^\d]{0,8}(\d{4,6})",
    )
    for pattern in patterns:
        match = re.search(pattern, text)
        if not match:
            continue
        value = _safe_float(match.group(1), 0.0)
        if value <= 0:
            continue
        if "万" in match.group(0) or "w" in match.group(0).lower():
            value *= 10000
        return value
    return None


def _school_signal(row: dict[str, Any]) -> float:
    tier = str(
        row.get("school_tier") or row.get("school_level") or row.get("tier") or ""
    )
    if _contains_any(tier, ("C9", "顶尖985")):
        return 1.0
    if row.get("is_985") or _contains_any(tier, ("985",)):
        return 0.9
    if (
        row.get("is_211")
        or row.get("is_double_first_class")
        or _contains_any(tier, ("211", "双一流"))
    ):
        return 0.72
    numeric_tier = _safe_float(row.get("tier"), 0.0)
    if numeric_tier >= 4:
        return 0.9
    if numeric_tier >= 3:
        return 0.72
    if numeric_tier >= 2 or _contains_any(tier, ("一本", "本科", "重点")):
        return 0.45
    return 0.18


def _major_signal(row: dict[str, Any], query_text: str) -> float:
    major_name = str(row.get("major_name") or row.get("major_name_raw") or "")
    combined = f"{query_text} {major_name}"
    if _contains_any(combined, ("计算机", "软件", "人工智能", "数据科学", "computer")):
        return (
            1.0
            if _contains_any(
                major_name, ("计算机", "软件", "人工智能", "数据科学", "computer")
            )
            else 0.25
        )
    if _contains_any(combined, ("临床", "医学", "clinical")):
        return 1.0 if _contains_any(major_name, ("临床", "医学", "clinical")) else 0.25
    if _contains_any(combined, ("法学", "law")):
        return 1.0 if _contains_any(major_name, ("法学", "law")) else 0.25
    return 0.5


def _geo_signal(row: dict[str, Any], query_text: str) -> float:
    province = str(row.get("school_province") or row.get("province") or "")
    city = str(row.get("school_city") or row.get("city") or "")
    location = f"{province} {city}"
    if _contains_any(query_text, ("江浙沪",)):
        return 1.0 if _contains_any(location, ("浙江", "江苏", "上海")) else 0.2
    if _contains_any(query_text, ("浙江", "本省", "省内")):
        return 1.0 if "浙江" in location else 0.1
    if _contains_any(query_text, ("不出省", "绝不出省")):
        return 1.0 if "浙江" in location else 0.0
    return 0.35


def _tuition_signal(row: dict[str, Any], query_text: str) -> float:
    budget = _extract_budget_from_text(query_text)
    if budget is None:
        return 0.15
    tuition = _safe_float(row.get("tuition"), 0.0)
    if tuition <= 0:
        return 0.35
    if tuition <= budget:
        return 1.0
    excess = (tuition - budget) / max(budget, 1.0)
    return max(0.0, 1.0 - 2.0 * excess)


def _quality_signal(row: dict[str, Any]) -> float:
    quality = row.get("quality_score")
    if quality is not None:
        return max(0.0, min(1.0, _safe_float(quality) / 100.0))
    ranking = _safe_float(row.get("ranking"), 0.0)
    if ranking > 0:
        return max(0.1, min(1.0, 1.0 - ranking / 1000.0))
    min_rank = _safe_float(row.get("min_rank"), 0.0)
    if min_rank > 0:
        return max(0.1, min(1.0, 1.0 - min_rank / 250000.0))
    return 0.35


def _risk_signal(row: dict[str, Any]) -> float:
    label = str(
        row.get("risk_label") or row.get("risk_level") or row.get("risk_bucket") or ""
    )
    if label in {"保", "bao", "safety", "dian"}:
        return 1.0
    if label in {"稳", "wen", "match"}:
        return 0.7
    if label in {"冲", "chong", "reach"}:
        return 0.25
    ratio = _safe_float(row.get("rank_ratio"), -1.0)
    if ratio > 0:
        if ratio < 0.85:
            return 0.0
        if ratio < 0.98:
            return 0.25
        if ratio <= 1.15:
            return 0.7
        if ratio <= 1.40:
            return 1.0
    student_rank = _safe_float(row.get("student_rank"), 0.0)
    min_rank = _safe_float(row.get("min_rank"), 0.0)
    if student_rank > 0 and min_rank > 0:
        return _risk_signal({"rank_ratio": min_rank / student_rank})
    return 0.5


def infer_weights_from_v1_candidates(
    candidates: list[dict[str, Any]],
    *,
    query_text: str,
    top_n: int = 9,
) -> dict[str, float]:
    if not candidates:
        raise ValueError("v1 hybrid baseline produced no reranked candidates")
    evidence = {key: 0.0 for key in PREFERENCE_KEYS}
    used = candidates[: max(1, top_n)]
    for index, row in enumerate(used):
        rank_weight = 1.0 / math.log2(index + 2)
        signals = {
            "school": _school_signal(row),
            "major": _major_signal(row, query_text),
            "tuition": _tuition_signal(row, query_text),
            "quality": _quality_signal(row),
            "geo": _geo_signal(row, query_text),
            "risk": _risk_signal(row),
        }
        for key, value in signals.items():
            evidence[key] += rank_weight * max(0.0, min(1.0, value))
    return normalize_weights(evidence)


def _sample_dirichlet_uniform(rng: random.Random) -> dict[str, float]:
    draws = [rng.expovariate(1.0) for _ in PREFERENCE_KEYS]
    total = sum(draws)
    return {
        key: value / total for key, value in zip(PREFERENCE_KEYS, draws, strict=True)
    }


def estimate_random_baseline(
    dataset: list[IcebergProfile],
    *,
    samples: int = 50_000,
    seed: int = 20260513,
) -> dict[str, Any]:
    if samples <= 0:
        raise ValueError("samples must be positive")
    rng = random.Random(seed)
    profile_sums = {profile.profile_id: 0.0 for profile in dataset}
    profile_sq_sums = {profile.profile_id: 0.0 for profile in dataset}
    profile_f1_sums = {profile.profile_id: 0.0 for profile in dataset}
    profile_f1_sq_sums = {profile.profile_id: 0.0 for profile in dataset}
    dataset_values: list[float] = []
    dataset_f1_values: list[float] = []

    for _ in range(samples):
        weights = _sample_dirichlet_uniform(rng)
        sample_total = 0.0
        sample_f1_total = 0.0
        for profile in dataset:
            value = compute_mae(weights, profile.ground_truth_weights)
            f1_value = float(compute_prf(weights, profile)["f1"])
            profile_sums[profile.profile_id] += value
            profile_sq_sums[profile.profile_id] += value * value
            profile_f1_sums[profile.profile_id] += f1_value
            profile_f1_sq_sums[profile.profile_id] += f1_value * f1_value
            sample_total += value
            sample_f1_total += f1_value
        if dataset:
            dataset_values.append(sample_total / len(dataset))
            dataset_f1_values.append(sample_f1_total / len(dataset))

    rows: list[dict[str, Any]] = []
    for profile in dataset:
        mean = profile_sums[profile.profile_id] / samples
        f1_mean = profile_f1_sums[profile.profile_id] / samples
        variance = max(
            0.0,
            profile_sq_sums[profile.profile_id] / samples - mean * mean,
        )
        f1_variance = max(
            0.0,
            profile_f1_sq_sums[profile.profile_id] / samples - f1_mean * f1_mean,
        )
        rows.append(
            {
                "profile_id": profile.profile_id,
                "mean_mae": mean,
                "std_mae": math.sqrt(variance),
                "expected_f1": f1_mean,
                "std_f1": math.sqrt(f1_variance),
            }
        )
    dataset_mean = sum(dataset_values) / len(dataset_values) if dataset_values else 0.0
    dataset_std = _std(dataset_values)
    dataset_f1_mean = (
        sum(dataset_f1_values) / len(dataset_f1_values) if dataset_f1_values else 0.0
    )
    dataset_f1_std = _std(dataset_f1_values)
    return {
        "mean_mae": dataset_mean,
        "std_mae": dataset_std,
        "expected_f1": dataset_f1_mean,
        "std_f1": dataset_f1_std,
        "profile_rows": rows,
    }


def _std(values: list[float]) -> float:
    if len(values) < 2:
        return 0.0
    mean = sum(values) / len(values)
    return math.sqrt(sum((value - mean) ** 2 for value in values) / (len(values) - 1))


async def infer_initial_weights_with_llm(
    profile: IcebergProfile,
) -> dict[str, float]:
    try:
        return await _infer_initial_weights_native_json(profile)
    except Exception:
        pass

    llm = get_structured_chat_model()
    prompt = [
        SystemMessage(
            content=(
                "You estimate first-turn preference weights for a Gaokao advising "
                "agent. Use ONLY the user's explicit initial query. Do not infer "
                "hidden bottom lines, do not use profile_id, do not use later "
                "dialogue, and do not use ground-truth labels. Return five "
                "non-negative weights for school, major, tuition, quality, geo, and risk. "
                "The weights may be unnormalized; the evaluator will normalize them."
            )
        ),
        SystemMessage(content=f"Initial explicit query: {profile.explicit_query}"),
    ]
    try:
        structured = llm.with_structured_output(InitialPreferenceWeights)
        result = await ainvoke_with_timeout(
            structured,
            prompt,
            timeout=min(15.0, structured_timeout_seconds()),
            label="initial_query_weight_baseline_structured",
        )
        if isinstance(result, InitialPreferenceWeights):
            parsed = result
        else:
            parsed = InitialPreferenceWeights.model_validate(result)
    except Exception:
        # Some OpenAI-compatible providers expose JSON chat completions but stall on
        # the SDK parse endpoint used by with_structured_output. This fallback still
        # calls the real structured LLM and validates the returned JSON with the same
        # Pydantic schema; it only avoids the provider-specific parse wrapper.
        json_prompt = [
            SystemMessage(
                content=(
                    'Return JSON only. Schema: {"school": float, "major": float, '
                    '"tuition": float, "quality": float, "geo": float, '
                    '"rationale": string}. Estimate first-turn weights using ONLY '
                    "the user's explicit initial query. Do not use hidden preferences "
                    "or ground truth. Values may be unnormalized non-negative numbers."
                )
            ),
            SystemMessage(content=f"Initial explicit query: {profile.explicit_query}"),
        ]
        result = await ainvoke_with_timeout(
            llm,
            json_prompt,
            timeout=structured_timeout_seconds(),
            label="initial_query_weight_baseline_json",
        )
        parsed = InitialPreferenceWeights.model_validate(
            _json_from_text(str(getattr(result, "content", result)))
        )
    return normalize_weights(parsed)


async def _infer_initial_weights_native_json(
    profile: IcebergProfile,
) -> dict[str, float]:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is required for initial-query LLM baseline.")
    client = AsyncOpenAI(
        api_key=api_key,
        base_url=os.getenv("OPENAI_BASE_URL") or None,
        timeout=structured_timeout_seconds(),
        max_retries=0,
    )
    response = await client.chat.completions.create(
        model=os.getenv("SMALL_MODEL") or DEFAULT_STRUCTURED_MODEL,
        messages=[
            {
                "role": "system",
                "content": (
                    'Return JSON only. Schema: {"school": float, "major": float, '
                    '"tuition": float, "quality": float, "geo": float, '
                    '"rationale": string}. Estimate first-turn weights using ONLY '
                    "the user's explicit initial query. Do not use hidden preferences, "
                    "profile identifiers, later feedback, or ground truth. Values may "
                    "be unnormalized non-negative numbers."
                ),
            },
            {
                "role": "user",
                "content": f"Initial explicit query: {profile.explicit_query}",
            },
        ],
        max_tokens=256,
        temperature=0,
        response_format={"type": "json_object"},
        extra_body={"enable_thinking": False},
    )
    content = response.choices[0].message.content or ""
    return normalize_weights(
        InitialPreferenceWeights.model_validate(_json_from_text(content))
    )


async def compute_initial_llm_baseline(
    dataset: list[IcebergProfile],
    *,
    dataset_name: str,
    require_real: bool = False,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for profile in dataset:
        try:
            weights = await infer_initial_weights_with_llm(profile)
            rows.append(
                _reference_row(
                    dataset_name,
                    profile.profile_id,
                    INITIAL_LLM_BASELINE,
                    compute_mae(weights, profile.ground_truth_weights),
                    weights,
                    status="ok",
                )
            )
        except Exception as exc:
            if require_real:
                raise
            rows.append(
                _reference_row(
                    dataset_name,
                    profile.profile_id,
                    INITIAL_LLM_BASELINE,
                    1.0,
                    {},
                    status="error",
                    error_message=f"{type(exc).__name__}: {exc}",
                )
            )
    return rows


async def infer_v1_hybrid_weights(
    profile: IcebergProfile,
    *,
    timeout_seconds: float = 180.0,
) -> dict[str, float]:
    import asyncio

    from gaokaollm_bench.sandbox.v1_hybrid_rag import V1HybridRagBaselineAgent

    agent = V1HybridRagBaselineAgent()
    _, state = await asyncio.wait_for(
        agent.chat(profile.explicit_query),
        timeout=timeout_seconds,
    )
    candidates = (
        state.get("second_stage_reranked_candidates")
        or state.get("baseline_results")
        or []
    )
    if not isinstance(candidates, list):
        candidates = []
    return infer_weights_from_v1_candidates(
        [dict(candidate) for candidate in candidates if isinstance(candidate, dict)],
        query_text=profile.explicit_query,
    )


async def compute_v1_hybrid_baseline(
    dataset: list[IcebergProfile],
    *,
    dataset_name: str,
    require_real: bool = False,
    timeout_seconds: float = 180.0,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    values: list[float] = []
    for profile in dataset:
        try:
            weights = await infer_v1_hybrid_weights(
                profile,
                timeout_seconds=timeout_seconds,
            )
            mae_error = compute_mae(weights, profile.ground_truth_weights)
            values.append(mae_error)
            rows.append(
                _reference_row(
                    dataset_name,
                    profile.profile_id,
                    V1_HYBRID_BASELINE,
                    mae_error,
                    weights,
                    status="ok",
                )
            )
        except Exception as exc:
            if require_real:
                raise
            rows.append(
                _reference_row(
                    dataset_name,
                    profile.profile_id,
                    V1_HYBRID_BASELINE,
                    1.0,
                    {},
                    status="error",
                    error_message=f"{type(exc).__name__}: {exc}",
                )
            )
    if values:
        rows.insert(
            0,
            _reference_row(
                dataset_name,
                "__dataset__",
                V1_HYBRID_BASELINE,
                sum(values) / len(values),
                {"n": len(values), "std_mae": _std(values)},
                status="ok",
            ),
        )
    return rows


def random_baseline_rows(
    dataset: list[IcebergProfile],
    *,
    dataset_name: str,
    samples: int = 50_000,
    seed: int = 20260513,
) -> list[dict[str, Any]]:
    result = estimate_random_baseline(dataset, samples=samples, seed=seed)
    rows = [
        _reference_row(
            dataset_name,
            "__dataset__",
            RANDOM_BASELINE,
            float(result["mean_mae"]),
            {
                "samples": samples,
                "seed": seed,
                "std_mae": float(result["std_mae"]),
                "expected_f1": float(result["expected_f1"]),
                "std_f1": float(result["std_f1"]),
            },
            status="ok",
        )
    ]
    for profile_row in result["profile_rows"]:
        rows.append(
            _reference_row(
                dataset_name,
                str(profile_row["profile_id"]),
                RANDOM_BASELINE,
                float(profile_row["mean_mae"]),
                {
                    "samples": samples,
                    "seed": seed,
                    "std_mae": float(profile_row["std_mae"]),
                    "expected_f1": float(profile_row["expected_f1"]),
                    "std_f1": float(profile_row["std_f1"]),
                },
                status="ok",
            )
        )
    return rows


def _reference_row(
    dataset_name: str,
    profile_id: str,
    baseline_type: str,
    mae_error: float,
    weights: dict[str, Any],
    *,
    status: str,
    error_message: str = "",
) -> dict[str, Any]:
    return {
        "dataset": dataset_name,
        "profile_id": profile_id,
        "baseline_type": baseline_type,
        "mae_error": float(mae_error),
        "weights": json.dumps(weights, ensure_ascii=False, sort_keys=True),
        "status": status,
        "error_message": error_message,
    }


def write_reference_csv(
    rows: list[dict[str, Any]],
    output_dir: str | Path | None = None,
) -> str:
    csv_dir = Path(output_dir) if output_dir is not None else RESULTS_DIR
    csv_dir.mkdir(parents=True, exist_ok=True)
    csv_path = csv_dir / "reference_baselines.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(REFERENCE_FIELDS))
        writer.writeheader()
        writer.writerows(rows)
    return str(csv_path)


async def arun_reference_baselines(
    *,
    dataset_name: str = "robust",
    samples: int = 50_000,
    seed: int = 20260513,
    output_dir: str | Path | None = None,
    require_real: bool = False,
    include_v1_hybrid: bool = False,
    v1_timeout_seconds: float = 180.0,
) -> dict[str, Any]:
    dataset = get_dataset(dataset_name)
    rows = random_baseline_rows(
        dataset,
        dataset_name=dataset_name,
        samples=samples,
        seed=seed,
    )
    rows.extend(
        await compute_initial_llm_baseline(
            dataset,
            dataset_name=dataset_name,
            require_real=require_real,
        )
    )
    if include_v1_hybrid:
        rows.extend(
            await compute_v1_hybrid_baseline(
                dataset,
                dataset_name=dataset_name,
                require_real=require_real,
                timeout_seconds=v1_timeout_seconds,
            )
        )
    csv_path = write_reference_csv(rows, output_dir)
    classification_csv_path = merge_classification_metrics(
        classification_rows_from_reference_rows(rows, dataset),
        output_dir,
        replace_sources=(REFERENCE_SOURCE,),
    )
    print(_summary(rows))
    return {
        "rows": rows,
        "csv_path": csv_path,
        "classification_csv_path": classification_csv_path,
    }


def _summary(rows: list[dict[str, Any]]) -> str:
    lines = ["[reference_baselines] summary"]
    for baseline_type in (RANDOM_BASELINE, INITIAL_LLM_BASELINE, V1_HYBRID_BASELINE):
        values = [
            float(row["mae_error"])
            for row in rows
            if row.get("baseline_type") == baseline_type
            and row.get("profile_id") == "__dataset__"
            and row.get("status") == "ok"
        ]
        if not values:
            values = [
                float(row["mae_error"])
                for row in rows
                if row.get("baseline_type") == baseline_type
                and row.get("profile_id") != "__dataset__"
                and row.get("status") == "ok"
            ]
        if values:
            lines.append(
                f"  {baseline_type}: n={len(values)} mean_mae={sum(values) / len(values):.6f}"
            )
    return "\n".join(lines)


def run_cli(argv: list[str] | None = None) -> dict[str, Any]:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--dataset", choices=("smoke", "robust", "all"), default="robust"
    )
    parser.add_argument("--samples", type=int, default=50_000)
    parser.add_argument("--seed", type=int, default=20260513)
    parser.add_argument("--require-real", action="store_true")
    parser.add_argument("--include-v1-hybrid", action="store_true")
    parser.add_argument("--v1-timeout", type=float, default=180.0)
    args = parser.parse_args(argv)

    import asyncio

    result = asyncio.run(
        arun_reference_baselines(
            dataset_name=args.dataset,
            samples=args.samples,
            seed=args.seed,
            output_dir=RESULTS_DIR,
            require_real=args.require_real,
            include_v1_hybrid=args.include_v1_hybrid,
            v1_timeout_seconds=args.v1_timeout,
        )
    )
    print(f"[reference_baselines] wrote {result['csv_path']}")
    return result


if __name__ == "__main__":
    run_cli()
