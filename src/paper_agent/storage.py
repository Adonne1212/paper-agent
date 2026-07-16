from __future__ import annotations

import json
from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel

from paper_agent.models import Document, ProjectConfig, WorkspaceState, project_root

T = TypeVar("T", bound=BaseModel)


class ProjectStore:
    STATE_DIR = ".paper-agent"

    def __init__(self, root: Path):
        self.root = project_root(root)
        self.state_dir = self.root / self.STATE_DIR
        self.documents_dir = self.state_dir / "documents"
        self.artifacts_dir = self.state_dir / "artifacts"
        self.outputs_dir = self.root / "outputs"

    @property
    def state_path(self) -> Path:
        return self.state_dir / "state.json"

    def initialize(self, config: ProjectConfig, *, force: bool = False) -> WorkspaceState:
        if self.state_path.exists() and not force:
            raise FileExistsError(f"project already initialized: {self.root}")
        self.documents_dir.mkdir(parents=True, exist_ok=True)
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)
        self.outputs_dir.mkdir(parents=True, exist_ok=True)
        state = WorkspaceState(config=config)
        state.record("initialized", "project created")
        self.save_state(state)
        return state

    def require(self) -> WorkspaceState:
        if not self.state_path.exists():
            raise FileNotFoundError(f"not a Paper Agent project: {self.root}")
        return self.read_model(self.state_path, WorkspaceState)

    def save_state(self, state: WorkspaceState) -> None:
        self.write_model(self.state_path, state)

    def save_document(self, document: Document) -> Path:
        path = self.documents_dir / f"{document.id}.json"
        self.write_model(path, document)
        state = self.require()
        rel = str(path.relative_to(self.root))
        if rel not in state.documents:
            state.documents.append(rel)
        state.record("ingested", f"{document.role}: {document.filename}")
        self.save_state(state)
        return path

    def documents(self) -> list[Document]:
        state = self.require()
        return [self.read_model(self.root / path, Document) for path in state.documents]

    def documents_by_role(self, role: str) -> list[Document]:
        return [doc for doc in self.documents() if doc.role.value == role]

    def artifact_path(self, name: str) -> Path:
        return self.artifacts_dir / name

    @staticmethod
    def write_model(path: Path, model: BaseModel) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(path.suffix + ".tmp")
        temporary.write_text(model.model_dump_json(indent=2), encoding="utf-8")
        temporary.replace(path)

    @staticmethod
    def read_model(path: Path, model_type: type[T]) -> T:
        return model_type.model_validate_json(path.read_text(encoding="utf-8"))

    @staticmethod
    def write_json(path: Path, data: object) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(path.suffix + ".tmp")
        temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        temporary.replace(path)
