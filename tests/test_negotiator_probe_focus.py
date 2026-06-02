from app.graphs.nodes.negotiator import (
    _anchor_candidate_rows,
    _available_cost_dimensions_for_state,
    _cost_dimensions_for_probe,
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
