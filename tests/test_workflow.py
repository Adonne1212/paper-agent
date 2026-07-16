from pathlib import Path

import pytest

from paper_agent.ingest import ingest_document
from paper_agent.models import DocumentRole, Genre, ModelProfile, ProjectConfig
from paper_agent.storage import ProjectStore
from paper_agent.workflow import Workflow


def write_example(path: Path, variant: int) -> None:
    path.write_text(
        f"""# 优秀案例 {variant}

## 引言

本文提出一个范围明确的问题，并说明讨论这个问题的意义与中心判断。

## 概念与背景

本文对核心概念进行界定，并基于课程背景建立后续分析所需的共同前提。

## 主要论证

主要论证把观点、材料和解释连接起来，同时区分事实判断与作者自己的分析。

## 反方观点与回应

本文考虑合理的反对意见，说明结论适用的条件以及仍然存在的限制。

## 结论

结论回答开头提出的问题，并概括论证意义而不加入新的外部事实。
""",
        encoding="utf-8",
    )


def test_end_to_end_offline_workflow(tmp_path: Path) -> None:
    project = tmp_path / "project"
    store = ProjectStore(project)
    store.initialize(ProjectConfig(title="数字工具与大学学习", genre=Genre.GENERAL_ESSAY))

    assignment = tmp_path / "assignment.txt"
    assignment.write_text("撰写一篇结构完整、引用可靠的课程论文。", encoding="utf-8")
    store.save_document(ingest_document(assignment, DocumentRole.ASSIGNMENT))
    for index in range(3):
        example_path = tmp_path / f"example-{index}.md"
        write_example(example_path, index)
        store.save_document(ingest_document(example_path, DocumentRole.EXAMPLE))
    source = tmp_path / "source.txt"
    source.write_text(
        "可靠的写作流程需要明确任务目标，并在规划、起草和修订之间反复检查。"
        "证据只有经过解释才能有效支持论文中的判断。",
        encoding="utf-8",
    )
    store.save_document(ingest_document(source, DocumentRole.SOURCE))

    workflow = Workflow(store, ModelProfile(provider="deterministic", model="offline"))
    skill, outline, draft, report, outputs = workflow.run()

    assert skill.status == "ready"
    assert len(outline.sections) == 5
    assert len(draft.sections) == 5
    assert report.passed
    assert all(path.exists() and path.stat().st_size > 0 for path in outputs)
    assert outputs[1].suffix == ".docx"
    assert store.require().current_stage == "exported"


def test_survey_report_requires_real_data(tmp_path: Path) -> None:
    project = tmp_path / "survey"
    store = ProjectStore(project)
    store.initialize(ProjectConfig(title="校园调研", genre=Genre.SURVEY_REPORT))
    assignment = tmp_path / "assignment.txt"
    assignment.write_text("形成一份调研报告。", encoding="utf-8")
    store.save_document(ingest_document(assignment, DocumentRole.ASSIGNMENT))
    for index in range(3):
        example_path = tmp_path / f"example-survey-{index}.md"
        write_example(example_path, index)
        store.save_document(ingest_document(example_path, DocumentRole.EXAMPLE))
    source = tmp_path / "survey-source.txt"
    source.write_text("这是一份用于说明调研背景的来源资料，包含足够长度的文本。", encoding="utf-8")
    store.save_document(ingest_document(source, DocumentRole.SOURCE))
    workflow = Workflow(store, ModelProfile(provider="deterministic", model="offline"))
    with pytest.raises(RuntimeError, match="真实 data"):
        workflow.run()
