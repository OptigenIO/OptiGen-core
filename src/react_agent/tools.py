"""Define tools available to the agent for problem specification and search."""

import json
from pathlib import Path
from typing import Any, Literal, Optional, cast

from langchain_tavily import TavilySearch
from langgraph.runtime import get_runtime

from react_agent.context import Context
from react_agent.project_snapshot import Constraint, Scenario, UserAPISchemaDefinition


async def search(query: str) -> Optional[dict[str, Any]]:
    """Search for general web results.

    This function performs a search using the Tavily search engine, which is designed
    to provide comprehensive, accurate, and trusted results. It's particularly useful
    for answering questions about current events.
    """
    runtime = get_runtime(Context)
    wrapped = TavilySearch(max_results=runtime.context.max_search_results)
    return cast(dict[str, Any], await wrapped.ainvoke({"query": query}))


def read_problem_specification() -> str:
    """Read the complete problem specification from the project settings.

    Returns the project snapshot JSON containing title, description,
    constraints, and schema definitions for the optimization problem.
    """
    runtime = get_runtime(Context)
    if (
        runtime.context.project_settings
        and runtime.context.project_settings.project_snapshot
    ):
        return runtime.context.project_settings.project_snapshot.model_dump_json(
            indent=2
        )
    return "{}"


def available_python_dependencies() -> str:
    """Return a list of available Python dependencies to use in solver scripts."""
    return "pyomo"


def add_constraint(
    name: str,
    description: str,
    constraint_type: Literal["hard", "soft"],
    formula: str = "",
    where: str = "",
    rank: Optional[int] = None,
) -> str:
    r"""Add a new constraint or objective to the optimization problem.

    Use this tool to add both constraints and objectives:
    - **Objectives** = what to maximize/minimize. Add as "soft" constraints with a **rank** (1 = highest priority).
    - **Constraints** = strict rules that *must* be met. Use type="hard" for these.

    Hard constraints are mandatory and must be satisfied. Soft constraints (objectives) can be violated but incur a penalty.
    If objectives conflict, ask the user to clarify priorities.

    **LaTeX Formatting for formulas:**
    - Use `\\mathrm{}` for variable names
    - For subscripts with multiple characters, always use braces: `x_{ij}` not `x_ij`, `\\mathrm{required}_{\\mathrm{staff}}` not `\\mathrm{required_staff}`
    - Without braces, only the first character is subscripted
    - Use `\\text{}` only for plain English
    - All formulas must be KaTeX-compatible

    Args:
        name: Unique identifier for the constraint (e.g., "no_overlapping_shifts")
        description: Human-readable explanation of what the constraint enforces
        constraint_type: Either "hard" (must be satisfied) or "soft" (objective)
        formula: Mathematical formula or expression for the constraint (optional). Must use KaTeX-compatible LaTeX.
        where: Condition specifying when/where the constraint applies (optional)
        rank: Priority rank for soft constraints - lower values = higher priority (optional, required for objectives)

    Returns:
        Confirmation message with the added constraint details.
    """
    runtime = get_runtime(Context)
    if not runtime.context.project_settings:
        return "Error: Project settings not initialized."

    constraint = Constraint(
        name=name,
        description=description,
        type=constraint_type,
        formula=formula,
        where=where,
        rank=rank,
    )

    try:
        runtime.context.project_settings.add_constraint(constraint)
    except ValueError as e:
        return f"Error adding constraint: {e}"
    return f"Successfully added constraint '{name}' ({constraint_type})."


def remove_constraint(name: str) -> str:
    """Remove an existing constraint from the optimization problem by its name.

    Args:
        name: The unique identifier of the constraint to remove

    Returns:
        Confirmation message indicating whether the constraint was removed.
    """
    runtime = get_runtime(Context)
    if not runtime.context.project_settings:
        return "Error: Project settings not initialized."

    removed = runtime.context.project_settings.remove_constraint(name)
    if removed:
        return f"Successfully removed constraint '{name}'."
    return f"Constraint '{name}' not found."


def update_project_metadata(
    title: Optional[str] = None, description: Optional[str] = None
) -> str:
    """Update the project title and/or description.

    Use this to set or modify the high-level metadata about the optimization
    problem being solved.

    Args:
        title: New title for the project (optional)
        description: New description for the project (optional)

    Returns:
        Confirmation message with the updated metadata.
    """
    runtime = get_runtime(Context)
    if not runtime.context.project_settings:
        return "Error: Project settings not initialized."

    updates = []
    if title and description:
        runtime.context.project_settings.update(title=title, description=description)
        updates.append(f"title='{title}'")
        updates.append(f"description='{description}'")
    elif title:
        runtime.context.project_settings.update(title=title)
        updates.append(f"title='{title}'")
    elif description:
        runtime.context.project_settings.update(description=description)
        updates.append(f"description='{description}'")

    if updates:
        return f"Successfully updated project metadata: {', '.join(updates)}."
    return "No updates provided."


def update_request_schema(schema: dict[str, Any]) -> str:
    """Update the problem request schema (input format).

    Use this to set the request/response schemas once the model is clearer.
    The request schema defines the structure of input data that users will
    provide when submitting optimization problems. This should be done after
    objectives and constraints are confirmed.

    Args:
        schema: JSON schema dictionary defining the expected input format (OpenAPI format)

    Returns:
        Confirmation message with the updated schema.
    """
    runtime = get_runtime(Context)
    if not runtime.context.project_settings:
        return "Error: Project settings not initialized."

    current_schema_def = runtime.context.project_settings.schema_definition
    response_schema = current_schema_def.response_schema if current_schema_def else {}

    new_schema_def = UserAPISchemaDefinition(
        request_schema=schema, response_schema=response_schema
    )
    runtime.context.project_settings.update(schema_definition=new_schema_def)
    return f"Successfully updated request schema: {json.dumps(schema, indent=2)}"


def update_response_schema(schema: dict[str, Any]) -> str:
    """Update the problem response schema (output format).

    Use this to set the request/response schemas once the model is clearer.
    The response schema defines the structure of optimization results that
    will be returned to users after solving their problem. This should be done after
    objectives and constraints are confirmed.

    Args:
        schema: JSON schema dictionary defining the expected output format (OpenAPI format)

    Returns:
        Confirmation message with the updated schema.
    """
    runtime = get_runtime(Context)
    if not runtime.context.project_settings:
        return "Error: Project settings not initialized."

    current_schema_def = runtime.context.project_settings.schema_definition
    request_schema = current_schema_def.request_schema if current_schema_def else {}

    new_schema_def = UserAPISchemaDefinition(
        request_schema=request_schema, response_schema=schema
    )
    runtime.context.project_settings.update(schema_definition=new_schema_def)
    return f"Successfully updated response schema: {json.dumps(schema, indent=2)}"


def add_scenario(
    request_path: str,
    name: Optional[str] = None,
    description: Optional[str] = None,
) -> str:
    """Add a new scenario to the optimization problem dataset.

    This tool adds scenario metadata (path, name, description) to the project settings.
    The scenario JSON file should already have been created using the write_file tool
    before calling this function.

    Args:
        request_path: Path to the JSON file containing the scenario data (relative to project directory)
        name: Optional name/identifier for the scenario
        description: Optional human-readable description of the scenario

    Returns:
        Confirmation message with the added scenario details.
    """
    runtime = get_runtime(Context)
    if not runtime.context.project_settings:
        return "Error: Project settings not initialized."

    scenario = Scenario(
        name=name,
        description=description,
        request=Path(request_path),
    )
    runtime.context.project_settings.add_scenario(scenario)

    scenario_id = f"'{name}'" if name else "unnamed scenario"
    return (
        f"Successfully added scenario {scenario_id} with request path '{request_path}'."
    )


def remove_scenario(scenario_name: str) -> str:
    """Remove an existing scenario from the optimization problem dataset by its name.

    This removes the scenario metadata from project settings. It does not delete
    the actual JSON file containing the scenario data.

    Args:
        scenario_name: The name identifier of the scenario to remove

    Returns:
        Confirmation message indicating whether the scenario was removed.
    """
    runtime = get_runtime(Context)
    if not runtime.context.project_settings:
        return "Error: Project settings not initialized."

    removed = runtime.context.project_settings.remove_scenario(scenario_name)
    if removed:
        return f"Successfully removed scenario '{scenario_name}'."
    return f"Scenario '{scenario_name}' not found."
