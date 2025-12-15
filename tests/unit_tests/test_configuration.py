from react_agent.context import Context


def test_context_init() -> None:
    context = Context(model="openai/gpt-4o-mini")
    assert context.model == "openai/gpt-4o-mini"
