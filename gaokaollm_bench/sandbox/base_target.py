"""Abstract interface for target agents evaluated by gaokaollm-bench."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class BaseTargetAgent(ABC):
    """Contract every target decision agent must satisfy inside the sandbox."""

    @abstractmethod
    async def chat(self, user_input: str) -> tuple[str, dict[str, Any]]:
        """Return the target agent reply and its inspectable internal state."""

