from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import TypeVar
from uuid import uuid4

from pydantic import BaseModel, Field, TypeAdapter

from paper_agent.storage import ProjectStore

T = TypeVar("T", bound=BaseModel)
U = TypeVar("U")


def _now() -> datetime:
    return datetime.now(UTC)


class StageStatus(StrEnum):
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class StageRecord(BaseModel):
    name: str
    status: StageStatus
    input_digest: str
    output_path: str | None = None
    output_digest: str | None = None
    model_label: str | None = None
    attempts: int = 1
    reused: int = 0
    error_type: str | None = None
    error_message: str | None = None
    started_at: datetime = Field(default_factory=_now)
    completed_at: datetime | None = None


class RunManifest(BaseModel):
    run_id: str = Field(default_factory=lambda: uuid4().hex)
    pipeline_version: str = "0.3"
    model_routes: dict[str, str] = Field(default_factory=dict)
    stages: dict[str, StageRecord] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=_now)
    updated_at: datetime = Field(default_factory=_now)


def fingerprint(value: object) -> str:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def file_digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class StageRunner:
    """Checkpoint stages by validated inputs and immutable artifact digests."""

    def __init__(self, store: ProjectStore, model_routes: dict[str, str]):
        self.store = store
        self.runs_dir = store.state_dir / "runs"
        self.manifest_path = self.runs_dir / "latest.json"
        if self.manifest_path.exists():
            self.manifest = store.read_model(self.manifest_path, RunManifest)
        else:
            self.manifest = RunManifest(model_routes=model_routes)
        self.manifest.model_routes = model_routes
        self._save()

    def execute_model(
        self,
        *,
        name: str,
        input_value: object,
        output_path: Path,
        model_type: type[T],
        action: Callable[[], T],
        model_label: str | None = None,
    ) -> tuple[T, bool]:
        digest = self._input_digest(input_value)
        if self._reusable(name, digest, output_path):
            self._mark_reused(name)
            return self.store.read_model(output_path, model_type), True
        self._start(name, digest, output_path, model_label)
        try:
            result = action()
            if not output_path.exists():
                self.store.write_model(output_path, result)
            self._complete(name, output_path)
            return result, False
        except Exception as exc:
            self._fail(name, exc)
            raise

    def execute_json(
        self,
        *,
        name: str,
        input_value: object,
        output_path: Path,
        adapter: TypeAdapter[U],
        action: Callable[[], U],
        model_label: str | None = None,
    ) -> tuple[U, bool]:
        digest = self._input_digest(input_value)
        if self._reusable(name, digest, output_path):
            self._mark_reused(name)
            return adapter.validate_json(output_path.read_text(encoding="utf-8")), True
        self._start(name, digest, output_path, model_label)
        try:
            result = action()
            if not output_path.exists():
                self.store.write_json(output_path, adapter.dump_python(result, mode="json"))
            self._complete(name, output_path)
            return result, False
        except Exception as exc:
            self._fail(name, exc)
            raise

    def _reusable(self, name: str, input_digest: str, output_path: Path) -> bool:
        record = self.manifest.stages.get(name)
        return bool(
            record
            and record.status == StageStatus.COMPLETED
            and record.input_digest == input_digest
            and record.output_path == str(output_path.relative_to(self.store.root))
            and output_path.exists()
            and record.output_digest == file_digest(output_path)
        )

    def _input_digest(self, value: object) -> str:
        return fingerprint({"pipeline_version": self.manifest.pipeline_version, "input": value})

    def _start(
        self,
        name: str,
        input_digest: str,
        output_path: Path,
        model_label: str | None,
    ) -> None:
        previous = self.manifest.stages.get(name)
        self.manifest.stages[name] = StageRecord(
            name=name,
            status=StageStatus.RUNNING,
            input_digest=input_digest,
            output_path=str(output_path.relative_to(self.store.root)),
            model_label=model_label,
            attempts=(previous.attempts + 1) if previous else 1,
            reused=previous.reused if previous else 0,
        )
        self._save()

    def _complete(self, name: str, output_path: Path) -> None:
        record = self.manifest.stages[name]
        record.status = StageStatus.COMPLETED
        record.output_digest = file_digest(output_path)
        record.completed_at = _now()
        record.error_type = None
        record.error_message = None
        self._save()

    def _fail(self, name: str, exc: Exception) -> None:
        record = self.manifest.stages[name]
        record.status = StageStatus.FAILED
        record.error_type = type(exc).__name__
        record.error_message = str(exc)[:500]
        record.completed_at = _now()
        self._save()

    def _mark_reused(self, name: str) -> None:
        record = self.manifest.stages[name]
        record.reused += 1
        self._save()

    def _save(self) -> None:
        self.manifest.updated_at = _now()
        self.store.write_model(self.manifest_path, self.manifest)
