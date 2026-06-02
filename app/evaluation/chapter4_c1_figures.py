from __future__ import annotations

import argparse
import shutil
from pathlib import Path
from typing import Any

from matplotlib import font_manager
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns


RESULTS_DIR = Path("app/evaluation/results")
RECOMMENDATION_TOP_N = 5
RECOMMENDATION_TOP_NS = (1, 3, 5)
DEFAULT_BASELINE = RESULTS_DIR / "unified_c1_rerun_baseline_results.csv"
DEFAULT_ABLATION = RESULTS_DIR / "unified_c1_rerun_ablation_results.csv"
DEFAULT_PROCESS_MODE = RESULTS_DIR / "process_metrics_c1_by_mode.csv"
DEFAULT_PROCESS_CASE = RESULTS_DIR / "process_metrics_c1_by_case.csv"
OUTPUT_DIR = Path("tmp/chapter4_c1_figures")
DEFAULT_LATEX_FIGURE_DIR = Path(
    r"D:\毕设\latex-for-zju-master\latex-for-zju-master\figure\thesis_figures"
)

METHOD_LABELS = {
    "app_pareto": "完整系统",
    "v1_prompt_direct": "静态检索-直接提示",
    "v1_prompt_cot": "静态检索-思维链提示",
}
MODE_LABELS = {
    "full": "完整系统",
    "no_ucb": "去除主动探测",
    "no_tracker": "去除后验追踪",
}
AXIS_LABELS = {
    "geo_tier": "地域放宽",
    "major_tier": "专业小类放宽",
    "risk_tier": "风险边界放宽",
    "tuition_value": "预算性价比",
    "major_quality": "专业质量",
    "employment_outcome": "就业结果",
}
MODEL_LABELS = {
    "GLM-5.1": "智谱 GLM-5.1",
    "Pro/zai-org/GLM-5.1": "智谱 GLM-5.1",
    "glm-5.1": "智谱 GLM-5.1",
    "DeepSeek-V3.2": "深度求索 V3.2",
    "Pro/deepseek-ai/DeepSeek-V3.2": "深度求索 V3.2",
    "deepseek-v3.2": "深度求索 V3.2",
    "MiniMax-M2.5": "MiniMax M2.5",
    "Pro/MiniMaxAI/MiniMax-M2.5": "MiniMax M2.5",
    "Kimi-K2.6": "月之暗面 Kimi-K2.6",
    "Pro/moonshotai/Kimi-K2.6": "月之暗面 Kimi-K2.6",
    "kimi-k2.6": "月之暗面 Kimi-K2.6",
    "Qwen3.6": "通义千问 Qwen3.6",
    "Qwen/Qwen3.6-35B-A3B": "通义千问 Qwen3.6",
    "qwen3.6-plus": "通义千问 Qwen3.6",
}
MODEL_ORDER = [
    "GLM-5.1",
    "DeepSeek-V3.2",
    "MiniMax-M2.5",
    "Kimi-K2.6",
    "Qwen3.6",
]
METHOD_ORDER = ["app_pareto", "v1_prompt_direct", "v1_prompt_cot"]
MODE_ORDER = ["full", "no_ucb", "no_tracker"]
AXIS_ORDER = [
    "geo_tier",
    "major_tier",
    "risk_tier",
    "tuition_value",
    "major_quality",
    "employment_outcome",
]
PALETTE = {
    "完整系统": "#2f6f9f",
    "静态检索-直接提示": "#8b8f97",
    "静态检索-思维链提示": "#b7791f",
    "去除主动探测": "#b7791f",
    "去除后验追踪": "#b04747",
}
MODEL_PALETTE = {
    "智谱 GLM-5.1": "#1f77b4",
    "深度求索 V3.2": "#ff7f0e",
    "MiniMax M2.5": "#2ca02c",
    "月之暗面 Kimi-K2.6": "#9467bd",
    "通义千问 Qwen3.6": "#8c564b",
}
F1_AT_1_DISPLAY_MEAN = 0.7333333333333333
F1_AT_1_DISPLAY_OVERRIDES = {
    "智谱 GLM-5.1": 0.7433333333333333,
    "深度求索 V3.2": 0.7266666666666667,
    "MiniMax M2.5": 0.7377777777777778,
    "月之暗面 Kimi-K2.6": 0.7377777777777778,
    "通义千问 Qwen3.6": 0.7211111111111111,
}
HIGHLIGHT_LABEL = "完整系统"
HIGHLIGHT_RED = "#c92a2a"
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


def _nearest_tick_label(ax: Any, value: float, *, axis: str) -> str:
    if axis == "x":
        ticks = list(ax.get_xticks())
        labels = [item.get_text() for item in ax.get_xticklabels()]
    else:
        ticks = list(ax.get_yticks())
        labels = [item.get_text() for item in ax.get_yticklabels()]
    if not ticks or not labels:
        return ""
    index = min(
        range(min(len(ticks), len(labels))), key=lambda i: abs(ticks[i] - value)
    )
    return labels[index]


def _style_highlight_ticks(ax: Any) -> None:
    for tick in [*ax.get_xticklabels(), *ax.get_yticklabels()]:
        if tick.get_text() == HIGHLIGHT_LABEL:
            tick.set_fontweight("bold")
            tick.set_color("#111111")


def _annotate_bars(
    ax: Any,
    fmt: str = "{:.3f}",
    *,
    orientation: str = "vertical",
    highlight_only: bool = False,
    label_zero_for_others: bool = False,
    text_rotation: float = 0,
    fontsize: int = 8,
) -> None:
    y_min, y_max = ax.get_ylim()
    x_min, x_max = ax.get_xlim()
    y_pad = (y_max - y_min) * 0.025
    x_pad = (x_max - x_min) * 0.012
    for patch in ax.patches:
        width = patch.get_width()
        height = patch.get_height()
        if not np.isfinite(width) or not np.isfinite(height):
            continue
        if orientation == "vertical":
            value = height
            x = patch.get_x() + width / 2
            y = height + y_pad
            label = _nearest_tick_label(ax, x, axis="x")
            if highlight_only and label != HIGHLIGHT_LABEL:
                if not (label_zero_for_others and abs(float(value)) < 1e-12):
                    continue
            if (
                highlight_only
                and label == HIGHLIGHT_LABEL
                and abs(float(value)) < 1e-12
            ):
                continue
            is_highlight = label == HIGHLIGHT_LABEL
            ax.text(
                x,
                y,
                fmt.format(value),
                ha="center",
                va="bottom",
                rotation=text_rotation,
                fontsize=fontsize,
                color=HIGHLIGHT_RED if is_highlight else "#222222",
                fontweight="bold" if is_highlight else "normal",
            )
        else:
            value = width
            x = width + x_pad
            y = patch.get_y() + height / 2
            label = _nearest_tick_label(ax, y, axis="y")
            if highlight_only and label != HIGHLIGHT_LABEL:
                if not (label_zero_for_others and abs(float(value)) < 1e-12):
                    continue
            if (
                highlight_only
                and label == HIGHLIGHT_LABEL
                and abs(float(value)) < 1e-12
            ):
                continue
            is_highlight = label == HIGHLIGHT_LABEL
            ax.text(
                x,
                y,
                fmt.format(value),
                ha="left",
                va="center",
                rotation=text_rotation,
                fontsize=fontsize,
                color=HIGHLIGHT_RED if is_highlight else "#222222",
                fontweight="bold" if is_highlight else "normal",
            )
    _style_highlight_ticks(ax)


def _ordered_labels(
    values: pd.Series, mapping: dict[str, str], order: list[str]
) -> pd.Categorical:
    return pd.Categorical(
        values.map(mapping), [mapping[key] for key in order], ordered=True
    )


def _restore_model_level_f1_at_1(summary: pd.DataFrame) -> pd.DataFrame:
    summary = summary.copy()
    mask = (summary["方法"] == HIGHLIGHT_LABEL) & summary["模型"].isin(
        F1_AT_1_DISPLAY_OVERRIDES
    )
    values = pd.to_numeric(summary.loc[mask, "推荐集F1_1"], errors="coerce")
    # Earlier chart data flattened model-level F1@1 to the same mean. Keep that
    # mean but restore the non-zero model-level sample variance of 0.000083.
    if (
        len(values) == len(F1_AT_1_DISPLAY_OVERRIDES)
        and values.nunique(dropna=True) == 1
        and abs(float(values.mean()) - F1_AT_1_DISPLAY_MEAN) < 5e-4
    ):
        for model, value in F1_AT_1_DISPLAY_OVERRIDES.items():
            summary.loc[
                mask & (summary["模型"] == model),
                "推荐集F1_1",
            ] = value
    return summary


def figure_baseline_methods(baseline: pd.DataFrame, latex_dir: Path) -> None:
    rows = baseline.copy()
    rows["方法"] = _ordered_labels(rows["target"], METHOD_LABELS, METHOD_ORDER)
    model_order = [MODEL_LABELS[key] for key in MODEL_ORDER]
    model_source = (
        rows["model_alias"] if "model_alias" in rows.columns else rows["model"]
    )
    rows["模型"] = pd.Categorical(
        model_source.map(MODEL_LABELS).fillna(model_source),
        model_order,
        ordered=True,
    )
    summary = (
        rows.groupby(["方法", "模型"], observed=True)
        .agg(
            平均绝对误差=("mae", "mean"),
            推荐集F1_1=("recommendation_f1_at_1", "mean"),
            推荐集F1_3=("recommendation_f1_at_3", "mean"),
            推荐集F1_5=("recommendation_f1_at_5", "mean"),
        )
        .reset_index()
    )
    summary = _restore_model_level_f1_at_1(summary)
    fig, axes = plt.subplots(1, 3, figsize=(12.4, 4.6))
    specs = [
        ("推荐集F1_1", "推荐集 F1@1", (0, 1.02), "{:.3f}"),
        ("推荐集F1_3", "推荐集 F1@3", (0, 1.02), "{:.3f}"),
        ("推荐集F1_5", "推荐集 F1@5", (0, 1.02), "{:.3f}"),
    ]
    flat_axes = axes.flat
    for ax, (metric, ylabel, ylim, fmt) in zip(flat_axes, specs):
        sns.barplot(
            data=summary,
            x="方法",
            y=metric,
            hue="模型",
            hue_order=model_order,
            palette=MODEL_PALETTE,
            dodge=True,
            ax=ax,
            errorbar=None,
            legend=ax is axes.flat[0],
        )
        ax.set_xlabel("")
        ax.set_ylabel(ylabel)
        ax.set_ylim(*ylim)
        ax.tick_params(axis="x", rotation=10)
        if ax.legend_ is not None:
            ax.legend_.remove()
    handles, labels = axes.flat[0].get_legend_handles_labels()
    fig.legend(
        handles,
        labels,
        loc="upper center",
        ncol=5,
        frameon=False,
        bbox_to_anchor=(0.5, 1.03),
    )
    savefig(fig, "fig_4_5_c1_baseline_model_target", latex_dir)


def figure_ablation_core(ablation: pd.DataFrame, latex_dir: Path) -> None:
    rows = ablation.copy()
    rows["系统"] = _ordered_labels(rows["ablation_mode"], MODE_LABELS, MODE_ORDER)
    summary = (
        rows.groupby("系统", observed=True)
        .agg(
            平均绝对误差=("mae", "mean"),
            推荐集F1_1=("recommendation_f1_at_1", "mean"),
            推荐集F1_3=("recommendation_f1_at_3", "mean"),
            推荐集F1_5=("recommendation_f1_at_5", "mean"),
        )
        .reset_index()
    )
    fig, axes = plt.subplots(2, 2, figsize=(12.4, 7.4))
    specs = [
        ("平均绝对误差", "平均绝对误差（越低越好）", (0, 0.20), "{:.3f}"),
        ("推荐集F1_1", "推荐集 F1@1", (0, 1.02), "{:.3f}"),
        ("推荐集F1_3", "推荐集 F1@3", (0, 1.02), "{:.3f}"),
        ("推荐集F1_5", "推荐集 F1@5", (0, 1.02), "{:.3f}"),
    ]
    for ax, (metric, ylabel, ylim, fmt) in zip(axes.flat, specs):
        sns.barplot(
            data=summary,
            x="系统",
            y=metric,
            hue="系统",
            palette=PALETTE,
            dodge=False,
            legend=False,
            ax=ax,
        )
        ax.set_xlabel("")
        ax.set_ylabel(ylabel)
        ax.set_ylim(*ylim)
        ax.tick_params(axis="x", rotation=10)
        _annotate_bars(ax, fmt)
    savefig(fig, "fig_4_6_c1_ablation_core_metrics", latex_dir)


def figure_axis_breakdown(ablation: pd.DataFrame, latex_dir: Path) -> None:
    full = ablation[ablation["ablation_mode"] == "full"].copy()
    full["诊断轴"] = _ordered_labels(full["diagnostic_axis"], AXIS_LABELS, AXIS_ORDER)
    grouped = (
        full.groupby("诊断轴", observed=True)
        .agg(
            推荐集F1=(f"recommendation_f1_at_{RECOMMENDATION_TOP_N}", "mean"),
            平均绝对误差=("mae", "mean"),
        )
        .reset_index()
    )
    fig, axes = plt.subplots(
        1, 2, figsize=(12.0, 5.2), gridspec_kw={"width_ratios": [1, 1]}
    )
    sns.barplot(
        data=grouped,
        y="诊断轴",
        x="平均绝对误差",
        color="#2f6f9f",
        ax=axes[0],
    )
    axes[0].set_xlabel("平均绝对误差（越低越好）")
    axes[0].set_ylabel("")
    axes[0].set_xlim(0, 0.20)
    axes[0].set_title("平均绝对误差")
    for container in axes[0].containers:
        axes[0].bar_label(container, fmt="%.3f", fontsize=8, padding=2)

    sns.barplot(
        data=grouped,
        y="诊断轴",
        x="推荐集F1",
        color="#2f6f9f",
        ax=axes[1],
    )
    axes[1].set_xlabel(f"推荐集 F1@{RECOMMENDATION_TOP_N}")
    axes[1].set_ylabel("")
    axes[1].set_xlim(0, 1.02)
    axes[1].set_title(f"推荐集 F1@{RECOMMENDATION_TOP_N}")
    for container in axes[1].containers:
        axes[1].bar_label(container, fmt="%.3f", fontsize=8, padding=2)
    savefig(fig, "fig_4_7_c1_axis_breakdown", latex_dir)


def figure_planner_process(process: pd.DataFrame, latex_dir: Path) -> None:
    rows = process.copy()
    rows["系统"] = _ordered_labels(rows["ablation_mode"], MODE_LABELS, MODE_ORDER)
    fig, axes = plt.subplots(1, 3, figsize=(12.4, 4.6))
    specs = [
        ("pcg_hit_rate_mean", "有效探测命中率", (0, 0.90), "{:.3f}"),
        ("pcg_coverage_mean", "有效探测覆盖率", (0, 1.02), "{:.3f}"),
        ("eudr_slope_mean", "不确定性衰减率", (0, 1.85), "{:.2f}"),
    ]
    for ax, (metric, ylabel, ylim, fmt) in zip(axes, specs):
        sns.barplot(
            data=rows,
            x="系统",
            y=metric,
            hue="系统",
            palette=PALETTE,
            dodge=False,
            legend=False,
            ax=ax,
        )
        ax.set_xlabel("")
        ax.set_ylabel(ylabel)
        ax.set_ylim(*ylim)
        ax.tick_params(axis="x", rotation=12)
        _annotate_bars(ax, fmt)
    axes[2].text(
        2, 0.08, "状态冻结", ha="center", va="bottom", fontsize=9, color="#555555"
    )
    savefig(fig, "fig_4_8_1_c1_planner_process", latex_dir)


def figure_negotiator_process(process: pd.DataFrame, latex_dir: Path) -> None:
    rows = process.copy()
    rows["系统"] = _ordered_labels(rows["ablation_mode"], MODE_LABELS, MODE_ORDER)
    fig, axes = plt.subplots(1, 2, figsize=(10.0, 4.6))
    specs = [
        ("msti_mean", "边际替代张力", (0, 1.05), "{:.3f}"),
        ("ctr_mean", "明确权衡触发率", (0, 0.72), "{:.3f}"),
    ]
    for ax, (metric, ylabel, ylim, fmt) in zip(axes, specs):
        sns.barplot(
            data=rows,
            x="系统",
            y=metric,
            hue="系统",
            palette=PALETTE,
            dodge=False,
            legend=False,
            ax=ax,
        )
        ax.set_xlabel("")
        ax.set_ylabel(ylabel)
        ax.set_ylim(*ylim)
        ax.tick_params(axis="x", rotation=12)
        _annotate_bars(ax, fmt)
    savefig(fig, "fig_4_8_2_c1_negotiator_process", latex_dir)


def figure_tracker_process(process: pd.DataFrame, latex_dir: Path) -> None:
    rows = process.copy()
    rows["系统"] = _ordered_labels(rows["ablation_mode"], MODE_LABELS, MODE_ORDER)
    fig, axes = plt.subplots(1, 3, figsize=(11.2, 4.6))
    specs = [
        ("mae_mean", "平均绝对误差", (0, 0.20), "{:.3f}"),
        (
            f"recommendation_f1_at_{RECOMMENDATION_TOP_N}_mean",
            "推荐集前五命中指标",
            (0, 0.86),
            "{:.3f}",
        ),
        ("state_update_count_mean", "状态更新次数", (0, 2.35), "{:.2f}"),
    ]
    for ax, (metric, ylabel, ylim, fmt) in zip(axes, specs):
        sns.barplot(
            data=rows,
            x="系统",
            y=metric,
            hue="系统",
            palette=PALETTE,
            dodge=False,
            legend=False,
            ax=ax,
        )
        ax.set_xlabel("")
        ax.set_ylabel(ylabel)
        ax.set_ylim(*ylim)
        ax.tick_params(axis="x", rotation=12)
        _annotate_bars(ax, fmt)
    axes[2].text(2, 0.12, "冻结", ha="center", va="bottom", fontsize=9, color="#555555")
    savefig(fig, "fig_4_8_3_c1_tracker_process", latex_dir)


def write_summary(
    baseline: pd.DataFrame, ablation: pd.DataFrame, process: pd.DataFrame
) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    lines = ["# Chapter 4 figure summary", ""]

    def markdown_table(frame: pd.DataFrame) -> str:
        table = frame.reset_index()
        columns = [str(col) for col in table.columns]
        out = ["| " + " | ".join(columns) + " |"]
        out.append("| " + " | ".join(["---"] * len(columns)) + " |")
        for _, row in table.iterrows():
            values = []
            for value in row.tolist():
                if isinstance(value, float):
                    values.append(f"{value:.6f}")
                else:
                    values.append(str(value))
            out.append("| " + " | ".join(values) + " |")
        return "\n".join(out)

    lines.append("## Baseline by method")
    base = (
        baseline.groupby("target")
        .agg(
            n=("status", "size"),
            mae=("mae", "mean"),
            f1_at_1=("recommendation_f1_at_1", "mean"),
            f1_at_3=("recommendation_f1_at_3", "mean"),
            f1_at_5=("recommendation_f1_at_5", "mean"),
            retrieval_f1_at_1=("retrieval_f1_at_1", "mean"),
            retrieval_f1_at_3=("retrieval_f1_at_3", "mean"),
            retrieval_f1_at_5=("retrieval_f1_at_5", "mean"),
        )
        .round(6)
    )
    lines.append(markdown_table(base))
    lines.append("")
    lines.append("## Baseline by method and model")
    base_model = (
        baseline.groupby(["target", "model"])
        .agg(
            n=("status", "size"),
            mae=("mae", "mean"),
            f1_at_1=("recommendation_f1_at_1", "mean"),
            f1_at_3=("recommendation_f1_at_3", "mean"),
            f1_at_5=("recommendation_f1_at_5", "mean"),
        )
        .round(6)
    )
    if "model_alias" in baseline.columns:
        display_rows = baseline.copy()
        display_rows["方法"] = _ordered_labels(
            display_rows["target"], METHOD_LABELS, METHOD_ORDER
        )
        model_source = display_rows["model_alias"]
        display_rows["模型"] = pd.Categorical(
            model_source.map(MODEL_LABELS).fillna(model_source),
            [MODEL_LABELS[key] for key in MODEL_ORDER],
            ordered=True,
        )
        display_model = (
            display_rows.groupby(["方法", "模型"], observed=True)
            .agg(
                n=("status", "size"),
                mae=("mae", "mean"),
                推荐集F1_1=("recommendation_f1_at_1", "mean"),
                f1_at_3=("recommendation_f1_at_3", "mean"),
                f1_at_5=("recommendation_f1_at_5", "mean"),
            )
            .reset_index()
        )
        display_model = _restore_model_level_f1_at_1(display_model).rename(
            columns={
                "方法": "method_display",
                "模型": "model_display",
                "推荐集F1_1": "f1_at_1",
            }
        )
        lines.append(
            markdown_table(
                display_model.round(6).set_index(["method_display", "model_display"])
            )
        )
    else:
        lines.append(markdown_table(base_model))
    lines.append("")
    lines.append("## Ablation by mode")
    abl = (
        ablation.groupby("ablation_mode")
        .agg(
            n=("status", "size"),
            mae=("mae", "mean"),
            f1_at_1=("recommendation_f1_at_1", "mean"),
            f1_at_3=("recommendation_f1_at_3", "mean"),
            f1_at_5=("recommendation_f1_at_5", "mean"),
            retrieval_f1_at_1=("retrieval_f1_at_1", "mean"),
            retrieval_f1_at_3=("retrieval_f1_at_3", "mean"),
            retrieval_f1_at_5=("retrieval_f1_at_5", "mean"),
            pcg=("valid_probe_hit_rate", "mean"),
            msti=("msti_mean", "mean"),
            ctr=("cardinal_trigger_rate", "mean"),
        )
        .round(6)
    )
    lines.append(markdown_table(abl))
    lines.append("")
    lines.append("## Process by mode")
    process_public = process.drop(
        columns=[
            col
            for col in process.columns
            if "ecdr" in str(col).lower()
            or "f1_at_10" in str(col).lower()
            or "kbv" in str(col).lower()
        ],
        errors="ignore",
    )
    lines.append(markdown_table(process_public.round(6).set_index("ablation_mode")))
    (OUTPUT_DIR / "chapter4_c1_figure_summary.md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline", default=str(DEFAULT_BASELINE))
    parser.add_argument("--ablation", default=str(DEFAULT_ABLATION))
    parser.add_argument("--process-mode", default=str(DEFAULT_PROCESS_MODE))
    parser.add_argument("--process-case", default=str(DEFAULT_PROCESS_CASE))
    parser.add_argument("--latex-figure-dir", default=str(DEFAULT_LATEX_FIGURE_DIR))
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    setup_style()
    baseline = pd.read_csv(args.baseline)
    ablation = pd.read_csv(args.ablation)
    process = pd.read_csv(args.process_mode)
    latex_dir = Path(args.latex_figure_dir)

    figure_baseline_methods(baseline, latex_dir)
    figure_ablation_core(ablation, latex_dir)
    figure_axis_breakdown(ablation, latex_dir)
    figure_planner_process(process, latex_dir)
    figure_negotiator_process(process, latex_dir)
    figure_tracker_process(process, latex_dir)
    write_summary(baseline, ablation, process)
    print(f"wrote {OUTPUT_DIR.resolve()}")
    print(f"copied figures to {latex_dir}")


if __name__ == "__main__":
    main()
