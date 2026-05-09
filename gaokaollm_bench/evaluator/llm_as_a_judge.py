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

    return await evaluate_process_with_chain(
        transcript=transcript,
        persona=persona,
        llm_client=llm_client,
    )
