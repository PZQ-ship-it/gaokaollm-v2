from pathlib import Path

import pytest

from app.core.db_pg import close_pool
from app.flows.probers import run_all_probes, run_baseline
from tests._env_checks import require_database


STRICT_CONSTRAINTS = {
    "score": 600,
    "province": "浙江",
    "major": "临床医学",
    "budget": 100000,
}


def test_probers_flow_has_no_llm_dependency():
    source = Path("app/flows/probers.py").read_text(encoding="utf-8")

    assert "langchain" not in source.lower()
    assert "openai" not in source.lower()
    assert "get_chat_model" not in source


@pytest.mark.asyncio
async def test_baseline_returns_only_local_ordinary_clinical_schools():
    require_database()
    baseline = await run_baseline(STRICT_CONSTRAINTS)
    await close_pool()

    assert baseline
    assert len(baseline) <= 3
    assert all(row["school_province"] == "浙江" for row in baseline)
    assert all("临床医学" in row["major_name"] for row in baseline)
    assert all(row["min_score"] <= STRICT_CONSTRAINTS["score"] for row in baseline)
    assert max(row["tier"] for row in baseline) == 2


@pytest.mark.asyncio
async def test_all_probes_find_real_higher_tier_opportunities():
    require_database()
    baseline = await run_baseline(STRICT_CONSTRAINTS)
    opportunities = await run_all_probes(STRICT_CONSTRAINTS)
    await close_pool()

    baseline_tier = max(row["tier"] for row in baseline)
    geo_relax = opportunities["geo_relax"]
    major_relax = opportunities["major_relax"]

    assert geo_relax
    assert all(row["tier"] > baseline_tier for row in geo_relax)
    assert all(
        row["school_province"] != STRICT_CONSTRAINTS["province"] for row in geo_relax
    )
    assert any(row["school_name"] == "石河子大学" for row in geo_relax)

    assert major_relax
    assert all(row["tier"] > baseline_tier for row in major_relax)
    assert all(
        row["school_province"] == STRICT_CONSTRAINTS["province"] for row in major_relax
    )
    assert any(row["school_name"] == "宁波大学" for row in major_relax)
