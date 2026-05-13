import json
from pathlib import Path
from typing import Any


RESULTS_DIR = Path(__file__).parent / "results"
EPISODE_LOG_FILE = "episode_logs.jsonl"


def episode_log_path(output_dir: str | Path | None = None) -> Path:
    directory = Path(output_dir) if output_dir is not None else RESULTS_DIR
    return directory / EPISODE_LOG_FILE


def reset_episode_log(output_dir: str | Path | None = None) -> str:
    path = episode_log_path(output_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("", encoding="utf-8")
    return str(path)


def append_episode_log(
    row: dict[str, Any],
    output_dir: str | Path | None = None,
) -> str:
    path = episode_log_path(output_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as file:
        file.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")
    return str(path)


def read_episode_logs(path: str | Path | None = None) -> list[dict[str, Any]]:
    log_path = Path(path) if path is not None else episode_log_path()
    if not log_path.exists():
        return []
    rows: list[dict[str, Any]] = []
    with log_path.open("r", encoding="utf-8") as file:
        for line in file:
            line = line.strip()
            if not line:
                continue
            try:
                parsed = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(parsed, dict):
                rows.append(parsed)
    return rows
