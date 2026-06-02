import argparse
import json
import math
import random
import re
from pathlib import Path
from typing import Any

from app.evaluation.benchmark import get_robust_evaluation_dataset
from app.evaluation.schemas import IcebergProfile


DATA_DIR = Path(__file__).parent / "data"
DEFAULT_OUTPUT = DATA_DIR / "synthetic_pressure_profiles_60.jsonl"
DEFAULT_REPORT = DATA_DIR / "synthetic_pressure_profiles_60_report.md"
PREFERENCE_KEYS = ("school", "major", "tuition", "quality", "geo", "risk")
DIMENSION_NAMES = {
    "school": "学校层次",
    "major": "专业匹配",
    "tuition": "学费预算",
    "quality": "培养质量",
    "geo": "地域偏好",
    "risk": "风险弹性",
}


VARIANTS = (
    {
        "suffix": "school_decoy",
        "score_delta": -8,
        "talk_style": "defensive_school",
        "query_tail": "我嘴上还是想优先冲学校名气，但也不想最后选得太难受。",
        "weight_shift": {"school": 0.02, "major": -0.01, "geo": -0.01},
    },
    {
        "suffix": "geo_soft",
        "score_delta": -3,
        "talk_style": "geo_softening",
        "query_tail": "地域我先说可以商量，但家里其实会反复比较通勤和距离。",
        "weight_shift": {"geo": 0.02, "quality": -0.01, "school": -0.01},
    },
    {
        "suffix": "budget_hint",
        "score_delta": 4,
        "talk_style": "budget_hint",
        "query_tail": "预算我不想一开始说死，但太高的费用会让我很犹豫。",
        "weight_shift": {"tuition": 0.02, "school": -0.01, "quality": -0.01},
    },
    {
        "suffix": "quality_hint",
        "score_delta": 9,
        "talk_style": "quality_hint",
        "query_tail": "我也会看培养质量和专业口碑，只是第一轮不太会直接说。",
        "weight_shift": {"quality": 0.02, "geo": -0.01, "tuition": -0.01},
    },
    {
        "suffix": "plain_retry",
        "score_delta": 13,
        "talk_style": "plain_rephrasing",
        "query_tail": "请先给我一个稳妥建议，我再决定哪些条件能让步。",
        "weight_shift": {
            "major": 0.01,
            "quality": 0.01,
            "risk": 0.01,
            "school": -0.01,
            "geo": -0.01,
            "tuition": -0.01,
        },
    },
)


def _score_from_query(query: str) -> int:
    match = re.search(r"(\d{3})分", query)
    if not match:
        return 610
    return int(match.group(1))


def _replace_score(query: str, score: int) -> str:
    return re.sub(r"\d{3}分", f"{score}分", query, count=1)


def _target_dimensions(weights: dict[str, float]) -> list[str]:
    targets = [key for key in PREFERENCE_KEYS if float(weights.get(key, 0.0)) >= 0.35]
    if targets:
        return sorted(
            targets, key=lambda key: (-weights[key], PREFERENCE_KEYS.index(key))
        )
    return [
        max(
            PREFERENCE_KEYS,
            key=lambda key: (float(weights.get(key, 0.0)), -PREFERENCE_KEYS.index(key)),
        )
    ]


def _profile_type(targets: list[str], profile_id: str) -> str:
    if "balanced" in profile_id:
        return "balanced"
    if len(targets) >= 2:
        return "dual_axis"
    return "single_axis"


def _normalize(weights: dict[str, float]) -> dict[str, float]:
    clipped = {key: max(0.01, float(weights.get(key, 0.0))) for key in PREFERENCE_KEYS}
    total = sum(clipped.values())
    if not math.isfinite(total) or total <= 0:
        return {key: 1.0 / len(PREFERENCE_KEYS) for key in PREFERENCE_KEYS}
    normalized = {key: value / total for key, value in clipped.items()}
    correction = 1.0 - sum(normalized.values())
    normalized[PREFERENCE_KEYS[0]] += correction
    return normalized


def _shift_weights(
    base: dict[str, float],
    shift: dict[str, float],
    rng: random.Random,
) -> dict[str, float]:
    jitter = {key: rng.uniform(-0.006, 0.006) for key in PREFERENCE_KEYS}
    updated = {
        key: float(base.get(key, 0.0)) + float(shift.get(key, 0.0)) + jitter[key]
        for key in PREFERENCE_KEYS
    }
    return _normalize(updated)


def _bottom_line_text(targets: list[str]) -> str:
    if len(targets) == 1:
        return f"合成压力画像：真实底线仍集中在{DIMENSION_NAMES[targets[0]]}。"
    names = "和".join(DIMENSION_NAMES[target] for target in targets)
    return f"合成压力画像：真实底线是{names}并重，任一维度被忽略都会触发拒绝。"


def generate_synthetic_pressure_profiles(
    *,
    size: int = 60,
    seed: int = 20260517,
) -> list[dict[str, Any]]:
    if size <= 0:
        raise ValueError("size must be positive")
    rng = random.Random(seed)
    seeds = get_robust_evaluation_dataset()
    rows: list[dict[str, Any]] = []
    index = 0
    while len(rows) < size:
        seed_profile = seeds[index % len(seeds)]
        variant = VARIANTS[(index // len(seeds)) % len(VARIANTS)]
        base_score = _score_from_query(seed_profile.explicit_query)
        score = max(400, min(680, base_score + int(variant["score_delta"])))
        weights = _shift_weights(
            seed_profile.ground_truth_weights,
            dict(variant["weight_shift"]),
            rng,
        )
        targets = _target_dimensions(weights)
        profile_id = (
            f"synthetic_pressure_{len(rows) + 1:03d}_"
            f"{seed_profile.profile_id}_{variant['suffix']}"
        )
        explicit_query = _replace_score(seed_profile.explicit_query, score)
        explicit_query = f"{explicit_query}{variant['query_tail']}"
        rows.append(
            {
                "profile_id": profile_id,
                "explicit_query": explicit_query,
                "hidden_bottom_line": _bottom_line_text(targets),
                "ground_truth_weights": weights,
                "metadata": {
                    "source": "deterministic_seed_mutation",
                    "seed_profile_id": seed_profile.profile_id,
                    "variant": variant["suffix"],
                    "talk_style": variant["talk_style"],
                    "score": score,
                    "score_band": _score_band(score),
                    "exam_province": "浙江",
                    "hidden_bottom_line_type": _profile_type(
                        targets, seed_profile.profile_id
                    ),
                    "target_dimensions": targets,
                    "is_dual_or_multi_axis": len(targets) >= 2,
                },
            }
        )
        index += 1
    return rows


def _score_band(score: int) -> str:
    if score < 560:
        return "low"
    if score < 610:
        return "mid"
    if score < 640:
        return "high"
    return "top"


def write_jsonl(rows: list[dict[str, Any]], output_path: str | Path) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as file:
        for row in rows:
            file.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
    return path


def read_synthetic_pressure_profiles(
    path: str | Path = DEFAULT_OUTPUT,
) -> list[IcebergProfile]:
    profile_path = Path(path)
    if not profile_path.exists():
        raise FileNotFoundError(
            f"Synthetic pressure dataset not found: {profile_path}. "
            "Run python -m app.evaluation.synthetic_profiles first."
        )
    profiles: list[IcebergProfile] = []
    with profile_path.open("r", encoding="utf-8") as file:
        for line in file:
            if not line.strip():
                continue
            data = json.loads(line)
            profiles.append(IcebergProfile.model_validate(data))
    return profiles


def audit_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    type_counts: dict[str, int] = {}
    style_counts: dict[str, int] = {}
    seed_counts: dict[str, int] = {}
    invalid_weight_sums: list[str] = []
    for row in rows:
        metadata = dict(row.get("metadata") or {})
        type_name = str(metadata.get("hidden_bottom_line_type") or "unknown")
        style = str(metadata.get("talk_style") or "unknown")
        seed_profile = str(metadata.get("seed_profile_id") or "unknown")
        type_counts[type_name] = type_counts.get(type_name, 0) + 1
        style_counts[style] = style_counts.get(style, 0) + 1
        seed_counts[seed_profile] = seed_counts.get(seed_profile, 0) + 1
        weights = dict(row.get("ground_truth_weights") or {})
        total = sum(float(weights.get(key, 0.0)) for key in PREFERENCE_KEYS)
        if abs(total - 1.0) > 1e-6:
            invalid_weight_sums.append(str(row.get("profile_id")))
    return {
        "n": len(rows),
        "type_counts": type_counts,
        "style_counts": style_counts,
        "seed_counts": seed_counts,
        "invalid_weight_sums": invalid_weight_sums,
    }


def write_report(rows: list[dict[str, Any]], report_path: str | Path) -> Path:
    audit = audit_rows(rows)
    path = Path(report_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Synthetic Pressure Profile Report",
        "",
        "This dataset is a deterministic stress-test expansion from the 12 robust seed profiles.",
        "It is not a real-user generalization set and should not be merged into the main robust table.",
        "",
        f"- profiles: {audit['n']}",
        f"- invalid_weight_sums: {len(audit['invalid_weight_sums'])}",
        "",
        "## Hidden Bottom-Line Types",
        "",
    ]
    for key, count in sorted(audit["type_counts"].items()):
        lines.append(f"- {key}: {count}")
    lines.extend(["", "## Talk Styles", ""])
    for key, count in sorted(audit["style_counts"].items()):
        lines.append(f"- {key}: {count}")
    lines.extend(["", "## Seed Coverage", ""])
    for key, count in sorted(audit["seed_counts"].items()):
        lines.append(f"- {key}: {count}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def run_cli(argv: list[str] | None = None) -> dict[str, str]:
    parser = argparse.ArgumentParser()
    parser.add_argument("--size", type=int, default=60)
    parser.add_argument("--seed", type=int, default=20260517)
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--report", default=str(DEFAULT_REPORT))
    args = parser.parse_args(argv)

    rows = generate_synthetic_pressure_profiles(size=args.size, seed=args.seed)
    output = write_jsonl(rows, args.output)
    report = write_report(rows, args.report)
    print(f"[synthetic_profiles] wrote {output}")
    print(f"[synthetic_profiles] wrote {report}")
    return {"output": str(output), "report": str(report)}


if __name__ == "__main__":
    run_cli()
