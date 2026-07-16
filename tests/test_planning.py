from paper_agent.models import (
    AssignmentSpec,
    EvidenceCard,
    Genre,
    ModelProfile,
    ProjectConfig,
    WritingSkill,
)
from paper_agent.planning import create_outline
from paper_agent.providers import DeterministicClient


def test_outline_has_claim_move_evidence_contract_and_exact_budget() -> None:
    skill = WritingSkill(
        name="test",
        genre=Genre.GENERAL_ESSAY,
        sample_count=3,
        confidence=0.9,
        status="ready",
        section_sequence=["引言", "主要论证", "结论"],
        section_word_ratios={"引言": 0.2, "主要论证": 0.6, "结论": 0.2},
        style={},
        rules=[],
        source_document_ids=[],
        validation={},
    )
    evidence = [
        EvidenceCard(
            id="E-learning-1",
            document_id="learning",
            location="block-1",
            excerpt="数字学习工具能够支持学生规划和反馈。",
            summary="数字学习工具支持规划",
            keywords=["数字", "学习", "规划"],
        ),
        EvidenceCard(
            id="E-other-1",
            document_id="other",
            location="block-1",
            excerpt="校园绿化改善了公共空间。",
            summary="校园绿化改善空间",
            keywords=["校园", "绿化"],
        ),
    ]
    outline = create_outline(
        ProjectConfig(
            title="数字学习工具与大学生学习规划",
            genre=Genre.GENERAL_ESSAY,
            target_words=1001,
        ),
        AssignmentSpec(purpose="分析数字工具的作用"),
        skill,
        evidence,
        DeterministicClient(ModelProfile(provider="deterministic", model="offline")),
    )

    assert sum(section.target_words for section in outline.sections) == 1001
    assert all(section.claims and section.rhetorical_moves for section in outline.sections)
    assert all(section.evidence_ids[0] == "E-learning-1" for section in outline.sections)
