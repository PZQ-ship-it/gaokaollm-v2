from decimal import Decimal

from gaokaollm_bench.data_gen.major_quality_backfill import (
    clean_major_name,
    discipline_score,
    featured_major_score,
    key_major_score,
    major_rank_score,
    quality_tier,
    rating_score,
    satisfaction_signal_score,
)


def test_clean_major_name_removes_major_suffix():
    assert clean_major_name("阿拉伯语专业") == "阿拉伯语"
    assert clean_major_name("软件工程（专业）") == "软件工程"
    assert clean_major_name("计算机科学与技术") == "计算机科学与技术"
    assert clean_major_name(None) is None


def test_quality_scores_prioritize_rank_and_evaluation():
    assert rating_score("A+") == 100
    assert rating_score(" A- ") == 90
    assert major_rank_score(1, "A+") == 100
    assert major_rank_score(20, "B+") == 86
    assert discipline_score("A", 0.85) == 80.75


def test_auxiliary_quality_scores_and_tiers():
    assert key_major_score("国家级") == 88
    assert featured_major_score({"国家特色": "是"}) == 84
    assert satisfaction_signal_score(Decimal("4.8")) == 77.0
    assert quality_tier(95) == "A"
    assert quality_tier(83) == "B"
    assert quality_tier(72) == "C"
    assert quality_tier(60) == "D"
