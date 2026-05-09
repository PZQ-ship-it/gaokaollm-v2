"""Run target agents through the multi-turn benchmark sandbox."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import socket
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from app.core.db_pg import get_database_url
from gaokaollm_bench.evaluator.deterministic_judge import check_hallucination
from gaokaollm_bench.evaluator.llm_as_a_judge import evaluate_process
from gaokaollm_bench.llm.openai_chat import OpenAIChatClient
from gaokaollm_bench.sandbox.arena import run_episode
from gaokaollm_bench.sandbox.base_target import BaseTargetAgent
from gaokaollm_bench.sandbox.target_agents import (
    AppGraphTargetAgent,
    HardConstraintBaselineAgent,
)
from gaokaollm_bench.schemas import EvalReport, IcebergPersona, Transcript


TARGET_APP_PARETO = "app_pareto"
TARGET_HARD_CONSTRAINT = "hard_constraint"
DEFAULT_TARGETS = [TARGET_APP_PARETO, TARGET_HARD_CONSTRAINT]
DEFAULT_MODEL = "gpt-5.2"


@dataclass(frozen=True)
class RunConfig:
    personas_path: Path
    targets: list[str]
    max_turns: int
    limit: int | None
    output_dir: Path
    judge_model: str | None
    simulator_model: str | None
    paper_summary_path: Path | None = Path(
        "gaokaollm_bench/outputs/agent_benchmark_summary.md"
    )
    offline_deterministic: bool = False
    db_preflight: bool = True


def load_personas(path: Path, limit: int | None = None) -> list[IcebergPersona]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, dict) and "items" in data:
        data = data["items"]
    if not isinstance(data, list):
        raise ValueError("personas file must contain a list or {'items': [...]}")
    if limit is not None:
        data = data[:limit]
    return [IcebergPersona.model_validate(item) for item in data]


def build_target(name: str, *, case_id: str) -> BaseTargetAgent:
    if name == TARGET_APP_PARETO:
        return AppGraphTargetAgent(thread_id=f"bench-{case_id}")
    if name == TARGET_HARD_CONSTRAINT:
        return HardConstraintBaselineAgent()
    raise ValueError(f"unknown target: {name}")


def target_requires_db(name: str) -> bool:
    return name in {TARGET_APP_PARETO, TARGET_HARD_CONSTRAINT}


class DeterministicSimulatorLlm:
    """Local simulator fallback for environments without LLM network access."""

    async def ainvoke(self, prompt: Any) -> str:
        text = str(prompt)
        persona = _json_after_label(text, "考生属性:")
        flex = _json_after_label(text, "隐性妥协条件:")
        agent_reply = _slice_between(text, "被测系统回复:", "请输出本轮 JSON。")

        if "我还需要补充" in agent_reply and persona.get("subjects"):
            subjects = "、".join(str(item) for item in persona["subjects"])
            return _json_response(
                thought="系统在补齐必要约束，继续提供选科。",
                is_persuaded=False,
                utterance=f"我的选考是{subjects}。",
            )

        trigger_schools = _trigger_schools(flex)
        has_trigger_school = any(school in agent_reply for school in trigger_schools)
        has_score_evidence = bool(
            "最低分" in agent_reply or "分" in agent_reply and trigger_schools
        )
        if has_trigger_school and has_score_evidence:
            return _json_response(
                thought="回复包含隐藏妥协条件中的学校和分数证据。",
                is_persuaded=True,
                utterance="这些学校和分数证据比较具体，我愿意把这个方向纳入考虑。",
            )

        return _json_response(
            thought="还没有看到足够具体且命中隐藏妥协条件的证据。",
            is_persuaded=False,
            utterance="还是不太能接受，除非你给出更具体的学校和分数对比。",
        )


class DeterministicJudgeLlm:
    """Local process judge fallback for reproducible no-network smoke runs."""

    async def ainvoke(self, prompt: Any) -> str:
        text = str(prompt)
        persona = _json_after_label(text, "Persona:")
        transcript = _json_after_label(text, "Transcript:")
        flex = persona.get("implicit_flexibilities") or {}
        trigger_schools = _trigger_schools(flex)
        agent_turns = [
            turn
            for turn in transcript.get("turns", [])
            if turn.get("role") == "target_agent"
        ]
        combined = "\n".join(str(turn.get("content") or "") for turn in agent_turns)
        success = any(school in combined for school in trigger_schools) and (
            "最低分" in combined or "分" in combined
        )
        baseline_tier = int((persona.get("background") or {}).get("baseline_tier") or 0)
        accepted_tier = _max_trigger_tier(flex, combined)
        pareto_gain = max(0, accepted_tier - baseline_tier) if success else 0
        return json.dumps(
            {
                "case_id": persona.get("case_id") or "",
                "hallucination_rate": 0.0,
                "elicitation_success": success,
                "pareto_gain": pareto_gain,
                "judge_reasoning": (
                    "确定性裁判：检查被测系统是否提到隐藏志愿集合中的学校并给出分数证据。"
                    if success
                    else "确定性裁判：未观察到命中隐藏妥协条件的学校和分数证据。"
                ),
            },
            ensure_ascii=False,
        )


async def evaluate_transcript(
    transcript: Transcript,
    *,
    judge_llm: Any,
) -> EvalReport:
    hallucination_rate = await check_hallucination(transcript, _DefaultDbPool())
    report = await evaluate_process(transcript, transcript.persona, judge_llm)
    return report.model_copy(update={"hallucination_rate": hallucination_rate})


async def run_target_cases(
    *,
    target_name: str,
    personas: list[IcebergPersona],
    config: RunConfig,
    simulator_llm: Any,
    judge_llm: Any,
) -> list[dict[str, Any]]:
    transcript_dir = config.output_dir / "transcripts" / target_name
    report_path = config.output_dir / "reports" / f"{target_name}.jsonl"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    if report_path.exists():
        report_path.unlink()

    rows: list[dict[str, Any]] = []
    for persona in personas:
        target = build_target(target_name, case_id=persona.case_id)
        try:
            transcript = await run_episode(
                persona,
                target,
                max_turns=config.max_turns,
                simulator_llm_client=simulator_llm,
                output_dir=transcript_dir,
            )
            report = await evaluate_transcript(transcript, judge_llm=judge_llm)
            row = {
                "status": "ok",
                "target": target_name,
                "case_id": persona.case_id,
                "hallucination_rate": report.hallucination_rate,
                "elicitation_success": report.elicitation_success,
                "pareto_gain": report.pareto_gain,
                "turns": len(transcript.turns),
                "judge_reasoning": report.judge_reasoning,
                "transcript_path": str(
                    transcript_dir / f"transcript_{persona.case_id}.json"
                ),
            }
        except Exception as exc:
            row = {
                "status": "failed",
                "target": target_name,
                "case_id": persona.case_id,
                "hallucination_rate": None,
                "elicitation_success": False,
                "pareto_gain": 0,
                "turns": 0,
                "judge_reasoning": "",
                "transcript_path": "",
                "error_type": type(exc).__name__,
                "error": str(exc),
            }
        rows.append(row)
        with report_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    return rows


def write_report_jsonl(rows: list[dict[str, Any]], output_dir: Path) -> None:
    report_dir = output_dir / "reports"
    report_dir.mkdir(parents=True, exist_ok=True)
    by_target: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        by_target.setdefault(str(row["target"]), []).append(row)
    for target, target_rows in by_target.items():
        report_path = report_dir / f"{target}.jsonl"
        with report_path.open("w", encoding="utf-8") as handle:
            for row in target_rows:
                handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def aggregate(rows: list[dict[str, Any]]) -> dict[str, Any]:
    by_target: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        by_target.setdefault(str(row["target"]), []).append(row)

    targets: dict[str, dict[str, Any]] = {}
    for target, target_rows in by_target.items():
        count = len(target_rows)
        ok_rows = [row for row in target_rows if row.get("status") == "ok"]
        success_count = sum(1 for row in ok_rows if row["elicitation_success"])
        targets[target] = {
            "cases": count,
            "completed_cases": len(ok_rows),
            "failed_cases": count - len(ok_rows),
            "elicitation_success_rate": _mean(
                1.0 if row["elicitation_success"] else 0.0 for row in ok_rows
            ),
            "success_count": success_count,
            "mean_pareto_gain": _mean(float(row["pareto_gain"]) for row in ok_rows),
            "mean_hallucination_rate": _mean(
                float(row["hallucination_rate"]) for row in ok_rows
            ),
            "avg_turns": _mean(float(row["turns"]) for row in ok_rows),
        }
    return {"targets": targets, "rows": rows}


def write_summary_files(
    *,
    config: RunConfig,
    personas: list[IcebergPersona],
    rows: list[dict[str, Any]],
) -> dict[str, Any]:
    summary = aggregate(rows)
    summary["run"] = {
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "personas": str(config.personas_path),
        "case_count": len(personas),
        "targets": config.targets,
        "max_turns": config.max_turns,
        "judge_model": config.judge_model or os.getenv("OPENAI_MODEL"),
        "simulator_model": config.simulator_model or os.getenv("OPENAI_MODEL"),
        "offline_deterministic": config.offline_deterministic,
        "db_preflight": config.db_preflight,
    }
    config.output_dir.mkdir(parents=True, exist_ok=True)
    (config.output_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    summary_md = render_summary_md(summary)
    (config.output_dir / "summary.md").write_text(summary_md, encoding="utf-8")

    if config.paper_summary_path is not None:
        config.paper_summary_path.parent.mkdir(parents=True, exist_ok=True)
        config.paper_summary_path.write_text(summary_md, encoding="utf-8")
    return summary


def render_summary_md(summary: dict[str, Any]) -> str:
    run = summary["run"]
    lines = [
        "# Agent Benchmark Summary",
        "",
        "## Setting",
        "",
        f"- Personas: `{run['personas']}`",
        f"- Cases: {run['case_count']}",
        f"- Targets: {', '.join(run['targets'])}",
        f"- Max turns: {run['max_turns']}",
        f"- Simulator model: {run.get('simulator_model') or 'not recorded'}",
        f"- Judge model: {run.get('judge_model') or 'not recorded'}",
        f"- Offline deterministic: {run.get('offline_deterministic', False)}",
        "- Default province when omitted by the user: `浙江`",
        "",
        "## Aggregate Results",
        "",
        "| Target | Cases | Completed | Failed | Elicitation Success | Mean Pareto Gain | Mean Hallucination | Avg Turns |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for target, metrics in summary["targets"].items():
        lines.append(
            f"| {target} | {metrics['cases']} | "
            f"{metrics['completed_cases']} | "
            f"{metrics['failed_cases']} | "
            f"{metrics['elicitation_success_rate']:.3f} | "
            f"{metrics['mean_pareto_gain']:.3f} | "
            f"{metrics['mean_hallucination_rate']:.3f} | "
            f"{metrics['avg_turns']:.2f} |"
        )

    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "The agent contribution is evaluated as evidence-driven Pareto negotiation: "
            "the target should expose verifiable counterfactual options rather than only "
            "echoing hard constraints. In this run, `app_pareto` is expected to use "
            "`major_geo_relax`, a joint major-and-region relaxation path aligned with "
            "the `major_hierarchy` persona construction. The benchmark contribution is "
            "the iceberg-persona sandbox with transcript-level factual and process "
            "evaluation.",
            "",
            "## Case Notes",
            "",
        ]
    )
    for row in summary["rows"][:5]:
        if row.get("status") == "ok":
            lines.append(
                f"- `{row['target']}` / `{row['case_id']}`: "
                f"success={row['elicitation_success']}, "
                f"pareto_gain={row['pareto_gain']}, "
                f"hallucination={row['hallucination_rate']:.3f}. "
                f"{row['judge_reasoning']}"
            )
        else:
            lines.append(
                f"- `{row['target']}` / `{row['case_id']}` failed: "
                f"{row.get('error_type')}: {row.get('error')}"
            )

    lines.extend(
        [
            "",
            "## Limitations",
            "",
            "Results depend on the configured simulator and judge models, the current "
            "PostgreSQL snapshot, and the selected persona subset. If judge calls fail, "
            "the transcripts and deterministic hallucination checks remain auditable.",
            "",
        ]
    )
    return "\n".join(lines)


def _mean(values: Any) -> float:
    items = list(values)
    if not items:
        return 0.0
    return sum(items) / len(items)


def is_database_reachable(timeout: float = 2.0) -> tuple[bool, str]:
    url = get_database_url()
    parsed = urlparse(url)
    host = parsed.hostname or "127.0.0.1"
    port = parsed.port or 5432
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True, f"{host}:{port}"
    except OSError as exc:
        return False, f"{host}:{port} ({type(exc).__name__}: {exc})"


def preflight_failure_rows(
    *,
    config: RunConfig,
    personas: list[IcebergPersona],
    reason: str,
) -> list[dict[str, Any]]:
    rows = []
    for target in config.targets:
        if not target_requires_db(target):
            continue
        for persona in personas:
            rows.append(
                {
                    "status": "failed",
                    "target": target,
                    "case_id": persona.case_id,
                    "hallucination_rate": None,
                    "elicitation_success": False,
                    "pareto_gain": 0,
                    "turns": 0,
                    "judge_reasoning": "",
                    "transcript_path": "",
                    "error_type": "PreflightFailed",
                    "error": reason,
                }
            )
    return rows


def _json_response(*, thought: str, is_persuaded: bool, utterance: str) -> str:
    return json.dumps(
        {
            "thought": thought,
            "is_persuaded": is_persuaded,
            "utterance": utterance,
        },
        ensure_ascii=False,
    )


def _slice_between(text: str, start: str, end: str) -> str:
    if start not in text:
        return ""
    value = text.split(start, 1)[1]
    if end in value:
        value = value.split(end, 1)[0]
    return value.strip()


def _json_after_label(text: str, label: str) -> dict[str, Any]:
    if label not in text:
        return {}
    tail = text.split(label, 1)[1].lstrip()
    decoder = json.JSONDecoder()
    try:
        data, _ = decoder.raw_decode(tail)
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def _trigger_schools(flex: dict[str, Any]) -> list[str]:
    schools: list[str] = []
    for key in ("trigger_school", "accepted_school"):
        value = flex.get(key)
        if isinstance(value, str):
            schools.append(value)
    for row in flex.get("volunteer_set") or []:
        if isinstance(row, dict) and row.get("school_name"):
            schools.append(str(row["school_name"]))
    return list(dict.fromkeys(schools))


def _max_trigger_tier(flex: dict[str, Any], text: str) -> int:
    tiers = []
    for row in flex.get("volunteer_set") or []:
        if not isinstance(row, dict):
            continue
        if str(row.get("school_name") or "") not in text:
            continue
        try:
            tiers.append(int(row.get("tier") or 0))
        except (TypeError, ValueError):
            pass
    return max(tiers) if tiers else 0


class _DefaultDbPool:
    async def fetch(self, query: str, *params: Any) -> list[dict[str, Any]]:
        from app.core import db_pg

        return await db_pg.fetch_query(query, *params)


async def async_main(args: argparse.Namespace) -> None:
    config = RunConfig(
        personas_path=Path(args.personas),
        targets=args.targets,
        max_turns=args.max_turns,
        limit=args.limit,
        output_dir=Path(args.output_dir),
        judge_model=args.judge_model,
        simulator_model=args.simulator_model,
        paper_summary_path=Path(args.paper_summary) if args.paper_summary else None,
        offline_deterministic=args.offline_deterministic,
        db_preflight=not args.skip_db_preflight,
    )
    personas = load_personas(config.personas_path, config.limit)
    if config.db_preflight and any(target_requires_db(name) for name in config.targets):
        db_ok, db_status = is_database_reachable()
        if not db_ok:
            rows = preflight_failure_rows(
                config=config,
                personas=personas,
                reason=f"database is not reachable: {db_status}",
            )
            write_report_jsonl(rows, config.output_dir)
            write_summary_files(config=config, personas=personas, rows=rows)
            return

    if config.offline_deterministic:
        simulator_llm = DeterministicSimulatorLlm()
        judge_llm = DeterministicJudgeLlm()
    else:
        llm_client = OpenAIChatClient(timeout=args.request_timeout)
        simulator_llm = llm_client.as_chat_model(
            model=config.simulator_model or os.getenv("OPENAI_MODEL") or DEFAULT_MODEL,
            temperature=0,
        )
        judge_llm = llm_client.as_chat_model(
            model=config.judge_model or os.getenv("OPENAI_MODEL") or DEFAULT_MODEL,
            temperature=0,
        )

    all_rows: list[dict[str, Any]] = []
    for target_name in config.targets:
        rows = await run_target_cases(
            target_name=target_name,
            personas=personas,
            config=config,
            simulator_llm=simulator_llm,
            judge_llm=judge_llm,
        )
        all_rows.extend(rows)

    write_summary_files(config=config, personas=personas, rows=all_rows)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run app and baseline agents through gaokaollm-bench."
    )
    parser.add_argument("--personas", required=True)
    parser.add_argument("--targets", nargs="+", default=DEFAULT_TARGETS)
    parser.add_argument("--max-turns", type=int, default=6)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument(
        "--output-dir",
        default="gaokaollm_bench/outputs/agent_benchmark",
    )
    parser.add_argument("--judge-model", default=None)
    parser.add_argument("--simulator-model", default=None)
    parser.add_argument(
        "--paper-summary",
        default="gaokaollm_bench/outputs/agent_benchmark_summary.md",
        help="Optional markdown path for the thesis-facing summary; pass empty to skip.",
    )
    parser.add_argument("--request-timeout", type=float, default=90.0)
    parser.add_argument(
        "--offline-deterministic",
        action="store_true",
        help="Use local deterministic simulator and judge instead of LLM calls.",
    )
    parser.add_argument(
        "--skip-db-preflight",
        action="store_true",
        help="Skip the fast PostgreSQL reachability check before running DB targets.",
    )
    return parser


def main() -> None:
    asyncio.run(async_main(build_parser().parse_args()))


if __name__ == "__main__":
    main()
