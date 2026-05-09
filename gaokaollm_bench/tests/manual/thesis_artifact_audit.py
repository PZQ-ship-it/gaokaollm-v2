"""Audit thesis-facing benchmark artifacts without rerunning experiments."""

from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


DEFAULT_EXPERIMENT_DIR = Path("gaokaollm_bench/outputs/agent_benchmark_major_geo_v1")
DEFAULT_THESIS_DOC = Path(
    "gaokaollm_bench/outputs/thesis_agent_benchmark_contribution.md"
)
DEFAULT_EVIDENCE_DOC = Path(
    "gaokaollm_bench/outputs/agent_benchmark_major_geo_v1_evidence.md"
)
DEFAULT_OUTPUT_JSON = Path("gaokaollm_bench/outputs/thesis_artifact_audit.json")
DEFAULT_OUTPUT_MD = Path("gaokaollm_bench/outputs/thesis_artifact_audit.md")

TARGET_APP = "app_pareto"
TARGET_BASELINE = "hard_constraint"
FAILURE_CASE_ID = "real-db-set-浙江-569-009"

EXPECTED_METRICS = {
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
}


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
    parser.add_argument("--experiment-dir", default=str(DEFAULT_EXPERIMENT_DIR))
    parser.add_argument("--thesis-doc", default=str(DEFAULT_THESIS_DOC))
    parser.add_argument("--evidence-doc", default=str(DEFAULT_EVIDENCE_DOC))
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


def has_agent_evidence(transcript: dict[str, Any]) -> bool:
    for state in target_internal_states(transcript):
        opportunities = state.get("pareto_opportunities") or {}
        major_geo = opportunities.get("major_geo_relax") or state.get("major_geo_relax")
        recommended = state.get("recommended_schools")
        if major_geo or recommended:
            return True
    return False


def has_baseline_major_geo(transcript: dict[str, Any]) -> bool:
    for state in target_internal_states(transcript):
        opportunities = state.get("pareto_opportunities") or {}
        if opportunities.get("major_geo_relax") or state.get("major_geo_relax"):
            return True
    return False


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


def audit(args: argparse.Namespace) -> dict[str, Any]:
    experiment_dir = Path(args.experiment_dir)
    thesis_doc = Path(args.thesis_doc)
    evidence_doc = Path(args.evidence_doc)
    output_json = Path(args.output_json)
    output_md = Path(args.output_md)
    summary_path = experiment_dir / "summary.json"
    app_report_path = experiment_dir / "reports" / f"{TARGET_APP}.jsonl"
    baseline_report_path = experiment_dir / "reports" / f"{TARGET_BASELINE}.jsonl"

    required_docs = [
        Path("db/README.md"),
        Path("gaokaollm_bench/README.md"),
        Path("gaokaollm_bench/tests/README.md"),
        Path("gaokaollm_bench/tests/manual/README.md"),
        Path("gaokaollm_bench/data_gen/README.md"),
        Path("gaokaollm_bench/data_gen/README_major_probe.md"),
        Path("gaokaollm_bench/sandbox/README.md"),
        Path("gaokaollm_bench/simulator/README.md"),
        Path("gaokaollm_bench/evaluator/README.md"),
        thesis_doc,
        evidence_doc,
        summary_path,
        app_report_path,
        baseline_report_path,
    ]

    checks: list[Check] = []
    missing_docs = [str(path) for path in required_docs if not path.exists()]
    add_check(
        checks,
        "required_artifacts_exist",
        not missing_docs,
        "all required README, report, summary, and thesis docs exist"
        if not missing_docs
        else "missing: " + ", ".join(missing_docs),
    )

    summary = read_json(summary_path) if summary_path.exists() else {}
    app_rows = read_jsonl(app_report_path) if app_report_path.exists() else []
    baseline_rows = (
        read_jsonl(baseline_report_path) if baseline_report_path.exists() else []
    )
    app_by_case = rows_by_case(app_rows)
    baseline_by_case = rows_by_case(baseline_rows)

    for target, expected_metrics in EXPECTED_METRICS.items():
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
        and app_success == 9
        and app_failure == 1
        and baseline_success == 0
        and same_case_ids,
        (
            f"app rows={len(app_rows)}, app success={app_success}, "
            f"app failure={app_failure}, baseline success={baseline_success}, "
            f"same case ids={same_case_ids}"
        ),
    )

    app_transcripts: dict[str, dict[str, Any]] = {}
    missing_transcripts: list[str] = []
    evidence_failures: list[str] = []
    for case_id, row in app_by_case.items():
        path = resolve_transcript_path(
            str(row.get("transcript_path", "")), experiment_dir, TARGET_APP
        )
        if not path.exists():
            missing_transcripts.append(f"{TARGET_APP}:{case_id}")
            continue
        transcript = load_transcript(path)
        app_transcripts[case_id] = transcript
        if row.get("elicitation_success") is True and not has_agent_evidence(
            transcript
        ):
            evidence_failures.append(case_id)

    baseline_major_geo_cases: list[str] = []
    for case_id, row in baseline_by_case.items():
        path = resolve_transcript_path(
            str(row.get("transcript_path", "")), experiment_dir, TARGET_BASELINE
        )
        if not path.exists():
            missing_transcripts.append(f"{TARGET_BASELINE}:{case_id}")
            continue
        transcript = load_transcript(path)
        if has_baseline_major_geo(transcript):
            baseline_major_geo_cases.append(case_id)

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
        "successful_app_cases_have_evidence",
        not evidence_failures,
        "all successful app_pareto cases expose major_geo_relax or recommended_schools"
        if not evidence_failures
        else "missing evidence: " + ", ".join(evidence_failures),
    )
    add_check(
        checks,
        "baseline_has_no_major_geo_relax",
        not baseline_major_geo_cases,
        "hard_constraint transcripts do not expose major_geo_relax"
        if not baseline_major_geo_cases
        else "baseline major_geo_relax present: " + ", ".join(baseline_major_geo_cases),
    )

    thesis_text = thesis_doc.read_text(encoding="utf-8") if thesis_doc.exists() else ""
    evidence_text = (
        evidence_doc.read_text(encoding="utf-8") if evidence_doc.exists() else ""
    )
    combined_text = thesis_text + "\n" + evidence_text
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

    failure_row = app_by_case.get(FAILURE_CASE_ID)
    failure_documented = (
        failure_row is not None
        and failure_row.get("elicitation_success") is False
        and FAILURE_CASE_ID in evidence_text
        and "唯一失败样本" in evidence_text
        and "100% 成功" in evidence_text
    )
    add_check(
        checks,
        "known_failure_case_documented",
        failure_documented,
        f"{FAILURE_CASE_ID} is explicitly documented as the non-success case"
        if failure_documented
        else f"{FAILURE_CASE_ID} failure documentation is incomplete",
    )

    pytest_recorded = "79 passed, 9 skipped, 1 warning" in thesis_text
    add_check(
        checks,
        "recorded_pytest_result_present",
        pytest_recorded,
        "thesis contribution doc records: 79 passed, 9 skipped, 1 warning"
        if pytest_recorded
        else "thesis contribution doc does not record the expected pytest result",
    )

    hash_paths = [
        summary_path,
        app_report_path,
        baseline_report_path,
        thesis_doc,
        evidence_doc,
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

    report = {
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "experiment_dir": str(experiment_dir),
        "overall_passed": all(check.passed for check in checks),
        "checks": [check.to_dict() for check in checks],
        "summary_metrics": summary.get("targets", {}),
        "case_rows": case_rows,
        "file_hashes_sha256": file_hashes,
        "outputs": {
            "json": str(output_json),
            "markdown": str(output_md),
        },
    }
    return report


def write_markdown(path: Path, report: dict[str, Any]) -> None:
    lines = [
        "# Thesis Artifact Audit",
        "",
        f"- Created at: `{report['created_at']}`",
        f"- Experiment dir: `{report['experiment_dir']}`",
        f"- Overall: `{'PASS' if report['overall_passed'] else 'FAIL'}`",
        "",
        "## Checks",
        "",
        "| Check | Status | Detail |",
        "|---|---|---|",
    ]
    for check in report["checks"]:
        status = "PASS" if check["passed"] else "FAIL"
        detail = str(check["detail"]).replace("|", "/")
        lines.append(f"| `{check['name']}` | {status} | {detail} |")

    lines.extend(
        [
            "",
            "## Metrics",
            "",
            (
                "| Target | Cases | Success | Elicitation Success | "
                "Mean Pareto Gain | Mean Hallucination | Avg Turns |"
            ),
            "|---|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for target, metrics in report["summary_metrics"].items():
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

    lines.extend(
        [
            "",
            "## Case Coverage",
            "",
            (
                "| Case | app_pareto | App Turns | App Gain | App Halluc. | "
                "hard_constraint | Baseline Turns |"
            ),
            "|---|---|---:|---:|---:|---|---:|",
        ]
    )
    for row in report["case_rows"]:
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

    lines.extend(["", "## SHA256", "", "| File | SHA256 |", "|---|---|"])
    for file_path, digest in report["file_hashes_sha256"].items():
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
        raise SystemExit("Audit failed: " + ", ".join(failed))
    print("Audit passed.")


if __name__ == "__main__":
    main()
