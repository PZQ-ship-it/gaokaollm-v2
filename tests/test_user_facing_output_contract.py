import json
from pathlib import Path

from app.graphs.nodes.negotiator import (
    _candidate_evidence_text,
    _final_table_row,
    _sanitize_user_output,
    _score_text,
    _school_evidence_comparison,
    _xai_fallback_text,
)


BANNED_USER_TOKENS = (
    "min_score=",
    "min_rank=",
    "tier=",
    "tier 2",
    "tuition_delta=",
    "quality_score=",
    "outcome_score=",
    "utility=",
    "_implicit_utility",
    "semantic_score",
    "_semantic_score",
    "_lexicographic_tier",
    "_lexicographic_epsilon",
    "rank_ratio",
    "c/r",
    "隐性效用",
    "标准化效用",
)


def _sample_candidate() -> dict:
    return {
        "school_name": "江苏大学",
        "school_province": "江苏",
        "school_city": "镇江",
        "major_name": "医学检验技术",
        "min_score": 597,
        "min_rank": 45643,
        "subject_requirement": "物理、化学",
        "tuition": 7480,
        "tuition_delta": 1980,
        "tier": 2,
        "ranking": 113,
        "major_strength_rating": "B+",
        "major_strength_rank": 48,
        "major_similarity_score": 0.82,
        "major_similarity_target": "医学",
        "major_similarity_label": "较贴合",
        "_implicit_utility": 0.84,
        "semantic_score": 0.91,
        "_semantic_score": 0.91,
        "_lexicographic_tier": 84,
    }


def _assert_user_facing(text: str) -> None:
    for token in BANNED_USER_TOKENS:
        assert token not in text


def test_candidate_evidence_text_is_user_facing() -> None:
    text = _candidate_evidence_text(_sample_candidate())

    assert "江苏大学" in text
    assert "医学检验技术" in text
    assert "最低录取分 597" in text
    assert "最低录取位次 45643" in text
    assert "物理、化学" in text
    assert "学费约 7480 元/年" in text
    assert "综合排名参考第 113 名" in text
    assert "重点本科层次" in text
    assert "专业贴合度约 82%" in text
    assert "综合排名前 300 层次" not in text
    _assert_user_facing(text)


def test_score_text_and_final_fallback_do_not_expose_internal_fields() -> None:
    row = _sample_candidate()
    text = "\n".join(
        [
            _score_text(row),
            _xai_fallback_text(
                {"school": 0.4, "major": 0.3, "tuition": 0.1},
                [row],
                {"reach": [row], "match": [], "safety": []},
            ),
        ]
    )

    _assert_user_facing(text)


def test_final_table_row_uses_user_facing_columns() -> None:
    row = _final_table_row(_sample_candidate(), "reach", 1)

    assert row["bucket_label"] == "冲"
    assert row["school"] == "江苏大学"
    assert row["major"] == "医学检验技术"
    assert row["admission"] == "597 分 / 位次 45643"
    assert row["subjects"] == "物理、化学"
    assert row["tuition"] == "约 7480 元/年"
    assert "重点本科层次" in row["school_level"]
    assert "专业贴合度约 82%" in row["reason"]
    assert not {
        "min_score",
        "min_rank",
        "tier",
        "tuition_delta",
        "_implicit_utility",
        "_semantic_score",
        "_lexicographic_tier",
    }.intersection(row)
    _assert_user_facing(json.dumps(row, ensure_ascii=False))


def test_sanitize_user_output_rewrites_legacy_probe_jargon() -> None:
    raw = (
        "江苏大学 min_score=597 min_rank=45643 tier=2 "
        "ranking=113 tuition_delta=1980 utility=0.84 "
        "semantic_score=0.91 _lexicographic_tier=84 major_geo_relax"
    )
    text = _sanitize_user_output(raw)

    assert "最低录取分 597" in text
    assert "最低录取位次 45643" in text
    assert "学校平台/标签：重点本科层次" in text
    assert "综合排名前 300 层次" not in text
    assert "相对预算差额 1980" in text
    assert "专业或地域边界放宽" in text
    _assert_user_facing(text)


def test_sanitize_user_output_extracts_llm_text_field() -> None:
    raw = "{'text': '上海海洋大学是双一流，但专业贴合度下降，需要你判断是否接受。', 'latest_tradeoff_pair': {'debug': true}}"
    text = _sanitize_user_output(raw)

    assert text == "上海海洋大学是双一流，但专业贴合度下降，需要你判断是否接受。"
    assert "latest_tradeoff_pair" not in text


def test_school_evidence_comparison_separates_platform_and_ranking() -> None:
    baseline = {
        "school_name": "温州医科大学",
        "major_name": "生物医学工程",
        "tier": 2,
        "ranking": 191,
    }
    relaxed = {
        "school_name": "上海海洋大学",
        "major_name": "水产类",
        "is_double_first_class": True,
        "tier": 3,
        "ranking": 206,
    }

    comparison = _school_evidence_comparison(baseline, relaxed)
    brief = comparison["brief"]

    assert comparison["platform_relation"] == "b_higher"
    assert comparison["ranking_relation"] == "b_worse"
    assert "学校平台标签更突出" in brief
    assert "综合排名参考不比参照项靠前" in brief
    assert "不能说成“综合排名更好”" in brief


def test_demo_label_prefers_actual_geo_relaxation_over_stale_major_stage() -> None:
    source = Path("app/web/demo.html").read_text(encoding="utf-8")
    geo_branch = "if (geoRelaxed && !majorRelaxed)"
    stale_stage_branch = "if (row?.relaxation_stage_label)"

    assert geo_branch in source
    assert 'label: "地域范围放宽"' in source
    assert source.index(geo_branch) < source.index(stale_stage_branch)


def test_demo_displays_rank_window_and_risk_relaxation_boundary() -> None:
    source = Path("app/web/demo.html").read_text(encoding="utf-8")

    assert 'id="risk-window"' in source
    assert "const riskRankRatios" in source
    assert "initialMin: 0.85" in source
    assert "relaxedMin: 0.75" in source
    assert "max: 1.40" in source
    assert "function acceptedRiskRelaxed(data)" in source
    assert 'dimension === "risk"' in source
    assert "当前预估位次" in source
    assert "上探边界" in source
    assert "保底边界" in source
    assert "initialLower" in source
    assert '["冲", lowerRatio, riskRankRatios.reachUpper]' in source
    assert "ratio >= riskRankRatios.initialMin" in source
    assert source.count("renderRiskWindow(data);") >= 2


def test_demo_gates_candidates_until_confirmed_question() -> None:
    source = Path("app/web/demo.html").read_text(encoding="utf-8")

    assert "function hasConfirmedQuestion(data)" in source
    assert "if (!hasConfirmedQuestion(data))" in source
    assert "候选正在核验，正式取舍问题生成后展示。" in source
    render_cards_start = source.index("function renderCards(data)")
    assert source.index(
        "if (!hasConfirmedQuestion(data))",
        render_cards_start,
    ) < source.index("const baseline = dedupeRows", render_cards_start)
