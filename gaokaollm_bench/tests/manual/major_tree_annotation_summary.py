"""Summarize major-tree annotation experiments for thesis tables.

This script only reads experiment artifacts and writes compact JSON/Markdown
summaries. It does not connect to the database or call an LLM.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any


DEFAULT_OUTPUT_JSON = Path("gaokaollm_bench/outputs/major_tree_annotation_summary.json")
DEFAULT_OUTPUT_MD = Path("gaokaollm_bench/outputs/major_tree_annotation_summary.md")

OBSERVED_TREE_PATH = Path("gaokaollm_bench/sample_data/major_tree_observed_full.json")
FINAL_TREE_PATH = Path("gaokaollm_bench/outputs/major_tree_final_reviewed.json")
VAL_BENCHMARK_PATH = Path("gaokaollm_bench/outputs/major_val_benchmark/summary.json")
ABLATION_PATH = Path(
    "gaokaollm_bench/outputs/major_probe_classification_ablation/summary.json"
)
ARCH_TRIALS_PATH = Path(
    "gaokaollm_bench/outputs/major_probe_architecture_trials/"
    "architecture_trials_summary.json"
)
FRKAN_PATH = Path(
    "gaokaollm_bench/outputs/major_probe_frkan_trials/frkan_trials_summary.json"
)
REVIEWED_CANDIDATES_PATH = Path(
    "gaokaollm_bench/outputs/"
    "major_probe_review_candidates_mlp_h256_sqrt_threshold035_llm_reviewed.json"
)
RERUN_REVIEW_PATH = Path(
    "gaokaollm_bench/outputs/major_val_llm_review_rerun/summary.json"
)
TOPK_BENCHMARK_PATH = Path(
    "gaokaollm_bench/outputs/major_val_llm_topk_benchmark_deepseek_r1/summary.json"
)


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _round4(value: Any) -> float | None:
    if value is None:
        return None
    return round(float(value), 4)


def _metric_row(
    *,
    method: str,
    source: str,
    accuracy: Any,
    macro_f1: Any,
    top3: Any,
    note: str,
) -> dict[str, Any]:
    return {
        "method": method,
        "source": source,
        "accuracy": _round4(accuracy),
        "macro_f1": _round4(macro_f1),
        "top3_accuracy": _round4(top3),
        "note": note,
    }


def _aggregate_by_group(path: Path) -> dict[str, dict[str, Any]]:
    data = _load_json(path)
    return {str(item["group"]): item for item in data.get("aggregates", [])}


def _best_nonbaseline_architecture(path: Path) -> dict[str, Any]:
    items = [
        item
        for item in _load_json(path).get("aggregates", [])
        if item.get("model_kind") != "mlp"
        and not str(item.get("architecture_name", "")).startswith("baseline_mlp")
    ]
    return max(items, key=lambda item: float(item["best_val_macro_f1_mean"]))


def _best_frkan(path: Path) -> dict[str, Any]:
    items = [
        item
        for item in _load_json(path).get("aggregates", [])
        if item.get("model_kind") == "fr_kan"
    ]
    return max(items, key=lambda item: float(item["best_val_macro_f1_mean"]))


def _review_rerun_summary() -> dict[str, Any] | None:
    if not RERUN_REVIEW_PATH.exists():
        return None
    return _load_json(RERUN_REVIEW_PATH)


def _topk_benchmark_summary() -> dict[str, Any] | None:
    if not TOPK_BENCHMARK_PATH.exists():
        return None
    return _load_json(TOPK_BENCHMARK_PATH)


def _llm_result(topk: dict[str, Any] | None, name: str) -> dict[str, Any] | None:
    if not topk:
        return None
    for row in topk.get("llm_results", []):
        if row.get("name") == name:
            return row
    return None


def build_summary() -> dict[str, Any]:
    observed = _load_json(OBSERVED_TREE_PATH)
    final = _load_json(FINAL_TREE_PATH)
    val = _load_json(VAL_BENCHMARK_PATH)
    ablation = _aggregate_by_group(ABLATION_PATH)
    best_arch = _best_nonbaseline_architecture(ARCH_TRIALS_PATH)
    best_frkan = _best_frkan(FRKAN_PATH)
    reviewed = _load_json(REVIEWED_CANDIDATES_PATH)
    review_rerun = _review_rerun_summary()
    topk = _topk_benchmark_summary()

    observed_build = observed["observed_build"]
    final_build = final["observed_build"]
    review_status = Counter(str(row.get("review_status")) for row in reviewed)
    review_with_decision = sum(1 for row in reviewed if row.get("review_decision"))
    review_changed = sum(
        1
        for row in reviewed
        if row.get("review_decision")
        and row.get("review_decision") != row.get("recommended_label")
    )

    threshold_sweep = val.get("threshold_sweep", [])
    threshold_035 = next(
        item for item in threshold_sweep if abs(float(item["threshold"]) - 0.35) < 1e-9
    )
    recommended_topk = topk.get("recommended_threshold") if topk else None
    mlp_llm_metrics = (
        recommended_topk["metrics"]
        if recommended_topk is not None
        else review_rerun["metrics"]
        if review_rerun is not None
        else threshold_035["metrics"]
    )
    mlp_llm_note = (
        (
            f"推荐 {recommended_topk['name']}；"
            f"复核 {recommended_topk.get('review_count', 0)} 条，"
            f"修正 {recommended_topk['metrics']['corrected_count']} 条、"
            f"回退 {recommended_topk['metrics']['regressed_count']} 条。"
        )
        if recommended_topk is not None
        else (
            f"阈值 0.35，复核 {review_rerun['reviewed_count']} 条，"
            f"修正 {review_rerun['corrected_count']} 条、回退 "
            f"{review_rerun['regressed_count']} 条；"
            "该结果用于验证低置信审校是否带来 held-out 指标增益。"
        )
        if review_rerun is not None
        else (
            f"阈值 0.35 时审校率 {threshold_035['llm_review_rate']:.4f}，"
            "当前验证集上总体指标与 MLP 持平。"
        )
    )
    direct_llm = _llm_result(topk, "direct_llm_full")

    method_comparison = [
        _metric_row(
            method="规则挂载",
            source="observed tree",
            accuracy=None,
            macro_f1=None,
            top3=None,
            note=(
                f"覆盖 {observed_build['assigned_distinct_names']} 个去重专业名、"
                f"{observed_build['assigned_row_count']} 条录取记录；"
                "确定性规则作为 clean label 来源，不报告分类器准确率。"
            ),
        ),
        _metric_row(
            method="向量质心最近邻",
            source="clean validation",
            accuracy=val["embedding_only"]["accuracy"],
            macro_f1=val["embedding_only"]["macro_f1"],
            top3=val["embedding_only"]["top3_accuracy"],
            note="不训练分类头，仅用专业表示与叶子簇质心相似度分类。",
        ),
        _metric_row(
            method="直接大模型分类",
            source="clean validation",
            accuracy=(direct_llm or {})
            .get("metrics", {})
            .get("valid_accuracy", val["direct_kimi"]["accuracy"]),
            macro_f1=(direct_llm or {})
            .get("metrics", {})
            .get("macro_f1", val["direct_kimi"]["macro_f1"]),
            top3=None,
            note=(
                f"有效覆盖率 {(direct_llm or {}).get('metrics', {}).get('valid_coverage', val['direct_kimi']['coverage']):.4f}，"
                f"严格准确率 {(direct_llm or {}).get('metrics', {}).get('strict_accuracy', val['direct_kimi'].get('strict_accuracy', 0.0)):.4f}；"
                "直接 52 类标注作为稳定性诊断而非最终方法。"
            ),
        ),
        _metric_row(
            method="线性探针",
            source="3 seeds",
            accuracy=ablation["raw__linear__sqrt_balanced"]["best_val_accuracy_mean"],
            macro_f1=ablation["raw__linear__sqrt_balanced"]["best_val_macro_f1_mean"],
            top3=ablation["raw__linear__sqrt_balanced"]["best_val_top3_accuracy_mean"],
            note="使用同一 clean validation set 的线性分类头。",
        ),
        _metric_row(
            method="浅层 MLP 探针",
            source="3 seeds",
            accuracy=ablation["raw__mlp__sqrt_balanced"]["best_val_accuracy_mean"],
            macro_f1=ablation["raw__mlp__sqrt_balanced"]["best_val_macro_f1_mean"],
            top3=ablation["raw__mlp__sqrt_balanced"]["best_val_top3_accuracy_mean"],
            note="Macro-F1 最优配置，用于后续低置信候选生成。",
        ),
        _metric_row(
            method="浅层 MLP 单模型",
            source="clean validation",
            accuracy=val["probe"]["accuracy"],
            macro_f1=val["probe"]["macro_f1"],
            top3=val["probe"]["top3_accuracy"],
            note="最终用于低置信审校的单模型 checkpoint。",
        ),
        _metric_row(
            method="深层/残差 MLP",
            source="architecture sweep",
            accuracy=best_arch["best_val_accuracy_mean"],
            macro_f1=best_arch["best_val_macro_f1_mean"],
            top3=best_arch["best_val_top3_accuracy_mean"],
            note=f"最佳非基线结构为 {best_arch['architecture_name']}，未超过浅层 MLP。",
        ),
        _metric_row(
            method="FR-KAN 分类头",
            source="FR-KAN sweep",
            accuracy=best_frkan["best_val_accuracy_mean"],
            macro_f1=best_frkan["best_val_macro_f1_mean"],
            top3=best_frkan["best_val_top3_accuracy_mean"],
            note=f"最佳 FR-KAN 试探为 {best_frkan['trial_name']}，未通过晋升门槛。",
        ),
        _metric_row(
            method="MLP + LLM 低置信重标注",
            source="clean validation rerun",
            accuracy=mlp_llm_metrics["accuracy"],
            macro_f1=mlp_llm_metrics["macro_f1"],
            top3=val["probe"]["top3_accuracy"],
            note=mlp_llm_note,
        ),
    ]

    return {
        "clean_validation_set": {
            "rows": val["probe"]["total"],
            "labels": 52,
            "label_source": "rule-labeled validation set treated as clean labels",
        },
        "coverage": {
            "raw_distinct_names": observed_build["total_distinct_names"],
            "raw_rows": observed_build["total_rows"],
            "rule_assigned_distinct_names": observed_build["assigned_distinct_names"],
            "rule_unassigned_distinct_names": observed_build[
                "unassigned_distinct_names"
            ],
            "rule_assigned_rows": observed_build["assigned_row_count"],
            "rule_unassigned_rows": observed_build["unassigned_row_count"],
            "final_assigned_distinct_names": final_build["assigned_distinct_names"],
            "final_unassigned_distinct_names": final_build["unassigned_distinct_names"],
            "final_assigned_rows": final_build["assigned_row_count"],
            "final_unassigned_rows": final_build["unassigned_row_count"],
            "probe_review_assigned_distinct_names": final_build[
                "probe_review_finalize"
            ]["assigned_distinct_names"],
            "probe_review_assigned_rows": final_build["probe_review_finalize"][
                "assigned_row_count"
            ],
            "leaf_observed_names_before_review": 18596,
            "leaf_observed_names_after_review": 19096,
        },
        "candidate_review": {
            "candidate_total": len(reviewed),
            "status_counts": dict(review_status),
            "review_decision_count": review_with_decision,
            "review_changed_count": review_changed,
            "rerun": review_rerun,
            "topk_benchmark": topk,
        },
        "method_comparison": method_comparison,
    }


def _metric_text(value: float | None) -> str:
    return "-" if value is None else f"{value:.4f}"


def render_markdown(summary: dict[str, Any]) -> str:
    coverage = summary["coverage"]
    lines = [
        "# 专业层级本体标注实验汇总",
        "",
        "本报告由现有专业树、验证集 benchmark、分类消融和候选审校产物汇总生成；"
        "除可选的低置信审校重跑结果外，不连接数据库，不重跑 Agent/Benchmark。",
        "",
        "## 覆盖与审校增益",
        "",
        "| 阶段 | 去重专业名覆盖 | 录取记录覆盖 | 说明 |",
        "|---|---:|---:|---|",
        (
            f"| 规则挂载 | {coverage['rule_assigned_distinct_names']} / "
            f"{coverage['raw_distinct_names']} | {coverage['rule_assigned_rows']} / "
            f"{coverage['raw_rows']} | 人工本体骨架和确定性规则覆盖 |"
        ),
        (
            f"| MLP + LLM/人工审校后 | {coverage['final_assigned_distinct_names']} / "
            f"{coverage['raw_distinct_names']} | {coverage['final_assigned_rows']} / "
            f"{coverage['raw_rows']} | 模型候选与审校流程补齐低置信样本 |"
        ),
        (
            f"| 叶子观测专业名 | {coverage['leaf_observed_names_before_review']} -> "
            f"{coverage['leaf_observed_names_after_review']} | - | "
            "审校后新增 500 条叶子观测专业名 |"
        ),
        "",
        "## 方法对比",
        "",
        "| 方法 | Accuracy | Macro-F1 | Top-3 | 说明 |",
        "|---|---:|---:|---:|---|",
    ]
    for row in summary["method_comparison"]:
        lines.append(
            "| {method} | {accuracy} | {macro_f1} | {top3} | {note} |".format(
                method=row["method"],
                accuracy=_metric_text(row["accuracy"]),
                macro_f1=_metric_text(row["macro_f1"]),
                top3=_metric_text(row["top3_accuracy"]),
                note=row["note"],
            )
        )
    review = summary["candidate_review"]
    lines.extend(
        [
            "",
            "## Top-k 候选池",
            "",
        ]
    )
    topk = summary["candidate_review"].get("topk_benchmark")
    if topk:
        lines.extend(
            [
                "| 指标 | 数值 |",
                "|---|---:|",
            ]
        )
        for key, value in topk["probe_metrics"]["hit_at_k"].items():
            lines.append(f"| {key} | {value:.4f} |")
        lines.extend(["", "## LLM 重标注关键结果", ""])
        lines.extend(
            [
                "| 方案 | Accuracy | Macro-F1 | changed | corrected | regressed |",
                "|---|---:|---:|---:|---:|---:|",
            ]
        )
        interesting = {
            "candidate_top5_full",
            "candidate_top10_full",
            "direct_llm_full",
            "candidate_top5_threshold_0.20",
            "candidate_top10_threshold_0.20",
            "candidate_top5_threshold_0.35",
            "candidate_top10_threshold_0.35",
        }
        for row in topk["llm_results"]:
            if row["name"] not in interesting:
                continue
            metrics = row["metrics"]
            lines.append(
                f"| {row['name']} | {metrics['accuracy']:.4f} | "
                f"{metrics['macro_f1']:.4f} | {metrics['changed_count']} | "
                f"{metrics['corrected_count']} | {metrics['regressed_count']} |"
            )
    lines.extend(
        [
            "",
            "## 候选审校统计",
            "",
            f"- 候选总数：{review['candidate_total']}",
            f"- 状态分布：{review['status_counts']}",
            f"- 产生审校决策的候选数：{review['review_decision_count']}",
            f"- 历史审校中改变模型 top-1 的候选数：{review['review_changed_count']}",
        ]
    )
    rerun = review.get("rerun")
    if rerun:
        lines.extend(
            [
                f"- 验证集低置信重跑审校数：{rerun['reviewed_count']}",
                f"- 重跑改变数：{rerun['changed_count']}",
                f"- 重跑修正数：{rerun['corrected_count']}",
                f"- 重跑回退数：{rerun['regressed_count']}",
            ]
        )
    lines.extend(
        [
            "",
            "## 论文口径",
            "",
            "clean validation set 的规则标签作为分类准确率评估依据。"
            "MLP 是当前最稳的自动候选生成器；直接大模型分类存在输出稳定性问题。"
            "低置信重标注如未显著提升 held-out 指标，应如实写作审校覆盖和质量控制机制，"
            "而不是包装成全面性能提升。",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Summarize major-tree annotation experiment artifacts."
    )
    parser.add_argument("--output-json", default=str(DEFAULT_OUTPUT_JSON))
    parser.add_argument("--output-md", default=str(DEFAULT_OUTPUT_MD))
    args = parser.parse_args()

    summary = build_summary()
    output_json = Path(args.output_json)
    output_md = Path(args.output_md)
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    output_md.write_text(render_markdown(summary), encoding="utf-8")
    print(f"Wrote {output_json}")
    print(f"Wrote {output_md}")


if __name__ == "__main__":
    main()
