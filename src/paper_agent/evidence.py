from __future__ import annotations

import re

from paper_agent.models import Document, EvidenceCard


def build_evidence_cards(
    documents: list[Document], *, max_excerpt_chars: int = 600
) -> list[EvidenceCard]:
    cards: list[EvidenceCard] = []
    for document in documents:
        for block in document.blocks:
            if block.kind == "heading" or len(block.text.strip()) < 30:
                continue
            excerpt = re.sub(r"\s+", " ", block.text).strip()[:max_excerpt_chars]
            location_parts = []
            if block.page:
                location_parts.append(f"p.{block.page}")
            if block.heading:
                location_parts.append(block.heading)
            location_parts.append(f"block-{block.index}")
            card_id = f"E-{document.id}-{block.index}"
            cards.append(
                EvidenceCard(
                    id=card_id,
                    document_id=document.id,
                    location=": ".join(location_parts),
                    excerpt=excerpt,
                    summary=_first_sentence(excerpt),
                    source_located=True,
                    bibliographic_verified=False,
                )
            )
    return cards


def _first_sentence(value: str) -> str:
    parts = re.split(r"(?<=[。！？!?])", value, maxsplit=1)
    return parts[0].strip()[:240]
