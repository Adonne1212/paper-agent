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
    DocumentRole,
    Draft,
    EvidenceCard,
    ModelProfile,
    Outline,
    WritingSkill,
)
from paper_agent.planning import create_outline
from paper_agent.providers import create_client
from paper_agent.requirements import analyze_assignment
from paper_agent.skill import build_skill, enrich_skill_with_model
from paper_agent.storage import ProjectStore

evidence_adapter = TypeAdapter(list[EvidenceCard])


class Workflow:
    def __init__(self, store: ProjectStore, model_profile: ModelProfile):
        self.store = store
        self.profile = model_profile
        self.client = create_client(model_profile)

    def build_skill(self) -> WritingSkill:
        state = self.store.require()
        examples = self.store.documents_by_role(DocumentRole.EXAMPLE.value)
        skill = build_skill(examples, state.config.genre)
        assignments = self.store.documents_by_role(DocumentRole.ASSIGNMENT.value)
        assignment_text = "\n\n".join(item.text for item in assignments)
        skill = enrich_skill_with_model(skill, examples, assignment_text, self.client)
        path = self.store.artifact_path("skill.json")
        self.store.write_model(path, skill)
        state.skill_path = str(path.relative_to(self.store.root))
        state.record("skill-ready", f"skill {skill.status}, confidence={skill.confidence}")
        self.store.save_state(state)
        return skill

    def analyze_assignment(self) -> AssignmentSpec:
        state = self.store.require()
        assignments = self.store.documents_by_role(DocumentRole.ASSIGNMENT.value)
        spec = analyze_assignment(assignments, self.client)
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
        outline = create_outline(state.config, assignment, skill, evidence, self.client)
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
        draft = create_draft(state.config, assignment, outline, skill, evidence, self.client)
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
            report = enrich_audit_with_model(report, draft, outline, assignment, self.client)
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
        assignment = self.analyze_assignment()
        skill = self.build_skill()
        if skill.status != "ready":
            raise RuntimeError(
                f"案例 Skill 未达到自动门槛（confidence={skill.confidence}）；"
                "请增加同类案例或审阅 Skill。"
            )
        evidence = self.build_evidence()
        outline = self.plan(assignment, skill, evidence)
        draft = self.draft(assignment, skill, evidence, outline)
        report = self.audit(draft, outline, evidence)
        revised = revise_draft(draft, outline, evidence, report, self.client)
        if revised is not draft:
            draft = revised
            path = self.store.artifact_path("draft.json")
            self.store.write_model(path, draft)
            state = self.store.require()
            state.record("revised", "one bounded model revision pass")
            self.store.save_state(state)
            report = self.audit(draft, outline, evidence)
        outputs = self.export(draft, evidence, report)
        return skill, outline, draft, report, outputs
