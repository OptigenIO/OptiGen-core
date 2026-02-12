"""Define the agent graph configuration."""

from typing import Any

from deepagents import create_deep_agent  # type: ignore[import-untyped]
from deepagents.backends import FilesystemBackend  # type: ignore[import-untyped]
from langchain.chat_models import init_chat_model
from langchain_core.language_models import BaseChatModel
from langgraph.checkpoint.memory import InMemorySaver

from react_agent.context import Context
from react_agent.mcp import get_mcp_tools
from react_agent.prompts import (
    BASE_SYSTEM_PROMPT,
    PROBLEM_FORMULATOR_PROMPT,
    SCHEMA_DATASET_DESIGNER_PROMPT,
    SOLVER_CODER_PROMPT,
)
from react_agent.tools import (
    add_constraint,
    add_scenario,
    add_solver_script,
    available_python_dependencies,
    read_problem_specification,
    remove_constraint,
    remove_scenario,
    remove_solver_script,
    run,
    search,
    update_project_metadata,
    update_request_schema,
    update_response_schema,
)

WORKING_DIR = "./working_dir_default"


def get_subagents(extra_tools: list[Any] | None = None) -> list[dict[str, Any]]:
    """Get the list of subagents, optionally injecting extra tools."""
    solver_tools = [
        read_problem_specification,
        available_python_dependencies,
        search,
        add_solver_script,
        remove_solver_script,
        run,
    ]
    
    if extra_tools:
        solver_tools.extend(extra_tools)

    return [
        {
            "name": "problem_formulator",
            "description": "Clarifies and structures the optimization problem specification.",
            "system_prompt": PROBLEM_FORMULATOR_PROMPT,
            "tools": [
                read_problem_specification,
                update_project_metadata,
                add_constraint,
                remove_constraint,
            ],
        },
        {
            "name": "schema_dataset_designer",
            "description": "Designs request/response schemas and manages the scenario dataset.",
            "system_prompt": SCHEMA_DATASET_DESIGNER_PROMPT,
            "tools": [
                read_problem_specification,
                update_request_schema,
                update_response_schema,
                add_scenario,
                remove_scenario,
            ],
        },
        {
            "name": "solver_coder",
            "description": "Proposes and refines solver implementation strategies.",
            "system_prompt": SOLVER_CODER_PROMPT,
            "tools": solver_tools,
        },
    ]


async def create_graph(
    model: BaseChatModel | str | None = None,
    backend: Any = None,
    context: Context | None = None,
    extra_tools: list[Any] | None = None,
) -> Any:
    """Create the agent graph using the provided model and backend.

    Args:
        model: Optional chat model instance or model string. If None, uses model
               from Context (or creates default Context if context is None).
        backend: Optional backend instance. If None, creates a default
                 FilesystemBackend with WORKING_DIR.
        context: Optional Context instance. Only used if model is None to
                 determine the model. If None, creates a default Context
                 which will read from environment variables if available.
        extra_tools: Optional list of additional tools (e.g., from MCP) to add to
                    the solver_coder subagent.

    Returns:
        The configured agent graph.
    """
    # Determine the model to use
    if model is None:
        if context is None:
            context = Context()
        # Convert model string from "provider/model" to "provider:model" format
        # that init_chat_model expects
        model_str = context.model.replace("/", ":", 1)
        chat_model = init_chat_model(model_str)
    elif isinstance(model, str):
        # Convert model string from "provider/model" to "provider:model" format
        model_str = model.replace("/", ":", 1)
        chat_model = init_chat_model(model_str)
    else:
        chat_model = model

    # Determine the backend to use
    if backend is None:
        backend = FilesystemBackend(root_dir=WORKING_DIR, virtual_mode=True)

    # Load MCP tools if no extra tools provided (and not explicitly None)
    # If extra_tools is None, we check environment for MCP tools
    if extra_tools is None:
        extra_tools = await get_mcp_tools()

    return create_deep_agent(
        tools=[read_problem_specification, search, run],
        backend=backend,
        system_prompt=BASE_SYSTEM_PROMPT,
        model=chat_model,
        context_schema=Context,
        subagents=get_subagents(extra_tools),
        checkpointer=InMemorySaver(),
    )
