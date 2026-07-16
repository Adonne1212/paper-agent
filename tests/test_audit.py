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
