from paper_agent.audit import audit_draft
from paper_agent.models import (
    Draft,
    DraftSection,
    EvidenceCard,
    Outline,
    OutlineSection,
)


def test_invalid_evidence_blocks_release() -> None:
    outline = Outline(
        research_question="问题",
        thesis="论点",
        total_words=1000,
        sections=[OutlineSection(id="S1", title="引言", purpose="建立问题", target_words=200)],
    )
    draft = Draft(
        title="题目",
        model="test",
        sections=[
            DraftSection(
                section_id="S1",
                title="引言",
                content="这一判断来自不存在的证据。[E:E-missing-0]",
            )
        ],
    )
    report = audit_draft(draft, outline, [], [])
    assert not report.passed
    assert any(item.code == "invalid-evidence-id" for item in report.findings)


def test_valid_evidence_passes_blocker_gate() -> None:
    evidence = EvidenceCard(
        id="E-source-0",
        document_id="source",
        location="block-0",
        excerpt="来源内容足够长，用来支撑一个可验证判断。",
        summary="来源支持判断",
        source_located=True,
        bibliographic_verified=False,
    )
    outline = Outline(
        research_question="问题",
        thesis="论点",
        total_words=1000,
        sections=[
            OutlineSection(
                id="S1",
                title="引言",
                purpose="建立问题",
                target_words=200,
                evidence_ids=[evidence.id],
            )
        ],
    )
    draft = Draft(
        title="题目",
        model="test",
        sections=[
            DraftSection(
                section_id="S1",
                title="引言",
                content="已有资料支持这一判断。[E:E-source-0]",
                evidence_ids=[evidence.id],
            )
        ],
    )
    report = audit_draft(draft, outline, [evidence], [])
    assert report.passed


def test_audit_reports_completion_and_section_development() -> None:
    outline = Outline(
        research_question="问题",
        thesis="论点",
        total_words=1000,
        sections=[OutlineSection(id="S1", title="分析", purpose="分析", target_words=1000)],
    )
    draft = Draft(
        title="题目",
        model="test",
        sections=[DraftSection(section_id="S1", title="分析", content="内容很短。")],
    )
    report = audit_draft(draft, outline, [], [])
    codes = {item.code for item in report.findings}
    assert "draft-too-short" in codes
    assert "section-underdeveloped" in codes
    assert report.metrics["completion_ratio"] < 0.8
