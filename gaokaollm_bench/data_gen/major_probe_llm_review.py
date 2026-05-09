"""Use an LLM to review low-confidence probe candidates without editing the tree."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from gaokaollm_bench.constrains.llm import (
    DEFAULT_REVIEW_MODEL,
    ENV_LLM_REVIEW_MODEL,
    ENV_OPENAI_API_KEY,
    ENV_OPENAI_BASE_URL,
    ENV_OPENAI_MODEL,
)
from gaokaollm_bench.constrains.paths import (
    MAJOR_REVIEW_CANDIDATES,
    MAJOR_REVIEW_CANDIDATES_REVIEWED,
)
from gaokaollm_bench.chains.major_review import review_major_candidates
from gaokaollm_bench.llm.openai_chat import OpenAIChatClient


DEFAULT_INPUT = MAJOR_REVIEW_CANDIDATES
DEFAULT_OUTPUT = MAJOR_REVIEW_CANDIDATES_REVIEWED


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
        help=f"LLM model name. Defaults to {ENV_LLM_REVIEW_MODEL}, {ENV_OPENAI_MODEL}, or {DEFAULT_REVIEW_MODEL}.",
    )
    parser.add_argument("--api-key-env", default=ENV_OPENAI_API_KEY)
    parser.add_argument("--base-url-env", default=ENV_OPENAI_BASE_URL)
    parser.add_argument("--batch-size", type=int, default=10)
    parser.add_argument(
        "--per-item",
        action="store_true",
        help="Use one prompt per request chunk and run those chunks in parallel.",
    )
    parser.add_argument(
        "--items-per-request",
        type=int,
        default=4,
        help="How many candidates to pack into each LLM request in --per-item mode.",
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=10,
        help="Maximum concurrent API calls in --per-item mode.",
    )
    parser.add_argument(
        "--request-timeout",
        type=float,
        default=60.0,
        help="Per-request timeout in seconds for the LLM API client.",
    )
    parser.add_argument(
        "--checkpoint-every-batch",
        action="store_true",
        help="Write the reviewed JSON after every progress batch.",
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


def _safe_print(message: str) -> None:
    encoding = sys.stdout.encoding or "utf-8"
    safe_message = message.encode(encoding, errors="replace").decode(
        encoding, errors="replace"
    )
    print(safe_message, flush=True)


def _output_path(args: argparse.Namespace) -> Path:
    return Path(args.input) if args.in_place else Path(args.output)


def _write_rows(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")


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


def _should_review(
    row: dict[str, Any], *, include_manual_overrides: bool, force: bool
) -> bool:
    if row.get("review_status") != "low_confidence":
        return False
    if not force and (row.get("review_decision") or row.get("llm_review")):
        return False
    if not row.get("probe_predictions"):
        return False
    if not include_manual_overrides and row.get("recommended_label") != _top1_label(
        row
    ):
        return False
    return True


def _chunk_items(
    items: list[dict[str, Any]], chunk_size: int
) -> list[list[dict[str, Any]]]:
    return [items[i : i + chunk_size] for i in range(0, len(items), chunk_size)]


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
    request_timeout: float,
) -> dict[str, dict[str, Any]]:
    client = OpenAIChatClient(
        api_key=api_key,
        base_url=base_url,
        timeout=request_timeout,
        max_retries=0,
    )
    return await review_major_candidates(
        llm_client=client,
        model=model,
        items=items,
    )


async def _review_one(
    item: dict[str, Any],
    *,
    model: str,
    api_key: str,
    base_url: str | None,
    semaphore: asyncio.Semaphore,
    request_timeout: float,
) -> tuple[str, dict[str, Any] | None, str | None]:
    async with semaphore:
        try:
            reviewed = await _review_batch(
                [item],
                model=model,
                api_key=api_key,
                base_url=base_url,
                request_timeout=request_timeout,
            )
            major_name = str(item.get("major_name") or "")
            return major_name, reviewed.get(major_name), None
        except Exception as exc:  # pragma: no cover - defensive around external APIs
            major_name = str(item.get("major_name") or "")
            return major_name, None, f"{type(exc).__name__}: {exc}"


async def _review_chunk(
    items: list[dict[str, Any]],
    *,
    model: str,
    api_key: str,
    base_url: str | None,
    request_timeout: float,
) -> tuple[dict[str, dict[str, Any]], str | None]:
    try:
        reviewed = await _review_batch(
            items,
            model=model,
            api_key=api_key,
            base_url=base_url,
            request_timeout=request_timeout,
        )
        return reviewed, None
    except Exception as exc:  # pragma: no cover - external API failure
        return {}, f"{type(exc).__name__}: {exc}"


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


async def _main_async(
    args: argparse.Namespace,
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    load_dotenv()
    removed_ssl_env = _sanitize_ssl_env(keep_invalid_ssl_env=args.keep_invalid_ssl_env)
    api_key = os.getenv(args.api_key_env)
    if not api_key:
        raise RuntimeError(f"{args.api_key_env} is required")
    base_url = os.getenv(args.base_url_env) or None
    model = (
        args.model
        or os.getenv(ENV_LLM_REVIEW_MODEL)
        or os.getenv(ENV_OPENAI_MODEL)
        or DEFAULT_REVIEW_MODEL
    )

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

    total_batches = (
        (len(review_indices) + args.batch_size - 1) // args.batch_size
        if review_indices
        else 0
    )
    _safe_print(
        f"Starting LLM review: eligible={len(review_indices)} "
        f"batch_size={args.batch_size} batches={total_batches}"
    )

    if args.batch_size < 1:
        raise ValueError("--batch-size must be at least 1")
    if args.concurrency < 1:
        raise ValueError("--concurrency must be at least 1")
    if args.request_timeout <= 0:
        raise ValueError("--request-timeout must be positive")
    if args.items_per_request < 1:
        raise ValueError("--items-per-request must be at least 1")

    if args.per_item:
        chunk_size = args.items_per_request
        chunked_indices = _chunk_items(review_indices, chunk_size)
        total_batches = len(chunked_indices)
        _safe_print(
            f"Per-item mode enabled: concurrency={args.concurrency} "
            f"items_per_request={chunk_size}"
        )
        semaphore = asyncio.Semaphore(args.concurrency)

        async def _bounded_review(
            payloads: list[dict[str, Any]],
        ) -> tuple[dict[str, Any], str | None]:
            async with semaphore:
                return await _review_chunk(
                    payloads,
                    model=model,
                    api_key=api_key,
                    base_url=base_url,
                    request_timeout=args.request_timeout,
                )

        tasks = []
        for batch_no, batch_indices in enumerate(chunked_indices, start=1):
            payloads = [_candidate_payload(rows[idx]) for idx in batch_indices]
            _safe_print(
                f"Reviewing batch {batch_no}/{total_batches}: "
                f"{len(batch_indices)} items in one request"
            )
            tasks.append(asyncio.create_task(_bounded_review(payloads)))

        for batch_no, batch_indices, future in zip(
            range(1, total_batches + 1), chunked_indices, tasks
        ):
            reviewed, batch_error = await future
            errors: dict[str, str] = {}
            if batch_error:
                errors = {
                    str(rows[idx].get("major_name")): batch_error
                    for idx in batch_indices
                }
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
            _safe_print(
                f"Finished batch {batch_no}/{total_batches}: reviewed={stats['reviewed']} "
                f"changed={stats['changed']} errors={stats['errors']}"
            )
            if errors:
                first_major, first_error = next(iter(errors.items()))
                _safe_print(f"First error: {first_major}: {first_error}")
            if args.checkpoint_every_batch and not args.dry_run:
                _write_rows(_output_path(args), rows)
        return rows, stats

    for batch_no, start in enumerate(
        range(0, len(review_indices), args.batch_size), start=1
    ):
        batch_indices = review_indices[start : start + args.batch_size]
        _safe_print(
            f"Reviewing batch {batch_no}/{total_batches}: {len(batch_indices)} items"
        )
        payloads = [_candidate_payload(rows[idx]) for idx in batch_indices]
        reviewed = await _review_batch(
            payloads,
            model=model,
            api_key=api_key,
            base_url=base_url,
            request_timeout=args.request_timeout,
        )
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
        _safe_print(
            f"Finished batch {batch_no}/{total_batches}: reviewed={stats['reviewed']} "
            f"changed={stats['changed']}"
        )
        if args.checkpoint_every_batch and not args.dry_run:
            _write_rows(_output_path(args), rows)

    return rows, stats


def main() -> None:
    args = _parse_args()
    rows, stats = asyncio.run(_main_async(args))
    _safe_print(json.dumps(stats, ensure_ascii=False, indent=2))
    if args.dry_run:
        _safe_print("Dry run: output not written.")
        return

    output_path = _output_path(args)
    _write_rows(output_path, rows)
    _safe_print(f"Wrote reviewed candidates to {output_path}")


if __name__ == "__main__":
    main()
