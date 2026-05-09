"""Prompt builders for major classification and review tasks."""

from __future__ import annotations

import json
from typing import Any

from gaokaollm_bench.constrains.enums import ChatMessageRole
from gaokaollm_bench.contracts.llm_io import MajorClassificationInput


def build_major_classification_messages(
    input_data: MajorClassificationInput,
) -> list[dict[str, str]]:
    labels = (
        [{"label": item.label} for item in input_data.labels]
        if input_data.labels_only
        else [item.model_dump(exclude_none=True) for item in input_data.labels]
    )
    system = (
        "你是高考专业分类器。"
        "你必须只从候选标签中选择一个最接近的 selected_label。"
        "selected_label 必须严格使用候选中的 label 字段，不能输出 label_name、解释或其他文本。"
        + (
            "如果完全无法判断，可以返回 null。"
            if input_data.allow_null
            else "不要返回 null。"
        )
    )
    user = json.dumps(
        {
            "item": {
                "major_name": input_data.major_name,
                "normalized_text": input_data.normalized_text,
            },
            "labels": labels,
        },
        ensure_ascii=False,
    )
    return [
        {"role": ChatMessageRole.SYSTEM.value, "content": system},
        {"role": ChatMessageRole.USER.value, "content": user},
    ]


def build_major_review_messages(items: list[dict[str, Any]]) -> list[dict[str, str]]:
    system = (
        "你是高考专业复核员。"
        "你只能从每个 item 的 candidates 中选择一个最合适的 selected_label。"
        "如果候选都不合适，可以返回 null。"
        "不要输出概率，不要扩展候选范围。"
        '输出 JSON: {"items":[{"major_name":...,"selected_label":...,"reason":...}]}'
    )
    user = json.dumps({"items": items}, ensure_ascii=False, indent=2)
    return [
        {"role": ChatMessageRole.SYSTEM.value, "content": system},
        {"role": ChatMessageRole.USER.value, "content": user},
    ]
