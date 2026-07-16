from pathlib import Path

import pytest

from paper_agent.models import AssignmentSpec, Genre, ProjectConfig
from paper_agent.runtime import RunManifest, StageRunner, StageStatus
from paper_agent.storage import ProjectStore


def test_stage_runner_reuses_matching_artifact_and_invalidates_changed_input(
    tmp_path: Path,
) -> None:
    store = ProjectStore(tmp_path / "project")
    store.initialize(ProjectConfig(title="测试", genre=Genre.GENERAL_ESSAY))
    runner = StageRunner(store, {"analysis": "deterministic:a"})
    output = store.artifact_path("assignment.json")
    calls = 0

    def action() -> AssignmentSpec:
        nonlocal calls
        calls += 1
        return AssignmentSpec(purpose=f"任务-{calls}")

    first, first_reused = runner.execute_model(
        name="assignment",
        input_value={"document": "sha-a"},
        output_path=output,
        model_type=AssignmentSpec,
        action=action,
        model_label="deterministic:a",
    )
    second, second_reused = runner.execute_model(
        name="assignment",
        input_value={"document": "sha-a"},
        output_path=output,
        model_type=AssignmentSpec,
        action=action,
        model_label="deterministic:a",
    )
    third, third_reused = runner.execute_model(
        name="assignment",
        input_value={"document": "sha-b"},
        output_path=output,
        model_type=AssignmentSpec,
        action=action,
        model_label="deterministic:a",
    )

    assert first.purpose == second.purpose == "任务-1"
    assert third.purpose == "任务-2"
    assert (first_reused, second_reused, third_reused) == (False, True, False)
    assert calls == 2
    manifest = store.read_model(store.state_dir / "runs" / "latest.json", RunManifest)
    assert manifest.stages["assignment"].attempts == 2
    assert manifest.stages["assignment"].reused == 1


def test_stage_runner_records_failure_without_losing_manifest(tmp_path: Path) -> None:
    store = ProjectStore(tmp_path / "project")
    store.initialize(ProjectConfig(title="测试", genre=Genre.GENERAL_ESSAY))
    runner = StageRunner(store, {})

    def fail() -> AssignmentSpec:
        raise RuntimeError("provider unavailable")

    with pytest.raises(RuntimeError, match="provider unavailable"):
        runner.execute_model(
            name="assignment",
            input_value={"document": "sha-a"},
            output_path=store.artifact_path("assignment.json"),
            model_type=AssignmentSpec,
            action=fail,
        )

    manifest = store.read_model(store.state_dir / "runs" / "latest.json", RunManifest)
    record = manifest.stages["assignment"]
    assert record.status == StageStatus.FAILED
    assert record.error_type == "RuntimeError"
    assert record.error_message == "provider unavailable"
