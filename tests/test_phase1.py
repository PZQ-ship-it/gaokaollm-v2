import pytest
from langchain_core.messages import HumanMessage

from app.core.db_pg import close_pool, fetch_query
from app.core.llm_client import get_chat_model
from app.schemas.models import UserConstraints
from app.schemas.state import (
    DEFAULT_IMPLICIT_WEIGHTS,
    DEFAULT_WEIGHT_VARIANCE,
    AgentState,
)
from tests._env_checks import require_database


def test_agent_state_and_user_constraints_contract():
    constraints = UserConstraints(
        score=600,
        province="北京",
        major="临床医学",
        budget=30000,
    )
    state: AgentState = {
        "messages": [HumanMessage(content="600分必须在北京读临床")],
        "constraints": constraints.model_dump(),
        "baseline_results": [],
        "score_waste": 0,
        "pareto_opportunities": {},
        "implicit_weights": dict(DEFAULT_IMPLICIT_WEIGHTS),
        "weight_variance": dict(DEFAULT_WEIGHT_VARIANCE),
    }

    assert state["constraints"]["score"] == 600
    assert state["messages"][0].content == "600分必须在北京读临床"
    assert state["implicit_weights"]["school"] == 0.25
    assert state["weight_variance"]["tuition"] == 1.0


@pytest.mark.asyncio
async def test_fetch_query_select_one():
    require_database()
    rows = await fetch_query("SELECT 1 AS value")
    await close_pool()

    assert rows == [{"value": 1}]


@pytest.mark.asyncio
async def test_llm_ping():
    llm = get_chat_model()
    try:
        response = await llm.ainvoke([HumanMessage(content="ping")])
    except Exception as exc:
        pytest.skip(f"LLM endpoint is not reachable: {type(exc).__name__}: {exc}")

    assert response.content
