from __future__ import annotations

import re
from collections import Counter

from paper_agent.models import (
    AssignmentSpec,
    AuditFinding,
    AuditReport,
    Document,
    Draft,
    EvidenceCard,
    Outline,
    Severity,
)
from paper_agent.providers import ModelClient, ModelError

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

    section_lengths = {
        section.section_id: len(re.sub(r"\s+", "", section.content)) for section in draft.sections
    }
    target_by_section = {section.id: section.target_words for section in outline.sections}
    total_characters = sum(section_lengths.values())
    completion_ratio = total_characters / max(1, outline.total_words)
    if completion_ratio < 0.8:
        findings.append(
            AuditFinding(
                code="draft-too-short",
                severity=Severity.IMPORTANT,
                message=f"草稿仅达到目标篇幅的 {completion_ratio:.0%}。",
                suggestion="优先扩展证据解释、比较、反例处理和结论综合，不要用重复句凑字数。",
            )
        )
    elif completion_ratio > 1.25:
        findings.append(
            AuditFinding(
                code="draft-too-long",
                severity=Severity.SUGGESTION,
                message=f"草稿达到目标篇幅的 {completion_ratio:.0%}，可能明显超长。",
                suggestion="压缩背景复述和重复观点，保留分析链条。",
            )
        )
    for planned_section in outline.sections:
        actual_length = section_lengths.get(planned_section.id, 0)
        if actual_length < planned_section.target_words * 0.65:
            findings.append(
                AuditFinding(
                    code="section-underdeveloped",
                    severity=Severity.IMPORTANT,
                    message=(
                        f"本节约 {actual_length} 字，"
                        f"低于规划目标 {planned_section.target_words} 字。"
                    ),
                    location=planned_section.title,
                    suggestion="补全本节规划中的判断、证据解释、论证担保和适用边界。",
                )
            )

    evidence_document_map = {item.id: item.document_id for item in evidence}
    cited_documents = {
        evidence_document_map[item] for item in cited if item in evidence_document_map
    }
    assigned = {
        item for section in outline.sections for item in section.evidence_ids if item in valid_ids
    }
    draft_by_id = {section.section_id: section for section in draft.sections}
    for planned in outline.sections:
        section_draft = draft_by_id.get(planned.id)
        section_assigned = set(planned.evidence_ids) & valid_ids
        section_cited = set(CITATION_RE.findall(section_draft.content)) if section_draft else set()
        if section_assigned and not (section_assigned & section_cited):
            findings.append(
                AuditFinding(
                    code="section-evidence-not-used",
                    severity=Severity.IMPORTANT,
                    message="本节规划已绑定证据，但正文没有使用对应 Evidence ID。",
                    location=planned.title,
                    suggestion="将本节可核验判断绑定到规划证据，并解释证据与判断的关系。",
                )
            )

    blockers = sum(item.severity == Severity.BLOCKER for item in findings)
    important = sum(item.severity == Severity.IMPORTANT for item in findings)
    metrics = {
        "characters": len(re.sub(r"\s+", "", all_text)),
        "body_characters": total_characters,
        "target_characters": outline.total_words,
        "completion_ratio": round(completion_ratio, 4),
        "section_completion": {
            section_id: round(length / max(1, target_by_section.get(section_id, 1)), 4)
            for section_id, length in section_lengths.items()
        },
        "sections_expected": len(expected),
        "sections_written": len(actual),
        "evidence_available": len(valid_ids),
        "evidence_cited": len(citation_counts),
        "evidence_uncited": len(uncited),
        "evidence_assigned": len(assigned),
        "assigned_evidence_cited": len(assigned & set(cited)),
        "source_documents_cited": len(cited_documents),
        "unsupported_numeric_paragraphs": unsupported_numbers,
        "unresolved_placeholders": len(placeholders),
        "example_overlap": round(overlap, 4),
        "blockers": blockers,
        "important": important,
    }
    metrics["one_shot_success"] = _one_shot_success(metrics)
    return AuditReport(passed=blockers == 0, findings=findings, metrics=metrics)


def enrich_audit_with_model(
    report: AuditReport,
    draft: Draft,
    outline: Outline,
    assignment: AssignmentSpec,
    client: ModelClient,
) -> AuditReport:
    """Add bounded rubric feedback; deterministic integrity blockers remain authoritative."""
    if client.profile.provider.lower() in {"deterministic", "offline"}:
        return report
    contract = [
        {
            "id": item.id,
            "title": item.title,
            "purpose": item.purpose,
            "claims": item.claims,
            "moves": item.rhetorical_moves,
        }
        for item in outline.sections
    ]
    try:
        data = client.generate_json(
            system=(
                "你是独立的中文大学论文质量评估器。只评价提供的草稿，不补写事实，"
                "不把风格偏好当作事实错误。输出严格 JSON。"
            ),
            prompt=(
                "OUTPUT_KIND:EVALUATE_DRAFT\n"
                f"任务目的: {assignment.purpose}\n硬约束: {assignment.hard_constraints}\n"
                f"章节合同: {contract}\n"
                f"研究问题: {outline.research_question}\n"
                f"中心论点: {outline.thesis}\n"
                f"草稿:\n{draft.markdown[:30000]}\n"
                "返回 scores 和 findings。scores 仅含 task_fit、coverage、reasoning、"
                "genre_moves、coherence、citation_use，均为0-100整数。findings最多6项，"
                "每项含 code、severity（important或suggestion）、message、"
                "location（章节标题或空）、"
                "suggestion。优先报告会实质降低课程论文完成度的问题。"
            ),
        )
    except ModelError:
        return report
    allowed_locations = {item.title for item in draft.sections} | {
        item.section_id for item in draft.sections
    }
    findings = list(report.findings)
    raw_findings = data.get("findings", [])
    if not isinstance(raw_findings, list):
        raw_findings = []
    for item in raw_findings[:6]:
        if not isinstance(item, dict):
            continue
        severity = str(item.get("severity", "suggestion")).lower()
        location = str(item.get("location") or "").strip() or None
        if location not in allowed_locations:
            location = None
        message = str(item.get("message") or "").strip()
        if not message:
            continue
        findings.append(
            AuditFinding(
                code=f"model-{str(item.get('code') or 'quality').strip()}",
                severity=Severity.IMPORTANT if severity == "important" else Severity.SUGGESTION,
                message=message,
                location=location,
                suggestion=str(item.get("suggestion") or "").strip() or None,
            )
        )
    scores: dict[str, int] = {}
    for key in ("task_fit", "coverage", "reasoning", "genre_moves", "coherence", "citation_use"):
        try:
            scores[key] = max(0, min(100, int(data.get("scores", {}).get(key))))
        except (TypeError, ValueError, AttributeError):
            continue
    metrics = dict(report.metrics)
    if scores:
        metrics["quality_scores"] = scores
        metrics["quality_score_mean"] = round(sum(scores.values()) / len(scores), 1)
    blockers = sum(item.severity == Severity.BLOCKER for item in findings)
    metrics["blockers"] = blockers
    metrics["important"] = sum(item.severity == Severity.IMPORTANT for item in findings)
    metrics["one_shot_success"] = _one_shot_success(metrics)
    return report.model_copy(
        update={"passed": blockers == 0, "findings": findings, "metrics": metrics}
    )


def _one_shot_success(metrics: dict[str, object]) -> bool:
    """Strict operational gate; it is an eval signal, not a promise of a grade."""
    try:
        base_ok = (
            _metric_int(metrics, "blockers") == 0
            and _metric_int(metrics, "important") == 0
            and _metric_int(metrics, "sections_written")
            == _metric_int(metrics, "sections_expected")
            and 0.8 <= _metric_float(metrics, "completion_ratio") <= 1.25
            and _metric_int(metrics, "unresolved_placeholders") == 0
            and _metric_int(metrics, "unsupported_numeric_paragraphs") == 0
        )
    except (TypeError, ValueError):
        return False
    scores = metrics.get("quality_scores")
    if isinstance(scores, dict) and len(scores) == 6:
        try:
            return base_ok and all(_number(value) >= 70 for value in scores.values())
        except (TypeError, ValueError):
            return False
    return False


def _metric_int(metrics: dict[str, object], key: str) -> int:
    return int(_number(metrics.get(key, 0)))


def _metric_float(metrics: dict[str, object], key: str) -> float:
    return _number(metrics.get(key, 0))


def _number(value: object) -> float:
    if isinstance(value, bool):
        return float(int(value))
    if isinstance(value, int | float | str):
        return float(value)
    raise TypeError("metric is not numeric")
