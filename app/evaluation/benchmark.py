import csv
from pathlib import Path
from typing import Any

from app.evaluation.sandbox import run_sandbox_evaluation
from app.evaluation.schemas import IcebergProfile
from app.evaluation.simulator import UserSimulator


ABLATION_MODES = ("full", "no_ucb", "no_tracker")
CSV_FIELDS = (
    "profile_id",
    "ablation_mode",
    "mae_error",
    "negotiation_turns",
    "status",
    "error_message",
)


def get_evaluation_dataset() -> list[IcebergProfile]:
    return [
        IcebergProfile(
            profile_id="profile_major_bottom_line",
            explicit_query="我只想上985，学校牌子必须足够硬，专业可以再看看。",
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
            explicit_query="帮我推荐性价比高的大类，学校和专业都可以灵活一点。",
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
            explicit_query="我要尽量冲最好的名校，地域和专业都可以谈。",
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


def _mock_replies_for_profile(profile: IcebergProfile) -> list[str]:
    if profile.profile_id == "profile_major_bottom_line":
        return ["只要专业是计算机大类，我可以接受学校差一点", "专业不能偏太远"]
    if profile.profile_id == "profile_geo_bottom_line":
        return ["不行，我绝对不出省", "本省内学费高一点也可以"]
    if profile.profile_id == "profile_tuition_bottom_line":
        return ["预算不能超，学费太贵绝对不行", "名校可以，但费用必须压住"]
    return ["我可以考虑", "这个不太行"]


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


def run_ablation_benchmark(
    agent_app: Any,
    simulator_class: type[UserSimulator],
    dataset: list[IcebergProfile],
    use_mock: bool = False,
    output_dir: str | Path | None = None,
    max_turns: int = 8,
) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    csv_dir = (
        Path(output_dir)
        if output_dir is not None
        else Path(__file__).parent / "results"
    )
    csv_dir.mkdir(parents=True, exist_ok=True)
    csv_path = csv_dir / "ablation_results.csv"

    for profile in dataset:
        for mode in ABLATION_MODES:
            simulator = simulator_class(
                profile,
                llm=None,
                mock_replies=_mock_replies_for_profile(profile) if use_mock else None,
            )
            thread_id = f"{profile.profile_id}_{mode}"
            try:
                result = run_sandbox_evaluation(
                    agent_app,
                    profile,
                    simulator,
                    thread_id=thread_id,
                    configurable={"ablation_mode": mode},
                    max_turns=max_turns,
                )
                rows.append(_result_row(profile, mode, result, status="ok"))
            except Exception as exc:
                rows.append(
                    _result_row(
                        profile,
                        mode,
                        {"mae_error": 1.0, "turns": 0},
                        status="error",
                        error_message=f"{type(exc).__name__}: {exc}",
                    )
                )

    with csv_path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=list(CSV_FIELDS))
        writer.writeheader()
        writer.writerows(rows)

    return {"rows": rows, "csv_path": str(csv_path)}
