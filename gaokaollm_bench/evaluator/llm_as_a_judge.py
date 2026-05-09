"""LLM-as-a-judge process evaluation for benchmark transcripts."""

from __future__ import annotations

from typing import Any

from gaokaollm_bench.llm.response_utils import invoke_text_llm, json_text_from_response
from gaokaollm_bench.prompts.evaluator_prompts import build_process_judge_prompt
from gaokaollm_bench.schemas import EvalReport, IcebergPersona, Transcript


async def evaluate_process(
    transcript: Transcript,
    persona: IcebergPersona,
    llm_client: Any,
) -> EvalReport:
    """Ask an LLM judge to score process quality and return a validated report."""

    prompt = build_process_judge_prompt(transcript, persona)
    response = await invoke_text_llm(llm_client, prompt)
    report = EvalReport.model_validate_json(json_text_from_response(response))

    if report.case_id != persona.case_id:
        return report.model_copy(update={"case_id": persona.case_id})
    return report
