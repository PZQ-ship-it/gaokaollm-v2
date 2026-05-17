"""Run one unified iceberg case with detailed local JSONL tracing."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from gaokaollm_bench.llm.openai_chat import OpenAIChatClient
from gaokaollm_bench.sandbox.arena import run_episode
from gaokaollm_bench.schemas import IcebergPersona
from gaokaollm_bench.tests.manual.agent_benchmark_run import (
    DEFAULT_MODEL,
    build_target,
    evaluate_transcript,
    transcript_diagnostics,
)
from gaokaollm_bench.utils.trace import trace_event


DEFAULT_PERSONAS = Path(
    "gaokaollm_bench/sample_data/unified_iceberg_personas_1c6c_real_db_180.json"
)
DEFAULT_OUTPUT_ROOT = Path("gaokaollm_bench/outputs/unified_case_debug_trace")
DEFAULT_TRACE_ROOT = Path("app/evaluation/results/traces")


def read_models(path: str | Path) -> list[str]:
    model_path = Path(path)
    if not model_path.exists():
        return []
    models: list[str] = []
    for raw in model_path.read_text(encoding="utf-8-sig").splitlines():
        line = raw.strip().lstrip("\ufeff")
        if line and not line.startswith("#"):
            models.append(line)
    return models


def load_personas(path: str | Path) -> list[IcebergPersona]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(data, dict) and isinstance(data.get("items"), list):
        data = data["items"]
    if not isinstance(data, list):
        raise ValueError("personas file must contain a list or {'items': [...]}")
    return [IcebergPersona.model_validate(item) for item in data]


def select_persona(args: argparse.Namespace) -> IcebergPersona:
    personas = load_personas(args.personas)
    for persona in personas:
        background = persona.background or {}
        if args.case_id and persona.case_id != args.case_id:
            continue
        if (
            args.constraint_count
            and int(background.get("constraint_count") or 0) != args.constraint_count
        ):
            continue
        if (
            args.diagnostic_axis
            and background.get("diagnostic_axis") != args.diagnostic_axis
        ):
            continue
        return persona
    raise ValueError(
        "no persona matched "
        f"case_id={args.case_id!r}, constraint_count={args.constraint_count!r}, "
        f"diagnostic_axis={args.diagnostic_axis!r}"
    )


def safe_name(value: str) -> str:
    safe = value
    for token in ("\\", "/", ":", "*", "?", '"', "<", ">", "|", " "):
        safe = safe.replace(token, "_")
    return safe


async def run_debug_case(args: argparse.Namespace) -> dict[str, Any]:
    load_dotenv()
    persona = select_persona(args)
    models = read_models(args.models_file)
    agent_model = args.model or (
        models[0] if models else os.getenv("OPENAI_MODEL") or DEFAULT_MODEL
    )
    simulator_model = args.simulator_model or os.getenv("SMALL_MODEL") or agent_model
    judge_model = args.judge_model or os.getenv("SMALL_MODEL") or agent_model

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    trace_id = args.trace_id or f"{timestamp}_{persona.case_id}_{args.target}"
    trace_dir = Path(args.trace_dir or DEFAULT_TRACE_ROOT / trace_id)
    output_dir = Path(args.output_dir or DEFAULT_OUTPUT_ROOT / trace_id)
    transcript_dir = output_dir / "transcripts" / args.target
    report_path = output_dir / "report.json"

    os.environ["OPENAI_MODEL"] = agent_model
    os.environ["GAOKAOLLM_TRACE_DIR"] = str(trace_dir)
    os.environ["GAOKAOLLM_TRACE_ID"] = trace_id

    trace_event(
        "DebugRunner",
        "debug_case_start",
        {
            "case_id": persona.case_id,
            "target": args.target,
            "agent_model": agent_model,
            "simulator_model": simulator_model,
            "judge_model": judge_model,
            "background": persona.background,
            "explicit_red_lines": persona.explicit_red_lines,
        },
    )

    llm_client = OpenAIChatClient(timeout=args.request_timeout)
    simulator_llm = llm_client.as_chat_model(
        model=simulator_model,
        temperature=0,
        max_tokens=256,
    )
    judge_llm = llm_client.as_chat_model(
        model=judge_model,
        temperature=0,
        max_tokens=512,
    )
    target = build_target(args.target, case_id=persona.case_id)

    try:
        transcript = await asyncio.wait_for(
            run_episode(
                persona,
                target,
                max_turns=args.max_turns,
                simulator_llm_client=simulator_llm,
                output_dir=transcript_dir,
            ),
            timeout=args.case_timeout,
        )
        diagnostics = transcript_diagnostics(transcript)
        report_payload: dict[str, Any]
        eval_status = "ok"
        try:
            report = await asyncio.wait_for(
                evaluate_transcript(transcript, judge_llm=judge_llm),
                timeout=args.case_timeout,
            )
            report_payload = report.model_dump()
        except Exception as exc:
            eval_status = "failed"
            report_payload = {
                "error_type": type(exc).__name__,
                "error": str(exc),
            }
            trace_event(
                "DebugRunner",
                "evaluation_error",
                {
                    "case_id": persona.case_id,
                    "target": args.target,
                    **report_payload,
                },
            )
        output = {
            "status": "ok" if eval_status == "ok" else "episode_ok_eval_failed",
            "case_id": persona.case_id,
            "target": args.target,
            "agent_model": agent_model,
            "simulator_model": simulator_model,
            "judge_model": judge_model,
            "transcript_path": str(
                transcript_dir / f"transcript_{persona.case_id}.json"
            ),
            "trace_path": str(trace_dir / f"{trace_id}.jsonl"),
            "evaluation_status": eval_status,
            "report": report_payload,
            "diagnostics": diagnostics,
        }
    except Exception as exc:
        trace_event(
            "DebugRunner",
            "debug_case_error",
            {
                "case_id": persona.case_id,
                "target": args.target,
                "error_type": type(exc).__name__,
                "error": str(exc),
            },
        )
        output = {
            "status": "failed",
            "case_id": persona.case_id,
            "target": args.target,
            "trace_path": str(trace_dir / f"{trace_id}.jsonl"),
            "error_type": type(exc).__name__,
            "error": str(exc),
        }

    output_dir.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(output, ensure_ascii=False, indent=2))
    return output


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--personas", default=str(DEFAULT_PERSONAS))
    parser.add_argument("--case-id", default="")
    parser.add_argument("--constraint-count", type=int, default=1)
    parser.add_argument("--diagnostic-axis", default="geo_tier")
    parser.add_argument("--target", default="app_pareto_full")
    parser.add_argument("--models-file", default="models.txt")
    parser.add_argument("--model", default="")
    parser.add_argument("--simulator-model", default="")
    parser.add_argument("--judge-model", default="")
    parser.add_argument("--max-turns", type=int, default=2)
    parser.add_argument("--request-timeout", type=float, default=90.0)
    parser.add_argument("--case-timeout", type=float, default=180.0)
    parser.add_argument("--output-dir", default="")
    parser.add_argument("--trace-dir", default="")
    parser.add_argument("--trace-id", default="")
    return parser


def main() -> None:
    asyncio.run(run_debug_case(build_parser().parse_args()))


if __name__ == "__main__":
    main()
