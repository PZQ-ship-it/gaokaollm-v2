import builtins
import csv
import importlib.util
import re
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage

from app.evaluation.plotter import DEPENDENCY_HINT, generate_academic_report
from app.evaluation.transcript_exporter import export_case_study


def _analysis_output_dir() -> Path:
    output = Path("app/evaluation/results/test_phase8")
    shutil.rmtree(output, ignore_errors=True)
    output.mkdir(parents=True, exist_ok=True)
    return output


def _write_mock_ablation_csv(csv_path: Path) -> None:
    rows: list[dict[str, Any]] = []
    for index in range(10):
        rows.append(
            {
                "profile_id": f"p{index}",
                "ablation_mode": "full",
                "mae_error": 0.05 + index * 0.001,
                "negotiation_turns": 1 + (index % 2),
                "status": "ok",
                "error_message": "",
            }
        )
        rows.append(
            {
                "profile_id": f"p{index}",
                "ablation_mode": "no_ucb",
                "mae_error": 0.12 + index * 0.002,
                "negotiation_turns": 4 + (index % 3),
                "status": "ok",
                "error_message": "",
            }
        )
        rows.append(
            {
                "profile_id": f"p{index}",
                "ablation_mode": "no_tracker",
                "mae_error": 0.30 + index * 0.003,
                "negotiation_turns": 3 + (index % 2),
                "status": "ok",
                "error_message": "",
            }
        )
    with csv_path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=[
                "profile_id",
                "ablation_mode",
                "mae_error",
                "negotiation_turns",
                "status",
                "error_message",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)


def test_generate_academic_report_or_dependency_hint():
    output = _analysis_output_dir()
    try:
        csv_path = output / "mock_ablation_results.csv"
        _write_mock_ablation_csv(csv_path)

        deps_available = all(
            importlib.util.find_spec(module) is not None
            for module in ("pandas", "matplotlib", "seaborn", "scipy")
        )
        if not deps_available:
            try:
                generate_academic_report(str(csv_path), str(output))
            except RuntimeError as exc:
                assert "pandas matplotlib seaborn scipy" in str(exc)
                assert DEPENDENCY_HINT in str(exc)
                return
            raise AssertionError(
                "Expected dependency hint when plotting stack is missing"
            )

        paths = generate_academic_report(str(csv_path), str(output))
        for key in (
            "fig_efficiency_turns_png",
            "fig_efficiency_turns_pdf",
            "fig_alignment_mae_png",
            "fig_alignment_mae_pdf",
            "statistical_summary",
        ):
            path = Path(paths[key])
            assert path.exists()
            assert path.stat().st_size > 0

        summary = Path(paths["statistical_summary"]).read_text(encoding="utf-8")
        assert "p-value" in summary
        assert re.search(r"p-value=\d", summary)

        from matplotlib import pyplot as plt

        plt.close("all")
    finally:
        shutil.rmtree(output, ignore_errors=True)


def test_generate_academic_report_reports_missing_dependencies(monkeypatch):
    original_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "pandas":
            raise ImportError("missing pandas for test")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    try:
        generate_academic_report("missing.csv", str(_analysis_output_dir()))
    except RuntimeError as exc:
        assert "pandas matplotlib seaborn scipy" in str(exc)
    else:
        raise AssertionError("Expected RuntimeError for missing plotting dependencies")
    finally:
        shutil.rmtree(_analysis_output_dir(), ignore_errors=True)


@dataclass
class FakeSnapshot:
    values: dict[str, Any]


class FakeHistoryApp:
    def get_state_history(self, config: dict[str, Any]):
        assert config["configurable"]["thread_id"] == "case-thread"
        return [
            FakeSnapshot(
                {
                    "messages": [
                        HumanMessage(content="我只想留在江浙沪读计算机"),
                        AIMessage(content="偏好解释：系统发现您最看重专业与地域。"),
                    ]
                }
            ),
            FakeSnapshot(
                {
                    "latest_human_feedback": "可以接受跨省，但专业不能偏。",
                    "messages": [HumanMessage(content="我只想留在江浙沪读计算机")],
                }
            ),
            FakeSnapshot(
                {
                    "latest_agent_probe_question": "是否愿意牺牲地域换取学校跃迁？",
                    "messages": [HumanMessage(content="我只想留在江浙沪读计算机")],
                }
            ),
        ]


def test_export_case_study_writes_markdown_transcript():
    output = _analysis_output_dir() / "case_study.md"
    try:
        path = export_case_study(FakeHistoryApp(), "case-thread", str(output))
        content = Path(path).read_text(encoding="utf-8")

        assert output.exists()
        assert "**[Initial Query | User]**" in content
        assert "**[Round 1 | Agent Pareto Probe]**" in content
        assert "**[Round 1 | Simulator Feedback]**" in content
        assert "**[Final | EDMIE XAI Recommendation]**" in content
        assert "我只想留在江浙沪读计算机" in content
        assert "是否愿意牺牲地域换取学校跃迁？" in content
        assert "可以接受跨省，但专业不能偏。" in content
        assert "偏好解释：系统发现您最看重专业与地域。" in content
    finally:
        shutil.rmtree(output.parent, ignore_errors=True)
