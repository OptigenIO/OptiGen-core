"""Define project snapshot models for optimization problem specifications."""

from collections.abc import Mapping
from pathlib import Path
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


class Constraint(BaseModel):
    """Represents a constraint or objective in an optimization problem."""

    name: str
    description: str
    type: Literal["hard", "soft"]
    rank: Optional[int] = None
    formula: str = ""
    where: str = ""


class UserAPISchemaDefinition(BaseModel):
    """Defines the request and response schemas for the user API."""

    request_schema: Mapping[str, Any]
    response_schema: Mapping[str, Any]


class Scenario(BaseModel):
    """Represents a scenario in the optimization problem."""

    name: str
    description: str = ""
    request: Path


class SolverScript(BaseModel):
    """Represents a solver script in the optimization problem."""

    name: str
    script: Path


class RunSolverScript(BaseModel):
    """Represents a run of a solver script."""

    solver_script_name: str
    input_file: Path
    output_file: Path


class ProjectSnapshot(BaseModel):
    """Represents a complete snapshot of the optimization problem configuration."""

    optigen_snapshot_version: str = "0.0.4"
    snapshot_version: int = 1
    title: str = ""
    description: str = ""
    constraints: list[Constraint] = Field(default_factory=list)
    schema_definition: UserAPISchemaDefinition | None = None
    dataset: list[Scenario] = Field(default_factory=list)
    solver_scripts: list[SolverScript] = Field(default_factory=list)
    runs: list[RunSolverScript] = Field(default_factory=list)
