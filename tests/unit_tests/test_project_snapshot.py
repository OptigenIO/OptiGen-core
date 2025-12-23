"""Tests for ProjectSettings getter and setter methods."""

import tempfile
import threading
from collections.abc import Iterator
from pathlib import Path

import pytest

from react_agent.project_snapshot import (
    Constraint,
    ProjectSettings,
    ProjectSnapshot,
    Scenario,
    UserAPISchemaDefinition,
)


@pytest.fixture
def temp_directory() -> Iterator[Path]:
    """Create a temporary directory for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_project_snapshot() -> ProjectSnapshot:
    """Create a sample ProjectSnapshot for testing."""
    return ProjectSnapshot(
        title="Test Project",
        description="A test project description",
        constraints=[
            Constraint(
                name="test_constraint",
                description="A test constraint",
                type="hard",
                formula="x > 0",
                where="x is a variable",
            )
        ],
        dataset=[
            Scenario(
                name="scenario_1",
                description="A test scenario",
            )
        ],
        schema_definition=UserAPISchemaDefinition(
            request_schema={
                "type": "object",
                "properties": {"input": {"type": "string"}},
            },
            response_schema={
                "type": "object",
                "properties": {"output": {"type": "string"}},
            },
        ),
    )


@pytest.fixture
def project_settings(
    temp_directory: Path, sample_project_snapshot: ProjectSnapshot
) -> ProjectSettings:
    """Create ProjectSettings instance for testing."""
    return ProjectSettings(temp_directory, sample_project_snapshot)


class TestInitialization:
    """Tests for initialization."""

    def test_init_creates_snapshot_if_none(self, temp_directory: Path) -> None:
        """Test that initialization creates a snapshot if none is provided."""
        settings = ProjectSettings(temp_directory)
        assert settings.project_snapshot is not None
        assert settings.title is None

    def test_init_loads_existing_snapshot(self, temp_directory: Path) -> None:
        """Test that initialization loads an existing snapshot."""
        original = ProjectSettings(temp_directory)
        original.update(title="Loaded Title")

        # Re-initialize
        loaded = ProjectSettings(temp_directory)
        assert loaded.title == "Loaded Title"


class TestProperties:
    """Tests for properties (read-only) and update method."""

    def test_title_property_and_update(self, project_settings: ProjectSettings) -> None:
        """Test title property and update via update()."""
        assert project_settings.title == "Test Project"
        project_settings.update(title="New Title")
        assert project_settings.title == "New Title"

        # Verify persistence
        reloaded = ProjectSettings(project_settings.directory)
        assert reloaded.title == "New Title"

    def test_description_property_and_update(
        self, project_settings: ProjectSettings
    ) -> None:
        """Test description property and update via update()."""
        assert project_settings.description == "A test project description"
        project_settings.update(description="New Description")
        assert project_settings.description == "New Description"

        # Verify persistence
        reloaded = ProjectSettings(project_settings.directory)
        assert reloaded.description == "New Description"

    def test_schema_definition_property_and_update(
        self, project_settings: ProjectSettings
    ) -> None:
        """Test schema_definition property and update via update()."""
        assert project_settings.schema_definition is not None

        new_schema = UserAPISchemaDefinition(
            request_schema={"type": "object", "properties": {"new": {"type": "int"}}},
            response_schema={"type": "object"},
        )
        project_settings.update(schema_definition=new_schema)
        assert project_settings.schema_definition is not None
        assert "new" in project_settings.schema_definition.request_schema["properties"]

        # Verify persistence
        reloaded = ProjectSettings(project_settings.directory)
        assert reloaded.schema_definition is not None
        assert "new" in reloaded.schema_definition.request_schema["properties"]


class TestUpdate:
    """Tests for generic update method."""

    def test_update_method(self, project_settings: ProjectSettings) -> None:
        """Test generic update method."""
        project_settings.update(
            title="Updated Title", description="Updated Description"
        )
        assert project_settings.title == "Updated Title"
        assert project_settings.description == "Updated Description"

        # Verify persistence
        reloaded = ProjectSettings(project_settings.directory)
        assert reloaded.title == "Updated Title"
        assert reloaded.description == "Updated Description"


class TestConstraints:
    """Tests for constraint management."""

    def test_constraints_property(self, project_settings: ProjectSettings) -> None:
        """Test constraints property."""
        constraints = project_settings.constraints
        assert len(constraints) == 1
        assert constraints[0].name == "test_constraint"

    def test_add_constraint(self, project_settings: ProjectSettings) -> None:
        """Test adding a constraint."""
        new_constraint = Constraint(
            name="new", description="new constraint", type="soft"
        )
        project_settings.add_constraint(new_constraint)
        assert len(project_settings.constraints) == 2
        assert project_settings.get_constraint_by_name("new") == new_constraint

        # Verify persistence
        reloaded = ProjectSettings(project_settings.directory)
        assert len(reloaded.constraints) == 2

    def test_remove_constraint(self, project_settings: ProjectSettings) -> None:
        """Test removing a constraint."""
        assert project_settings.remove_constraint("test_constraint")
        assert len(project_settings.constraints) == 0
        assert not project_settings.remove_constraint("nonexistent")

        # Verify persistence
        reloaded = ProjectSettings(project_settings.directory)
        assert len(reloaded.constraints) == 0

    def test_update_constraint(self, project_settings: ProjectSettings) -> None:
        """Test updating a constraint."""
        assert project_settings.update_constraint(
            "test_constraint", description="Updated"
        )
        c = project_settings.get_constraint_by_name("test_constraint")
        assert c is not None
        assert c.description == "Updated"
        assert c.type == "hard"  # Unchanged

        # Verify persistence
        reloaded = ProjectSettings(project_settings.directory)
        c_reloaded = reloaded.get_constraint_by_name("test_constraint")
        assert c_reloaded is not None
        assert c_reloaded.description == "Updated"


class TestSchemaHelpers:
    """Tests for schema helper methods."""

    def test_get_request_schema(self, project_settings: ProjectSettings) -> None:
        """Test get_request_schema helper."""
        schema = project_settings.get_request_schema()
        assert schema is not None
        assert "input" in schema["properties"]

    def test_get_response_schema(self, project_settings: ProjectSettings) -> None:
        """Test get_response_schema helper."""
        schema = project_settings.get_response_schema()
        assert schema is not None
        assert "output" in schema["properties"]


class TestDatasetAndScenarios:
    """Tests for Scenario model and dataset management."""

    def test_dataset_property(self, project_settings: ProjectSettings) -> None:
        """Test dataset property exposes scenarios."""
        dataset = project_settings.dataset
        assert dataset is not None
        assert len(dataset) == 1
        assert dataset[0].name == "scenario_1"

    def test_add_scenario(self, project_settings: ProjectSettings) -> None:
        """Test adding a scenario and persistence."""
        new_scenario = Scenario(
            name="scenario_2",
            description="Second scenario",
        )
        project_settings.add_scenario(new_scenario)

        # In-memory
        added = project_settings.get_scenario_by_name("scenario_2")
        assert added is not None
        assert added.description == "Second scenario"

        # Verify persistence
        reloaded = ProjectSettings(project_settings.directory)
        reloaded_scenario = reloaded.get_scenario_by_name("scenario_2")
        assert reloaded_scenario is not None
        assert reloaded_scenario.description == "Second scenario"

    def test_add_scenario_with_duplicate_name_raises(
        self, project_settings: ProjectSettings
    ) -> None:
        """Test adding a scenario with an existing name raises ValueError."""
        duplicate = Scenario(
            name="scenario_1",
            description="Duplicate scenario",
        )
        with pytest.raises(ValueError):
            project_settings.add_scenario(duplicate)

    def test_remove_scenario(self, project_settings: ProjectSettings) -> None:
        """Test removing a scenario by name."""
        assert project_settings.remove_scenario("scenario_1")
        assert project_settings.get_scenario_by_name("scenario_1") is None

        # Removing non-existent scenario returns False
        assert not project_settings.remove_scenario("nonexistent")

        # Verify persistence
        reloaded = ProjectSettings(project_settings.directory)
        assert reloaded.get_scenario_by_name("scenario_1") is None

    def test_get_scenario_by_name_when_dataset_none(self, temp_directory: Path) -> None:
        """Test get_scenario_by_name returns None when dataset is not initialized."""
        settings = ProjectSettings(temp_directory)
        assert settings.dataset is None
        assert settings.get_scenario_by_name("anything") is None

    def test_remove_scenario_when_dataset_none(self, temp_directory: Path) -> None:
        """Test remove_scenario returns False when dataset is not initialized."""
        settings = ProjectSettings(temp_directory)
        assert settings.dataset is None
        assert settings.remove_scenario("anything") is False


class TestConcurrentAccess:
    """Tests for thread safety of concurrent modifications."""

    def test_concurrent_add_constraints_no_lost_updates(
        self, temp_directory: Path
    ) -> None:
        """Test that concurrent constraint additions do not lose updates.

        This simulates the race condition where multiple agents (threads)
        add constraints simultaneously. Without proper locking, updates would be lost.
        """
        settings = ProjectSettings(temp_directory)
        num_threads = 5
        constraints_per_thread = 4

        def add_constraints(thread_id: int) -> None:
            """Add multiple constraints from a thread."""
            for i in range(constraints_per_thread):
                constraint = Constraint(
                    name=f"thread_{thread_id}_constraint_{i}",
                    description=f"Constraint from thread {thread_id}",
                    type="hard" if i % 2 == 0 else "soft",
                )
                settings.add_constraint(constraint)

        # Launch multiple threads adding constraints concurrently
        threads = []
        for thread_id in range(num_threads):
            thread = threading.Thread(target=add_constraints, args=(thread_id,))
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Verify all constraints were added (no lost updates)
        expected_count = num_threads * constraints_per_thread
        reloaded = ProjectSettings(temp_directory)
        assert len(reloaded.constraints) == expected_count

        # Verify all constraint names are unique and correct
        names = {c.name for c in reloaded.constraints}
        assert len(names) == expected_count

    def test_concurrent_add_scenarios_no_lost_updates(
        self, temp_directory: Path
    ) -> None:
        """Test that concurrent scenario additions do not lose updates."""
        settings = ProjectSettings(temp_directory)
        num_threads = 4
        scenarios_per_thread = 3

        def add_scenarios(thread_id: int) -> None:
            """Add multiple scenarios from a thread."""
            for i in range(scenarios_per_thread):
                scenario = Scenario(
                    name=f"scenario_thread_{thread_id}_{i}",
                    description=f"Scenario from thread {thread_id}",
                )
                settings.add_scenario(scenario)

        # Launch multiple threads adding scenarios concurrently
        threads = []
        for thread_id in range(num_threads):
            thread = threading.Thread(target=add_scenarios, args=(thread_id,))
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Verify all scenarios were added (no lost updates)
        expected_count = num_threads * scenarios_per_thread
        reloaded = ProjectSettings(temp_directory)
        assert reloaded.dataset is not None
        assert len(reloaded.dataset) == expected_count

        # Verify all scenario names are unique and correct
        names = {s.name for s in reloaded.dataset if s.name}
        assert len(names) == expected_count

    def test_concurrent_mixed_operations(self, temp_directory: Path) -> None:
        """Test concurrent mix of add, update, and remove operations.

        This is a stress test simulating realistic parallel agent behavior.
        """
        settings = ProjectSettings(
            temp_directory,
            ProjectSnapshot(
                title="Concurrent Test",
                constraints=[
                    Constraint(
                        name=f"initial_constraint_{i}",
                        description="Initial constraint",
                        type="hard",
                    )
                    for i in range(3)
                ],
            ),
        )
        settings.persist_settings()

        num_threads = 3
        errors = []

        def mixed_operations(thread_id: int) -> None:
            """Perform mixed operations from a thread."""
            try:
                # Add constraint
                constraint = Constraint(
                    name=f"thread_{thread_id}_new",
                    description="New constraint",
                    type="soft",
                )
                settings.add_constraint(constraint)

                # Update existing constraint (safe - won't conflict)
                initial_name = f"initial_constraint_{thread_id % 3}"
                settings.update_constraint(
                    initial_name, description=f"Updated by thread {thread_id}"
                )

                # Remove another initial constraint (may conflict with others)
                # Use thread_id to distribute removal attempts
                target_to_remove = f"initial_constraint_{(thread_id + 1) % 3}"
                settings.remove_constraint(target_to_remove)
            except Exception as e:
                errors.append((thread_id, str(e)))

        # Launch threads
        threads = []
        for thread_id in range(num_threads):
            thread = threading.Thread(target=mixed_operations, args=(thread_id,))
            threads.append(thread)
            thread.start()

        # Wait for completion
        for thread in threads:
            thread.join()

        # No errors should occur
        assert not errors, f"Errors during concurrent operations: {errors}"

        # Verify state consistency
        reloaded = ProjectSettings(temp_directory)
        # Should have 3 initial + 3 newly added = 6
        # But some initial ones were removed (up to 3)
        # So we expect between 3-6 constraints
        assert 3 <= len(reloaded.constraints) <= 6
