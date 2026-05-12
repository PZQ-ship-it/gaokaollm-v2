from typing import Any, Literal


AblationMode = Literal["full", "no_ucb", "no_tracker"]
VALID_ABLATION_MODES: set[str] = {"full", "no_ucb", "no_tracker"}


def get_ablation_mode(config: Any = None) -> AblationMode:
    configurable = config.get("configurable", {}) if isinstance(config, dict) else {}
    mode = str(configurable.get("ablation_mode") or "full")
    if mode not in VALID_ABLATION_MODES:
        return "full"
    return mode  # type: ignore[return-value]
