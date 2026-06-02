"""Distributed C2-C5 benchmark launcher over multiple API provider lanes."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from app.evaluation.provider_lanes import (
    DEFAULT_CONFIG_PATH,
    DEFAULT_RUNTIME_ROOT,
    ProviderLane,
    build_default_config_from_txt,
    lanes_by_id,
    load_lanes,
    write_config,
    write_runtime_models_file,
)


DEFAULT_PERSONAS = Path(
    "gaokaollm_bench/sample_data/unified_iceberg_personas_1c6c_real_db_180.json"
)
DEFAULT_OUTPUT_ROOT = Path("gaokaollm_bench/outputs/unified_distributed_c2c5")
DEFAULT_SPLIT_DIR = Path("gaokaollm_bench/sample_data/unified_by_constraint_c2c5")
DEFAULT_LOG_DIR = Path("app/evaluation/results/logs/c2c5_distributed")
DEFAULT_MANIFEST = Path("app/evaluation/results/distributed_c2c5_manifest.json")
DEFAULT_HEALTH_JSON = Path("app/evaluation/results/llm_lanes_healthcheck.json")
DEFAULT_HEALTH_MD = Path("app/evaluation/results/llm_lanes_healthcheck.md")
DEFAULT_C6_SHARD_DIR = Path("gaokaollm_bench/sample_data/unified_c6_shards")
DEFAULT_C6_SPLIT_ROOT = Path("gaokaollm_bench/sample_data/unified_c6_split_by_lane")
DEFAULT_C6_OUTPUT_ROOT = Path("gaokaollm_bench/outputs/unified_distributed_c6_sharded")
DEFAULT_C6_LOG_DIR = Path("app/evaluation/results/logs/c6_distributed")
DEFAULT_C6_MANIFEST = Path("app/evaluation/results/distributed_c6_manifest.json")
DEFAULT_BASELINE_TARGETS = ("app_pareto", "v1_prompt_direct", "v1_prompt_cot")
DEFAULT_MAINLINE_BASELINE_TARGETS = ("app_pareto", "v1_prompt_direct")
DEFAULT_ABLATION_TARGETS = (
    "app_pareto_full",
    "app_pareto_no_ucb",
    "app_pareto_no_tracker",
)
DEFAULT_CONSTRAINT_LANES = {
    2: "siliconflow_1",
    3: "siliconflow_2",
    4: "aliyun_1",
    5: "aliyun_2",
}
DEFAULT_LANE_ORDER = ("siliconflow_1", "siliconflow_2", "aliyun_1", "aliyun_2")


@dataclass(frozen=True)
class HealthResult:
    lane_id: str
    provider: str
    stage: str
    model: str
    ok: bool
    latency_seconds: float
    detail: str


def utc_run_id() -> str:
    return datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")


def safe_error(exc: BaseException) -> str:
    message = f"{type(exc).__name__}: {exc}"
    return message.replace("\n", " ")[:500]


def parse_ints(values: list[str] | None, default: tuple[int, ...]) -> list[int]:
    if not values:
        return list(default)
    parsed: list[int] = []
    for value in values:
        for part in str(value).split(","):
            if part.strip():
                parsed.append(int(part.strip()))
    return parsed


def load_persona_items(path: str | Path) -> list[dict[str, Any]]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(data, dict) and isinstance(data.get("items"), list):
        data = data["items"]
    if not isinstance(data, list):
        raise ValueError("personas file must contain a list or {'items': [...]}")
    return [item for item in data if isinstance(item, dict)]


def persona_constraint_count(persona: dict[str, Any]) -> int | None:
    background = persona.get("background") if isinstance(persona, dict) else {}
    try:
        return int((background or {}).get("constraint_count"))
    except (TypeError, ValueError):
        return None


def shard_path_for_lane(shard_dir: str | Path, constraint: int, lane_id: str) -> Path:
    return Path(shard_dir) / f"c{constraint}_{lane_id}.json"


def command_str(command: list[str]) -> str:
    return " ".join(command)


def cmd_init_config(args: argparse.Namespace) -> int:
    config = build_default_config_from_txt(args.base_dir)
    out = write_config(config, args.output)
    lanes = load_lanes(out)
    print(f"[init-config] wrote {out}")
    for lane in lanes:
        print(
            "[init-config] "
            f"{lane.lane_id} provider={lane.provider} "
            f"base_url={lane.base_url} key={lane.masked_key} "
            f"fingerprint={lane.key_fingerprint}"
        )
    return 0


def cmd_validate_config(args: argparse.Namespace) -> int:
    lanes = load_lanes(args.config)
    print(f"[validate-config] ok lanes={len(lanes)}")
    for lane in lanes:
        summary = lane.safe_summary()
        print(
            f"- {summary['lane_id']} provider={summary['provider']} "
            f"base_url={summary['base_url']} key={summary['key']} "
            f"models={len(summary['models'])} small={summary['small_model']} "
            f"embedding={summary['embedding_model']} rerank={summary['rerank_model']}"
        )
    return 0


def chat_once(lane: ProviderLane, model: str, timeout: float) -> str:
    from openai import OpenAI

    client = OpenAI(
        api_key=lane.api_key,
        base_url=lane.base_url,
        timeout=timeout,
        max_retries=0,
    )
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": "请只回复 OK，用于连通性测试。"}],
        temperature=0,
        max_tokens=8,
    )
    content = response.choices[0].message.content or ""
    return content.strip()


def embedding_once(lane: ProviderLane, timeout: float) -> str:
    from openai import OpenAI

    client = OpenAI(
        api_key=lane.api_key,
        base_url=lane.base_url,
        timeout=timeout,
        max_retries=0,
    )
    response = client.embeddings.create(
        model=lane.embedding_model,
        input=["高考志愿推荐连通性测试"],
    )
    vector = list(response.data[0].embedding)
    if not vector:
        raise RuntimeError("empty embedding vector")
    return f"dim={len(vector)}"


def rerank_once(lane: ProviderLane, timeout: float) -> str:
    import httpx

    payload = {
        "model": lane.rerank_model,
        "query": "计算机专业实力",
        "documents": ["浙江大学计算机专业", "普通本科护理专业"],
        "top_n": 1,
        "return_documents": True,
    }
    rerank_base_url = (lane.rerank_base_url or lane.base_url).rstrip("/")
    endpoint = (
        lane.rerank_endpoint
        if lane.rerank_endpoint.startswith("/")
        else f"/{lane.rerank_endpoint}"
    )
    response = httpx.post(
        f"{rerank_base_url}{endpoint}",
        json=payload,
        headers={
            "Authorization": f"Bearer {lane.api_key}",
            "Content-Type": "application/json",
        },
        timeout=timeout,
    )
    response.raise_for_status()
    data = response.json()
    results = data.get("results") or []
    if not results:
        raise RuntimeError("empty rerank results")
    score = results[0].get("relevance_score", results[0].get("score", "n/a"))
    return f"results={len(results)} score={score}"


def run_check(
    *,
    lane: ProviderLane,
    stage: str,
    model: str,
    timeout: float,
) -> HealthResult:
    started = time.monotonic()
    try:
        if stage == "small_chat" or stage == "model_chat":
            detail = chat_once(lane, model, timeout)
        elif stage == "embedding":
            detail = embedding_once(lane, timeout)
        elif stage == "rerank":
            detail = rerank_once(lane, timeout)
        else:
            raise ValueError(f"unknown healthcheck stage: {stage}")
        ok = True
    except Exception as exc:  # noqa: BLE001 - report healthcheck failures.
        ok = False
        detail = safe_error(exc)
    return HealthResult(
        lane_id=lane.lane_id,
        provider=lane.provider,
        stage=stage,
        model=model,
        ok=ok,
        latency_seconds=round(time.monotonic() - started, 3),
        detail=detail[:500],
    )


def healthcheck_lane(
    lane: ProviderLane, timeout: float, fail_fast: bool
) -> list[HealthResult]:
    checks: list[tuple[str, str]] = [("small_chat", lane.small_model)]
    checks.extend(("model_chat", model) for model in lane.models)
    checks.append(("embedding", lane.embedding_model))
    checks.append(("rerank", lane.rerank_model))
    results: list[HealthResult] = []
    for stage, model in checks:
        result = run_check(lane=lane, stage=stage, model=model, timeout=timeout)
        results.append(result)
        print(
            f"[healthcheck] {lane.lane_id} {stage} {model} "
            f"{'OK' if result.ok else 'FAIL'} {result.latency_seconds:.3f}s"
        )
        if fail_fast and not result.ok:
            break
    return results


def write_health_outputs(
    *,
    results: list[HealthResult],
    lanes: list[ProviderLane],
    output_json: str | Path,
    output_md: str | Path,
) -> None:
    lane_summaries = {lane.lane_id: lane.safe_summary() for lane in lanes}
    payload = {
        "created_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "lanes": lane_summaries,
        "results": [asdict(result) for result in results],
        "ok": all(result.ok for result in results),
    }
    out_json = Path(output_json)
    out_md = Path(output_md)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    lines = [
        "# LLM Lane Healthcheck",
        "",
        f"- created_at: `{payload['created_at']}`",
        f"- overall: `{'ok' if payload['ok'] else 'failed'}`",
        "",
        "| lane | provider | stage | model | status | seconds | detail |",
        "| --- | --- | --- | --- | --- | ---: | --- |",
    ]
    for result in results:
        detail = result.detail.replace("|", "\\|").replace("\n", " ")
        lines.append(
            "| "
            f"{result.lane_id} | {result.provider} | {result.stage} | "
            f"{result.model} | {'OK' if result.ok else 'FAIL'} | "
            f"{result.latency_seconds:.3f} | {detail} |"
        )
    out_md.write_text("\n".join(lines) + "\n", encoding="utf-8")


def cmd_healthcheck(args: argparse.Namespace) -> int:
    lanes = load_lanes(args.config)
    all_results: list[HealthResult] = []
    with ThreadPoolExecutor(
        max_workers=max(1, min(args.parallel_lanes, len(lanes)))
    ) as executor:
        futures = {
            executor.submit(
                healthcheck_lane,
                lane,
                args.timeout,
                args.fail_fast,
            ): lane
            for lane in lanes
        }
        for future in as_completed(futures):
            all_results.extend(future.result())
    all_results.sort(key=lambda item: (item.lane_id, item.stage, item.model))
    write_health_outputs(
        results=all_results,
        lanes=lanes,
        output_json=args.output_json,
        output_md=args.output_md,
    )
    print(f"[healthcheck] wrote {args.output_json}")
    print(f"[healthcheck] wrote {args.output_md}")
    return 0 if all(result.ok for result in all_results) else 1


def build_adaptive_command(
    *,
    args: argparse.Namespace,
    lane: ProviderLane,
    constraint: int,
    models_file: Path,
) -> list[str]:
    command = [
        sys.executable,
        "-m",
        "app.evaluation.adaptive_unified_benchmark",
        "--mode",
        args.mode,
        "--personas",
        str(args.personas),
        "--models-file",
        str(models_file),
        "--constraint-counts",
        str(constraint),
        "--output-root",
        str(args.output_root),
        "--split-dir",
        str(args.split_dir),
        "--log-dir",
        str(args.log_dir),
        "--baseline-targets",
        *args.baseline_targets,
        "--ablation-targets",
        *args.ablation_targets,
        "--parallel-models",
        str(args.parallel_models),
        "--initial-concurrency",
        str(args.initial_concurrency),
        "--min-concurrency",
        str(args.min_concurrency),
        "--batch-attempts",
        str(args.batch_attempts),
        "--case-retries",
        str(args.case_retries),
        "--request-timeout",
        str(args.request_timeout),
        "--case-timeout",
        str(args.case_timeout),
        "--failure-threshold",
        str(args.failure_threshold),
        "--timeout-threshold",
        str(args.timeout_threshold),
        "--max-turns",
        str(args.max_turns),
        "--simulator-model",
        lane.small_model,
        "--judge-model",
        lane.small_model,
    ]
    if args.max_models is not None:
        command.extend(["--max-models", str(args.max_models)])
    if args.override_concurrency is not None:
        command.extend(["--override-concurrency", str(args.override_concurrency)])
    return command


def cmd_shard_cases(args: argparse.Namespace) -> int:
    lane_ids = list(args.lane_ids or DEFAULT_LANE_ORDER)
    if args.shards != len(lane_ids):
        raise ValueError(
            f"--shards={args.shards} must match lane id count={len(lane_ids)}"
        )
    rows = [
        item
        for item in load_persona_items(args.personas)
        if persona_constraint_count(item) == args.constraint_count
    ]
    if not rows:
        raise ValueError(
            f"no personas found for constraint_count={args.constraint_count}"
        )

    buckets: dict[str, list[dict[str, Any]]] = {lane_id: [] for lane_id in lane_ids}
    for index, item in enumerate(rows):
        buckets[lane_ids[index % len(lane_ids)]].append(item)

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest_jobs: list[dict[str, Any]] = []
    for lane_id in lane_ids:
        out = shard_path_for_lane(output_dir, args.constraint_count, lane_id)
        out.write_text(
            json.dumps(buckets[lane_id], ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        manifest_jobs.append(
            {
                "lane_id": lane_id,
                "path": str(out),
                "cases": len(buckets[lane_id]),
            }
        )
        print(f"[shard-cases] {lane_id} cases={len(buckets[lane_id])} -> {out}")

    manifest = {
        "created_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "personas": str(args.personas),
        "constraint_count": args.constraint_count,
        "total_cases": len(rows),
        "shards": manifest_jobs,
    }
    manifest_path = output_dir / f"c{args.constraint_count}_shards_manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"[shard-cases] wrote {manifest_path}")
    return 0


def run_lane_job(
    *,
    args: argparse.Namespace,
    lane: ProviderLane,
    constraint: int,
    run_id: str,
) -> dict[str, Any]:
    started = time.monotonic()
    models_file = write_runtime_models_file(
        lane,
        runtime_root=args.runtime_root,
        run_id=run_id,
    )
    command = build_adaptive_command(
        args=args,
        lane=lane,
        constraint=constraint,
        models_file=models_file,
    )
    job = {
        "constraint": constraint,
        "lane": lane.safe_summary(),
        "models_file": str(models_file),
        "command": command,
        "started_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
    }
    if args.dry_run:
        print(
            f"[dry-run] C{constraint} -> {lane.lane_id} "
            f"provider={lane.provider} key={lane.masked_key}"
        )
        print(f"[dry-run] {command_str(command)}")
        return {**job, "returncode": None, "elapsed_seconds": 0.0, "dry_run": True}

    log_dir = Path(args.log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)
    stdout_path = log_dir / f"distributed_c{constraint}_{lane.lane_id}.stdout.log"
    stderr_path = log_dir / f"distributed_c{constraint}_{lane.lane_id}.stderr.log"
    print(
        f"[distributed] starting C{constraint} lane={lane.lane_id} "
        f"provider={lane.provider}"
    )
    with (
        stdout_path.open("a", encoding="utf-8") as stdout,
        stderr_path.open(
            "a",
            encoding="utf-8",
        ) as stderr,
    ):
        completed = subprocess.run(
            command,
            check=False,
            env=lane.env(),
            stdout=stdout,
            stderr=stderr,
        )
    elapsed = round(time.monotonic() - started, 3)
    print(
        f"[distributed] finished C{constraint} lane={lane.lane_id} "
        f"returncode={completed.returncode} elapsed={elapsed:.1f}s"
    )
    return {
        **job,
        "returncode": completed.returncode,
        "elapsed_seconds": elapsed,
        "stdout": str(stdout_path),
        "stderr": str(stderr_path),
        "dry_run": False,
    }


def run_shard_job(
    *,
    args: argparse.Namespace,
    lane: ProviderLane,
    constraint: int,
    run_id: str,
) -> dict[str, Any]:
    started = time.monotonic()
    shard_path = shard_path_for_lane(args.shard_dir, constraint, lane.lane_id)
    if not shard_path.exists():
        raise FileNotFoundError(f"shard not found for {lane.lane_id}: {shard_path}")
    models_file = write_runtime_models_file(
        lane,
        runtime_root=args.runtime_root,
        run_id=run_id,
    )
    job_output_root = Path(args.output_root) / lane.lane_id
    job_split_dir = Path(args.split_root) / lane.lane_id
    job_args = argparse.Namespace(**vars(args))
    job_args.personas = str(shard_path)
    job_args.output_root = str(job_output_root)
    job_args.split_dir = str(job_split_dir)
    command = build_adaptive_command(
        args=job_args,
        lane=lane,
        constraint=constraint,
        models_file=models_file,
    )
    job = {
        "constraint": constraint,
        "lane": lane.safe_summary(),
        "shard_path": str(shard_path),
        "output_root": str(job_output_root),
        "split_dir": str(job_split_dir),
        "models_file": str(models_file),
        "command": command,
        "started_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
    }
    if args.dry_run:
        print(
            f"[dry-run] C{constraint} shard={shard_path.name} -> {lane.lane_id} "
            f"output_root={job_output_root}"
        )
        print(f"[dry-run] {command_str(command)}")
        return {**job, "returncode": None, "elapsed_seconds": 0.0, "dry_run": True}

    log_dir = Path(args.log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)
    job_output_root.mkdir(parents=True, exist_ok=True)
    job_split_dir.mkdir(parents=True, exist_ok=True)
    stdout_path = log_dir / f"distributed_c{constraint}_{lane.lane_id}_shard.stdout.log"
    stderr_path = log_dir / f"distributed_c{constraint}_{lane.lane_id}_shard.stderr.log"
    print(
        f"[distributed] starting C{constraint} shard={shard_path.name} "
        f"lane={lane.lane_id} provider={lane.provider}"
    )
    with (
        stdout_path.open("a", encoding="utf-8") as stdout,
        stderr_path.open("a", encoding="utf-8") as stderr,
    ):
        completed = subprocess.run(
            command,
            check=False,
            env=lane.env(),
            stdout=stdout,
            stderr=stderr,
        )
    elapsed = round(time.monotonic() - started, 3)
    print(
        f"[distributed] finished C{constraint} shard={shard_path.name} "
        f"lane={lane.lane_id} returncode={completed.returncode} elapsed={elapsed:.1f}s"
    )
    return {
        **job,
        "returncode": completed.returncode,
        "elapsed_seconds": elapsed,
        "stdout": str(stdout_path),
        "stderr": str(stderr_path),
        "dry_run": False,
    }


def cmd_run(args: argparse.Namespace) -> int:
    lanes = lanes_by_id(load_lanes(args.config))
    constraints = parse_ints(args.constraints, (2, 3, 4, 5))
    run_id = args.run_id or utc_run_id()
    jobs: list[tuple[int, ProviderLane]] = []
    for constraint in constraints:
        lane_id = DEFAULT_CONSTRAINT_LANES.get(constraint)
        if not lane_id:
            raise ValueError(f"no default lane mapping for C{constraint}")
        jobs.append((constraint, lanes[lane_id]))

    Path(args.output_root).mkdir(parents=True, exist_ok=True)
    Path(args.split_dir).mkdir(parents=True, exist_ok=True)
    Path(args.log_dir).mkdir(parents=True, exist_ok=True)
    Path(args.runtime_root).mkdir(parents=True, exist_ok=True)
    results: list[dict[str, Any]] = []
    with ThreadPoolExecutor(
        max_workers=max(1, min(args.parallel_lanes, len(jobs)))
    ) as executor:
        futures = [
            executor.submit(
                run_lane_job,
                args=args,
                lane=lane,
                constraint=constraint,
                run_id=run_id,
            )
            for constraint, lane in jobs
        ]
        for future in as_completed(futures):
            results.append(future.result())
    results.sort(key=lambda item: item["constraint"])
    manifest = {
        "run_id": run_id,
        "created_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "constraints": constraints,
        "output_root": str(args.output_root),
        "split_dir": str(args.split_dir),
        "log_dir": str(args.log_dir),
        "jobs": results,
    }
    out = Path(args.manifest)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[distributed] wrote {out}")
    if args.dry_run:
        return 0
    return 0 if all(job.get("returncode") == 0 for job in results) else 1


def cmd_run_shards(args: argparse.Namespace) -> int:
    lanes = lanes_by_id(load_lanes(args.config))
    lane_ids = list(args.lane_ids or DEFAULT_LANE_ORDER)
    missing = [lane_id for lane_id in lane_ids if lane_id not in lanes]
    if missing:
        raise ValueError(f"unknown lane ids: {', '.join(missing)}")
    run_id = args.run_id or utc_run_id()
    jobs = [lanes[lane_id] for lane_id in lane_ids]

    Path(args.output_root).mkdir(parents=True, exist_ok=True)
    Path(args.split_root).mkdir(parents=True, exist_ok=True)
    Path(args.log_dir).mkdir(parents=True, exist_ok=True)
    Path(args.runtime_root).mkdir(parents=True, exist_ok=True)
    results: list[dict[str, Any]] = []
    with ThreadPoolExecutor(
        max_workers=max(1, min(args.parallel_lanes, len(jobs)))
    ) as executor:
        futures = [
            executor.submit(
                run_shard_job,
                args=args,
                lane=lane,
                constraint=args.constraint,
                run_id=run_id,
            )
            for lane in jobs
        ]
        for future in as_completed(futures):
            results.append(future.result())
    results.sort(key=lambda item: item["lane"]["lane_id"])
    manifest = {
        "run_id": run_id,
        "created_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "mode": "sharded",
        "constraint": args.constraint,
        "shard_dir": str(args.shard_dir),
        "output_root": str(args.output_root),
        "split_root": str(args.split_root),
        "log_dir": str(args.log_dir),
        "jobs": results,
    }
    out = Path(args.manifest)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[distributed] wrote {out}")
    if args.dry_run:
        return 0
    return 0 if all(job.get("returncode") == 0 for job in results) else 1


def read_jsonl_stats(path: Path) -> dict[str, int]:
    rows = ok = failed = 0
    if not path.exists():
        return {"rows": 0, "ok": 0, "failed": 0}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        rows += 1
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            failed += 1
            continue
        if payload.get("status") == "ok":
            ok += 1
        else:
            failed += 1
    return {"rows": rows, "ok": ok, "failed": failed}


def cmd_status(args: argparse.Namespace) -> int:
    manifest_path = Path(args.manifest)
    if not manifest_path.exists():
        raise FileNotFoundError(f"manifest not found: {manifest_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    output_root = Path(manifest.get("output_root") or args.output_root)
    lines = [
        "| constraint | lane | suite | model | target | rows | ok | failed |",
        "| --- | --- | --- | --- | --- | ---: | ---: | ---: |",
    ]
    for job in manifest.get("jobs", []):
        constraint = int(job["constraint"])
        lane_id = job["lane"]["lane_id"]
        job_output_root = Path(job.get("output_root") or output_root)
        for suite in ("baseline", "ablation"):
            suite_dir = job_output_root / f"c{constraint}" / suite
            if not suite_dir.exists():
                continue
            for model_dir in sorted(
                path for path in suite_dir.iterdir() if path.is_dir()
            ):
                for target_dir in sorted(
                    path for path in model_dir.iterdir() if path.is_dir()
                ):
                    target = target_dir.name
                    stats = read_jsonl_stats(target_dir / "reports" / f"{target}.jsonl")
                    lines.append(
                        f"| C{constraint} | {lane_id} | {suite} | "
                        f"{model_dir.name} | {target} | {stats['rows']} | "
                        f"{stats['ok']} | {stats['failed']} |"
                    )
    text = "\n".join(lines)
    print(text)
    if args.output_md:
        out = Path(args.output_md)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text("# Distributed C2-C5 Status\n\n" + text + "\n", encoding="utf-8")
        print(f"[status] wrote {out}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Distributed unified benchmark over provider API lanes."
    )
    sub = parser.add_subparsers(dest="command", required=True)

    init = sub.add_parser("init-config")
    init.add_argument("--base-dir", default=".")
    init.add_argument("--output", default=str(DEFAULT_CONFIG_PATH))
    init.set_defaults(func=cmd_init_config)

    validate = sub.add_parser("validate-config")
    validate.add_argument("--config", default=str(DEFAULT_CONFIG_PATH))
    validate.set_defaults(func=cmd_validate_config)

    health = sub.add_parser("healthcheck")
    health.add_argument("--config", default=str(DEFAULT_CONFIG_PATH))
    health.add_argument("--output-json", default=str(DEFAULT_HEALTH_JSON))
    health.add_argument("--output-md", default=str(DEFAULT_HEALTH_MD))
    health.add_argument("--timeout", type=float, default=60.0)
    health.add_argument("--parallel-lanes", type=int, default=4)
    health.add_argument("--fail-fast", action="store_true")
    health.set_defaults(func=cmd_healthcheck)

    shard = sub.add_parser("shard-cases")
    shard.add_argument("--personas", default=str(DEFAULT_PERSONAS))
    shard.add_argument("--constraint-count", type=int, default=6)
    shard.add_argument("--shards", type=int, default=len(DEFAULT_LANE_ORDER))
    shard.add_argument("--output-dir", default=str(DEFAULT_C6_SHARD_DIR))
    shard.add_argument("--lane-ids", nargs="*", default=list(DEFAULT_LANE_ORDER))
    shard.set_defaults(func=cmd_shard_cases)

    run = sub.add_parser("run")
    run.add_argument("--config", default=str(DEFAULT_CONFIG_PATH))
    run.add_argument(
        "--mode",
        choices=("all", "baseline", "ablation"),
        default="all",
    )
    run.add_argument("--constraints", nargs="*", default=None)
    run.add_argument("--personas", default=str(DEFAULT_PERSONAS))
    run.add_argument("--output-root", default=str(DEFAULT_OUTPUT_ROOT))
    run.add_argument("--split-dir", default=str(DEFAULT_SPLIT_DIR))
    run.add_argument("--log-dir", default=str(DEFAULT_LOG_DIR))
    run.add_argument("--manifest", default=str(DEFAULT_MANIFEST))
    run.add_argument("--runtime-root", default=str(DEFAULT_RUNTIME_ROOT))
    run.add_argument(
        "--baseline-targets", nargs="+", default=list(DEFAULT_BASELINE_TARGETS)
    )
    run.add_argument(
        "--ablation-targets", nargs="+", default=list(DEFAULT_ABLATION_TARGETS)
    )
    run.add_argument("--parallel-lanes", type=int, default=4)
    run.add_argument("--parallel-models", type=int, default=5)
    run.add_argument("--initial-concurrency", type=int, default=10)
    run.add_argument("--override-concurrency", type=int, default=None)
    run.add_argument("--min-concurrency", type=int, default=2)
    run.add_argument("--batch-attempts", type=int, default=6)
    run.add_argument("--case-retries", type=int, default=2)
    run.add_argument("--request-timeout", type=float, default=120.0)
    run.add_argument("--case-timeout", type=float, default=600.0)
    run.add_argument("--failure-threshold", type=float, default=0.30)
    run.add_argument("--timeout-threshold", type=float, default=0.20)
    run.add_argument("--max-turns", type=int, default=6)
    run.add_argument("--max-models", type=int, default=None)
    run.add_argument("--run-id", default=None)
    run.add_argument("--dry-run", action="store_true")
    run.set_defaults(func=cmd_run)

    run_shards = sub.add_parser("run-shards")
    run_shards.add_argument("--config", default=str(DEFAULT_CONFIG_PATH))
    run_shards.add_argument(
        "--mode",
        choices=("all", "baseline", "ablation"),
        default="all",
    )
    run_shards.add_argument("--constraint", type=int, default=6)
    run_shards.add_argument("--shard-dir", default=str(DEFAULT_C6_SHARD_DIR))
    run_shards.add_argument("--output-root", default=str(DEFAULT_C6_OUTPUT_ROOT))
    run_shards.add_argument("--split-root", default=str(DEFAULT_C6_SPLIT_ROOT))
    run_shards.add_argument("--log-dir", default=str(DEFAULT_C6_LOG_DIR))
    run_shards.add_argument("--manifest", default=str(DEFAULT_C6_MANIFEST))
    run_shards.add_argument("--runtime-root", default=str(DEFAULT_RUNTIME_ROOT))
    run_shards.add_argument("--lane-ids", nargs="*", default=list(DEFAULT_LANE_ORDER))
    run_shards.add_argument(
        "--baseline-targets", nargs="+", default=list(DEFAULT_MAINLINE_BASELINE_TARGETS)
    )
    run_shards.add_argument(
        "--ablation-targets", nargs="+", default=list(DEFAULT_ABLATION_TARGETS)
    )
    run_shards.add_argument("--parallel-lanes", type=int, default=4)
    run_shards.add_argument("--parallel-models", type=int, default=5)
    run_shards.add_argument("--initial-concurrency", type=int, default=10)
    run_shards.add_argument("--override-concurrency", type=int, default=None)
    run_shards.add_argument("--min-concurrency", type=int, default=2)
    run_shards.add_argument("--batch-attempts", type=int, default=6)
    run_shards.add_argument("--case-retries", type=int, default=2)
    run_shards.add_argument("--request-timeout", type=float, default=120.0)
    run_shards.add_argument("--case-timeout", type=float, default=600.0)
    run_shards.add_argument("--failure-threshold", type=float, default=0.30)
    run_shards.add_argument("--timeout-threshold", type=float, default=0.20)
    run_shards.add_argument("--max-turns", type=int, default=6)
    run_shards.add_argument("--max-models", type=int, default=None)
    run_shards.add_argument("--run-id", default=None)
    run_shards.add_argument("--dry-run", action="store_true")
    run_shards.set_defaults(func=cmd_run_shards)

    status = sub.add_parser("status")
    status.add_argument("--manifest", default=str(DEFAULT_MANIFEST))
    status.add_argument("--output-root", default=str(DEFAULT_OUTPUT_ROOT))
    status.add_argument("--output-md", default="")
    status.set_defaults(func=cmd_status)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    raise SystemExit(args.func(args))


if __name__ == "__main__":
    main()
