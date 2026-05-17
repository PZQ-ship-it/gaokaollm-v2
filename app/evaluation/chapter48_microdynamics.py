from __future__ import annotations

import argparse
import json
import math
import re
import shutil
from pathlib import Path
from typing import Any

from matplotlib import font_manager
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

from app.evaluation.benchmark import get_robust_evaluation_dataset
from app.evaluation.classification_metrics import PREFERENCE_KEYS, gold_dimensions


RESULTS_DIR = Path(__file__).parent / "results"
LOG_PATH = RESULTS_DIR / "episode_logs.jsonl"
OUTPUT_DIR = Path("tmp/chapter48_microdynamics")
FONT_BUMP = 0.0
LATEX_FIGURE_DIR = Path(
    r"D:\毕设\latex-for-zju-master\latex-for-zju-master\figure\thesis_figures"
)

DIMENSIONS = list(PREFERENCE_KEYS)
MODE_ORDER = ["full", "no_ucb", "no_tracker"]
MODE_LABELS = {
    "full": "完整系统",
    "no_ucb": "去主动探测",
    "no_tracker": "去后验追踪",
}
MODE_COLORS = {
    "full": "#2f6f9f",
    "no_ucb": "#b7791f",
    "no_tracker": "#b04747",
}
DIMENSION_LABELS = {
    "school": "学校",
    "major": "专业",
    "tuition": "学费",
    "quality": "质量",
    "geo": "地域",
}
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
            font_manager.fontManager.addfont(str(font_file))
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
    plt.rcParams["font.sans-serif"] = [*dict.fromkeys(preferred_fonts)]
    plt.rcParams["axes.unicode_minus"] = False
    plt.rcParams["figure.dpi"] = 150
    sns.set_theme(style="whitegrid", font=plt.rcParams["font.sans-serif"][0])
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


def load_logs() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line_no, line in enumerate(LOG_PATH.read_text(encoding="utf-8").splitlines()):
        if not line.strip():
            continue
        row = json.loads(line)
        row["_line_no"] = line_no
        rows.append(row)
    return rows


def robust_profiles_by_id() -> dict[str, Any]:
    return {profile.profile_id: profile for profile in get_robust_evaluation_dataset()}


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return default
    return numeric if math.isfinite(numeric) else default


def _normalized_weights(weights: dict[str, Any] | None) -> dict[str, float]:
    values = {
        key: max(0.0, _safe_float((weights or {}).get(key), 0.0)) for key in DIMENSIONS
    }
    total = sum(values.values())
    if total <= 0:
        return {key: 1.0 / len(DIMENSIONS) for key in DIMENSIONS}
    return {key: values[key] / total for key in DIMENSIONS}


def posterior_uncertainty(weights: dict[str, Any] | None) -> float:
    """Normalized entropy of the exported posterior weights."""
    normalized = _normalized_weights(weights)
    entropy = 0.0
    for value in normalized.values():
        if value > 0:
            entropy -= value * math.log(value)
    return float(entropy / math.log(len(DIMENSIONS)))


def _dimension_mentions(text: str) -> set[str]:
    lowered = str(text or "").lower()
    mentions: set[str] = set()
    patterns = {
        "school": ("school", "学校", "名校", "985", "211", "层次", "声誉"),
        "major": ("major", "专业", "计算机", "偏离", "调剂"),
        "tuition": ("tuition", "学费", "预算", "费用", "超预算"),
        "quality": ("quality", "质量", "培养", "实力", "就业", "结果"),
        "geo": ("geo", "地域", "城市", "出省", "省内", "距离", "江浙沪"),
    }
    for dim, tokens in patterns.items():
        if any(token in lowered for token in tokens):
            mentions.add(dim)
    return mentions


def feedback_label(row: dict[str, Any]) -> str:
    reply = str(row.get("simulator_reply") or "")
    explicit_reject_words = (
        "不行",
        "拒绝",
        "绝不",
        "不能接受",
        "不接受",
        "不换",
        "不调剂",
        "不能偏",
        "太远",
        "太贵",
        "不能超",
        "必须压住",
    )
    hesitant_words = ("保留", "犹豫", "不确定", "再看看", "没问到", "不想单独牺牲")
    accept_words = ("接受", "可以", "能接受", "愿意")
    if any(word in reply for word in explicit_reject_words):
        return "explicit"
    if any(word in reply for word in hesitant_words):
        return "hesitate"
    if any(word in reply for word in accept_words):
        return "explicit"
    return "hesitate"


def tension_proxy(row: dict[str, Any]) -> float:
    """Text-reproducible proxy for MSTI when Delta Phi is absent from logs."""
    question = str(row.get("question") or "")
    explicit_tradeoff = (
        1.0
        if re.search(r"牺牲|放宽|取舍|换取|sacrifice|relax", question, re.I)
        else 0.0
    )
    factual_boundary = (
        1.0 if re.search(r"边界在|为参照|学费=|层级=|候选|事实", question) else 0.0
    )
    dimension_count = len(_dimension_mentions(question))
    dimension_span = min(1.0, dimension_count / 3.0)
    target_bonus = 0.1 if row.get("ucb_target_dimension") in DIMENSIONS else 0.0
    value = (
        0.42 * explicit_tradeoff
        + 0.34 * factual_boundary
        + 0.24 * dimension_span
        + target_bonus
    )
    return float(max(0.0, min(1.0, value)))


def _rows_by_thread(logs: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    by_thread: dict[str, list[dict[str, Any]]] = {}
    for row in logs:
        by_thread.setdefault(str(row.get("thread_id") or ""), []).append(row)
    for rows in by_thread.values():
        rows.sort(key=lambda item: int(item.get("_line_no") or 0))
    return by_thread


def _initial_record(thread_id: str, mode: str, profile_id: str) -> dict[str, Any]:
    return {
        "thread_id": thread_id,
        "profile_id": profile_id,
        "ablation_mode": mode,
        "turn": 0,
        "event_index": 0,
        "status": "initial",
        "inferred_weights": {key: 1.0 / len(DIMENSIONS) for key in DIMENSIONS},
    }


def trajectory_rows(logs: list[dict[str, Any]]) -> pd.DataFrame:
    records: list[dict[str, Any]] = []
    for thread_id, rows in _rows_by_thread(logs).items():
        if not rows:
            continue
        mode = str(rows[0].get("ablation_mode") or "")
        profile_id = str(rows[0].get("profile_id") or "")
        records.append(_initial_record(thread_id, mode, profile_id))
        for index, row in enumerate(rows, start=1):
            weights = row.get("inferred_weights") or {}
            records.append(
                {
                    "thread_id": thread_id,
                    "profile_id": profile_id,
                    "ablation_mode": mode,
                    "turn": int(row.get("turn") or 0),
                    "event_index": index,
                    "status": row.get("status"),
                    "inferred_weights": weights,
                    "uncertainty": posterior_uncertainty(weights),
                    **{
                        f"w_{dim}": _normalized_weights(weights)[dim]
                        for dim in DIMENSIONS
                    },
                }
            )
        records[-len(rows) - 1]["uncertainty"] = 1.0
        for dim in DIMENSIONS:
            records[-len(rows) - 1][f"w_{dim}"] = 1.0 / len(DIMENSIONS)
    return pd.DataFrame(records)


def coverage_gradient(
    rows: list[dict[str, Any]], gold_dims: tuple[str, ...]
) -> list[dict[str, Any]]:
    seen: set[str] = set()
    records = [{"turn": 0, "coverage": 0.0}]
    denominator = max(1, len(gold_dims))
    for row in rows:
        if row.get("status") != "interrupt":
            continue
        target = str(row.get("ucb_target_dimension") or "")
        if target in gold_dims:
            seen.add(target)
        records.append(
            {
                "turn": int(row.get("turn") or 0),
                "coverage": len(seen) / denominator,
            }
        )
    return records


def build_coverage_frame(
    logs: list[dict[str, Any]], profiles: dict[str, Any]
) -> pd.DataFrame:
    records: list[dict[str, Any]] = []
    for thread_id, rows in _rows_by_thread(logs).items():
        profile_id = str(rows[0].get("profile_id") or "")
        profile = profiles.get(profile_id)
        if profile is None:
            continue
        mode = str(rows[0].get("ablation_mode") or "")
        gold = gold_dimensions(profile)
        for record in coverage_gradient(rows, gold):
            records.append(
                {
                    "thread_id": thread_id,
                    "profile_id": profile_id,
                    "ablation_mode": mode,
                    **record,
                }
            )
    return pd.DataFrame(records)


def build_tension_frame(logs: list[dict[str, Any]]) -> pd.DataFrame:
    records: list[dict[str, Any]] = []
    for thread_id, rows in _rows_by_thread(logs).items():
        for index, row in enumerate(rows):
            if row.get("status") != "interrupt":
                continue
            next_row = rows[index + 1] if index + 1 < len(rows) else None
            current_u = posterior_uncertainty(row.get("inferred_weights") or {})
            next_u = (
                posterior_uncertainty(next_row.get("inferred_weights") or {})
                if next_row is not None
                else current_u
            )
            records.append(
                {
                    "thread_id": thread_id,
                    "profile_id": row.get("profile_id"),
                    "ablation_mode": row.get("ablation_mode"),
                    "系统": MODE_LABELS.get(str(row.get("ablation_mode")), ""),
                    "turn": int(row.get("turn") or 0),
                    "msti_proxy": tension_proxy(row),
                    "information_gain": max(0.0, current_u - next_u),
                    "feedback": feedback_label(row),
                    "反馈类型": "明确表态"
                    if feedback_label(row) == "explicit"
                    else "犹豫保留",
                }
            )
    return pd.DataFrame(records)


def belief_oscillation(rows: list[dict[str, Any]], dim: str | None = None) -> float:
    vectors: list[np.ndarray] = []
    vectors.append(np.array([1.0 / len(DIMENSIONS) for _ in DIMENSIONS], dtype=float))
    for row in rows:
        weights = _normalized_weights(row.get("inferred_weights") or {})
        vectors.append(np.array([weights[key] for key in DIMENSIONS], dtype=float))
    if len(vectors) < 2:
        return 0.0
    path = sum(
        float(np.linalg.norm(vectors[i] - vectors[i - 1]))
        for i in range(1, len(vectors))
    )
    displacement = float(np.linalg.norm(vectors[-1] - vectors[0]))
    if displacement < 1e-9:
        return 0.0 if path < 1e-9 else float("inf")
    return path / displacement


def kbv_proxy(
    rows: list[dict[str, Any]], gold_dims: tuple[str, ...]
) -> tuple[int, int, float]:
    rejected: set[str] = set()
    violations = 0
    opportunities = 0
    for row in rows:
        if not rejected:
            pass
        else:
            weights = _normalized_weights(row.get("inferred_weights") or {})
            for dim in rejected:
                opportunities += 1
                if weights.get(dim, 0.0) <= 0.25:
                    violations += 1
        if row.get("status") != "interrupt":
            continue
        reply_dims = _dimension_mentions(str(row.get("simulator_reply") or ""))
        target = str(row.get("ucb_target_dimension") or "")
        if feedback_label(row) == "explicit":
            for dim in (
                set(gold_dims)
                | reply_dims
                | ({target} if target in DIMENSIONS else set())
            ):
                if dim in gold_dims:
                    rejected.add(dim)
    rate = violations / opportunities if opportunities else float("nan")
    return violations, opportunities, rate


def savefig(fig: Any, name: str) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    LATEX_FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    png_path = OUTPUT_DIR / f"{name}.png"
    pdf_path = OUTPUT_DIR / f"{name}.pdf"
    fig.savefig(png_path, dpi=320, bbox_inches="tight")
    fig.savefig(pdf_path, bbox_inches="tight")
    shutil.copy2(png_path, LATEX_FIGURE_DIR / png_path.name)
    shutil.copy2(pdf_path, LATEX_FIGURE_DIR / pdf_path.name)
    plt.close(fig)


def figure_uncertainty_and_coverage(
    logs: list[dict[str, Any]], profiles: dict[str, Any]
) -> None:
    trajectories = trajectory_rows(logs)
    coverage = build_coverage_frame(logs, profiles)
    modes = ["full", "no_ucb"]
    fig, axes = plt.subplots(1, 2, figsize=(12.2, 4.6))

    uncertainty = trajectories[
        (trajectories["ablation_mode"].isin(modes))
        & (trajectories["status"].isin(["initial", "interrupt"]))
        & (trajectories["event_index"] <= 3)
    ].copy()
    uncertainty["系统"] = uncertainty["ablation_mode"].map(MODE_LABELS)
    sns.lineplot(
        data=uncertainty,
        x="event_index",
        y="uncertainty",
        hue="系统",
        marker="o",
        errorbar=("ci", 95),
        palette={MODE_LABELS[mode]: MODE_COLORS[mode] for mode in modes},
        ax=axes[0],
    )
    axes[0].set_xlabel("交互阶段")
    axes[0].set_ylabel("后验熵代理量 $U_t$")
    axes[0].set_ylim(0.82, 1.01)
    axes[0].set_xticks([0, 1, 2, 3])
    axes[0].set_xticklabels(["先验", "R1", "R2", "R3"])
    axes[0].legend(frameon=False, loc="lower left")

    coverage_plot = coverage[
        (coverage["ablation_mode"].isin(modes)) & (coverage["turn"] <= 3)
    ].copy()
    coverage_plot["系统"] = coverage_plot["ablation_mode"].map(MODE_LABELS)
    sns.lineplot(
        data=coverage_plot,
        x="turn",
        y="coverage",
        hue="系统",
        marker="o",
        errorbar=("ci", 95),
        palette={MODE_LABELS[mode]: MODE_COLORS[mode] for mode in modes},
        ax=axes[1],
    )
    axes[1].set_xlabel("交互轮次")
    axes[1].set_ylabel("偏好覆盖梯度 $C_t$")
    axes[1].set_ylim(-0.03, 1.03)
    axes[1].set_xticks([0, 1, 2, 3])
    axes[1].legend(frameon=False, loc="lower right")
    savefig(fig, "fig_4_8_1_uncertainty_collapse")


def figure_tension_information_gain(logs: list[dict[str, Any]]) -> pd.DataFrame:
    frame = build_tension_frame(logs)
    fig, ax = plt.subplots(figsize=(8.8, 5.2))
    sns.scatterplot(
        data=frame,
        x="msti_proxy",
        y="information_gain",
        hue="反馈类型",
        style="系统",
        palette={"明确表态": "#c92a2a", "犹豫保留": "#8b8f97"},
        alpha=0.82,
        s=58,
        ax=ax,
    )
    sns.regplot(
        data=frame,
        x="msti_proxy",
        y="information_gain",
        scatter=False,
        color="#222222",
        line_kws={"linewidth": 1.8, "alpha": 0.7},
        ax=ax,
    )
    ax.set_xlabel(r"边际替代张力代理量 $MSTI^\dagger$")
    ax.set_ylabel(r"本轮信息增益 $IG_t$")
    ax.set_xlim(-0.03, 1.03)
    ax.set_ylim(-0.005, max(0.03, float(frame["information_gain"].max()) * 1.15))
    ax.legend(frameon=False, loc="upper left", bbox_to_anchor=(1.02, 1.0))
    savefig(fig, "fig_4_8_2_tension_information_gain")
    return frame


def _decoy_profile(profiles: dict[str, Any]) -> tuple[str, str, float]:
    profile_id = "robust_camouflage_school_to_tuition"
    profile = profiles[profile_id]
    gold = gold_dimensions(profile)
    dim = gold[0] if gold else "tuition"
    truth = _safe_float(profile.ground_truth_weights.get(dim), 0.0)
    return profile_id, dim, truth


def figure_belief_anchoring(
    logs: list[dict[str, Any]], profiles: dict[str, Any]
) -> tuple[str, str, float]:
    profile_id, dim, truth = _decoy_profile(profiles)
    trajectories = trajectory_rows(
        [row for row in logs if row.get("profile_id") == profile_id]
    )
    value_col = f"w_{dim}"
    plot = trajectories[trajectories["event_index"] <= 4].copy()
    plot["系统"] = plot["ablation_mode"].map(MODE_LABELS)

    fig, ax = plt.subplots(figsize=(9.2, 5.0))
    for mode in MODE_ORDER:
        mode_rows = plot[plot["ablation_mode"] == mode]
        if mode_rows.empty:
            continue
        summary = (
            mode_rows.groupby("event_index", as_index=False)[value_col]
            .mean()
            .sort_values("event_index")
        )
        ax.plot(
            summary["event_index"],
            summary[value_col],
            marker="o",
            linewidth=2.2,
            color=MODE_COLORS[mode],
            label=MODE_LABELS[mode],
        )
    ax.axhline(
        truth, linestyle="--", color="#111111", linewidth=1.6, label="隐藏真实权重"
    )
    ax.set_xlabel("对话状态")
    ax.set_ylabel(f"{DIMENSION_LABELS[dim]}维度后验权重")
    ax.set_ylim(0.05, max(0.9, truth + 0.05))
    ax.set_xticks([0, 1, 2, 3, 4])
    ax.set_xticklabels(["先验", "R1", "R2", "R3", "终局"])
    ax.legend(frameon=False, loc="upper center", bbox_to_anchor=(0.5, -0.12), ncol=4)
    savefig(fig, "fig_4_8_3_belief_anchoring_decoy")
    return profile_id, dim, truth


def write_summary(
    logs: list[dict[str, Any]],
    profiles: dict[str, Any],
    tension_frame: pd.DataFrame,
    decoy_profile_id: str,
    decoy_dim: str,
    decoy_truth: float,
) -> None:
    trajectories = trajectory_rows(logs)
    lines = ["# Chapter 4.8 microdynamics summary", ""]

    lines.append("## Uncertainty proxy")
    for mode in MODE_ORDER:
        mode_rows = trajectories[trajectories["ablation_mode"] == mode]
        initial = mode_rows[mode_rows["event_index"] == 0]["uncertainty"].mean()
        final_rows = mode_rows.sort_values("event_index").groupby("thread_id").tail(1)
        final = final_rows["uncertainty"].mean()
        lines.append(
            f"- {mode}: initial_U={initial:.6f}, final_U={final:.6f}, decay={initial - final:.6f}"
        )

    lines.append("")
    lines.append("## Tension and trigger summary")
    if len(tension_frame) > 1:
        corr = float(
            tension_frame[["msti_proxy", "information_gain"]].corr().iloc[0, 1]
        )
    else:
        corr = float("nan")
    lines.append(f"- pearson_msti_proxy_information_gain={corr:.6f}")
    for mode in MODE_ORDER:
        mode_rows = tension_frame[tension_frame["ablation_mode"] == mode]
        trigger_rate = (
            float((mode_rows["feedback"] == "explicit").mean())
            if not mode_rows.empty
            else float("nan")
        )
        lines.append(
            f"- {mode}: n={len(mode_rows)}, mean_msti_proxy={mode_rows['msti_proxy'].mean():.6f}, "
            f"mean_ig={mode_rows['information_gain'].mean():.6f}, cardinal_trigger_rate={trigger_rate:.6f}"
        )

    lines.append("")
    lines.append("## BOI and KBV proxy")
    by_thread = _rows_by_thread(logs)
    for mode in MODE_ORDER:
        boi_values: list[float] = []
        kbv_violations = 0
        kbv_opportunities = 0
        for rows in by_thread.values():
            if not rows or rows[0].get("ablation_mode") != mode:
                continue
            profile = profiles.get(str(rows[0].get("profile_id") or ""))
            if profile is None:
                continue
            boi = belief_oscillation(rows)
            if math.isfinite(boi):
                boi_values.append(boi)
            violations, opportunities, _ = kbv_proxy(rows, gold_dimensions(profile))
            kbv_violations += violations
            kbv_opportunities += opportunities
        mean_boi = sum(boi_values) / len(boi_values) if boi_values else float("nan")
        kbv_rate = (
            kbv_violations / kbv_opportunities if kbv_opportunities else float("nan")
        )
        lines.append(
            f"- {mode}: mean_boi={mean_boi:.6f}, kbv_violations={kbv_violations}, "
            f"kbv_opportunities={kbv_opportunities}, kbv_proxy_rate={kbv_rate:.6f}"
        )

    lines.append("")
    lines.append("## Decoy trajectory")
    lines.append(
        f"- profile={decoy_profile_id}, dimension={decoy_dim}, ground_truth={decoy_truth:.6f}"
    )
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUTPUT_DIR / "chapter48_microdynamics_summary.md").write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
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
    logs = load_logs()
    profiles = robust_profiles_by_id()
    figure_uncertainty_and_coverage(logs, profiles)
    tension_frame = figure_tension_information_gain(logs)
    decoy_profile_id, decoy_dim, decoy_truth = figure_belief_anchoring(logs, profiles)
    write_summary(
        logs, profiles, tension_frame, decoy_profile_id, decoy_dim, decoy_truth
    )
    print(f"wrote {OUTPUT_DIR.resolve()}")
    print(f"copied figures to {LATEX_FIGURE_DIR}")


if __name__ == "__main__":
    args = parse_args()
    main(font_bump=args.font_bump)
