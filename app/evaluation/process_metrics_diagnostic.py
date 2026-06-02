"""Build process-diagnostic tables from unified benchmark metrics.

This script is intentionally offline: it reads an existing ablation metrics CSV
and transcript JSON files, then rewrites process indicators with explicit
validity/status columns. In particular, a no-tracker run with frozen belief
state is marked as not applicable for BOI/EUDR instead of being treated as a
perfectly stable zero.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable


DIMENSIONS = ("school", "major", "tuition", "quality", "geo", "risk")
DEFAULT_INPUT = Path(
    "app/evaluation/results/unified_micro_oracle_v3_ablation_results.csv"
)
DEFAULT_CASE_OUTPUT = Path("app/evaluation/results/process_metrics_by_case.csv")
DEFAULT_MODE_OUTPUT = Path("app/evaluation/results/process_metrics_by_mode.csv")
DEFAULT_SUMMARY_OUTPUT = Path("app/evaluation/results/process_metrics_summary.md")
RECOMMENDATION_TOP_N = 3
RECOMMENDATION_TOP_NS = (1, 3, 5, 10)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames: list[str] = []
    seen: set[str] = set()
    for row in rows:
        for key in row:
            if key not in seen:
                seen.add(key)
                fieldnames.append(key)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    return number if math.isfinite(number) else default


def optional_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"true", "1", "yes", "y"}


def mean(values: Iterable[float]) -> float:
    items = [value for value in values if math.isfinite(value)]
    return sum(items) / len(items) if items else 0.0


def std(values: Iterable[float]) -> float:
    items = [value for value in values if math.isfinite(value)]
    if len(items) <= 1:
        return 0.0
    avg = mean(items)
    return math.sqrt(sum((value - avg) ** 2 for value in items) / (len(items) - 1))


def read_transcript(path_value: str) -> dict[str, Any] | None:
    if not path_value:
        return None
    path = Path(path_value)
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def target_turns(transcript: dict[str, Any] | None) -> list[dict[str, Any]]:
    return [
        turn
        for turn in list((transcript or {}).get("turns") or [])
        if str(turn.get("role")) == "target_agent"
    ]


def numeric_map(value: Any) -> dict[str, float]:
    if not isinstance(value, dict):
        return {}
    output: dict[str, float] = {}
    for key, raw in value.items():
        try:
            output[str(key)] = float(raw)
        except (TypeError, ValueError):
            continue
    return output


def dimension_delta(a: dict[str, float], b: dict[str, float]) -> float:
    return sum(
        abs(float(a.get(dim, 0.0)) - float(b.get(dim, 0.0))) for dim in DIMENSIONS
    )


def belief_observations(transcript: dict[str, Any] | None) -> list[dict[str, Any]]:
    observations: list[dict[str, Any]] = []
    for turn in target_turns(transcript):
        state = turn.get("internal_state") or {}
        weights = numeric_map(state.get("implicit_weights"))
        variance = numeric_map(state.get("weight_variance"))
        if weights or variance:
            observations.append(
                {
                    "turn_id": turn.get("turn_id"),
                    "weights": weights,
                    "variance": variance,
                }
            )
    return observations


def state_update_count(observations: list[dict[str, Any]]) -> int:
    count = 0
    for previous, current in zip(observations, observations[1:]):
        weight_delta = dimension_delta(
            previous.get("weights") or {}, current.get("weights") or {}
        )
        var_delta = dimension_delta(
            previous.get("variance") or {}, current.get("variance") or {}
        )
        if weight_delta > 1e-9 or var_delta > 1e-9:
            count += 1
    return count


def state_status(mode: str, observations: list[dict[str, Any]], updates: int) -> str:
    if len(observations) < 2:
        return "single_turn_no_update_opportunity"
    if updates == 0:
        if mode == "no_tracker":
            return "frozen_state_tracker_disabled"
        return "frozen_state_no_observed_update"
    return "updated"


def effective_msti(row: dict[str, str]) -> float:
    observed_count = safe_float(row.get("msti_observed_count"), 0.0)
    if observed_count > 0:
        return safe_float(row.get("msti_mean"), 0.0)
    return safe_float(row.get("expected_msti"), safe_float(row.get("msti_mean"), 0.0))


def enrich_case(row: dict[str, str]) -> dict[str, Any]:
    transcript = read_transcript(row.get("transcript_path", ""))
    observations = belief_observations(transcript)
    updates = state_update_count(observations)
    mode = str(row.get("ablation_mode") or "")
    status = state_status(mode, observations, updates)
    kbv_opportunities = int(safe_float(row.get("kbv_opportunities"), 0.0))
    boi_raw = optional_float(row.get("boi"))
    eudr_raw = optional_float(row.get("eudr_slope"))
    boi_valid = status == "updated" and boi_raw is not None
    eudr_valid = status == "updated" and eudr_raw is not None
    kbv_valid = kbv_opportunities > 0
    target_evidence = truthy(row.get("target_supplied_acceptable_evidence"))
    acceptable_hit = truthy(row.get("acceptable_candidate_hit"))
    ecdr = 1.0 if (target_evidence or acceptable_hit) else 0.0
    output: dict[str, Any] = {
        "model": row.get("model", ""),
        "target": row.get("target", ""),
        "ablation_mode": mode,
        "case_id": row.get("case_id", ""),
        "diagnostic_axis": row.get("diagnostic_axis", ""),
        "status": row.get("status", ""),
        "target_turn_count": int(safe_float(row.get("target_turn_count"), 0.0)),
        "state_observation_count": len(observations),
        "state_update_count": updates,
        "state_status": status,
        "eudr_slope_raw": eudr_raw if eudr_raw is not None else "",
        "eudr_ratio_raw": row.get("eudr_ratio", ""),
        "eudr_valid": eudr_valid,
        "eudr_effective": eudr_raw if eudr_valid else "",
        "pcg_first_valid_probe_turn": row.get("first_valid_probe_turn", ""),
        "pcg_valid_probe_hit_rate": safe_float(row.get("valid_probe_hit_rate"), 0.0),
        "pcg_valid_probe_coverage": safe_float(row.get("valid_probe_coverage"), 0.0),
        "msti_effective": effective_msti(row),
        "msti_source": "observed_delta_phi"
        if safe_float(row.get("msti_observed_count"), 0.0) > 0
        else "expected_msti",
        "ctr_cardinal_trigger_rate": safe_float(row.get("cardinal_trigger_rate"), 0.0),
        "ctr_opportunities": int(safe_float(row.get("ctr_opportunities"), 0.0)),
        "boi_raw": boi_raw if boi_raw is not None else "",
        "boi_valid": boi_valid,
        "boi_effective": boi_raw if boi_valid else "",
        "kbv_opportunities": kbv_opportunities,
        "kbv_violations": int(safe_float(row.get("kbv_violations"), 0.0)),
        "kbv_status": "measured" if kbv_valid else "no_kbv_opportunity",
        "kbv_rate_effective": safe_float(row.get("kbv_rate"), 0.0) if kbv_valid else "",
        "ecdr_candidate_evidence_rate": ecdr,
        "acceptable_candidate_hit": acceptable_hit,
        "target_supplied_acceptable_evidence": target_evidence,
        "elicitation_success_aux": truthy(row.get("elicitation_success")),
        "mae": safe_float(row.get("mae"), 0.0),
        "topk_f1": safe_float(row.get("topk_f1"), 0.0),
        "notes": "",
    }
    for limit in RECOMMENDATION_TOP_NS:
        output[f"recommendation_f1_at_{limit}"] = safe_float(
            row.get(f"recommendation_f1_at_{limit}"),
            0.0,
        )
    if not boi_valid:
        output["notes"] = _append_note(output["notes"], f"BOI {status}")
    if not eudr_valid:
        output["notes"] = _append_note(output["notes"], f"EUDR {status}")
    if not kbv_valid:
        output["notes"] = _append_note(output["notes"], "KBV no opportunity")
    return output


def _append_note(existing: str, note: str) -> str:
    return f"{existing}; {note}" if existing else note


def aggregate_by_mode(case_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in case_rows:
        grouped[str(row.get("ablation_mode") or "")].append(row)
    output: list[dict[str, Any]] = []
    for mode in ("full", "no_ucb", "no_tracker"):
        rows = grouped.get(mode, [])
        if not rows:
            continue
        boi_values = [
            float(row["boi_effective"])
            for row in rows
            if row.get("boi_effective") != ""
        ]
        eudr_values = [
            float(row["eudr_effective"])
            for row in rows
            if row.get("eudr_effective") != ""
        ]
        kbv_values = [
            float(row["kbv_rate_effective"])
            for row in rows
            if row.get("kbv_rate_effective") != ""
        ]
        item: dict[str, Any] = {
            "ablation_mode": mode,
            "n": len(rows),
            "completed": sum(1 for row in rows if row.get("status") == "ok"),
            "state_update_count_mean": mean(
                float(row["state_update_count"]) for row in rows
            ),
            "state_update_count_std": std(
                float(row["state_update_count"]) for row in rows
            ),
            "frozen_state_count": sum(
                1 for row in rows if "frozen_state" in str(row.get("state_status"))
            ),
            "eudr_valid_n": len(eudr_values),
            "eudr_slope_mean": mean(eudr_values),
            "eudr_slope_std": std(eudr_values),
            "pcg_hit_rate_mean": mean(
                float(row["pcg_valid_probe_hit_rate"]) for row in rows
            ),
            "pcg_hit_rate_std": std(
                float(row["pcg_valid_probe_hit_rate"]) for row in rows
            ),
            "pcg_coverage_mean": mean(
                float(row["pcg_valid_probe_coverage"]) for row in rows
            ),
            "msti_mean": mean(float(row["msti_effective"]) for row in rows),
            "msti_std": std(float(row["msti_effective"]) for row in rows),
            "ctr_mean": mean(float(row["ctr_cardinal_trigger_rate"]) for row in rows),
            "ctr_std": std(float(row["ctr_cardinal_trigger_rate"]) for row in rows),
            "boi_valid_n": len(boi_values),
            "boi_mean": mean(boi_values),
            "boi_std": std(boi_values),
            "kbv_valid_n": len(kbv_values),
            "kbv_rate_mean": mean(kbv_values),
            "kbv_rate_std": std(kbv_values),
            "ecdr_mean": mean(
                float(row["ecdr_candidate_evidence_rate"]) for row in rows
            ),
            "ecdr_std": std(float(row["ecdr_candidate_evidence_rate"]) for row in rows),
            "aux_elicitation_success_rate": mean(
                1.0 if row.get("elicitation_success_aux") else 0.0 for row in rows
            ),
            "mae_mean": mean(float(row["mae"]) for row in rows),
            "mae_std": std(float(row["mae"]) for row in rows),
            "topk_f1_mean": mean(float(row["topk_f1"]) for row in rows),
            "topk_f1_std": std(float(row["topk_f1"]) for row in rows),
        }
        for limit in RECOMMENDATION_TOP_NS:
            item[f"recommendation_f1_at_{limit}_mean"] = mean(
                float(row[f"recommendation_f1_at_{limit}"]) for row in rows
            )
            item[f"recommendation_f1_at_{limit}_std"] = std(
                float(row[f"recommendation_f1_at_{limit}"]) for row in rows
            )
        output.append(item)
    return output


def fmt(value: Any) -> str:
    if value == "":
        return ""
    if isinstance(value, float):
        return f"{value:.3f}"
    return str(value)


def markdown_table(rows: list[dict[str, Any]], columns: list[str]) -> list[str]:
    lines = [
        "| " + " | ".join(columns) + " |",
        "| " + " | ".join("---" for _ in columns) + " |",
    ]
    for row in rows:
        lines.append(
            "| " + " | ".join(fmt(row.get(column, "")) for column in columns) + " |"
        )
    return lines


def write_summary(
    path: Path, by_mode: list[dict[str, Any]], by_case: list[dict[str, Any]]
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    mode_map = {row["ablation_mode"]: row for row in by_mode}
    full = mode_map.get("full", {})
    no_ucb = mode_map.get("no_ucb", {})
    no_tracker = mode_map.get("no_tracker", {})
    lines: list[str] = [
        "# Process Metrics Diagnostic Summary",
        "",
        "This offline summary treats candidate discovery as a negotiator sub-metric (ECDR), not as the main end-to-end score.",
        "",
        "## By Mode",
        "",
        *markdown_table(
            by_mode,
            [
                "ablation_mode",
                "n",
                "state_update_count_mean",
                "eudr_valid_n",
                "eudr_slope_mean",
                "pcg_hit_rate_mean",
                "pcg_coverage_mean",
                "msti_mean",
                "ctr_mean",
                "boi_valid_n",
                "boi_mean",
                "kbv_valid_n",
                "kbv_rate_mean",
                "ecdr_mean",
                "mae_mean",
                "recommendation_f1_at_1_mean",
                "recommendation_f1_at_3_mean",
                "recommendation_f1_at_5_mean",
                "recommendation_f1_at_10_mean",
            ],
        ),
        "",
        "## Interpretation Notes",
        "",
        (
            f"- UCB planner: full PCG hit rate={fmt(full.get('pcg_hit_rate_mean', ''))}, "
            f"no-UCB={fmt(no_ucb.get('pcg_hit_rate_mean', ''))}; candidate discovery ECDR is "
            f"{fmt(full.get('ecdr_mean', ''))} vs {fmt(no_ucb.get('ecdr_mean', ''))}."
        ),
        (
            f"- Tracker: full has MAE={fmt(full.get('mae_mean', ''))}, "
            f"F1@1/3/5/10={fmt(full.get('recommendation_f1_at_1_mean', ''))}/"
            f"{fmt(full.get('recommendation_f1_at_3_mean', ''))}/"
            f"{fmt(full.get('recommendation_f1_at_5_mean', ''))}/"
            f"{fmt(full.get('recommendation_f1_at_10_mean', ''))}; "
            f"no-tracker has MAE={fmt(no_tracker.get('mae_mean', ''))}, "
            f"F1@1/3/5/10={fmt(no_tracker.get('recommendation_f1_at_1_mean', ''))}/"
            f"{fmt(no_tracker.get('recommendation_f1_at_3_mean', ''))}/"
            f"{fmt(no_tracker.get('recommendation_f1_at_5_mean', ''))}/"
            f"{fmt(no_tracker.get('recommendation_f1_at_10_mean', ''))}."
        ),
        (
            f"- BOI/EUDR validity: no-tracker frozen-state count={fmt(no_tracker.get('frozen_state_count', ''))}; "
            "frozen zeros are marked not applicable and excluded from BOI/EUDR means."
        ),
        "- KBV: rates are reported only when a rejection creates later violation opportunities; otherwise the case is marked no_kbv_opportunity.",
        "- ECDR/elicitation success are auxiliary evidence-negotiation outcomes, not the primary tracker metric.",
        "",
        "## Case-Level Failures",
        "",
    ]
    failed = [
        row
        for row in by_case
        if row.get("ablation_mode") == "full"
        and not row.get("acceptable_candidate_hit")
    ]
    if failed:
        lines.extend(
            markdown_table(
                failed,
                [
                    "case_id",
                    "diagnostic_axis",
                    "pcg_first_valid_probe_turn",
                    "pcg_valid_probe_hit_rate",
                    "state_status",
                    "notes",
                ],
            )
        )
    else:
        lines.append("- No full-mode candidate-discovery failures.")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--case-output", type=Path, default=DEFAULT_CASE_OUTPUT)
    parser.add_argument("--mode-output", type=Path, default=DEFAULT_MODE_OUTPUT)
    parser.add_argument("--summary", type=Path, default=DEFAULT_SUMMARY_OUTPUT)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    rows = read_csv(args.input)
    by_case = [enrich_case(row) for row in rows]
    by_mode = aggregate_by_mode(by_case)
    write_csv(args.case_output, by_case)
    write_csv(args.mode_output, by_mode)
    write_summary(args.summary, by_mode, by_case)
    print(f"[process_metrics] wrote {args.case_output}")
    print(f"[process_metrics] wrote {args.mode_output}")
    print(f"[process_metrics] wrote {args.summary}")


if __name__ == "__main__":
    main()
