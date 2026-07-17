import json
from pathlib import Path

import pytest
import typer
from typer.testing import CliRunner

from paper_agent.cli import _workflow, app
from paper_agent.models import Genre, ProjectConfig
from paper_agent.providers import ModelRole
from paper_agent.storage import ProjectStore

runner = CliRunner()


def test_main_help_lists_end_to_end_commands() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "ingest" in result.stdout
    assert "run" in result.stdout
    assert "skill" in result.stdout


def test_run_requires_explicit_model_provider() -> None:
    command = typer.main.get_command(app)
    run_command = command.commands["run"]  # type: ignore[attr-defined]
    required = {param.name for param in run_command.params if getattr(param, "required", False)}
    assert {"provider", "model"} <= required

    result = runner.invoke(app, ["run"])
    assert result.exit_code == 2
    result = runner.invoke(app, ["run", "--provider", "deterministic"])
    assert result.exit_code == 2


def test_model_config_routes_independent_models(tmp_path: Path) -> None:
    project = tmp_path / "project"
    ProjectStore(project).initialize(ProjectConfig(title="测试", genre=Genre.GENERAL_ESSAY))
    config = tmp_path / "models.json"
    config.write_text(
        json.dumps(
            {
                "planning": {"provider": "deterministic", "model": "planner"},
                "writing": {"provider": "deterministic", "model": "writer"},
                "evaluation": {"provider": "deterministic", "model": "reviewer"},
            }
        ),
        encoding="utf-8",
    )

    workflow = _workflow(project, "deterministic", "default", None, None, config)
    assert workflow.router.for_role(ModelRole.ANALYSIS).label == "deterministic:default"
    assert workflow.router.for_role(ModelRole.PLANNING).label == "deterministic:planner"
    assert workflow.router.for_role(ModelRole.WRITING).label == "deterministic:writer"
    assert workflow.router.for_role(ModelRole.EVALUATION).label == "deterministic:reviewer"


def test_model_config_rejects_unknown_role(tmp_path: Path) -> None:
    project = tmp_path / "project"
    ProjectStore(project).initialize(ProjectConfig(title="测试", genre=Genre.GENERAL_ESSAY))
    config = tmp_path / "models.json"
    config.write_text('{"unknown": {}}', encoding="utf-8")
    with pytest.raises(ValueError, match="未知模型角色"):
        _workflow(project, "deterministic", "default", None, None, config)
