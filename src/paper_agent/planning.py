from __future__ import annotations

from paper_agent.genres import profile_for
from paper_agent.models import (
    AssignmentSpec,
    EvidenceCard,
    Outline,
    OutlineSection,
    ProjectConfig,
    WritingSkill,
)
from paper_agent.providers import ModelClient


def create_outline(
    config: ProjectConfig,
    assignment: AssignmentSpec,
    skill: WritingSkill,
    evidence: list[EvidenceCard],
    client: ModelClient,
) -> Outline:
    plan_data = client.generate_json(
        system=(
            "你是中文大学课程论文的规划助手。只基于任务说明与给定资料规划，"
            "不得编造文献、数据或调研事实。输出严格 JSON。"
        ),
        prompt=(
            "OUTPUT_KIND:PLAN\n"
            f"论文类型：{config.genre.value}\n题目：{config.title}\n"
            f"任务目的：{assignment.purpose}\n"
            f"受众：{assignment.audience}\n"
            f"硬约束：{assignment.hard_constraints}\n"
            f"禁止事项：{assignment.prohibited}\n"
            "返回字段 research_question 与 thesis。research_question 必须可分析且范围适当；"
            "thesis 必须回应问题、可争辩、可由资料支持。"
        ),
    )
    question = str(plan_data.get("research_question") or f"如何分析“{config.title}”这一问题？")
    thesis = str(plan_data.get("thesis") or f"本文围绕“{config.title}”建立基于资料的分析框架。")

    evidence_ids = [item.id for item in evidence]
    sequence = list(skill.section_sequence or [item.title for item in profile_for(config.genre)])
    for required in assignment.required_sections:
        if required not in sequence and required not in {"参考文献", "关键词"}:
            conclusion_index = next(
                (index for index, title in enumerate(sequence) if title in {"结论", "结语"}),
                len(sequence),
            )
            sequence.insert(conclusion_index, required)
    default_purpose = {item.title: item.purpose for item in profile_for(config.genre)}
    weights = {title: skill.section_word_ratios.get(title, 1 / len(sequence)) for title in sequence}
    weight_total = sum(weights.values()) or 1.0
    sections: list[OutlineSection] = []
    cursor = 0
    for index, title in enumerate(sequence, start=1):
        ratio = weights[title] / weight_total
        target_words = max(200, round(config.target_words * ratio))
        per_section = max(1, len(evidence_ids) // max(1, len(sequence)))
        selected = evidence_ids[cursor : cursor + per_section]
        cursor += per_section
        sections.append(
            OutlineSection(
                id=f"S{index}",
                title=title,
                purpose=default_purpose.get(title, f"完成“{title}”对应的论述功能"),
                target_words=target_words,
                evidence_ids=selected,
            )
        )
    if evidence_ids and sections and cursor < len(evidence_ids):
        sections[-1].evidence_ids.extend(evidence_ids[cursor:])
    return Outline(
        research_question=question,
        thesis=thesis,
        sections=sections,
        total_words=config.target_words,
    )
