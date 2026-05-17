"""Build a six-case reachable candidate-set oracle dataset."""

from __future__ import annotations

import argparse
import asyncio
import json
import math
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from app.flows.probers import run_all_probes
from gaokaollm_bench.data_gen.build_unified_iceberg_cases import (
    _candidate_id,
    _phi_pair,
    case_to_persona,
)
from gaokaollm_bench.evaluator.candidate_set_oracle import (
    axis_oracle_rule,
    default_acceptable_probe_dims,
    default_acceptable_probe_keys,
)
from gaokaollm_bench.schemas import UnifiedIcebergCase
from gaokaollm_bench.sandbox.target_agents import (
    _fallback_extract_constraints,
    _merge_constraints,
)


DEFAULT_SOURCE = Path(
    "gaokaollm_bench/sample_data/unified_iceberg_cases_1c6c_real_db_180.jsonl"
)
DEFAULT_MASTER_JSONL = Path(
    "gaokaollm_bench/sample_data/unified_micro_oracle_cases_1c_6.jsonl"
)
DEFAULT_PERSONA_VIEW = Path(
    "gaokaollm_bench/sample_data/unified_micro_oracle_personas_1c_6.json"
)
DEFAULT_AUDIT_JSON = Path("gaokaollm_bench/outputs/unified_micro_oracle_audit.json")
DEFAULT_AUDIT_MD = Path("gaokaollm_bench/outputs/unified_micro_oracle_audit.md")
AXES = (
    "geo_tier",
    "major_tier",
    "risk_tier",
    "tuition_value",
    "major_quality",
    "employment_outcome",
)
PROBE_KEY_TO_DIM = {
    "geo_relax": "geo",
    "region_tree_relax": "geo",
    "city_relax": "geo",
    "major_geo_relax": "major",
    "major_relax": "major",
    "strength_relax": "quality",
    "major_quality_relax": "quality",
    "employment_outcome_relax": "quality",
    "risk_band_relax": "school",
    "tuition_value_relax": "tuition",
}
NOISY_SCHOOL_TERMS = (
    "中北学院",
    "泰州学院",
    "职业技术",
    "职业学院",
    "职业大学",
    "独立学院",
    "民办",
)
NOISY_MAJOR_TERMS = (
    "中外合作",
    "合作办学",
    "国际",
    "校区",
    "只招",
    "政治面貌",
    "成绩不低于",
    "凤凰校区",
    "5+3",
)


def read_cases(path: Path) -> list[UnifiedIcebergCase]:
    cases: list[UnifiedIcebergCase] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                cases.append(UnifiedIcebergCase.model_validate(json.loads(line)))
    return cases


async def build_micro_cases(
    source: Path,
) -> tuple[list[UnifiedIcebergCase], list[dict[str, Any]]]:
    cases = [
        case
        for case in read_cases(source)
        if int(case.constraint_count) == 1 and case.diagnostic_axis in AXES
    ]
    selected: list[UnifiedIcebergCase] = []
    audit: list[dict[str, Any]] = []
    for axis in AXES:
        axis_cases = [case for case in cases if case.diagnostic_axis == axis]
        chosen: (
            tuple[UnifiedIcebergCase, list[dict[str, Any]], dict[str, int]] | None
        ) = None
        for case in axis_cases:
            constraints = _constraints_from_case(case)
            try:
                opportunities = await run_all_probes(
                    constraints,
                    user_state={
                        "constraints": constraints,
                        "implicit_weights": case.ground_truth_weights,
                        "diagnostic_axis": axis,
                    },
                )
            except Exception as exc:
                audit.append(
                    {
                        "case_id": case.case_id,
                        "axis": axis,
                        "status": "probe_failed",
                        "error_type": type(exc).__name__,
                        "error": str(exc),
                    }
                )
                continue
            counts = {
                key: len(value) if isinstance(value, list) else 0
                for key, value in opportunities.items()
            }
            acceptable = _acceptable_candidates_for_axis(case, opportunities)
            audit.append(
                {
                    "case_id": case.case_id,
                    "axis": axis,
                    "status": "candidate_scan",
                    "opportunity_counts": counts,
                    "acceptable_count": len(acceptable),
                    "acceptable_probe_keys": default_acceptable_probe_keys(axis),
                }
            )
            if len(acceptable) >= 2:
                chosen = (case, acceptable[:5], counts)
                break
        if chosen is None:
            raise RuntimeError(f"no reachable acceptable micro case for {axis}")
        case, acceptable, counts = chosen
        selected.append(_case_with_acceptable_set(case, acceptable))
        audit.append(
            {
                "case_id": case.case_id,
                "axis": axis,
                "status": "selected",
                "opportunity_counts": counts,
                "acceptable_count": len(acceptable),
                "acceptable_probe_keys": default_acceptable_probe_keys(axis),
                "acceptable_candidates": [_audit_candidate(row) for row in acceptable],
                "exemplar_candidate": _audit_candidate(acceptable[0]),
            }
        )
    return selected, audit


def _constraints_from_case(case: UnifiedIcebergCase) -> dict[str, Any]:
    background = case.background or {}
    constraints = _merge_constraints(
        {},
        _fallback_extract_constraints(case.initial_utterance),
    )
    constraints["score"] = constraints.get("score") or background.get("score")
    constraints["selected_subjects"] = (
        constraints.get("selected_subjects")
        or background.get("subjects")
        or ["物理", "化学", "生物"]
    )
    axis = case.diagnostic_axis
    if axis == "risk_tier":
        constraints["risk_preference"] = "conservative"
    if axis == "tuition_value":
        budget = (
            case.explicit_red_lines.get("tuition_budget")
            or case.explicit_red_lines.get("tuition")
            or background.get("budget")
            or 5000
        )
        constraints["budget"] = _int_from_text(budget, default=5000)
    if axis == "major_quality":
        constraints["strength"] = "major_quality"
    if axis == "employment_outcome":
        constraints["employment_preference"] = "employment_outcome"
        if not constraints.get("major") and background.get("preferred_major"):
            constraints["major"] = background.get("preferred_major")
    return {key: value for key, value in constraints.items() if value not in ("", [])}


def _acceptable_candidates_for_axis(
    case: UnifiedIcebergCase,
    opportunities: dict[str, Any],
) -> list[dict[str, Any]]:
    rule = axis_oracle_rule(case.diagnostic_axis)
    allowed = set(rule.get("acceptable_probe_keys") or [])
    rows: list[dict[str, Any]] = []
    for key in allowed:
        values = opportunities.get(key) or []
        if isinstance(values, dict):
            flat: list[dict[str, Any]] = []
            for bucket, bucket_rows in values.items():
                for row in bucket_rows or []:
                    if isinstance(row, dict):
                        item = dict(row)
                        item.setdefault("risk_bucket", bucket)
                        flat.append(item)
            values = flat
        for raw in values:
            if not isinstance(raw, dict):
                continue
            row = dict(raw)
            row["_opportunity_key"] = key
            if _row_satisfies_axis(case, row):
                row.setdefault(
                    "candidate_id",
                    _candidate_id(row, f"reachable:{case.case_id}:{len(rows)}"),
                )
                row.setdefault("source", "reachable_probe_candidate")
                rows.append(row)
    return _dedupe(rows)


def _row_satisfies_axis(case: UnifiedIcebergCase, row: dict[str, Any]) -> bool:
    if not _row_is_clean(row):
        return False
    if row.get("school_name") in (None, "") or row.get("major_name") in (None, ""):
        return False
    if row.get("year") in (None, "") or row.get("min_score") in (None, ""):
        return False
    axis = case.diagnostic_axis
    baseline_tier = _float(case.baseline_candidate_a.get("tier"))
    tier = _float(row.get("tier"))
    tier_delta = max(0.0, (tier or 0.0) - (baseline_tier or 0.0))
    row["tier_delta"] = tier_delta
    if (
        row.get("ranking") is not None
        and case.baseline_candidate_a.get("ranking") is not None
    ):
        row["ranking_gain"] = max(
            0.0,
            float(case.baseline_candidate_a["ranking"]) - float(row["ranking"]),
        )
    if axis == "geo_tier":
        return str(row.get("school_province") or "") != str(
            case.background.get("province") or ""
        ) and (tier_delta >= 1 or _float(row.get("ranking_gain")) >= 50)
    if axis == "major_tier":
        return _major_is_related(
            str(
                case.background.get("preferred_major")
                or case.explicit_red_lines.get("major")
                or ""
            ),
            str(row.get("major_name") or ""),
        ) and (tier_delta >= 1 or (_float(row.get("quality_gain")) or 0.0) >= 10)
    if axis == "risk_tier":
        margin = _float(row.get("score_margin"))
        return (
            margin is not None
            and -5 <= margin <= 20
            and (tier_delta >= 1 or row.get("risk_level"))
        )
    if axis == "tuition_value":
        tuition_delta = _float(row.get("tuition_delta"))
        if tuition_delta is None or not (0 < tuition_delta <= 10000):
            return False
        row.setdefault("tuition_value_gain", 1)
        return True
    if axis == "major_quality":
        return (
            (_float(row.get("quality_gain")) or 0.0) >= 10
            or row.get("quality_score") is not None
            or row.get("major_strength_rank") is not None
        )
    if axis == "employment_outcome":
        return (
            (_float(row.get("outcome_gain")) or 0.0) >= 10
            or row.get("outcome_score") is not None
            or row.get("employment_rank") is not None
        )
    return False


def _row_is_clean(row: dict[str, Any]) -> bool:
    school = str(row.get("school_name") or "")
    major = str(row.get("major_name") or "")
    if not school or not major:
        return False
    if any(term in school for term in NOISY_SCHOOL_TERMS):
        return False
    if any(term in major for term in NOISY_MAJOR_TERMS):
        return False
    return len(major) <= 40


def _major_is_related(preferred: str, candidate: str) -> bool:
    preferred_text = str(preferred or "")
    candidate_text = str(candidate or "")
    if not preferred_text:
        return True
    groups = [
        (
            "临床",
            (
                "临床",
                "医学",
                "基础医学",
                "口腔",
                "护理",
                "药",
                "中医",
                "康复",
                "眼视光",
            ),
        ),
        ("医学", ("医学", "基础医学", "口腔", "护理", "药", "中医", "康复", "眼视光")),
        ("计算机", ("计算机", "软件", "数据", "人工智能", "网络", "信息安全", "智能")),
        ("软件", ("软件", "计算机", "数据", "人工智能", "网络", "信息")),
        ("法学", ("法学", "法律", "知识产权", "政治")),
    ]
    for marker, allowed in groups:
        if marker in preferred_text:
            return any(token in candidate_text for token in allowed)
    return any(token and token in candidate_text for token in preferred_text[:4])


def _case_with_acceptable_set(
    case: UnifiedIcebergCase,
    acceptable: list[dict[str, Any]],
) -> UnifiedIcebergCase:
    exemplar = dict(acceptable[0])
    exemplar["role"] = "golden_candidate_b"
    phi_a, phi_b, delta_phi, expected_msti = _phi_pair(
        axis=case.diagnostic_axis,
        baseline=case.baseline_candidate_a,
        golden=exemplar,
        audit=exemplar,
        persona=case_to_persona(case),
    )
    predicate = axis_oracle_rule(case.diagnostic_axis)
    predicate.update(
        {
            "oracle_type": "reachable_candidate_set",
            "minimum_required_volunteers": 1,
            "candidate_count": len(acceptable),
            "exemplar_candidate_id": exemplar.get("candidate_id"),
        }
    )
    flex = dict(case.implicit_flexibilities)
    flex.update(
        {
            "trigger_type": "candidate_set_verified_option",
            "acceptable_candidates": acceptable,
            "acceptance_predicate": predicate,
            "acceptable_probe_dims": default_acceptable_probe_dims(
                case.diagnostic_axis,
                case.probe_gold_dims,
            ),
            "acceptable_probe_keys": default_acceptable_probe_keys(
                case.diagnostic_axis
            ),
            "golden_candidate_b": exemplar,
            "volunteer_set": [exemplar],
            "minimum_required_volunteers": 1,
            "trigger_condition": (
                "系统主动提出 acceptable_candidates 中任一真实可达候选，并给出学校、专业、年份/最低分"
                "及对应收益证据，即可触发用户认真考虑。"
            ),
        }
    )
    background = dict(case.background)
    background.update(
        {
            "micro_oracle": True,
            "acceptable_candidate_count": len(acceptable),
            "acceptable_probe_dims": flex["acceptable_probe_dims"],
            "acceptable_probe_keys": flex["acceptable_probe_keys"],
        }
    )
    initial_utterance = case.initial_utterance
    if case.diagnostic_axis == "employment_outcome":
        preferred_major = str(case.background.get("preferred_major") or "").strip()
        if preferred_major and preferred_major not in initial_utterance:
            initial_utterance = f"{initial_utterance} 专业方向可以灵活，但请先围绕{preferred_major}相关方向给就业证据。"
    return case.model_copy(
        update={
            "case_id": f"micro-oracle-{case.diagnostic_axis}",
            "initial_utterance": initial_utterance,
            "background": background,
            "hidden_bottom_line": flex["trigger_condition"],
            "trigger_condition": flex["trigger_condition"],
            "golden_candidate_b": exemplar,
            "acceptable_candidates": acceptable,
            "acceptance_predicate": predicate,
            "acceptable_probe_dims": flex["acceptable_probe_dims"],
            "acceptable_probe_keys": flex["acceptable_probe_keys"],
            "phi_b": phi_b,
            "delta_phi": delta_phi,
            "expected_msti": expected_msti,
            "volunteer_set": [exemplar],
            "implicit_flexibilities": flex,
            "process_milestones": {
                **case.process_milestones,
                "accept_after_verified_option": [
                    str(row.get("school_name") or "") for row in acceptable
                ],
                "candidate_set_oracle": True,
            },
        }
    )


def _audit_candidate(row: dict[str, Any]) -> dict[str, Any]:
    keys = [
        "candidate_id",
        "_opportunity_key",
        "school_name",
        "school_province",
        "major_name",
        "year",
        "min_score",
        "min_rank",
        "tier",
        "tier_delta",
        "ranking",
        "ranking_gain",
        "score_margin",
        "risk_level",
        "tuition",
        "tuition_delta",
        "quality_score",
        "quality_gain",
        "outcome_score",
        "outcome_gain",
    ]
    return {key: row.get(key) for key in keys if row.get(key) not in (None, "")}


def _dedupe(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[tuple[Any, Any, Any, Any]] = set()
    output: list[dict[str, Any]] = []
    for row in rows:
        key = (
            row.get("school_id") or row.get("school_name"),
            row.get("major_id") or row.get("major_name"),
            row.get("year"),
            row.get("_opportunity_key"),
        )
        if key in seen:
            continue
        seen.add(key)
        output.append(row)
    return output


def _float(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _int_from_text(value: Any, *, default: int) -> int:
    if isinstance(value, (int, float)):
        return int(value)
    import re

    match = re.search(r"\d{4,6}", str(value or ""))
    return int(match.group(0)) if match else default


def write_outputs(
    cases: list[UnifiedIcebergCase],
    audit: list[dict[str, Any]],
    *,
    master_jsonl: Path,
    persona_view: Path,
    audit_json: Path,
    audit_md: Path,
) -> None:
    master_jsonl.parent.mkdir(parents=True, exist_ok=True)
    with master_jsonl.open("w", encoding="utf-8", newline="\n") as handle:
        for case in cases:
            handle.write(
                json.dumps(
                    case.model_dump(),
                    ensure_ascii=False,
                    sort_keys=True,
                    default=str,
                )
                + "\n"
            )
    personas = [case_to_persona(case).model_dump() for case in cases]
    persona_view.parent.mkdir(parents=True, exist_ok=True)
    persona_view.write_text(
        json.dumps(personas, ensure_ascii=False, indent=2, default=str) + "\n",
        encoding="utf-8",
    )
    audit_json.parent.mkdir(parents=True, exist_ok=True)
    audit_json.write_text(
        json.dumps(audit, ensure_ascii=False, indent=2, default=str) + "\n",
        encoding="utf-8",
    )
    audit_md.parent.mkdir(parents=True, exist_ok=True)
    audit_md.write_text(_render_audit_md(cases, audit), encoding="utf-8")


def _render_audit_md(
    cases: list[UnifiedIcebergCase], audit: list[dict[str, Any]]
) -> str:
    lines = [
        "# Unified Micro Oracle Audit",
        "",
        f"Selected cases: {len(cases)}.",
        "",
        "| Axis | Case | Acceptable candidates | Probe keys | Exemplar |",
        "| --- | --- | ---: | --- | --- |",
    ]
    selected_rows = [row for row in audit if row.get("status") == "selected"]
    for row in selected_rows:
        exemplar = row.get("exemplar_candidate") or {}
        lines.append(
            "| "
            + " | ".join(
                [
                    str(row.get("axis") or ""),
                    str(row.get("case_id") or ""),
                    str(row.get("acceptable_count") or 0),
                    ",".join(row.get("acceptable_probe_keys") or []),
                    f"{exemplar.get('school_name')} {exemplar.get('major_name')} {exemplar.get('min_score')}",
                ]
            )
            + " |"
        )
    return "\n".join(lines) + "\n"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--master-jsonl", type=Path, default=DEFAULT_MASTER_JSONL)
    parser.add_argument("--persona-view", type=Path, default=DEFAULT_PERSONA_VIEW)
    parser.add_argument("--audit-json", type=Path, default=DEFAULT_AUDIT_JSON)
    parser.add_argument("--audit-md", type=Path, default=DEFAULT_AUDIT_MD)
    return parser


async def async_main(args: argparse.Namespace) -> int:
    load_dotenv()
    cases, audit = await build_micro_cases(args.source)
    write_outputs(
        cases,
        audit,
        master_jsonl=args.master_jsonl,
        persona_view=args.persona_view,
        audit_json=args.audit_json,
        audit_md=args.audit_md,
    )
    print(f"[micro_oracle] wrote {len(cases)} cases to {args.master_jsonl}")
    print(f"[micro_oracle] wrote persona view to {args.persona_view}")
    print(f"[micro_oracle] wrote audit to {args.audit_md}")
    return 0


def main() -> int:
    return asyncio.run(async_main(build_parser().parse_args()))


if __name__ == "__main__":
    raise SystemExit(main())
