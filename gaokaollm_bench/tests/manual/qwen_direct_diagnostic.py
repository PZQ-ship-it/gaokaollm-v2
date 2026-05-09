"""Layered diagnostic for Qwen direct major-classification failures.

The goal is to isolate the failing layer:

1. Basic API/model availability.
2. OpenAI-compatible json_object response mode.
3. OpenAI-compatible json_schema response mode.
4. Tiny-label major classification.
5. Full-label major classification.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import time
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from gaokaollm_bench.chains.major_classification import classify_major
from gaokaollm_bench.constrains.llm import DEFAULT_SMALL_MODEL, ENV_SMALL_MODEL
from gaokaollm_bench.constrains.paths import (
    MAJOR_ABLATION_BEST_LABEL_MAP,
    MAJOR_FINAL_TREE,
    OUTPUTS_DIR,
)
from gaokaollm_bench.contracts.llm_io import MajorLabelOption
from gaokaollm_bench.data_gen.major_embedding import _normalize_text
from gaokaollm_bench.data_gen.major_tree import load_major_tree
from gaokaollm_bench.llm.openai_chat import OpenAIChatClient


ValidationFn = Callable[[dict[str, Any]], tuple[bool, str]]

DEFAULT_OUTPUT = OUTPUTS_DIR / "qwen_direct_diagnostic.json"
DEFAULT_MAJOR_NAME = "\u4e91\u8ba1\u7b97\u6280\u672f\u5e94\u7528"
PREFERRED_TINY_LABELS = [
    "vocational_computer_network",
    "computer_science",
    "data_ai",
    "software_engineering",
    "medical_tcm",
]


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Diagnose Qwen direct LLM failures")
    parser.add_argument("--model", default=None)
    parser.add_argument("--major-name", default=DEFAULT_MAJOR_NAME)
    parser.add_argument("--request-timeout", type=float, default=60.0)
    parser.add_argument("--label-map", default=str(MAJOR_ABLATION_BEST_LABEL_MAP))
    parser.add_argument("--major-tree", default=str(MAJOR_FINAL_TREE))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument(
        "--include-full-labels",
        action="store_true",
        help="Also test the current full-label direct classification prompt.",
    )
    parser.add_argument(
        "--continue-after-basic-failure",
        action="store_true",
        help="Continue deeper tests even if the plain-text API call fails.",
    )
    return parser.parse_args()


def _load_label_map(path: Path) -> tuple[dict[str, int], dict[int, str]]:
    label_map = json.loads(path.read_text(encoding="utf-8"))
    return label_map, {int(v): k for k, v in label_map.items()}


def _node_name(tree: dict[str, Any], label: str) -> str:
    node = (tree.get("nodes") or {}).get(label) or {}
    return str(node.get("label") or label)


def _build_label_options(
    label_ids: list[str], tree: dict[str, Any]
) -> list[MajorLabelOption]:
    return [
        MajorLabelOption(label=label_id, label_name=_node_name(tree, label_id))
        for label_id in label_ids
    ]


def _parse_json_maybe(text: str) -> Any:
    try:
        return json.loads(text)
    except Exception:
        return None


def _apply_validation(
    record: dict[str, Any], validator: ValidationFn | None
) -> dict[str, Any]:
    if validator is None or record.get("status") != "ok":
        return record
    valid, note = validator(record)
    record["semantic_valid"] = valid
    record["validation_note"] = note
    if not valid:
        record["status"] = "invalid_output"
    return record


async def _run_case(
    name: str, coro: Awaitable[Any], validator: ValidationFn | None = None
) -> dict[str, Any]:
    started = time.perf_counter()
    try:
        result = await coro
        duration = time.perf_counter() - started
        if isinstance(result, str):
            record = {
                "name": name,
                "status": "ok",
                "duration_sec": round(duration, 3),
                "raw_content": result,
                "parsed_json": _parse_json_maybe(result),
            }
            return _apply_validation(record, validator)
        if hasattr(result, "model_dump"):
            record = {
                "name": name,
                "status": "ok",
                "duration_sec": round(duration, 3),
                "result": result.model_dump(),
            }
            return _apply_validation(record, validator)
        record = {
            "name": name,
            "status": "ok",
            "duration_sec": round(duration, 3),
            "result": result,
        }
        return _apply_validation(record, validator)
    except Exception as exc:  # pragma: no cover - external API behavior
        duration = time.perf_counter() - started
        return {
            "name": name,
            "status": "error",
            "duration_sec": round(duration, 3),
            "error_type": type(exc).__name__,
            "error": str(exc),
        }


def _validate_plain(record: dict[str, Any]) -> tuple[bool, str]:
    text = str(record.get("raw_content") or "").strip()
    return text == "OK", f"expected literal OK, got {text!r}"


def _validate_minimal_json(record: dict[str, Any]) -> tuple[bool, str]:
    parsed = record.get("parsed_json")
    valid = (
        isinstance(parsed, dict)
        and parsed.get("ok") is True
        and parsed.get("label") == "yes"
    )
    return valid, f"expected ok=true,label=yes, got {parsed!r}"


def _label_validator(label_ids: set[str]) -> ValidationFn:
    def _validate(record: dict[str, Any]) -> tuple[bool, str]:
        parsed = record.get("parsed_json")
        selected = parsed.get("selected_label") if isinstance(parsed, dict) else None
        valid = selected in label_ids
        return valid, f"expected selected_label in candidates, got {selected!r}"

    return _validate


def _validate_chain_label(record: dict[str, Any]) -> tuple[bool, str]:
    result = record.get("result") or {}
    valid = bool(result.get("label_valid"))
    return valid, f"expected label_valid=true, got error={result.get('error')!r}"


def _minimal_schema() -> dict[str, Any]:
    return {
        "type": "json_schema",
        "json_schema": {
            "name": "qwen_minimal_diagnostic",
            "strict": True,
            "schema": {
                "type": "object",
                "additionalProperties": False,
                "required": ["ok", "label"],
                "properties": {
                    "ok": {"type": "boolean"},
                    "label": {"type": "string", "enum": ["yes", "no"]},
                },
            },
        },
    }


def _classification_schema(label_options: list[MajorLabelOption]) -> dict[str, Any]:
    return {
        "type": "json_schema",
        "json_schema": {
            "name": "qwen_tiny_major_classification",
            "strict": True,
            "schema": {
                "type": "object",
                "additionalProperties": False,
                "required": ["major_name", "selected_label"],
                "properties": {
                    "major_name": {"type": "string"},
                    "selected_label": {
                        "type": "string",
                        "enum": [item.label for item in label_options],
                    },
                },
            },
        },
    }


def _classify_prompt(major_name: str, label_options: list[MajorLabelOption]) -> str:
    return json.dumps(
        {
            "instruction": (
                "Choose exactly one selected_label from labels. Output JSON only."
            ),
            "item": {
                "major_name": major_name,
                "normalized_text": _normalize_text(major_name),
            },
            "labels": [item.model_dump(exclude_none=True) for item in label_options],
            "output_schema": {"major_name": "string", "selected_label": "label id"},
        },
        ensure_ascii=False,
    )


def _case_status(results: dict[str, dict[str, Any]], name: str) -> str:
    return str(results.get(name, {}).get("status") or "missing")


def _chain_label_valid(results: dict[str, dict[str, Any]], name: str) -> bool | None:
    if name not in results:
        return None
    payload = results.get(name, {}).get("result") or {}
    return bool(payload.get("label_valid"))


def _chain_error(results: dict[str, dict[str, Any]], name: str) -> str | None:
    payload = results.get(name, {}).get("result") or {}
    return payload.get("error") or results.get(name, {}).get("error")


def _infer_conclusion(results_list: list[dict[str, Any]]) -> dict[str, Any]:
    results = {item["name"]: item for item in results_list}
    plain = _case_status(results, "plain_text")
    json_object = _case_status(results, "json_object_minimal")
    json_schema = _case_status(results, "json_schema_minimal")
    tiny_raw_schema = _case_status(results, "tiny_label_raw_json_schema")
    tiny_chain_valid = _chain_label_valid(results, "tiny_label_lcel_chain")
    full_chain_valid = _chain_label_valid(results, "full_label_lcel_chain")
    full_error = _chain_error(results, "full_label_lcel_chain")

    if tiny_chain_valid and full_chain_valid is None:
        layer = "full_label_not_tested"
        conclusion = "Tiny-label LCEL classification works; full-label classification was not run."
    elif tiny_chain_valid and not full_chain_valid:
        layer = "full_label_enum_or_prompt_scale"
        conclusion = (
            "Tiny-label LCEL classification works but full-label LCEL classification "
            "fails; the issue is full enum/prompt scale or response latency."
        )
        if full_error:
            conclusion += f" Failure signal: {full_error}"
    elif tiny_chain_valid and full_chain_valid:
        layer = "not_reproduced"
        conclusion = (
            "Direct classification failure was not reproduced in the LCEL chain; "
            "historical failures are likely concurrency, timeout, or service fluctuation."
        )
    elif plain != "ok":
        layer = "api_or_model_availability"
        conclusion = (
            "Plain text call failed or returned invalid content; the first failure "
            "layer is API/model availability, gateway behavior, or SDK response handling."
        )
    elif json_object != "ok":
        layer = "json_object_response_format"
        conclusion = (
            "Plain text works but json_object fails or returns invalid content; "
            "the issue is JSON mode compatibility or SDK response handling."
        )
    elif json_schema != "ok":
        layer = "json_schema_response_format"
        conclusion = (
            "json_object works but minimal json_schema fails or returns invalid content; "
            "the model/gateway has unstable json_schema support."
        )
    elif tiny_raw_schema != "ok" and not tiny_chain_valid:
        layer = "small_label_classification_prompt"
        conclusion = (
            "Minimal schema works but tiny-label classification fails; "
            "the issue is the classification instruction or label semantics."
        )
    else:
        layer = "mixed_or_inconclusive"
        conclusion = (
            "Mixed result; inspect each case's error_type, duration_sec, raw_content, "
            "and semantic_valid fields."
        )

    return {
        "failure_layer": layer,
        "conclusion": conclusion,
        "observations": {
            "plain_text": plain,
            "json_object_minimal": json_object,
            "json_schema_minimal": json_schema,
            "tiny_label_raw_json_schema": tiny_raw_schema,
            "tiny_label_lcel_chain_label_valid": tiny_chain_valid,
            "full_label_lcel_chain_label_valid": full_chain_valid,
        },
    }


async def _main_async(args: argparse.Namespace) -> dict[str, Any]:
    load_dotenv()
    model = args.model or os.getenv(ENV_SMALL_MODEL) or DEFAULT_SMALL_MODEL
    client = OpenAIChatClient(timeout=args.request_timeout, max_retries=0)
    label_map, inv_label_map = _load_label_map(Path(args.label_map))
    tree = load_major_tree(args.major_tree)

    tiny_ids = [label_id for label_id in PREFERRED_TINY_LABELS if label_id in label_map]
    if len(tiny_ids) < 3:
        tiny_ids = [inv_label_map[idx] for idx in sorted(inv_label_map)[:5]]
    tiny_options = _build_label_options(tiny_ids, tree)
    full_options = _build_label_options(
        [inv_label_map[idx] for idx in sorted(inv_label_map)], tree
    )

    messages_plain = [{"role": "user", "content": "Output exactly: OK"}]
    messages_json = [
        {"role": "user", "content": 'Output JSON only: {"ok": true, "label": "yes"}'}
    ]
    messages_tiny = [
        {"role": "user", "content": _classify_prompt(args.major_name, tiny_options)}
    ]
    tiny_label_ids = {item.label for item in tiny_options}

    cases: list[tuple[str, Callable[[], Awaitable[Any]], ValidationFn | None]] = [
        (
            "plain_text",
            lambda: client.complete_json(
                model=model, messages=messages_plain, temperature=0, max_tokens=16
            ),
            _validate_plain,
        ),
        (
            "json_object_minimal",
            lambda: client.complete_json(
                model=model,
                messages=messages_json,
                response_format={"type": "json_object"},
                temperature=0,
                max_tokens=64,
            ),
            _validate_minimal_json,
        ),
        (
            "json_schema_minimal",
            lambda: client.complete_json(
                model=model,
                messages=messages_json,
                response_format=_minimal_schema(),
                temperature=0,
                max_tokens=64,
            ),
            _validate_minimal_json,
        ),
        (
            "tiny_label_raw_json_schema",
            lambda: client.complete_json(
                model=model,
                messages=messages_tiny,
                response_format=_classification_schema(tiny_options),
                temperature=0,
                max_tokens=128,
            ),
            _label_validator(tiny_label_ids),
        ),
        (
            "tiny_label_lcel_chain",
            lambda: classify_major(
                llm_client=client,
                model=model,
                major_name=args.major_name,
                normalized_text=_normalize_text(args.major_name),
                label_options=tiny_options,
                allow_null=False,
                labels_only=False,
            ),
            _validate_chain_label,
        ),
    ]
    if args.include_full_labels:
        cases.append(
            (
                "full_label_lcel_chain",
                lambda: classify_major(
                    llm_client=client,
                    model=model,
                    major_name=args.major_name,
                    normalized_text=_normalize_text(args.major_name),
                    label_options=full_options,
                    allow_null=False,
                    labels_only=False,
                ),
                _validate_chain_label,
            )
        )

    results = []
    for name, make_coro, validator in cases:
        print(f"[diagnostic] running {name} ...", flush=True)
        item = await _run_case(name, make_coro(), validator)
        print(
            f"[diagnostic] {name}: {item['status']} in {item['duration_sec']}s",
            flush=True,
        )
        results.append(item)
        if (
            name == "plain_text"
            and item["status"] != "ok"
            and not args.continue_after_basic_failure
        ):
            results.extend(
                [
                    {"name": case_name, "status": "skipped_due_to_basic_failure"}
                    for case_name, _, _ in cases[1:]
                ]
            )
            break

    report = {
        "model": model,
        "major_name": args.major_name,
        "request_timeout": args.request_timeout,
        "include_full_labels": args.include_full_labels,
        "continue_after_basic_failure": args.continue_after_basic_failure,
        "results": results,
        "summary": _infer_conclusion(results),
    }
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return report


def main() -> None:
    args = _parse_args()
    report = asyncio.run(_main_async(args))
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    print(f"Wrote diagnostic report to {args.output}")


if __name__ == "__main__":
    main()
