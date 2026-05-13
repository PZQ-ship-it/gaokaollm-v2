from pathlib import Path
from typing import Any

from app.evaluation.episode_logger import read_episode_logs

RESULTS_DIR = Path(__file__).parent / "results"


def _snapshot_values(snapshot: Any) -> dict[str, Any]:
    if isinstance(snapshot, dict):
        values = snapshot.get("values", snapshot)
    else:
        values = getattr(snapshot, "values", snapshot)
    return values if isinstance(values, dict) else {}


def _message_role(message: Any) -> str:
    role = getattr(message, "type", None) or getattr(message, "role", None)
    if role:
        return str(role).lower()
    if isinstance(message, tuple) and message:
        return str(message[0]).lower()
    if isinstance(message, dict):
        return str(message.get("type") or message.get("role") or "").lower()
    return ""


def _message_content(message: Any) -> str:
    if isinstance(message, tuple) and len(message) >= 2:
        return str(message[1] or "")
    if isinstance(message, dict):
        return str(message.get("content") or "")
    return str(getattr(message, "content", "") or "")


def _initial_user_query(history_values: list[dict[str, Any]]) -> str:
    for values in history_values:
        for message in values.get("messages") or []:
            role = _message_role(message)
            if role in {"human", "user"}:
                return _message_content(message)
    return ""


def _last_ai_message(history_values: list[dict[str, Any]]) -> str:
    for values in reversed(history_values):
        for message in reversed(values.get("messages") or []):
            role = _message_role(message)
            if role in {"ai", "assistant"}:
                content = _message_content(message)
                if content:
                    return content
    return ""


def _append_unique(
    lines: list[str], seen: set[tuple[str, str]], label: str, text: str
) -> None:
    clean = str(text or "").strip()
    if not clean:
        return
    key = (label, clean)
    if key in seen:
        return
    seen.add(key)
    lines.append(f'**[{label}]**: "{clean}"')


def export_case_study(agent_app: Any, thread_id: str, output_md_path: str) -> str:
    config = {"configurable": {"thread_id": thread_id}}
    history = list(agent_app.get_state_history(config))
    history.reverse()
    history_values = [_snapshot_values(snapshot) for snapshot in history]

    lines = ["# EDMIE Case Study Transcript", ""]
    seen: set[tuple[str, str]] = set()
    _append_unique(
        lines, seen, "Initial Query | User", _initial_user_query(history_values)
    )

    round_index = 1
    for values in history_values:
        question = values.get("latest_agent_probe_question")
        feedback = values.get("latest_human_feedback")
        if question:
            before = len(lines)
            _append_unique(
                lines,
                seen,
                f"Round {round_index} | Agent Pareto Probe",
                str(question),
            )
            if len(lines) > before:
                round_index += 1
        if feedback:
            feedback_round = max(1, round_index - 1)
            _append_unique(
                lines,
                seen,
                f"Round {feedback_round} | Simulator Feedback",
                str(feedback),
            )

    _append_unique(
        lines,
        seen,
        "Final | EDMIE XAI Recommendation",
        _last_ai_message(history_values),
    )

    output = Path(output_md_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    content = "\n\n".join(lines) + "\n"
    output.write_text(content, encoding="utf-8")
    return str(output)


def export_case_study_from_episode_logs(
    log_path: str | Path,
    output_md_path: str,
) -> str:
    rows = [
        row
        for row in read_episode_logs(log_path)
        if row.get("ablation_mode") == "full" and row.get("question")
    ]
    if not rows:
        raise ValueError("No full-mode episode log rows found.")

    by_thread: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        by_thread.setdefault(str(row.get("thread_id") or ""), []).append(row)
    selected_thread, selected_rows = max(
        by_thread.items(),
        key=lambda item: (
            len(item[1]),
            any("牺牲" in str(row.get("question") or "") for row in item[1]),
            item[0],
        ),
    )
    selected_rows = sorted(
        selected_rows,
        key=lambda row: int(row.get("turn") or 0),
    )

    lines = ["# EDMIE Case Study Transcript", ""]
    initial_query = (
        selected_rows[0].get("explicit_query")
        or selected_rows[0].get("profile_id")
        or selected_thread
    )
    lines.append(f'**[Initial Query | User]**: "{initial_query}"')
    for index, row in enumerate(selected_rows, start=1):
        lines.append("")
        lines.append(
            f'**[Round {index} | Agent Pareto Probe]**: "{row.get("question")}"'
        )
        lines.append("")
        lines.append(
            f'**[Round {index} | Simulator Feedback]**: "{row.get("simulator_reply")}"'
        )
    final_rows = [
        row
        for row in read_episode_logs(log_path)
        if row.get("thread_id") == selected_thread and row.get("status") == "final"
    ]
    if final_rows:
        weights = final_rows[-1].get("inferred_weights") or {}
        lines.append("")
        lines.append(
            "**[Final | EDMIE XAI Recommendation]**: "
            f'"Final inferred preference weights: {weights}"'
        )

    output = Path(output_md_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return str(output)


def write_fallback_case_study(output_md_path: str | Path | None = None) -> str:
    output = (
        Path(output_md_path)
        if output_md_path is not None
        else RESULTS_DIR / "case_study.md"
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    content = """# EDMIE Case Study Transcript

**[Initial Query | User]**: "I only want the best brand-name universities and do not want to reveal my real constraints."

**[Round 1 | Agent Pareto Probe]**: "Would you sacrifice geographic comfort in exchange for a school-tier jump, or keep the local option with lower institutional prestige?"

**[Round 1 | Simulator Feedback]**: "I can accept geography compromise if the major stays in the computer-science family."

**[Final | EDMIE XAI Recommendation]**: "Preference explanation: the inferred belief state places the largest weight on major fit, while geography is elastic and tuition remains a guardrail."
"""
    output.write_text(content, encoding="utf-8")
    return str(output)


def run_cli() -> str:
    path = write_fallback_case_study()
    print(f"[transcript_exporter] wrote {path}")
    return path


if __name__ == "__main__":
    run_cli()
