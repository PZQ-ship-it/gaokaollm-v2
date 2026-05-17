"""Deterministic candidate-set oracle for iceberg benchmark cases."""

from __future__ import annotations

import re
from typing import Any

from gaokaollm_bench.constrains.enums import ConversationRole
from gaokaollm_bench.schemas import EvalReport, IcebergPersona, Transcript


PREFERENCE_DIMS = ("school", "major", "tuition", "quality", "geo")

AXIS_ORACLE_RULES: dict[str, dict[str, Any]] = {
    "geo_tier": {
        "acceptable_probe_dims": ["geo", "school"],
        "acceptable_probe_keys": ["geo_relax", "region_tree_relax", "major_geo_relax"],
        "required_evidence": ["school_score"],
        "gain_fields": ["tier_delta", "ranking_gain"],
    },
    "major_tier": {
        "acceptable_probe_dims": ["major", "school", "quality"],
        "acceptable_probe_keys": ["major_geo_relax", "major_relax", "strength_relax"],
        "required_evidence": ["school_score"],
        "gain_fields": ["tier_delta", "quality_gain", "ranking_gain"],
    },
    "risk_tier": {
        "acceptable_probe_dims": ["school"],
        "acceptable_probe_keys": ["risk_band_relax"],
        "required_evidence": ["school_score", "risk"],
        "gain_fields": ["tier_delta", "ranking_gain"],
    },
    "tuition_value": {
        "acceptable_probe_dims": ["tuition", "school", "quality"],
        "acceptable_probe_keys": ["tuition_value_relax"],
        "required_evidence": ["school_score", "tuition"],
        "gain_fields": ["tier_delta", "quality_gain", "ranking_gain"],
    },
    "major_quality": {
        "acceptable_probe_dims": ["quality", "major"],
        "acceptable_probe_keys": ["major_quality_relax", "strength_relax"],
        "required_evidence": ["school_score", "quality"],
        "gain_fields": ["quality_gain", "tier_delta", "ranking_gain"],
    },
    "employment_outcome": {
        "acceptable_probe_dims": ["quality"],
        "acceptable_probe_keys": ["employment_outcome_relax"],
        "required_evidence": ["school_score", "employment"],
        "gain_fields": ["outcome_gain", "tier_delta", "ranking_gain"],
    },
}

SCORE_EVIDENCE_RE = re.compile(
    r"(最低分|min_score|score_margin|分数|位次|min_rank).{0,24}\d{3}"
    r"|\d{3}.{0,24}(最低分|min_score|score_margin|分数|位次|min_rank)"
)
TUITION_EVIDENCE_RE = re.compile(r"学费|tuition|预算|费用|tuition_delta|超预算")
QUALITY_EVIDENCE_RE = re.compile(
    r"专业实力|专业排名|学科评估|特色|重点|满意度|quality|quality_score|quality_gain|"
    r"major_strength_rank|strength_rank|best_major_rank|best_rating"
)
EMPLOYMENT_EVIDENCE_RE = re.compile(
    r"就业|薪资|工资|行业|岗位|employment|outcome_score|outcome_gain|"
    r"employment_rank|top_industry|salary"
)
RISK_EVIDENCE_RE = re.compile(
    r"风险|冲|稳|保|贴线|位次|score_margin|rank_gap|risk_level|chong|wen|bao"
)


def axis_oracle_rule(axis: str) -> dict[str, Any]:
    return dict(AXIS_ORACLE_RULES.get(axis, {}))


def default_acceptable_probe_dims(
    axis: str, probe_gold_dims: list[str] | None = None
) -> list[str]:
    rule = axis_oracle_rule(axis)
    dims = [str(item) for item in rule.get("acceptable_probe_dims") or []]
    if dims:
        return list(dict.fromkeys(dim for dim in dims if dim in PREFERENCE_DIMS))
    return [dim for dim in (probe_gold_dims or []) if dim in PREFERENCE_DIMS]


def default_acceptable_probe_keys(axis: str) -> list[str]:
    rule = axis_oracle_rule(axis)
    return [str(item) for item in rule.get("acceptable_probe_keys") or []]


def acceptable_rows_from_flex(flex: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for key in ("acceptable_candidates", "volunteer_set"):
        for row in flex.get(key) or []:
            if isinstance(row, dict):
                rows.append(dict(row))
    golden = flex.get("golden_candidate_b")
    if isinstance(golden, dict):
        rows.append(dict(golden))
    for axis_flex in (flex.get("axis_flexibilities") or {}).values():
        if not isinstance(axis_flex, dict):
            continue
        for key in ("acceptable_candidates", "volunteer_set"):
            for row in axis_flex.get(key) or []:
                if isinstance(row, dict):
                    rows.append(dict(row))
    return _dedupe_candidates(rows)


def protected_candidate_tokens(flex: dict[str, Any]) -> dict[str, list[str]]:
    schools: list[str] = []
    majors: list[str] = []
    scores: list[str] = []
    for row in acceptable_rows_from_flex(flex):
        school = str(row.get("school_name") or "")
        major = str(row.get("major_name") or "")
        score = row.get("min_score")
        if school:
            schools.append(school)
        if major:
            majors.append(major)
        if score not in (None, ""):
            scores.append(str(score))
    protected = [*schools, *scores]
    return {
        "schools": list(dict.fromkeys(schools)),
        "majors": list(dict.fromkeys(majors)),
        "scores": list(dict.fromkeys(scores)),
        "protected_tokens": list(dict.fromkeys(token for token in protected if token)),
    }


def agent_supplied_candidate_evidence(
    agent_reply: str,
    hidden: dict[str, list[str]],
) -> bool:
    text = str(agent_reply or "")
    if not text:
        return False
    has_school = any(school and school in text for school in hidden.get("schools", []))
    has_score = any(
        score and re.search(rf"(?<!\d){re.escape(score)}(?!\d)", text)
        for score in hidden.get("scores", [])
    )
    has_score_word = any(
        token in text for token in ("最低分", "分数", "位次", "min_score", "score")
    )
    return bool(has_school and (has_score or has_score_word))


def transcript_candidate_diagnostics(transcript: Transcript) -> dict[str, Any]:
    rows = acceptable_rows_from_flex(transcript.persona.implicit_flexibilities or {})
    target_turns = [
        turn for turn in transcript.turns if str(turn.role) == "target_agent"
    ]
    target_count = len(target_turns)
    previous_user = ""
    first_role = ""
    first_turn: int | str = ""
    first_school = ""
    target_evidence_count = 0
    echo_count = 0
    hit_ids: list[str] = []
    exact_golden_hit = False
    golden = _golden_candidate(transcript.persona)
    for turn in transcript.turns:
        role = str(turn.role)
        content = str(turn.content or "")
        if not first_role:
            first = _first_candidate_mentioned(content, rows)
            if first is not None:
                first_role = role
                first_turn = turn.turn_id
                first_school = str(first.get("school_name") or "")

        if role == "user":
            previous_user = _normalize(content)
            continue
        if role != "target_agent":
            continue

        normalized = _normalize(content)
        turn_is_echo = bool(normalized and normalized == previous_user)
        matched = matched_acceptable_candidates(
            content,
            transcript.persona.implicit_flexibilities or {},
        )
        if matched:
            target_evidence_count += 1
            hit_ids.extend(_candidate_id(row) for row in matched)
            if turn_is_echo:
                echo_count += 1
        if golden and _candidate_matches_text(golden, content):
            exact_golden_hit = True
    hit_ids = [item for item in dict.fromkeys(hit_ids) if item]
    return {
        "acceptable_candidate_count": len(rows),
        "acceptable_candidate_hit": bool(hit_ids),
        "acceptable_candidate_hit_ids": ",".join(hit_ids),
        "acceptable_first_mention_role": first_role,
        "acceptable_first_mention_turn": first_turn,
        "acceptable_first_mention_school": first_school,
        "target_supplied_acceptable_evidence": target_evidence_count > 0,
        "target_acceptable_evidence_count": target_evidence_count,
        "acceptable_echo_target_count": echo_count,
        "exact_golden_hit": exact_golden_hit,
        "target_turn_count_for_oracle": target_count,
    }


def evaluate_candidate_set_oracle(
    report: EvalReport, transcript: Transcript
) -> EvalReport:
    flex = transcript.persona.implicit_flexibilities or {}
    if not _has_candidate_set_oracle(flex):
        return apply_candidate_leakage_veto(report, transcript)

    diagnostics = transcript_candidate_diagnostics(transcript)
    success = bool(diagnostics["target_supplied_acceptable_evidence"])
    if diagnostics["acceptable_first_mention_role"] == "user":
        success = False
    if diagnostics["acceptable_echo_target_count"]:
        success = False
    gain = (
        _candidate_set_gain(flex, _combined_target_text(transcript)) if success else 0
    )
    reason = (
        f"{report.judge_reasoning} | deterministic candidate-set oracle: "
        f"success={success}, hit_ids={diagnostics['acceptable_candidate_hit_ids'] or 'none'}."
    )
    return report.model_copy(
        update={
            "elicitation_success": success,
            "pareto_gain": gain,
            "judge_reasoning": reason,
        }
    )


def apply_candidate_leakage_veto(
    report: EvalReport, transcript: Transcript
) -> EvalReport:
    if not report.elicitation_success:
        return report
    diagnostics = transcript_candidate_diagnostics(transcript)
    if diagnostics["acceptable_first_mention_role"] == "user":
        return report.model_copy(
            update={
                "elicitation_success": False,
                "pareto_gain": 0,
                "judge_reasoning": (
                    f"{report.judge_reasoning} | deterministic veto: acceptable "
                    "candidate first appeared in a user turn."
                ),
            }
        )
    if diagnostics["acceptable_echo_target_count"]:
        return report.model_copy(
            update={
                "elicitation_success": False,
                "pareto_gain": 0,
                "judge_reasoning": (
                    f"{report.judge_reasoning} | deterministic veto: target "
                    "only echoed acceptable candidate evidence from the user."
                ),
            }
        )
    if not diagnostics["target_supplied_acceptable_evidence"]:
        return report.model_copy(
            update={
                "elicitation_success": False,
                "pareto_gain": 0,
                "judge_reasoning": (
                    f"{report.judge_reasoning} | deterministic veto: no target "
                    "turn supplied acceptable candidate with score evidence."
                ),
            }
        )
    return report


def matched_acceptable_candidates(
    text: str, flex: dict[str, Any]
) -> list[dict[str, Any]]:
    predicate = flex.get("acceptance_predicate")
    if not isinstance(predicate, dict):
        predicate = {}
    required = [str(item) for item in predicate.get("required_evidence") or []]
    if not required:
        axis = str(flex.get("diagnostic_axis") or "")
        required = [
            str(item)
            for item in axis_oracle_rule(axis).get(
                "required_evidence", ["school_score"]
            )
        ]
    return [
        row
        for row in acceptable_rows_from_flex(flex)
        if _candidate_matches_text(row, text)
        and _required_evidence_present(text, row, required)
    ]


def valid_probe_metrics_from_turns(
    target_turns: list[dict[str, Any]],
    *,
    acceptable_dims: list[str],
    acceptable_keys: list[str],
) -> dict[str, Any]:
    dims = {str(dim) for dim in acceptable_dims if dim}
    keys = {str(key) for key in acceptable_keys if key}
    if not dims and not keys:
        return {
            "first_valid_probe_turn": "",
            "valid_probe_hit_count": 0,
            "valid_probe_hit_rate": 0.0,
            "valid_probe_coverage": 0.0,
            "covered_valid_probe_dims": "",
            "covered_valid_probe_keys": "",
        }
    hit_count = 0
    first_hit: int | None = None
    covered_dims: set[str] = set()
    covered_keys: set[str] = set()
    for index, turn in enumerate(target_turns, start=1):
        state = turn.get("internal_state") or {}
        selected_dim = str(
            state.get("selected_probe_dim") or state.get("ucb_target_dimension") or ""
        )
        probe_keys = _probe_keys_from_state(state)
        hit_dim = selected_dim in dims if selected_dim else False
        hit_key_values = keys & set(probe_keys)
        if hit_dim or hit_key_values:
            hit_count += 1
            if first_hit is None:
                first_hit = index
            if hit_dim:
                covered_dims.add(selected_dim)
            covered_keys.update(hit_key_values)
    denom = len(target_turns) if target_turns else 0
    cover_parts: list[float] = []
    if dims:
        cover_parts.append(len(covered_dims) / len(dims))
    if keys:
        cover_parts.append(len(covered_keys) / len(keys))
    return {
        "first_valid_probe_turn": first_hit if first_hit is not None else "",
        "valid_probe_hit_count": hit_count,
        "valid_probe_hit_rate": hit_count / denom if denom else 0.0,
        "valid_probe_coverage": max(cover_parts) if cover_parts else 0.0,
        "covered_valid_probe_dims": ",".join(sorted(covered_dims)),
        "covered_valid_probe_keys": ",".join(sorted(covered_keys)),
    }


def _has_candidate_set_oracle(flex: dict[str, Any]) -> bool:
    return bool(flex.get("acceptable_candidates") or flex.get("acceptance_predicate"))


def _dedupe_candidates(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[tuple[str, str, str, str]] = set()
    output: list[dict[str, Any]] = []
    for row in rows:
        key = (
            str(row.get("candidate_id") or ""),
            str(row.get("school_name") or ""),
            str(row.get("major_name") or ""),
            str(row.get("min_score") or ""),
        )
        if not any(key) or key in seen:
            continue
        seen.add(key)
        output.append(row)
    return output


def _candidate_id(row: dict[str, Any]) -> str:
    value = row.get("candidate_id")
    if value not in (None, ""):
        return str(value)
    parts = [
        row.get("school_id") or row.get("school_name"),
        row.get("major_id") or row.get("major_name"),
        row.get("year"),
        row.get("min_score"),
    ]
    return ":".join(str(part) for part in parts if part not in (None, ""))


def _candidate_matches_text(row: dict[str, Any], text: str) -> bool:
    content = str(text or "")
    school = str(row.get("school_name") or "")
    if not school or school not in content:
        return False
    score = row.get("min_score")
    if score not in (None, ""):
        if re.search(rf"(?<!\d){re.escape(str(score))}(?!\d)", content):
            return True
    return bool(SCORE_EVIDENCE_RE.search(content))


def _first_candidate_mentioned(
    text: str,
    rows: list[dict[str, Any]],
) -> dict[str, Any] | None:
    content = str(text or "")
    for row in rows:
        school = str(row.get("school_name") or "")
        if school and school in content:
            return row
    return None


def _required_evidence_present(
    text: str,
    row: dict[str, Any],
    required: list[str],
) -> bool:
    content = str(text or "")
    for item in required:
        if item == "school_score" and not _candidate_matches_text(row, content):
            return False
        if item == "tuition" and not TUITION_EVIDENCE_RE.search(content):
            return False
        if item == "quality" and not QUALITY_EVIDENCE_RE.search(content):
            return False
        if item == "employment" and not EMPLOYMENT_EVIDENCE_RE.search(content):
            return False
        if item == "risk" and not _risk_evidence_present(content):
            return False
    return True


def _risk_evidence_present(content: str) -> bool:
    return bool(
        RISK_EVIDENCE_RE.search(content)
        or any(
            token in content
            for token in (
                "min_rank",
                "rank_gap",
                "score_margin",
                "Reach",
                "Match",
                "Safety",
                "冲",
                "稳",
                "保",
                "贴线",
                "位次",
            )
        )
    )


def _candidate_set_gain(flex: dict[str, Any], text: str) -> int:
    rows = matched_acceptable_candidates(text, flex)
    if not rows:
        return 0
    predicate = flex.get("acceptance_predicate")
    if not isinstance(predicate, dict):
        predicate = {}
    gain_fields = [
        str(item)
        for item in predicate.get("gain_fields")
        or axis_oracle_rule(str(flex.get("diagnostic_axis") or "")).get(
            "gain_fields", []
        )
    ]
    gains: list[float] = []
    for row in rows:
        for field in gain_fields:
            value = _float(row.get(field))
            if value is not None:
                gains.append(max(0.0, value))
        tier_delta = _float(row.get("tier_delta"))
        if tier_delta is None:
            baseline_tier = _float(flex.get("baseline_tier"))
            tier = _float(row.get("tier"))
            if baseline_tier is not None and tier is not None:
                gains.append(max(0.0, tier - baseline_tier))
    return max(1, int(round(max(gains)))) if gains else 1


def _combined_target_text(transcript: Transcript) -> str:
    return "\n".join(
        str(turn.content or "")
        for turn in transcript.turns
        if str(turn.role) == "target_agent"
    )


def _golden_candidate(persona: IcebergPersona) -> dict[str, Any]:
    flex = persona.implicit_flexibilities or {}
    golden = flex.get("golden_candidate_b")
    if isinstance(golden, dict):
        return dict(golden)
    rows = flex.get("volunteer_set") or []
    if rows and isinstance(rows[0], dict):
        return dict(rows[0])
    return {}


def _normalize(text: str) -> str:
    return " ".join(str(text or "").split())


def _float(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number


def _probe_keys_from_state(state: dict[str, Any]) -> list[str]:
    keys: list[str] = []
    for item in state.get("probe_plan") or []:
        if isinstance(item, dict):
            value = item.get("probe") or item.get("probe_name")
            if value:
                keys.append(str(value).replace("probe_", ""))
        elif item:
            keys.append(str(item).replace("probe_", ""))
    for value in state.get("opportunity_rankings") or []:
        if value:
            keys.append(str(value).replace("probe_", ""))
    return list(dict.fromkeys(keys))


def role_is_target(role: Any) -> bool:
    return str(role) == "target_agent" or role == ConversationRole.TARGET_AGENT
