"""Shared Pydantic schemas for the gaokaollm-bench pipeline."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

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


class UnifiedIcebergCase(BaseModel):
    """Canonical case with both process gold labels and weight gold labels."""

    model_config = ConfigDict(extra="forbid")

    case_id: str
    constraint_count: int
    diagnostic_axis: str
    initial_utterance: str
    explicit_red_lines: dict[str, Any]
    hidden_bottom_line: str
    trigger_condition: str
    ground_truth_weights: dict[str, float]
    probe_gold_dims: list[str]
    weight_gold_dims: list[str]
    baseline_candidate_a: dict[str, Any]
    golden_candidate_b: dict[str, Any]
    acceptable_candidates: list[dict[str, Any]] = Field(default_factory=list)
    acceptance_predicate: dict[str, Any] = Field(default_factory=dict)
    acceptable_probe_dims: list[str] = Field(default_factory=list)
    acceptable_probe_keys: list[str] = Field(default_factory=list)
    phi_a: dict[str, float]
    phi_b: dict[str, float]
    delta_phi: dict[str, float]
    expected_msti: float
    volunteer_set: list[dict[str, Any]]
    minimum_required_volunteers: int = 1
    background: dict[str, Any]
    implicit_flexibilities: dict[str, Any]
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
