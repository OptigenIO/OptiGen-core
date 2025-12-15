"""Define the agent graph configuration."""

from deepagents import create_deep_agent
from deepagents.backends import FilesystemBackend
from langchain.chat_models import init_chat_model

from react_agent.context import Context
from react_agent.prompts import BASE_SYSTEM_PROMPT
from react_agent.tools import ALL_TOOLS

WORKING_DIR = "./working_dir"

graph = create_deep_agent(
    tools=ALL_TOOLS,
    backend=FilesystemBackend(root_dir=WORKING_DIR, virtual_mode=True),
    system_prompt=BASE_SYSTEM_PROMPT,
    model=init_chat_model("anthropic:claude-haiku-4-5"),
    context_schema=Context,
)
