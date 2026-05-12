from pathlib import Path
from typing import Any


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
