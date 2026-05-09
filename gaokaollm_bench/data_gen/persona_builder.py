"""LLM-assisted IcebergPersona synthesis from verified Pareto gaps."""

from __future__ import annotations

from typing import Any

from gaokaollm_bench.chains.persona_synthesis import synthesize_persona_with_chain
from gaokaollm_bench.schemas import IcebergPersona


async def synthesize_persona(
    gap_data: dict[str, Any], llm_client: Any
) -> IcebergPersona:
    """Synthesize and validate a stubborn persona from verified gap data."""

    return await synthesize_persona_with_chain(
        gap_data=gap_data,
        llm_client=llm_client,
    )
