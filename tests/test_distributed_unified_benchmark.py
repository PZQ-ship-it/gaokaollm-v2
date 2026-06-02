import json
import asyncio
from pathlib import Path

from app.evaluation import distributed_unified_benchmark as dub
from gaokaollm_bench.constrains.enums import ConversationRole
from gaokaollm_bench.evaluator.llm_as_a_judge import evaluate_process
from gaokaollm_bench.simulator.user_agent import SimulatorStep
from gaokaollm_bench.schemas import ConversationTurn, IcebergPersona, Transcript
from gaokaollm_bench.tests.manual.agent_benchmark_run import (
    _archive_retry_rows,
    _existing_rows_for_retry,
)


def _persona(case_id: str, constraint_count: int) -> dict:
    return {
        "case_id": case_id,
        "background": {"constraint_count": constraint_count},
    }


def _lane(
    lane_id: str,
    *,
    provider: str = "test",
    key: str | None = None,
) -> dict:
    return {
        "lane_id": lane_id,
        "provider": provider,
        "api_key": key or f"sk-secret-{lane_id}-abcdef",
        "base_url": "https://example.invalid/v1",
        "models": [f"{lane_id}-model-{index}" for index in range(5)],
        "small_model": f"{lane_id}-small",
        "embedding_model": f"{lane_id}-embedding",
        "rerank_model": f"{lane_id}-rerank",
        "rerank_base_url": "https://example.invalid/v1",
        "rerank_endpoint": "/rerank",
    }


def _write_lane_config(path: Path) -> None:
    path.write_text(
        json.dumps(
            {
                "version": 1,
                "lanes": [
                    _lane("siliconflow_1", provider="siliconflow"),
                    _lane("siliconflow_2", provider="siliconflow"),
                    _lane("aliyun_1", provider="aliyun"),
                    _lane("aliyun_2", provider="aliyun"),
                ],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


def test_shard_cases_writes_expected_c6_lane_counts(tmp_path):
    personas = [
        *[_persona(f"c6-{index:02d}", 6) for index in range(30)],
        _persona("c5-ignore", 5),
    ]
    personas_path = tmp_path / "personas.json"
    personas_path.write_text(
        json.dumps(personas, ensure_ascii=False),
        encoding="utf-8",
    )
    output_dir = tmp_path / "shards"
    args = dub.build_parser().parse_args(
        [
            "shard-cases",
            "--personas",
            str(personas_path),
            "--constraint-count",
            "6",
            "--output-dir",
            str(output_dir),
        ]
    )

    assert args.func(args) == 0

    counts = {}
    for lane_id in dub.DEFAULT_LANE_ORDER:
        shard = output_dir / f"c6_{lane_id}.json"
        rows = json.loads(shard.read_text(encoding="utf-8"))
        counts[lane_id] = len(rows)
        assert all(row["background"]["constraint_count"] == 6 for row in rows)
    assert counts == {
        "siliconflow_1": 8,
        "siliconflow_2": 8,
        "aliyun_1": 7,
        "aliyun_2": 7,
    }


def test_run_shards_dry_run_maps_lanes_without_exposing_keys(tmp_path):
    config = tmp_path / "lanes.json"
    _write_lane_config(config)
    shard_dir = tmp_path / "shards"
    shard_dir.mkdir()
    for lane_id in dub.DEFAULT_LANE_ORDER:
        (shard_dir / f"c6_{lane_id}.json").write_text(
            json.dumps([_persona(f"{lane_id}-case", 6)]),
            encoding="utf-8",
        )
    manifest = tmp_path / "manifest.json"
    args = dub.build_parser().parse_args(
        [
            "run-shards",
            "--config",
            str(config),
            "--shard-dir",
            str(shard_dir),
            "--output-root",
            str(tmp_path / "outputs"),
            "--split-root",
            str(tmp_path / "splits"),
            "--log-dir",
            str(tmp_path / "logs"),
            "--manifest",
            str(manifest),
            "--runtime-root",
            str(tmp_path / "runtime"),
            "--dry-run",
        ]
    )

    assert args.func(args) == 0

    text = manifest.read_text(encoding="utf-8")
    payload = json.loads(text)
    assert payload["mode"] == "sharded"
    assert [job["lane"]["lane_id"] for job in payload["jobs"]] == sorted(
        dub.DEFAULT_LANE_ORDER
    )
    assert "v1_prompt_cot" not in text
    assert "secret-siliconflow" not in text
    assert "secret-aliyun" not in text
    assert all("api_key" not in job for job in payload["jobs"])
    for job in payload["jobs"]:
        command = " ".join(job["command"])
        assert "--personas" in command
        assert job["shard_path"] in command
        assert job["output_root"] in command


def test_run_shards_dry_run_supports_baseline_only_cot(tmp_path):
    config = tmp_path / "lanes.json"
    _write_lane_config(config)
    shard_dir = tmp_path / "shards"
    shard_dir.mkdir()
    for lane_id in dub.DEFAULT_LANE_ORDER:
        (shard_dir / f"c3_{lane_id}.json").write_text(
            json.dumps([_persona(f"{lane_id}-case", 3)]),
            encoding="utf-8",
        )
    manifest = tmp_path / "manifest.json"
    args = dub.build_parser().parse_args(
        [
            "run-shards",
            "--config",
            str(config),
            "--constraint",
            "3",
            "--mode",
            "baseline",
            "--shard-dir",
            str(shard_dir),
            "--output-root",
            str(tmp_path / "outputs"),
            "--split-root",
            str(tmp_path / "splits"),
            "--log-dir",
            str(tmp_path / "logs"),
            "--manifest",
            str(manifest),
            "--runtime-root",
            str(tmp_path / "runtime"),
            "--baseline-targets",
            "v1_prompt_cot",
            "--parallel-models",
            "5",
            "--initial-concurrency",
            "10",
            "--dry-run",
        ]
    )

    assert args.func(args) == 0

    text = manifest.read_text(encoding="utf-8")
    payload = json.loads(text)
    assert payload["constraint"] == 3
    assert "sk-secret" not in text
    for job in payload["jobs"]:
        command = job["command"]
        mode_index = command.index("--mode")
        assert command[mode_index + 1] == "baseline"
        targets_index = command.index("--baseline-targets")
        assert command[targets_index + 1] == "v1_prompt_cot"


def test_status_reads_job_specific_output_root(tmp_path):
    lane_output = tmp_path / "outputs" / "siliconflow_1"
    target = "app_pareto"
    report_dir = lane_output / "c6" / "baseline" / "model_a" / target / "reports"
    report_dir.mkdir(parents=True)
    (report_dir / f"{target}.jsonl").write_text(
        "\n".join(
            [
                json.dumps({"status": "ok", "case_id": "a"}),
                json.dumps({"status": "error", "case_id": "b"}),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "jobs": [
                    {
                        "constraint": 6,
                        "lane": {"lane_id": "siliconflow_1"},
                        "output_root": str(lane_output),
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    output_md = tmp_path / "status.md"
    args = dub.build_parser().parse_args(
        [
            "status",
            "--manifest",
            str(manifest),
            "--output-md",
            str(output_md),
        ]
    )

    assert args.func(args) == 0

    text = output_md.read_text(encoding="utf-8")
    assert (
        "| C6 | siliconflow_1 | baseline | model_a | app_pareto | 2 | 1 | 1 |" in text
    )


def test_simulator_step_defaults_to_not_persuaded_on_partial_output():
    step = SimulatorStep.model_validate({"thought": "still thinking"})

    assert step.is_persuaded is False
    assert step.utterance == ""


def test_evaluate_process_falls_back_on_invalid_judge_output():
    class EmptyJudge:
        async def ainvoke(self, prompt):
            return "{}"

    persona = IcebergPersona(
        case_id="case-judge-fallback",
        background={},
        explicit_red_lines={},
        implicit_flexibilities={},
        initial_utterance="initial",
        process_milestones={},
    )
    transcript = Transcript(
        persona=persona,
        turns=[
            ConversationTurn(
                turn_id=1,
                role=ConversationRole.TARGET_AGENT,
                content="No verified candidate yet.",
                internal_state={},
            )
        ],
    )

    report = asyncio.run(evaluate_process(transcript, persona, EmptyJudge()))

    assert report.case_id == persona.case_id
    assert report.elicitation_success is False
    assert report.pareto_gain == 0
    assert "LLM judge fallback" in report.judge_reasoning


def test_retry_resume_archives_failed_rows_without_counting_them_completed(tmp_path):
    transcript = tmp_path / "transcript.json"
    transcript.write_text("{}", encoding="utf-8")
    report = tmp_path / "app_pareto.jsonl"
    failed = {
        "status": "failed",
        "case_id": "retry-me",
        "error_type": "APITimeoutError",
    }
    ok = {
        "status": "ok",
        "case_id": "done",
        "transcript_path": str(transcript),
    }
    report.write_text(
        json.dumps(failed, ensure_ascii=False)
        + "\n"
        + json.dumps(ok, ensure_ascii=False)
        + "\n",
        encoding="utf-8",
    )

    ok_rows, retry_rows = _existing_rows_for_retry(report)
    archived = _archive_retry_rows(report, retry_rows)

    assert [row["case_id"] for row in ok_rows] == ["done"]
    assert [row["case_id"] for row in retry_rows] == ["retry-me"]
    assert archived == 1
    archive_text = (tmp_path / "app_pareto.retry_failures.jsonl").read_text(
        encoding="utf-8"
    )
    assert "APITimeoutError" in archive_text
