"""LLM-as-a-judge process evaluation for benchmark transcripts."""

from __future__ import annotations

from typing import Any

from gaokaollm_bench.chains.process_judge import evaluate_process_with_chain
from gaokaollm_bench.schemas import EvalReport, IcebergPersona, Transcript


async def evaluate_process(
    transcript: Transcript,
    persona: IcebergPersona,
    llm_client: Any,
) -> EvalReport:
    """Ask an LLM judge to score process quality and return a validated report."""

    try:
        return await evaluate_process_with_chain(
            transcript=transcript,
            persona=persona,
            llm_client=llm_client,
        )
    except Exception as exc:
        return _fallback_eval_report(persona, exc)


def _fallback_eval_report(persona: IcebergPersona, exc: Exception) -> EvalReport:
    """Return a conservative report when the LLM judge emits invalid output."""

    reason = str(exc).splitlines()[0] if str(exc) else type(exc).__name__
    if len(reason) > 240:
        reason = f"{reason[:237]}..."
    return EvalReport(
        case_id=persona.case_id,
        hallucination_rate=0.0,
        elicitation_success=False,
        pareto_gain=0,
        judge_reasoning=(
            "LLM judge fallback: invalid or unavailable judge response; "
            f"{type(exc).__name__}: {reason}"
        ),
    )
