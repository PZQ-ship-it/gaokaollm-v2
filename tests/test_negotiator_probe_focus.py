from app.graphs.nodes.negotiator import (
    _anchor_candidate_rows,
    _available_cost_dimensions_for_state,
    _cost_dimensions_for_probe,
    _final_recommendation_table_matrix,
    _new_challenger_rows,
    select_constrained_tradeoff_pair,
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
        "_phi_features": {"risk": 0.5, **features},
    }


def test_constrained_tradeoff_keeps_school_as_benefit_not_cost():
    baseline = _candidate(
        "Local Medical",
        "Clinical",
        1.0,
        {"school": 0.45, "major": 1.0, "tuition": 1.0, "quality": 0.5, "geo": 1.0},
    )
    challenger = _candidate(
        "National Better",
        "Public Health",
        1.1,
        {"school": 0.8, "major": 0.65, "tuition": 1.0, "quality": 0.6, "geo": 0.7},
    )

    option_a, option_b, delta, cost, benefit = select_constrained_tradeoff_pair(
        [baseline, challenger],
        cost_dimensions=("geo", "major"),
        benefit_dimensions=("school", "quality"),
        challenger_rows=[challenger],
        anchor_rows=[baseline],
    )

    assert option_a["school_name"] == "Local Medical"
    assert option_b["school_name"] == "National Better"
    assert cost in {"geo", "major"}
    assert cost not in {"school", "quality"}
    assert benefit in {"school", "quality"}
    assert delta[cost] < 0
    assert delta[benefit] > 0


def test_constrained_tradeoff_prioritizes_current_probe_challenger():
    baseline = _candidate(
        "Current Accepted",
        "Medical Test",
        1.0,
        {"school": 0.5, "major": 1.0, "tuition": 0.65, "quality": 0.5, "geo": 1.0},
    )
    stale_budget = _candidate(
        "Budget Only",
        "Medical Test",
        1.4,
        {"school": 0.55, "major": 1.0, "tuition": 0.5, "quality": 0.5, "geo": 1.0},
    )
    probe_challenger = _candidate(
        "Probe Direction",
        "Health Management",
        0.9,
        {"school": 0.75, "major": 0.65, "tuition": 1.0, "quality": 0.6, "geo": 0.7},
    )

    _option_a, option_b, _delta, cost, _benefit = select_constrained_tradeoff_pair(
        [baseline, stale_budget, probe_challenger],
        cost_dimensions=("geo", "major"),
        benefit_dimensions=("school", "quality"),
        challenger_rows=[probe_challenger],
        anchor_rows=[baseline, stale_budget],
    )

    assert option_b["school_name"] == "Probe Direction"
    assert cost in {"geo", "major"}


def test_constrained_tradeoff_prefers_minimal_pair_when_target_gain_match():
    baseline = _candidate(
        "Current",
        "临床医学",
        1.0,
        {"school": 0.5, "major": 0.9, "tuition": 1.0, "quality": 0.5, "geo": 1.0},
    )
    noisy = _candidate(
        "Noisy Better",
        "土木工程",
        1.1,
        {"school": 0.8, "major": 0.1, "tuition": 0.6, "quality": 0.8, "geo": 0.2},
    )
    clean = _candidate(
        "Clean Better",
        "临床医学",
        1.0,
        {"school": 0.8, "major": 0.85, "tuition": 0.6, "quality": 0.52, "geo": 0.95},
    )
    baseline["tuition"] = 5500
    noisy["tuition"] = 7000
    clean["tuition"] = 7000

    _option_a, option_b, delta, cost, benefit = select_constrained_tradeoff_pair(
        [baseline, noisy, clean],
        cost_dimensions=("tuition",),
        benefit_dimensions=("school",),
        challenger_rows=[noisy, clean],
        anchor_rows=[baseline],
    )

    assert option_b["school_name"] == "Clean Better"
    assert cost == "tuition"
    assert benefit == "school"
    assert abs(delta["major"]) < 0.1


def test_constrained_tradeoff_skips_candidate_after_hesitate():
    baseline = _candidate(
        "西藏大学",
        "临床医学",
        1.0,
        {"school": 0.5, "major": 1.0, "tuition": 1.0, "quality": 0.5, "geo": 0.7},
    )
    repeated_challenger = _candidate(
        "宁波大学",
        "土木工程",
        1.4,
        {"school": 0.85, "major": 0.2, "tuition": 1.0, "quality": 0.8, "geo": 1.0},
    )
    fresh_challenger = _candidate(
        "石河子大学",
        "口腔医学",
        0.9,
        {"school": 0.7, "major": 0.8, "tuition": 1.0, "quality": 0.65, "geo": 0.4},
    )

    _option_a, option_b, _delta, cost, _benefit = select_constrained_tradeoff_pair(
        [baseline, repeated_challenger, fresh_challenger],
        cost_dimensions=("geo", "major"),
        benefit_dimensions=("school", "quality"),
        challenger_rows=[repeated_challenger, fresh_challenger],
        anchor_rows=[baseline],
        tabu_candidate_signatures={"宁波大学|土木工程"},
    )

    assert option_b["school_name"] == "石河子大学"
    assert cost in {"geo", "major"}


def test_constrained_tradeoff_skips_reversed_probed_pair():
    baseline = _candidate(
        "A大学",
        "临床医学",
        1.0,
        {"school": 0.5, "major": 1.0, "tuition": 1.0, "quality": 0.5, "geo": 0.8},
    )
    old_pair_challenger = _candidate(
        "B大学",
        "预防医学",
        1.1,
        {"school": 0.8, "major": 0.6, "tuition": 1.0, "quality": 0.6, "geo": 0.7},
    )
    fresh_challenger = _candidate(
        "C大学",
        "口腔医学",
        0.9,
        {"school": 0.7, "major": 0.7, "tuition": 1.0, "quality": 0.65, "geo": 0.6},
    )

    _option_a, option_b, _delta, _cost, _benefit = select_constrained_tradeoff_pair(
        [baseline, old_pair_challenger, fresh_challenger],
        cost_dimensions=("geo", "major"),
        benefit_dimensions=("school", "quality"),
        challenger_rows=[old_pair_challenger, fresh_challenger],
        anchor_rows=[baseline],
        tabu_pair_signatures={("A大学|临床医学", "B大学|预防医学")},
    )

    assert option_b["school_name"] == "C大学"


def test_blocked_dimension_filters_joint_probe_costs():
    costs = _available_cost_dimensions_for_state(
        {"factual_blocked_dimensions": ["major"]},
        "major_geo_relax",
        "school",
    )

    assert costs == ("geo",)


def test_joint_probe_cost_dimension_follows_ucb_target_dimension():
    assert _cost_dimensions_for_probe("major_geo_relax", "geo") == ("geo",)
    assert _cost_dimensions_for_probe("major_geo_relax", "major") == ("major",)
    assert _cost_dimensions_for_probe("major_geo_relax", "tuition") == (
        "geo",
        "major",
    )


def test_anchor_rows_match_visible_current_candidates_not_hidden_baseline():
    visible = _candidate(
        "杭州师范大学",
        "预防医学",
        0.8,
        {"school": 0.65, "major": 0.9, "tuition": 1.0, "quality": 0.7, "geo": 1.0},
    )
    hidden = _candidate(
        "江苏农牧科技职业学院",
        "动物医学",
        1.8,
        {"school": 0.2, "major": 0.75, "tuition": 1.0, "quality": 0.2, "geo": 0.7},
    )

    anchors = _anchor_candidate_rows(
        {
            "baseline_results": [hidden],
            "pareto_opportunities": {
                "global_baseline": {
                    "reach": [visible],
                    "match": [],
                    "safety": [],
                    "hidden": [hidden],
                }
            },
        }
    )

    assert [row["school_name"] for row in anchors] == ["杭州师范大学"]


def test_focused_rows_are_not_used_as_anchor_when_current_candidates_empty():
    hidden_probe = _candidate(
        "河南大学",
        "会计学",
        1.4,
        {"school": 0.8, "major": 0.2, "tuition": 1.0, "quality": 0.7, "geo": 0.2},
    )
    anchors = _anchor_candidate_rows(
        {
            "baseline_results": [],
            "pareto_opportunities": {
                "major_geo_relax": [hidden_probe],
            },
        }
    )
    challengers = _new_challenger_rows([hidden_probe], anchors)

    assert anchors == []
    assert challengers == [hidden_probe]


def test_final_table_uses_aggressive_slots_after_risk_acceptance():
    def row(bucket: str, index: int) -> dict[str, object]:
        return _candidate(
            f"{bucket}-{index}",
            "临床医学",
            1.0 - index * 0.01,
            {"school": 0.7, "major": 1.0, "tuition": 1.0, "quality": 0.7, "geo": 1.0},
        )

    matrix = _final_recommendation_table_matrix(
        {
            "accepted_relaxations": [{"dimension": "risk_band_relax"}],
            "pareto_opportunities": {
                "global_baseline": {
                    "reach": [row("reach", index) for index in range(50)],
                    "match": [row("match", index) for index in range(30)],
                    "safety": [row("safety", index) for index in range(30)],
                }
            },
        }
    )

    assert len(matrix["reach"]) == 45
    assert len(matrix["match"]) == 18
    assert len(matrix["safety"]) == 17
