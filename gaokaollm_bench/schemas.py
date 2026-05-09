"""Shared Pydantic schemas for the gaokaollm-bench pipeline."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict

from gaokaollm_bench.constrains.enums import ConversationRole


class IcebergPersona(BaseModel):
    """Hidden-preference profile used to drive benchmark conversations."""

    model_config = ConfigDict(extra="forbid")

    case_id: str
    background: dict[str, Any]
    explicit_red_lines: dict[str, Any]
    implicit_flexibilities: dict[str, Any]
    initial_utterance: str
    process_milestones: dict[str, Any]


class ConversationTurn(BaseModel):
    """One observable turn in a benchmark conversation."""

    model_config = ConfigDict(extra="forbid")

    turn_id: int
    role: ConversationRole
    content: str
    internal_state: dict[str, Any]


class Transcript(BaseModel):
    """Complete interaction trace for one benchmark episode."""

    model_config = ConfigDict(extra="forbid")

    persona: IcebergPersona
    turns: list[ConversationTurn]


class EvalReport(BaseModel):
    """Final evaluation report emitted by benchmark judges."""

    model_config = ConfigDict(extra="forbid")

    case_id: str
    hallucination_rate: float
    elicitation_success: bool
    pareto_gain: int
    judge_reasoning: str
