from __future__ import annotations

import re
from collections import Counter

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
            keywords = _keywords(excerpt)
            cards.append(
                EvidenceCard(
                    id=card_id,
                    document_id=document.id,
                    location=": ".join(location_parts),
                    excerpt=excerpt,
                    summary=_extractive_summary(excerpt, keywords),
                    keywords=keywords,
                    source_located=True,
                    bibliographic_verified=False,
                )
            )
    return cards


def _extractive_summary(value: str, keywords: list[str]) -> str:
    sentences = [item.strip() for item in re.split(r"(?<=[。！？!?])", value) if item.strip()]
    if not sentences:
        return value.strip()[:240]
    first = sentences[0]
    if len(sentences) == 1:
        return first[:240]
    salient = max(sentences[1:], key=lambda item: sum(keyword in item for keyword in keywords))
    return f"{first} {salient}"[:240]


def _keywords(value: str, limit: int = 8) -> list[str]:
    """Create a cheap, language-agnostic retrieval index without extra dependencies."""
    latin = re.findall(r"[A-Za-z][A-Za-z0-9_-]{2,}", value.lower())
    chinese_runs = re.findall(r"[\u4e00-\u9fff]{2,}", value)
    chinese = [run[index : index + 2] for run in chinese_runs for index in range(len(run) - 1)]
    stop = {"本文", "研究", "进行", "通过", "以及", "可以", "相关", "主要"}
    counts = Counter(token for token in latin + chinese if token not in stop)
    return [token for token, _ in counts.most_common(limit)]
