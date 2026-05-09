"""Pydantic contracts shared by LLM chains."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class MajorLabelOption(BaseModel):
    model_config = ConfigDict(extra="forbid")

    label: str
    label_name: str | None = None


class MajorClassificationInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    major_name: str
    normalized_text: str | None = None
    labels: list[MajorLabelOption]
    allow_null: bool = False
    labels_only: bool = False


class MajorClassificationOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    major_name: str
    selected_label: str | None


class ChainResult(BaseModel):
    model_config = ConfigDict(extra="allow")

    major_name: str
    selected_label: str | None = None
    raw_content: str = ""
    parsed_json: Any = None
    repaired_json: dict[str, Any] = Field(default_factory=dict)
    validated_output: dict[str, Any] | None = None
    schema_valid: bool = False
    label_valid: bool = False
    repair_notes: list[str] = Field(default_factory=list)
    response_mode: str | None = None
    error: str | None = None


class MajorReviewInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    major_name: str
    candidates: list[MajorLabelOption]


class MajorReviewOutputItem(BaseModel):
    model_config = ConfigDict(extra="allow")

    major_name: str
    selected_label: str | None = None
    reason: str = ""


class MajorReviewOutput(BaseModel):
    model_config = ConfigDict(extra="allow")

    items: list[MajorReviewOutputItem]
