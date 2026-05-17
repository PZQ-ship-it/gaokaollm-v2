"""Run unified iceberg benchmark matrices for baseline and ablation experiments."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

from dotenv import load_dotenv


DEFAULT_PERSONAS = Path(
    "gaokaollm_bench/sample_data/unified_iceberg_personas_1c6c_real_db_180.json"
)
DEFAULT_MODELS_FILE = Path("models.txt")
DEFAULT_BASELINE_ROOT = Path("gaokaollm_bench/outputs/unified_baseline_arena")
DEFAULT_ABLATION_ROOT = Path("gaokaollm_bench/outputs/unified_ablation_arena")
DEFAULT_SMOKE_ROOT = Path("gaokaollm_bench/outputs/unified_smoke_arena")
DEFAULT_BASELINE_TARGETS = ("app_pareto", "v1_prompt_direct", "v1_prompt_cot")
DEFAULT_ABLATION_TARGETS = (
    "app_pareto_full",
    "app_pareto_no_ucb",
    "app_pareto_no_tracker",
)


def read_models(path: str | Path) -> list[str]:
    model_path = Path(path)
    if not model_path.exists():
        raise FileNotFoundError(model_path)
    models: list[str] = []
    for raw_line in model_path.read_text(encoding="utf-8-sig").splitlines():
        line = raw_line.strip().lstrip("\ufeff")
        if line and not line.startswith("#"):
            models.append(line)
    if not models:
        raise ValueError(f"no models found in {model_path}")
    return models


def safe_name(value: str) -> str:
    safe = value
    for token in ("\\", "/", ":", "*", "?", '"', "<", ">", "|", " "):
        safe = safe.replace(token, "_")
    return safe


def summary_is_complete(
    summary_path: Path, *, target: str, expected_cases: int
) -> bool:
    if not summary_path.exists():
        return False
    try:
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    metrics = dict(summary.get("targets") or {}).get(target)
    if not isinstance(metrics, dict):
        return False
    try:
        cases = int(float(metrics.get("cases") or 0))
        completed = int(float(metrics.get("completed_cases") or 0))
        failed = int(float(metrics.get("failed_cases") or 0))
    except (TypeError, ValueError):
        return False
    return cases == expected_cases and completed == expected_cases and failed == 0


def count_personas(path: str | Path, *, limit: int | None) -> int:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(data, dict) and isinstance(data.get("items"), list):
        count = len(data["items"])
    elif isinstance(data, list):
        count = len(data)
    else:
        raise ValueError("personas file must contain a list or {'items': [...]}")
    return min(count, limit) if limit is not None else count


def write_run_meta(
    output_dir: Path,
    *,
    suite: str,
    model: str,
    target: str,
    personas: Path,
    expected_cases: int,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "suite": suite,
        "model": model,
        "model_safe": safe_name(model),
        "target": target,
        "personas": str(personas),
        "expected_cases": expected_cases,
    }
    (output_dir / "run_meta.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def run_one_target(
    *,
    suite: str,
    model: str,
    target: str,
    personas: Path,
    output_dir: Path,
    expected_cases: int,
    max_turns: int,
    limit: int | None,
    simulator_model: str | None,
    judge_model: str | None,
    concurrency: int,
    case_retries: int,
    request_timeout: float,
    case_timeout: float | None,
    skip_existing: bool,
    offline_deterministic: bool,
) -> None:
    summary_path = output_dir / "summary.json"
    if skip_existing and summary_is_complete(
        summary_path,
        target=target,
        expected_cases=expected_cases,
    ):
        print(f"[unified] skip complete {suite}/{safe_name(model)}/{target}")
        return

    write_run_meta(
        output_dir,
        suite=suite,
        model=model,
        target=target,
        personas=personas,
        expected_cases=expected_cases,
    )
    env = dict(os.environ)
    env["OPENAI_MODEL"] = model
    command = [
        sys.executable,
        "-m",
        "gaokaollm_bench.tests.manual.agent_benchmark_run",
        "--personas",
        str(personas),
        "--targets",
        target,
        "--max-turns",
        str(max_turns),
        "--output-dir",
        str(output_dir),
        "--paper-summary",
        "",
        "--request-timeout",
        str(request_timeout),
        "--concurrency",
        str(concurrency),
        "--case-retries",
        str(case_retries),
    ]
    if limit is not None:
        command.extend(["--limit", str(limit)])
    if case_timeout is not None:
        command.extend(["--case-timeout", str(case_timeout)])
    if simulator_model:
        command.extend(["--simulator-model", simulator_model])
    if judge_model:
        command.extend(["--judge-model", judge_model])
    if offline_deterministic:
        command.append("--offline-deterministic")
    if skip_existing:
        command.append("--skip-existing-cases")

    print(f"[unified] run {suite}/{safe_name(model)}/{target}")
    subprocess.run(command, check=True, env=env)


def run_matrix(args: argparse.Namespace) -> None:
    load_dotenv()
    personas = Path(args.personas)
    models = read_models(args.models_file)
    if args.max_models is not None:
        models = models[: args.max_models]

    simulator_model = args.simulator_model or os.getenv("SMALL_MODEL")
    judge_model = args.judge_model or os.getenv("SMALL_MODEL")
    expected_cases = count_personas(personas, limit=args.limit)

    mode = args.mode
    baseline_root = Path(args.baseline_root)
    ablation_root = Path(args.ablation_root)
    if mode == "smoke":
        baseline_root = Path(args.smoke_root) / "baseline"
        ablation_root = Path(args.smoke_root) / "ablation"

    should_run_baseline = mode in {"smoke", "baseline", "all"}
    should_run_ablation = mode in {"smoke", "ablation", "all"}

    if should_run_baseline:
        for model in models:
            for target in args.baseline_targets:
                output_dir = baseline_root / safe_name(model) / target
                run_one_target(
                    suite="baseline",
                    model=model,
                    target=target,
                    personas=personas,
                    output_dir=output_dir,
                    expected_cases=expected_cases,
                    max_turns=args.max_turns,
                    limit=args.limit,
                    simulator_model=simulator_model,
                    judge_model=judge_model,
                    concurrency=args.concurrency,
                    case_retries=args.case_retries,
                    request_timeout=args.request_timeout,
                    case_timeout=args.case_timeout,
                    skip_existing=args.skip_existing,
                    offline_deterministic=args.offline_deterministic,
                )

    if should_run_ablation:
        main_model = models[0]
        for target in args.ablation_targets:
            output_dir = ablation_root / safe_name(main_model) / target
            run_one_target(
                suite="ablation",
                model=main_model,
                target=target,
                personas=personas,
                output_dir=output_dir,
                expected_cases=expected_cases,
                max_turns=args.max_turns,
                limit=args.limit,
                simulator_model=simulator_model,
                judge_model=judge_model,
                concurrency=args.concurrency,
                case_retries=args.case_retries,
                request_timeout=args.request_timeout,
                case_timeout=args.case_timeout,
                skip_existing=args.skip_existing,
                offline_deterministic=args.offline_deterministic,
            )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run unified iceberg baseline and ablation benchmark matrices."
    )
    parser.add_argument(
        "--mode",
        choices=("smoke", "baseline", "ablation", "all"),
        default="all",
    )
    parser.add_argument("--models-file", default=str(DEFAULT_MODELS_FILE))
    parser.add_argument("--personas", default=str(DEFAULT_PERSONAS))
    parser.add_argument(
        "--baseline-targets",
        nargs="+",
        default=list(DEFAULT_BASELINE_TARGETS),
    )
    parser.add_argument(
        "--ablation-targets",
        nargs="+",
        default=list(DEFAULT_ABLATION_TARGETS),
    )
    parser.add_argument("--baseline-root", default=str(DEFAULT_BASELINE_ROOT))
    parser.add_argument("--ablation-root", default=str(DEFAULT_ABLATION_ROOT))
    parser.add_argument("--smoke-root", default=str(DEFAULT_SMOKE_ROOT))
    parser.add_argument("--max-models", type=int, default=None)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--max-turns", type=int, default=6)
    parser.add_argument("--simulator-model", default=None)
    parser.add_argument("--judge-model", default=None)
    parser.add_argument("--concurrency", type=int, default=10)
    parser.add_argument("--case-retries", type=int, default=2)
    parser.add_argument("--request-timeout", type=float, default=90.0)
    parser.add_argument("--case-timeout", type=float, default=300.0)
    parser.add_argument("--skip-existing", action="store_true")
    parser.add_argument("--offline-deterministic", action="store_true")
    return parser


def main() -> None:
    run_matrix(build_parser().parse_args())


if __name__ == "__main__":
    main()
