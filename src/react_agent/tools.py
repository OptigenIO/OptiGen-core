"""Define tools available to the agent for problem specification and search."""

import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Literal, Optional, cast

from langchain_tavily import TavilySearch
from langgraph.runtime import get_runtime

from react_agent.context import Context
from react_agent.types import (
    Constraint,
    RunSolverScript,
    Scenario,
    SolverScript,
    UserAPISchemaDefinition,
)


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
    formula: str,
    where: str,
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


def update_request_schema(json_schema: dict[str, Any]) -> str:
    """Update the problem request schema (input format).

    Use this to set the request/response schemas once the model is clearer.
    The request schema defines the structure of input data that users will
    provide when submitting optimization problems. This should be done after
    objectives and constraints are confirmed.

    Args:
        json_schema: JSON schema dictionary defining the expected input format (OpenAPI format)

    Returns:
        Confirmation message with the updated schema.
    """
    runtime = get_runtime(Context)
    if not runtime.context.project_settings:
        return "Error: Project settings not initialized."

    current_schema_def = (
        runtime.context.project_settings.project_snapshot.schema_definition
    )
    response_schema = current_schema_def.response_schema if current_schema_def else {}

    new_schema_def = UserAPISchemaDefinition(
        request_schema=json_schema, response_schema=response_schema
    )
    runtime.context.project_settings.update(schema_definition=new_schema_def)
    return f"Successfully updated request schema: {json.dumps(json_schema, indent=2)}"


def update_response_schema(json_schema: dict[str, Any]) -> str:
    """Update the problem response schema (output format).

    Use this to set the request/response schemas once the model is clearer.
    The response schema defines the structure of optimization results that
    will be returned to users after solving their problem. This should be done after
    objectives and constraints are confirmed.

    Args:
        json_schema: JSON schema dictionary defining the expected output format (OpenAPI format)

    Returns:
        Confirmation message with the updated schema.
    """
    runtime = get_runtime(Context)
    if not runtime.context.project_settings:
        return "Error: Project settings not initialized."

    current_schema_def = (
        runtime.context.project_settings.project_snapshot.schema_definition
    )
    request_schema = current_schema_def.request_schema if current_schema_def else {}

    new_schema_def = UserAPISchemaDefinition(
        request_schema=request_schema, response_schema=json_schema
    )
    runtime.context.project_settings.update(schema_definition=new_schema_def)
    return f"Successfully updated response schema: {json.dumps(json_schema, indent=2)}"


def add_scenario(
    request_path: str,
    name: str,
    description: str,
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


def add_solver_script(
    name: str,
    script_path: str,
) -> str:
    """Add a new solver script to the optimization problem.

    This tool adds solver script metadata (name, script path) to the project settings.
    The solver script file should already have been created using the write_file tool
    before calling this function.

    Args:
        name: Unique identifier/name for the solver script
        script_path: Optional path to the solver script file (relative to project directory)

    Returns:
        Confirmation message with the added solver script details.
    """
    runtime = get_runtime(Context)
    if not runtime.context.project_settings:
        return "Error: Project settings not initialized."

    solver_script = SolverScript(
        name=name,
        script=Path(script_path),
    )

    try:
        runtime.context.project_settings.add_solver_script(solver_script)
    except ValueError as e:
        return f"Error adding solver script: {e}"

    script_info = f" with script path '{script_path}'"
    return f"Successfully added solver script '{name}'{script_info}."


def remove_solver_script(solver_script_name: str) -> str:
    """Remove an existing solver script from the optimization problem by its name.

    This removes the solver script metadata from project settings. It does not delete
    the actual script file.

    Args:
        solver_script_name: The name identifier of the solver script to remove

    Returns:
        Confirmation message indicating whether the solver script was removed.
    """
    runtime = get_runtime(Context)
    if not runtime.context.project_settings:
        return "Error: Project settings not initialized."

    removed = runtime.context.project_settings.remove_solver_script(solver_script_name)
    if removed:
        return f"Successfully removed solver script '{solver_script_name}'."
    return f"Solver script '{solver_script_name}' not found."


def run(
    solver_script_name: str,
    path_to_input_file: str,
    path_to_output_file: str,
) -> str:
    """Run a solver script registered in optigen.json with an input file and write the result to the output file.
    
        When running a solver script, the input file should be the same as the one used to create the scenario.
        This runs `python path_to_solver_entrypoint.py path_to_input_file.json path_to_output_file.json` and runs the solver on the 
        input file and saves the output to the output file. A log file with the same name as the output file but with .log extension
        is also created in the same directory, containing all stdout and stderr from the script execution.
        
        Place outputs in `outputs/unique_name_of_the_run.log`.


    Args:
        solver_script_name: Name of the solver script to run
        path_to_input_file: Path to the input file (relative to project directory)
        path_to_output_file: Path to the output file (relative to project directory)

    Returns:
        Confirmation message with the run details.
    """
    runtime = get_runtime(Context)
    if not runtime.context.project_settings:
        return "Error: Project settings not initialized."

    # Find the solver script
    solver = runtime.context.project_settings.get_solver_script_by_name(
        solver_script_name
    )
    if not solver:
        return f"Error: Solver script '{solver_script_name}' not found."

    if not solver.script:
        return (
            f"Error: Solver script '{solver_script_name}' has no script path defined."
        )

    # Resolve paths
    project_dir = runtime.context.project_settings.directory
    script_full_path = project_dir / solver.script
    input_full_path = project_dir / path_to_input_file
    output_full_path = project_dir / path_to_output_file

    if not script_full_path.exists():
        return f"Error: Script file '{script_full_path}' does not exist."
    if not input_full_path.exists():
        return f"Error: Input file '{input_full_path}' does not exist."

    # Create output directory
    output_full_path.parent.mkdir(parents=True, exist_ok=True)

    # Create log file path (same directory as output, with .log extension)
    log_full_path = output_full_path.with_suffix(".log")

    try:
        # Run command: python script.py input_file.json output_file.json
        # We run from project_dir so that relative paths in script might work if needed,
        # but we pass absolute paths for script, input, and output to be safe.
        cmd = [
            sys.executable,
            str(script_full_path),
            str(input_full_path),
            str(output_full_path),
        ]
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=str(project_dir),
        )

        # Write stdout and stderr to log file
        log_content = []
        if result.stdout:
            log_content.append("=== STDOUT ===\n")
            log_content.append(result.stdout)
        if result.stderr:
            log_content.append("\n=== STDERR ===\n")
            log_content.append(result.stderr)
        
        if log_content:
            log_full_path.write_text("".join(log_content))

        if result.returncode != 0:
            return f"Error executing solver script: {result.stderr}"

    except Exception as e:
        return f"Error running solver script: {e}"

    run_record = RunSolverScript(
        solver_script_name=solver_script_name,
        input_file=Path(path_to_input_file),
        output_file=Path(path_to_output_file),
    )

    try:
        runtime.context.project_settings.add_run(run_record)
    except ValueError as e:
        return f"Error recording run: {e}"

    log_path = Path(path_to_output_file).with_suffix(".log")
    return f"Successfully ran solver '{solver_script_name}' with input '{path_to_input_file}' and saved output to '{path_to_output_file}'. Log file saved to '{log_path}'."
