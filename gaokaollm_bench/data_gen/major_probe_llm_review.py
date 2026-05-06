"""Use an LLM to review low-confidence probe candidates without editing the tree."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv


DEFAULT_INPUT = Path("gaokaollm_bench/outputs/major_probe_review_candidates.json")
DEFAULT_OUTPUT = Path("gaokaollm_bench/outputs/major_probe_review_candidates_llm_reviewed.json")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="LLM-review low-confidence major probe candidates."
    )
    parser.add_argument("--input", default=str(DEFAULT_INPUT))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument(
        "--in-place",
        action="store_true",
        help="Overwrite --input instead of writing --output.",
    )
    parser.add_argument(
        "--model",
        default=None,
        help="LLM model name. Defaults to LLM_REVIEW_MODEL, OPENAI_MODEL, or gpt-5.2.",
    )
    parser.add_argument("--api-key-env", default="OPENAI_API_KEY")
    parser.add_argument("--base-url-env", default="OPENAI_BASE_URL")
    parser.add_argument("--batch-size", type=int, default=10)
    parser.add_argument(
        "--per-item",
        action="store_true",
        help="Call the LLM once per item instead of reviewing multiple items in one prompt.",
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=10,
        help="Maximum concurrent API calls in --per-item mode.",
    )
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument(
        "--include-manual-overrides",
        action="store_true",
        help="Also review rows whose recommended_label no longer equals probe top-1.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-review rows that already contain llm_review or review_decision.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Call the LLM and print summary, but do not write output.",
    )
    parser.add_argument(
        "--keep-invalid-ssl-env",
        action="store_true",
        help="Do not unset SSL_CERT_FILE/REQUESTS_CA_BUNDLE when they point to missing files.",
    )
    return parser.parse_args()


def _sanitize_ssl_env(*, keep_invalid_ssl_env: bool) -> list[str]:
    """Unset broken SSL env vars that make httpx fail before making a request."""

    if keep_invalid_ssl_env:
        return []

    removed = []
    for env_name in ("SSL_CERT_FILE", "REQUESTS_CA_BUNDLE"):
        value = os.environ.get(env_name)
        if value and not Path(value).exists():
            os.environ.pop(env_name, None)
            removed.append(env_name)
    return removed


def _load_rows(path: Path) -> list[dict[str, Any]]:
    rows = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(rows, list):
        raise ValueError("Input JSON must be a list")
    return rows


def _candidate_payload(row: dict[str, Any]) -> dict[str, Any]:
    candidates = []
    for pred in row.get("probe_predictions") or []:
        label = pred.get("label")
        label_name = pred.get("label_name")
        if label and label_name:
            candidates.append({"label": str(label), "label_name": str(label_name)})
    return {"major_name": str(row.get("major_name") or ""), "candidates": candidates}


def _top1_label(row: dict[str, Any]) -> str | None:
    predictions = row.get("probe_predictions") or []
    if not predictions:
        return None
    return predictions[0].get("label")


def _should_review(row: dict[str, Any], *, include_manual_overrides: bool, force: bool) -> bool:
    if row.get("review_status") != "low_confidence":
        return False
    if not force and (row.get("review_decision") or row.get("llm_review")):
        return False
    if not row.get("probe_predictions"):
        return False
    if not include_manual_overrides and row.get("recommended_label") != _top1_label(row):
        return False
    return True


def _system_prompt() -> str:
    return (
        "你是高考专业分类审校员。你只允许从给定 candidates 中选择最合适的一个分类，"
        "也可以在候选都不合适时返回 null 表示不修改。"
        "不要使用概率，因为用户不会提供概率。"
        "输出必须是 JSON，格式为 {\"items\":[{\"major_name\":...,\"selected_label\":...或null,\"reason\":...}]}。"
    )


def _user_prompt(items: list[dict[str, Any]]) -> str:
    return json.dumps({"items": items}, ensure_ascii=False, indent=2)


def _parse_llm_json(content: str) -> dict[str, Any]:
    text = content.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.startswith("json"):
            text = text[4:]
    return json.loads(text.strip())


async def _review_batch(
    items: list[dict[str, Any]],
    *,
    model: str,
    api_key: str,
    base_url: str | None,
) -> dict[str, dict[str, Any]]:
    from openai import AsyncOpenAI

    client = AsyncOpenAI(api_key=api_key, base_url=base_url)
    response = await client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": _system_prompt()},
            {"role": "user", "content": _user_prompt(items)},
        ],
        response_format={"type": "json_object"},
    )
    content = response.choices[0].message.content or "{}"
    parsed = _parse_llm_json(content)
    reviewed = {}
    for item in parsed.get("items") or []:
        major_name = item.get("major_name")
        if major_name:
            reviewed[str(major_name)] = item
    return reviewed


async def _review_one(
    item: dict[str, Any],
    *,
    model: str,
    api_key: str,
    base_url: str | None,
    semaphore: asyncio.Semaphore,
) -> tuple[str, dict[str, Any] | None, str | None]:
    async with semaphore:
        try:
            reviewed = await _review_batch(
                [item],
                model=model,
                api_key=api_key,
                base_url=base_url,
            )
            major_name = str(item.get("major_name") or "")
            return major_name, reviewed.get(major_name), None
        except Exception as exc:  # pragma: no cover - defensive around external APIs
            major_name = str(item.get("major_name") or "")
            return major_name, None, f"{type(exc).__name__}: {exc}"


def _apply_review(row: dict[str, Any], item: dict[str, Any]) -> bool:
    candidates = {
        str(pred["label"]): str(pred["label_name"])
        for pred in row.get("probe_predictions") or []
        if pred.get("label") and pred.get("label_name")
    }
    selected_label = item.get("selected_label")
    if selected_label is None or selected_label == "":
        row["llm_review"] = {
            "selected_label": None,
            "selected_label_name": None,
            "changed": False,
            "reason": item.get("reason") or "",
        }
        row["review_notes"] = item.get("reason") or row.get("review_notes") or ""
        return False

    selected_label = str(selected_label)
    if selected_label not in candidates:
        row["llm_review"] = {
            "selected_label": None,
            "selected_label_name": None,
            "changed": False,
            "invalid_selected_label": selected_label,
            "reason": item.get("reason") or "",
        }
        return False

    old_label = row.get("recommended_label")
    old_label_name = row.get("recommended_label_name")
    selected_label_name = candidates[selected_label]
    row["recommended_label"] = selected_label
    row["recommended_label_name"] = selected_label_name
    row["review_status"] = "llm_reviewed"
    row["review_decision"] = selected_label
    row["review_notes"] = item.get("reason") or row.get("review_notes") or ""
    row["llm_review"] = {
        "selected_label": selected_label,
        "selected_label_name": selected_label_name,
        "changed": old_label != selected_label,
        "old_label": old_label,
        "old_label_name": old_label_name,
        "reason": item.get("reason") or "",
    }
    return old_label != selected_label


async def _main_async(args: argparse.Namespace) -> tuple[list[dict[str, Any]], dict[str, int]]:
    load_dotenv()
    removed_ssl_env = _sanitize_ssl_env(keep_invalid_ssl_env=args.keep_invalid_ssl_env)
    api_key = os.getenv(args.api_key_env)
    if not api_key:
        raise RuntimeError(f"{args.api_key_env} is required")
    base_url = os.getenv(args.base_url_env) or None
    model = args.model or os.getenv("LLM_REVIEW_MODEL") or os.getenv("OPENAI_MODEL") or "gpt-5.2"

    rows = _load_rows(Path(args.input))
    review_indices = [
        idx
        for idx, row in enumerate(rows)
        if _should_review(
            row,
            include_manual_overrides=args.include_manual_overrides,
            force=args.force,
        )
    ]
    if args.limit is not None:
        if args.limit < 1:
            raise ValueError("--limit must be at least 1")
        review_indices = review_indices[: args.limit]

    stats = {
        "eligible": len(review_indices),
        "reviewed": 0,
        "changed": 0,
        "unchanged_or_no_change": 0,
        "removed_invalid_ssl_env": removed_ssl_env,
    }

    total_batches = (len(review_indices) + args.batch_size - 1) // args.batch_size if review_indices else 0
    print(
        f"Starting LLM review: eligible={len(review_indices)} "
        f"batch_size={args.batch_size} batches={total_batches}",
        flush=True,
    )

    if args.batch_size < 1:
        raise ValueError("--batch-size must be at least 1")
    if args.concurrency < 1:
        raise ValueError("--concurrency must be at least 1")

    if args.per_item:
        total_batches = (
            (len(review_indices) + args.batch_size - 1) // args.batch_size
            if review_indices
            else 0
        )
        print(
            f"Per-item mode enabled: concurrency={args.concurrency} "
            f"items_per_progress_batch={args.batch_size}",
            flush=True,
        )
        semaphore = asyncio.Semaphore(args.concurrency)
        for batch_no, start in enumerate(range(0, len(review_indices), args.batch_size), start=1):
            batch_indices = review_indices[start : start + args.batch_size]
            payloads = [_candidate_payload(rows[idx]) for idx in batch_indices]
            print(
                f"Reviewing progress batch {batch_no}/{total_batches}: "
                f"{len(batch_indices)} parallel item calls",
                flush=True,
            )
            results = await asyncio.gather(
                *[
                    _review_one(
                        payload,
                        model=model,
                        api_key=api_key,
                        base_url=base_url,
                        semaphore=semaphore,
                    )
                    for payload in payloads
                ]
            )
            reviewed = {major_name: item for major_name, item, error in results if item}
            errors = {major_name: error for major_name, item, error in results if error}
            if errors:
                stats.setdefault("error_examples", [])
                for major_name, error in list(errors.items())[:3]:
                    if len(stats["error_examples"]) < 5:
                        stats["error_examples"].append(
                            {"major_name": major_name, "error": error}
                        )
            for idx in batch_indices:
                row = rows[idx]
                item = reviewed.get(str(row.get("major_name")))
                if not item:
                    if str(row.get("major_name")) in errors:
                        row.setdefault("llm_review_errors", []).append(
                            errors[str(row.get("major_name"))]
                        )
                    continue
                changed = _apply_review(row, item)
                stats["reviewed"] += 1
                if changed:
                    stats["changed"] += 1
                else:
                    stats["unchanged_or_no_change"] += 1
            stats.setdefault("errors", 0)
            stats["errors"] += len(errors)
            print(
                f"Finished progress batch {batch_no}/{total_batches}: "
                f"reviewed={stats['reviewed']} changed={stats['changed']} errors={stats['errors']}",
                flush=True,
            )
            if errors:
                first_major, first_error = next(iter(errors.items()))
                print(f"First error: {first_major}: {first_error}", flush=True)
        return rows, stats

    for batch_no, start in enumerate(range(0, len(review_indices), args.batch_size), start=1):
        batch_indices = review_indices[start : start + args.batch_size]
        print(
            f"Reviewing batch {batch_no}/{total_batches}: {len(batch_indices)} items",
            flush=True,
        )
        payloads = [_candidate_payload(rows[idx]) for idx in batch_indices]
        reviewed = await _review_batch(payloads, model=model, api_key=api_key, base_url=base_url)
        for idx in batch_indices:
            row = rows[idx]
            item = reviewed.get(str(row.get("major_name")))
            if not item:
                continue
            changed = _apply_review(row, item)
            stats["reviewed"] += 1
            if changed:
                stats["changed"] += 1
            else:
                stats["unchanged_or_no_change"] += 1
        print(
            f"Finished batch {batch_no}/{total_batches}: reviewed={stats['reviewed']} "
            f"changed={stats['changed']}",
            flush=True,
        )

    return rows, stats


def main() -> None:
    args = _parse_args()
    rows, stats = asyncio.run(_main_async(args))
    print(json.dumps(stats, ensure_ascii=False, indent=2))
    if args.dry_run:
        print("Dry run: output not written.")
        return

    output_path = Path(args.input) if args.in_place else Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote reviewed candidates to {output_path}")


if __name__ == "__main__":
    main()
