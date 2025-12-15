from pathlib import Path
from typing import Any, Dict, Literal, Optional

from pydantic import BaseModel


class Constraint(BaseModel):
    name: str
    description: str
    type: Literal["hard", "soft"]
    rank: Optional[int] = None
    formula: str = ""
    where: str = ""

    def __eq__(self, other):
        if not isinstance(other, Constraint):
            return False
        return self.name == other.name


class UserAPISchemaDefinition(BaseModel):
    request_schema: Dict[str, Any]
    response_schema: Dict[str, Any]


class ProjectSnapshot(BaseModel):
    optigen_snapshot_version: str = "0.0.1"
    snapshot_version: int = 1
    title: str | None = None
    description: str | None = None
    constraints: list[Constraint] = []
    schema_definition: UserAPISchemaDefinition | None = None


class ProjectSettings:
    def __init__(
        self, directory: Path, project_snapshot: ProjectSnapshot | None = None
    ):
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
        self.settings_file.write_text(self.project_snapshot.model_dump_json(indent=4))

    @property
    def title(self) -> str | None:
        return self.project_snapshot.title

    @property
    def description(self) -> str | None:
        return self.project_snapshot.description

    def update(self, **kwargs) -> None:
        """Generic update method for project settings."""
        self.project_snapshot = self.project_snapshot.model_copy(update=kwargs)
        self.persist_settings()

    @property
    def constraints(self) -> list[Constraint]:
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
        return self.project_snapshot.schema_definition

    def get_request_schema(self) -> dict | None:
        if self.project_snapshot.schema_definition:
            return self.project_snapshot.schema_definition.request_schema
        return None

    def get_response_schema(self) -> dict | None:
        if self.project_snapshot.schema_definition:
            return self.project_snapshot.schema_definition.response_schema
        return None
