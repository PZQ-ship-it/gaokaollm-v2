"""Compatibility exports for chain contracts.

New code should import these Pydantic models from
`gaokaollm_bench.contracts.llm_io`.
"""

from gaokaollm_bench.contracts.llm_io import (
    ChainResult,
    MajorClassificationInput,
    MajorClassificationOutput,
    MajorLabelOption,
    MajorReviewInput,
)

__all__ = [
    "ChainResult",
    "MajorClassificationInput",
    "MajorClassificationOutput",
    "MajorLabelOption",
    "MajorReviewInput",
]
