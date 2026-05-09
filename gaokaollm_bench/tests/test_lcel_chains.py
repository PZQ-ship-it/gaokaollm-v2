import pytest

from gaokaollm_bench.chains.major_classification import classify_major
from gaokaollm_bench.chains.json_repair import repair_major_payload
from gaokaollm_bench.chains.major_review import review_major_candidates
from gaokaollm_bench.contracts.llm_io import MajorLabelOption


class MockRunnableLlm:
    async def ainvoke(self, prompt):
        text = prompt.to_string() if hasattr(prompt, "to_string") else str(prompt)
        if "candidates" in text:
            return (
                '{"items":[{"major_name":"云计算技术应用",'
                '"selected_label":"data_ai","reason":"matches cloud/data"}]}'
            )
        return '{"major_name":"云计算技术应用","selected_label":"data_ai"}'


@pytest.mark.asyncio
async def test_direct_major_classification_uses_lcel_repair_and_validation():
    result = await classify_major(
        llm_client=MockRunnableLlm(),
        model="mock",
        major_name="云计算技术应用",
        label_options=[
            MajorLabelOption(label="data_ai", label_name="数据智能类"),
            MajorLabelOption(label="medical_tcm", label_name="中医中药临床类"),
        ],
    )

    assert result.selected_label == "data_ai"
    assert result.label_valid is True
    assert result.response_mode == "lcel_json_schema"


@pytest.mark.asyncio
async def test_major_review_chain_restricts_output_to_candidate_labels():
    reviewed = await review_major_candidates(
        llm_client=MockRunnableLlm(),
        model="mock",
        items=[
            {
                "major_name": "云计算技术应用",
                "candidates": [{"label": "data_ai", "label_name": "数据智能类"}],
            }
        ],
    )

    assert reviewed["云计算技术应用"]["selected_label"] == "data_ai"
    assert reviewed["云计算技术应用"]["label_valid"] is True


def test_major_repair_replaces_placeholder_major_name():
    repaired = repair_major_payload(
        {"major_name": ": ", "selected_label": "data_ai"},
        major_name="云计算技术应用",
        label_options=[MajorLabelOption(label="data_ai", label_name="数据智能类")],
    )

    assert repaired["major_name"] == "云计算技术应用"
    assert repaired["schema_valid"] is True
    assert repaired["label_valid"] is True
    assert "replaced_invalid_major_name" in repaired["repair_notes"]
