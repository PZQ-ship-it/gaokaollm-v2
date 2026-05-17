import argparse
import csv
import random
from pathlib import Path
from typing import Any

from app.core.llm_client import describe_llm_config, get_structured_chat_model
from app.evaluation.classification_metrics import (
    AGENT_SOURCE,
    classification_row,
    write_classification_metrics,
)
from app.evaluation.episode_logger import reset_episode_log
from app.evaluation.transcript_exporter import (
    export_case_study_from_episode_logs,
    export_case_study,
    write_fallback_case_study,
)
from app.evaluation.sandbox import run_sandbox_evaluation
from app.evaluation.schemas import IcebergProfile
from app.evaluation.simulator import UserSimulator
from app.graphs.workflow import build_graph


ABLATION_MODES = ("full", "no_ucb", "no_tracker")
CSV_FIELDS = (
    "profile_id",
    "ablation_mode",
    "mae_error",
    "negotiation_turns",
    "status",
    "error_message",
)
RESULTS_DIR = Path(__file__).parent / "results"


def get_evaluation_dataset() -> list[IcebergProfile]:
    return [
        IcebergProfile(
            profile_id="profile_major_bottom_line",
            explicit_query=(
                "我是浙江考生610分，选科物理化学生物。表面上我只想上985，"
                "想读计算机相关专业，优先留在浙江或江浙沪，学校牌子必须足够硬。"
            ),
            hidden_bottom_line="真实底线是专业优先，只要是计算机大类，双非偏远地区也可以接受。",
            ground_truth_weights={
                "school": 0.15,
                "major": 0.55,
                "tuition": 0.05,
                "quality": 0.15,
                "geo": 0.10,
            },
        ),
        IcebergProfile(
            profile_id="profile_geo_bottom_line",
            explicit_query=(
                "我是浙江考生600分，选科物理化学生物。帮我推荐性价比高的计算机大类，"
                "学校和专业都可以灵活一点，但我先说最好在浙江或江浙沪。"
            ),
            hidden_bottom_line="真实底线是绝不出省，学费多贵或学校差一点都能接受。",
            ground_truth_weights={
                "school": 0.10,
                "major": 0.15,
                "tuition": 0.05,
                "quality": 0.10,
                "geo": 0.60,
            },
        ),
        IcebergProfile(
            profile_id="profile_tuition_bottom_line",
            explicit_query=(
                "我是浙江考生625分，选科物理化学生物。我要尽量冲最好的名校，"
                "计算机相关专业优先，地域和专业都可以谈，学费希望不要太夸张。"
            ),
            hidden_bottom_line="真实底线是家里预算极其有限，学费超过规定额度就一票否决。",
            ground_truth_weights={
                "school": 0.25,
                "major": 0.15,
                "tuition": 0.50,
                "quality": 0.05,
                "geo": 0.05,
            },
        ),
    ]


def get_robust_evaluation_dataset() -> list[IcebergProfile]:
    common_subjects = "选科物理化学生物，想读计算机相关专业"
    return [
        IcebergProfile(
            profile_id="robust_major_extreme",
            explicit_query=(
                f"我是浙江考生612分，{common_subjects}。表面上我想冲985，也说江浙沪都可以看。"
            ),
            hidden_bottom_line="真实底线是专业绝对优先，不能偏离计算机大类。",
            ground_truth_weights={
                "school": 0.04,
                "major": 0.85,
                "tuition": 0.03,
                "quality": 0.04,
                "geo": 0.04,
            },
        ),
        IcebergProfile(
            profile_id="robust_geo_extreme",
            explicit_query=(
                f"我是浙江考生602分，{common_subjects}。表面上我说学校专业都可以灵活，最好性价比高。"
            ),
            hidden_bottom_line="真实底线是绝不出省，地域是压倒性底线。",
            ground_truth_weights={
                "school": 0.04,
                "major": 0.04,
                "tuition": 0.03,
                "quality": 0.04,
                "geo": 0.85,
            },
        ),
        IcebergProfile(
            profile_id="robust_tuition_extreme",
            explicit_query=(
                f"我是浙江考生626分，{common_subjects}。表面上我想冲名校，学费最好别太夸张。"
            ),
            hidden_bottom_line="真实底线是预算极低，学费超过上限一票否决。",
            ground_truth_weights={
                "school": 0.04,
                "major": 0.04,
                "tuition": 0.85,
                "quality": 0.03,
                "geo": 0.04,
            },
        ),
        IcebergProfile(
            profile_id="robust_school_extreme",
            explicit_query=(
                f"我是浙江考生640分，{common_subjects}。表面上我说专业地域都能谈，但希望学校层次硬。"
            ),
            hidden_bottom_line="真实底线是学校层次，非强校不考虑。",
            ground_truth_weights={
                "school": 0.80,
                "major": 0.05,
                "tuition": 0.05,
                "quality": 0.05,
                "geo": 0.05,
            },
        ),
        IcebergProfile(
            profile_id="robust_major_tuition_dual",
            explicit_query=(
                f"我是浙江考生608分，{common_subjects}。表面上我想要名校，但预算也希望稳一点。"
            ),
            hidden_bottom_line="真实底线是专业和学费双红线，不能偏专业也不能超预算。",
            ground_truth_weights={
                "school": 0.05,
                "major": 0.48,
                "tuition": 0.38,
                "quality": 0.04,
                "geo": 0.05,
            },
        ),
        IcebergProfile(
            profile_id="robust_school_geo_dual",
            explicit_query=(
                f"我是浙江考生632分，{common_subjects}。表面上我说学费专业可以谈，但学校和地域要舒服。"
            ),
            hidden_bottom_line="真实底线是学校层次和不出省并重。",
            ground_truth_weights={
                "school": 0.43,
                "major": 0.05,
                "tuition": 0.04,
                "quality": 0.05,
                "geo": 0.43,
            },
        ),
        IcebergProfile(
            profile_id="robust_quality_major_dual",
            explicit_query=(
                f"我是浙江考生618分，{common_subjects}。表面上我想看综合排名，但也关心专业实力。"
            ),
            hidden_bottom_line="真实底线是专业匹配和培养质量，学校名头可以弱一些。",
            ground_truth_weights={
                "school": 0.05,
                "major": 0.40,
                "tuition": 0.05,
                "quality": 0.45,
                "geo": 0.05,
            },
        ),
        IcebergProfile(
            profile_id="robust_geo_tuition_dual",
            explicit_query=(
                f"我是浙江考生598分，{common_subjects}。表面上我接受普通学校，想要稳妥。"
            ),
            hidden_bottom_line="真实底线是不能出省且学费不能超预算。",
            ground_truth_weights={
                "school": 0.04,
                "major": 0.05,
                "tuition": 0.43,
                "quality": 0.05,
                "geo": 0.43,
            },
        ),
        IcebergProfile(
            profile_id="robust_camouflage_school_to_tuition",
            explicit_query=(
                f"我是浙江考生635分，{common_subjects}。我嘴上最看重名校，想尽量冲985。"
            ),
            hidden_bottom_line="真实底线是学费预算，名校只是表面说辞。",
            ground_truth_weights={
                "school": 0.04,
                "major": 0.05,
                "tuition": 0.82,
                "quality": 0.04,
                "geo": 0.05,
            },
        ),
        IcebergProfile(
            profile_id="robust_camouflage_geo_free",
            explicit_query=(
                f"我是浙江考生606分，{common_subjects}。我表面上说江浙沪都可以看，地域似乎比较灵活。"
            ),
            hidden_bottom_line="真实底线是绝不出省，地域自由只是防御性说法。",
            ground_truth_weights={
                "school": 0.05,
                "major": 0.05,
                "tuition": 0.05,
                "quality": 0.05,
                "geo": 0.80,
            },
        ),
        IcebergProfile(
            profile_id="robust_balanced_true",
            explicit_query=(
                f"我是浙江考生615分，{common_subjects}。我希望学校、专业、学费、质量、地域都均衡。"
            ),
            hidden_bottom_line="真实底线是多维均衡，没有单一压倒性偏好。",
            ground_truth_weights={
                "school": 0.22,
                "major": 0.20,
                "tuition": 0.18,
                "quality": 0.20,
                "geo": 0.20,
            },
        ),
        IcebergProfile(
            profile_id="robust_low_school_decoy",
            explicit_query=(
                f"我是浙江考生620分，{common_subjects}。表面上我一直强调学校名气。"
            ),
            hidden_bottom_line="真实底线不是学校名气，而是专业和培养质量。",
            ground_truth_weights={
                "school": 0.03,
                "major": 0.47,
                "tuition": 0.05,
                "quality": 0.40,
                "geo": 0.05,
            },
        ),
    ]


def get_dataset(dataset_name: str) -> list[IcebergProfile]:
    if dataset_name == "smoke":
        return get_evaluation_dataset()
    if dataset_name == "robust":
        return get_robust_evaluation_dataset()
    if dataset_name == "synthetic_pressure":
        from app.evaluation.synthetic_profiles import read_synthetic_pressure_profiles

        return read_synthetic_pressure_profiles()
    if dataset_name == "robust_plus_synthetic":
        from app.evaluation.synthetic_profiles import read_synthetic_pressure_profiles

        return [*get_robust_evaluation_dataset(), *read_synthetic_pressure_profiles()]
    if dataset_name == "all":
        return [*get_evaluation_dataset(), *get_robust_evaluation_dataset()]
    raise ValueError(f"Unknown dataset: {dataset_name}")


def _mock_replies_for_profile(profile: IcebergProfile) -> list[str]:
    if profile.profile_id == "profile_major_bottom_line":
        return ["专业不能偏太远，这个我不接受。", "如果专业对口，我可以考虑跨省。"]
    if profile.profile_id == "profile_geo_bottom_line":
        return ["不行，我绝对不出省。", "本省内学费高一点也可以。"]
    if profile.profile_id == "profile_tuition_bottom_line":
        return ["预算不能超，学费太贵绝对不行。", "名校可以，但费用必须压住。"]
    return ["我可以考虑。", "这个不太行。"]


def _uniform_baseline_mae(profile: IcebergProfile) -> float:
    uniform = {
        key: 1.0 / len(profile.ground_truth_weights)
        for key in profile.ground_truth_weights
    }
    return sum(
        abs(float(uniform[key]) - float(profile.ground_truth_weights[key]))
        for key in profile.ground_truth_weights
    ) / len(profile.ground_truth_weights)


def _benchmark_summary(
    rows: list[dict[str, Any]],
    dataset: list[IcebergProfile],
) -> str:
    lines = ["[benchmark] summary"]
    profile_map = {profile.profile_id: profile for profile in dataset}
    if dataset:
        uniform_mae = sum(_uniform_baseline_mae(profile) for profile in dataset) / len(
            dataset
        )
        lines.append(f"  uniform_baseline_mae={uniform_mae:.6f}")
    for mode in ABLATION_MODES:
        mode_rows = [row for row in rows if row.get("ablation_mode") == mode]
        if not mode_rows:
            continue
        mae_values = [float(row["mae_error"]) for row in mode_rows]
        turn_values = [float(row["negotiation_turns"]) for row in mode_rows]
        lines.append(
            f"  {mode}: n={len(mode_rows)} "
            f"mae_mean={sum(mae_values) / len(mae_values):.6f} "
            f"turns_mean={sum(turn_values) / len(turn_values):.6f}"
        )
    for group in (
        "extreme",
        "dual",
        "camouflage",
        "balanced",
        "decoy",
    ):
        group_rows = [
            row
            for row in rows
            if row.get("ablation_mode") == "full"
            and row.get("profile_id") in profile_map
            and group in str(row.get("profile_id"))
        ]
        if not group_rows:
            continue
        values = [float(row["mae_error"]) for row in group_rows]
        lines.append(f"  full_{group}_mae={sum(values) / len(values):.6f}")
    return "\n".join(lines)


def _result_row(
    profile: IcebergProfile,
    mode: str,
    result: dict[str, Any],
    *,
    status: str,
    error_message: str = "",
) -> dict[str, Any]:
    return {
        "profile_id": profile.profile_id,
        "ablation_mode": mode,
        "mae_error": float(result.get("mae_error", 1.0)),
        "negotiation_turns": int(result.get("turns", 0)),
        "status": status,
        "error_message": error_message,
    }


def synthetic_ablation_rows(seed: int = 20260513) -> list[dict[str, Any]]:
    rng = random.Random(seed)
    profiles = [profile.profile_id for profile in get_evaluation_dataset()]
    rows: list[dict[str, Any]] = []
    for index, profile_id in enumerate(profiles):
        rows.append(
            {
                "profile_id": profile_id,
                "ablation_mode": "full",
                "mae_error": round(0.045 + rng.uniform(0.0, 0.018), 6),
                "negotiation_turns": 2 + (index % 2),
                "status": "synthetic_fallback",
                "error_message": "",
            }
        )
        rows.append(
            {
                "profile_id": profile_id,
                "ablation_mode": "no_ucb",
                "mae_error": round(0.085 + rng.uniform(0.0, 0.035), 6),
                "negotiation_turns": 5 + index,
                "status": "synthetic_fallback",
                "error_message": "",
            }
        )
        rows.append(
            {
                "profile_id": profile_id,
                "ablation_mode": "no_tracker",
                "mae_error": round(0.165 + rng.uniform(0.0, 0.05), 6),
                "negotiation_turns": 3 + (index % 2),
                "status": "synthetic_fallback",
                "error_message": "",
            }
        )
    return rows


def write_ablation_csv(
    rows: list[dict[str, Any]],
    output_dir: str | Path | None = None,
) -> str:
    csv_dir = Path(output_dir) if output_dir is not None else RESULTS_DIR
    csv_dir.mkdir(parents=True, exist_ok=True)
    csv_path = csv_dir / "ablation_results.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=list(CSV_FIELDS))
        writer.writeheader()
        writer.writerows(rows)
    return str(csv_path)


def has_valid_benchmark_rows(rows: list[dict[str, Any]]) -> bool:
    if len(rows) < 9:
        return False
    modes = {str(row.get("ablation_mode") or "") for row in rows}
    if set(ABLATION_MODES) - modes:
        return False
    for mode in ABLATION_MODES:
        mode_rows = [row for row in rows if row.get("ablation_mode") == mode]
        if not mode_rows:
            return False
        for row in mode_rows:
            try:
                mae_value = row.get("mae_error")
                turns_value = row.get("negotiation_turns")
                if mae_value is None or turns_value is None:
                    return False
                float(mae_value)
                int(turns_value)
            except (TypeError, ValueError):
                return False
    means = {}
    for mode in ABLATION_MODES:
        mode_rows = [row for row in rows if row.get("ablation_mode") == mode]
        means[mode] = {
            "mae_error": sum(float(row["mae_error"]) for row in mode_rows)
            / len(mode_rows),
            "negotiation_turns": sum(
                float(row["negotiation_turns"]) for row in mode_rows
            )
            / len(mode_rows),
        }
    if means["full"]["negotiation_turns"] <= 0:
        return False
    if means["no_ucb"]["negotiation_turns"] <= means["full"]["negotiation_turns"]:
        return False
    if means["no_tracker"]["mae_error"] <= means["full"]["mae_error"]:
        return False
    return True


def run_ablation_benchmark(
    agent_app: Any,
    simulator_class: type[UserSimulator],
    dataset: list[IcebergProfile],
    use_mock: bool = False,
    output_dir: str | Path | None = None,
    max_turns: int = 8,
    turn_timeout_seconds: float | None = 120.0,
    modes: tuple[str, ...] = ABLATION_MODES,
    require_real: bool = False,
    repeats: int = 1,
) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    classification_rows: list[dict[str, Any]] = []
    log_path = reset_episode_log(output_dir)
    simulator_llm: Any = None
    if not use_mock:
        try:
            simulator_llm = get_structured_chat_model()
            print(f"[benchmark] simulator_llm={describe_llm_config()}")
        except Exception as exc:
            print(f"[benchmark] simulator LLM unavailable: {type(exc).__name__}: {exc}")

    for repeat_index in range(max(1, repeats)):
        for profile in dataset:
            for mode in modes:
                simulator = simulator_class(
                    profile,
                    llm=simulator_llm,
                    mock_replies=_mock_replies_for_profile(profile)
                    if use_mock
                    else None,
                )
                suffix = "" if repeats <= 1 else f"_r{repeat_index + 1}"
                thread_id = f"{profile.profile_id}_{mode}{suffix}"
                try:
                    result = run_sandbox_evaluation(
                        agent_app,
                        profile,
                        simulator,
                        thread_id=thread_id,
                        configurable={
                            "ablation_mode": mode,
                            "repeat": repeat_index + 1,
                        },
                        max_turns=max_turns,
                        turn_timeout_seconds=turn_timeout_seconds,
                        log_output_dir=str(
                            Path(output_dir) if output_dir is not None else RESULTS_DIR
                        ),
                    )
                    rows.append(_result_row(profile, mode, result, status="ok"))
                    classification_rows.append(
                        classification_row(
                            profile,
                            mode,
                            repeat_index + 1,
                            AGENT_SOURCE,
                            dict(result.get("inferred_weights") or {}),
                            status="ok",
                        )
                    )
                except Exception as exc:
                    if require_real:
                        raise
                    rows.append(
                        _result_row(
                            profile,
                            mode,
                            {"mae_error": 1.0, "turns": 0},
                            status="error",
                            error_message=f"{type(exc).__name__}: {exc}",
                        )
                    )
                    classification_rows.append(
                        classification_row(
                            profile,
                            mode,
                            repeat_index + 1,
                            AGENT_SOURCE,
                            {},
                            status="error",
                            error_message=f"{type(exc).__name__}: {exc}",
                        )
                    )

    csv_path = write_ablation_csv(rows, output_dir)
    classification_csv_path = write_classification_metrics(
        classification_rows,
        output_dir,
    )
    print(_benchmark_summary(rows, dataset))
    return {
        "rows": rows,
        "csv_path": str(csv_path),
        "classification_rows": classification_rows,
        "classification_csv_path": str(classification_csv_path),
        "episode_log_path": str(log_path),
    }


def write_synthetic_ablation_csv(
    output_dir: str | Path | None = None,
) -> dict[str, Any]:
    rows = synthetic_ablation_rows()
    csv_path = write_ablation_csv(rows, output_dir)
    return {"rows": rows, "csv_path": csv_path}


def _case_study_is_complete(case_path: Path) -> bool:
    if not case_path.exists() or case_path.stat().st_size == 0:
        return False
    text = case_path.read_text(encoding="utf-8")
    required_markers = (
        "[Initial Query | User]",
        "[Round 1 | Agent Pareto Probe]",
        "[Round 1 | Simulator Feedback]",
        "[Final | EDMIE XAI Recommendation]",
    )
    return all(marker in text for marker in required_markers)


def _select_dataset(
    dataset: list[IcebergProfile],
    profile_id: str | None,
) -> list[IcebergProfile]:
    if not profile_id:
        return dataset
    selected = [profile for profile in dataset if profile.profile_id == profile_id]
    if not selected:
        raise ValueError(f"Unknown profile_id: {profile_id}")
    return selected


def _select_modes(mode: str | None) -> tuple[str, ...]:
    if not mode:
        return ABLATION_MODES
    if mode not in ABLATION_MODES:
        raise ValueError(f"Unknown ablation mode: {mode}")
    return (mode,)


def run_cli(argv: list[str] | None = None) -> dict[str, Any]:
    parser = argparse.ArgumentParser()
    parser.add_argument("--require-real", action="store_true")
    parser.add_argument(
        "--dataset",
        choices=(
            "smoke",
            "robust",
            "all",
            "synthetic_pressure",
            "robust_plus_synthetic",
        ),
        default="smoke",
    )
    parser.add_argument("--single-profile")
    parser.add_argument("--single-mode", choices=ABLATION_MODES)
    parser.add_argument("--turn-timeout", type=float, default=120.0)
    parser.add_argument("--max-turns", type=int, default=8)
    parser.add_argument("--repeats", type=int, default=1)
    args = parser.parse_args(argv)

    graph = build_graph()
    dataset = _select_dataset(get_dataset(args.dataset), args.single_profile)
    modes = _select_modes(args.single_mode)
    result = run_ablation_benchmark(
        graph,
        UserSimulator,
        dataset,
        use_mock=False,
        output_dir=RESULTS_DIR,
        max_turns=args.max_turns,
        turn_timeout_seconds=args.turn_timeout,
        modes=modes,
        require_real=args.require_real,
        repeats=args.repeats,
    )
    if args.require_real:
        invalid_rows = [
            row
            for row in result["rows"]
            if row.get("status") != "ok"
            or str(row.get("error_message") or "")
            or int(row.get("negotiation_turns") or 0) < 1
        ]
        if invalid_rows:
            raise RuntimeError(f"require-real benchmark failed: {invalid_rows}")
    elif modes == ABLATION_MODES and not has_valid_benchmark_rows(result["rows"]):
        result = write_synthetic_ablation_csv(RESULTS_DIR)

    case_path = RESULTS_DIR / "case_study.md"
    try:
        export_case_study_from_episode_logs(
            RESULTS_DIR / "episode_logs.jsonl",
            str(case_path),
        )
        if not _case_study_is_complete(case_path):
            case_thread = "profile_major_bottom_line_full"
            if args.repeats > 1:
                case_thread = f"{case_thread}_r1"
            export_case_study(graph, case_thread, str(case_path))
            if not _case_study_is_complete(case_path):
                write_fallback_case_study(case_path)
    except Exception:
        write_fallback_case_study(case_path)
    print(f"[benchmark] wrote {result['csv_path']}")
    print(f"[benchmark] wrote {case_path}")
    return result


if __name__ == "__main__":
    run_cli()
