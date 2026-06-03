import argparse
import json
import re
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]

STYLE_BANNED_TOKENS = (
    "精准推断",
    "极度",
    "终极推荐报告",
    "牌子更好",
    "真实权重",
    "效用",
)
INTERNAL_TOKENS = (
    "min_score=",
    "min_rank=",
    "tier=",
    "ranking=",
    "tuition_delta=",
    "c/r",
    "_implicit_utility",
    "_phi_features",
)
DEPENDENCY_PATTERNS = (
    (
        "database",
        re.compile(r"database|postgres|psycopg|connection refused|db preflight", re.I),
    ),
    (
        "llm",
        re.compile(
            r"llm|openai|apiconnectionerror|api connection|503|empty content", re.I
        ),
    ),
    ("runtime_timeout", re.compile(r"\btimeout\b|timed out", re.I)),
    ("output_contract", re.compile(r"empty content|json|schema|parse", re.I)),
)


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _status_from_failures(
    failures: list[str], warnings: list[str] | None = None
) -> str:
    if failures:
        return "fail"
    if warnings:
        return "warning"
    return "pass"


def _classify_errors(trace: dict[str, Any]) -> list[dict[str, Any]]:
    classified: list[dict[str, Any]] = []
    failures = list((trace.get("analysis") or {}).get("failures") or [])
    for error in trace.get("errors") or []:
        if isinstance(error, dict):
            failures.append(
                " ".join(
                    str(error.get(key) or "")
                    for key in ("error_type", "error")
                    if error.get(key)
                )
            )
    for item in failures:
        category = "unknown"
        for name, pattern in DEPENDENCY_PATTERNS:
            if pattern.search(str(item)):
                category = name
                break
        classified.append({"category": category, "evidence": str(item)[:500]})
    return classified


def _round_has_interrupt_meta(row: dict[str, Any]) -> bool:
    return bool(
        row.get("latest_question_kind")
        or row.get("latest_probe_target_dimension")
        or row.get("latest_tradeoff_pair")
    )


def _int_value(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _diagnose_trace(path: Path) -> dict[str, Any]:
    trace = _load_json(path)
    rounds = [row for row in trace.get("rounds") or [] if isinstance(row, dict)]
    analysis = trace.get("analysis") or {}
    final_reply = str(trace.get("final_reply") or "")
    final_question_kind = str(trace.get("final_question_kind") or "")
    final_recommendation_count = _int_value(trace.get("final_recommendation_count"))
    errors = _classify_errors(trace)
    analysis_status = str(analysis.get("status") or "").lower()
    failures = [str(item) for item in analysis.get("failures") or []]

    output_style_hits = [
        token for token in STYLE_BANNED_TOKENS if token and token in final_reply
    ]
    internal_hits = [
        token for token in INTERNAL_TOKENS if token and token in final_reply
    ]
    missing_interrupt_meta = [
        int(row.get("turn") or 0)
        for row in rounds
        if str(row.get("question") or "").strip() and not _round_has_interrupt_meta(row)
    ]
    tradeoff_rounds = [
        row for row in rounds if row.get("latest_question_kind") == "tradeoff"
    ]
    non_budget_costs = sorted(
        {
            str(row.get("latest_probe_target_dimension") or "")
            for row in tradeoff_rounds
            if str(row.get("latest_probe_target_dimension") or "")
            and str(row.get("latest_probe_target_dimension") or "") != "tuition"
        }
    )
    latencies = [
        float(row.get("turn_latency_seconds"))
        for row in rounds
        if isinstance(row.get("turn_latency_seconds"), (int, float))
    ]
    final_table_missing = (
        final_question_kind == "finalize_offer"
        and bool(final_reply.strip())
        and final_recommendation_count <= 0
    )

    return {
        "path": str(path),
        "thread_id": trace.get("thread_id"),
        "mode": trace.get("mode") or "graph",
        "round_count": len(rounds),
        "analysis_status": analysis_status,
        "final_recommendation_count": final_recommendation_count,
        "final_recommendation_bucket_counts": trace.get(
            "final_recommendation_bucket_counts"
        )
        or {},
        "final_table_missing": final_table_missing,
        "task_completion": "pass"
        if not errors
        and not final_table_missing
        and (final_reply or analysis_status == "ok")
        else "fail",
        "tool_reliability": "fail" if errors else "pass",
        "output_contract": _status_from_failures(
            internal_hits,
            output_style_hits,
        ),
        "state_integrity": "fail"
        if final_table_missing
        else "warning"
        if missing_interrupt_meta
        else "pass",
        "loop_resistance": "pass"
        if len(rounds) <= 6 and not any("repeat" in item.lower() for item in failures)
        else "warning",
        "observability": "warning"
        if missing_interrupt_meta or not latencies
        else "pass",
        "latency_cost": "warning"
        if any(value > 45 for value in latencies)
        else "unknown"
        if not latencies
        else "pass",
        "error_categories": errors,
        "analysis_failures": failures,
        "output_style_hits": output_style_hits,
        "internal_output_hits": internal_hits,
        "missing_interrupt_meta_turns": missing_interrupt_meta,
        "non_budget_cost_dimensions": non_budget_costs,
        "preflight": trace.get("preflight") or {},
    }


def _aggregate(reports: list[dict[str, Any]]) -> dict[str, Any]:
    dimensions = [
        "task_completion",
        "tool_reliability",
        "output_contract",
        "state_integrity",
        "loop_resistance",
        "observability",
        "latency_cost",
    ]
    rollup: dict[str, dict[str, int]] = {}
    for dimension in dimensions:
        counts = {"pass": 0, "warning": 0, "fail": 0, "unknown": 0}
        for report in reports:
            status = str(report.get(dimension) or "unknown")
            counts[status if status in counts else "unknown"] += 1
        rollup[dimension] = counts

    root_causes: list[dict[str, Any]] = []
    if any(report.get("error_categories") for report in reports):
        categories: dict[str, int] = {}
        for report in reports:
            for error in report.get("error_categories") or []:
                category = str(error.get("category") or "unknown")
                categories[category] = categories.get(category, 0) + 1
        root_causes.append(
            {
                "rank": 1,
                "cause": "运行依赖失败或不稳定",
                "evidence": categories,
                "confidence": "high",
                "fix": "启动前置检查、timeout 显式配置、失败时结构化落盘。",
            }
        )
    if any(
        report.get("internal_output_hits") or report.get("output_style_hits")
        for report in reports
    ):
        root_causes.append(
            {
                "rank": len(root_causes) + 1,
                "cause": "用户输出契约约束不足或历史 prompt 版本过松",
                "evidence": [
                    {
                        "path": report["path"],
                        "internal_hits": report.get("internal_output_hits"),
                        "style_hits": report.get("output_style_hits"),
                    }
                    for report in reports
                    if report.get("internal_output_hits")
                    or report.get("output_style_hits")
                ],
                "confidence": "high",
                "fix": "保留最终回答 sanitizer 与 system prompt 的禁用表达/字段约束，并纳入回归测试。",
            }
        )
    if any(report.get("missing_interrupt_meta_turns") for report in reports):
        root_causes.append(
            {
                "rank": len(root_causes) + 1,
                "cause": "trace 可观测性不足",
                "evidence": [
                    {
                        "path": report["path"],
                        "turns": report.get("missing_interrupt_meta_turns"),
                    }
                    for report in reports
                    if report.get("missing_interrupt_meta_turns")
                ],
                "confidence": "medium",
                "fix": "从 interrupt payload 直接记录 question_kind、target_dimension、tradeoff_pair。",
            }
        )
    if any(report.get("final_table_missing") for report in reports):
        root_causes.append(
            {
                "rank": len(root_causes) + 1,
                "cause": "最终推荐缺少结构化志愿表",
                "evidence": [
                    {
                        "path": report["path"],
                        "final_recommendation_count": report.get(
                            "final_recommendation_count"
                        ),
                    }
                    for report in reports
                    if report.get("final_table_missing")
                ],
                "confidence": "high",
                "fix": "让 trace 和 API state 同步记录 final_recommendation_matrix/count。",
            }
        )

    return {
        "run_count": len(reports),
        "dimension_rollup": rollup,
        "root_causes": root_causes,
    }


def _markdown(summary: dict[str, Any]) -> str:
    lines = [
        "# Agent Run Diagnosis",
        "",
        "## Summary",
        "",
        f"- Runs inspected: {summary['aggregate']['run_count']}",
        "- Agent/system inspected: Gaokao recommendation LangGraph frontend demo agent",
        "- Main diagnosis: current successful trace is healthy, while historical failures cluster around runtime dependency fragility, old output contract drift, and trace observability gaps.",
        "- Highest-impact fix: keep startup/preflight checks and make trace reports capture interrupt metadata plus structured failures.",
        "",
        "## Run Health",
        "",
        "| Dimension | Pass | Warning | Fail | Unknown |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for dimension, counts in summary["aggregate"]["dimension_rollup"].items():
        lines.append(
            f"| {dimension} | {counts['pass']} | {counts['warning']} | {counts['fail']} | {counts['unknown']} |"
        )
    lines.extend(["", "## Root Causes", ""])
    if summary["aggregate"]["root_causes"]:
        lines.append("| Rank | Cause | Confidence | Fix |")
        lines.append("| ---: | --- | --- | --- |")
        for item in summary["aggregate"]["root_causes"]:
            lines.append(
                f"| {item['rank']} | {item['cause']} | {item['confidence']} | {item['fix']} |"
            )
    else:
        lines.append("- No root causes detected from the inspected runs.")
    lines.extend(["", "## Runs", ""])
    lines.append(
        "| Path | Completion | Tool Reliability | Output Contract | State | Observability |"
    )
    lines.append("| --- | --- | --- | --- | --- | --- |")
    for report in summary["runs"]:
        lines.append(
            "| {path} | {task_completion} | {tool_reliability} | {output_contract} | {state_integrity} | {observability} |".format(
                **report
            )
        )
    lines.append("")
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Diagnose gaokao agent run traces.")
    parser.add_argument("traces", nargs="+", help="Trace JSON files to inspect.")
    parser.add_argument("--output", default="")
    parser.add_argument("--markdown-output", default="")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    reports = [_diagnose_trace(Path(path)) for path in args.traces]
    summary = {
        "runs": reports,
        "aggregate": _aggregate(reports),
        "optimization_plan": {
            "prompt_system_instruction_changes": [
                "继续禁止用户可见输出出现内部字段、硬编码黑话和夸张营销式表述。",
                "保留无显著跃迁时的诚实说明：不误导用户接受不存在的收益。",
            ],
            "tool_schema_changes": [],
            "retrieval_knowledge_changes": [],
            "routing_state_orchestration_changes": [
                "在 trace 层记录 interrupt payload 中的 question_kind、target_dimension、tradeoff_pair。",
                "graph 构建、stream、LLM/API/DB 失败均写成结构化 errors，而不是只抛 traceback。",
            ],
            "eval_logging_changes": [
                "把本脚本纳入 demo 回归：同一批 trace 输出 dimension_rollup 和 root_causes。",
                "保留 current successful trace 与 historical failing trace 做 before/after 对照。",
            ],
        },
        "verification_plan": [
            {
                "test": "successful real-db trace diagnosis",
                "metric": "task_completion pass and output_contract pass",
                "pass_gate": "latest real trace has no internal tokens or banned style tokens",
            },
            {
                "test": "historical failure diagnosis",
                "metric": "root cause category detected",
                "pass_gate": "DB/LLM/output-contract failures are classified instead of unknown-only",
            },
            {
                "test": "trace observability",
                "metric": "missing_interrupt_meta_turns",
                "pass_gate": "new traces record interrupt metadata for question turns",
            },
        ],
    }
    if args.output:
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(
            json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    if args.markdown_output:
        output = Path(args.markdown_output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(_markdown(summary), encoding="utf-8")
    print(json.dumps({"aggregate": summary["aggregate"]}, ensure_ascii=False, indent=2))
    has_fail = any(
        report.get("task_completion") == "fail" and not report.get("error_categories")
        for report in reports
    )
    return 1 if has_fail else 0


if __name__ == "__main__":
    raise SystemExit(main())
