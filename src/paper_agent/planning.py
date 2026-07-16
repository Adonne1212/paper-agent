from __future__ import annotations

import re
from typing import Any

from paper_agent.genres import profile_for, rhetorical_moves_for
from paper_agent.models import (
    AssignmentSpec,
    EvidenceCard,
    Outline,
    OutlineSection,
    ProjectConfig,
    WritingSkill,
)
from paper_agent.providers import ModelClient, ModelError


def create_outline(
    config: ProjectConfig,
    assignment: AssignmentSpec,
    skill: WritingSkill,
    evidence: list[EvidenceCard],
    client: ModelClient,
) -> Outline:
    sequence = _section_sequence(config, assignment, skill)
    purposes = {item.title: item.purpose for item in profile_for(config.genre)}
    targets = _word_targets(config.target_words, sequence, skill.section_word_ratios)
    evidence_index = "\n".join(
        f"[{item.id}] {item.summary} | 关键词: {', '.join(item.keywords)} | {item.location}"
        for item in evidence
    )
    section_contract = [
        {
            "id": f"S{index}",
            "title": title,
            "purpose": purposes.get(title, f"完成“{title}”对应的论述功能"),
            "target_words": targets[index - 1],
        }
        for index, title in enumerate(sequence, start=1)
    ]
    try:
        plan_data = client.generate_json(
            system=(
                "你是中文大学课程论文的规划助手。只基于任务说明和给定资料规划，"
                "不得编造文献、数据或调研事实。输出严格 JSON。"
            ),
            prompt=(
                "OUTPUT_KIND:PLAN\n"
                f"论文类型: {config.genre.value}\n题目: {config.title}\n"
                f"任务目的: {assignment.purpose}\n受众: {assignment.audience}\n"
                f"硬约束: {assignment.hard_constraints}\n禁止事项: {assignment.prohibited}\n"
                f"固定章节合同: {section_contract}\n"
                f"可用证据目录:\n{evidence_index or '无'}\n"
                "返回 research_question、thesis、sections。sections 必须逐项对应固定章节合同，"
                "每项包含 id、claims（1-3个可论证判断）、evidence_ids、counterargument（可空）、"
                "evidence_gap（证据不足时具体说明）。只能使用目录中的 Evidence ID。"
            ),
        )
    except ModelError:
        plan_data = {}

    question = str(plan_data.get("research_question") or f"如何分析“{config.title}”这一问题？")
    thesis = str(plan_data.get("thesis") or f"本文围绕“{config.title}”建立基于资料的分析框架。")
    raw_sections = plan_data.get("sections", [])
    if not isinstance(raw_sections, list):
        raw_sections = []
    model_sections = {
        str(item.get("id")): item
        for item in raw_sections
        if isinstance(item, dict) and item.get("id")
    }
    valid_ids = {item.id for item in evidence}
    sections: list[OutlineSection] = []
    for index, title in enumerate(sequence, start=1):
        section_id = f"S{index}"
        model_section = model_sections.get(section_id, {})
        claims = _clean_strings(model_section.get("claims"), limit=3)
        if not claims:
            claims = [f"本节将围绕“{title}”完成对研究问题的一个必要回答。"]
        requested = [
            item for item in _clean_strings(model_section.get("evidence_ids")) if item in valid_ids
        ]
        query = " ".join([config.title, title, purposes.get(title, ""), *claims])
        selected = _select_evidence(query, evidence, requested=requested, limit=4)
        gap = _optional_text(model_section.get("evidence_gap"))
        if not selected and title not in {"引言", "结论", "结语"}:
            gap = gap or "当前资料中没有与本节直接匹配的可定位证据。"
        sections.append(
            OutlineSection(
                id=section_id,
                title=title,
                purpose=purposes.get(title, f"完成“{title}”对应的论述功能"),
                target_words=targets[index - 1],
                claims=claims,
                rhetorical_moves=rhetorical_moves_for(config.genre, title),
                counterargument=_optional_text(model_section.get("counterargument")),
                evidence_gap=gap,
                evidence_ids=selected,
            )
        )
    return Outline(
        research_question=question,
        thesis=thesis,
        sections=sections,
        total_words=config.target_words,
    )


def _section_sequence(
    config: ProjectConfig, assignment: AssignmentSpec, skill: WritingSkill
) -> list[str]:
    sequence = list(skill.section_sequence or [item.title for item in profile_for(config.genre)])
    for required in assignment.required_sections:
        if required not in sequence and required not in {"参考文献", "关键词"}:
            conclusion = next(
                (index for index, title in enumerate(sequence) if title in {"结论", "结语"}),
                len(sequence),
            )
            sequence.insert(conclusion, required)
    return sequence


def _word_targets(total: int, sequence: list[str], ratios: dict[str, float]) -> list[int]:
    weights = [max(0.01, ratios.get(title, 1 / len(sequence))) for title in sequence]
    denominator = sum(weights)
    raw = [total * weight / denominator for weight in weights]
    targets = [int(item) for item in raw]
    for index in sorted(range(len(raw)), key=lambda item: raw[item] - targets[item], reverse=True):
        if sum(targets) >= total:
            break
        targets[index] += 1
    return targets


def _select_evidence(
    query: str,
    evidence: list[EvidenceCard],
    *,
    requested: list[str],
    limit: int,
) -> list[str]:
    selected = list(dict.fromkeys(requested))[:limit]
    query_terms = _terms(query)
    ranked = sorted(
        (
            (
                len(query_terms & (_terms(item.summary) | set(item.keywords))),
                len(query_terms & _terms(item.excerpt)),
                item,
            )
            for item in evidence
        ),
        key=lambda row: (row[0], row[1]),
        reverse=True,
    )
    for summary_score, excerpt_score, item in ranked:
        if summary_score == 0 and excerpt_score == 0:
            continue
        if item.id not in selected:
            selected.append(item.id)
        if len(selected) >= limit:
            break
    return selected


def _terms(value: str) -> set[str]:
    latin = set(re.findall(r"[a-z][a-z0-9_-]{2,}", value.lower()))
    runs = re.findall(r"[\u4e00-\u9fff]{2,}", value)
    chinese = {run[index : index + 2] for run in runs for index in range(len(run) - 1)}
    return latin | chinese


def _clean_strings(value: Any, *, limit: int | None = None) -> list[str]:
    if not isinstance(value, list):
        return []
    items = [str(item).strip() for item in value if str(item).strip()]
    return items[:limit] if limit is not None else items


def _optional_text(value: Any) -> str | None:
    text = str(value).strip() if value is not None else ""
    return text or None
