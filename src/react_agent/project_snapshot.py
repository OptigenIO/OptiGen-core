"""Define project snapshot models for optimization problem specifications."""

from pathlib import Path
from typing import Any, Dict, Literal, Optional

from pydantic import BaseModel


class Constraint(BaseModel):
    """Represents a constraint or objective in an optimization problem."""

    name: str
    description: str
    type: Literal["hard", "soft"]
    rank: Optional[int] = None
    formula: str = ""
    where: str = ""

    def __eq__(self, other):
        """Check equality based on constraint name."""
        if not isinstance(other, Constraint):
            return False
        return self.name == other.name


class UserAPISchemaDefinition(BaseModel):
    """Defines the request and response schemas for the user API."""

    request_schema: Dict[str, Any]
    response_schema: Dict[str, Any]


class ProjectSnapshot(BaseModel):
    """Represents a complete snapshot of the optimization problem configuration."""

    optigen_snapshot_version: str = "0.0.1"
    snapshot_version: int = 1
    title: str | None = None
    description: str | None = None
    constraints: list[Constraint] = []
    schema_definition: UserAPISchemaDefinition | None = None


class ProjectSettings:
    """Manages project settings and persistence for optimization problems."""

    def __init__(
        self, directory: Path, project_snapshot: ProjectSnapshot | None = None
    ):
        """Initialize project settings from directory or provided snapshot."""
        self.directory = directory
        self.settings_file = directory / "optigen.json"

        if self.settings_file.exists():
            self.project_snapshot = ProjectSnapshot.model_validate_json(
                self.settings_file.read_text()
            )
        else:
            self.project_snapshot = project_snapshot or ProjectSnapshot()
            self.persist_settings()

    def persist_settings(self):
        """Persist the current project snapshot to disk."""
        self.settings_file.write_text(self.project_snapshot.model_dump_json(indent=4))

    @property
    def title(self) -> str | None:
        """Get the project title."""
        return self.project_snapshot.title

    @property
    def description(self) -> str | None:
        """Get the project description."""
        return self.project_snapshot.description

    def update(self, **kwargs) -> None:
        """Update project settings with provided keyword arguments."""
        self.project_snapshot = self.project_snapshot.model_copy(update=kwargs)
        self.persist_settings()

    @property
    def constraints(self) -> list[Constraint]:
        """Get the list of constraints."""
        return self.project_snapshot.constraints

    def add_constraint(self, constraint: Constraint) -> None:
        """Add a constraint and persist changes.

        Raises:
            ValueError: If a constraint with the same name already exists.
        """
        if any(c.name == constraint.name for c in self.constraints):
            raise ValueError(
                f"Constraint with name '{constraint.name}' already exists."
            )

        self.project_snapshot.constraints.append(constraint)
        self.persist_settings()

    def remove_constraint(self, constraint_name: str) -> bool:
        """Remove a constraint by name. Returns True if found and removed."""
        original_length = len(self.project_snapshot.constraints)
        self.project_snapshot.constraints = [
            c for c in self.project_snapshot.constraints if c.name != constraint_name
        ]
        removed = len(self.project_snapshot.constraints) < original_length
        if removed:
            self.persist_settings()
        return removed

    def get_constraint_by_name(self, name: str) -> Constraint | None:
        """Get a constraint by its name, or None if not found."""
        for constraint in self.project_snapshot.constraints:
            if constraint.name == name:
                return constraint
        return None

    def update_constraint(self, name: str, **kwargs) -> bool:
        """Update a constraint by name. Returns True if found and updated."""
        constraint = self.get_constraint_by_name(name)
        if constraint is None:
            return False

        updated = constraint.model_copy(update=kwargs)

        for i, c in enumerate(self.project_snapshot.constraints):
            if c.name == name:
                self.project_snapshot.constraints[i] = updated
                break

        self.persist_settings()
        return True

    @property
    def schema_definition(self) -> UserAPISchemaDefinition | None:
        """Get the API schema definition."""
        return self.project_snapshot.schema_definition

    def get_request_schema(self) -> dict | None:
        """Get the request schema, or None if not defined."""
        if self.project_snapshot.schema_definition:
            return self.project_snapshot.schema_definition.request_schema
        return None

    def get_response_schema(self) -> dict | None:
        """Get the response schema, or None if not defined."""
        if self.project_snapshot.schema_definition:
            return self.project_snapshot.schema_definition.response_schema
        return None
