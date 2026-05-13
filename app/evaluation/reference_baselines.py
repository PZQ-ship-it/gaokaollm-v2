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
from app.evaluation.schemas import IcebergProfile


PREFERENCE_KEYS = ("school", "major", "tuition", "quality", "geo")
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


class InitialPreferenceWeights(BaseModel):
    school: float = 0.2
    major: float = 0.2
    tuition: float = 0.2
    quality: float = 0.2
    geo: float = 0.2
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
            value = float(raw.get(key, 0.2))
        except (TypeError, ValueError):
            value = 0.2
        values[key] = max(0.0, min(1.0, value))
    total = sum(values.values())
    if not math.isfinite(total) or total <= 0.0:
        return {key: 1.0 / len(PREFERENCE_KEYS) for key in PREFERENCE_KEYS}
    return {key: values[key] / total for key in PREFERENCE_KEYS}


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
    dataset_values: list[float] = []

    for _ in range(samples):
        weights = _sample_dirichlet_uniform(rng)
        sample_total = 0.0
        for profile in dataset:
            value = compute_mae(weights, profile.ground_truth_weights)
            profile_sums[profile.profile_id] += value
            profile_sq_sums[profile.profile_id] += value * value
            sample_total += value
        if dataset:
            dataset_values.append(sample_total / len(dataset))

    rows: list[dict[str, Any]] = []
    for profile in dataset:
        mean = profile_sums[profile.profile_id] / samples
        variance = max(
            0.0,
            profile_sq_sums[profile.profile_id] / samples - mean * mean,
        )
        rows.append(
            {
                "profile_id": profile.profile_id,
                "mean_mae": mean,
                "std_mae": math.sqrt(variance),
            }
        )
    dataset_mean = sum(dataset_values) / len(dataset_values) if dataset_values else 0.0
    dataset_std = _std(dataset_values)
    return {"mean_mae": dataset_mean, "std_mae": dataset_std, "profile_rows": rows}


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
                "non-negative weights for school, major, tuition, quality, and geo. "
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
            {"samples": samples, "seed": seed, "std_mae": float(result["std_mae"])},
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
    csv_path = write_reference_csv(rows, output_dir)
    print(_summary(rows))
    return {"rows": rows, "csv_path": csv_path}


def _summary(rows: list[dict[str, Any]]) -> str:
    lines = ["[reference_baselines] summary"]
    for baseline_type in (RANDOM_BASELINE, INITIAL_LLM_BASELINE):
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
    args = parser.parse_args(argv)

    import asyncio

    result = asyncio.run(
        arun_reference_baselines(
            dataset_name=args.dataset,
            samples=args.samples,
            seed=args.seed,
            output_dir=RESULTS_DIR,
            require_real=args.require_real,
        )
    )
    print(f"[reference_baselines] wrote {result['csv_path']}")
    return result


if __name__ == "__main__":
    run_cli()
