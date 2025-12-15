"""Tests for ProjectSettings getter and setter methods."""

import tempfile
from collections.abc import Iterator
from pathlib import Path

import pytest

from react_agent.project_snapshot import (
    Constraint,
    ProjectSettings,
    ProjectSnapshot,
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
        assert settings.settings_file.exists()

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
