import csv
import json
import math
from pathlib import Path
from typing import Any

from app.evaluation.schemas import IcebergProfile


PREFERENCE_KEYS = ("school", "major", "tuition", "quality", "geo", "risk")
RESULTS_DIR = Path(__file__).parent / "results"
CLASSIFICATION_FIELDS = (
    "profile_id",
    "ablation_mode",
    "repeat",
    "source",
    "precision",
    "recall",
    "f1",
    "gold_dims",
    "pred_dims",
    "weights",
    "status",
    "error_message",
)
REFERENCE_SOURCE = "reference_baseline"
AGENT_SOURCE = "agent_ablation"
INITIAL_QUERY_BASELINE = "initial_query_llm"
RANDOM_BASELINE = "random_dirichlet_expected"


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return default
    return numeric if math.isfinite(numeric) else default


def _json_dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def _json_loads_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if not isinstance(value, str) or not value.strip():
        return {}
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _json_loads_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value]
    if not isinstance(value, str) or not value.strip():
        return []
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return []
    if isinstance(parsed, list):
        return [str(item) for item in parsed]
    return []


def _ranked_dimensions(weights: dict[str, Any]) -> list[str]:
    values = {key: _safe_float(weights.get(key, 0.0)) for key in PREFERENCE_KEYS}
    return sorted(
        PREFERENCE_KEYS,
        key=lambda key: (-values[key], PREFERENCE_KEYS.index(key)),
    )


def gold_dimensions(
    profile: IcebergProfile,
    threshold: float = 0.35,
) -> tuple[str, ...]:
    """Return the hidden bottom-line dimension set for one Iceberg profile."""
    weights = profile.ground_truth_weights or {}
    above_threshold = [
        key for key in PREFERENCE_KEYS if _safe_float(weights.get(key)) >= threshold
    ]
    if above_threshold:
        return tuple(
            sorted(
                above_threshold,
                key=lambda key: (
                    -_safe_float(weights.get(key)),
                    PREFERENCE_KEYS.index(key),
                ),
            )
        )
    ranked = _ranked_dimensions(weights)
    return (ranked[0],) if ranked else ()


def predicted_dimensions(weights: dict[str, Any], k: int) -> tuple[str, ...]:
    """Return Top-k dimensions from inferred weights."""
    if k <= 0:
        return ()
    return tuple(_ranked_dimensions(weights)[: min(k, len(PREFERENCE_KEYS))])


def compute_prf(
    weights: dict[str, Any],
    profile: IcebergProfile,
    threshold: float = 0.35,
) -> dict[str, Any]:
    gold = gold_dimensions(profile, threshold=threshold)
    pred = predicted_dimensions(weights, len(gold))
    gold_set = set(gold)
    pred_set = set(pred)
    overlap = len(gold_set & pred_set)
    precision = overlap / len(pred_set) if pred_set else 0.0
    recall = overlap / len(gold_set) if gold_set else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "gold_dims": gold,
        "pred_dims": pred,
    }


def classification_row(
    profile: IcebergProfile,
    ablation_mode: str,
    repeat: int | str,
    source: str,
    weights: dict[str, Any] | None,
    *,
    status: str = "ok",
    error_message: str = "",
) -> dict[str, Any]:
    safe_weights = dict(weights or {})
    if status == "ok":
        metrics = compute_prf(safe_weights, profile)
    else:
        metrics = {
            "precision": 0.0,
            "recall": 0.0,
            "f1": 0.0,
            "gold_dims": gold_dimensions(profile),
            "pred_dims": (),
        }
    return {
        "profile_id": profile.profile_id,
        "ablation_mode": ablation_mode,
        "repeat": repeat,
        "source": source,
        "precision": float(metrics["precision"]),
        "recall": float(metrics["recall"]),
        "f1": float(metrics["f1"]),
        "gold_dims": _json_dumps(list(metrics["gold_dims"])),
        "pred_dims": _json_dumps(list(metrics["pred_dims"])),
        "weights": _json_dumps(safe_weights),
        "status": status,
        "error_message": error_message,
    }


def classification_row_from_metrics(
    profile: IcebergProfile,
    ablation_mode: str,
    repeat: int | str,
    source: str,
    weights: dict[str, Any] | None,
    metrics: dict[str, Any],
    *,
    status: str = "ok",
    error_message: str = "",
) -> dict[str, Any]:
    safe_weights = dict(weights or {})
    gold = metrics.get("gold_dims") or gold_dimensions(profile)
    pred = metrics.get("pred_dims") or ()
    return {
        "profile_id": profile.profile_id,
        "ablation_mode": ablation_mode,
        "repeat": repeat,
        "source": source,
        "precision": float(metrics.get("precision", 0.0)),
        "recall": float(metrics.get("recall", 0.0)),
        "f1": float(metrics.get("f1", 0.0)),
        "gold_dims": _json_dumps(list(gold)),
        "pred_dims": _json_dumps(list(pred)),
        "weights": _json_dumps(safe_weights),
        "status": status,
        "error_message": error_message,
    }


def classification_rows_from_reference_rows(
    reference_rows: list[dict[str, Any]],
    dataset: list[IcebergProfile],
) -> list[dict[str, Any]]:
    profile_map = {profile.profile_id: profile for profile in dataset}
    rows: list[dict[str, Any]] = []
    for row in reference_rows:
        baseline_type = str(row.get("baseline_type") or "")
        if not baseline_type:
            continue
        profile_id = str(row.get("profile_id") or "")
        if profile_id == "__dataset__" or profile_id not in profile_map:
            continue
        status = str(row.get("status") or "ok")
        weights = _json_loads_dict(row.get("weights", ""))
        if baseline_type == RANDOM_BASELINE:
            metrics = _random_expected_metrics(profile_map[profile_id], weights)
            rows.append(
                classification_row_from_metrics(
                    profile_map[profile_id],
                    baseline_type,
                    "",
                    REFERENCE_SOURCE,
                    weights,
                    metrics,
                    status=status,
                    error_message=str(row.get("error_message") or ""),
                )
            )
            continue
        rows.append(
            classification_row(
                profile_map[profile_id],
                baseline_type,
                "",
                REFERENCE_SOURCE,
                weights,
                status=status,
                error_message=str(row.get("error_message") or ""),
            )
        )
    return rows


def _random_expected_metrics(
    profile: IcebergProfile,
    metadata: dict[str, Any],
) -> dict[str, Any]:
    """Return stored expected random-baseline PRF metrics for one profile."""

    expected_f1 = _safe_float(metadata.get("expected_f1"), 0.0)
    gold = gold_dimensions(profile)
    return {
        "precision": expected_f1,
        "recall": expected_f1,
        "f1": expected_f1,
        "gold_dims": gold,
        "pred_dims": (),
    }


def read_classification_metrics(path: str | Path) -> list[dict[str, Any]]:
    metric_path = Path(path)
    if not metric_path.exists():
        return []
    with metric_path.open("r", encoding="utf-8", newline="") as file:
        return list(csv.DictReader(file))


def write_classification_metrics(
    rows: list[dict[str, Any]],
    output_dir: str | Path | None = None,
) -> str:
    csv_dir = Path(output_dir) if output_dir is not None else RESULTS_DIR
    csv_dir.mkdir(parents=True, exist_ok=True)
    csv_path = csv_dir / "classification_metrics.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(CLASSIFICATION_FIELDS))
        writer.writeheader()
        writer.writerows(rows)
    return str(csv_path)


def merge_classification_metrics(
    rows: list[dict[str, Any]],
    output_dir: str | Path | None = None,
    *,
    replace_sources: tuple[str, ...] = (),
) -> str:
    csv_dir = Path(output_dir) if output_dir is not None else RESULTS_DIR
    csv_path = csv_dir / "classification_metrics.csv"
    existing = read_classification_metrics(csv_path)
    if replace_sources:
        existing = [
            row
            for row in existing
            if str(row.get("source") or "") not in replace_sources
        ]
    return write_classification_metrics([*existing, *rows], csv_dir)


def parse_dims(value: Any) -> tuple[str, ...]:
    return tuple(_json_loads_list(value))


def parse_weights(value: Any) -> dict[str, Any]:
    return _json_loads_dict(value)
