"""Common enum-like string values used across the benchmark."""

from __future__ import annotations

from enum import Enum


class StrEnum(str, Enum):
    """Python-version-stable string enum base."""

    def __str__(self) -> str:
        return self.value


class ConversationRole(StrEnum):
    USER = "user"
    TARGET_AGENT = "target_agent"


class ChatMessageRole(StrEnum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"


class ProbeModelKind(StrEnum):
    LINEAR = "linear"
    MLP = "mlp"
    DEEP_MLP = "deep_mlp"
    RESIDUAL_MLP = "residual_mlp"
    FR_KAN = "fr_kan"


class ProbeClassWeight(StrEnum):
    NONE = "none"
    BALANCED = "balanced"
    SQRT_BALANCED = "sqrt_balanced"


class ProbeSelectionMetric(StrEnum):
    VAL_ACCURACY = "val_accuracy"
    VAL_MACRO_F1 = "val_macro_f1"
    VAL_LOSS = "val_loss"
    TRAIN_ACCURACY = "train_accuracy"
    TRAIN_LOSS = "train_loss"


class ProbeActivation(StrEnum):
    RELU = "relu"
    GELU = "gelu"


class PersonaRelaxation(StrEnum):
    PROVINCE = "province"
    MAJOR_CLINICAL_TO_MEDTECH = "major_clinical_to_medtech"
    MAJOR_ANY = "major_any"
    MAJOR_HIERARCHY = "major_hierarchy"


class MajorRelaxScope(StrEnum):
    PROVINCE = "province"
    NATIONAL = "national"


class PersonaShape(StrEnum):
    VOLUNTEER_SET = "volunteer_set"
    SINGLE_GAP = "single_gap"


class DedupKeyMode(StrEnum):
    SCHOOL_PAIR = "school_pair"
    SCHOOL_MAJOR = "school_major"
    SCORE = "score"


class PersonaSynthesisMode(StrEnum):
    TEMPLATE = "template"
    LLM = "llm"


def values(enum_cls: type[StrEnum]) -> list[str]:
    return [item.value for item in enum_cls]
