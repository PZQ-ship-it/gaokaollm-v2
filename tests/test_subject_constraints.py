import pytest

from app.core.db_pg import close_pool
from app.flows.probers import run_baseline
from app.schemas.models import UserConstraints


SCIENCE_CONSTRAINTS = {
    "score": 600,
    "province": "浙江",
    "major": "临床医学",
    "budget": 100000,
    "selected_subjects": ["物理", "化学", "生物"],
}

LIBERAL_CONSTRAINTS = {
    **SCIENCE_CONSTRAINTS,
    "selected_subjects": ["政治", "历史", "地理"],
}


def _subject_requirement_is_satisfied(row: dict, selected_subjects: set[str]) -> bool:
    requirement_type = row["requirement_type"]
    required_subjects = set(row["requirement_normalized"] or [])

    if requirement_type == "none" or not required_subjects:
        return True
    if requirement_type == "all_required":
        return required_subjects.issubset(selected_subjects)
    if requirement_type == "any_required":
        return bool(required_subjects & selected_subjects)
    return False


def test_user_constraints_accept_selected_subjects():
    constraints = UserConstraints(
        score=600,
        province="浙江",
        major="临床医学",
        budget=100000,
        selected_subjects=["物理", "化学", "生物"],
    )

    assert constraints.selected_subjects == ["物理", "化学", "生物"]


@pytest.mark.asyncio
async def test_baseline_filters_by_satisfied_subject_requirements():
    baseline = await run_baseline(SCIENCE_CONSTRAINTS)
    await close_pool()

    selected_subjects = set(SCIENCE_CONSTRAINTS["selected_subjects"])
    assert baseline
    assert all(_subject_requirement_is_satisfied(row, selected_subjects) for row in baseline)


@pytest.mark.asyncio
async def test_baseline_filters_out_unsatisfied_medical_requirements():
    unfiltered = await run_baseline({key: value for key, value in SCIENCE_CONSTRAINTS.items() if key != "selected_subjects"})
    baseline = await run_baseline(LIBERAL_CONSTRAINTS)
    await close_pool()

    forbidden = {"物理", "化学", "生物"}
    assert unfiltered
    assert all(not (set(row["requirement_normalized"] or []) & forbidden) for row in baseline)
