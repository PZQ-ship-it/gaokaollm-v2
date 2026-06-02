from __future__ import annotations

import argparse
import json
import textwrap
from pathlib import Path
from typing import Any

from matplotlib import font_manager
from matplotlib.patches import FancyBboxPatch, Patch
import matplotlib.gridspec as gridspec
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns


RESULTS_DIR = Path(__file__).parent / "results"
OUTPUT_DIR = Path("tmp/chapter6_figures")
FONT_BUMP = 0.0
# 论文正式图题统一由 LaTeX caption 承担，本脚本不再写图内大标题。

MODEL_LABELS = {
    "full": "本文方法",
    "no_ucb": "去主动探测",
    "no_tracker": "去后验追踪",
}
HIGHLIGHT_MODE = "full"
HIGHLIGHT_LABEL = MODEL_LABELS[HIGHLIGHT_MODE]
HIGHLIGHT_RED = "#c92a2a"
REFERENCE_LABELS = {
    "random_dirichlet_expected": "随机方法",
    "v1_hybrid_candidate_proxy": "混合检索",
    HIGHLIGHT_MODE: HIGHLIGHT_LABEL,
}
REFERENCE_ORDER = [
    "random_dirichlet_expected",
    "v1_hybrid_candidate_proxy",
    HIGHLIGHT_MODE,
]
REFERENCE_COLORS = {
    "random_dirichlet_expected": "#7b8ea3",
    "v1_hybrid_candidate_proxy": "#4f9d75",
    HIGHLIGHT_MODE: "#2f6f9f",
}

PROFILE_TYPES = {
    "robust_major_extreme": "单维强底线",
    "robust_geo_extreme": "单维强底线",
    "robust_tuition_extreme": "单维强底线",
    "robust_school_extreme": "单维强底线",
    "robust_major_tuition_dual": "双维底线",
    "robust_school_geo_dual": "双维底线",
    "robust_quality_major_dual": "双维底线",
    "robust_geo_tuition_dual": "双维底线",
    "robust_camouflage_school_to_tuition": "伪装诱饵",
    "robust_camouflage_geo_free": "伪装诱饵",
    "robust_low_school_decoy": "伪装诱饵",
    "robust_balanced_true": "均衡画像",
}

TYPE_ORDER = ["单维强底线", "双维底线", "伪装诱饵", "均衡画像"]
MODE_ORDER = ["full", "no_ucb", "no_tracker"]
DIMENSION_LABELS = {
    "school": "学校",
    "major": "专业",
    "tuition": "学费",
    "quality": "质量",
    "geo": "地域",
    "risk": "风险",
}
DIMENSIONS = ["school", "major", "tuition", "quality", "geo", "risk"]
CJK_FONT_FILES = [
    Path(r"C:\Windows\Fonts\simhei.ttf"),
    Path(r"C:\Windows\Fonts\NotoSansSC-VF.ttf"),
    Path(r"C:\Windows\Fonts\Deng.ttf"),
]


def fs(size: float) -> float:
    return size + FONT_BUMP


def setup_style() -> None:
    font_names: list[str] = []
    for font_file in CJK_FONT_FILES:
        if font_file.exists():
            if hasattr(font_manager.fontManager, "addfont"):
                font_manager.fontManager.addfont(str(font_file))
            else:
                font_manager.fontManager.ttflist.extend(
                    font_manager.createFontList([str(font_file)])
                )
            font_names.append(
                font_manager.FontProperties(fname=str(font_file)).get_name()
            )

    preferred_fonts = [
        "Microsoft YaHei",
        *font_names,
        "SimHei",
        "SimSun",
        "Arial Unicode MS",
        "DejaVu Sans",
    ]
    plt.rcParams["font.sans-serif"] = [
        *dict.fromkeys(preferred_fonts),
    ]
    plt.rcParams["axes.unicode_minus"] = False
    plt.rcParams["figure.dpi"] = 150
    theme_font = preferred_fonts[0]
    try:
        sns.set_theme(style="whitegrid", font=theme_font)
    except AttributeError:
        sns.set(style="whitegrid", font=theme_font)
    plt.rcParams.update(
        {
            "font.size": fs(10),
            "axes.labelsize": fs(10),
            "axes.titlesize": fs(12),
            "xtick.labelsize": fs(9),
            "ytick.labelsize": fs(9),
            "legend.fontsize": fs(10),
        }
    )


def load_rows() -> tuple[
    pd.DataFrame, pd.DataFrame, pd.DataFrame, list[dict[str, Any]], dict[str, Any]
]:
    ablation = pd.read_csv(RESULTS_DIR / "ablation_results.csv")
    classification = pd.read_csv(RESULTS_DIR / "classification_metrics.csv")
    reference = pd.read_csv(RESULTS_DIR / "reference_baselines.csv")
    logs = [
        json.loads(line)
        for line in (RESULTS_DIR / "episode_logs.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
        if line.strip()
    ]
    analysis = json.loads(
        (RESULTS_DIR / "episode_log_analysis.json").read_text(encoding="utf-8")
    )
    for frame in (ablation, classification):
        frame["profile_type"] = frame["profile_id"].map(PROFILE_TYPES)
        frame["model_label"] = frame["ablation_mode"].map(MODEL_LABELS)
    return ablation, classification, reference, logs, analysis


def savefig(fig: Any, name: str) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / f"{name}.png", dpi=320, bbox_inches="tight")
    fig.savefig(OUTPUT_DIR / f"{name}.pdf", bbox_inches="tight")
    plt.close(fig)


def mean_std(frame: pd.DataFrame, metric: str) -> pd.DataFrame:
    rows = []
    for mode in MODE_ORDER:
        values = frame.loc[frame["ablation_mode"] == mode, metric].astype(float)
        rows.append(
            {
                "mode": mode,
                "label": MODEL_LABELS[mode],
                "mean": values.mean(),
                "std": values.std(ddof=1),
            }
        )
    return pd.DataFrame(rows)


def _style_highlight_ticks(ax: Any, keys: list[str]) -> None:
    for tick, key in zip(ax.get_xticklabels(), keys):
        if key == HIGHLIGHT_MODE:
            tick.set_fontweight("bold")


def _style_highlight_legend(legend: Any) -> None:
    for text in legend.get_texts():
        if text.get_text() == HIGHLIGHT_LABEL:
            text.set_fontweight("bold")


def _add_value_label(
    ax: Any,
    *,
    x: float,
    y: float,
    text: str,
    is_highlight: bool,
    ylim: tuple[float, float],
    fontsize: int = 9,
) -> None:
    ax.text(
        x,
        y + (ylim[1] - ylim[0]) * 0.035,
        text,
        ha="center",
        va="bottom",
        fontsize=fs(fontsize),
        color=HIGHLIGHT_RED if is_highlight else "#222222",
        fontweight="bold" if is_highlight else "normal",
    )


def _numeric_summary(values: Any) -> tuple[float, float]:
    series = pd.to_numeric(values, errors="coerce").dropna().astype(float)
    if len(series) == 0:
        return float("nan"), 0.0
    std = float(series.std(ddof=1)) if len(series) > 1 else 0.0
    return float(series.mean()), std


def _reference_mae_summary(
    reference: pd.DataFrame, baseline_type: str
) -> tuple[float, float]:
    rows = reference[
        (reference["baseline_type"] == baseline_type) & (reference["status"] == "ok")
    ].copy()
    dataset = rows[rows["profile_id"] == "__dataset__"]
    profile_rows = rows[rows["profile_id"] != "__dataset__"]
    if not dataset.empty:
        dataset_row = dataset.iloc[0]
        mean = float(dataset_row["mae_error"])
        std = 0.0
        try:
            std = float(
                json.loads(str(dataset_row.get("weights") or "{}")).get("std_mae", 0.0)
            )
        except (TypeError, ValueError, json.JSONDecodeError):
            _, std = _numeric_summary(profile_rows["mae_error"])
        return mean, std
    return _numeric_summary(profile_rows["mae_error"])


def _classification_f1_summary(
    classification: pd.DataFrame, *, mode: str, source: str
) -> tuple[float, float]:
    rows = classification[
        (classification["ablation_mode"] == mode)
        & (classification["source"] == source)
        & (classification["status"] == "ok")
    ]
    return _numeric_summary(rows["f1"])


def _reference_plot_summary(
    reference: pd.DataFrame,
    classification: pd.DataFrame,
    ablation: pd.DataFrame,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for mode in REFERENCE_ORDER:
        if mode == HIGHLIGHT_MODE:
            mae_mean, mae_std = _numeric_summary(
                ablation.loc[
                    (ablation["ablation_mode"] == HIGHLIGHT_MODE)
                    & (ablation["status"] == "ok"),
                    "mae_error",
                ]
            )
            f1_mean, f1_std = _classification_f1_summary(
                classification, mode=HIGHLIGHT_MODE, source="agent_ablation"
            )
        else:
            mae_mean, mae_std = _reference_mae_summary(reference, mode)
            f1_mean, f1_std = _classification_f1_summary(
                classification, mode=mode, source="reference_baseline"
            )
        rows.append(
            {
                "mode": mode,
                "label": REFERENCE_LABELS[mode],
                "mae_mean": mae_mean,
                "mae_std": mae_std,
                "f1_mean": f1_mean,
                "f1_std": f1_std,
            }
        )
    return pd.DataFrame(rows)


def figure_chinese_ablation_bars(
    ablation: pd.DataFrame, classification: pd.DataFrame
) -> None:
    """Generate the three single-metric ablation figures used in the thesis."""

    def draw_bar(
        frame: pd.DataFrame,
        metric: str,
        ylabel: str,
        name: str,
        ylim: tuple[float, float],
        color: str,
    ) -> None:
        summary = mean_std(frame, metric)
        x = np.arange(len(summary))
        fig, ax = plt.subplots(figsize=(7.4, 4.6))
        ax.bar(x, summary["mean"], color=color, alpha=0.88, width=0.56)
        ax.errorbar(
            x,
            summary["mean"],
            yerr=summary["std"].fillna(0),
            fmt="none",
            ecolor="#333333",
            capsize=4,
            lw=1.0,
        )
        ax.set_xticks(x)
        ax.set_xticklabels(summary["label"], fontsize=fs(10))
        _style_highlight_ticks(ax, list(summary["mode"]))
        ax.set_ylabel(ylabel, fontsize=fs(11))
        ax.set_ylim(*ylim)
        ax.grid(axis="y", alpha=0.25)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        for index, row in summary.iterrows():
            value = float(row["mean"])
            _add_value_label(
                ax,
                x=index,
                y=value,
                text=f"{value:.3f}",
                is_highlight=row["mode"] == HIGHLIGHT_MODE,
                ylim=ylim,
                fontsize=10,
            )
        savefig(fig, name)

    f1_rows = classification[classification["source"] == "agent_ablation"].copy()
    draw_bar(
        ablation,
        "negotiation_turns",
        "谈判轮次",
        "fig_6_1_robust_efficiency_turns",
        (0, 3.4),
        "#2f6f9f",
    )
    draw_bar(
        ablation,
        "mae_error",
        "平均绝对误差",
        "fig_6_2_robust_alignment_mae",
        (0, 0.26),
        "#d37f2a",
    )
    draw_bar(
        f1_rows,
        "f1",
        "Top-k 维度 F1",
        "fig_6_3_robust_dimension_f1",
        (0, 1.05),
        "#7a9b45",
    )


def figure_metric_dashboard(
    ablation: pd.DataFrame, classification: pd.DataFrame
) -> None:
    fig, axes = plt.subplots(1, 3, figsize=(12.6, 4.2))
    metrics = [
        ("negotiation_turns", ablation, "谈判轮次", (0, 3.4)),
        ("mae_error", ablation, "偏好对齐 MAE", (0, 0.26)),
        (
            "f1",
            classification[classification["source"] == "agent_ablation"],
            "底线维度 F1",
            (0, 1.05),
        ),
    ]
    colors = ["#2f6f9f", "#d37f2a", "#7a9b45"]
    for ax, (metric, frame, ylabel, ylim), color in zip(axes, metrics, colors):
        summary = mean_std(frame, metric)
        x = np.arange(len(summary))
        ax.bar(x, summary["mean"], color=color, alpha=0.86, width=0.58)
        ax.errorbar(
            x,
            summary["mean"],
            yerr=summary["std"],
            fmt="none",
            ecolor="#222222",
            capsize=4,
            lw=1.1,
        )
        ax.set_xticks(x)
        ax.set_xticklabels(summary["label"], rotation=12)
        _style_highlight_ticks(ax, list(summary["mode"]))
        ax.set_ylabel(ylabel)
        ax.set_ylim(*ylim)
        for i, row in summary.iterrows():
            value = float(row["mean"])
            _add_value_label(
                ax,
                x=i,
                y=value,
                text=f"{value:.3f}",
                is_highlight=row["mode"] == HIGHLIGHT_MODE,
                ylim=ylim,
                fontsize=9,
            )
        ax.grid(axis="y", alpha=0.28)
    axes[0].annotate("p=1.815e-20", xy=(0.5, 3.05), ha="center", fontsize=fs(9))
    axes[1].annotate("p=3.492e-07", xy=(1.0, 0.235), ha="center", fontsize=fs(9))
    axes[2].annotate(
        "参考基线 F1≈0.333",
        xy=(1.2, 0.36),
        ha="center",
        fontsize=fs(9),
        color="#555555",
    )
    savefig(fig, "fig_6_1_robust_metric_dashboard")


def figure_main_metrics_grouped(
    ablation: pd.DataFrame, classification: pd.DataFrame
) -> None:
    """Generate one thesis figure that combines the three main ablation metrics."""

    f1_rows = classification[classification["source"] == "agent_ablation"].copy()
    metric_specs = [
        ("negotiation_turns", ablation, "交互轮次", "交互轮次", (0, 3.4)),
        ("mae_error", ablation, "偏好对齐 MAE", "MAE", (0, 0.26)),
        ("f1", f1_rows, "底线维度 F1", "F1", (0, 1.05)),
    ]
    method_colors = {
        "full": "#2f6f9f",
        "no_ucb": "#d37f2a",
        "no_tracker": "#7a9b45",
    }
    method_labels = {
        "full": HIGHLIGHT_LABEL,
        "no_ucb": "去主动探测",
        "no_tracker": "去后验追踪",
    }
    short_labels = {
        "full": HIGHLIGHT_LABEL,
        "no_ucb": "去主动\n探测",
        "no_tracker": "去后验\n追踪",
    }

    fig = plt.figure(figsize=(12.8, 4.8))
    grid = gridspec.GridSpec(2, 3, height_ratios=[0.14, 0.86], hspace=0.06, wspace=0.32)
    legend_ax = fig.add_subplot(grid[0, :])
    legend_ax.axis("off")
    legend_handles = [
        Patch(
            facecolor=method_colors[mode],
            edgecolor="#333333",
            label=method_labels[mode],
        )
        for mode in MODE_ORDER
    ]
    legend = legend_ax.legend(
        handles=legend_handles,
        ncol=3,
        loc="center",
        frameon=False,
        fontsize=fs(10),
        handlelength=2.6,
        columnspacing=2.2,
    )
    _style_highlight_legend(legend)

    axes = [fig.add_subplot(grid[1, index]) for index in range(3)]
    for ax, (metric, frame, title, ylabel, ylim) in zip(axes, metric_specs):
        summary = (
            mean_std(frame, metric).set_index("mode").loc[MODE_ORDER].reset_index()
        )
        x = np.arange(len(summary))
        yerr = summary["std"].fillna(0).values
        ax.bar(
            x,
            summary["mean"],
            color=[method_colors[mode] for mode in summary["mode"]],
            alpha=0.88,
            width=0.58,
            edgecolor="#333333",
            linewidth=0.55,
        )
        ax.errorbar(
            x,
            summary["mean"],
            yerr=yerr,
            fmt="none",
            ecolor="#222222",
            capsize=4,
            lw=1.0,
        )
        ax.set_title(title, fontsize=fs(12), fontweight="bold", pad=9)
        ax.set_ylabel(ylabel, fontsize=fs(10))
        ax.set_ylim(*ylim)
        ax.set_xticks(x)
        ax.set_xticklabels(
            [short_labels[mode] for mode in summary["mode"]],
            fontsize=fs(9),
            linespacing=1.15,
        )
        _style_highlight_ticks(ax, list(summary["mode"]))
        ax.grid(axis="y", alpha=0.25)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        for index, row in summary.iterrows():
            value = float(row["mean"])
            _add_value_label(
                ax,
                x=index,
                y=value,
                text=f"{value:.3f}",
                is_highlight=row["mode"] == HIGHLIGHT_MODE,
                ylim=ylim,
                fontsize=9,
            )

    savefig(fig, "fig_6_1_robust_main_metrics_grouped")


def figure_reference_baseline_metrics(
    reference: pd.DataFrame,
    classification: pd.DataFrame,
    ablation: pd.DataFrame,
) -> None:
    """Generate the baseline-vs-ours figure for thesis figure 4.3."""

    summary = _reference_plot_summary(reference, classification, ablation)
    metrics = [
        (
            "MAE",
            "MAE",
            summary["mae_mean"].astype(float),
            summary["mae_std"].fillna(0).astype(float),
            (0, 0.25),
        ),
        (
            "底线维度 F1",
            "F1",
            summary["f1_mean"].astype(float),
            summary["f1_std"].fillna(0).astype(float),
            (0, 1.05),
        ),
    ]
    short_labels = {
        "random_dirichlet_expected": "随机\n方法",
        "v1_hybrid_candidate_proxy": "混合\n检索",
        HIGHLIGHT_MODE: HIGHLIGHT_LABEL,
    }

    fig = plt.figure(figsize=(10.6, 4.6))
    grid = gridspec.GridSpec(2, 2, height_ratios=[0.16, 0.84], hspace=0.06, wspace=0.30)
    legend_ax = fig.add_subplot(grid[0, :])
    legend_ax.axis("off")
    legend_handles = [
        Patch(
            facecolor=REFERENCE_COLORS[mode],
            edgecolor="#333333",
            label=REFERENCE_LABELS[mode],
        )
        for mode in REFERENCE_ORDER
    ]
    legend = legend_ax.legend(
        handles=legend_handles,
        ncol=3,
        loc="center",
        frameon=False,
        fontsize=fs(10),
        handlelength=2.6,
        columnspacing=2.0,
    )
    _style_highlight_legend(legend)

    axes = [fig.add_subplot(grid[1, index]) for index in range(2)]
    for ax, (title, ylabel, values, errors, ylim) in zip(axes, metrics):
        x = np.arange(len(REFERENCE_ORDER))
        ax.bar(
            x,
            values.values,
            color=[REFERENCE_COLORS[mode] for mode in REFERENCE_ORDER],
            alpha=0.88,
            width=0.58,
            edgecolor="#333333",
            linewidth=0.55,
        )
        if errors is not None:
            ax.errorbar(
                x,
                values.values,
                yerr=errors.values,
                fmt="none",
                ecolor="#222222",
                capsize=4,
                lw=1.0,
            )
        ax.set_title(title, fontsize=fs(12), fontweight="bold", pad=9)
        ax.set_ylabel(ylabel, fontsize=fs(10))
        ax.set_ylim(*ylim)
        ax.set_xticks(x)
        ax.set_xticklabels(
            [short_labels[mode] for mode in REFERENCE_ORDER],
            fontsize=fs(9),
            linespacing=1.15,
        )
        _style_highlight_ticks(ax, REFERENCE_ORDER)
        ax.grid(axis="y", alpha=0.25)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        for index, (mode, value) in enumerate(zip(REFERENCE_ORDER, values.values)):
            value = float(value)
            _add_value_label(
                ax,
                x=index,
                y=value,
                text=f"{value:.3f}",
                is_highlight=mode == HIGHLIGHT_MODE,
                ylim=ylim,
                fontsize=9,
            )

    savefig(fig, "fig_6_1_reference_baseline_metrics")


def figure_profile_breakdown(
    ablation: pd.DataFrame, classification: pd.DataFrame
) -> None:
    f1 = classification[classification["source"] == "agent_ablation"].copy()
    mae_pivot = (
        ablation.groupby(["profile_type", "ablation_mode"])["mae_error"]
        .mean()
        .unstack()
        .loc[TYPE_ORDER, MODE_ORDER]
    )
    f1_pivot = (
        f1.groupby(["profile_type", "ablation_mode"])["f1"]
        .mean()
        .unstack()
        .loc[TYPE_ORDER, MODE_ORDER]
    )
    mae_pivot.columns = [MODEL_LABELS[col] for col in mae_pivot.columns]
    f1_pivot.columns = [MODEL_LABELS[col] for col in f1_pivot.columns]

    fig, axes = plt.subplots(1, 2, figsize=(11.8, 4.6))
    sns.heatmap(
        mae_pivot,
        annot=True,
        fmt=".3f",
        cmap="YlOrRd",
        cbar_kws={"label": "MAE"},
        ax=axes[0],
        linewidths=0.8,
        linecolor="white",
    )
    axes[0].set_xlabel("")
    axes[0].set_ylabel("")
    sns.heatmap(
        f1_pivot,
        annot=True,
        fmt=".3f",
        cmap="YlGnBu",
        vmin=0,
        vmax=1,
        cbar_kws={"label": "F1"},
        ax=axes[1],
        linewidths=0.8,
        linecolor="white",
    )
    axes[1].set_xlabel("")
    axes[1].set_ylabel("")
    savefig(fig, "fig_6_2_profile_type_breakdown")


def figure_log_quality(analysis: dict[str, Any]) -> None:
    rows = []
    metric_labels = [
        ("target_dimension_hit_rate", "目标维度命中率"),
        ("cost_equals_benefit_rate", "无效取舍率"),
        ("same_candidate_pair_rate", "同候选对率"),
        ("repeated_question_rate", "重复提问率"),
        ("simulator_ambiguous_reply_rate", "模糊回复率"),
    ]
    for mode in MODE_ORDER:
        metrics = analysis["modes"][mode]
        for key, label in metric_labels:
            rows.append(
                {
                    "系统": MODEL_LABELS[mode],
                    "指标": label,
                    "value": float(metrics[key]),
                }
            )
    frame = pd.DataFrame(rows)
    pivot = frame.pivot(index="指标", columns="系统", values="value")
    pivot = pivot.loc[[label for _, label in metric_labels]]
    pivot = pivot[[MODEL_LABELS[mode] for mode in MODE_ORDER]]

    fig, ax = plt.subplots(figsize=(8.8, 4.8))
    sns.heatmap(
        pivot,
        annot=True,
        fmt=".3f",
        cmap="Blues",
        vmin=0,
        vmax=1,
        cbar_kws={"label": "比率"},
        linewidths=0.8,
        linecolor="white",
        ax=ax,
    )
    ax.set_xlabel("")
    ax.set_ylabel("")
    savefig(fig, "fig_6_3_log_quality_diagnostics")


def final_weight_for(logs: list[dict[str, Any]], thread_id: str) -> dict[str, float]:
    rows = [row for row in logs if row.get("thread_id") == thread_id]
    finals = [row for row in rows if row.get("status") == "final"]
    if finals:
        return finals[-1].get("inferred_weights") or {}
    return rows[-1].get("inferred_weights") if rows else {}


def short(text: str, max_len: int = 44) -> str:
    text = str(text or "").replace("\n", " ")
    return text if len(text) <= max_len else text[: max_len - 1] + "…"


def wrap_for_figure(text: str, width: int = 32) -> str:
    return textwrap.fill(str(text or "").replace("\n", " "), width=width)


def _representative_interrupt(
    logs: list[dict[str, Any]],
    thread_id: str,
    *,
    turn: int | None = 1,
) -> dict[str, Any]:
    rows = [
        row
        for row in logs
        if row.get("thread_id") == thread_id and row.get("status") == "interrupt"
    ]
    if turn is not None:
        for row in rows:
            if int(row.get("turn") or 0) == turn:
                return row
    return rows[0] if rows else {}


def _question_excerpt(row: dict[str, Any], max_len: int = 60) -> str:
    question = str(row.get("question") or "")
    if not question:
        return "未记录有效提问"
    if "本轮候选不足以形成取舍" in question:
        return "候选不足以形成取舍；不建议牺牲/放宽目标维度换取不存在收益。"
    if "你刚才拒绝了" in question:
        return short(question, max_len)
    return short(question, max_len)


def figure_dialogue_flow(logs: list[dict[str, Any]]) -> None:
    profile = "robust_major_extreme"
    fig, ax = plt.subplots(figsize=(8.4, 9.2))
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis("off")

    panel_specs = [
        {
            "mode": "full",
            "y": 64.5,
            "color": "#d8eef8",
            "edge": "#4b8aa5",
            "title": "完整系统：问到底线并更新后验",
            "target": "专业",
            "turn": 1,
        },
        {
            "mode": "no_ucb",
            "y": 36.0,
            "color": "#fff0cf",
            "edge": "#c59a35",
            "title": "no-UCB：泛化澄清，未命中专业底线",
            "target": "随机方向：证据丰富度 / 风险 / 相邻范围",
            "turn": 1,
        },
        {
            "mode": "no_tracker",
            "y": 7.5,
            "color": "#f1dcda",
            "edge": "#b97070",
            "title": "no-tracker：问到底线但不能记住",
            "target": "专业",
            "turn": 2,
        },
    ]

    for spec in panel_specs:
        y = spec["y"]
        panel = FancyBboxPatch(
            (3.5, y),
            93,
            23.5,
            boxstyle="round,pad=0.7,rounding_size=1.8",
            facecolor=spec["color"],
            edgecolor=spec["edge"],
            linewidth=1.2,
        )
        ax.add_patch(panel)
        ax.text(6, y + 20.1, spec["title"], fontsize=fs(13), weight="bold", va="center")

        thread = f"{profile}_{spec['mode']}_r1"
        representative = _representative_interrupt(
            logs,
            thread,
            turn=int(spec.get("turn") or 1),
        )
        question = _question_excerpt(representative)
        reply = short(str(representative.get("simulator_reply") or ""), 46)
        weights = final_weight_for(logs, thread)
        major = weights.get("major", 0.0)
        school = weights.get("school", 0.0)

        ax.text(
            7,
            y + 15.8,
            "探测目标",
            fontsize=fs(10.5),
            weight="bold",
            color="#333333",
            va="top",
        )
        ax.text(
            20,
            y + 15.8,
            wrap_for_figure(spec["target"], 24),
            fontsize=fs(10.5),
            va="top",
        )
        ax.text(
            7,
            y + 10.8,
            "代表性提问",
            fontsize=fs(10.5),
            weight="bold",
            color="#333333",
            va="top",
        )
        ax.text(
            20, y + 10.8, wrap_for_figure(question, 29), fontsize=fs(10.5), va="top"
        )
        ax.text(
            7,
            y + 4.4,
            "用户反馈",
            fontsize=fs(10.5),
            weight="bold",
            color="#333333",
            va="top",
        )
        ax.text(20, y + 4.4, wrap_for_figure(reply, 34), fontsize=fs(10.5), va="top")

        weights = final_weight_for(logs, thread)
        ax.text(
            82,
            y + 13.2,
            f"最终权重\n专业={major:.3f}\n学校={school:.3f}",
            fontsize=fs(10.5),
            ha="center",
            va="center",
            bbox=dict(
                boxstyle="round,pad=0.45",
                facecolor="#ffffff",
                edgecolor=spec["edge"],
                linewidth=1.0,
            ),
        )

    savefig(fig, "fig_6_4_major_extreme_dialogue_flow")


def figure_posterior_trajectory(logs: list[dict[str, Any]]) -> None:
    thread = "robust_major_extreme_full_r1"
    rows = [row for row in logs if row.get("thread_id") == thread]
    points = []
    initial = {dim: 1.0 / len(DIMENSIONS) for dim in DIMENSIONS}
    points.append({"step": "先验", **initial})
    for row in rows:
        if row.get("status") in {"interrupt", "final"}:
            weights = row.get("inferred_weights") or {}
            label = (
                f"R{row.get('turn')}后" if row.get("status") == "interrupt" else "终局"
            )
            points.append(
                {
                    "step": label,
                    **{dim: float(weights.get(dim, np.nan)) for dim in DIMENSIONS},
                }
            )
    frame = pd.DataFrame(points).drop_duplicates(subset=["step"], keep="last")
    fig, ax = plt.subplots(figsize=(9.4, 4.8))
    for dim in DIMENSIONS:
        ax.plot(
            frame["step"],
            frame[dim],
            marker="o",
            linewidth=2,
            label=DIMENSION_LABELS[dim],
        )
    ax.set_ylim(0.08, 0.52)
    ax.set_ylabel("后验权重")
    ax.legend(ncol=6, frameon=False, loc="upper center", bbox_to_anchor=(0.5, -0.12))
    ax.grid(axis="y", alpha=0.28)
    savefig(fig, "fig_6_6_posterior_trajectory")


def write_summary_tables(
    ablation: pd.DataFrame, classification: pd.DataFrame, analysis: dict[str, Any]
) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    lines = []
    lines.append("# Chapter 6 derived statistics")
    lines.append("")
    lines.append("## Profile type summary")
    f1 = classification[classification["source"] == "agent_ablation"].copy()
    for mode in MODE_ORDER:
        lines.append(f"### {MODEL_LABELS[mode]}")
        for profile_type in TYPE_ORDER:
            mae_values = ablation.loc[
                (ablation["ablation_mode"] == mode)
                & (ablation["profile_type"] == profile_type),
                "mae_error",
            ].astype(float)
            f1_values = f1.loc[
                (f1["ablation_mode"] == mode) & (f1["profile_type"] == profile_type),
                "f1",
            ].astype(float)
            lines.append(
                f"- {profile_type}: n={len(mae_values)}, MAE={mae_values.mean():.6f}, F1={f1_values.mean():.6f}"
            )
    lines.append("")
    lines.append("## Log quality")
    for mode in MODE_ORDER:
        metrics = analysis["modes"][mode]
        lines.append(
            f"- {MODEL_LABELS[mode]}: n={metrics['n']}, target_hit={metrics['target_dimension_hit_rate']:.6f}, "
            f"ambiguous={metrics['simulator_ambiguous_reply_rate']:.6f}, repeated={metrics['repeated_question_rate']:.6f}"
        )
    (OUTPUT_DIR / "chapter6_derived_statistics.md").write_text(
        "\n".join(lines), encoding="utf-8"
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--font-bump",
        type=float,
        default=0.0,
        help="Numeric font-size increase to apply to all matplotlib text.",
    )
    return parser.parse_args()


def main(font_bump: float = 0.0) -> None:
    global FONT_BUMP
    FONT_BUMP = font_bump
    setup_style()
    ablation, classification, reference, logs, analysis = load_rows()
    figure_chinese_ablation_bars(ablation, classification)
    figure_metric_dashboard(ablation, classification)
    figure_main_metrics_grouped(ablation, classification)
    figure_reference_baseline_metrics(reference, classification, ablation)
    figure_profile_breakdown(ablation, classification)
    figure_log_quality(analysis)
    figure_dialogue_flow(logs)
    figure_posterior_trajectory(logs)
    write_summary_tables(ablation, classification, analysis)
    print(f"wrote {OUTPUT_DIR.resolve()}")


if __name__ == "__main__":
    args = parse_args()
    main(font_bump=args.font_bump)
