"""Adaptive controller for unified iceberg benchmark runs.

The controller first probes a small sample with increasing concurrency, then runs
the full matrix by constraint-count levels. Completed case rows are preserved by
the lower-level benchmark runner, so failed cases can be retried with a lower
concurrency without wasting successful API calls.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from dotenv import load_dotenv


DEFAULT_PERSONAS = Path(
    "gaokaollm_bench/sample_data/unified_iceberg_personas_1c6c_real_db_180.json"
)
DEFAULT_SPLIT_DIR = Path("gaokaollm_bench/sample_data/unified_by_constraint")
DEFAULT_OUTPUT_ROOT = Path("gaokaollm_bench/outputs/unified_adaptive_arena")
DEFAULT_PROBE_ROOT = Path("gaokaollm_bench/outputs/unified_concurrency_probe")
DEFAULT_LOG_DIR = Path("app/evaluation/results/logs")
DEFAULT_BASELINE_TARGETS = ("app_pareto", "v1_prompt_direct", "v1_prompt_cot")
DEFAULT_ABLATION_TARGETS = (
    "app_pareto_full",
    "app_pareto_no_ucb",
    "app_pareto_no_tracker",
)
TRANSIENT_ERROR_TOKENS = (
    "Timeout",
    "APITimeout",
    "APIConnection",
    "Connection error",
)


@dataclass(frozen=True)
class RunStats:
    output_dir: Path
    target: str
    expected_cases: int
    rows: int
    ok: int
    failed: int
    transient_failures: int
    elapsed_seconds: float

    @property
    def failure_rate(self) -> float:
        return self.failed / self.expected_cases if self.expected_cases else 0.0

    @property
    def transient_rate(self) -> float:
        return (
            self.transient_failures / self.expected_cases
            if self.expected_cases
            else 0.0
        )

    @property
    def complete(self) -> bool:
        return self.ok >= self.expected_cases and self.failed == 0


def read_models(path: str | Path) -> list[str]:
    model_path = Path(path)
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


def load_personas(path: str | Path) -> list[dict[str, Any]]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(data, dict) and isinstance(data.get("items"), list):
        data = data["items"]
    if not isinstance(data, list):
        raise ValueError("personas file must contain a list or {'items': [...]}")
    return [item for item in data if isinstance(item, dict)]


def constraint_count(persona: dict[str, Any]) -> int | None:
    background = persona.get("background") if isinstance(persona, dict) else {}
    try:
        return int((background or {}).get("constraint_count"))
    except (TypeError, ValueError):
        return None


def ensure_constraint_splits(
    personas_path: str | Path,
    split_dir: str | Path,
    counts: list[int],
) -> dict[int, Path]:
    personas = load_personas(personas_path)
    out_dir = Path(split_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    paths: dict[int, Path] = {}
    for count in counts:
        rows = [item for item in personas if constraint_count(item) == count]
        if not rows:
            raise ValueError(f"no personas found for constraint_count={count}")
        out = out_dir / f"unified_iceberg_personas_{count}c.json"
        out.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
        paths[count] = out
    return paths


def write_run_meta(
    output_dir: Path,
    *,
    suite: str,
    model: str,
    target: str,
    personas: Path,
    expected_cases: int,
    constraint_count_value: int | None,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "suite": suite,
        "model": model,
        "model_safe": safe_name(model),
        "target": target,
        "personas": str(personas),
        "expected_cases": expected_cases,
        "constraint_count": constraint_count_value,
    }
    (output_dir / "run_meta.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def read_report_stats(
    output_dir: Path,
    *,
    target: str,
    expected_cases: int,
    elapsed_seconds: float,
) -> RunStats:
    report_path = output_dir / "reports" / f"{target}.jsonl"
    rows = 0
    ok = 0
    failed = 0
    transient = 0
    if report_path.exists():
        for line in report_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            rows += 1
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                failed += 1
                continue
            if row.get("status") == "ok":
                ok += 1
            else:
                failed += 1
                error_blob = f"{row.get('error_type') or ''} {row.get('error') or ''}"
                if any(token in error_blob for token in TRANSIENT_ERROR_TOKENS):
                    transient += 1
    return RunStats(
        output_dir=output_dir,
        target=target,
        expected_cases=expected_cases,
        rows=rows,
        ok=ok,
        failed=failed,
        transient_failures=transient,
        elapsed_seconds=elapsed_seconds,
    )


def run_agent_benchmark(
    *,
    model: str,
    target: str,
    personas: Path,
    output_dir: Path,
    suite: str,
    expected_cases: int,
    constraint_count_value: int | None,
    concurrency: int,
    case_retries: int,
    request_timeout: float,
    case_timeout: float,
    max_turns: int,
    simulator_model: str | None,
    judge_model: str | None,
    limit: int | None,
    log_dir: Path,
) -> RunStats:
    write_run_meta(
        output_dir,
        suite=suite,
        model=model,
        target=target,
        personas=personas,
        expected_cases=expected_cases,
        constraint_count_value=constraint_count_value,
    )
    log_dir.mkdir(parents=True, exist_ok=True)
    log_prefix = (
        f"{suite}_c{constraint_count_value or 'probe'}_"
        f"{safe_name(model)}_{target}_p{concurrency}"
    )
    stdout_path = log_dir / f"{log_prefix}.stdout.log"
    stderr_path = log_dir / f"{log_prefix}.stderr.log"
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
        "--case-timeout",
        str(case_timeout),
        "--concurrency",
        str(concurrency),
        "--case-retries",
        str(case_retries),
        "--skip-existing-cases",
    ]
    if simulator_model:
        command.extend(["--simulator-model", simulator_model])
    if judge_model:
        command.extend(["--judge-model", judge_model])
    if limit is not None:
        command.extend(["--limit", str(limit)])
    env = dict(os.environ)
    env["OPENAI_MODEL"] = model
    started = time.monotonic()
    with (
        stdout_path.open("a", encoding="utf-8") as stdout,
        stderr_path.open(
            "a",
            encoding="utf-8",
        ) as stderr,
    ):
        subprocess.run(command, check=False, env=env, stdout=stdout, stderr=stderr)
    elapsed = time.monotonic() - started
    return read_report_stats(
        output_dir,
        target=target,
        expected_cases=expected_cases,
        elapsed_seconds=elapsed,
    )


def reduce_concurrency(current: int, *, minimum: int) -> int:
    if current <= minimum:
        return minimum
    return max(minimum, max(1, current // 2))


def run_until_complete(
    *,
    model: str,
    target: str,
    personas: Path,
    output_dir: Path,
    suite: str,
    expected_cases: int,
    constraint_count_value: int | None,
    initial_concurrency: int,
    min_concurrency: int,
    case_retries: int,
    request_timeout: float,
    case_timeout: float,
    max_turns: int,
    simulator_model: str | None,
    judge_model: str | None,
    failure_threshold: float,
    timeout_threshold: float,
    batch_attempts: int,
    log_dir: Path,
    limit: int | None = None,
) -> RunStats:
    concurrency = max(min_concurrency, initial_concurrency)
    last_stats: RunStats | None = None
    for attempt in range(1, max(1, batch_attempts) + 1):
        stats = run_agent_benchmark(
            model=model,
            target=target,
            personas=personas,
            output_dir=output_dir,
            suite=suite,
            expected_cases=expected_cases,
            constraint_count_value=constraint_count_value,
            concurrency=concurrency,
            case_retries=case_retries,
            request_timeout=request_timeout,
            case_timeout=case_timeout,
            max_turns=max_turns,
            simulator_model=simulator_model,
            judge_model=judge_model,
            limit=limit,
            log_dir=log_dir,
        )
        print(
            "[adaptive] "
            f"{suite}/c{constraint_count_value}/{safe_name(model)}/{target} "
            f"attempt={attempt} concurrency={concurrency} "
            f"ok={stats.ok}/{stats.expected_cases} failed={stats.failed} "
            f"transient={stats.transient_failures} "
            f"elapsed={stats.elapsed_seconds:.1f}s"
        )
        last_stats = stats
        if stats.complete:
            return stats
        should_reduce = (
            stats.failure_rate >= failure_threshold
            or stats.transient_rate >= timeout_threshold
            or (stats.failed > 0 and attempt >= 2)
        )
        if should_reduce:
            new_concurrency = reduce_concurrency(concurrency, minimum=min_concurrency)
            if new_concurrency < concurrency:
                print(
                    "[adaptive] reducing concurrency "
                    f"{concurrency} -> {new_concurrency} for {target}"
                )
                concurrency = new_concurrency
    assert last_stats is not None
    return last_stats


def probe_concurrency(
    args: argparse.Namespace, personas_by_count: dict[int, Path]
) -> int:
    models = read_models(args.models_file)
    model = models[0]
    probe_personas = personas_by_count[args.probe_constraint_count]
    expected_cases = min(args.probe_limit, len(load_personas(probe_personas)))
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    selected = max(1, args.probe_concurrency_levels[0])
    previous_good = selected
    probe_rows: list[dict[str, Any]] = []
    for concurrency in args.probe_concurrency_levels:
        output_dir = (
            Path(args.probe_root)
            / run_id
            / f"c{args.probe_constraint_count}"
            / f"p{concurrency}"
            / safe_name(model)
            / args.probe_target
        )
        stats = run_agent_benchmark(
            model=model,
            target=args.probe_target,
            personas=probe_personas,
            output_dir=output_dir,
            suite="probe",
            expected_cases=expected_cases,
            constraint_count_value=args.probe_constraint_count,
            concurrency=concurrency,
            case_retries=args.case_retries,
            request_timeout=args.request_timeout,
            case_timeout=args.case_timeout,
            max_turns=args.max_turns,
            simulator_model=args.simulator_model,
            judge_model=args.judge_model,
            limit=args.probe_limit,
            log_dir=Path(args.log_dir),
        )
        row = {
            "concurrency": concurrency,
            "ok": stats.ok,
            "expected_cases": stats.expected_cases,
            "failed": stats.failed,
            "transient_failures": stats.transient_failures,
            "failure_rate": stats.failure_rate,
            "transient_rate": stats.transient_rate,
            "elapsed_seconds": stats.elapsed_seconds,
            "output_dir": str(output_dir),
        }
        probe_rows.append(row)
        print(
            "[adaptive_probe] "
            f"concurrency={concurrency} ok={stats.ok}/{stats.expected_cases} "
            f"failed={stats.failed} transient={stats.transient_failures} "
            f"failure_rate={stats.failure_rate:.3f} "
            f"transient_rate={stats.transient_rate:.3f}"
        )
        if (
            stats.failure_rate >= args.failure_threshold
            or stats.transient_rate >= args.timeout_threshold
        ):
            if concurrency == args.probe_concurrency_levels[0]:
                selected = reduce_concurrency(concurrency, minimum=1)
            else:
                selected = previous_good
            print(
                f"[adaptive_probe] threshold exceeded; selected_concurrency={selected}"
            )
            break
        previous_good = concurrency
        selected = concurrency

    report_path = Path(args.probe_root) / run_id / "probe_summary.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        json.dumps(
            {
                "selected_concurrency": selected,
                "rows": probe_rows,
                "model": model,
                "target": args.probe_target,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return selected


def run_model_target_jobs(
    *,
    models: list[str],
    target: str,
    personas: Path,
    output_root: Path,
    suite: str,
    constraint_count_value: int,
    expected_cases: int,
    initial_concurrency: int,
    args: argparse.Namespace,
) -> list[RunStats]:
    stats: list[RunStats] = []
    max_workers = max(1, min(args.parallel_models, len(models)))
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = []
        for model in models:
            output_dir = (
                output_root
                / f"c{constraint_count_value}"
                / suite
                / safe_name(model)
                / target
            )
            futures.append(
                executor.submit(
                    run_until_complete,
                    model=model,
                    target=target,
                    personas=personas,
                    output_dir=output_dir,
                    suite=suite,
                    expected_cases=expected_cases,
                    constraint_count_value=constraint_count_value,
                    initial_concurrency=initial_concurrency,
                    min_concurrency=args.min_concurrency,
                    case_retries=args.case_retries,
                    request_timeout=args.request_timeout,
                    case_timeout=args.case_timeout,
                    max_turns=args.max_turns,
                    simulator_model=args.simulator_model,
                    judge_model=args.judge_model,
                    failure_threshold=args.failure_threshold,
                    timeout_threshold=args.timeout_threshold,
                    batch_attempts=args.batch_attempts,
                    log_dir=Path(args.log_dir),
                )
            )
        for future in as_completed(futures):
            stats.append(future.result())
    return stats


def run_by_constraint(
    args: argparse.Namespace, personas_by_count: dict[int, Path]
) -> None:
    models = read_models(args.models_file)
    if args.max_models is not None:
        models = models[: args.max_models]
    output_root = Path(args.output_root)
    selected_concurrency = args.initial_concurrency
    if args.auto_tune:
        selected_concurrency = probe_concurrency(args, personas_by_count)
    if args.override_concurrency is not None:
        selected_concurrency = args.override_concurrency

    for count in args.constraint_counts:
        personas = personas_by_count[count]
        expected_cases = len(load_personas(personas))
        print(
            f"[adaptive] starting constraint_count={count} "
            f"cases={expected_cases} concurrency={selected_concurrency}"
        )

        if args.mode in {"run", "all", "baseline"}:
            for target in args.baseline_targets:
                run_model_target_jobs(
                    models=models,
                    target=target,
                    personas=personas,
                    output_root=output_root,
                    suite="baseline",
                    constraint_count_value=count,
                    expected_cases=expected_cases,
                    initial_concurrency=selected_concurrency,
                    args=args,
                )

        if args.mode in {"run", "all", "ablation"}:
            main_model = models[0]
            for target in args.ablation_targets:
                run_model_target_jobs(
                    models=[main_model],
                    target=target,
                    personas=personas,
                    output_root=output_root,
                    suite="ablation",
                    constraint_count_value=count,
                    expected_cases=expected_cases,
                    initial_concurrency=selected_concurrency,
                    args=args,
                )


def parse_int_list(values: list[str] | None, default: tuple[int, ...]) -> list[int]:
    if not values:
        return list(default)
    parsed: list[int] = []
    for value in values:
        for part in str(value).split(","):
            if part.strip():
                parsed.append(int(part.strip()))
    return parsed


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Adaptive concurrency controller for unified iceberg benchmark."
    )
    parser.add_argument(
        "--mode",
        choices=("probe", "run", "all", "baseline", "ablation"),
        default="all",
    )
    parser.add_argument("--personas", default=str(DEFAULT_PERSONAS))
    parser.add_argument("--models-file", default="models.txt")
    parser.add_argument("--split-dir", default=str(DEFAULT_SPLIT_DIR))
    parser.add_argument("--output-root", default=str(DEFAULT_OUTPUT_ROOT))
    parser.add_argument("--probe-root", default=str(DEFAULT_PROBE_ROOT))
    parser.add_argument("--log-dir", default=str(DEFAULT_LOG_DIR))
    parser.add_argument("--constraint-counts", nargs="*", default=None)
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
    parser.add_argument("--max-models", type=int, default=None)
    parser.add_argument("--parallel-models", type=int, default=1)
    parser.add_argument("--initial-concurrency", type=int, default=10)
    parser.add_argument("--override-concurrency", type=int, default=None)
    parser.add_argument("--min-concurrency", type=int, default=1)
    parser.add_argument("--batch-attempts", type=int, default=3)
    parser.add_argument("--case-retries", type=int, default=2)
    parser.add_argument("--request-timeout", type=float, default=90.0)
    parser.add_argument("--case-timeout", type=float, default=300.0)
    parser.add_argument("--max-turns", type=int, default=6)
    parser.add_argument("--simulator-model", default=None)
    parser.add_argument("--judge-model", default=None)
    parser.add_argument("--auto-tune", action="store_true")
    parser.add_argument("--probe-target", default="app_pareto")
    parser.add_argument("--probe-constraint-count", type=int, default=1)
    parser.add_argument("--probe-limit", type=int, default=4)
    parser.add_argument(
        "--probe-concurrency-levels",
        nargs="+",
        type=int,
        default=[2, 5, 10],
    )
    parser.add_argument("--failure-threshold", type=float, default=0.30)
    parser.add_argument("--timeout-threshold", type=float, default=0.20)
    return parser


def main() -> None:
    load_dotenv()
    args = build_parser().parse_args()
    args.constraint_counts = parse_int_list(args.constraint_counts, (1, 2, 3, 4, 5, 6))
    args.simulator_model = args.simulator_model or os.getenv("SMALL_MODEL")
    args.judge_model = args.judge_model or os.getenv("SMALL_MODEL")
    split_counts = sorted(set([*args.constraint_counts, args.probe_constraint_count]))
    personas_by_count = ensure_constraint_splits(
        args.personas,
        args.split_dir,
        split_counts,
    )
    if args.mode == "probe":
        selected = probe_concurrency(args, personas_by_count)
        print(f"[adaptive_probe] selected_concurrency={selected}")
        return
    run_by_constraint(args, personas_by_count)


if __name__ == "__main__":
    main()
