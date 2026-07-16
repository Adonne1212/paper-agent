from __future__ import annotations

import re
from collections import Counter

from paper_agent.models import (
    AuditFinding,
    AuditReport,
    Document,
    Draft,
    EvidenceCard,
    Outline,
    Severity,
)

CITATION_RE = re.compile(r"\[E:(E-[A-Za-z0-9-]+)\]")
NUMBER_RE = re.compile(r"(?<![A-Za-z])(?:\d+(?:\.\d+)?%|\d{2,}(?:\.\d+)?)")


def _ngrams(text: str, size: int = 20) -> set[str]:
    normalized = re.sub(r"[\s\W_]+", "", text)
    if len(normalized) < size:
        return set()
    return {normalized[index : index + size] for index in range(len(normalized) - size + 1)}


def _example_overlap(draft: str, examples: list[Document]) -> tuple[float, str | None]:
    draft_grams = _ngrams(draft)
    if not draft_grams:
        return 0.0, None
    highest = 0.0
    filename: str | None = None
    for example in examples:
        grams = _ngrams(example.text)
        if not grams:
            continue
        overlap = len(draft_grams & grams) / len(draft_grams)
        if overlap > highest:
            highest = overlap
            filename = example.filename
    return highest, filename


def audit_draft(
    draft: Draft,
    outline: Outline,
    evidence: list[EvidenceCard],
    examples: list[Document],
) -> AuditReport:
    findings: list[AuditFinding] = []
    valid_ids = {item.id for item in evidence}
    all_text = draft.markdown
    cited = CITATION_RE.findall(all_text)
    invalid = sorted(set(cited) - valid_ids)
    for evidence_id in invalid:
        findings.append(
            AuditFinding(
                code="invalid-evidence-id",
                severity=Severity.BLOCKER,
                message=f"引用了不存在的证据 ID：{evidence_id}",
                suggestion="删除该引用或导入并绑定真实来源。",
            )
        )

    placeholders = re.findall(r"【待补[^】]*】", all_text)
    for placeholder in placeholders:
        findings.append(
            AuditFinding(
                code="unresolved-placeholder",
                severity=Severity.IMPORTANT,
                message=f"存在待补内容：{placeholder}",
                suggestion="补充真实资料后重新生成或在提交前人工处理。",
            )
        )

    expected = {section.id for section in outline.sections}
    actual = {section.section_id for section in draft.sections}
    for missing in sorted(expected - actual):
        findings.append(
            AuditFinding(
                code="missing-section",
                severity=Severity.BLOCKER,
                message=f"提纲章节 {missing} 没有草稿。",
            )
        )

    unsupported_numbers = 0
    for section in draft.sections:
        for paragraph in re.split(r"\n\s*\n", section.content):
            if NUMBER_RE.search(paragraph) and not CITATION_RE.search(paragraph):
                unsupported_numbers += 1
                findings.append(
                    AuditFinding(
                        code="number-without-evidence",
                        severity=Severity.IMPORTANT,
                        message="包含数字性陈述但本段未绑定证据。",
                        location=section.title,
                        suggestion="绑定真实 Evidence ID，或明确说明数字来自用户自己的材料。",
                    )
                )

    citation_counts = Counter(cited)
    uncited = valid_ids - set(cited)
    overlap, overlap_file = _example_overlap(all_text, examples)
    if overlap >= 0.08:
        findings.append(
            AuditFinding(
                code="example-overlap",
                severity=Severity.BLOCKER if overlap >= 0.15 else Severity.IMPORTANT,
                message=f"草稿与案例 {overlap_file} 的连续文本相似度偏高（{overlap:.1%}）。",
                suggestion="重写相似片段；案例只应用于学习结构和质量标准。",
            )
        )

    duplicate_paragraphs = Counter(
        re.sub(r"\s+", "", item)
        for section in draft.sections
        for item in re.split(r"\n\s*\n", section.content)
        if len(re.sub(r"\s+", "", item)) >= 40
    )
    duplicates = [item for item, count in duplicate_paragraphs.items() if count > 1]
    if duplicates:
        findings.append(
            AuditFinding(
                code="duplicate-paragraph",
                severity=Severity.IMPORTANT,
                message=f"检测到 {len(duplicates)} 个重复段落。",
                suggestion="合并重复论述并改善章节分工。",
            )
        )

    blockers = sum(item.severity == Severity.BLOCKER for item in findings)
    important = sum(item.severity == Severity.IMPORTANT for item in findings)
    metrics = {
        "characters": len(re.sub(r"\s+", "", all_text)),
        "sections_expected": len(expected),
        "sections_written": len(actual),
        "evidence_available": len(valid_ids),
        "evidence_cited": len(citation_counts),
        "evidence_uncited": len(uncited),
        "unsupported_numeric_paragraphs": unsupported_numbers,
        "unresolved_placeholders": len(placeholders),
        "example_overlap": round(overlap, 4),
        "blockers": blockers,
        "important": important,
    }
    return AuditReport(passed=blockers == 0, findings=findings, metrics=metrics)
