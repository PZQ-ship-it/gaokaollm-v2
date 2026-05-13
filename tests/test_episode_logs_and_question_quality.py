from pathlib import Path

from app.evaluation.episode_logger import (
    append_episode_log,
    read_episode_logs,
    reset_episode_log,
)
from app.evaluation.log_analyzer import analyze_episode_logs, extract_cost_benefit
from app.evaluation.simulator import extract_cost_dimension
from app.evaluation.transcript_exporter import export_case_study_from_episode_logs
from app.graphs.nodes.negotiator import (
    _fallback_pareto_question,
    _followup_pareto_question,
    select_forced_tradeoff_pair,
    select_max_divergence_pair,
)


def _candidate(
    school: str,
    major: str,
    utility: float,
    features: dict[str, float],
) -> dict[str, object]:
    return {
        "school_name": school,
        "major_name": major,
        "_implicit_utility": utility,
        "_phi_features": features,
    }


def test_episode_logger_writes_jsonl_rows(tmp_path):
    reset_episode_log(tmp_path)
    append_episode_log(
        {
            "profile_id": "robust_major_extreme",
            "ablation_mode": "full",
            "turn": 1,
            "question": "你愿意牺牲/放宽 专业匹配(major) 来换取 学校层次(school) 跃迁吗？",
            "status": "interrupt",
        },
        tmp_path,
    )

    rows = read_episode_logs(tmp_path / "episode_logs.jsonl")

    assert len(rows) == 1
    assert rows[0]["profile_id"] == "robust_major_extreme"
    assert rows[0]["status"] == "interrupt"


def test_log_analyzer_flags_repetition_and_target_hits(tmp_path):
    rows = [
        {
            "profile_id": "robust_major_extreme",
            "ablation_mode": "full",
            "thread_id": "t1",
            "question": "在 A 和 B 之间，你愿意牺牲/放宽 专业匹配(major) 来换取 学校层次(school) 跃迁吗？",
            "simulator_reply": "专业不能偏太远，这个我不接受。",
            "status": "interrupt",
        },
        {
            "profile_id": "robust_major_extreme",
            "ablation_mode": "full",
            "thread_id": "t1",
            "question": "在 A 和 B 之间，你愿意牺牲/放宽 专业匹配(major) 来换取 学校层次(school) 跃迁吗？",
            "simulator_reply": "这个问题没问到我的真正底线，我先保留。",
            "status": "interrupt",
        },
        {
            "profile_id": "robust_school_extreme",
            "ablation_mode": "no_ucb",
            "thread_id": "t2",
            "question": "在 A 和 A 之间，你愿意牺牲/放宽 学校层次(school) 来换取 学校层次(school) 跃迁吗？",
            "simulator_reply": "我有点犹豫。",
            "status": "interrupt",
        },
    ]

    summary = analyze_episode_logs(rows)

    assert summary["modes"]["full"]["repeated_question_rate"] == 0.5
    assert summary["modes"]["full"]["target_dimension_hit_rate"] == 1.0
    assert summary["modes"]["full"]["simulator_ambiguous_reply_rate"] == 0.5
    assert summary["modes"]["no_ucb"]["cost_equals_benefit_rate"] == 1.0
    assert summary["modes"]["no_ucb"]["same_candidate_pair_rate"] == 1.0


def test_simulator_cost_dimension_parser_understands_cn_and_en_labels():
    examples = {
        "你愿意牺牲/放宽 专业匹配(major) 来换取 学校层次(school) 跃迁吗？": "major",
        "你愿意牺牲/放宽 地域距离(geo) 来换取 学校层次(school) 跃迁吗？": "geo",
        "你愿意牺牲/放宽 学费预算(tuition) 来换取 培养质量(quality) 跃迁吗？": "tuition",
        "Would you sacrifice quality for school?": "quality",
        "你愿意牺牲/放宽 学校层次(school) 来换取 专业匹配(major) 跃迁吗？": "school",
    }

    for question, expected in examples.items():
        assert extract_cost_dimension(question) == expected


def test_fallback_question_never_trades_dimension_for_itself():
    option_a = _candidate(
        "A大学",
        "计算机",
        1.0,
        {"school": 0.9, "major": 0.4, "tuition": 1.0, "quality": 0.5, "geo": 0.8},
    )
    option_b = _candidate(
        "B大学",
        "软件工程",
        0.9,
        {"school": 0.5, "major": 0.8, "tuition": 1.0, "quality": 0.5, "geo": 0.8},
    )

    question = _fallback_pareto_question(
        option_a,
        option_b,
        {"school": -0.4, "major": 0.4, "tuition": 0.0, "quality": 0.0, "geo": 0.0},
        forced_cost_dimension="school",
    )
    cost, benefit = extract_cost_benefit(question)

    assert cost == "school"
    assert benefit != "school"
    assert "A大学" in question
    assert "B大学" in question
    assert "如果保留" in question
    assert "如果改看" in question
    assert "牺牲/放宽 学校层次(school)" in question
    assert "换取 专业匹配(major)" in question
    assert "本轮候选不足" not in question
    assert "没有带来明确" not in question
    assert "正向收益跃迁" not in question
    assert "没有清晰收益" not in question


def test_fallback_question_avoids_fake_same_candidate_pair_when_no_option_b():
    option_a = _candidate(
        "A大学",
        "计算机",
        1.0,
        {"school": 0.5, "major": 0.7, "tuition": 1.0, "quality": 0.5, "geo": 0.8},
    )

    question = _fallback_pareto_question(
        option_a,
        {},
        {"school": 0.4, "major": 0.0, "tuition": 0.0, "quality": 0.0, "geo": 0.0},
        forced_cost_dimension="major",
    )

    assert "A大学 和 A大学" not in question
    assert "本轮候选不足以形成取舍" in question
    assert "低信息量探测" in question
    assert "牺牲/放宽 专业匹配(major)" in question
    assert "换取不存在的收益" in question
    assert "正向收益跃迁" not in question
    assert "没有清晰收益" not in question


def test_followup_question_changes_surface_form_after_first_turn():
    first = "在 A 和 B 之间，你愿意牺牲/放宽 专业匹配(major) 来换取 学校层次(school) 跃迁吗？"
    followup = _followup_pareto_question(
        {"school": 0.6, "major": -1.0, "tuition": 0.0, "quality": 0.0, "geo": 0.0},
        "major",
        1,
    )

    assert followup != first
    assert "你刚才拒绝了" in followup
    assert "专业不能偏太远" in followup
    assert "专业不偏离" in followup
    assert extract_cost_benefit(followup)[0] == "major"
    assert "底线确认" not in followup
    assert "没有明确的正向收益跃迁" not in followup
    assert "没有清晰收益" not in followup


def test_followup_question_keeps_fact_tradeoff_when_pair_has_gain():
    option_a = _candidate(
        "A大学",
        "计算机",
        1.0,
        {"school": 0.5, "major": 1.0, "tuition": 1.0, "quality": 0.5, "geo": 0.8},
    )
    option_b = _candidate(
        "C大学",
        "智能科学与技术",
        0.8,
        {"school": 0.9, "major": 0.4, "tuition": 1.0, "quality": 0.5, "geo": 0.8},
    )

    question = _followup_pareto_question(
        {"school": 0.4, "major": -0.6, "tuition": 0.0, "quality": 0.0, "geo": 0.0},
        "major",
        1,
        option_a=option_a,
        option_b=option_b,
    )
    cost, benefit = extract_cost_benefit(question)

    assert "如果保留" in question
    assert "如果改看" in question
    assert "A大学" in question
    assert "C大学" in question
    assert "事实取舍" in question
    assert cost == "major"
    assert benefit == "school"
    assert "正向收益跃迁" not in question
    assert "没有清晰收益" not in question


def test_forced_tradeoff_pair_requires_real_gain_on_another_dimension():
    option_a = _candidate(
        "A大学",
        "计算机",
        1.0,
        {"school": 0.5, "major": 1.0, "tuition": 1.0, "quality": 0.5, "geo": 0.8},
    )
    bad_b = _candidate(
        "B大学",
        "计算机",
        0.9,
        {"school": 0.4, "major": 0.4, "tuition": 1.0, "quality": 0.5, "geo": 0.8},
    )
    good_b = _candidate(
        "C大学",
        "计算机",
        0.8,
        {"school": 0.9, "major": 0.4, "tuition": 1.0, "quality": 0.5, "geo": 0.8},
    )

    _a, selected_b, delta = select_forced_tradeoff_pair(
        [option_a, bad_b, good_b],
        "major",
    )

    assert selected_b["school_name"] == "C大学"
    assert delta["major"] < 0
    assert delta["school"] > 0


def test_forced_tradeoff_pair_returns_no_pair_without_real_gain():
    option_a = _candidate(
        "A大学",
        "计算机",
        1.0,
        {"school": 0.5, "major": 1.0, "tuition": 1.0, "quality": 0.5, "geo": 0.8},
    )
    bad_b = _candidate(
        "B大学",
        "植物保护",
        0.9,
        {"school": 0.4, "major": 0.4, "tuition": 0.9, "quality": 0.5, "geo": 0.8},
    )

    _a, selected_b, delta = select_forced_tradeoff_pair(
        [option_a, bad_b],
        "major",
    )

    assert selected_b == {}
    assert delta == {
        "school": 0.0,
        "major": 0.0,
        "tuition": 0.0,
        "quality": 0.0,
        "geo": 0.0,
    }


def test_select_max_divergence_pair_skips_same_school_major_pair():
    top_features = {
        "school": 0.8,
        "major": 0.8,
        "tuition": 1.0,
        "quality": 0.8,
        "geo": 0.8,
    }
    candidates = [
        _candidate("Top1", "计算机", 1.0, top_features),
        _candidate(
            "Top1",
            "计算机",
            0.98,
            {"school": 0.1, "major": 0.1, "tuition": 0.1, "quality": 0.1, "geo": 0.1},
        ),
        _candidate(
            "Different",
            "计算机",
            0.8,
            {"school": 0.2, "major": 0.2, "tuition": 0.2, "quality": 0.2, "geo": 0.2},
        ),
    ]

    _option_a, option_b, _delta = select_max_divergence_pair(candidates)

    assert option_b["school_name"] == "Different"


def test_case_study_can_export_from_real_episode_log(tmp_path):
    log_path = Path(reset_episode_log(tmp_path))
    append_episode_log(
        {
            "profile_id": "robust_major_extreme",
            "ablation_mode": "full",
            "thread_id": "case-1",
            "turn": 1,
            "question": "你愿意牺牲/放宽 专业匹配(major) 来换取 学校层次(school) 跃迁吗？",
            "simulator_reply": "专业不能偏太远，这个我不接受。",
            "status": "interrupt",
        },
        tmp_path,
    )
    append_episode_log(
        {
            "profile_id": "robust_major_extreme",
            "ablation_mode": "full",
            "thread_id": "case-1",
            "turn": 2,
            "inferred_weights": {"major": 0.6, "school": 0.1},
            "status": "final",
        },
        tmp_path,
    )

    output = tmp_path / "case.md"
    export_case_study_from_episode_logs(log_path, str(output))
    content = output.read_text(encoding="utf-8")

    assert "Agent Pareto Probe" in content
    assert "专业不能偏太远" in content
    assert "Final inferred preference weights" in content
