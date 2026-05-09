"""Audit thesis-facing benchmark artifacts without rerunning experiments."""

from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


TARGET_APP = "app_pareto"
TARGET_BASELINE = "hard_constraint"

DEFAULT_THESIS_DOCS = [
    Path("gaokaollm_bench/outputs/thesis_agent_benchmark_contribution.md"),
    Path("gaokaollm_bench/outputs/thesis_method_experiment_chapters.md"),
]
DEFAULT_OUTPUT_JSON = Path("gaokaollm_bench/outputs/thesis_artifact_audit.json")
DEFAULT_OUTPUT_MD = Path("gaokaollm_bench/outputs/thesis_artifact_audit.md")


@dataclass(frozen=True)
class ExperimentConfig:
    name: str
    experiment_dir: Path
    evidence_doc: Path
    opportunity_field: str
    expected_metrics: dict[str, dict[str, float | int]]
    expected_app_success: int
    expected_app_failure: int
    expected_baseline_success: int
    min_success_opportunity_count: int = 0
    failure_case_id: str | None = None
    failure_markers: tuple[str, ...] = ()


EXPERIMENTS = [
    ExperimentConfig(
        name="major_geo_v1",
        experiment_dir=Path("gaokaollm_bench/outputs/agent_benchmark_major_geo_v1"),
        evidence_doc=Path(
            "gaokaollm_bench/outputs/agent_benchmark_major_geo_v1_evidence.md"
        ),
        opportunity_field="major_geo_relax",
        expected_metrics={
            TARGET_APP: {
                "cases": 10,
                "completed_cases": 10,
                "failed_cases": 0,
                "elicitation_success_rate": 0.9,
                "success_count": 9,
                "mean_pareto_gain": 0.9,
                "mean_hallucination_rate": 0.0,
                "avg_turns": 5.2,
            },
            TARGET_BASELINE: {
                "cases": 10,
                "completed_cases": 10,
                "failed_cases": 0,
                "elicitation_success_rate": 0.0,
                "success_count": 0,
                "mean_pareto_gain": 0.0,
                "mean_hallucination_rate": 0.0,
                "avg_turns": 7.0,
            },
        },
        expected_app_success=9,
        expected_app_failure=1,
        expected_baseline_success=0,
        failure_case_id="real-db-set-浙江-569-009",
        failure_markers=("唯一失败样本", "100% 成功"),
    ),
    ExperimentConfig(
        name="risk_band_v1",
        experiment_dir=Path("gaokaollm_bench/outputs/agent_benchmark_risk_band_v1"),
        evidence_doc=Path(
            "gaokaollm_bench/outputs/agent_benchmark_risk_band_v1_evidence.md"
        ),
        opportunity_field="risk_band_relax",
        expected_metrics={
            TARGET_APP: {
                "cases": 10,
                "completed_cases": 10,
                "failed_cases": 0,
                "elicitation_success_rate": 1.0,
                "success_count": 10,
                "mean_pareto_gain": 3.0,
                "mean_hallucination_rate": 0.0,
                "avg_turns": 5.0,
            },
            TARGET_BASELINE: {
                "cases": 10,
                "completed_cases": 10,
                "failed_cases": 0,
                "elicitation_success_rate": 0.0,
                "success_count": 0,
                "mean_pareto_gain": 0.0,
                "mean_hallucination_rate": 0.0,
                "avg_turns": 15.0,
            },
        },
        expected_app_success=10,
        expected_app_failure=0,
        expected_baseline_success=0,
        min_success_opportunity_count=3,
    ),
]


@dataclass(frozen=True)
class Check:
    name: str
    passed: bool
    detail: str

    def to_dict(self) -> dict[str, Any]:
        return {"name": self.name, "passed": self.passed, "detail": self.detail}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Audit thesis benchmark artifacts without DB or LLM calls."
    )
    parser.add_argument(
        "--experiment",
        choices=["all", *[experiment.name for experiment in EXPERIMENTS]],
        default="all",
        help="Experiment group to audit. Defaults to all thesis-facing experiments.",
    )
    parser.add_argument(
        "--experiment-dir",
        default=None,
        help=(
            "Legacy single-experiment override. If set, audits only the matching "
            "configured experiment directory."
        ),
    )
    parser.add_argument(
        "--evidence-doc",
        default=None,
        help="Legacy evidence-doc override used together with --experiment-dir.",
    )
    parser.add_argument(
        "--thesis-doc",
        action="append",
        default=None,
        help="Thesis doc to include in global checks. Can be passed multiple times.",
    )
    parser.add_argument("--output-json", default=str(DEFAULT_OUTPUT_JSON))
    parser.add_argument("--output-md", default=str(DEFAULT_OUTPUT_MD))
    return parser.parse_args()


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def add_check(checks: list[Check], name: str, passed: bool, detail: str) -> None:
    checks.append(Check(name=name, passed=passed, detail=detail))


def metric_matches(actual: Any, expected: Any) -> bool:
    if isinstance(expected, float):
        return actual is not None and abs(float(actual) - expected) < 1e-9
    return actual == expected


def rows_by_case(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {str(row["case_id"]): row for row in rows}


def load_transcript(path: Path) -> dict[str, Any]:
    return read_json(path)


def target_internal_states(transcript: dict[str, Any]) -> list[dict[str, Any]]:
    states: list[dict[str, Any]] = []
    for turn in transcript.get("turns", []):
        if turn.get("role") != "target_agent":
            continue
        state = turn.get("internal_state") or {}
        if isinstance(state, dict):
            states.append(state)
    return states


def opportunity_items(state: dict[str, Any], field: str) -> list[Any]:
    opportunities = state.get("pareto_opportunities") or {}
    value = opportunities.get(field) or state.get(field)
    if not value:
        return []
    if isinstance(value, list):
        return value
    return [value]


def recommended_items(state: dict[str, Any]) -> list[Any]:
    recommended = state.get("recommended_schools")
    if not recommended:
        return []
    if isinstance(recommended, list):
        return recommended
    return [recommended]


def has_agent_evidence(transcript: dict[str, Any], opportunity_field: str) -> bool:
    for state in target_internal_states(transcript):
        if opportunity_items(state, opportunity_field) or recommended_items(state):
            return True
    return False


def max_opportunity_count(transcript: dict[str, Any], opportunity_field: str) -> int:
    counts = [
        len(opportunity_items(state, opportunity_field))
        for state in target_internal_states(transcript)
    ]
    return max(counts, default=0)


def has_baseline_opportunity(
    transcript: dict[str, Any], opportunity_field: str
) -> bool:
    return any(
        opportunity_items(state, opportunity_field)
        for state in target_internal_states(transcript)
    )


def resolve_transcript_path(raw_path: str, experiment_dir: Path, target: str) -> Path:
    path = Path(raw_path)
    if path.exists():
        return path
    case_suffix = path.stem.replace("transcript_", "")
    transcript_dir = experiment_dir / "transcripts" / target
    matches = sorted(
        candidate
        for candidate in transcript_dir.glob("*.json")
        if case_suffix in candidate.stem
    )
    if len(matches) == 1:
        return matches[0]
    return path


def selected_experiments(args: argparse.Namespace) -> list[ExperimentConfig]:
    experiments = EXPERIMENTS
    if args.experiment != "all":
        experiments = [
            experiment
            for experiment in experiments
            if experiment.name == args.experiment
        ]
    if args.experiment_dir:
        override_dir = Path(args.experiment_dir)
        matches = [
            experiment
            for experiment in experiments
            if experiment.experiment_dir == override_dir
            or experiment.experiment_dir.resolve() == override_dir.resolve()
        ]
        if not matches:
            matches = [EXPERIMENTS[0]]
        evidence_doc = (
            Path(args.evidence_doc) if args.evidence_doc else matches[0].evidence_doc
        )
        base = matches[0]
        experiments = [
            ExperimentConfig(
                name=base.name,
                experiment_dir=override_dir,
                evidence_doc=evidence_doc,
                opportunity_field=base.opportunity_field,
                expected_metrics=base.expected_metrics,
                expected_app_success=base.expected_app_success,
                expected_app_failure=base.expected_app_failure,
                expected_baseline_success=base.expected_baseline_success,
                min_success_opportunity_count=base.min_success_opportunity_count,
                failure_case_id=base.failure_case_id,
                failure_markers=base.failure_markers,
            )
        ]
    return experiments


def required_readmes() -> list[Path]:
    return [
        Path("db/README.md"),
        Path("gaokaollm_bench/README.md"),
        Path("gaokaollm_bench/tests/README.md"),
        Path("gaokaollm_bench/tests/manual/README.md"),
        Path("gaokaollm_bench/data_gen/README.md"),
        Path("gaokaollm_bench/data_gen/README_major_probe.md"),
        Path("gaokaollm_bench/sandbox/README.md"),
        Path("gaokaollm_bench/simulator/README.md"),
        Path("gaokaollm_bench/evaluator/README.md"),
    ]


def audit_experiment(config: ExperimentConfig) -> dict[str, Any]:
    experiment_dir = config.experiment_dir
    summary_path = experiment_dir / "summary.json"
    app_report_path = experiment_dir / "reports" / f"{TARGET_APP}.jsonl"
    baseline_report_path = experiment_dir / "reports" / f"{TARGET_BASELINE}.jsonl"
    checks: list[Check] = []

    required_paths = [
        config.evidence_doc,
        summary_path,
        app_report_path,
        baseline_report_path,
    ]
    missing_paths = [str(path) for path in required_paths if not path.exists()]
    add_check(
        checks,
        "required_artifacts_exist",
        not missing_paths,
        "experiment evidence, report, and summary artifacts exist"
        if not missing_paths
        else "missing: " + ", ".join(missing_paths),
    )

    summary = read_json(summary_path) if summary_path.exists() else {}
    app_rows = read_jsonl(app_report_path) if app_report_path.exists() else []
    baseline_rows = (
        read_jsonl(baseline_report_path) if baseline_report_path.exists() else []
    )
    app_by_case = rows_by_case(app_rows)
    baseline_by_case = rows_by_case(baseline_rows)

    for target, expected_metrics in config.expected_metrics.items():
        actual_metrics = (summary.get("targets") or {}).get(target, {})
        mismatches = [
            f"{key}: expected {expected}, got {actual_metrics.get(key)}"
            for key, expected in expected_metrics.items()
            if not metric_matches(actual_metrics.get(key), expected)
        ]
        add_check(
            checks,
            f"{target}_metrics_match_summary_claim",
            not mismatches,
            "metrics match expected thesis claim"
            if not mismatches
            else "; ".join(mismatches),
        )

    app_success = sum(1 for row in app_rows if row.get("elicitation_success") is True)
    app_failure = sum(1 for row in app_rows if row.get("elicitation_success") is False)
    baseline_success = sum(
        1 for row in baseline_rows if row.get("elicitation_success") is True
    )
    same_case_ids = set(app_by_case) == set(baseline_by_case)
    add_check(
        checks,
        "case_coverage_and_outcomes",
        len(app_rows) == 10
        and len(baseline_rows) == 10
        and app_success == config.expected_app_success
        and app_failure == config.expected_app_failure
        and baseline_success == config.expected_baseline_success
        and same_case_ids,
        (
            f"app rows={len(app_rows)}, app success={app_success}, "
            f"app failure={app_failure}, baseline success={baseline_success}, "
            f"same case ids={same_case_ids}"
        ),
    )

    missing_transcripts: list[str] = []
    evidence_failures: list[str] = []
    insufficient_candidate_cases: list[str] = []
    for case_id, row in app_by_case.items():
        path = resolve_transcript_path(
            str(row.get("transcript_path", "")), experiment_dir, TARGET_APP
        )
        if not path.exists():
            missing_transcripts.append(f"{TARGET_APP}:{case_id}")
            continue
        transcript = load_transcript(path)
        if row.get("elicitation_success") is True:
            if not has_agent_evidence(transcript, config.opportunity_field):
                evidence_failures.append(case_id)
            candidate_count = max_opportunity_count(
                transcript, config.opportunity_field
            )
            if candidate_count < config.min_success_opportunity_count:
                insufficient_candidate_cases.append(f"{case_id}({candidate_count})")

    baseline_forbidden_cases: list[str] = []
    for case_id, row in baseline_by_case.items():
        path = resolve_transcript_path(
            str(row.get("transcript_path", "")), experiment_dir, TARGET_BASELINE
        )
        if not path.exists():
            missing_transcripts.append(f"{TARGET_BASELINE}:{case_id}")
            continue
        transcript = load_transcript(path)
        if has_baseline_opportunity(transcript, config.opportunity_field):
            baseline_forbidden_cases.append(case_id)

    add_check(
        checks,
        "transcripts_exist",
        not missing_transcripts,
        "all report transcript paths resolve"
        if not missing_transcripts
        else "missing transcripts: " + ", ".join(missing_transcripts),
    )
    add_check(
        checks,
        f"successful_app_cases_have_{config.opportunity_field}_evidence",
        not evidence_failures,
        (
            "all successful app_pareto cases expose "
            f"{config.opportunity_field} or recommended_schools"
        )
        if not evidence_failures
        else "missing evidence: " + ", ".join(evidence_failures),
    )
    if config.min_success_opportunity_count:
        add_check(
            checks,
            f"successful_app_cases_have_min_{config.opportunity_field}_candidates",
            not insufficient_candidate_cases,
            (
                "all successful app_pareto cases expose at least "
                f"{config.min_success_opportunity_count} {config.opportunity_field} candidates"
            )
            if not insufficient_candidate_cases
            else "insufficient candidates: " + ", ".join(insufficient_candidate_cases),
        )
    add_check(
        checks,
        f"baseline_has_no_{config.opportunity_field}",
        not baseline_forbidden_cases,
        f"hard_constraint transcripts do not expose {config.opportunity_field}"
        if not baseline_forbidden_cases
        else (
            f"baseline {config.opportunity_field} present: "
            + ", ".join(baseline_forbidden_cases)
        ),
    )

    evidence_text = (
        config.evidence_doc.read_text(encoding="utf-8")
        if config.evidence_doc.exists()
        else ""
    )
    if config.failure_case_id:
        failure_row = app_by_case.get(config.failure_case_id)
        failure_documented = (
            failure_row is not None
            and failure_row.get("elicitation_success") is False
            and config.failure_case_id in evidence_text
            and all(marker in evidence_text for marker in config.failure_markers)
        )
        add_check(
            checks,
            "known_failure_case_documented",
            failure_documented,
            f"{config.failure_case_id} is explicitly documented as the non-success case"
            if failure_documented
            else f"{config.failure_case_id} failure documentation is incomplete",
        )

    hash_paths = [
        summary_path,
        app_report_path,
        baseline_report_path,
        config.evidence_doc,
    ]
    for row in app_rows + baseline_rows:
        transcript_path = resolve_transcript_path(
            str(row.get("transcript_path", "")),
            experiment_dir,
            str(row.get("target", "")),
        )
        if transcript_path.exists():
            hash_paths.append(transcript_path)
    file_hashes = {
        str(path): sha256_file(path)
        for path in sorted(set(hash_paths), key=lambda item: str(item))
        if path.exists()
    }

    case_rows = []
    for case_id in sorted(app_by_case):
        app_row = app_by_case[case_id]
        baseline_row = baseline_by_case.get(case_id, {})
        case_rows.append(
            {
                "case_id": case_id,
                "app_success": app_row.get("elicitation_success"),
                "app_turns": app_row.get("turns"),
                "app_pareto_gain": app_row.get("pareto_gain"),
                "app_hallucination_rate": app_row.get("hallucination_rate"),
                "baseline_success": baseline_row.get("elicitation_success"),
                "baseline_turns": baseline_row.get("turns"),
            }
        )

    return {
        "name": config.name,
        "experiment_dir": str(config.experiment_dir),
        "opportunity_field": config.opportunity_field,
        "overall_passed": all(check.passed for check in checks),
        "checks": [check.to_dict() for check in checks],
        "summary_metrics": summary.get("targets", {}),
        "case_rows": case_rows,
        "file_hashes_sha256": file_hashes,
    }


def audit(args: argparse.Namespace) -> dict[str, Any]:
    output_json = Path(args.output_json)
    output_md = Path(args.output_md)
    thesis_docs = (
        [Path(path) for path in args.thesis_doc]
        if args.thesis_doc
        else DEFAULT_THESIS_DOCS
    )
    experiments = selected_experiments(args)

    checks: list[Check] = []
    required_docs = [*required_readmes(), *thesis_docs]
    missing_docs = [str(path) for path in required_docs if not path.exists()]
    add_check(
        checks,
        "required_global_docs_exist",
        not missing_docs,
        "required README and thesis docs exist"
        if not missing_docs
        else "missing: " + ", ".join(missing_docs),
    )

    combined_text_parts = [
        path.read_text(encoding="utf-8") for path in thesis_docs if path.exists()
    ]
    combined_text_parts.extend(
        experiment.evidence_doc.read_text(encoding="utf-8")
        for experiment in experiments
        if experiment.evidence_doc.exists()
    )
    combined_text = "\n".join(combined_text_parts)
    leakage_terms_present = all(
        term in combined_text
        for term in ["不读取", "implicit_flexibilities", "volunteer_set"]
    )
    add_check(
        checks,
        "hidden_persona_leakage_boundary_documented",
        leakage_terms_present,
        "docs state Agent does not read hidden persona fields"
        if leakage_terms_present
        else "docs must mention 不读取, implicit_flexibilities, and volunteer_set",
    )

    pytest_recorded = "79 passed, 9 skipped, 1 warning" in combined_text
    add_check(
        checks,
        "recorded_pytest_result_present",
        pytest_recorded,
        "thesis docs record: 79 passed, 9 skipped, 1 warning"
        if pytest_recorded
        else "thesis docs do not record the expected pytest result",
    )

    experiment_reports = [audit_experiment(experiment) for experiment in experiments]
    global_hash_paths = thesis_docs
    global_file_hashes = {
        str(path): sha256_file(path)
        for path in sorted(set(global_hash_paths), key=lambda item: str(item))
        if path.exists()
    }

    report = {
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "experiments": experiment_reports,
        "overall_passed": all(check.passed for check in checks)
        and all(experiment["overall_passed"] for experiment in experiment_reports),
        "checks": [check.to_dict() for check in checks],
        "file_hashes_sha256": global_file_hashes,
        "outputs": {
            "json": str(output_json),
            "markdown": str(output_md),
        },
    }
    return report


def append_checks(lines: list[str], checks: list[dict[str, Any]]) -> None:
    lines.extend(["", "| Check | Status | Detail |", "|---|---|---|"])
    for check in checks:
        status = "PASS" if check["passed"] else "FAIL"
        detail = str(check["detail"]).replace("|", "/")
        lines.append(f"| `{check['name']}` | {status} | {detail} |")


def append_metrics(lines: list[str], metrics_by_target: dict[str, Any]) -> None:
    lines.extend(
        [
            "",
            "| Target | Cases | Success | Elicitation Success | "
            "Mean Pareto Gain | Mean Hallucination | Avg Turns |",
            "|---|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for target, metrics in metrics_by_target.items():
        lines.append(
            "| "
            + " | ".join(
                [
                    f"`{target}`",
                    str(metrics.get("cases")),
                    str(metrics.get("success_count")),
                    f"{float(metrics.get('elicitation_success_rate', 0)):.3f}",
                    f"{float(metrics.get('mean_pareto_gain', 0)):.3f}",
                    f"{float(metrics.get('mean_hallucination_rate', 0)):.3f}",
                    f"{float(metrics.get('avg_turns', 0)):.2f}",
                ]
            )
            + " |"
        )


def append_case_rows(lines: list[str], case_rows: list[dict[str, Any]]) -> None:
    lines.extend(
        [
            "",
            "| Case | app_pareto | App Turns | App Gain | App Halluc. | "
            "hard_constraint | Baseline Turns |",
            "|---|---|---:|---:|---:|---|---:|",
        ]
    )
    for row in case_rows:
        lines.append(
            "| "
            + " | ".join(
                [
                    f"`{row['case_id']}`",
                    str(row["app_success"]).lower(),
                    str(row["app_turns"]),
                    str(row["app_pareto_gain"]),
                    f"{float(row['app_hallucination_rate']):.3f}",
                    str(row["baseline_success"]).lower(),
                    str(row["baseline_turns"]),
                ]
            )
            + " |"
        )


def write_markdown(path: Path, report: dict[str, Any]) -> None:
    experiment_names = [experiment["name"] for experiment in report["experiments"]]
    lines = [
        "# Thesis Artifact Audit",
        "",
        f"- Created at: `{report['created_at']}`",
        f"- Experiments: `{', '.join(experiment_names)}`",
        f"- Overall: `{'PASS' if report['overall_passed'] else 'FAIL'}`",
        "",
        "## Global Checks",
    ]
    append_checks(lines, report["checks"])

    for experiment in report["experiments"]:
        lines.extend(
            [
                "",
                f"## Experiment: `{experiment['name']}`",
                "",
                f"- Experiment dir: `{experiment['experiment_dir']}`",
                f"- Opportunity field: `{experiment['opportunity_field']}`",
                f"- Overall: `{'PASS' if experiment['overall_passed'] else 'FAIL'}`",
                "",
                "### Checks",
            ]
        )
        append_checks(lines, experiment["checks"])
        lines.extend(["", "### Metrics"])
        append_metrics(lines, experiment["summary_metrics"])
        lines.extend(["", "### Case Coverage"])
        append_case_rows(lines, experiment["case_rows"])

    lines.extend(["", "## SHA256", "", "| File | SHA256 |", "|---|---|"])
    combined_hashes: dict[str, str] = dict(report["file_hashes_sha256"])
    for experiment in report["experiments"]:
        combined_hashes.update(experiment["file_hashes_sha256"])
    for file_path, digest in sorted(combined_hashes.items()):
        lines.append(f"| `{file_path}` | `{digest}` |")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    args = parse_args()
    output_json = Path(args.output_json)
    output_md = Path(args.output_md)
    report = audit(args)

    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    write_markdown(output_md, report)

    print(f"Wrote {output_json}")
    print(f"Wrote {output_md}")
    if not report["overall_passed"]:
        failed = [check["name"] for check in report["checks"] if not check["passed"]]
        for experiment in report["experiments"]:
            failed.extend(
                f"{experiment['name']}:{check['name']}"
                for check in experiment["checks"]
                if not check["passed"]
            )
        raise SystemExit("Audit failed: " + ", ".join(failed))
    print("Audit passed.")


if __name__ == "__main__":
    main()
