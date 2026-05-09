"""Prompt builders for evaluator LLM tasks."""

from __future__ import annotations

from gaokaollm_bench.schemas import IcebergPersona, Transcript


JUDGE_SYSTEM_PROMPT = """
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


def build_process_judge_prompt(transcript: Transcript, persona: IcebergPersona) -> str:
    return (
        f"{JUDGE_SYSTEM_PROMPT}\n\n"
        "Persona:\n"
        f"{persona.model_dump_json(indent=2)}\n\n"
        "Transcript:\n"
        f"{transcript.model_dump_json(indent=2)}"
    )
