import argparse
import json
import re
from pathlib import Path
from typing import Any

from app.evaluation.benchmark import get_dataset
from app.evaluation.classification_metrics import gold_dimensions
from app.evaluation.episode_logger import read_episode_logs


RESULTS_DIR = Path(__file__).parent / "results"

DIMENSION_TOKENS = {
    "school": (
        "school",
        "学校层次",
        "学校",
        "名校",
        "985",
        "211",
    ),
    "major": (
        "major",
        "专业匹配",
        "专业",
        "调剂",
    ),
    "tuition": (
        "tuition",
        "学费预算",
        "学费",
        "预算",
        "费用",
    ),
    "quality": (
        "quality",
        "培养质量",
        "质量",
        "实力",
        "学科",
    ),
    "geo": (
        "geo",
        "地域距离",
        "地域",
        "外省",
        "出省",
        "跨省",
        "城市",
    ),
}

AMBIGUOUS_TOKENS = (
    "犹豫",
    "不确定",
    "保留",
    "再看",
    "没问到",
    "可以考虑",
)


def dimension_from_text(text: str) -> str | None:
    lowered = str(text or "").lower()
    for dimension, tokens in DIMENSION_TOKENS.items():
        if any(token.lower() in lowered for token in tokens):
            return dimension
    return None


def extract_dimension(text: str) -> str | None:
    raw = str(text or "")
    patterns = (
        r"(?:牺牲/放宽|牺牲|放宽)\s*([^\s，,。！？?]{1,24})",
        r"(?:换取|获得)\s*([^\s，,。！？?]{1,24})",
    )
    for pattern in patterns:
        match = re.search(pattern, raw, flags=re.I)
        if not match:
            continue
        dimension = dimension_from_text(match.group(1))
        if dimension:
            return dimension
    return dimension_from_text(raw)


def extract_cost_benefit(question: str) -> tuple[str | None, str | None]:
    raw = str(question or "")
    cost = None
    benefit = None
    cost_match = re.search(
        r"(?:牺牲/放宽|牺牲|放宽)\s*([^\s，,。！？?]{1,24})",
        raw,
        flags=re.I,
    )
    benefit_match = re.search(
        r"(?:换取|获得)\s*([^\s，,。！？?]{1,24})",
        raw,
        flags=re.I,
    )
    if cost_match:
        cost = dimension_from_text(cost_match.group(1))
    if benefit_match:
        benefit = dimension_from_text(benefit_match.group(1))
    return cost, benefit


def _same_candidate_question(question: str) -> bool:
    raw = str(question or "")
    match = re.search(r"在\s*(.*?)\s*和\s*(.*?)\s*之间", raw)
    if match:
        return match.group(1).strip() == match.group(2).strip()
    return False


def _gold_map() -> dict[str, set[str]]:
    profiles = [*get_dataset("robust"), *get_dataset("smoke")]
    return {profile.profile_id: set(gold_dimensions(profile)) for profile in profiles}


def analyze_episode_logs(rows: list[dict[str, Any]]) -> dict[str, Any]:
    interrupt_rows = [row for row in rows if row.get("status") == "interrupt"]
    gold_by_profile = _gold_map()
    by_mode: dict[str, list[dict[str, Any]]] = {}
    for row in interrupt_rows:
        by_mode.setdefault(str(row.get("ablation_mode") or ""), []).append(row)

    summary: dict[str, Any] = {"total_interrupts": len(interrupt_rows), "modes": {}}
    for mode, mode_rows in sorted(by_mode.items()):
        previous_by_thread: dict[str, str] = {}
        repeated = 0
        cost_equals_benefit = 0
        same_candidate = 0
        target_hits = 0
        ambiguous = 0
        for row in mode_rows:
            question = str(row.get("question") or "")
            reply = str(row.get("simulator_reply") or "")
            thread_id = str(row.get("thread_id") or "")
            if previous_by_thread.get(thread_id) == question:
                repeated += 1
            previous_by_thread[thread_id] = question

            cost, benefit = extract_cost_benefit(question)
            if cost and benefit and cost == benefit:
                cost_equals_benefit += 1
            if _same_candidate_question(question):
                same_candidate += 1

            gold = gold_by_profile.get(str(row.get("profile_id") or ""), set())
            asked_dimension = cost or extract_dimension(question)
            if asked_dimension and asked_dimension in gold:
                target_hits += 1
            if any(token in reply for token in AMBIGUOUS_TOKENS):
                ambiguous += 1

        denominator = len(mode_rows) or 1
        summary["modes"][mode] = {
            "n": len(mode_rows),
            "repeated_question_rate": repeated / denominator,
            "cost_equals_benefit_rate": cost_equals_benefit / denominator,
            "same_candidate_pair_rate": same_candidate / denominator,
            "target_dimension_hit_rate": target_hits / denominator,
            "simulator_ambiguous_reply_rate": ambiguous / denominator,
        }
    return summary


def write_analysis(
    summary: dict[str, Any],
    output_dir: str | Path | None = None,
) -> dict[str, str]:
    directory = Path(output_dir) if output_dir is not None else RESULTS_DIR
    directory.mkdir(parents=True, exist_ok=True)
    json_path = directory / "episode_log_analysis.json"
    md_path = directory / "episode_log_analysis.md"
    json_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    lines = [
        "# Episode Log Analysis",
        "",
        f"Total interrupts: {summary.get('total_interrupts', 0)}",
        "",
    ]
    for mode, metrics in (summary.get("modes") or {}).items():
        lines.append(f"## {mode}")
        for key, value in metrics.items():
            lines.append(f"- {key}: {value}")
        lines.append("")
    md_path.write_text("\n".join(lines), encoding="utf-8")
    return {"json_path": str(json_path), "md_path": str(md_path)}


def run_cli(argv: list[str] | None = None) -> dict[str, Any]:
    parser = argparse.ArgumentParser()
    parser.add_argument("--log-path", default=str(RESULTS_DIR / "episode_logs.jsonl"))
    parser.add_argument("--output-dir", default=str(RESULTS_DIR))
    args = parser.parse_args(argv)

    rows = read_episode_logs(args.log_path)
    summary = analyze_episode_logs(rows)
    paths = write_analysis(summary, args.output_dir)
    print(f"[log_analyzer] wrote {paths['md_path']}")
    return {"summary": summary, **paths}


if __name__ == "__main__":
    run_cli()
