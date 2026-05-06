"""LLM-as-a-judge process evaluation for benchmark transcripts."""

from __future__ import annotations

import json
from typing import Any

from gaokaollm_bench.schemas import EvalReport, IcebergPersona, Transcript


JUDGE_PROMPT = """
You are an evaluation judge for a multi-turn gaokao recommendation benchmark.
Return only valid JSON matching:
{
  "case_id": "string",
  "hallucination_rate": 0.0,
  "elicitation_success": true,
  "pareto_gain": 0,
  "judge_reasoning": "string"
}
Assess whether the target agent elicited hidden flexibility instead of merely
lecturing the user. pareto_gain is the accepted final school tier minus the
original stubborn baseline tier.
""".strip()


def _json_text_from_response(response: Any) -> str:
    if isinstance(response, str):
        return response
    if isinstance(response, dict):
        return json.dumps(response, ensure_ascii=False)

    content = getattr(response, "content", response)
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        for item in content:
            if isinstance(item, dict) and item.get("type") in {"text", "output_text"}:
                return str(item.get("text") or "")

    raise TypeError("llm_client response must be JSON text, a dict, or a message with content")


async def _invoke_llm(llm_client: Any, prompt: str) -> Any:
    if hasattr(llm_client, "ainvoke"):
        return await llm_client.ainvoke(prompt)
    if hasattr(llm_client, "acomplete"):
        return await llm_client.acomplete(prompt)
    if callable(llm_client):
        return await llm_client(prompt)
    raise TypeError("llm_client must provide ainvoke, acomplete, or be async callable")


async def evaluate_process(
    transcript: Transcript,
    persona: IcebergPersona,
    llm_client: Any,
) -> EvalReport:
    """Ask an LLM judge to score process quality and return a validated report."""

    prompt = (
        f"{JUDGE_PROMPT}\n\n"
        "Persona:\n"
        f"{persona.model_dump_json(indent=2)}\n\n"
        "Transcript:\n"
        f"{transcript.model_dump_json(indent=2)}"
    )
    response = await _invoke_llm(llm_client, prompt)
    report = EvalReport.model_validate_json(_json_text_from_response(response))

    if report.case_id != persona.case_id:
        return report.model_copy(update={"case_id": persona.case_id})
    return report

