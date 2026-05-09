"""Prompt builders for IcebergPersona synthesis."""

from __future__ import annotations

import json
from typing import Any


PERSONA_SYNTHESIS_SYSTEM_PROMPT = """
You generate benchmark personas for a gaokao recommendation agent.
Return only valid JSON matching this schema:
{
  "case_id": "string",
  "background": {"score": int, "province": "string", "subjects": list},
  "explicit_red_lines": {"...": "..."},
  "implicit_flexibilities": {"...": "..."},
  "initial_utterance": "string",
  "process_milestones": {"...": "..."}
}
The persona must be stubborn. The explicit red line must block Tier_B.
The implicit flexibility must only unlock when the target agent names Tier_B
and gives a truthful score comparison grounded in the supplied gap data.
Do not invent schools, scores, provinces, or tiers outside the gap data.
""".strip()


def build_persona_synthesis_prompt(gap_data: dict[str, Any]) -> str:
    return (
        f"{PERSONA_SYNTHESIS_SYSTEM_PROMPT}\n\n"
        "Verified Pareto gap data:\n"
        f"{json.dumps(gap_data, ensure_ascii=False, indent=2)}"
    )
