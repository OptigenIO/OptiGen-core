"""Define project snapshot models for optimization problem specifications."""

import os
import pathlib
import tempfile
import threading
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

    def __eq__(self, other: object) -> bool:
        """Check equality based on constraint name."""
        if not isinstance(other, Constraint):
            return False
        return self.name == other.name


class UserAPISchemaDefinition(BaseModel):
    """Defines the request and response schemas for the user API."""

    request_schema: Dict[str, Any]
    response_schema: Dict[str, Any]


class Scenario(BaseModel):
    """Represents a scenario in the optimization problem."""

    name: str | None = None
    description: str | None = None
    request: pathlib.Path | None = None


class ProjectSnapshot(BaseModel):
    """Represents a complete snapshot of the optimization problem configuration."""

    optigen_snapshot_version: str = "0.0.3"
    snapshot_version: int = 1
    title: str | None = None
    description: str | None = None
    constraints: list[Constraint] = []
    schema_definition: UserAPISchemaDefinition | None = None
    dataset: list[Scenario] | None = None


class ProjectSettings:
    """Manages project settings and persistence for optimization problems."""

    # Class-level lock for thread-safe file access across all instances
    _lock = threading.Lock()

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

    def _reload_from_disk(self) -> None:
        """Reload snapshot from disk if file exists.

        This should only be called when holding the lock.
        Used to capture the latest state before modifications.
        """
        if self.settings_file.exists():
            self.project_snapshot = ProjectSnapshot.model_validate_json(
                self.settings_file.read_text()
            )

    def _persist_unlocked(self) -> None:
        """Persist settings without acquiring lock.

        This should only be called when already holding the lock.
        Performs atomic write by writing to temp file then renaming.
        """
        self.directory.mkdir(parents=True, exist_ok=True)

        # Atomic write: write to temp file, then rename
        fd, tmp_path = tempfile.mkstemp(
            dir=self.directory, prefix=".optigen_", suffix=".tmp"
        )
        try:
            with os.fdopen(fd, "w") as f:
                f.write(self.project_snapshot.model_dump_json(indent=2))
            # os.replace is atomic on POSIX systems
            os.replace(tmp_path, self.settings_file)
        except Exception:
            # Clean up temp file on failure
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise

    def persist_settings(self) -> None:
        """Persist the current project snapshot to disk with thread safety.

        Acquires a lock to ensure atomic read-modify-write pattern
        when multiple threads access the same file.
        """
        with self._lock:
            self._persist_unlocked()

    @property
    def title(self) -> str | None:
        """Get the project title."""
        return self.project_snapshot.title

    @property
    def description(self) -> str | None:
        """Get the project description."""
        return self.project_snapshot.description

    def update(self, **kwargs: Any) -> None:
        """Update project settings with provided keyword arguments.

        Thread-safe: reloads latest state from disk, applies changes, then persists.
        """
        with self._lock:
            self._reload_from_disk()
            self.project_snapshot = self.project_snapshot.model_copy(update=kwargs)
            self._persist_unlocked()

    @property
    def constraints(self) -> list[Constraint]:
        """Get the list of constraints."""
        return self.project_snapshot.constraints

    def add_constraint(self, constraint: Constraint) -> None:
        """Add a constraint and persist changes.

        Thread-safe: reloads latest state, checks for duplicates, adds, then persists.

        Raises:
            ValueError: If a constraint with the same name already exists.
        """
        with self._lock:
            self._reload_from_disk()
            if any(
                c.name == constraint.name for c in self.project_snapshot.constraints
            ):
                raise ValueError(
                    f"Constraint with name '{constraint.name}' already exists."
                )
            self.project_snapshot.constraints.append(constraint)
            self._persist_unlocked()

    def remove_constraint(self, constraint_name: str) -> bool:
        """Remove a constraint by name. Returns True if found and removed.

        Thread-safe: reloads latest state, removes constraint, then persists.
        """
        with self._lock:
            self._reload_from_disk()
            original_length = len(self.project_snapshot.constraints)
            self.project_snapshot.constraints = [
                c
                for c in self.project_snapshot.constraints
                if c.name != constraint_name
            ]
            removed = len(self.project_snapshot.constraints) < original_length
            if removed:
                self._persist_unlocked()
            return removed

    def get_constraint_by_name(self, name: str) -> Constraint | None:
        """Get a constraint by its name, or None if not found."""
        for constraint in self.project_snapshot.constraints:
            if constraint.name == name:
                return constraint
        return None

    def update_constraint(self, name: str, **kwargs: Any) -> bool:
        """Update a constraint by name. Returns True if found and updated.

        Thread-safe: reloads latest state, updates constraint, then persists.
        """
        with self._lock:
            self._reload_from_disk()
            constraint = None
            for c in self.project_snapshot.constraints:
                if c.name == name:
                    constraint = c
                    break

            if constraint is None:
                return False

            updated = constraint.model_copy(update=kwargs)

            for i, c in enumerate(self.project_snapshot.constraints):
                if c.name == name:
                    self.project_snapshot.constraints[i] = updated
                    break

            self._persist_unlocked()
            return True

    @property
    def schema_definition(self) -> UserAPISchemaDefinition | None:
        """Get the API schema definition."""
        return self.project_snapshot.schema_definition

    def get_request_schema(self) -> dict[str, Any] | None:
        """Get the request schema, or None if not defined."""
        if self.project_snapshot.schema_definition:
            return self.project_snapshot.schema_definition.request_schema
        return None

    def get_response_schema(self) -> dict[str, Any] | None:
        """Get the response schema, or None if not defined."""
        if self.project_snapshot.schema_definition:
            return self.project_snapshot.schema_definition.response_schema
        return None

    @property
    def dataset(self) -> list[Scenario] | None:
        """Get the list of scenarios."""
        return self.project_snapshot.dataset

    def add_scenario(self, scenario: Scenario) -> None:
        """Add a scenario and persist changes.

        Thread-safe: reloads latest state, checks for duplicates, adds, then persists.

        Raises:
            ValueError: If a scenario with the same name already exists.
        """
        with self._lock:
            self._reload_from_disk()
            if self.project_snapshot.dataset is None:
                self.project_snapshot.dataset = []

            if scenario.name and any(
                s.name == scenario.name for s in self.project_snapshot.dataset
            ):
                raise ValueError(
                    f"Scenario with name '{scenario.name}' already exists."
                )

            self.project_snapshot.dataset.append(scenario)
            self._persist_unlocked()

    def remove_scenario(self, scenario_name: str) -> bool:
        """Remove a scenario by name. Returns True if found and removed.

        Thread-safe: reloads latest state, removes scenario, then persists.
        """
        with self._lock:
            self._reload_from_disk()
            if self.project_snapshot.dataset is None:
                return False

            original_length = len(self.project_snapshot.dataset)
            self.project_snapshot.dataset = [
                s for s in self.project_snapshot.dataset if s.name != scenario_name
            ]
            removed = len(self.project_snapshot.dataset) < original_length
            if removed:
                self._persist_unlocked()
            return removed

    def get_scenario_by_name(self, name: str) -> Scenario | None:
        """Get a scenario by its name, or None if not found."""
        if self.project_snapshot.dataset is not None:
            for scenario in self.project_snapshot.dataset:
                if scenario.name == name:
                    return scenario
        return None
