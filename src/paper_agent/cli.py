from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import typer
from pydantic import TypeAdapter

from paper_agent import __version__
from paper_agent.ingest import UnsupportedDocumentError, ingest_document
from paper_agent.models import (
    AuditReport,
    DocumentRole,
    Draft,
    EvidenceCard,
    Genre,
    ModelProfile,
    Outline,
    ProjectConfig,
)
from paper_agent.storage import ProjectStore
from paper_agent.workflow import Workflow

app = typer.Typer(
    name="paper-agent",
    help="从优秀案例学习写作 Skill，并基于可追溯资料生成中文大学论文草稿。",
    no_args_is_help=True,
)
skill_app = typer.Typer(help="生成和检查 Writing Skill。")
app.add_typer(skill_app, name="skill")
evidence_adapter = TypeAdapter(list[EvidenceCard])


def _version(value: bool) -> None:
    if value:
        typer.echo(__version__)
        raise typer.Exit()


@app.callback()
def main(
    version: Annotated[
        bool | None,
        typer.Option("--version", callback=_version, is_eager=True, help="显示版本号。"),
    ] = None,
) -> None:
    del version


def _profile(
    provider: str,
    model: str,
    base_url: str | None,
    api_key_env: str | None,
) -> ModelProfile:
    return ModelProfile(
        provider=provider,
        model=model,
        base_url=base_url,
        api_key_env=api_key_env,
    )


def _workflow(
    project: Path,
    provider: str,
    model: str,
    base_url: str | None,
    api_key_env: str | None,
) -> Workflow:
    return Workflow(ProjectStore(project), _profile(provider, model, base_url, api_key_env))


def _print_error(message: str) -> None:
    typer.secho(f"错误：{message}", fg=typer.colors.RED, err=True)


@app.command()
def init(
    project: Annotated[Path, typer.Argument(help="项目目录。")],
    title: Annotated[str, typer.Option("--title", "-t", help="论文题目或暂定题目。")],
    genre: Annotated[Genre, typer.Option("--genre", "-g", help="论文体裁。")],
    words: Annotated[int, typer.Option("--words", min=800, help="目标字数。")] = 5000,
    citation_style: Annotated[str, typer.Option("--citation-style")] = "gb-t-7714-2025",
) -> None:
    """初始化独立写作项目。"""
    try:
        store = ProjectStore(project)
        store.initialize(
            ProjectConfig(
                title=title,
                genre=genre,
                target_words=words,
                citation_style=citation_style,
            )
        )
    except (OSError, ValueError) as exc:
        _print_error(str(exc))
        raise typer.Exit(2) from exc
    typer.secho(f"已初始化：{store.root}", fg=typer.colors.GREEN)


@app.command()
def ingest(
    project: Annotated[Path, typer.Option("--project", "-p", help="Paper Agent 项目目录。")],
    role: Annotated[DocumentRole, typer.Option("--role", "-r", help="文档角色。")],
    files: Annotated[list[Path], typer.Argument(help="DOCX、文字版 PDF、Markdown 或 TXT。")],
) -> None:
    """解析并导入任务书、优秀案例、来源或真实数据。"""
    store = ProjectStore(project)
    try:
        store.require()
        for path in files:
            document = ingest_document(path, role)
            store.save_document(document)
            typer.echo(f"已导入 {document.filename} → {document.id}")
            for warning in document.warnings:
                typer.secho(f"  警告：{warning}", fg=typer.colors.YELLOW)
    except (OSError, ValueError, UnsupportedDocumentError) as exc:
        _print_error(str(exc))
        raise typer.Exit(2) from exc


@skill_app.command("build")
def skill_build(
    project: Annotated[Path, typer.Option("--project", "-p")] = Path("."),
) -> None:
    """从至少三篇同类型优秀案例生成结构化 Skill。"""
    workflow = _workflow(project, "deterministic", "offline", None, None)
    try:
        skill = workflow.build_skill()
    except (OSError, ValueError) as exc:
        _print_error(str(exc))
        raise typer.Exit(2) from exc
    typer.echo(
        json.dumps(
            {
                "status": skill.status,
                "confidence": skill.confidence,
                "samples": skill.sample_count,
                "sections": skill.section_sequence,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


@skill_app.command("show")
def skill_show(
    project: Annotated[Path, typer.Option("--project", "-p")] = Path("."),
) -> None:
    store = ProjectStore(project)
    state = store.require()
    if not state.skill_path:
        _print_error("尚未生成 Skill。")
        raise typer.Exit(2)
    typer.echo((store.root / state.skill_path).read_text(encoding="utf-8"))


@app.command()
def status(
    project: Annotated[Path, typer.Option("--project", "-p")] = Path("."),
) -> None:
    """显示当前阶段和已导入文档数量。"""
    store = ProjectStore(project)
    try:
        state = store.require()
        documents = store.documents()
    except OSError as exc:
        _print_error(str(exc))
        raise typer.Exit(2) from exc
    counts: dict[str, int] = {}
    for document in documents:
        counts[document.role.value] = counts.get(document.role.value, 0) + 1
    typer.echo(
        json.dumps(
            {
                "project": str(store.root),
                "title": state.config.title,
                "genre": state.config.genre.value,
                "stage": state.current_stage,
                "documents": counts,
                "artifacts": {
                    "assignment": state.assignment_path,
                    "skill": state.skill_path,
                    "outline": state.outline_path,
                    "draft": state.draft_path,
                    "audit": state.audit_path,
                },
            },
            ensure_ascii=False,
            indent=2,
        )
    )


@app.command()
def run(
    provider: Annotated[str, typer.Option(help="openai-compatible、anthropic 或 deterministic。")],
    model: Annotated[str, typer.Option(help="模型标识。")],
    project: Annotated[Path, typer.Option("--project", "-p")] = Path("."),
    base_url: Annotated[str | None, typer.Option(help="兼容 API 的基础 URL。")] = None,
    api_key_env: Annotated[
        str | None, typer.Option(help="保存 API Key 的环境变量名；不要直接传入密钥。")
    ] = None,
    allow_failed_audit: Annotated[
        bool, typer.Option(help="即使审计有 blocker 也保留导出；默认仍返回失败退出码。")
    ] = False,
) -> None:
    """自动执行 Skill → 证据 → 提纲 → 草稿 → 审计 → Markdown/DOCX。"""
    workflow = _workflow(project, provider, model, base_url, api_key_env)
    try:
        skill, outline, draft, report, outputs = workflow.run()
    except (OSError, ValueError, RuntimeError) as exc:
        _print_error(str(exc))
        raise typer.Exit(2) from exc
    typer.echo(f"Skill: {skill.status} ({skill.confidence:.1%})")
    typer.echo(f"提纲：{len(outline.sections)} 节；草稿：{len(draft.sections)} 节")
    typer.echo(f"审计：{'通过' if report.passed else '存在阻断项'}")
    for output in outputs:
        typer.echo(f"输出：{output}")
    if not report.passed and not allow_failed_audit:
        raise typer.Exit(3)


@app.command()
def audit(
    project: Annotated[Path, typer.Option("--project", "-p")] = Path("."),
) -> None:
    """重新审计已生成草稿。"""
    store = ProjectStore(project)
    state = store.require()
    required = (state.draft_path, state.outline_path, state.evidence_path)
    if not all(required):
        _print_error("缺少草稿、提纲或证据产物；请先运行 run。")
        raise typer.Exit(2)
    draft = store.read_model(store.root / str(state.draft_path), Draft)
    outline = store.read_model(store.root / str(state.outline_path), Outline)
    evidence = evidence_adapter.validate_json(
        (store.root / str(state.evidence_path)).read_text(encoding="utf-8")
    )
    workflow = _workflow(project, "deterministic", "offline", None, None)
    report = workflow.audit(draft, outline, evidence)
    typer.echo(report.model_dump_json(indent=2))
    if not report.passed:
        raise typer.Exit(3)


@app.command()
def export(
    project: Annotated[Path, typer.Option("--project", "-p")] = Path("."),
) -> None:
    """重新导出 Markdown 和 DOCX。"""
    store = ProjectStore(project)
    state = store.require()
    required = (state.draft_path, state.evidence_path, state.audit_path)
    if not all(required):
        _print_error("缺少草稿、证据或审计产物；请先运行 run。")
        raise typer.Exit(2)
    draft = store.read_model(store.root / str(state.draft_path), Draft)
    report = store.read_model(store.root / str(state.audit_path), AuditReport)
    evidence = evidence_adapter.validate_json(
        (store.root / str(state.evidence_path)).read_text(encoding="utf-8")
    )
    workflow = _workflow(project, "deterministic", "offline", None, None)
    for output in workflow.export(draft, evidence, report):
        typer.echo(output)
