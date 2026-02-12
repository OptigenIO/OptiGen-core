import pytest

from react_agent.context import Context
from react_agent.graph import create_graph

pytestmark = pytest.mark.anyio


async def test_react_agent_simple_passthrough() -> None:
    graph = await create_graph()
    res = await graph.ainvoke(
        {"messages": [("user", "What is your name?")]},
        context=Context(),
    )

    assert "optigen" in str(res["messages"][-1].content).lower()
