"""Build canonical iceberg cases with both process and weight gold labels."""

from __future__ import annotations

import argparse
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from app.evaluation.schemas import IcebergProfile
from gaokaollm_bench.evaluator.candidate_set_oracle import (
    axis_oracle_rule,
    default_acceptable_probe_dims,
    default_acceptable_probe_keys,
)
from gaokaollm_bench.schemas import IcebergPersona, UnifiedIcebergCase


SAMPLE_DATA_DIR = Path("gaokaollm_bench/sample_data")
OUTPUTS_DIR = Path("gaokaollm_bench/outputs")
APP_DATA_DIR = Path("app/evaluation/data")

DEFAULT_MASTER_JSONL = SAMPLE_DATA_DIR / "unified_iceberg_cases_1c6c_real_db_180.jsonl"
DEFAULT_PERSONA_VIEW = (
    SAMPLE_DATA_DIR / "unified_iceberg_personas_1c6c_real_db_180.json"
)
DEFAULT_PROFILE_VIEW = APP_DATA_DIR / "unified_iceberg_profiles_1c6c_real_db_180.jsonl"
DEFAULT_AUDIT_MD = OUTPUTS_DIR / "unified_iceberg_cases_1c6c_audit.md"
DEFAULT_AUDIT_JSON = OUTPUTS_DIR / "unified_iceberg_cases_1c6c_audit.json"

PREFERENCE_KEYS = ("school", "major", "tuition", "quality", "geo")
SOURCE_PERSONA_FILES = {
    count: SAMPLE_DATA_DIR / f"iceberg_personas_{count}constrain_real_db_30.json"
    for count in range(1, 7)
}
SOURCE_AUDIT_FILES = {
    1: OUTPUTS_DIR / "one_constraint_persona_audit.json",
    2: OUTPUTS_DIR / "two_constraint_persona_audit.json",
    3: OUTPUTS_DIR / "three_constraint_persona_audit.json",
    4: OUTPUTS_DIR / "four_constraint_persona_audit.json",
    5: OUTPUTS_DIR / "five_constraint_persona_audit.json",
    6: OUTPUTS_DIR / "six_constraint_persona_audit.json",
}

AXIS_CONFIG: dict[str, dict[str, Any]] = {
    "geo_tier": {
        "probe_gold_dims": ["geo"],
        "weight_gold_dims": ["school"],
        "weights": {
            "school": 0.55,
            "major": 0.12,
            "tuition": 0.08,
            "quality": 0.15,
            "geo": 0.10,
        },
    },
    "major_tier": {
        "probe_gold_dims": ["major"],
        "weight_gold_dims": ["school", "quality"],
        "weights": {
            "school": 0.38,
            "major": 0.12,
            "tuition": 0.05,
            "quality": 0.37,
            "geo": 0.08,
        },
    },
    "risk_tier": {
        "probe_gold_dims": ["school"],
        "weight_gold_dims": ["school"],
        "weights": {
            "school": 0.58,
            "major": 0.12,
            "tuition": 0.06,
            "quality": 0.14,
            "geo": 0.10,
        },
    },
    "tuition_value": {
        "probe_gold_dims": ["tuition"],
        "weight_gold_dims": ["school", "quality"],
        "weights": {
            "school": 0.36,
            "major": 0.05,
            "tuition": 0.19,
            "quality": 0.35,
            "geo": 0.05,
        },
    },
    "major_quality": {
        "probe_gold_dims": ["quality"],
        "weight_gold_dims": ["quality", "major"],
        "weights": {
            "school": 0.08,
            "major": 0.36,
            "tuition": 0.05,
            "quality": 0.46,
            "geo": 0.05,
        },
    },
    "employment_outcome": {
        "probe_gold_dims": ["quality"],
        "weight_gold_dims": ["quality"],
        "weights": {
            "school": 0.12,
            "major": 0.12,
            "tuition": 0.07,
            "quality": 0.62,
            "geo": 0.07,
        },
    },
}


def _load_json(path: Path) -> Any:
    if not path.exists():
        raise FileNotFoundError(path)
    return json.loads(path.read_text(encoding="utf-8"))


def _load_personas(path: Path) -> list[IcebergPersona]:
    data = _load_json(path)
    if isinstance(data, dict):
        data = data.get("items", [])
    if not isinstance(data, list):
        raise ValueError(f"{path} must contain a list or an items list")
    return [IcebergPersona.model_validate(item) for item in data]


def _load_audit(path: Path) -> dict[str, dict[str, Any]]:
    payload = _load_json(path)
    rows = payload.get("selected") if isinstance(payload, dict) else None
    if not isinstance(rows, list):
        raise ValueError(f"{path} does not contain selected audit rows")
    return {str(row["case_id"]): dict(row) for row in rows if isinstance(row, dict)}


def _normalize_weights(weights: dict[str, float]) -> dict[str, float]:
    clipped = {key: max(0.0, float(weights.get(key, 0.0))) for key in PREFERENCE_KEYS}
    total = sum(clipped.values())
    if total <= 0 or not math.isfinite(total):
        return {key: 1.0 / len(PREFERENCE_KEYS) for key in PREFERENCE_KEYS}
    normalized = {key: clipped[key] / total for key in PREFERENCE_KEYS}
    correction = 1.0 - sum(normalized.values())
    normalized[PREFERENCE_KEYS[0]] += correction
    return {key: round(float(value), 8) for key, value in normalized.items()}


def _candidate_id(row: dict[str, Any], fallback: str) -> str:
    admission_id = row.get("admission_score_id")
    if admission_id is not None:
        return f"admission:{admission_id}"
    parts = [
        row.get("school_id") or row.get("school_name"),
        row.get("major_id") or row.get("major_name"),
        row.get("year"),
        row.get("min_score"),
    ]
    compact = ":".join(str(part) for part in parts if part not in (None, ""))
    return compact or fallback


def _baseline_candidate(
    persona: IcebergPersona,
    audit: dict[str, Any],
) -> dict[str, Any]:
    background = persona.background
    return {
        "candidate_id": f"baseline:{persona.case_id}",
        "role": "baseline_candidate_a",
        "school_name": audit.get("baseline_school")
        or background.get("baseline_school"),
        "major_name": audit.get("baseline_major") or background.get("baseline_major"),
        "tier": audit.get("baseline_tier") or background.get("baseline_tier"),
        "ranking": audit.get("baseline_ranking") or background.get("baseline_ranking"),
        "school_province": background.get("province"),
        "score": background.get("score"),
        "source": "source_audit_baseline_anchor",
    }


def _golden_candidate(persona: IcebergPersona, audit: dict[str, Any]) -> dict[str, Any]:
    flex = persona.implicit_flexibilities
    volunteers = list(flex.get("volunteer_set") or [])
    if len(volunteers) != 1 or not isinstance(volunteers[0], dict):
        raise ValueError(f"{persona.case_id} must contain exactly one golden candidate")
    golden = dict(volunteers[0])
    golden.setdefault("role", "golden_candidate_b")
    golden.setdefault(
        "candidate_id", _candidate_id(golden, f"golden:{persona.case_id}")
    )
    golden.setdefault("school_name", audit.get("target_school"))
    golden.setdefault("major_name", audit.get("target_major"))
    golden.setdefault("year", audit.get("target_year"))
    golden.setdefault("min_score", audit.get("target_min_score"))
    golden.setdefault("min_rank", audit.get("target_min_rank"))
    golden.setdefault("tier", audit.get("target_tier"))
    golden["source"] = "real_db_golden_candidate"
    return golden


def _school_phi(candidate: dict[str, Any]) -> float:
    if bool(candidate.get("is_985")):
        return 0.85
    if bool(candidate.get("is_211")) or bool(candidate.get("is_double_first_class")):
        return 0.70
    try:
        tier = int(float(candidate.get("tier") or 0))
    except (TypeError, ValueError):
        tier = 0
    if tier >= 4:
        return 0.85
    if tier >= 3:
        return 0.70
    if tier >= 2:
        return 0.40
    return 0.10


def _base_phi(candidate: dict[str, Any]) -> dict[str, float]:
    return {
        "school": _school_phi(candidate),
        "major": 1.0,
        "tuition": 1.0,
        "quality": 0.5,
        "geo": 1.0,
    }


def _float(value: Any, default: float = 0.0) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    return number if math.isfinite(number) else default


def _phi_pair(
    *,
    axis: str,
    baseline: dict[str, Any],
    golden: dict[str, Any],
    audit: dict[str, Any],
    persona: IcebergPersona,
) -> tuple[dict[str, float], dict[str, float], dict[str, float], float]:
    phi_a = _base_phi(baseline)
    phi_b = _base_phi(golden)
    province = str(persona.background.get("province") or "")
    ranking_gain = max(
        0.0, _float(audit.get("ranking_gain") or golden.get("ranking_gain"))
    )
    if ranking_gain > 0:
        phi_b["school"] = min(1.0, phi_b["school"] + min(0.25, ranking_gain / 1200.0))

    if axis == "geo_tier":
        if str(golden.get("school_province") or "") != province:
            phi_b["geo"] = 0.70
    elif axis == "major_tier":
        phi_b["major"] = 0.65
    elif axis == "tuition_value":
        tuition_delta = max(
            0.0, _float(audit.get("tuition_delta") or golden.get("tuition_delta"))
        )
        phi_b["tuition"] = max(0.25, 1.0 - min(0.75, tuition_delta / 10000.0))
    elif axis == "major_quality":
        gain = max(0.0, _float(audit.get("quality_gain") or golden.get("quality_gain")))
        phi_b["quality"] = min(1.0, 0.5 + gain / 50.0)
    elif axis == "employment_outcome":
        gain = max(0.0, _float(audit.get("outcome_gain") or golden.get("outcome_gain")))
        phi_b["quality"] = min(1.0, 0.5 + gain / 70.0)

    delta = {key: round(float(phi_b[key] - phi_a[key]), 8) for key in PREFERENCE_KEYS}
    msti = round(sum(abs(value) for value in delta.values()), 8)
    return (
        {key: round(float(phi_a[key]), 8) for key in PREFERENCE_KEYS},
        {key: round(float(phi_b[key]), 8) for key in PREFERENCE_KEYS},
        delta,
        msti,
    )


def _hidden_bottom_line(
    persona: IcebergPersona,
    golden: dict[str, Any],
    probe_gold_dims: list[str],
    weight_gold_dims: list[str],
) -> str:
    flex = persona.implicit_flexibilities
    school = golden.get("school_name")
    major = golden.get("major_name")
    year = golden.get("year")
    min_score = golden.get("min_score")
    trigger = str(flex.get("trigger_condition") or "")
    return (
        "统一混合画像：用户表面坚持显式红线，但真实可妥协条件是系统给出"
        f"真实可达且证据完整的候选 {school} {major}（{year} 年最低分 {min_score}）。"
        f"主动探测应优先命中 {probe_gold_dims}，最终潜在效用权重集中在 {weight_gold_dims}。"
        f"触发条件：{trigger}"
    )


def _build_case(persona: IcebergPersona, audit: dict[str, Any]) -> UnifiedIcebergCase:
    axis = str(
        persona.background.get("diagnostic_axis") or audit.get("diagnostic_axis")
    )
    config = AXIS_CONFIG.get(axis)
    if config is None:
        raise ValueError(f"unsupported diagnostic axis: {axis}")
    constraint_count = int(persona.background.get("constraint_count") or 0)
    baseline = _baseline_candidate(persona, audit)
    golden = _golden_candidate(persona, audit)
    phi_a, phi_b, delta_phi, expected_msti = _phi_pair(
        axis=axis,
        baseline=baseline,
        golden=golden,
        audit=audit,
        persona=persona,
    )
    probe_gold_dims = list(config["probe_gold_dims"])
    weight_gold_dims = list(config["weight_gold_dims"])
    ground_truth_weights = _normalize_weights(dict(config["weights"]))
    flex = dict(persona.implicit_flexibilities)
    trigger_condition = str(flex.get("trigger_condition") or "")
    acceptable_candidates = [dict(golden)]
    acceptance_predicate = axis_oracle_rule(axis)
    acceptable_probe_dims = default_acceptable_probe_dims(axis, probe_gold_dims)
    acceptable_probe_keys = default_acceptable_probe_keys(axis)
    return UnifiedIcebergCase(
        case_id=persona.case_id,
        constraint_count=constraint_count,
        diagnostic_axis=axis,
        initial_utterance=persona.initial_utterance,
        explicit_red_lines=dict(persona.explicit_red_lines),
        hidden_bottom_line=_hidden_bottom_line(
            persona,
            golden,
            probe_gold_dims,
            weight_gold_dims,
        ),
        trigger_condition=trigger_condition,
        ground_truth_weights=ground_truth_weights,
        probe_gold_dims=probe_gold_dims,
        weight_gold_dims=weight_gold_dims,
        baseline_candidate_a=baseline,
        golden_candidate_b=golden,
        acceptable_candidates=acceptable_candidates,
        acceptance_predicate=acceptance_predicate,
        acceptable_probe_dims=acceptable_probe_dims,
        acceptable_probe_keys=acceptable_probe_keys,
        phi_a=phi_a,
        phi_b=phi_b,
        delta_phi=delta_phi,
        expected_msti=expected_msti,
        volunteer_set=[golden],
        minimum_required_volunteers=1,
        background=dict(persona.background),
        implicit_flexibilities=flex,
        process_milestones=dict(persona.process_milestones),
    )


def build_cases() -> list[UnifiedIcebergCase]:
    cases: list[UnifiedIcebergCase] = []
    for constraint_count in range(1, 7):
        personas = _load_personas(SOURCE_PERSONA_FILES[constraint_count])
        audit_by_case = _load_audit(SOURCE_AUDIT_FILES[constraint_count])
        for persona in personas:
            audit = audit_by_case.get(persona.case_id)
            if audit is None:
                raise KeyError(f"audit row missing for {persona.case_id}")
            cases.append(_build_case(persona, audit))
    return cases


def case_to_persona(case: UnifiedIcebergCase) -> IcebergPersona:
    background = dict(case.background)
    background.update(
        {
            "unified_case_id": case.case_id,
            "ground_truth_weights": case.ground_truth_weights,
            "probe_gold_dims": case.probe_gold_dims,
            "acceptable_probe_dims": case.acceptable_probe_dims,
            "acceptable_probe_keys": case.acceptable_probe_keys,
            "weight_gold_dims": case.weight_gold_dims,
            "expected_msti": case.expected_msti,
            "phi_a": case.phi_a,
            "phi_b": case.phi_b,
            "delta_phi": case.delta_phi,
        }
    )
    flex = dict(case.implicit_flexibilities)
    flex.update(
        {
            "hidden_bottom_line": case.hidden_bottom_line,
            "probe_gold_dims": case.probe_gold_dims,
            "weight_gold_dims": case.weight_gold_dims,
            "ground_truth_weights": case.ground_truth_weights,
            "baseline_candidate_a": case.baseline_candidate_a,
            "golden_candidate_b": case.golden_candidate_b,
            "acceptable_candidates": case.acceptable_candidates or case.volunteer_set,
            "acceptance_predicate": case.acceptance_predicate,
            "acceptable_probe_dims": case.acceptable_probe_dims,
            "acceptable_probe_keys": case.acceptable_probe_keys,
            "phi_a": case.phi_a,
            "phi_b": case.phi_b,
            "delta_phi": case.delta_phi,
            "expected_msti": case.expected_msti,
            "volunteer_set": case.volunteer_set,
            "minimum_required_volunteers": case.minimum_required_volunteers,
        }
    )
    return IcebergPersona(
        case_id=case.case_id,
        background=background,
        explicit_red_lines=case.explicit_red_lines,
        implicit_flexibilities=flex,
        initial_utterance=case.initial_utterance,
        process_milestones=case.process_milestones,
    )


def case_to_profile_row(case: UnifiedIcebergCase) -> dict[str, Any]:
    return {
        "profile_id": case.case_id,
        "explicit_query": case.initial_utterance,
        "hidden_bottom_line": case.hidden_bottom_line,
        "ground_truth_weights": case.ground_truth_weights,
        "metadata": {
            "source": "unified_iceberg_case",
            "constraint_count": case.constraint_count,
            "diagnostic_axis": case.diagnostic_axis,
            "probe_gold_dims": case.probe_gold_dims,
            "acceptable_probe_dims": case.acceptable_probe_dims,
            "acceptable_probe_keys": case.acceptable_probe_keys,
            "weight_gold_dims": case.weight_gold_dims,
            "expected_msti": case.expected_msti,
            "golden_candidate_id": case.golden_candidate_b.get("candidate_id"),
        },
    }


def validate_cases(cases: list[UnifiedIcebergCase]) -> None:
    seen: set[str] = set()
    for case in cases:
        if case.case_id in seen:
            raise AssertionError(f"duplicate case_id: {case.case_id}")
        seen.add(case.case_id)
        if case.constraint_count < 1 or case.constraint_count > 6:
            raise AssertionError(f"{case.case_id} invalid constraint_count")
        if set(case.ground_truth_weights) != set(PREFERENCE_KEYS):
            raise AssertionError(f"{case.case_id} invalid weight keys")
        total = sum(float(value) for value in case.ground_truth_weights.values())
        if abs(total - 1.0) > 1e-6:
            raise AssertionError(f"{case.case_id} weights sum to {total}")
        if not case.probe_gold_dims or not case.weight_gold_dims:
            raise AssertionError(f"{case.case_id} missing gold dims")
        for dim in [*case.probe_gold_dims, *case.weight_gold_dims]:
            if dim not in PREFERENCE_KEYS:
                raise AssertionError(f"{case.case_id} invalid gold dim: {dim}")
        if len(case.volunteer_set) != 1 or case.minimum_required_volunteers != 1:
            raise AssertionError(f"{case.case_id} volunteer invariant failed")
        if not case.acceptable_candidates:
            raise AssertionError(f"{case.case_id} missing acceptable candidates")
        if not case.acceptable_probe_dims or not case.acceptable_probe_keys:
            raise AssertionError(f"{case.case_id} missing acceptable probe labels")
        golden = case.golden_candidate_b
        for key in ("school_name", "major_name", "year", "min_score"):
            if golden.get(key) in (None, ""):
                raise AssertionError(f"{case.case_id} golden missing {key}")
        if set(case.phi_a) != set(PREFERENCE_KEYS) or set(case.phi_b) != set(
            PREFERENCE_KEYS
        ):
            raise AssertionError(f"{case.case_id} invalid phi keys")
        if set(case.delta_phi) != set(PREFERENCE_KEYS):
            raise AssertionError(f"{case.case_id} invalid delta_phi keys")
        recomputed = sum(abs(float(value)) for value in case.delta_phi.values())
        if abs(recomputed - float(case.expected_msti)) > 1e-6:
            raise AssertionError(f"{case.case_id} expected_msti mismatch")
        case_to_persona(case)
        IcebergProfile.model_validate(case_to_profile_row(case))


def write_jsonl(rows: list[dict[str, Any]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def write_outputs(
    cases: list[UnifiedIcebergCase],
    *,
    master_jsonl: Path,
    persona_view: Path,
    profile_view: Path,
    audit_md: Path,
    audit_json: Path,
) -> None:
    master_rows = [case.model_dump() for case in cases]
    write_jsonl(master_rows, master_jsonl)

    personas = [case_to_persona(case).model_dump() for case in cases]
    persona_view.parent.mkdir(parents=True, exist_ok=True)
    persona_view.write_text(
        json.dumps(personas, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    profile_rows = [case_to_profile_row(case) for case in cases]
    write_jsonl(profile_rows, profile_view)

    audit = build_audit(cases)
    audit_json.parent.mkdir(parents=True, exist_ok=True)
    audit_json.write_text(
        json.dumps(audit, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    audit_md.parent.mkdir(parents=True, exist_ok=True)
    audit_md.write_text(render_audit_md(audit), encoding="utf-8")


def build_audit(cases: list[UnifiedIcebergCase]) -> dict[str, Any]:
    by_constraint = Counter(case.constraint_count for case in cases)
    by_axis = Counter(case.diagnostic_axis for case in cases)
    by_pair = Counter((case.constraint_count, case.diagnostic_axis) for case in cases)
    msti_by_axis: dict[str, list[float]] = defaultdict(list)
    for case in cases:
        msti_by_axis[case.diagnostic_axis].append(float(case.expected_msti))
    axis_msti = {
        axis: {
            "count": len(values),
            "min": min(values),
            "mean": sum(values) / len(values),
            "max": max(values),
        }
        for axis, values in sorted(msti_by_axis.items())
    }
    return {
        "total_cases": len(cases),
        "by_constraint_count": dict(sorted(by_constraint.items())),
        "by_diagnostic_axis": dict(sorted(by_axis.items())),
        "by_constraint_axis": {
            f"{constraint_count}:{axis}": count
            for (constraint_count, axis), count in sorted(by_pair.items())
        },
        "msti_by_axis": axis_msti,
        "source_persona_files": {
            str(key): str(value) for key, value in SOURCE_PERSONA_FILES.items()
        },
    }


def render_audit_md(audit: dict[str, Any]) -> str:
    lines = [
        "# Unified Iceberg Cases Audit",
        "",
        f"Total cases: {audit['total_cases']}.",
        "",
        "## Constraint Counts",
        "",
        "| Constraint count | Cases |",
        "| ---: | ---: |",
    ]
    for count, value in audit["by_constraint_count"].items():
        lines.append(f"| {count} | {value} |")
    lines.extend(
        [
            "",
            "## Diagnostic Axes",
            "",
            "| Axis | Cases | MSTI min | MSTI mean | MSTI max |",
            "| --- | ---: | ---: | ---: | ---: |",
        ]
    )
    for axis, value in audit["by_diagnostic_axis"].items():
        msti = audit["msti_by_axis"][axis]
        lines.append(
            f"| {axis} | {value} | {msti['min']:.3f} | {msti['mean']:.3f} | {msti['max']:.3f} |"
        )
    lines.extend(
        [
            "",
            "## Constraint x Axis",
            "",
            "| Constraint | Axis | Cases |",
            "| ---: | --- | ---: |",
        ]
    )
    for key, value in audit["by_constraint_axis"].items():
        constraint, axis = key.split(":", 1)
        lines.append(f"| {constraint} | {axis} | {value} |")
    return "\n".join(lines) + "\n"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--master-jsonl", type=Path, default=DEFAULT_MASTER_JSONL)
    parser.add_argument("--persona-view", type=Path, default=DEFAULT_PERSONA_VIEW)
    parser.add_argument("--profile-view", type=Path, default=DEFAULT_PROFILE_VIEW)
    parser.add_argument("--audit-md", type=Path, default=DEFAULT_AUDIT_MD)
    parser.add_argument("--audit-json", type=Path, default=DEFAULT_AUDIT_JSON)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    cases = build_cases()
    validate_cases(cases)
    write_outputs(
        cases,
        master_jsonl=args.master_jsonl,
        persona_view=args.persona_view,
        profile_view=args.profile_view,
        audit_md=args.audit_md,
        audit_json=args.audit_json,
    )
    print(f"Wrote {len(cases)} unified cases to {args.master_jsonl}")
    print(f"Wrote IcebergPersona view to {args.persona_view}")
    print(f"Wrote IcebergProfile view to {args.profile_view}")
    print(f"Wrote audit markdown to {args.audit_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
