import json

import pytest

from paper_agent.audit import audit_draft, enrich_audit_with_model
from paper_agent.genres import profile_for, rhetorical_moves_for
from paper_agent.models import (
    AssignmentSpec,
    Draft,
    DraftSection,
    Genre,
    ModelProfile,
    Outline,
    OutlineSection,
)
from paper_agent.providers import ModelClient


class HighQualityEvaluator(ModelClient):
    def generate(self, *, system: str, prompt: str) -> str:
        del system, prompt
        return json.dumps(
            {
                "scores": {
                    "task_fit": 82,
                    "coverage": 80,
                    "reasoning": 78,
                    "genre_moves": 83,
                    "coherence": 81,
                    "citation_use": 75,
                },
                "findings": [],
            }
        )


@pytest.mark.parametrize("genre", list(Genre))
def test_four_genres_can_satisfy_strict_one_shot_contract(genre: Genre) -> None:
    profile = profile_for(genre)
    sections: list[OutlineSection] = []
    draft_sections: list[DraftSection] = []
    for index, item in enumerate(profile, start=1):
        target = round(1000 * item.ratio)
        section_id = f"S{index}"
        sections.append(
            OutlineSection(
                id=section_id,
                title=item.title,
                purpose=item.purpose,
                target_words=target,
                claims=[f"{item.title}需要回应全文问题"],
                rhetorical_moves=rhetorical_moves_for(genre, item.title),
            )
        )
        sentence = f"{item.title}围绕任务目标展开判断、解释材料与限定结论，"
        content = (sentence * (target // len(sentence) + 1))[:target]
        draft_sections.append(
            DraftSection(section_id=section_id, title=item.title, content=content)
        )
    outline = Outline(
        research_question="如何形成完整且有依据的课程论文？",
        thesis="结构、证据和修订共同决定草稿完成度。",
        sections=sections,
        total_words=sum(item.target_words for item in sections),
    )
    draft = Draft(title="测试论文", sections=draft_sections, model="replay:test")
    report = audit_draft(draft, outline, [], [])

    assert report.passed
    assert not report.metrics["one_shot_success"]
    enriched = enrich_audit_with_model(
        report,
        draft,
        outline,
        AssignmentSpec(purpose="完成指定体裁课程论文"),
        HighQualityEvaluator(ModelProfile(provider="replay", model="evaluator")),
    )
    assert enriched.metrics["one_shot_success"]
    assert enriched.metrics["quality_score_mean"] >= 70
