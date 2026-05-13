from __future__ import annotations

import ast
import json
import textwrap
from collections import Counter
from pathlib import Path
from typing import Any

from matplotlib.patches import FancyBboxPatch
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns


RESULTS_DIR = Path(__file__).parent / "results"
OUTPUT_DIR = Path("tmp/chapter6_figures")
# 论文正式图题统一由 LaTeX caption 承担，本脚本不再写图内大标题。

MODEL_LABELS = {
    "full": "EDMIE 完整模式",
    "no_ucb": "去主动探测",
    "no_tracker": "去后验追踪",
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
}
DIMENSIONS = ["school", "major", "tuition", "quality", "geo"]


def setup_style() -> None:
    plt.rcParams["font.sans-serif"] = [
        "Microsoft YaHei",
        "SimHei",
        "SimSun",
        "Arial Unicode MS",
        "DejaVu Sans",
    ]
    plt.rcParams["axes.unicode_minus"] = False
    plt.rcParams["figure.dpi"] = 150
    try:
        sns.set_theme(style="whitegrid", font="Microsoft YaHei")
    except AttributeError:
        sns.set(style="whitegrid", font="Microsoft YaHei")


def load_rows() -> tuple[
    pd.DataFrame, pd.DataFrame, list[dict[str, Any]], dict[str, Any]
]:
    ablation = pd.read_csv(RESULTS_DIR / "ablation_results.csv")
    classification = pd.read_csv(RESULTS_DIR / "classification_metrics.csv")
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
    return ablation, classification, logs, analysis


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
        ax.set_xticklabels(summary["label"], fontsize=10)
        ax.set_ylabel(ylabel, fontsize=11)
        ax.set_ylim(*ylim)
        ax.grid(axis="y", alpha=0.25)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        for index, value in enumerate(summary["mean"]):
            ax.text(
                index,
                value + (ylim[1] - ylim[0]) * 0.035,
                f"{value:.3f}",
                ha="center",
                va="bottom",
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
        ax.set_ylabel(ylabel)
        ax.set_ylim(*ylim)
        for i, value in enumerate(summary["mean"]):
            ax.text(
                i,
                value + (ylim[1] - ylim[0]) * 0.035,
                f"{value:.3f}",
                ha="center",
                fontsize=9,
            )
        ax.grid(axis="y", alpha=0.28)
    axes[0].annotate("p=1.815e-20", xy=(0.5, 3.05), ha="center", fontsize=9)
    axes[1].annotate("p=3.492e-07", xy=(1.0, 0.235), ha="center", fontsize=9)
    axes[2].annotate(
        "参考基线 F1≈0.333", xy=(1.2, 0.36), ha="center", fontsize=9, color="#555555"
    )
    savefig(fig, "fig_6_1_robust_metric_dashboard")


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
    metric_labels = {
        "repeated_question_rate": "重复提问率",
        "cost_equals_benefit_rate": "无效代价=收益率",
        "same_candidate_pair_rate": "同候选对率",
        "target_dimension_hit_rate": "目标维度命中率",
        "simulator_ambiguous_reply_rate": "模糊回复率",
    }
    for mode in MODE_ORDER:
        metrics = analysis["modes"][mode]
        for key, label in metric_labels.items():
            rows.append(
                {
                    "系统": MODEL_LABELS[mode],
                    "指标": label,
                    "value": float(metrics[key]),
                }
            )
    frame = pd.DataFrame(rows)
    pivot = frame.pivot(index="指标", columns="系统", values="value")
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
            "title": "EDMIE full：问到底线并更新后验",
            "target": "专业",
            "question": "用真实候选对追问：是否愿意放宽专业匹配。",
            "reply": "专业不能偏太远，这个我不接受。",
        },
        {
            "mode": "no_ucb",
            "y": 36.0,
            "color": "#fff0cf",
            "edge": "#c59a35",
            "title": "no-UCB：泛化澄清，未命中专业底线",
            "target": "随机方向：证据丰富度 / 风险 / 相邻范围",
            "question": "询问不确定性、风险等泛化方向，没有明确候选取舍。",
            "reply": "这个问题没问到我的真正底线，我先保留。",
        },
        {
            "mode": "no_tracker",
            "y": 7.5,
            "color": "#f1dcda",
            "edge": "#b97070",
            "title": "no-tracker：问到底线但不能记住",
            "target": "专业",
            "question": "第一轮命中专业底线，后续仍重复确认同一问题。",
            "reply": "专业不能偏太远，这个我不接受。",
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
        ax.text(6, y + 20.1, spec["title"], fontsize=13, weight="bold", va="center")

        thread = f"{profile}_{spec['mode']}_r1"
        weights = final_weight_for(logs, thread)
        major = weights.get("major", 0.0)
        school = weights.get("school", 0.0)

        ax.text(
            7,
            y + 15.8,
            "探测目标",
            fontsize=10.5,
            weight="bold",
            color="#333333",
            va="top",
        )
        ax.text(
            20, y + 15.8, wrap_for_figure(spec["target"], 24), fontsize=10.5, va="top"
        )
        ax.text(
            7,
            y + 10.8,
            "代表性提问",
            fontsize=10.5,
            weight="bold",
            color="#333333",
            va="top",
        )
        ax.text(
            20, y + 10.8, wrap_for_figure(spec["question"], 29), fontsize=10.5, va="top"
        )
        ax.text(
            7,
            y + 4.4,
            "用户反馈",
            fontsize=10.5,
            weight="bold",
            color="#333333",
            va="top",
        )
        ax.text(
            20, y + 4.4, wrap_for_figure(spec["reply"], 34), fontsize=10.5, va="top"
        )

        weights = final_weight_for(logs, thread)
        ax.text(
            82,
            y + 13.2,
            f"最终权重\n专业={major:.3f}\n学校={school:.3f}",
            fontsize=10.5,
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


def parse_list(value: str) -> list[str]:
    try:
        parsed = ast.literal_eval(value)
    except (ValueError, SyntaxError):
        return []
    return [str(item) for item in parsed] if isinstance(parsed, list) else []


def figure_bad_case(classification: pd.DataFrame) -> None:
    full = classification[
        (classification["source"] == "agent_ablation")
        & (classification["ablation_mode"] == "full")
    ].copy()
    full["gold_list"] = full["gold_dims"].apply(parse_list)
    full["pred_list"] = full["pred_dims"].apply(parse_list)
    miss_counter: Counter[str] = Counter()
    false_counter: Counter[str] = Counter()
    profile_failures = []
    for _, row in full.iterrows():
        gold = set(row["gold_list"])
        pred = set(row["pred_list"])
        if float(row["f1"]) < 1.0:
            profile_failures.append(row["profile_id"])
        for dim in sorted(gold - pred):
            miss_counter[dim] += 1
        for dim in sorted(pred - gold):
            false_counter[dim] += 1

    x = np.arange(len(DIMENSIONS))
    miss = [miss_counter[dim] for dim in DIMENSIONS]
    false = [false_counter[dim] for dim in DIMENSIONS]
    fig, axes = plt.subplots(1, 2, figsize=(11.2, 4.6))
    width = 0.38
    axes[0].bar(x - width / 2, miss, width, label="漏识别", color="#b45b5b")
    axes[0].bar(x + width / 2, false, width, label="误加入", color="#6d85b8")
    axes[0].set_xticks(x)
    axes[0].set_xticklabels([DIMENSION_LABELS[d] for d in DIMENSIONS])
    axes[0].set_ylabel("次数（36 次 full 运行）")
    axes[0].legend(frameon=False)
    axes[0].grid(axis="y", alpha=0.25)

    profile_counts = Counter(profile_failures)
    labels = [
        "专业+学费",
        "质量+专业",
        "地域+学费",
        "专业+质量诱饵",
    ]
    keys = [
        "robust_major_tuition_dual",
        "robust_quality_major_dual",
        "robust_geo_tuition_dual",
        "robust_low_school_decoy",
    ]
    axes[1].barh(labels, [profile_counts[key] for key in keys], color="#c4874a")
    axes[1].set_xlim(0, 3.4)
    axes[1].set_xlabel("失败重复数 / 3")
    axes[1].grid(axis="x", alpha=0.25)
    savefig(fig, "fig_6_5_bad_case_dimension_errors")


def figure_posterior_trajectory(logs: list[dict[str, Any]]) -> None:
    thread = "robust_major_extreme_full_r1"
    rows = [row for row in logs if row.get("thread_id") == thread]
    points = []
    initial = {dim: 0.2 for dim in DIMENSIONS}
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
    ax.legend(ncol=5, frameon=False, loc="upper center", bbox_to_anchor=(0.5, -0.12))
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


def main() -> None:
    setup_style()
    ablation, classification, logs, analysis = load_rows()
    figure_chinese_ablation_bars(ablation, classification)
    figure_metric_dashboard(ablation, classification)
    figure_profile_breakdown(ablation, classification)
    figure_log_quality(analysis)
    figure_dialogue_flow(logs)
    figure_bad_case(classification)
    figure_posterior_trajectory(logs)
    write_summary_tables(ablation, classification, analysis)
    print(f"wrote {OUTPUT_DIR.resolve()}")


if __name__ == "__main__":
    main()
