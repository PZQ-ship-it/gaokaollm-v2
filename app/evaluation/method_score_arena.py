import argparse
import csv
import json
import math
import os
import subprocess
import sys
from pathlib import Path
from typing import Any


RESULTS_DIR = Path(__file__).parent / "results"
DEFAULT_OUTPUT_ROOT = Path("gaokaollm_bench/outputs/method_score_arena")
DEFAULT_CSV = RESULTS_DIR / "method_score_arena.csv"
DEFAULT_SUMMARY = RESULTS_DIR / "method_score_arena_summary.md"
DEFAULT_SCATTER_PNG = RESULTS_DIR / "fig_method_score_scatter.png"
DEFAULT_SCATTER_PDF = RESULTS_DIR / "fig_method_score_scatter.pdf"
DEFAULT_TARGETS = ("app_pareto", "v1_prompt_direct", "v1_prompt_cot")


def read_models(path: str | Path = "models.txt") -> list[str]:
    model_path = Path(path)
    if not model_path.exists():
        raise FileNotFoundError(f"Model list not found: {model_path}")
    models = []
    for raw_line in model_path.read_text(encoding="utf-8-sig").splitlines():
        line = raw_line.strip().lstrip("\ufeff")
        if line and not line.startswith("#"):
            models.append(line)
    if not models:
        raise ValueError(f"No models found in {model_path}")
    return models


def _safe_name(value: str) -> str:
    return (
        value.replace("\\", "_").replace("/", "_").replace(":", "_").replace(" ", "_")
    )


def _model_short(model: str) -> str:
    return model.split("/")[-1] if "/" in model else model


def benchmark_score(
    *,
    elicitation_success_rate: float,
    mean_pareto_gain: float,
    mean_hallucination_rate: float,
    avg_turns: float,
) -> float:
    """Presentation score for scatter plots; raw metrics remain in the CSV."""

    return (
        100.0 * elicitation_success_rate
        + 5.0 * mean_pareto_gain
        - 100.0 * mean_hallucination_rate
        - 0.5 * avg_turns
    )


def run_benchmark_for_model(
    *,
    model: str,
    personas: str,
    output_dir: Path,
    targets: tuple[str, ...],
    max_turns: int,
    limit: int | None,
    simulator_model: str | None,
    judge_model: str | None,
    offline_deterministic: bool,
    request_timeout: float,
    case_timeout: float | None,
    concurrency: int,
    case_retries: int,
    skip_existing: bool,
) -> None:
    summary_path = output_dir / "summary.json"
    if skip_existing and _summary_is_complete(summary_path, targets):
        return
    if skip_existing and summary_path.exists():
        print(
            "[method_score_arena] existing summary has no completed results; "
            f"rerunning {output_dir.name}"
        )

    output_dir.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ)
    env["OPENAI_MODEL"] = model
    command = [
        sys.executable,
        "-m",
        "gaokaollm_bench.tests.manual.agent_benchmark_run",
        "--personas",
        personas,
        "--targets",
        *targets,
        "--max-turns",
        str(max_turns),
        "--output-dir",
        str(output_dir),
        "--paper-summary",
        "",
        "--request-timeout",
        str(request_timeout),
    ]
    if case_timeout is not None:
        command.extend(["--case-timeout", str(case_timeout)])
    command.extend(["--concurrency", str(concurrency)])
    command.extend(["--case-retries", str(case_retries)])
    if limit is not None:
        command.extend(["--limit", str(limit)])
    if simulator_model:
        command.extend(["--simulator-model", simulator_model])
    if judge_model:
        command.extend(["--judge-model", judge_model])
    if offline_deterministic:
        command.append("--offline-deterministic")

    subprocess.run(command, check=True, env=env)


def _summary_is_complete(summary_path: Path, targets: tuple[str, ...]) -> bool:
    if not summary_path.exists():
        return False
    try:
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False

    target_metrics = dict(summary.get("targets") or {})
    for target in targets:
        metrics = target_metrics.get(target)
        if not metrics:
            return False
        cases = int(_float(metrics.get("cases")))
        completed = int(_float(metrics.get("completed_cases")))
        failed = int(_float(metrics.get("failed_cases")))
        if cases <= 0 or completed < cases or failed > 0:
            return False
    return True


def collect_rows(output_root: str | Path, csv_path: str | Path = DEFAULT_CSV) -> Path:
    root = Path(output_root)
    rows: list[dict[str, Any]] = []
    for summary_path in sorted(root.glob("*/summary.json")):
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        model = summary_path.parent.name
        for target, metrics in dict(summary.get("targets") or {}).items():
            success = _float(metrics.get("elicitation_success_rate"))
            gain = _float(metrics.get("mean_pareto_gain"))
            hallucination = _float(metrics.get("mean_hallucination_rate"))
            turns = _float(metrics.get("avg_turns"))
            rows.append(
                {
                    "model": model,
                    "model_short": _model_short(model),
                    "target": target,
                    "cases": metrics.get("cases", 0),
                    "completed_cases": metrics.get("completed_cases", 0),
                    "failed_cases": metrics.get("failed_cases", 0),
                    "elicitation_success_rate": success,
                    "mean_pareto_gain": gain,
                    "mean_hallucination_rate": hallucination,
                    "avg_turns": turns,
                    "benchmark_score": benchmark_score(
                        elicitation_success_rate=success,
                        mean_pareto_gain=gain,
                        mean_hallucination_rate=hallucination,
                        avg_turns=turns,
                    ),
                    "summary_path": str(summary_path),
                }
            )

    out = Path(csv_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8", newline="") as file:
        fieldnames = [
            "model",
            "model_short",
            "target",
            "cases",
            "completed_cases",
            "failed_cases",
            "elicitation_success_rate",
            "mean_pareto_gain",
            "mean_hallucination_rate",
            "avg_turns",
            "benchmark_score",
            "summary_path",
        ]
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    return out


def _float(value: Any) -> float:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return 0.0
    return numeric if math.isfinite(numeric) else 0.0


def write_summary(
    csv_path: str | Path = DEFAULT_CSV,
    summary_path: str | Path = DEFAULT_SUMMARY,
) -> Path:
    rows = _read_rows(csv_path)
    completed_cases = sum(int(_float(row.get("completed_cases"))) for row in rows)
    failed_cases = sum(int(_float(row.get("failed_cases"))) for row in rows)
    grouped: dict[str, list[dict[str, str]]] = {}
    for row in rows:
        grouped.setdefault(row["target"], []).append(row)
    lines = [
        "# Method Score Arena Summary",
        "",
        "This arena compares method-level targets on the same benchmark task.",
        "The scatter score is for visualization only; raw success, gain, hallucination and turns remain reported.",
        "",
        f"Completed cases: {completed_cases}; failed cases: {failed_cases}.",
        "",
        "| Target | n models | Score mean | Success mean | Gain mean | Hallucination mean | Turns mean |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for target, target_rows in sorted(grouped.items()):
        lines.append(
            f"| {target} | {len(target_rows)} | "
            f"{_mean(target_rows, 'benchmark_score'):.3f} | "
            f"{_mean(target_rows, 'elicitation_success_rate'):.3f} | "
            f"{_mean(target_rows, 'mean_pareto_gain'):.3f} | "
            f"{_mean(target_rows, 'mean_hallucination_rate'):.3f} | "
            f"{_mean(target_rows, 'avg_turns'):.2f} |"
        )
    out = Path(summary_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out


def _read_rows(csv_path: str | Path) -> list[dict[str, str]]:
    path = Path(csv_path)
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as file:
        return list(csv.DictReader(file))


def _mean(rows: list[dict[str, str]], key: str) -> float:
    values = [_float(row.get(key)) for row in rows]
    return sum(values) / len(values) if values else 0.0


def generate_scatter(
    csv_path: str | Path = DEFAULT_CSV,
    output_png: str | Path = DEFAULT_SCATTER_PNG,
    output_pdf: str | Path = DEFAULT_SCATTER_PDF,
) -> dict[str, str]:
    try:
        import pandas as pd
        import seaborn as sns
        from matplotlib import pyplot as plt
    except ImportError:
        return {}

    rows = _read_rows(csv_path)
    if not rows:
        return {}
    df = pd.DataFrame(rows)
    for column in (
        "benchmark_score",
        "elicitation_success_rate",
        "mean_pareto_gain",
        "mean_hallucination_rate",
        "avg_turns",
    ):
        df[column] = pd.to_numeric(df[column], errors="coerce")
    sns.set_theme(style="whitegrid")
    figure, ax = plt.subplots(figsize=(10.5, 5.8))
    sns.stripplot(
        data=df,
        x="model_short",
        y="benchmark_score",
        hue="target",
        dodge=True,
        jitter=0.18,
        size=8,
        ax=ax,
    )
    ax.set_xlabel("")
    ax.set_ylabel("Benchmark Score")
    ax.set_title("Method-Level Scores Across Models and Prompt Styles")
    ax.tick_params(axis="x", rotation=18)
    ax.legend(title="")
    figure.tight_layout()
    png = Path(output_png)
    pdf = Path(output_pdf)
    png.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(png, dpi=300)
    figure.savefig(pdf)
    plt.close(figure)
    return {"png": str(png), "pdf": str(pdf)}


def _scatter_outputs_for_csv(
    csv_path: str | Path,
    scatter_png: str | None,
    scatter_pdf: str | None,
) -> tuple[Path, Path]:
    csv = Path(csv_path)
    if scatter_png:
        png = Path(scatter_png)
    elif csv.name == DEFAULT_CSV.name:
        png = DEFAULT_SCATTER_PNG
    else:
        png = csv.with_name(f"fig_{csv.stem}.png")

    if scatter_pdf:
        pdf = Path(scatter_pdf)
    elif csv.name == DEFAULT_CSV.name:
        pdf = DEFAULT_SCATTER_PDF
    else:
        pdf = csv.with_name(f"fig_{csv.stem}.pdf")
    return png, pdf


def run_cli(argv: list[str] | None = None) -> dict[str, str]:
    parser = argparse.ArgumentParser()
    parser.add_argument("--models-file", default="models.txt")
    parser.add_argument(
        "--personas",
        default="gaokaollm_bench/sample_data/iceberg_personas_real_db_10.json",
    )
    parser.add_argument("--output-root", default=str(DEFAULT_OUTPUT_ROOT))
    parser.add_argument("--csv", default=str(DEFAULT_CSV))
    parser.add_argument("--summary", default=str(DEFAULT_SUMMARY))
    parser.add_argument("--scatter-png")
    parser.add_argument("--scatter-pdf")
    parser.add_argument("--targets", nargs="+", default=list(DEFAULT_TARGETS))
    parser.add_argument("--max-turns", type=int, default=6)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--max-models", type=int)
    parser.add_argument("--simulator-model")
    parser.add_argument("--judge-model")
    parser.add_argument("--request-timeout", type=float, default=90.0)
    parser.add_argument("--case-timeout", type=float, default=300.0)
    parser.add_argument("--concurrency", type=int, default=1)
    parser.add_argument("--case-retries", type=int, default=1)
    parser.add_argument("--offline-deterministic", action="store_true")
    parser.add_argument("--skip-existing", action="store_true")
    parser.add_argument("--collect-only", action="store_true")
    args = parser.parse_args(argv)

    models = read_models(args.models_file)
    if args.max_models:
        models = models[: args.max_models]
    root = Path(args.output_root)
    if not args.collect_only:
        for model in models:
            run_benchmark_for_model(
                model=model,
                personas=args.personas,
                output_dir=root / _safe_name(model),
                targets=tuple(args.targets),
                max_turns=args.max_turns,
                limit=args.limit,
                simulator_model=args.simulator_model,
                judge_model=args.judge_model,
                offline_deterministic=args.offline_deterministic,
                request_timeout=args.request_timeout,
                case_timeout=args.case_timeout,
                concurrency=args.concurrency,
                case_retries=args.case_retries,
                skip_existing=args.skip_existing,
            )
    csv_path = collect_rows(root, args.csv)
    summary_path = write_summary(csv_path, args.summary)
    scatter_png, scatter_pdf = _scatter_outputs_for_csv(
        csv_path,
        args.scatter_png,
        args.scatter_pdf,
    )
    scatter = generate_scatter(csv_path, scatter_png, scatter_pdf)
    rows = _read_rows(csv_path)
    if rows and all(int(_float(row.get("completed_cases"))) == 0 for row in rows):
        print(
            "[method_score_arena] warning: no completed benchmark cases; "
            "check database/API availability before using the scatter plot."
        )
    print(f"[method_score_arena] wrote {csv_path}")
    print(f"[method_score_arena] wrote {summary_path}")
    if scatter:
        print(f"[method_score_arena] wrote {scatter['png']}")
    return {"csv": str(csv_path), "summary": str(summary_path), **scatter}


if __name__ == "__main__":
    run_cli()
