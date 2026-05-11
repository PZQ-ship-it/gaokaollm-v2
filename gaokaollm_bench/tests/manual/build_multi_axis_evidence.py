"""Build a compact evidence appendix for multi-axis benchmark runs."""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any


PROFILE_LABELS = {
    "major_geo_risk": "专业-地域放宽 + 风险组合",
    "quality_tuition": "专业质量 + 学费预算",
    "employment_region": "就业结果 + 地域层级证据",
}


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _profile(case_id: str) -> str:
    for value in PROFILE_LABELS:
        if value in case_id:
            return value
    return "unknown"


def _fmt_metric(value: float) -> str:
    return f"{value:.3f}"


def _profile_rows(rows: list[dict[str, Any]]) -> list[str]:
    lines = [
        "| Profile | Cases | Success | Mean gain | Axis success summary |",
        "|---|---:|---:|---:|---|",
    ]
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[_profile(str(row.get("case_id") or ""))].append(row)
    for profile, profile_rows in grouped.items():
        success = sum(bool(row.get("elicitation_success")) for row in profile_rows)
        gain = sum(float(row.get("pareto_gain") or 0) for row in profile_rows) / max(
            1, len(profile_rows)
        )
        axis_counts: dict[str, int] = defaultdict(int)
        for row in profile_rows:
            for axis, ok in (row.get("axis_successes") or {}).items():
                if ok:
                    axis_counts[str(axis)] += 1
        axis_summary = ", ".join(
            f"{axis} {count}/{len(profile_rows)}"
            for axis, count in sorted(axis_counts.items())
        )
        lines.append(
            f"| `{profile}` {PROFILE_LABELS.get(profile, '')} | {len(profile_rows)} | "
            f"{success} | {gain:.3f} | {axis_summary} |"
        )
    return lines


def _case_rows(
    app_rows: list[dict[str, Any]], hard_rows: list[dict[str, Any]]
) -> list[str]:
    hard_by_case = {row["case_id"]: row for row in hard_rows}
    lines = [
        "| Case | Profile | App success | Baseline success | Turns | Hallucination | Gain | Axis successes |",
        "|---|---|---:|---:|---:|---:|---:|---|",
    ]
    for row in app_rows:
        case_id = str(row["case_id"])
        hard = hard_by_case.get(case_id, {})
        axes = ", ".join(
            f"{axis}={str(ok).lower()}"
            for axis, ok in (row.get("axis_successes") or {}).items()
        )
        lines.append(
            f"| `{case_id}` | `{_profile(case_id)}` | {bool(row.get('elicitation_success'))} | "
            f"{bool(hard.get('elicitation_success'))} | {row.get('turns')} | "
            f"{float(row.get('hallucination_rate') or 0):.3f} | {row.get('pareto_gain')} | {axes} |"
        )
    return lines


def _candidate_for_axis(axis_flex: dict[str, Any]) -> str:
    volunteers = axis_flex.get("volunteer_set") or []
    if not volunteers:
        return "无候选记录"
    row = volunteers[0]
    parts = [
        str(row.get("school_name") or ""),
        str(row.get("major_name") or ""),
    ]
    for key in (
        "min_score",
        "min_rank",
        "risk_level",
        "quality_score",
        "quality_gain",
        "tuition",
        "tuition_delta",
        "outcome_score",
        "outcome_gain",
        "region_relax_strategy",
        "target_region_name",
    ):
        if row.get(key) is not None:
            parts.append(f"{key}={row.get(key)}")
    return "; ".join(part for part in parts if part)


def _evidence_rows(
    personas: list[dict[str, Any]], app_rows: list[dict[str, Any]]
) -> list[str]:
    row_by_case = {row["case_id"]: row for row in app_rows}
    lines = [
        "| Case | Required axes | Axis hit | Representative evidence from hidden set |",
        "|---|---|---|---|",
    ]
    for persona in personas:
        case_id = str(persona["case_id"])
        flex = persona.get("implicit_flexibilities") or {}
        axis_flex = flex.get("axis_flexibilities") or {}
        app_row = row_by_case.get(case_id, {})
        hits = app_row.get("axis_successes") or {}
        evidence = []
        for axis in flex.get("relaxation_axes") or []:
            evidence.append(f"{axis}: {_candidate_for_axis(axis_flex.get(axis) or {})}")
        lines.append(
            f"| `{case_id}` | {', '.join(flex.get('relaxation_axes') or [])} | "
            f"{json.dumps(hits, ensure_ascii=False)} | {'<br>'.join(evidence)} |"
        )
    return lines


def build_markdown(
    *,
    personas: Path,
    output_dir: Path,
    summary_md: Path,
) -> str:
    summary = _load_json(output_dir / "summary.json")
    app_rows = _load_jsonl(output_dir / "reports" / "app_pareto.jsonl")
    hard_rows = _load_jsonl(output_dir / "reports" / "hard_constraint.jsonl")
    persona_items = _load_json(personas)
    app = summary["targets"]["app_pareto"]
    hard = summary["targets"]["hard_constraint"]
    return "\n".join(
        [
            "# multi_axis_v2 轴一致性 Benchmark 压力测试逐例证据",
            "",
            "## 实验定位",
            "",
            "`multi_axis_v2` 是多轴隐藏妥协压力测试的修正版，目标是修正 v1 中部分画像轴不一致的问题。它不替代主实验，也不改变七组单轴/单类实验事实表；它专门检查同一用户同时存在两个隐藏妥协轴时，证据谈判 Agent 是否能同时组织两类证据。",
            "",
            "- Persona: `gaokaollm_bench/sample_data/iceberg_personas_multi_axis_coherent_real_db_30.json`",
            "- Output: `gaokaollm_bench/outputs/agent_benchmark_multi_axis_v2/`",
            f"- Summary: `{summary_md.as_posix()}`",
            "- Hidden fields `implicit_flexibilities`、`volunteer_set`、`axis_flexibilities` 仅用于模拟器和评测器，Agent 不读取。",
            "",
            "## 聚合指标核对",
            "",
            "| Target | Cases | Success | Mean Pareto gain | Mean hallucination | Avg turns |",
            "|---|---:|---:|---:|---:|---:|",
            f"| app_pareto | {app['cases']} | {_fmt_metric(app['elicitation_success_rate'])} | {_fmt_metric(app['mean_pareto_gain'])} | {_fmt_metric(app['mean_hallucination_rate'])} | {app['avg_turns']:.2f} |",
            f"| hard_constraint | {hard['cases']} | {_fmt_metric(hard['elicitation_success_rate'])} | {_fmt_metric(hard['mean_pareto_gain'])} | {_fmt_metric(hard['mean_hallucination_rate'])} | {hard['avg_turns']:.2f} |",
            "",
            "## Profile 结果",
            "",
            *_profile_rows(app_rows),
            "",
            "## 逐例结果",
            "",
            *_case_rows(app_rows, hard_rows),
            "",
            "## 轴级候选证据",
            "",
            *_evidence_rows(persona_items, app_rows),
            "",
            "## 论文可引用结论",
            "",
            "v2 修正后，Benchmark 构造不再依赖无关单轴样本拼接，而是记录 `multi_axis_version=v2` 与 `coherence_checks`。结果显示 app_pareto 仍显著高于硬约束基线，但就业-地域组合和部分质量-学费组合暴露出多轴证据编排瓶颈；这说明压力测试用于发现组合能力上限，而不是替代主实验结论。",
            "",
        ]
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--personas",
        type=Path,
        default=Path(
            "gaokaollm_bench/sample_data/iceberg_personas_multi_axis_coherent_real_db_30.json"
        ),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("gaokaollm_bench/outputs/agent_benchmark_multi_axis_v2"),
    )
    parser.add_argument(
        "--summary-md",
        type=Path,
        default=Path(
            "gaokaollm_bench/outputs/agent_benchmark_multi_axis_v2_summary.md"
        ),
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=Path(
            "gaokaollm_bench/outputs/agent_benchmark_multi_axis_v2_evidence.md"
        ),
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    content = build_markdown(
        personas=args.personas,
        output_dir=args.output_dir,
        summary_md=args.summary_md,
    )
    args.out.write_text(content, encoding="utf-8")
    print(f"Wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
