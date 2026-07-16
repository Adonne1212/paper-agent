from paper_agent.models import Document, DocumentRole, ModelProfile, TextBlock
from paper_agent.providers import DeterministicClient
from paper_agent.requirements import analyze_assignment


def test_assignment_constraints_are_explicit_and_traceable() -> None:
    document = Document(
        id="assignment-1",
        role=DocumentRole.ASSIGNMENT,
        source_path="assignment.md",
        filename="assignment.md",
        sha256="a" * 64,
        media_type="text/markdown",
        title="任务要求",
        blocks=[
            TextBlock(
                index=0,
                text="论文必须包含文献综述和结论，不得编造调研数据；建议讨论一种反方观点。",
            )
        ],
    )
    client = DeterministicClient(ModelProfile(provider="deterministic", model="offline"))
    spec = analyze_assignment([document], client)
    assert spec.source_document_ids == [document.id]
    assert "文献综述" in spec.required_sections
    assert "结论" in spec.required_sections
    assert any("不得编造" in item for item in spec.prohibited)
    assert any("必须" in item for item in spec.hard_constraints)
    assert spec.constraint_evidence
    assert all(evidence for evidence in spec.constraint_evidence.values())


def test_discuss_as_a_verb_does_not_create_a_required_section() -> None:
    document = Document(
        id="assignment-2",
        role=DocumentRole.ASSIGNMENT,
        source_path="assignment.md",
        filename="assignment.md",
        sha256="b" * 64,
        media_type="text/markdown",
        title="任务要求",
        blocks=[
            TextBlock(
                index=0,
                text="论文需要讨论至少一种反方观点，并在结论中说明适用范围。",
            )
        ],
    )
    client = DeterministicClient(ModelProfile(provider="deterministic", model="offline"))
    spec = analyze_assignment([document], client)
    assert "讨论" not in spec.required_sections
    assert "结论" in spec.required_sections


class HallucinatingClient(DeterministicClient):
    def generate_json(self, *, system: str, prompt: str) -> dict[str, object]:
        del system, prompt
        return {
            "purpose": "分析指定主题",
            "audience": "课程教师",
            "hard_constraints": ["必须开展一百份问卷调查"],
            "soft_preferences": [],
            "required_sections": ["实证分析"],
            "prohibited": ["禁止引用中文资料"],
        }


def test_model_cannot_add_constraints_without_source_evidence() -> None:
    document = Document(
        id="assignment-3",
        role=DocumentRole.ASSIGNMENT,
        source_path="assignment.md",
        filename="assignment.md",
        sha256="c" * 64,
        media_type="text/markdown",
        title="任务要求",
        blocks=[TextBlock(index=0, text="提交一篇三千字左右的课程论文。")],
    )
    client = HallucinatingClient(ModelProfile(provider="fake", model="test"))
    spec = analyze_assignment([document], client)
    assert "必须开展一百份问卷调查" not in spec.hard_constraints
    assert "实证分析" not in spec.required_sections
    assert "禁止引用中文资料" not in spec.prohibited
