"""Multi-turn sandbox arena for target-agent benchmark episodes."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from gaokaollm_bench.constrains.enums import ConversationRole
from gaokaollm_bench.sandbox.base_target import BaseTargetAgent
from gaokaollm_bench.schemas import ConversationTurn, IcebergPersona, Transcript
from gaokaollm_bench.simulator.user_agent import UserSimulator


async def run_episode(
    persona: IcebergPersona,
    target: BaseTargetAgent,
    max_turns: int = 6,
    *,
    simulator_llm_client: Any = None,
    output_dir: str | Path = ".",
) -> Transcript:
    """Run a controlled multi-turn episode and persist its transcript."""

    if simulator_llm_client is None:
        raise ValueError("simulator_llm_client is required to run the user simulator")
    if max_turns < 1:
        raise ValueError("max_turns must be at least 1")

    simulator = UserSimulator(persona, simulator_llm_client)
    turns: list[ConversationTurn] = [
        ConversationTurn(
            turn_id=1,
            role=ConversationRole.USER,
            content=persona.initial_utterance,
            internal_state={"is_persuaded": False, "source": "initial_utterance"},
        )
    ]

    current_user_input = persona.initial_utterance
    next_turn_id = 2

    for _ in range(max_turns):
        agent_reply, target_state = await target.chat(current_user_input)
        turns.append(
            ConversationTurn(
                turn_id=next_turn_id,
                role=ConversationRole.TARGET_AGENT,
                content=agent_reply,
                internal_state=target_state,
            )
        )
        next_turn_id += 1

        user_reply = await simulator.chat(agent_reply)
        turns.append(
            ConversationTurn(
                turn_id=next_turn_id,
                role=ConversationRole.USER,
                content=user_reply,
                internal_state=dict(simulator.internal_state),
            )
        )
        next_turn_id += 1

        if simulator.internal_state.get("is_persuaded") is True:
            break
        if (
            target_state.get("graph_status") == "finished"
            and target_state.get("reply_source") == "final_message"
        ):
            break

        current_user_input = user_reply

    transcript = Transcript(persona=persona, turns=turns)
    output_path = Path(output_dir) / f"transcript_{persona.case_id}.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(transcript.model_dump_json(indent=2), encoding="utf-8")

    return transcript
