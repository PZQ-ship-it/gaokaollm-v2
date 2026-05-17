"""Run target agents through the multi-turn benchmark sandbox."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import socket
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from app.core.db_pg import get_database_url
from gaokaollm_bench.evaluator.candidate_set_oracle import (
    acceptable_rows_from_flex,
    apply_candidate_leakage_veto,
    evaluate_candidate_set_oracle,
    matched_acceptable_candidates,
    transcript_candidate_diagnostics,
)
from gaokaollm_bench.evaluator.deterministic_judge import check_hallucination
from gaokaollm_bench.evaluator.llm_as_a_judge import evaluate_process
from gaokaollm_bench.llm.openai_chat import OpenAIChatClient
from gaokaollm_bench.sandbox.arena import run_episode
from gaokaollm_bench.sandbox.base_target import BaseTargetAgent
from gaokaollm_bench.sandbox.target_agents import (
    AppGraphTargetAgent,
    HardConstraintBaselineAgent,
    PromptedV1SoftRagBaselineAgent,
    V1SoftRagBaselineAgent,
)
from gaokaollm_bench.sandbox.v1_hybrid_rag import V1HybridRagBaselineAgent
from gaokaollm_bench.schemas import EvalReport, IcebergPersona, Transcript
from gaokaollm_bench.utils.trace import trace_event


TARGET_APP_PARETO = "app_pareto"
TARGET_APP_PARETO_FULL = "app_pareto_full"
TARGET_APP_PARETO_NO_UCB = "app_pareto_no_ucb"
TARGET_APP_PARETO_NO_TRACKER = "app_pareto_no_tracker"
TARGET_HARD_CONSTRAINT = "hard_constraint"
TARGET_V1_SOFT_RAG = "v1_soft_rag"
TARGET_V1_HYBRID_RAG = "v1_hybrid_rag"
TARGET_V1_PROMPT_DIRECT = "v1_prompt_direct"
TARGET_V1_PROMPT_COT = "v1_prompt_cot"
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
    case_timeout: float | None = None
    concurrency: int = 1
    case_retries: int = 0
    skip_existing_cases: bool = False


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
    app_aliases = {
        TARGET_APP_PARETO: "full",
        TARGET_APP_PARETO_FULL: "full",
        TARGET_APP_PARETO_NO_UCB: "no_ucb",
        TARGET_APP_PARETO_NO_TRACKER: "no_tracker",
    }
    if name in app_aliases:
        return AppGraphTargetAgent(
            thread_id=f"bench-{case_id}-{name}",
            ablation_mode=app_aliases[name],
            target_name=name,
        )
    if name == TARGET_HARD_CONSTRAINT:
        return HardConstraintBaselineAgent()
    if name == TARGET_V1_SOFT_RAG:
        return V1SoftRagBaselineAgent()
    if name == TARGET_V1_PROMPT_DIRECT:
        return PromptedV1SoftRagBaselineAgent(prompt_style="direct")
    if name == TARGET_V1_PROMPT_COT:
        return PromptedV1SoftRagBaselineAgent(prompt_style="cot")
    if name == TARGET_V1_HYBRID_RAG:
        return V1HybridRagBaselineAgent()
    raise ValueError(f"unknown target: {name}")


def target_requires_db(name: str) -> bool:
    return name in {
        TARGET_APP_PARETO,
        TARGET_APP_PARETO_FULL,
        TARGET_APP_PARETO_NO_UCB,
        TARGET_APP_PARETO_NO_TRACKER,
        TARGET_HARD_CONSTRAINT,
        TARGET_V1_SOFT_RAG,
        TARGET_V1_PROMPT_DIRECT,
        TARGET_V1_PROMPT_COT,
        TARGET_V1_HYBRID_RAG,
    }


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
        if flex.get("constraint_relaxed") == "multi_axis":
            has_trigger_school = _has_multi_axis_evidence(flex, agent_reply)
        elif flex.get("constraint_relaxed") == "risk_band":
            has_trigger_school = _has_risk_band_evidence(flex, agent_reply)
        elif flex.get("constraint_relaxed") == "strength":
            has_trigger_school = _has_strength_evidence(flex, agent_reply)
        elif flex.get("constraint_relaxed") == "major_quality":
            has_trigger_school = _has_major_quality_evidence(flex, agent_reply)
        elif flex.get("constraint_relaxed") == "tuition_value":
            has_trigger_school = _has_tuition_value_evidence(flex, agent_reply)
        elif flex.get("constraint_relaxed") == "employment_outcome":
            has_trigger_school = _has_employment_outcome_evidence(flex, agent_reply)
        elif flex.get("constraint_relaxed") == "region_tree":
            has_trigger_school = _has_region_tree_evidence(flex, agent_reply)
        else:
            has_trigger_school = any(
                school in agent_reply for school in trigger_schools
            )
        has_score_evidence = bool(
            "最低分" in agent_reply
            or "min_score" in agent_reply
            or "score_margin" in agent_reply
            or "分" in agent_reply
            and trigger_schools
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
        if flex.get("constraint_relaxed") == "multi_axis":
            success = _has_multi_axis_evidence(flex, combined)
        elif flex.get("constraint_relaxed") == "risk_band":
            success = _has_risk_band_evidence(flex, combined)
        elif flex.get("constraint_relaxed") == "strength":
            success = _has_strength_evidence(flex, combined)
        elif flex.get("constraint_relaxed") == "major_quality":
            success = _has_major_quality_evidence(flex, combined)
        elif flex.get("constraint_relaxed") == "tuition_value":
            success = _has_tuition_value_evidence(flex, combined)
        elif flex.get("constraint_relaxed") == "employment_outcome":
            success = _has_employment_outcome_evidence(flex, combined)
        elif flex.get("constraint_relaxed") == "region_tree":
            success = _has_region_tree_evidence(flex, combined)
        else:
            success = any(school in combined for school in trigger_schools) and (
                "最低分" in combined
                or "min_score" in combined
                or "score_margin" in combined
                or "分" in combined
            )
        baseline_tier = int((persona.get("background") or {}).get("baseline_tier") or 0)
        if flex.get("constraint_relaxed") == "multi_axis":
            pareto_gain = _multi_axis_gain(flex, combined) if success else 0
        elif flex.get("constraint_relaxed") == "risk_band":
            pareto_gain = _risk_portfolio_gain(flex) if success else 0
        elif flex.get("constraint_relaxed") == "strength":
            pareto_gain = _strength_rank_gain(flex, combined) if success else 0
        elif flex.get("constraint_relaxed") == "major_quality":
            pareto_gain = _major_quality_gain(flex, combined) if success else 0
        elif flex.get("constraint_relaxed") == "tuition_value":
            pareto_gain = _tuition_value_gain(flex, combined) if success else 0
        elif flex.get("constraint_relaxed") == "employment_outcome":
            pareto_gain = _employment_outcome_gain(flex, combined) if success else 0
        elif flex.get("constraint_relaxed") == "region_tree":
            pareto_gain = _region_tree_gain(flex, combined) if success else 0
        else:
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
    report = report.model_copy(update={"hallucination_rate": hallucination_rate})
    return evaluate_candidate_set_oracle(report, transcript)


def apply_golden_leakage_veto(
    report: EvalReport,
    transcript: Transcript,
) -> EvalReport:
    diagnostics = transcript_diagnostics(transcript)
    vetoed = apply_candidate_leakage_veto(report, transcript)
    if (
        vetoed is not report
        and vetoed.elicitation_success != report.elicitation_success
    ):
        trace_event(
            "Evaluator",
            "candidate_leakage_veto",
            {
                "case_id": transcript.persona.case_id,
                "diagnostics": diagnostics,
            },
        )
    return vetoed


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
    existing_ok_rows: list[dict[str, Any]] = []
    if config.skip_existing_cases and report_path.exists():
        existing_ok_rows = _existing_ok_rows(report_path)
    elif report_path.exists():
        report_path.unlink()

    rows: list[dict[str, Any]] = list(existing_ok_rows)
    completed_case_ids = {str(row.get("case_id")) for row in existing_ok_rows}
    pending_personas = [
        persona for persona in personas if persona.case_id not in completed_case_ids
    ]
    if config.skip_existing_cases and existing_ok_rows:
        with report_path.open("w", encoding="utf-8") as handle:
            for row in existing_ok_rows:
                handle.write(json.dumps(row, ensure_ascii=False) + "\n")
        print(
            f"[agent_benchmark] {target_name}: "
            f"skipping {len(existing_ok_rows)} completed cases, "
            f"running {len(pending_personas)} pending cases"
        )
    if not pending_personas:
        return rows

    async def _run_persona(persona: IcebergPersona) -> dict[str, Any]:
        max_attempts = max(1, int(config.case_retries or 0) + 1)
        last_error: Exception | None = None
        for attempt in range(1, max_attempts + 1):
            try:
                target = build_target(target_name, case_id=persona.case_id)
                row = await _run_one_case(
                    persona=persona,
                    target=target,
                    target_name=target_name,
                    config=config,
                    simulator_llm=simulator_llm,
                    judge_llm=judge_llm,
                    transcript_dir=transcript_dir,
                )
                if attempt > 1:
                    row["attempts"] = attempt
                flex = persona.implicit_flexibilities or {}
                if flex.get("constraint_relaxed") == "multi_axis":
                    details = _multi_axis_details(
                        flex,
                        _transcript_text_from_path(row.get("transcript_path")),
                    )
                    row["required_axes"] = details["required_axes"]
                    row["axis_successes"] = details["axis_successes"]
                    row["axis_pareto_gains"] = details["axis_pareto_gains"]
                return row
            except Exception as exc:
                last_error = exc
                if attempt < max_attempts:
                    await asyncio.sleep(min(20.0, 3.0 * attempt))
        assert last_error is not None
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
            "error_type": type(last_error).__name__,
            "error": str(last_error),
            "attempts": max_attempts,
        }
        return row

    concurrency = max(1, int(config.concurrency or 1))
    if concurrency == 1:
        for persona in pending_personas:
            row = await _run_persona(persona)
            rows.append(row)
            with report_path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(row, ensure_ascii=False) + "\n")
        return rows

    semaphore = asyncio.Semaphore(concurrency)

    async def _run_limited(persona: IcebergPersona) -> dict[str, Any]:
        async with semaphore:
            return await _run_persona(persona)

    tasks = [asyncio.create_task(_run_limited(persona)) for persona in pending_personas]
    for task in asyncio.as_completed(tasks):
        row = await task
        rows.append(row)
        with report_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    return rows


def _existing_ok_rows(report_path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    try:
        lines = report_path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return rows
    seen: set[str] = set()
    for line in lines:
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if row.get("status") != "ok":
            continue
        case_id = str(row.get("case_id") or "")
        if not case_id or case_id in seen:
            continue
        transcript_path = str(row.get("transcript_path") or "")
        if transcript_path and not Path(transcript_path).exists():
            continue
        seen.add(case_id)
        rows.append(row)
    return rows


async def _run_one_case(
    *,
    persona: IcebergPersona,
    target: BaseTargetAgent,
    target_name: str,
    config: RunConfig,
    simulator_llm: Any,
    judge_llm: Any,
    transcript_dir: Path,
) -> dict[str, Any]:
    async def _run() -> dict[str, Any]:
        trace_event(
            "BenchmarkRunner",
            "case_start",
            {
                "target": target_name,
                "case_id": persona.case_id,
                "max_turns": config.max_turns,
            },
        )
        transcript = await run_episode(
            persona,
            target,
            max_turns=config.max_turns,
            simulator_llm_client=simulator_llm,
            output_dir=transcript_dir,
        )
        trace_event(
            "BenchmarkRunner",
            "episode_finished",
            {
                "target": target_name,
                "case_id": persona.case_id,
                "turns": len(transcript.turns),
                "diagnostics": transcript_diagnostics(transcript),
            },
        )
        report = await evaluate_transcript(transcript, judge_llm=judge_llm)
        diagnostics = transcript_diagnostics(transcript)
        trace_event(
            "BenchmarkRunner",
            "evaluation_finished",
            {
                "target": target_name,
                "case_id": persona.case_id,
                "report": report.model_dump(),
                "diagnostics": diagnostics,
            },
        )
        return {
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
            **diagnostics,
        }

    if config.case_timeout and config.case_timeout > 0:
        return await asyncio.wait_for(_run(), timeout=config.case_timeout)
    return await _run()


def _transcript_text_from_path(path_value: Any) -> str:
    if not path_value:
        return ""
    try:
        transcript = Transcript.model_validate_json(
            Path(str(path_value)).read_text(encoding="utf-8")
        )
    except (OSError, ValueError):
        return ""
    return _combined_target_agent_text(transcript)


def transcript_diagnostics(transcript: Transcript) -> dict[str, Any]:
    target_turns = [
        turn for turn in transcript.turns if str(turn.role) == "target_agent"
    ]
    target_count = len(target_turns)
    previous_user = ""
    echo_count = 0
    probe_count = 0
    pareto_diff_count = 0
    uniform_weight_count = 0
    constant_variance_count = 0
    golden_echo_count = 0
    target_golden_evidence_count = 0
    first_role = ""
    first_turn: int | str = ""
    first_school = ""
    golden = _golden_evidence(transcript.persona)
    candidate_set = transcript_candidate_diagnostics(transcript)

    for turn in transcript.turns:
        role = str(turn.role)
        content = str(turn.content or "")
        if golden["schools"] and not first_role:
            for school in golden["schools"]:
                if school and school in content:
                    first_role = role
                    first_turn = turn.turn_id
                    first_school = school
                    break

        if role == "user":
            previous_user = _normalize_turn_text(content)
            continue
        if role != "target_agent":
            continue

        normalized = _normalize_turn_text(content)
        state = dict(turn.internal_state or {})
        is_echo = bool(normalized and normalized == previous_user)
        if is_echo:
            echo_count += 1
        if _is_probe_turn(state, content):
            probe_count += 1
        if state.get("latest_pareto_diff"):
            pareto_diff_count += 1
        if _is_uniform_weights(state.get("implicit_weights")):
            uniform_weight_count += 1
        if _is_constant_variance(state.get("weight_variance")):
            constant_variance_count += 1
        if _target_mentions_golden_evidence(content, golden):
            target_golden_evidence_count += 1
            if is_echo:
                golden_echo_count += 1

    return {
        "target_turn_count": target_count,
        "echo_rate": echo_count / target_count if target_count else 0.0,
        "probe_question_rate": probe_count / target_count if target_count else 0.0,
        "pareto_diff_rate": pareto_diff_count / target_count if target_count else 0.0,
        "uniform_weight_rate": (
            uniform_weight_count / target_count if target_count else 0.0
        ),
        "constant_variance_rate": (
            constant_variance_count / target_count if target_count else 0.0
        ),
        "golden_first_mention_role": first_role,
        "golden_first_mention_turn": first_turn,
        "golden_first_mention_school": first_school,
        "target_supplied_golden_evidence": target_golden_evidence_count > 0,
        "target_golden_evidence_count": target_golden_evidence_count,
        "golden_echo_target_count": golden_echo_count,
        **candidate_set,
    }


def _normalize_turn_text(text: str) -> str:
    return " ".join(str(text or "").split())


def _is_probe_turn(state: dict[str, Any], content: str) -> bool:
    if state.get("reply_source") in {
        "result_interrupt",
        "snapshot_interrupt",
        "latest_agent_probe_question",
    }:
        return True
    if state.get("latest_agent_probe_question"):
        return True
    return "选项A" in content and "选项B" in content


def _is_uniform_weights(value: Any) -> bool:
    if not isinstance(value, dict):
        return False
    dimensions = ("school", "major", "tuition", "quality", "geo")
    try:
        return all(abs(float(value.get(dim, -1.0)) - 0.2) <= 1e-9 for dim in dimensions)
    except (TypeError, ValueError):
        return False


def _is_constant_variance(value: Any) -> bool:
    if not isinstance(value, dict):
        return False
    dimensions = ("school", "major", "tuition", "quality", "geo")
    try:
        return all(abs(float(value.get(dim, -1.0)) - 1.0) <= 1e-9 for dim in dimensions)
    except (TypeError, ValueError):
        return False


def _golden_evidence(persona: IcebergPersona) -> dict[str, list[str]]:
    flex = persona.implicit_flexibilities or {}
    rows = acceptable_rows_from_flex(flex)

    schools: list[str] = []
    scores: list[str] = []
    for row in rows:
        school = str(row.get("school_name") or "")
        score = row.get("min_score")
        if school:
            schools.append(school)
        if score not in (None, ""):
            scores.append(str(score))
    return {
        "schools": list(dict.fromkeys(schools)),
        "scores": list(dict.fromkeys(scores)),
    }


def _target_mentions_golden_evidence(text: str, golden: dict[str, list[str]]) -> bool:
    if not text:
        return False
    has_school = any(school and school in text for school in golden.get("schools", []))
    if not has_school:
        return False
    has_exact_score = any(
        score and re.search(rf"(?<!\d){re.escape(score)}(?!\d)", text)
        for score in golden.get("scores", [])
    )
    has_score_word = bool(
        re.search(r"(最低分|min_score|score_margin|分数|位次).{0,20}\d{3}", text)
        or re.search(r"\d{3}.{0,20}(最低分|min_score|score_margin|分数|位次)", text)
    )
    return bool(has_exact_score or has_score_word)


def _target_mentions_acceptable_evidence(text: str, flex: dict[str, Any]) -> bool:
    return bool(matched_acceptable_candidates(text, flex))


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
            "`major_geo_relax` for joint major-and-region relaxation and "
            "`risk_band_relax` for conservative-to-chong/wen/bao portfolio negotiation; "
            "`strength_relax` is used when the persona targets school-strength evidence; "
            "`major_quality_relax` is used when the persona targets school-major quality evidence; "
            "`tuition_value_relax` is used when the persona targets small tuition-budget "
            "relaxation with value evidence; "
            "`employment_outcome_relax` is used when the persona targets employment, "
            "industry, job, or salary evidence; "
            "`region_tree_relax` is used when the persona targets reviewed region-tree "
            "geo-block or urban-tier evidence; "
            "`multi_axis` pressure tests require two existing opportunity axes to be "
            "found and evidenced in the same dialogue. `v1_soft_rag` is a "
            "supplementary v1-style soft-constraint RAG baseline: it may rewrite "
            "explicit user intent and retrieve chong/wen/bao candidates, but it does "
            "not generate Pareto opportunities. `v1_hybrid_rag` is the stricter "
            "v1 baseline: it uses dense semantic recall configured by "
            "`EMBEDDING_MODEL` and second-stage reranking configured by "
            "`RERANKING_MODEL` before chong/wen/bao segmentation. "
            "The benchmark contribution is "
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
    for axis_flex in (flex.get("axis_flexibilities") or {}).values():
        if not isinstance(axis_flex, dict):
            continue
        for row in axis_flex.get("volunteer_set") or []:
            if isinstance(row, dict) and row.get("school_name"):
                schools.append(str(row["school_name"]))
    return list(dict.fromkeys(schools))


def _combined_target_agent_text(transcript: Transcript) -> str:
    return "\n".join(
        str(turn.content)
        for turn in transcript.turns
        if str(turn.role) == "target_agent"
    )


def _score_evidence_present(text: str) -> bool:
    return (
        "鏈€浣庡垎" in text
        or "min_score" in text
        or "score_margin" in text
        or "鍒?" in text
        or "score=" in text
    )


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


def _has_risk_band_evidence(flex: dict[str, Any], text: str) -> bool:
    if not (
        "最低分" in text
        or "min_score" in text
        or "score_margin" in text
        or "分" in text
    ):
        return False
    hit_levels: set[str] = set()
    for row in flex.get("volunteer_set") or []:
        if not isinstance(row, dict):
            continue
        school = str(row.get("school_name") or "")
        risk_level = str(row.get("risk_level") or "")
        if school and school in text and risk_level and risk_level in text:
            hit_levels.add(risk_level)
    return {"chong", "wen", "bao"}.issubset(hit_levels)


def _has_strength_evidence(flex: dict[str, Any], text: str) -> bool:
    if not ("最低分" in text or "min_score" in text or "分" in text):
        return False
    strength_tokens = (
        "学科实力",
        "专业排名",
        "major_strength_rank",
        "strength_rank",
        "rating",
        "rank=",
    )
    if not any(token in text for token in strength_tokens):
        return False
    for row in flex.get("volunteer_set") or []:
        if not isinstance(row, dict):
            continue
        school = str(row.get("school_name") or "")
        if school and school in text:
            return True
    return False


def _has_major_quality_evidence(flex: dict[str, Any], text: str) -> bool:
    if not ("最低分" in text or "min_score" in text or "分" in text):
        return False
    quality_tokens = (
        "专业质量",
        "专业排名",
        "学科评估",
        "特色",
        "重点",
        "满意度",
        "quality",
        "quality_score",
        "quality_gain",
        "best_major_rank",
        "best_rating",
    )
    if not any(token in text for token in quality_tokens):
        return False
    for row in flex.get("volunteer_set") or []:
        if not isinstance(row, dict):
            continue
        school = str(row.get("school_name") or "")
        if school and school in text:
            return True
    return False


def _has_tuition_value_evidence(flex: dict[str, Any], text: str) -> bool:
    if not (
        "最低分" in text
        or "鏈€浣庡垎" in text
        or "min_score" in text
        or "score_margin" in text
        or "分" in text
        or "鍒?" in text
    ):
        return False
    tuition_tokens = (
        "学费",
        "tuition",
        "tuition_delta",
        "delta=",
        "预算",
        "元",
    )
    if not any(token in text for token in tuition_tokens):
        return False
    for row in flex.get("volunteer_set") or []:
        if not isinstance(row, dict):
            continue
        school = str(row.get("school_name") or "")
        if school and school in text:
            return True
    return False


def _has_employment_outcome_evidence(flex: dict[str, Any], text: str) -> bool:
    if not (
        "最低分" in text
        or "min_score" in text
        or "score_margin" in text
        or "分" in text
    ):
        return False
    employment_tokens = (
        "就业",
        "就业排名",
        "薪资",
        "工资",
        "行业",
        "岗位",
        "employment",
        "outcome_score",
        "outcome_gain",
        "employment_rank",
        "top_industry",
        "salary",
    )
    if not any(token in text for token in employment_tokens):
        return False
    for row in flex.get("volunteer_set") or []:
        if not isinstance(row, dict):
            continue
        school = str(row.get("school_name") or "")
        if school and school in text:
            return True
    return False


def _has_region_tree_evidence(flex: dict[str, Any], text: str) -> bool:
    if not (
        "min_score" in text
        or "score_margin" in text
        or "最低分" in text
        or "分" in text
    ):
        return False
    region_tokens = (
        "region_tree",
        "region_tree_relax",
        "geo_block_relax",
        "urban_tier_relax",
        "region_relax_strategy",
        "source_region",
        "target_region",
        "region=",
        "confidence=",
        "地域树",
        "地域",
        "城市层级",
        "地理",
    )
    if not any(token in text for token in region_tokens):
        return False
    for row in flex.get("volunteer_set") or []:
        if not isinstance(row, dict):
            continue
        school = str(row.get("school_name") or "")
        target_region = str(row.get("target_region_name") or "")
        strategy = str(row.get("region_relax_strategy") or "")
        if not school or school not in text:
            continue
        if (target_region and target_region in text) or (strategy and strategy in text):
            return True
    return False


def _has_major_geo_evidence(flex: dict[str, Any], text: str) -> bool:
    if not _score_evidence_present(text):
        return False
    if "major_geo_relax" in text:
        return True
    for row in flex.get("volunteer_set") or []:
        if not isinstance(row, dict):
            continue
        school = str(row.get("school_name") or "")
        if school and school in text:
            return True
    return False


def _axis_flex(flex: dict[str, Any], axis: str) -> dict[str, Any]:
    axis_flexibilities = flex.get("axis_flexibilities") or {}
    value = axis_flexibilities.get(axis)
    return value if isinstance(value, dict) else {}


def _has_axis_evidence(axis: str, axis_flex: dict[str, Any], text: str) -> bool:
    if axis == "major_geo":
        return _has_major_geo_evidence(axis_flex, text)
    if axis == "risk_band":
        return _score_evidence_present(text) and (
            "risk_band_relax" in text
            or {"chong", "wen", "bao"}.issubset(set(re.findall(r"chong|wen|bao", text)))
        )
    if axis == "major_quality":
        return _score_evidence_present(text) and (
            "major_quality_relax" in text
            or "strength_relax" in text
            or "quality_score" in text
            or "major_strength_rank" in text
        )
    if axis == "tuition_value":
        return _score_evidence_present(text) and (
            "tuition_value_relax" in text
            or ("tuition=" in text and "tuition_delta" in text)
        )
    if axis == "employment_outcome":
        return _score_evidence_present(text) and (
            "employment_outcome_relax" in text
            or "outcome_score" in text
            or "employment_rank" in text
        )
    if axis == "region_tree":
        return _score_evidence_present(text) and (
            "region_tree_relax" in text
            or "geo_block_relax" in text
            or "urban_tier_relax" in text
        )
    return False


def _axis_gain(axis: str, axis_flex: dict[str, Any], text: str) -> int:
    if axis == "major_geo":
        baseline_tier = int(float(axis_flex.get("baseline_tier") or 0))
        accepted_tier = _max_trigger_tier(axis_flex, text)
        return max(1, accepted_tier - baseline_tier)
    if axis == "risk_band":
        return max(1, _risk_portfolio_gain(axis_flex))
    if axis == "major_quality":
        return max(1, _major_quality_gain(axis_flex, text))
    if axis == "tuition_value":
        return max(1, _tuition_value_gain(axis_flex, text))
    if axis == "employment_outcome":
        return max(1, _employment_outcome_gain(axis_flex, text))
    if axis == "region_tree":
        return max(1, _region_tree_gain(axis_flex, text))
    return 0


def _multi_axis_details(flex: dict[str, Any], text: str) -> dict[str, Any]:
    required_axes = [str(axis) for axis in flex.get("relaxation_axes") or []]
    axis_successes: dict[str, bool] = {}
    axis_pareto_gains: dict[str, int] = {}
    for axis in required_axes:
        axis_flex = _axis_flex(flex, axis)
        success = _has_axis_evidence(axis, axis_flex, text)
        axis_successes[axis] = success
        axis_pareto_gains[axis] = _axis_gain(axis, axis_flex, text) if success else 0
    satisfied = bool(required_axes) and all(axis_successes.values())
    return {
        "required_axes": required_axes,
        "axis_successes": axis_successes,
        "axis_pareto_gains": axis_pareto_gains,
        "satisfied": satisfied,
        "pareto_gain": sum(axis_pareto_gains.values()) if satisfied else 0,
    }


def _has_multi_axis_evidence(flex: dict[str, Any], text: str) -> bool:
    return bool(_multi_axis_details(flex, text)["satisfied"])


def _multi_axis_gain(flex: dict[str, Any], text: str) -> int:
    return int(_multi_axis_details(flex, text)["pareto_gain"])


def _strength_rank_gain(flex: dict[str, Any], text: str) -> int:
    try:
        anchor_rank = int(float(flex.get("strength_anchor_rank")))
    except (TypeError, ValueError):
        anchor_rank = 0
    best_rank: int | None = None
    for row in flex.get("volunteer_set") or []:
        if not isinstance(row, dict):
            continue
        school = str(row.get("school_name") or "")
        if not school or school not in text:
            continue
        try:
            candidate_rank = int(float(row.get("major_strength_rank")))
        except (TypeError, ValueError):
            continue
        best_rank = (
            candidate_rank if best_rank is None else min(best_rank, candidate_rank)
        )
    if anchor_rank and best_rank is not None:
        return max(0, anchor_rank - best_rank)
    return 1 if best_rank is not None else 0


def _tuition_value_gain(flex: dict[str, Any], text: str) -> int:
    gains: list[int] = []
    for row in flex.get("volunteer_set") or []:
        if not isinstance(row, dict):
            continue
        school = str(row.get("school_name") or "")
        if not school or school not in text:
            continue
        try:
            gains.append(int(float(row.get("tuition_value_gain"))))
            continue
        except (TypeError, ValueError):
            pass
        try:
            ranking_gain = int(float(row.get("ranking_gain") or 0))
        except (TypeError, ValueError):
            ranking_gain = 0
        gains.append(1 if ranking_gain >= 50 else 0)
    return max(gains) if gains else 0


def _major_quality_gain(flex: dict[str, Any], text: str) -> int:
    gains: list[int] = []
    for row in flex.get("volunteer_set") or []:
        if not isinstance(row, dict):
            continue
        school = str(row.get("school_name") or "")
        if not school or school not in text:
            continue
        try:
            gains.append(int(float(row.get("quality_gain"))))
        except (TypeError, ValueError):
            gains.append(1)
    return max(gains) if gains else 0


def _employment_outcome_gain(flex: dict[str, Any], text: str) -> int:
    gains: list[int] = []
    for row in flex.get("volunteer_set") or []:
        if not isinstance(row, dict):
            continue
        school = str(row.get("school_name") or "")
        if not school or school not in text:
            continue
        try:
            gains.append(int(float(row.get("outcome_gain"))))
        except (TypeError, ValueError):
            gains.append(1)
    return max(gains) if gains else 0


def _region_tree_gain(flex: dict[str, Any], text: str) -> int:
    baseline_tier = 0
    try:
        baseline_tier = int(float(flex.get("baseline_tier") or 0))
    except (TypeError, ValueError):
        baseline_tier = 0
    if not baseline_tier:
        for row in flex.get("volunteer_set") or []:
            if not isinstance(row, dict):
                continue
            try:
                baseline_tier = int(float(row.get("baseline_tier") or 0))
                break
            except (TypeError, ValueError):
                pass
    accepted_tier = _max_trigger_tier(flex, text)
    return max(0, accepted_tier - baseline_tier)


def _risk_portfolio_gain(flex: dict[str, Any]) -> int:
    levels = set(str(item) for item in flex.get("risk_levels") or [])
    if not levels:
        for row in flex.get("volunteer_set") or []:
            if isinstance(row, dict) and row.get("risk_level"):
                levels.add(str(row["risk_level"]))
    return len(levels & {"chong", "wen", "bao"})


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
        case_timeout=args.case_timeout,
        concurrency=args.concurrency,
        case_retries=args.case_retries,
        skip_existing_cases=args.skip_existing_cases,
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
        os.environ["GAOKAOLLM_OFFLINE_DETERMINISTIC"] = "1"
        simulator_llm = DeterministicSimulatorLlm()
        judge_llm = DeterministicJudgeLlm()
    else:
        llm_client = OpenAIChatClient(timeout=args.request_timeout)
        simulator_llm = llm_client.as_chat_model(
            model=config.simulator_model or os.getenv("OPENAI_MODEL") or DEFAULT_MODEL,
            temperature=0,
            max_tokens=256,
        )
        judge_llm = llm_client.as_chat_model(
            model=config.judge_model or os.getenv("OPENAI_MODEL") or DEFAULT_MODEL,
            temperature=0,
            max_tokens=512,
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
        "--case-timeout",
        type=float,
        default=None,
        help="Optional wall-clock timeout in seconds for one persona/target case.",
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=1,
        help="Number of persona cases to run concurrently within each target.",
    )
    parser.add_argument(
        "--case-retries",
        type=int,
        default=0,
        help="Retry count for one persona/target case after transient failures.",
    )
    parser.add_argument(
        "--skip-existing-cases",
        action="store_true",
        help="Preserve completed ok rows in an existing report and rerun only pending or failed cases.",
    )
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
