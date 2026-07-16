from paper_agent.models import Document, DocumentRole, Genre, TextBlock
from paper_agent.skill import build_skill


def example(identifier: str) -> Document:
    headings = ["引言", "概念与背景", "主要论证", "反方观点与回应", "结论"]
    blocks: list[TextBlock] = []
    for heading in headings:
        blocks.append(
            TextBlock(index=len(blocks), text=heading, heading=heading, level=1, kind="heading")
        )
        blocks.append(
            TextBlock(
                index=len(blocks),
                text=f"{heading}中的论述包含观点、证据与解释，并且说明适用范围。" * 5,
                heading=heading,
            )
        )
    return Document(
        id=identifier,
        role=DocumentRole.EXAMPLE,
        source_path=f"{identifier}.md",
        filename=f"{identifier}.md",
        sha256=identifier * 8,
        media_type="text/markdown",
        title=identifier,
        blocks=blocks,
    )


def test_build_skill_from_three_consistent_examples() -> None:
    skill = build_skill([example("a"), example("b"), example("c")], Genre.GENERAL_ESSAY)
    assert skill.status == "ready"
    assert skill.sample_count == 3
    assert skill.section_sequence[0] == "引言"
    assert abs(sum(skill.section_word_ratios.values()) - 1) < 1e-9
    assert all(rule.evidence for rule in skill.rules)
