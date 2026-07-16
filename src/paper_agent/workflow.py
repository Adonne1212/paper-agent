from __future__ import annotations

from pathlib import Path

from pydantic import TypeAdapter

from paper_agent.audit import audit_draft, enrich_audit_with_model
from paper_agent.drafting import create_draft, revise_draft
from paper_agent.evidence import build_evidence_cards
from paper_agent.exporting import export_docx, export_markdown
from paper_agent.models import (
    AssignmentSpec,
    AuditReport,
    Document,
    DocumentRole,
    Draft,
    EvidenceCard,
    ModelProfile,
    Outline,
    WritingSkill,
)
from paper_agent.planning import create_outline
from paper_agent.providers import ModelRole, create_router
from paper_agent.requirements import analyze_assignment
from paper_agent.runtime import StageRunner
from paper_agent.skill import build_skill, enrich_skill_with_model
from paper_agent.storage import ProjectStore

evidence_adapter = TypeAdapter(list[EvidenceCard])


class Workflow:
    def __init__(
        self,
        store: ProjectStore,
        model_profile: ModelProfile,
        route_profiles: dict[ModelRole, ModelProfile] | None = None,
    ):
        self.store = store
        self.store.require()
        self.profile = model_profile
        self.router = create_router(model_profile, route_profiles)
        self.client = self.router.default
        self.runner = StageRunner(store, self.router.labels())

    def build_skill(self) -> WritingSkill:
        state = self.store.require()
        examples = self.store.documents_by_role(DocumentRole.EXAMPLE.value)
        skill = build_skill(examples, state.config.genre)
        assignments = self.store.documents_by_role(DocumentRole.ASSIGNMENT.value)
        assignment_text = "\n\n".join(item.text for item in assignments)
        skill = enrich_skill_with_model(
            skill,
            examples,
            assignment_text,
            self.router.for_role(ModelRole.ANALYSIS),
        )
        path = self.store.artifact_path("skill.json")
        self.store.write_model(path, skill)
        state.skill_path = str(path.relative_to(self.store.root))
        state.record("skill-ready", f"skill {skill.status}, confidence={skill.confidence}")
        self.store.save_state(state)
        return skill

    def analyze_assignment(self) -> AssignmentSpec:
        state = self.store.require()
        assignments = self.store.documents_by_role(DocumentRole.ASSIGNMENT.value)
        spec = analyze_assignment(assignments, self.router.for_role(ModelRole.ANALYSIS))
        path = self.store.artifact_path("assignment.json")
        self.store.write_model(path, spec)
        state.assignment_path = str(path.relative_to(self.store.root))
        state.record("assignment-ready", f"{len(spec.hard_constraints)} hard constraints")
        self.store.save_state(state)
        return spec

    def build_evidence(self) -> list[EvidenceCard]:
        state = self.store.require()
        source_documents = self.store.documents_by_role(DocumentRole.SOURCE.value)
        source_documents += self.store.documents_by_role(DocumentRole.DATA.value)
        cards = build_evidence_cards(source_documents)
        path = self.store.artifact_path("evidence.json")
        self.store.write_json(path, evidence_adapter.dump_python(cards, mode="json"))
        state.evidence_path = str(path.relative_to(self.store.root))
        state.record("evidence-ready", f"{len(cards)} evidence cards")
        self.store.save_state(state)
        return cards

    def plan(
        self,
        assignment: AssignmentSpec,
        skill: WritingSkill,
        evidence: list[EvidenceCard],
    ) -> Outline:
        state = self.store.require()
        outline = create_outline(
            state.config,
            assignment,
            skill,
            evidence,
            self.router.for_role(ModelRole.PLANNING),
        )
        path = self.store.artifact_path("outline.json")
        self.store.write_model(path, outline)
        state.outline_path = str(path.relative_to(self.store.root))
        state.record("outline-ready", f"{len(outline.sections)} sections")
        self.store.save_state(state)
        return outline

    def draft(
        self,
        assignment: AssignmentSpec,
        skill: WritingSkill,
        evidence: list[EvidenceCard],
        outline: Outline,
    ) -> Draft:
        state = self.store.require()
        draft = create_draft(
            state.config,
            assignment,
            outline,
            skill,
            evidence,
            self.router.for_role(ModelRole.WRITING),
        )
        path = self.store.artifact_path("draft.json")
        self.store.write_model(path, draft)
        state.draft_path = str(path.relative_to(self.store.root))
        state.record("draft-ready", f"{len(draft.sections)} sections via {draft.model}")
        self.store.save_state(state)
        return draft

    def audit(self, draft: Draft, outline: Outline, evidence: list[EvidenceCard]) -> AuditReport:
        state = self.store.require()
        examples = self.store.documents_by_role(DocumentRole.EXAMPLE.value)
        report = audit_draft(draft, outline, evidence, examples)
        if state.assignment_path:
            assignment = self.store.read_model(
                self.store.root / state.assignment_path, AssignmentSpec
            )
            report = enrich_audit_with_model(
                report,
                draft,
                outline,
                assignment,
                self.router.for_role(ModelRole.EVALUATION),
            )
        path = self.store.artifact_path("audit.json")
        self.store.write_model(path, report)
        state.audit_path = str(path.relative_to(self.store.root))
        state.record("audited", f"passed={report.passed}")
        self.store.save_state(state)
        return report

    def export(
        self,
        draft: Draft,
        evidence: list[EvidenceCard],
        report: AuditReport,
    ) -> tuple[Path, Path]:
        markdown = export_markdown(draft, evidence, report, self.store.outputs_dir / "draft.md")
        docx = export_docx(draft, report, self.store.outputs_dir / "draft.docx")
        state = self.store.require()
        state.record("exported", f"{markdown.name}, {docx.name}")
        self.store.save_state(state)
        return markdown, docx

    def run(self) -> tuple[WritingSkill, Outline, Draft, AuditReport, tuple[Path, Path]]:
        state = self.store.require()
        assignments = self.store.documents_by_role(DocumentRole.ASSIGNMENT.value)
        sources = self.store.documents_by_role(DocumentRole.SOURCE.value)
        data = self.store.documents_by_role(DocumentRole.DATA.value)
        if not assignments:
            raise RuntimeError("自动运行前必须导入至少一份 assignment。")
        if not sources and not data:
            raise RuntimeError("自动运行前必须导入至少一份 source 或真实 data。")
        if state.config.genre.value == "survey-report" and not data:
            raise RuntimeError("调研报告必须导入真实 data；系统不会虚构问卷、访谈或调研结果。")
        assignments_input = self._document_inputs(assignments)
        examples = self.store.documents_by_role(DocumentRole.EXAMPLE.value)
        examples_input = self._document_inputs(examples)
        source_input = self._document_inputs([*sources, *data])
        analysis_client = self.router.for_role(ModelRole.ANALYSIS)
        planning_client = self.router.for_role(ModelRole.PLANNING)
        writing_client = self.router.for_role(ModelRole.WRITING)
        evaluation_client = self.router.for_role(ModelRole.EVALUATION)

        assignment_path = self.store.artifact_path("assignment.json")
        assignment, reused = self.runner.execute_model(
            name="assignment",
            input_value={"documents": assignments_input, "model": analysis_client.label},
            output_path=assignment_path,
            model_type=AssignmentSpec,
            action=self.analyze_assignment,
            model_label=analysis_client.label,
        )
        self._sync_artifact("assignment_path", assignment_path, "assignment", reused)

        skill_path = self.store.artifact_path("skill.json")
        skill, reused = self.runner.execute_model(
            name="skill",
            input_value={
                "genre": state.config.genre.value,
                "examples": examples_input,
                "assignments": assignments_input,
                "model": analysis_client.label,
            },
            output_path=skill_path,
            model_type=WritingSkill,
            action=self.build_skill,
            model_label=analysis_client.label,
        )
        self._sync_artifact("skill_path", skill_path, "skill", reused)
        if skill.status != "ready":
            raise RuntimeError(
                f"案例 Skill 未达到自动门槛（confidence={skill.confidence}）；"
                "请增加同类案例或审阅 Skill。"
            )

        evidence_path = self.store.artifact_path("evidence.json")
        evidence, reused = self.runner.execute_json(
            name="evidence",
            input_value={"documents": source_input, "extractor": "extractive-v2"},
            output_path=evidence_path,
            adapter=evidence_adapter,
            action=self.build_evidence,
        )
        self._sync_artifact("evidence_path", evidence_path, "evidence", reused)

        outline_path = self.store.artifact_path("outline.json")
        outline, reused = self.runner.execute_model(
            name="outline",
            input_value={
                "config": self._config_input(),
                "assignment": assignment.model_dump(mode="json"),
                "skill": skill.model_dump(mode="json"),
                "evidence": evidence_adapter.dump_python(evidence, mode="json"),
                "model": planning_client.label,
            },
            output_path=outline_path,
            model_type=Outline,
            action=lambda: self.plan(assignment, skill, evidence),
            model_label=planning_client.label,
        )
        self._sync_artifact("outline_path", outline_path, "outline", reused)

        initial_draft_path = self.store.artifact_path("draft.initial.json")
        initial_draft, _ = self.runner.execute_model(
            name="draft-initial",
            input_value={
                "config": self._config_input(),
                "assignment": assignment.model_dump(mode="json"),
                "skill": skill.model_dump(mode="json"),
                "outline": outline.model_dump(mode="json"),
                "evidence": evidence_adapter.dump_python(evidence, mode="json"),
                "model": writing_client.label,
            },
            output_path=initial_draft_path,
            model_type=Draft,
            action=lambda: self._write_initial_draft(
                assignment, skill, evidence, outline, initial_draft_path
            ),
            model_label=writing_client.label,
        )

        initial_audit_path = self.store.artifact_path("audit.initial.json")
        initial_report, _ = self.runner.execute_model(
            name="audit-initial",
            input_value={
                "draft": initial_draft.model_dump(mode="json"),
                "outline": outline.model_dump(mode="json"),
                "evidence": evidence_adapter.dump_python(evidence, mode="json"),
                "examples": examples_input,
                "assignment": assignment.model_dump(mode="json"),
                "model": evaluation_client.label,
            },
            output_path=initial_audit_path,
            model_type=AuditReport,
            action=lambda: self._audit_to_path(
                initial_draft,
                outline,
                evidence,
                assignment,
                initial_audit_path,
            ),
            model_label=evaluation_client.label,
        )

        final_draft_path = self.store.artifact_path("draft.json")
        draft, reused = self.runner.execute_model(
            name="revision",
            input_value={
                "draft": initial_draft.model_dump(mode="json"),
                "outline": outline.model_dump(mode="json"),
                "evidence": evidence_adapter.dump_python(evidence, mode="json"),
                "audit": initial_report.model_dump(mode="json"),
                "model": writing_client.label,
            },
            output_path=final_draft_path,
            model_type=Draft,
            action=lambda: self._write_final_draft(
                initial_draft,
                outline,
                evidence,
                initial_report,
                final_draft_path,
            ),
            model_label=writing_client.label,
        )
        self._sync_artifact("draft_path", final_draft_path, "revision", reused)

        audit_path = self.store.artifact_path("audit.json")
        report, reused = self.runner.execute_model(
            name="audit-final",
            input_value={
                "draft": draft.model_dump(mode="json"),
                "outline": outline.model_dump(mode="json"),
                "evidence": evidence_adapter.dump_python(evidence, mode="json"),
                "examples": examples_input,
                "assignment": assignment.model_dump(mode="json"),
                "model": evaluation_client.label,
            },
            output_path=audit_path,
            model_type=AuditReport,
            action=lambda: self.audit(draft, outline, evidence),
            model_label=evaluation_client.label,
        )
        self._sync_artifact("audit_path", audit_path, "audit-final", reused)
        outputs = self.export(draft, evidence, report)
        return skill, outline, draft, report, outputs

    @staticmethod
    def _document_inputs(documents: list[Document]) -> list[dict[str, str]]:
        return [
            {"id": str(item.id), "sha256": str(item.sha256), "role": str(item.role.value)}
            for item in documents
        ]

    def _config_input(self) -> dict[str, object]:
        config = self.store.require().config
        return {
            "title": config.title,
            "genre": config.genre.value,
            "target_words": config.target_words,
            "language": config.language,
            "citation_style": config.citation_style,
        }

    def _sync_artifact(self, attribute: str, path: Path, stage: str, reused: bool) -> None:
        state = self.store.require()
        setattr(state, attribute, str(path.relative_to(self.store.root)))
        if reused:
            state.record("checkpoint-reused", stage)
        self.store.save_state(state)

    def _write_initial_draft(
        self,
        assignment: AssignmentSpec,
        skill: WritingSkill,
        evidence: list[EvidenceCard],
        outline: Outline,
        path: Path,
    ) -> Draft:
        state = self.store.require()
        draft = create_draft(
            state.config,
            assignment,
            outline,
            skill,
            evidence,
            self.router.for_role(ModelRole.WRITING),
        )
        self.store.write_model(path, draft)
        state.record("draft-initial-ready", f"{len(draft.sections)} sections via {draft.model}")
        self.store.save_state(state)
        return draft

    def _audit_to_path(
        self,
        draft: Draft,
        outline: Outline,
        evidence: list[EvidenceCard],
        assignment: AssignmentSpec,
        path: Path,
    ) -> AuditReport:
        examples = self.store.documents_by_role(DocumentRole.EXAMPLE.value)
        report = audit_draft(draft, outline, evidence, examples)
        report = enrich_audit_with_model(
            report,
            draft,
            outline,
            assignment,
            self.router.for_role(ModelRole.EVALUATION),
        )
        self.store.write_model(path, report)
        return report

    def _write_final_draft(
        self,
        draft: Draft,
        outline: Outline,
        evidence: list[EvidenceCard],
        report: AuditReport,
        path: Path,
    ) -> Draft:
        revised = revise_draft(
            draft,
            outline,
            evidence,
            report,
            self.router.for_role(ModelRole.WRITING),
        )
        self.store.write_model(path, revised)
        state = self.store.require()
        state.draft_path = str(path.relative_to(self.store.root))
        state.record("revision-ready", "bounded revision stage completed")
        self.store.save_state(state)
        return revised
