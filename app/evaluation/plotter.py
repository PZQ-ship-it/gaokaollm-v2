from pathlib import Path
import csv
import math
import struct
import zlib
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
RESULTS_DIR = Path(__file__).parent / "results"
REFERENCE_LABELS = {
    "random_dirichlet_expected": "Random Dirichlet Baseline",
    "initial_query_llm": "Initial-query LLM Baseline",
}


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
    try:
        left_values = [float(value) for value in left]
        right_values = [float(value) for value in right]
    except (TypeError, ValueError):
        left_values = []
        right_values = []
    if left_values and right_values:
        left_std = _std(left_values)
        right_std = _std(right_values)
        if (
            math.isfinite(left_std)
            and math.isfinite(right_std)
            and left_std == 0.0
            and right_std == 0.0
        ):
            return 0.0 if _mean(left_values) != _mean(right_values) else 1.0
    result = stats.ttest_ind(left, right, equal_var=False, nan_policy="omit")
    pvalue = float(result.pvalue)
    if math.isnan(pvalue) and left_values and right_values:
        return 0.0 if _mean(left_values) != _mean(right_values) else 1.0
    return pvalue


def _reference_summary_lines(output_dir: Path) -> list[str]:
    path = output_dir / "reference_baselines.csv"
    if not path.exists():
        return []
    rows = _read_csv_rows(str(path))
    lines = ["", "Reference Baselines"]
    for baseline_type, label in REFERENCE_LABELS.items():
        dataset_rows = [
            row
            for row in rows
            if row.get("baseline_type") == baseline_type
            and row.get("profile_id") == "__dataset__"
            and row.get("status") == "ok"
        ]
        value_rows = dataset_rows or [
            row
            for row in rows
            if row.get("baseline_type") == baseline_type
            and row.get("profile_id") != "__dataset__"
            and row.get("status") == "ok"
        ]
        values: list[float] = []
        for row in value_rows:
            try:
                values.append(float(row.get("mae_error", "")))
            except (TypeError, ValueError):
                continue
        if values:
            lines.append(f"  {label}: MAE={_mean(values):.6f}, n={len(values)}")
    return lines if len(lines) > 2 else []


def _reference_mae_rows(output_dir: Path) -> list[dict[str, Any]]:
    path = output_dir / "reference_baselines.csv"
    if not path.exists():
        return []
    rows = _read_csv_rows(str(path))
    plot_rows: list[dict[str, Any]] = []
    for baseline_type, label in REFERENCE_LABELS.items():
        dataset_rows = [
            row
            for row in rows
            if row.get("baseline_type") == baseline_type
            and row.get("profile_id") == "__dataset__"
            and row.get("status") == "ok"
        ]
        value_rows = dataset_rows or [
            row
            for row in rows
            if row.get("baseline_type") == baseline_type
            and row.get("profile_id") != "__dataset__"
            and row.get("status") == "ok"
        ]
        for row in value_rows:
            try:
                mae = float(row.get("mae_error", ""))
            except (TypeError, ValueError):
                continue
            plot_rows.append(
                {
                    "ablation_mode": baseline_type,
                    "model_variant": label,
                    "mae_error": mae,
                    "negotiation_turns": float("nan"),
                    "status": row.get("status", "ok"),
                    "error_message": row.get("error_message", ""),
                }
            )
    return plot_rows


def _summary_text(df: Any, stats: Any, output_dir: Path | None = None) -> str:
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
    if output_dir is not None:
        lines.extend(_reference_summary_lines(output_dir))
    return "\n".join(lines) + "\n"


def _read_csv_rows(csv_path: str) -> list[dict[str, Any]]:
    with open(csv_path, "r", encoding="utf-8", newline="") as file:
        return list(csv.DictReader(file))


def _mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else float("nan")


def _std(values: list[float]) -> float:
    if len(values) < 2:
        return float("nan")
    mean = _mean(values)
    return math.sqrt(sum((value - mean) ** 2 for value in values) / (len(values) - 1))


def _fallback_series(rows: list[dict[str, Any]], mode: str, metric: str) -> list[float]:
    values: list[float] = []
    for row in rows:
        if row.get("ablation_mode") != mode:
            continue
        try:
            values.append(float(row.get(metric, "")))
        except (TypeError, ValueError):
            continue
    return values


def _normal_cdf(value: float) -> float:
    return 0.5 * (1.0 + math.erf(value / math.sqrt(2.0)))


def _fallback_p_value(left: list[float], right: list[float]) -> float:
    if len(left) < 2 or len(right) < 2:
        return float("nan")
    left_var = _std(left) ** 2
    right_var = _std(right) ** 2
    denom = math.sqrt(left_var / len(left) + right_var / len(right))
    if denom <= 0:
        return 0.0 if _mean(left) != _mean(right) else 1.0
    t_value = abs((_mean(left) - _mean(right)) / denom)
    return max(0.0, min(1.0, 2.0 * (1.0 - _normal_cdf(t_value))))


def _fallback_summary_text(
    rows: list[dict[str, Any]],
    output_dir: Path | None = None,
) -> str:
    lines = [
        "Ablation Statistical Summary",
        "Generated by standard-library fallback.",
        "",
    ]
    for mode, label in MODEL_LABELS.items():
        lines.append(f"[{label}] n={len(_fallback_series(rows, mode, 'mae_error'))}")
        for metric in ("negotiation_turns", "mae_error"):
            values = _fallback_series(rows, mode, metric)
            lines.append(
                f"  {metric}: mean={_mean(values):.6f}, std={_std(values):.6f}"
            )
        lines.append("")
    turns_p = _fallback_p_value(
        _fallback_series(rows, "full", "negotiation_turns"),
        _fallback_series(rows, "no_ucb", "negotiation_turns"),
    )
    mae_p = _fallback_p_value(
        _fallback_series(rows, "full", "mae_error"),
        _fallback_series(rows, "no_tracker", "mae_error"),
    )
    lines.extend(
        [
            "Independent Welch T-Tests",
            f"  EDMIE (Ours) vs w/o UCB Active Probing on negotiation_turns: p-value={turns_p:.6g}",
            f"  EDMIE (Ours) vs w/o BT-Gradient Tracker on mae_error: p-value={mae_p:.6g}",
        ]
    )
    if output_dir is not None:
        lines.extend(_reference_summary_lines(output_dir))
    return "\n".join(lines) + "\n"


def _png_chunk(tag: bytes, data: bytes) -> bytes:
    return (
        struct.pack(">I", len(data))
        + tag
        + data
        + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
    )


def _write_minimal_png(path: Path, *, color: tuple[int, int, int]) -> None:
    width, height = 320, 180
    raw = b"".join(b"\x00" + bytes(color) * width for _ in range(height))
    data = (
        b"\x89PNG\r\n\x1a\n"
        + _png_chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
        + _png_chunk(b"IDAT", zlib.compress(raw))
        + _png_chunk(b"IEND", b"")
    )
    path.write_bytes(data)


def _write_minimal_pdf(path: Path, title: str, body: str) -> None:
    escaped = (
        (title + " - " + body)
        .replace("\\", "\\\\")
        .replace("(", "\\(")
        .replace(")", "\\)")
    )
    stream = f"BT /F1 14 Tf 50 750 Td ({escaped[:180]}) Tj ET"
    pdf = (
        "%PDF-1.4\n"
        "1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n"
        "2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj\n"
        "3 0 obj << /Type /Page /Parent 2 0 R /Resources << /Font << /F1 4 0 R >> >> "
        "/MediaBox [0 0 612 792] /Contents 5 0 R >> endobj\n"
        "4 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj\n"
        f"5 0 obj << /Length {len(stream)} >> stream\n{stream}\nendstream endobj\n"
        "xref\n0 6\n0000000000 65535 f \n"
        "trailer << /Root 1 0 R /Size 6 >>\nstartxref\n0\n%%EOF\n"
    )
    path.write_text(pdf, encoding="latin-1")


def generate_academic_report_fallback(csv_path: str, output_dir: str) -> dict[str, str]:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    rows = _read_csv_rows(csv_path)
    turns_pdf = output / "fig_efficiency_turns.pdf"
    turns_png = output / "fig_efficiency_turns.png"
    mae_pdf = output / "fig_alignment_mae.pdf"
    mae_png = output / "fig_alignment_mae.png"
    summary_path = output / "statistical_summary.txt"
    summary = _fallback_summary_text(rows, output)
    _write_minimal_png(turns_png, color=(63, 127, 191))
    _write_minimal_png(mae_png, color=(191, 94, 74))
    _write_minimal_pdf(
        turns_pdf,
        "Convergence Efficiency",
        "Fallback chart; see statistical_summary.txt",
    )
    _write_minimal_pdf(
        mae_pdf, "Alignment MAE", "Fallback chart; see statistical_summary.txt"
    )
    summary_path.write_text(summary, encoding="utf-8")
    return {
        "fig_efficiency_turns_pdf": str(turns_pdf),
        "fig_efficiency_turns_png": str(turns_png),
        "fig_alignment_mae_pdf": str(mae_pdf),
        "fig_alignment_mae_png": str(mae_png),
        "statistical_summary": str(summary_path),
    }


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
    reference_mae_rows = _reference_mae_rows(output)
    mae_df = (
        pd.concat([df, pd.DataFrame(reference_mae_rows)], ignore_index=True)
        if reference_mae_rows
        else df
    )
    _save_barplot(
        sns,
        plt,
        mae_df,
        y="mae_error",
        ylabel="Mean Absolute Error",
        title="Preference Alignment Error Across Baselines",
        output_pdf=mae_pdf,
        output_png=mae_png,
    )
    summary_path.write_text(_summary_text(df, stats, output), encoding="utf-8")
    plt.close("all")

    return {
        "fig_efficiency_turns_pdf": str(turns_pdf),
        "fig_efficiency_turns_png": str(turns_png),
        "fig_alignment_mae_pdf": str(mae_pdf),
        "fig_alignment_mae_png": str(mae_png),
        "statistical_summary": str(summary_path),
    }


def run_cli() -> dict[str, str]:
    csv_path = RESULTS_DIR / "ablation_results.csv"
    try:
        result = generate_academic_report(str(csv_path), str(RESULTS_DIR))
    except RuntimeError as exc:
        print(f"[plotter] {exc}; using standard-library fallback figures")
        result = generate_academic_report_fallback(str(csv_path), str(RESULTS_DIR))
    print(f"[plotter] wrote {RESULTS_DIR}")
    return result


if __name__ == "__main__":
    run_cli()
