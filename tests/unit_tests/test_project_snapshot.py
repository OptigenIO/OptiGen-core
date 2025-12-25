import json
from pathlib import Path

import pytest

from react_agent.project_snapshot import ProjectSettings
from react_agent.types import (
    Constraint,
    ProjectSnapshot,
    RunSolverScript,
    Scenario,
    SolverScript,
)


@pytest.fixture
def project_dir(tmp_path: Path) -> Path:
    p = tmp_path / "project"
    p.mkdir()
    return p


@pytest.fixture
def project_settings(project_dir: Path) -> ProjectSettings:
    return ProjectSettings(project_dir)


def test_initialization_creates_file(project_dir: Path) -> None:
    settings = ProjectSettings(project_dir)
    # Initialization doesn't automatically create file, must persist
    settings.persist_settings()
    assert (project_dir / "optigen.json").exists()


def test_load_existing_file(project_dir: Path) -> None:
    data = ProjectSnapshot(title="Existing Project").model_dump_json()
    (project_dir / "optigen.json").write_text(data)

    settings = ProjectSettings(project_dir)
    assert settings.project_snapshot.title == "Existing Project"


def test_add_constraint_persistence(
    project_settings: ProjectSettings, project_dir: Path
) -> None:
    c = Constraint(name="c1", description="desc", type="hard")
    project_settings.add_constraint(c)

    # Check memory
    assert len(project_settings.project_snapshot.constraints) == 1
    assert project_settings.project_snapshot.constraints[0].name == "c1"

    # Check disk
    content = json.loads((project_dir / "optigen.json").read_text())
    assert content["constraints"][0]["name"] == "c1"


def test_add_constraint_duplicate_error(project_settings: ProjectSettings) -> None:
    c = Constraint(name="c1", description="desc", type="hard")
    project_settings.add_constraint(c)

    with pytest.raises(ValueError, match="Constraint with name 'c1' already exists"):
        project_settings.add_constraint(c)


def test_update_constraint(project_settings: ProjectSettings) -> None:
    c = Constraint(name="c1", description="desc", type="hard")
    project_settings.add_constraint(c)

    updated = project_settings.update_constraint("c1", description="new desc")
    assert updated
    assert project_settings.project_snapshot.constraints[0].description == "new desc"

    # Verify non-existent
    assert not project_settings.update_constraint("nonexistent", description="foo")


def test_remove_constraint(project_settings: ProjectSettings) -> None:
    c = Constraint(name="c1", description="desc", type="hard")
    project_settings.add_constraint(c)

    removed = project_settings.remove_constraint("c1")
    assert removed
    assert len(project_settings.project_snapshot.constraints) == 0

    assert not project_settings.remove_constraint("c1")


def test_transaction_reloads_from_disk(project_dir: Path) -> None:
    """Test that modifying operations reload state from disk before applying changes."""
    # 1. Initialize settings
    settings = ProjectSettings(project_dir)
    settings.project_snapshot.title = "Original"
    settings.persist_settings()

    # 2. Simulate external modification (e.g. another process/thread)
    external_data = settings.project_snapshot.model_copy()
    external_data.title = "Changed Externally"
    (project_dir / "optigen.json").write_text(external_data.model_dump_json())

    # 3. Perform an operation on settings
    # This should trigger _transaction() -> _reload_from_disk()
    c = Constraint(name="c1", description="d", type="hard")
    settings.add_constraint(c)

    # 4. Verify that "Changed Externally" was preserved and constraint added
    assert settings.project_snapshot.title == "Changed Externally"
    assert settings.project_snapshot.constraints[0].name == "c1"


def test_add_run_composite_key(project_settings: ProjectSettings) -> None:
    """Test adding runs which use a composite key for uniqueness."""
    run1 = RunSolverScript(
        solver_script_name="s1",
        input_file=Path("in1.json"),
        output_file=Path("out1.json"),
    )
    project_settings.add_run(run1)

    # Same script, different input - allowed
    run2 = RunSolverScript(
        solver_script_name="s1",
        input_file=Path("in2.json"),
        output_file=Path("out2.json"),
    )
    project_settings.add_run(run2)
    assert len(project_settings.project_snapshot.runs) == 2

    # Exact duplicate - denied
    with pytest.raises(ValueError):
        project_settings.add_run(run1)


def test_scenario_operations(project_settings: ProjectSettings) -> None:
    """Brief test for scenario operations to ensure generic methods work."""
    s = Scenario(name="s1", request=Path("req.json"))
    project_settings.add_scenario(s)
    assert project_settings.get_scenario_by_name("s1") == s

    project_settings.remove_scenario("s1")
    assert project_settings.get_scenario_by_name("s1") is None
