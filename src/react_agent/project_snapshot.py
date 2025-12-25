"""Project settings management for optimization problems."""

import threading
from collections.abc import Callable, Mapping
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Generator, TypeVar

from react_agent.storage import JsonFileStore
from react_agent.types import (
    Constraint,
    ProjectSnapshot,
    RunSolverScript,
    Scenario,
    SolverScript,
)

T = TypeVar("T")


class ProjectSettings:
    """Manages project settings and persistence for optimization problems."""

    # Class-level lock for thread-safe file access across all instances
    _lock = threading.Lock()

    def __init__(
        self, directory: Path, project_snapshot: ProjectSnapshot | None = None
    ):
        """Initialize project settings from directory or provided snapshot."""
        self.directory = directory
        self.store = JsonFileStore(directory / "optigen.json")

        content = self.store.load()
        if content:
            self.project_snapshot = ProjectSnapshot.model_validate_json(content)
        else:
            self.project_snapshot = project_snapshot or ProjectSnapshot()

    def _reload_from_disk(self) -> None:
        """Reload snapshot from disk if file exists.

        This should only be called when holding the lock.
        Used to capture the latest state before modifications.
        """
        content = self.store.load()
        if content:
            self.project_snapshot = ProjectSnapshot.model_validate_json(content)

    def _persist_unlocked(self) -> None:
        """Persist settings without acquiring lock.

        This should only be called when already holding the lock.
        Performs atomic write via JsonFileStore.
        """
        self.store.save_atomic(self.project_snapshot.model_dump_json(indent=2))

    def persist_settings(self) -> None:
        """Persist the current project snapshot to disk with thread safety.

        Acquires a lock to ensure atomic read-modify-write pattern
        when multiple threads access the same file.
        """
        with self._lock:
            self._persist_unlocked()

    @contextmanager
    def _transaction(self) -> Generator[None, None, None]:
        """Context manager for thread-safe read-modify-write transactions.

        Acquires lock, reloads from disk, yields control, then persists.
        Ensures atomic operations and prevents forgetting to persist or reload.
        """
        with self._lock:
            self._reload_from_disk()
            before = self.project_snapshot
            try:
                yield
            except Exception:
                self.project_snapshot = before
                raise
            else:
                self._persist_unlocked()

    def _add_unique(
        self,
        items: list[T],
        item: T,
        key: Callable[[T], Any],
        error_message: str,
    ) -> None:
        """Add an item to a list if it doesn't already exist based on key.

        Args:
            items: The list to add to.
            item: The item to add.
            key: Function to extract the key from an item for duplicate checking.
            error_message: Error message to raise if duplicate found.

        Raises:
            ValueError: If an item with the same key already exists.
        """
        if any(key(existing) == key(item) for existing in items):
            raise ValueError(error_message)
        items.append(item)

    def _remove_by_key(
        self,
        items: list[T],
        key_value: Any,
        key: Callable[[T], Any],
    ) -> bool:
        """Remove items from a list by key value.

        Args:
            items: The list to remove from.
            key_value: The key value to match.
            key: Function to extract the key from an item.

        Returns:
            True if any items were removed, False otherwise.
        """
        original_length = len(items)
        items[:] = [item for item in items if key(item) != key_value]
        return len(items) < original_length

    def _get_by_key(
        self,
        items: list[T],
        key_value: Any,
        key: Callable[[T], Any],
    ) -> T | None:
        """Get an item from a list by key value.

        Args:
            items: The list to search.
            key_value: The key value to match.
            key: Function to extract the key from an item.

        Returns:
            The matching item, or None if not found.
        """
        for item in items:
            if key(item) == key_value:
                return item
        return None

    def _update_by_key(
        self,
        items: list[T],
        key_value: Any,
        key: Callable[[T], Any],
        update_fn: Callable[[T], T],
    ) -> bool:
        """Update an item in a list by key value.

        Args:
            items: The list to update.
            key_value: The key value to match.
            key: Function to extract the key from an item.
            update_fn: Function to create the updated item from the existing one.

        Returns:
            True if the item was found and updated, False otherwise.
        """
        for i, item in enumerate(items):
            if key(item) == key_value:
                items[i] = update_fn(item)
                return True
        return False

    def update(self, **kwargs: Any) -> None:
        """Update project settings with provided keyword arguments.

        Thread-safe: reloads latest state from disk, applies changes, then persists.
        """
        with self._transaction():
            self.project_snapshot = self.project_snapshot.model_copy(update=kwargs)

    def add_constraint(self, constraint: Constraint) -> None:
        """Add a constraint and persist changes.

        Thread-safe: reloads latest state, checks for duplicates, adds, then persists.

        Raises:
            ValueError: If a constraint with the same name already exists.
        """
        with self._transaction():
            self._add_unique(
                self.project_snapshot.constraints,
                constraint,
                key=lambda c: c.name,
                error_message=f"Constraint with name '{constraint.name}' already exists.",
            )

    def remove_constraint(self, constraint_name: str) -> bool:
        """Remove a constraint by name. Returns True if found and removed.

        Thread-safe: reloads latest state, removes constraint, then persists.
        """
        with self._transaction():
            return self._remove_by_key(
                self.project_snapshot.constraints,
                constraint_name,
                key=lambda c: c.name,
            )

    def get_constraint_by_name(self, name: str) -> Constraint | None:
        """Get a constraint by its name, or None if not found."""
        return self._get_by_key(
            self.project_snapshot.constraints,
            name,
            key=lambda c: c.name,
        )

    def update_constraint(self, name: str, **kwargs: Any) -> bool:
        """Update a constraint by name. Returns True if found and updated.

        Thread-safe: reloads latest state, updates constraint, then persists.
        """
        with self._transaction():
            return self._update_by_key(
                self.project_snapshot.constraints,
                name,
                key=lambda c: c.name,
                update_fn=lambda c: c.model_copy(update=kwargs),
            )

    def add_scenario(self, scenario: Scenario) -> None:
        """Add a scenario and persist changes.

        Thread-safe: reloads latest state, checks for duplicates, adds, then persists.

        Raises:
            ValueError: If a scenario with the same name already exists.
        """
        with self._transaction():
            self._add_unique(
                self.project_snapshot.dataset,
                scenario,
                key=lambda s: s.name,
                error_message=f"Scenario with name '{scenario.name}' already exists.",
            )

    def remove_scenario(self, scenario_name: str) -> bool:
        """Remove a scenario by name. Returns True if found and removed.

        Thread-safe: reloads latest state, removes scenario, then persists.
        """
        with self._transaction():
            return self._remove_by_key(
                self.project_snapshot.dataset,
                scenario_name,
                key=lambda s: s.name,
            )

    def get_scenario_by_name(self, name: str) -> Scenario | None:
        """Get a scenario by its name, or None if not found."""
        return self._get_by_key(
            self.project_snapshot.dataset,
            name,
            key=lambda s: s.name,
        )

    def add_solver_script(self, solver_script: SolverScript) -> None:
        """Add a solver script and persist changes.

        Thread-safe: reloads latest state, checks for duplicates, adds, then persists.

        Raises:
            ValueError: If a solver script with the same name already exists.
        """
        with self._transaction():
            self._add_unique(
                self.project_snapshot.solver_scripts,
                solver_script,
                key=lambda s: s.name,
                error_message=f"Solver script with name '{solver_script.name}' already exists.",
            )

    def remove_solver_script(self, solver_script_name: str) -> bool:
        """Remove a solver script by name. Returns True if found and removed.

        Thread-safe: reloads latest state, removes solver script, then persists.
        """
        with self._transaction():
            return self._remove_by_key(
                self.project_snapshot.solver_scripts,
                solver_script_name,
                key=lambda s: s.name,
            )

    def get_solver_script_by_name(self, name: str) -> SolverScript | None:
        """Get a solver script by its name, or None if not found."""
        return self._get_by_key(
            self.project_snapshot.solver_scripts,
            name,
            key=lambda s: s.name,
        )

    def add_run(self, run: RunSolverScript) -> None:
        """Add a solver run and persist changes.

        Thread-safe: reloads latest state, checks for duplicates, adds, then persists.

        Raises:
            ValueError: If a run with the same solver_script_name and input_file already exists.
        """
        with self._transaction():
            # Check for duplicates based on composite key (solver_script_name, input_file)
            self._add_unique(
                self.project_snapshot.runs,
                run,
                key=lambda r: (r.solver_script_name, r.input_file),
                error_message=f"Run for solver '{run.solver_script_name}' with input '{run.input_file}' already exists.",
            )
