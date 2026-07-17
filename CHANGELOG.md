# Changelog

## 0.3.1 — 2026-07-17

- 修复 GitHub Actions 中因 Typer/Rich 彩色错误输出和终端宽度差异导致的 CLI 测试失败。
- CLI 必填参数测试改为直接验证命令契约，同时继续验证缺参时的退出码。
- 在 Python 3.11 与 3.13 的全新环境中通过 37 项测试、Ruff 和严格 mypy 检查。

## 0.1.0 — 2026-07-16

- 首个可发布版本。
- 支持 DOCX、文字版 PDF、Markdown 和 TXT 摄入，明确拒绝扫描版 PDF。
- 支持从至少三篇优秀案例生成带证据、置信度和版本信息的 Writing Skill。
- 支持把任务书解析为高优先级硬约束、必需章节和禁止事项。
- 支持 OpenAI-compatible、Anthropic 和本地兼容 endpoint。
- 提供自动规划、分节写作、Evidence ID、引用审计、案例防复制检查。
- 支持 Markdown 和 DOCX 导出。
