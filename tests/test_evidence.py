from paper_agent.evidence import build_evidence_cards
from paper_agent.models import Document, DocumentRole, TextBlock


def test_evidence_card_keeps_location_keywords_and_salient_sentence() -> None:
    document = Document(
        id="source",
        role=DocumentRole.SOURCE,
        source_path="source.txt",
        filename="source.txt",
        sha256="abc",
        media_type="text/plain",
        title="数字学习",
        blocks=[
            TextBlock(
                index=1,
                page=2,
                heading="研究发现",
                text=(
                    "本段讨论大学学习中的一般背景。"
                    "无关内容用于补充说明。"
                    "数字学习工具能够支持学习规划和形成性反馈。"
                ),
            )
        ],
    )
    card = build_evidence_cards([document])[0]

    assert card.location == "p.2: 研究发现: block-1"
    assert card.keywords
    assert "数字学习工具" in card.summary
