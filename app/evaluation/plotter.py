from pathlib import Path
from typing import Any


MODEL_LABELS = {
    "full": "EDMIE (Ours)",
    "no_ucb": "w/o UCB Active Probing",
    "no_tracker": "w/o BT-Gradient Tracker",
}
DEPENDENCY_HINT = (
    "Please install pandas matplotlib seaborn scipy to generate academic plots: "
    "pip install pandas matplotlib seaborn scipy"
)


def _load_plotting_stack() -> tuple[Any, Any, Any, Any]:
    try:
        import pandas as pd
        import seaborn as sns
        from matplotlib import pyplot as plt
        from scipy import stats
    except ImportError as exc:
        raise RuntimeError(DEPENDENCY_HINT) from exc
    return pd, sns, plt, stats


def _barplot(sns: Any, data: Any, *, x: str, y: str, ax: Any) -> None:
    try:
        sns.barplot(data=data, x=x, y=y, errorbar=("ci", 95), ax=ax)
    except (AttributeError, TypeError):
        sns.barplot(data=data, x=x, y=y, ci=95, ax=ax)


def _save_barplot(
    sns: Any,
    plt: Any,
    data: Any,
    *,
    y: str,
    ylabel: str,
    title: str,
    output_pdf: Path,
    output_png: Path,
) -> None:
    figure, ax = plt.subplots(figsize=(8.8, 5.2))
    _barplot(sns, data, x="model_variant", y=y, ax=ax)
    ax.set_xlabel("")
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    ax.tick_params(axis="x", rotation=18)
    figure.tight_layout()
    figure.savefig(output_pdf)
    figure.savefig(output_png, dpi=300)
    plt.close(figure)


def _series_for(df: Any, mode: str, metric: str) -> Any:
    return df.loc[df["ablation_mode"] == mode, metric].dropna()


def _ttest_p_value(stats: Any, left: Any, right: Any) -> float:
    if len(left) < 2 or len(right) < 2:
        return float("nan")
    result = stats.ttest_ind(left, right, equal_var=False, nan_policy="omit")
    return float(result.pvalue)


def _summary_text(df: Any, stats: Any) -> str:
    lines = ["Ablation Statistical Summary", ""]
    for mode, label in MODEL_LABELS.items():
        group = df[df["ablation_mode"] == mode]
        lines.append(f"[{label}] n={len(group)}")
        for metric in ("negotiation_turns", "mae_error"):
            mean = float(group[metric].mean()) if len(group) else float("nan")
            std = float(group[metric].std(ddof=1)) if len(group) > 1 else float("nan")
            lines.append(f"  {metric}: mean={mean:.6f}, std={std:.6f}")
        lines.append("")

    full_turns = _series_for(df, "full", "negotiation_turns")
    no_ucb_turns = _series_for(df, "no_ucb", "negotiation_turns")
    full_mae = _series_for(df, "full", "mae_error")
    no_tracker_mae = _series_for(df, "no_tracker", "mae_error")
    turns_p = _ttest_p_value(stats, full_turns, no_ucb_turns)
    mae_p = _ttest_p_value(stats, full_mae, no_tracker_mae)
    lines.extend(
        [
            "Independent Welch T-Tests",
            f"  EDMIE (Ours) vs w/o UCB Active Probing on negotiation_turns: p-value={turns_p:.6g}",
            f"  EDMIE (Ours) vs w/o BT-Gradient Tracker on mae_error: p-value={mae_p:.6g}",
        ]
    )
    return "\n".join(lines) + "\n"


def generate_academic_report(csv_path: str, output_dir: str) -> dict[str, str]:
    pd, sns, plt, stats = _load_plotting_stack()
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(csv_path)
    required_columns = {"ablation_mode", "negotiation_turns", "mae_error"}
    missing = sorted(required_columns - set(df.columns))
    if missing:
        raise ValueError(f"ablation CSV missing required columns: {', '.join(missing)}")

    df = df.copy()
    df["model_variant"] = (
        df["ablation_mode"].map(MODEL_LABELS).fillna(df["ablation_mode"])
    )
    df["negotiation_turns"] = pd.to_numeric(df["negotiation_turns"], errors="coerce")
    df["mae_error"] = pd.to_numeric(df["mae_error"], errors="coerce")

    sns.set_theme(style="whitegrid")
    turns_pdf = output / "fig_efficiency_turns.pdf"
    turns_png = output / "fig_efficiency_turns.png"
    mae_pdf = output / "fig_alignment_mae.pdf"
    mae_png = output / "fig_alignment_mae.png"
    summary_path = output / "statistical_summary.txt"

    _save_barplot(
        sns,
        plt,
        df,
        y="negotiation_turns",
        ylabel="Negotiation Turns",
        title="Convergence Efficiency Across Ablations",
        output_pdf=turns_pdf,
        output_png=turns_png,
    )
    _save_barplot(
        sns,
        plt,
        df,
        y="mae_error",
        ylabel="Mean Absolute Error",
        title="Preference Alignment Error Across Ablations",
        output_pdf=mae_pdf,
        output_png=mae_png,
    )
    summary_path.write_text(_summary_text(df, stats), encoding="utf-8")
    plt.close("all")

    return {
        "fig_efficiency_turns_pdf": str(turns_pdf),
        "fig_efficiency_turns_png": str(turns_png),
        "fig_alignment_mae_pdf": str(mae_pdf),
        "fig_alignment_mae_png": str(mae_png),
        "statistical_summary": str(summary_path),
    }
