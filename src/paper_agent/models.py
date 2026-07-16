from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, model_validator


def utc_now() -> datetime:
    return datetime.now(UTC)


class Genre(StrEnum):
    GENERAL_ESSAY = "general-essay"
    LITERATURE_REVIEW = "literature-review"
    SURVEY_REPORT = "survey-report"
    UNDERGRAD_THESIS = "undergrad-thesis"


class DocumentRole(StrEnum):
    ASSIGNMENT = "assignment"
    EXAMPLE = "example"
    SOURCE = "source"
    DATA = "data"


class ProjectConfig(BaseModel):
    title: str
    genre: Genre
    target_words: int = Field(default=5000, ge=800, le=100_000)
    language: str = "zh-CN"
    citation_style: str = "gb-t-7714-2025"
    model_profile: str = "default"
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class AssignmentSpec(BaseModel):
    purpose: str
    audience: str = "课程教师与同学"
    hard_constraints: list[str] = Field(default_factory=list)
    soft_preferences: list[str] = Field(default_factory=list)
    required_sections: list[str] = Field(default_factory=list)
    prohibited: list[str] = Field(default_factory=list)
    source_document_ids: list[str] = Field(default_factory=list)
    constraint_evidence: dict[str, list[str]] = Field(default_factory=dict)
    model_analysis: str | None = None
    generated_at: datetime = Field(default_factory=utc_now)


class TextBlock(BaseModel):
    index: int
    text: str
    heading: str | None = None
    level: int | None = None
    page: int | None = None
    kind: str = "paragraph"


class Document(BaseModel):
    id: str
    role: DocumentRole
    source_path: str
    filename: str
    sha256: str
    media_type: str
    title: str
    blocks: list[TextBlock]
    warnings: list[str] = Field(default_factory=list)
    ingested_at: datetime = Field(default_factory=utc_now)

    @property
    def text(self) -> str:
        return "\n\n".join(block.text for block in self.blocks if block.text.strip())


class SkillRule(BaseModel):
    id: str
    category: str
    statement: str
    support: float = Field(ge=0, le=1)
    evidence: list[str] = Field(default_factory=list)
    counterexamples: list[str] = Field(default_factory=list)
    required: bool = False


class WritingSkill(BaseModel):
    name: str
    version: str = "0.1.0"
    genre: Genre
    sample_count: int
    recommended_sample_count: int = 5
    confidence: float = Field(ge=0, le=1)
    status: str
    section_sequence: list[str]
    section_word_ratios: dict[str, float]
    style: dict[str, Any]
    rules: list[SkillRule]
    source_document_ids: list[str]
    validation: dict[str, Any]
    generated_at: datetime = Field(default_factory=utc_now)

    @model_validator(mode="after")
    def ratios_are_sane(self) -> WritingSkill:
        if self.section_word_ratios:
            total = sum(self.section_word_ratios.values())
            if not 0.98 <= total <= 1.02:
                raise ValueError("section_word_ratios must sum to approximately 1")
        return self


class EvidenceCard(BaseModel):
    id: str
    document_id: str
    location: str
    excerpt: str
    summary: str
    keywords: list[str] = Field(default_factory=list)
    source_located: bool = True
    bibliographic_verified: bool = False


class OutlineSection(BaseModel):
    id: str
    title: str
    purpose: str
    target_words: int
    claims: list[str] = Field(default_factory=list)
    rhetorical_moves: list[str] = Field(default_factory=list)
    counterargument: str | None = None
    evidence_gap: str | None = None
    evidence_ids: list[str] = Field(default_factory=list)
    subsections: list[OutlineSection] = Field(default_factory=list)


class Outline(BaseModel):
    research_question: str
    thesis: str
    sections: list[OutlineSection]
    total_words: int
    generated_at: datetime = Field(default_factory=utc_now)


class DraftSection(BaseModel):
    section_id: str
    title: str
    content: str
    evidence_ids: list[str] = Field(default_factory=list)


class Draft(BaseModel):
    title: str
    sections: list[DraftSection]
    model: str
    generated_at: datetime = Field(default_factory=utc_now)

    @property
    def markdown(self) -> str:
        parts = [f"# {self.title}"]
        for section in self.sections:
            parts.extend((f"## {section.title}", section.content.strip()))
        return "\n\n".join(parts).strip() + "\n"


class Severity(StrEnum):
    BLOCKER = "blocker"
    IMPORTANT = "important"
    SUGGESTION = "suggestion"
    INFO = "info"


class AuditFinding(BaseModel):
    code: str
    severity: Severity
    message: str
    location: str | None = None
    suggestion: str | None = None


class AuditReport(BaseModel):
    passed: bool
    findings: list[AuditFinding]
    metrics: dict[str, Any]
    generated_at: datetime = Field(default_factory=utc_now)


class ModelProfile(BaseModel):
    provider: str
    model: str
    base_url: str | None = None
    api_key_env: str | None = None
    temperature: float = Field(default=0.3, ge=0, le=2)
    timeout_seconds: float = Field(default=120, gt=0)
    max_retries: int = Field(default=2, ge=0, le=5)


class WorkspaceState(BaseModel):
    config: ProjectConfig
    documents: list[str] = Field(default_factory=list)
    assignment_path: str | None = None
    skill_path: str | None = None
    evidence_path: str | None = None
    outline_path: str | None = None
    draft_path: str | None = None
    audit_path: str | None = None
    current_stage: str = "initialized"
    history: list[dict[str, Any]] = Field(default_factory=list)

    def record(self, stage: str, detail: str) -> None:
        self.current_stage = stage
        self.history.append({"stage": stage, "detail": detail, "at": utc_now().isoformat()})
        self.config.updated_at = utc_now()


def project_root(path: Path) -> Path:
    return path.expanduser().resolve()
