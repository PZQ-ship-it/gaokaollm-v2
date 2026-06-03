import json
from pathlib import Path

from scripts.diagnose_agent_runs import _aggregate, _diagnose_trace


def _write_trace(path: Path, payload: dict) -> Path:
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return path


def test_diagnose_success_trace_with_interrupt_metadata(tmp_path: Path) -> None:
    path = _write_trace(
        tmp_path / "success.json",
        {
            "thread_id": "success",
            "rounds": [
                {
                    "turn": 1,
                    "question": "是否愿意小幅放宽预算？",
                    "latest_question_kind": "tradeoff",
                    "latest_probe_target_dimension": "tuition",
                    "latest_tradeoff_pair": {"cost_dimension": "tuition"},
                    "turn_latency_seconds": 2.5,
                }
            ],
            "analysis": {"status": "ok", "failures": []},
            "errors": [],
            "final_question_kind": "finalize_offer",
            "final_recommendation_count": 6,
            "final_recommendation_bucket_counts": {
                "reach": 2,
                "match": 2,
                "safety": 2,
            },
            "final_reply": "根据你的偏好，推荐优先考虑这些候选。",
        },
    )

    report = _diagnose_trace(path)

    assert report["task_completion"] == "pass"
    assert report["tool_reliability"] == "pass"
    assert report["output_contract"] == "pass"
    assert report["state_integrity"] == "pass"
    assert report["observability"] == "pass"
    assert report["final_recommendation_count"] == 6


def test_diagnose_output_style_and_runtime_timeout(tmp_path: Path) -> None:
    style_path = _write_trace(
        tmp_path / "style.json",
        {
            "thread_id": "style",
            "rounds": [],
            "analysis": {"status": "ok", "failures": []},
            "errors": [],
            "final_reply": "志愿填报终极推荐报告：这是一次精准推断。",
        },
    )
    timeout_path = _write_trace(
        tmp_path / "timeout.json",
        {
            "thread_id": "timeout",
            "rounds": [],
            "analysis": {"status": "failed", "failures": ["turn 1: timeout"]},
            "errors": [
                {
                    "turn": 1,
                    "error": "timeout",
                    "error_type": "TimeoutError",
                }
            ],
            "final_reply": "",
        },
    )

    reports = [_diagnose_trace(style_path), _diagnose_trace(timeout_path)]
    aggregate = _aggregate(reports)

    assert reports[0]["output_contract"] == "warning"
    assert reports[1]["tool_reliability"] == "fail"
    assert aggregate["dimension_rollup"]["output_contract"]["warning"] == 1
    assert aggregate["root_causes"][0]["evidence"]["runtime_timeout"] >= 1


def test_diagnose_final_offer_requires_structured_table(tmp_path: Path) -> None:
    path = _write_trace(
        tmp_path / "missing-final-table.json",
        {
            "thread_id": "missing-final-table",
            "rounds": [],
            "analysis": {"status": "ok", "failures": []},
            "errors": [],
            "final_question_kind": "finalize_offer",
            "final_recommendation_count": 0,
            "final_reply": "已经生成最终推荐。",
        },
    )

    report = _diagnose_trace(path)
    aggregate = _aggregate([report])

    assert report["task_completion"] == "fail"
    assert report["state_integrity"] == "fail"
    assert report["final_table_missing"] is True
    assert aggregate["root_causes"][0]["cause"] == "最终推荐缺少结构化志愿表"
