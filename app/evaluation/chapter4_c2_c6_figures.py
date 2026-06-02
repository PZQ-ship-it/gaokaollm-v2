from __future__ import annotations

import argparse
import shutil
from pathlib import Path
from typing import Any

from matplotlib import font_manager
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns


RESULTS_DIR = Path("app/evaluation/results")
DEFAULT_BASELINE = RESULTS_DIR / "unified_c2_c6_baseline_results.csv"
DEFAULT_ABLATION = RESULTS_DIR / "unified_c2_c6_ablation_results.csv"
DEFAULT_PROCESS_MODE = RESULTS_DIR / "process_metrics_c2_c6_by_mode.csv"
OUTPUT_DIR = Path("tmp/chapter4_c2_c6_figures")
DEFAULT_LATEX_FIGURE_DIR = Path(
    r"D:\毕设\latex-for-zju-master\latex-for-zju-master\figure\thesis_figures"
)

TARGET_LABELS = {
    "app_pareto": "完整系统",
    "v1_prompt_direct": "静态检索-直接提示",
}
MODE_LABELS = {
    "full": "完整系统",
    "no_ucb": "去主动探测",
    "no_tracker": "去后验追踪",
}
TARGET_ORDER = ["app_pareto", "v1_prompt_direct"]
MODE_ORDER = ["full", "no_ucb", "no_tracker"]
PALETTE = {
    "完整系统": "#2f6f9f",
    "静态检索-直接提示": "#8b8f97",
    "去主动探测": "#b7791f",
    "去后验追踪": "#b04747",
}
CJK_FONT_FILES = [
    Path(r"C:\Windows\Fonts\msyh.ttc"),
    Path(r"C:\Windows\Fonts\simhei.ttf"),
    Path(r"C:\Windows\Fonts\Deng.ttf"),
    Path(r"C:\Windows\Fonts\simsun.ttc"),
]


def setup_style() -> None:
    font_names: list[str] = []
    for font_file in CJK_FONT_FILES:
        if font_file.exists():
            font_manager.fontManager.addfont(str(font_file))
            font_names.append(
                font_manager.FontProperties(fname=str(font_file)).get_name()
            )
    fonts = [*font_names, "Microsoft YaHei", "SimHei", "SimSun", "DejaVu Sans"]
    plt.rcParams["font.sans-serif"] = [*dict.fromkeys(fonts)]
    plt.rcParams["axes.unicode_minus"] = False
    plt.rcParams["figure.dpi"] = 150
    plt.rcParams.update(
        {
            "font.size": 10,
            "axes.labelsize": 10,
            "axes.titlesize": 12,
            "xtick.labelsize": 9,
            "ytick.labelsize": 9,
            "legend.fontsize": 9,
        }
    )
    sns.set_theme(style="whitegrid", font=plt.rcParams["font.sans-serif"][0])


def savefig(fig: Any, name: str, latex_dir: Path) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    latex_dir.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    png = OUTPUT_DIR / f"{name}.png"
    pdf = OUTPUT_DIR / f"{name}.pdf"
    fig.savefig(png, dpi=320, bbox_inches="tight")
    fig.savefig(pdf, bbox_inches="tight")
    shutil.copy2(png, latex_dir / png.name)
    shutil.copy2(pdf, latex_dir / pdf.name)
    plt.close(fig)


def _lineplot(
    *,
    data: pd.DataFrame,
    x: str,
    y: str,
    hue: str,
    ax: Any,
    ylabel: str,
    ylim: tuple[float, float] | None = None,
) -> None:
    sns.lineplot(
        data=data,
        x=x,
        y=y,
        hue=hue,
        style=hue,
        markers=True,
        dashes=False,
        palette=PALETTE,
        linewidth=2,
        markersize=7,
        errorbar=None,
        ax=ax,
    )
    ax.set_xlabel("显式约束数量")
    ax.set_ylabel(ylabel)
    if ylim is not None:
        ax.set_ylim(*ylim)
    ax.set_xticks([2, 3, 4, 5, 6])
    ax.legend(title="")


def figure_baseline_gradient(baseline: pd.DataFrame, latex_dir: Path) -> None:
    rows = baseline[baseline["target"].isin(TARGET_ORDER)].copy()
    rows["方法"] = pd.Categorical(
        rows["target"].map(TARGET_LABELS),
        [TARGET_LABELS[key] for key in TARGET_ORDER],
        ordered=True,
    )
    grouped = (
        rows.groupby(["constraint_count", "方法"], observed=True)
        .agg(
            mae=("mae", "mean"),
            f1_at_1=("recommendation_f1_at_1", "mean"),
            f1_at_5=("recommendation_f1_at_5", "mean"),
            success=("elicitation_success", "mean"),
            pareto_gain=("pareto_gain", "mean"),
        )
        .reset_index()
    )
    fig, axes = plt.subplots(2, 2, figsize=(12.0, 8.0))
    specs = [
        ("mae", "平均绝对误差（越低越好）", None),
        ("f1_at_1", "推荐集 F1@1", (0, 1.02)),
        ("f1_at_5", "推荐集 F1@5", (0, 1.02)),
        ("pareto_gain", "平均 Pareto gain", None),
    ]
    for ax, (metric, ylabel, ylim) in zip(axes.flat, specs):
        _lineplot(
            data=grouped,
            x="constraint_count",
            y=metric,
            hue="方法",
            ax=ax,
            ylabel=ylabel,
            ylim=ylim,
        )
    savefig(fig, "fig_4_9_c2_c6_baseline_gradient", latex_dir)


def figure_ablation_gradient(ablation: pd.DataFrame, latex_dir: Path) -> None:
    rows = ablation[ablation["ablation_mode"].isin(MODE_ORDER)].copy()
    rows["系统"] = pd.Categorical(
        rows["ablation_mode"].map(MODE_LABELS),
        [MODE_LABELS[key] for key in MODE_ORDER],
        ordered=True,
    )
    grouped = (
        rows.groupby(["constraint_count", "系统"], observed=True)
        .agg(
            mae=("mae", "mean"),
            f1_at_1=("recommendation_f1_at_1", "mean"),
            f1_at_5=("recommendation_f1_at_5", "mean"),
            pcg=("valid_probe_hit_rate", "mean"),
        )
        .reset_index()
    )
    fig, axes = plt.subplots(2, 2, figsize=(12.0, 8.0))
    specs = [
        ("mae", "平均绝对误差（越低越好）", None),
        ("f1_at_1", "推荐集 F1@1", (0, 1.02)),
        ("f1_at_5", "推荐集 F1@5", (0, 1.02)),
        ("pcg", "有效探测命中率", (0, 1.02)),
    ]
    for ax, (metric, ylabel, ylim) in zip(axes.flat, specs):
        _lineplot(
            data=grouped,
            x="constraint_count",
            y=metric,
            hue="系统",
            ax=ax,
            ylabel=ylabel,
            ylim=ylim,
        )
    savefig(fig, "fig_4_10_c2_c6_ablation_gradient", latex_dir)


def figure_process_diagnostics(process: pd.DataFrame, latex_dir: Path) -> None:
    rows = process[process["ablation_mode"].isin(MODE_ORDER)].copy()
    rows["系统"] = pd.Categorical(
        rows["ablation_mode"].map(MODE_LABELS),
        [MODE_LABELS[key] for key in MODE_ORDER],
        ordered=True,
    )
    fig, axes = plt.subplots(2, 3, figsize=(13.6, 8.0))
    specs = [
        ("pcg_hit_rate_mean", "有效探测命中率", (0, 1.02)),
        ("pcg_coverage_mean", "有效探测覆盖率", (0, 1.02)),
        ("msti_mean", "边际替代张力", None),
        ("ctr_mean", "明确权衡触发率", (0, 1.02)),
        ("mae_mean", "平均绝对误差", None),
        ("recommendation_f1_at_5_mean", "推荐集 F1@5", (0, 1.02)),
    ]
    for ax, (metric, ylabel, ylim) in zip(axes.flat, specs):
        sns.barplot(
            data=rows,
            x="系统",
            y=metric,
            hue="系统",
            palette=PALETTE,
            dodge=False,
            legend=False,
            errorbar=None,
            ax=ax,
        )
        ax.set_xlabel("")
        ax.set_ylabel(ylabel)
        ax.tick_params(axis="x", rotation=10)
        if ylim is not None:
            ax.set_ylim(*ylim)
        for container in ax.containers:
            ax.bar_label(container, fmt="%.3f", fontsize=8, padding=2)
    savefig(fig, "fig_4_11_c2_c6_process_diagnostics", latex_dir)


def markdown_table(frame: pd.DataFrame) -> str:
    table = frame.reset_index()
    lines = ["| " + " | ".join(str(col) for col in table.columns) + " |"]
    lines.append("| " + " | ".join(["---"] * len(table.columns)) + " |")
    for _, row in table.iterrows():
        values = []
        for value in row.tolist():
            if isinstance(value, float):
                values.append(f"{value:.6f}")
            else:
                values.append(str(value))
        lines.append("| " + " | ".join(values) + " |")
    return "\n".join(lines)


def write_summary(
    baseline: pd.DataFrame,
    ablation: pd.DataFrame,
    process: pd.DataFrame,
) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    lines = ["# Chapter 4 C2-C6 figure summary", ""]
    lines.append("## Baseline gradient")
    baseline_group = (
        baseline.groupby(["target", "constraint_count"])
        .agg(
            n=("status", "size"),
            completed=("status", lambda value: int((value == "ok").sum())),
            mae=("mae", "mean"),
            f1_at_1=("recommendation_f1_at_1", "mean"),
            f1_at_5=("recommendation_f1_at_5", "mean"),
            pareto_gain=("pareto_gain", "mean"),
        )
        .round(6)
    )
    lines.append(markdown_table(baseline_group))
    lines.append("")
    lines.append("## Ablation gradient")
    ablation_group = (
        ablation.groupby(["ablation_mode", "constraint_count"])
        .agg(
            n=("status", "size"),
            completed=("status", lambda value: int((value == "ok").sum())),
            mae=("mae", "mean"),
            f1_at_1=("recommendation_f1_at_1", "mean"),
            f1_at_5=("recommendation_f1_at_5", "mean"),
            pcg=("valid_probe_hit_rate", "mean"),
        )
        .round(6)
    )
    lines.append(markdown_table(ablation_group))
    lines.append("")
    lines.append("## Process by mode")
    lines.append(markdown_table(process.round(6).set_index("ablation_mode")))
    (OUTPUT_DIR / "chapter4_c2_c6_figure_summary.md").write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline", default=str(DEFAULT_BASELINE))
    parser.add_argument("--ablation", default=str(DEFAULT_ABLATION))
    parser.add_argument("--process-mode", default=str(DEFAULT_PROCESS_MODE))
    parser.add_argument("--latex-figure-dir", default=str(DEFAULT_LATEX_FIGURE_DIR))
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    setup_style()
    baseline = pd.read_csv(args.baseline)
    ablation = pd.read_csv(args.ablation)
    process = pd.read_csv(args.process_mode)
    latex_dir = Path(args.latex_figure_dir)

    figure_baseline_gradient(baseline, latex_dir)
    figure_ablation_gradient(ablation, latex_dir)
    figure_process_diagnostics(process, latex_dir)
    write_summary(baseline, ablation, process)
    print(f"wrote {OUTPUT_DIR.resolve()}")
    print(f"copied figures to {latex_dir}")


if __name__ == "__main__":
    main()
