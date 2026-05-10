from gaokaollm_bench.data_gen.employment_outcome_backfill import (
    evidence_sources_for_row,
    normalize_employment_rows,
    outcome_score_from_rank,
    parse_employment_rank,
)


def test_parse_employment_rank_extracts_numeric_rank():
    assert parse_employment_rank("第12名") == 12
    assert parse_employment_rank("排名 3 / 300") == 3
    assert parse_employment_rank("") is None
    assert parse_employment_rank(None) is None


def test_outcome_score_uses_rank_and_evidence_bonus():
    assert outcome_score_from_rank(1, evidence_count=3) == 100.0
    assert outcome_score_from_rank(40, evidence_count=2) > outcome_score_from_rank(80)
    assert outcome_score_from_rank(None, evidence_count=4) > outcome_score_from_rank(
        None
    )


def test_normalize_employment_rows_keeps_best_profile_per_major():
    rows = [
        {
            "major_id": 1,
            "major_name": "软件工程",
            "employment_rank": "第45名",
            "top_city": "杭州",
            "top_industry": "软件服务",
            "industry_distribution": {"items": ["软件服务"]},
            "salary_distribution": {},
            "raw": {"source": "low"},
        },
        {
            "major_id": 1,
            "major_name": "软件工程",
            "employment_rank": "第8名",
            "top_city": "深圳",
            "top_industry": "互联网",
            "industry_distribution": {"items": ["互联网"]},
            "salary_distribution": {"items": ["10k-15k"]},
            "raw": {"source": "high"},
        },
    ]

    profiles = normalize_employment_rows(rows)

    assert len(profiles) == 1
    profile = profiles[0]
    assert profile.major_id == 1
    assert profile.employment_rank == 8
    assert profile.top_industry == "互联网"
    assert profile.outcome_score >= 90
    assert "salary_distribution" in profile.evidence_sources


def test_evidence_sources_handles_empty_json_safely():
    row = {
        "employment_rank": None,
        "industry_distribution": "",
        "city_distribution": {},
        "job_distribution": None,
        "salary_distribution": {"items": ["8k-10k"]},
    }

    assert evidence_sources_for_row(row) == ["salary_distribution"]
