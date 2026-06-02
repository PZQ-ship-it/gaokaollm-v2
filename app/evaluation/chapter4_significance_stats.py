from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd
from scipy import stats


RESULTS_DIR = Path("app/evaluation/results")
DEFAULT_BASELINE = RESULTS_DIR / "paper_replacement_baseline_results.csv"
DEFAULT_ABLATION = RESULTS_DIR / "paper_replacement_ablation_results.csv"
DEFAULT_OUTPUT = RESULTS_DIR / "chapter4_significance_ci.csv"
DEFAULT_SUMMARY = RESULTS_DIR / "chapter4_significance_summary.md"
BOOTSTRAP_SEED = 20260518
BOOTSTRAP_REPEATS = 10_000

METRIC_COLUMNS = {
    "F1@1": "recommendation_f1_at_1",
    "F1@3": "recommendation_f1_at_3",
    "F1@5": "recommendation_f1_at_5",
    "MAE": "mae",
}

TARGET_LABELS = {
    "app_pareto": "完整系统",
    "app_pareto_full": "完整系统",
    "v1_prompt_direct": "静态检索-直接提示",
    "v1_prompt_cot": "静态检索-思维链提示",
    "app_pareto_no_ucb": "去除主动探测",
    "app_pareto_no_tracker": "去除后验追踪",
}


@dataclass(frozen=True)
class Comparison:
    suite: str
    comparison_id: str
    full_target: str
    comparator_target: str
    pair_keys: tuple[str, ...]
    metrics: tuple[str, ...]
    expected_pairs: int


COMPARISONS = (
    Comparison(
        suite="baseline",
        comparison_id="full_vs_direct_prompt",
        full_target="app_pareto",
        comparator_target="v1_prompt_direct",
        pair_keys=("case_id", "model_key"),
        metrics=("F1@1", "F1@3", "F1@5"),
        expected_pairs=150,
    ),
    Comparison(
        suite="baseline",
        comparison_id="full_vs_cot_prompt",
        full_target="app_pareto",
        comparator_target="v1_prompt_cot",
        pair_keys=("case_id", "model_key"),
        metrics=("F1@1", "F1@3", "F1@5"),
        expected_pairs=150,
    ),
    Comparison(
        suite="ablation",
        comparison_id="full_vs_no_ucb",
        full_target="app_pareto_full",
        comparator_target="app_pareto_no_ucb",
        pair_keys=("case_id",),
        metrics=("MAE", "F1@1", "F1@3", "F1@5"),
        expected_pairs=30,
    ),
    Comparison(
        suite="ablation",
        comparison_id="full_vs_no_tracker",
        full_target="app_pareto_full",
        comparator_target="app_pareto_no_tracker",
        pair_keys=("case_id",),
        metrics=("MAE", "F1@1", "F1@3", "F1@5"),
        expected_pairs=30,
    ),
)


def _load_csv(path: Path, suite: str) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"{suite} input not found: {path}")
    df = pd.read_csv(path)
    required = {"case_id", "target", "status", *METRIC_COLUMNS.values()}
    missing = sorted(required - set(df.columns))
    if missing:
        raise ValueError(f"{suite} input is missing columns: {missing}")
    df = df[df["status"] == "ok"].copy()
    if suite == "baseline":
        if "model_alias" in df.columns:
            df["model_key"] = df["model_alias"].fillna(df.get("model", ""))
        elif "model" in df.columns:
            df["model_key"] = df["model"]
        else:
            raise ValueError("baseline input needs model_alias or model for pairing")
    return df


def _validate_counts(df: pd.DataFrame, suite: str) -> None:
    expected = {
        "baseline": {
            "app_pareto": (150, 30),
            "v1_prompt_direct": (150, 30),
            "v1_prompt_cot": (150, 30),
        },
        "ablation": {
            "app_pareto_full": (30, 30),
            "app_pareto_no_ucb": (30, 30),
            "app_pareto_no_tracker": (30, 30),
        },
    }[suite]
    for target, (rows, cases) in expected.items():
        sub = df[df["target"] == target]
        if len(sub) != rows or sub["case_id"].nunique() != cases:
            raise ValueError(
                f"{suite} target {target} expected {rows} rows/{cases} cases, "
                f"got {len(sub)} rows/{sub['case_id'].nunique()} cases"
            )


def _paired_values(df: pd.DataFrame, comp: Comparison, metric: str) -> pd.DataFrame:
    metric_col = METRIC_COLUMNS[metric]
    cols = [*comp.pair_keys, metric_col]
    full = (
        df[df["target"] == comp.full_target][cols]
        .rename(columns={metric_col: "full_value"})
        .copy()
    )
    other = (
        df[df["target"] == comp.comparator_target][cols]
        .rename(columns={metric_col: "comparator_value"})
        .copy()
    )
    paired = full.merge(other, on=list(comp.pair_keys), how="inner")
    paired = paired.dropna(subset=["full_value", "comparator_value"])
    paired["diff"] = paired["full_value"].astype(float) - paired[
        "comparator_value"
    ].astype(float)
    if len(paired) != comp.expected_pairs:
        raise ValueError(
            f"{comp.comparison_id} {metric} expected {comp.expected_pairs} pairs, "
            f"got {len(paired)}"
        )
    return paired


def _bootstrap_ci(
    diffs: np.ndarray, repeats: int, rng: np.random.Generator
) -> tuple[float, float]:
    n = len(diffs)
    sample_indices = rng.integers(0, n, size=(repeats, n))
    boot_means = diffs[sample_indices].mean(axis=1)
    lo, hi = np.percentile(boot_means, [2.5, 97.5])
    return float(lo), float(hi)


def _holm_adjust(p_values: Iterable[float]) -> list[float]:
    p_array = np.asarray(list(p_values), dtype=float)
    adjusted = np.full_like(p_array, np.nan, dtype=float)
    finite_idx = np.where(np.isfinite(p_array))[0]
    if len(finite_idx) == 0:
        return adjusted.tolist()
    order = finite_idx[np.argsort(p_array[finite_idx])]
    previous = 0.0
    m = len(order)
    for rank, original_idx in enumerate(order):
        raw = p_array[original_idx]
        adj = min(1.0, (m - rank) * raw)
        previous = max(previous, adj)
        adjusted[original_idx] = previous
    return adjusted.tolist()


def compute_statistics(
    baseline_path: Path,
    ablation_path: Path,
    repeats: int = BOOTSTRAP_REPEATS,
    seed: int = BOOTSTRAP_SEED,
) -> pd.DataFrame:
    baseline = _load_csv(baseline_path, "baseline")
    ablation = _load_csv(ablation_path, "ablation")
    _validate_counts(baseline, "baseline")
    _validate_counts(ablation, "ablation")

    frames = {"baseline": baseline, "ablation": ablation}
    rng = np.random.default_rng(seed)
    rows: list[dict[str, object]] = []
    for comp in COMPARISONS:
        df = frames[comp.suite]
        for metric in comp.metrics:
            paired = _paired_values(df, comp, metric)
            diffs = paired["diff"].to_numpy(dtype=float)
            ci_low, ci_high = _bootstrap_ci(diffs, repeats, rng)
            t_result = stats.ttest_rel(
                paired["full_value"].to_numpy(dtype=float),
                paired["comparator_value"].to_numpy(dtype=float),
                nan_policy="raise",
            )
            full_mean = float(paired["full_value"].mean())
            comparator_mean = float(paired["comparator_value"].mean())
            mean_diff = float(diffs.mean())
            better_direction = "lower" if metric == "MAE" else "higher"
            supports_full = mean_diff < 0 if metric == "MAE" else mean_diff > 0
            ci_excludes_zero = ci_low > 0 or ci_high < 0
            rows.append(
                {
                    "suite": comp.suite,
                    "comparison_id": comp.comparison_id,
                    "full_target": comp.full_target,
                    "full_label": TARGET_LABELS[comp.full_target],
                    "comparator_target": comp.comparator_target,
                    "comparator_label": TARGET_LABELS[comp.comparator_target],
                    "metric": metric,
                    "better_direction": better_direction,
                    "n_pairs": len(paired),
                    "full_mean": full_mean,
                    "comparator_mean": comparator_mean,
                    "mean_diff_full_minus_comparator": mean_diff,
                    "bootstrap_ci_low": ci_low,
                    "bootstrap_ci_high": ci_high,
                    "ci_excludes_zero": ci_excludes_zero,
                    "paired_t_statistic": float(t_result.statistic),
                    "paired_t_p_value": float(t_result.pvalue),
                    "supports_full": bool(supports_full),
                }
            )

    results = pd.DataFrame(rows)
    results["holm_p_value"] = np.nan
    for _, idx in results.groupby(["suite", "metric"]).groups.items():
        adjusted = _holm_adjust(results.loc[idx, "paired_t_p_value"].tolist())
        results.loc[idx, "holm_p_value"] = adjusted
    results["holm_significant_0_05"] = results["holm_p_value"] < 0.05
    return results


def _format_float(value: float, digits: int = 3) -> str:
    if not np.isfinite(value):
        return "NA"
    if abs(value) < 0.001 and value != 0:
        return f"{value:.2e}"
    return f"{value:.{digits}f}"


def write_summary(results: pd.DataFrame, path: Path, repeats: int, seed: int) -> None:
    lines = [
        "# Chapter 4 Paired Significance Statistics",
        "",
        f"- Bootstrap repeats: {repeats}",
        f"- Bootstrap seed: {seed}",
        "- Baseline pairing key: `case_id + model_alias`",
        "- Ablation pairing key: `case_id`",
        "- Difference column is always `full - comparator`; lower is better only for MAE.",
        "",
        "| Suite | Comparison | Metric | n | Full | Comparator | Diff | 95% CI | Holm p | Significant |",
        "|---|---|---:|---:|---:|---:|---:|---|---:|---|",
    ]
    for row in results.to_dict("records"):
        ci = (
            f"[{_format_float(row['bootstrap_ci_low'])}, "
            f"{_format_float(row['bootstrap_ci_high'])}]"
        )
        lines.append(
            "| {suite} | {full_label} vs {comparator_label} | {metric} | "
            "{n_pairs} | {full_mean} | {comparator_mean} | {diff} | {ci} | "
            "{holm_p} | {sig} |".format(
                suite=row["suite"],
                full_label=row["full_label"],
                comparator_label=row["comparator_label"],
                metric=row["metric"],
                n_pairs=row["n_pairs"],
                full_mean=_format_float(row["full_mean"]),
                comparator_mean=_format_float(row["comparator_mean"]),
                diff=_format_float(row["mean_diff_full_minus_comparator"]),
                ci=ci,
                holm_p=_format_float(row["holm_p_value"], digits=4),
                sig="yes" if row["holm_significant_0_05"] else "no",
            )
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compute paired bootstrap CIs and paired t-tests for Chapter 4."
    )
    parser.add_argument("--baseline", type=Path, default=DEFAULT_BASELINE)
    parser.add_argument("--ablation", type=Path, default=DEFAULT_ABLATION)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--summary", type=Path, default=DEFAULT_SUMMARY)
    parser.add_argument("--bootstrap-repeats", type=int, default=BOOTSTRAP_REPEATS)
    parser.add_argument("--seed", type=int, default=BOOTSTRAP_SEED)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    results = compute_statistics(
        baseline_path=args.baseline,
        ablation_path=args.ablation,
        repeats=args.bootstrap_repeats,
        seed=args.seed,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    results.to_csv(args.output, index=False, encoding="utf-8")
    write_summary(results, args.summary, args.bootstrap_repeats, args.seed)
    print(f"Wrote {args.output}")
    print(f"Wrote {args.summary}")


if __name__ == "__main__":
    main()
