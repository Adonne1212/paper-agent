from typer.testing import CliRunner

from paper_agent.cli import app

runner = CliRunner()


def test_main_help_lists_end_to_end_commands() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "ingest" in result.stdout
    assert "run" in result.stdout
    assert "skill" in result.stdout


def test_run_requires_explicit_model_provider() -> None:
    result = runner.invoke(app, ["run"])
    assert result.exit_code == 2
    assert "--provider" in result.stdout
    result = runner.invoke(app, ["run", "--provider", "deterministic"])
    assert result.exit_code == 2
    assert "--model" in result.stdout
