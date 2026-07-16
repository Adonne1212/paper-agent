# v0.1.0 发布审查

审查日期：2026-07-16

## 审查方法

本审查分别核对：用户最初明确需求、写作理论与实现的对应关系、README 能力声明、自动化测试、wheel 安装包和从安装包运行的端到端示例。没有把“代码存在”单独视为功能完成证据。

## 原始需求审查

| 明确需求 | 实现证据 | 验证证据 | 结论 |
|---|---|---|---|
| 在独立目录工作 | `paper-agent/`、嵌套 `AGENTS.md` | 项目无父目录代码依赖 | 满足 |
| 命令行工具 | `paper_agent.cli`、console script | CLI help 测试、wheel smoke test | 满足 |
| 多模型切换 | OpenAI-compatible、Anthropic、本地兼容 endpoint | 两种 HTTP 协议 mock 契约测试；本地兼容复用 OpenAI 路径 | 满足接口要求；未使用用户密钥做线上计费测试 |
| 中文优先 | 中文 CLI、Prompt、Genre Profile、DOCX 样式 | 中文 Markdown/DOCX 端到端输出与编码检查 | 满足 |
| 四类论文 | 四个 `Genre` 与独立 Genre Profile | 四类 profile 完整性测试 | 满足结构支持；真实写作效果仍取决于模型与案例 |
| DOCX、文字 PDF、Markdown、TXT | `ingest.py` 四条解析路径 | 四类解析测试，含文字 PDF 页码 | 满足 |
| 暂不支持扫描 PDF | 无文字层时明确拒绝 | 空白/扫描 PDF 拒绝测试 | 满足 |
| 上传一定数量案例后自动总结 Skill | 跨案例结构统计、语义规则归纳、证据过滤、置信门禁 | 三案例 Skill 测试、端到端 smoke test | 满足；v0.1 最低三篇、建议五篇 |
| Skill 后自动按工作流写作 | `Workflow.run` 串联 Skill、Evidence、Plan、Draft、Audit、Export | 从 wheel 安装后的一条 `run` 命令完成全链 | 满足 |
| 教师/课程要求优先 | 独立 Assignment Spec，区分硬约束、必需章节、禁止事项，每项绑定任务书证据句并注入规划和写作 | 任务要求解析、结构语义消歧、无依据模型约束拒绝测试 | 满足 |
| 尽可能高完成度草稿 | 分章节目标、字数预算、Evidence ID、论证规则、一次有边界修订、确定性审计 | 端到端结构与审计测试 | 工程机制满足；没有把离线测试文本冒充真实模型质量 |
| 学术诚信边界 | 数据真实性门禁、假 Evidence 阻断、案例重合检查、Prompt Injection 警告 | 假引用、无调研数据、扫描件及注入测试 | 满足 |
| 可在 GitHub 发布 | `pyproject.toml`、CI、Apache-2.0、README、贡献/安全文档、wheel | wheel 构建和隔离安装成功 | 满足本地发布条件；远程仓库尚未由用户授权创建 |

## 理论—实现审查

| 理论 | 实现位置 | 审查结果 |
|---|---|---|
| Flower–Hayes 递归写作过程 | Plan → Draft → Audit → bounded Revision → Audit | 真实模型路径执行一次有边界修订；阻断级事实问题不自动改写 |
| Genre-based pedagogy | 四类 Genre Profile、案例 Skill、任务上下文 | 不用统一五段式覆盖全部体裁；案例规则可补充内置规则 |
| Swales 修辞动作 | section purpose、Skill 的 structure/semantic rules | 章节按交际目的规划，不只学习标题词频 |
| Toulmin 论证 | 必需的证据—推理规则、规划 Prompt、审计 | 要求 Claim–Evidence–Warrant；当前审计主要验证来源绑定，深层推理质量仍由模型和人工复核 |
| 范例学习/形成性评价 | 多案例比较、规则证据、支持度、反例、门禁 | 不从单篇案例生成稳定 Skill，不把案例原句作为模板 |
| 文献综合 | 文献综述 Profile、主题综合硬规则、Evidence Card | 支持基于来源的综合；v0.1 不提供数据库检索或完整书目管理器 |

## 实现声明审查

以下内容已在 README 明确限制，不能在发布宣传中改写成已实现能力：

- 不支持扫描 PDF/OCR、复杂公式和图片语义。
- 不自动访问付费数据库或实施真实调查。
- Evidence Card 可定位回用户文件，但不等于书目元数据已由 Crossref/数据库核验。
- 输出保留 Evidence ID 台账，GB/T 7714 最终书目和学校模板需要人工核验。
- 离线 deterministic provider 只验证流程，不代表写作质量。
- 不承诺查重率、AI 检测、分数或学校审核结果。

## 发布验证记录

- Ruff：通过。
- pytest：24 项发布审查测试全部通过，包含任务书约束原文追踪、结构语义消歧、无依据模型约束拒绝与本地 Markdown 链接检查。
- wheel：`paper_agent_cli-0.1.0-py3-none-any.whl` 构建成功；最终 SHA-256 为 `be6107ced1ca7d3593553f13717fd25b2c3443f5b452686c175ff6a7eaf6d496`。
- 源码—wheel 一致性：wheel 内 16 个 `paper_agent/*.py` 与当前源码逐文件 SHA-256 对比，无差异。
- wheel 隔离安装：成功。
- 安装包 CLI smoke：三案例 → Skill（ready，87.6%）→ 带原文证据的 Assignment Spec → 五节提纲 → 五节草稿 → 审计 → Markdown/DOCX，成功。
- 中文编码：Markdown 与 DOCX 均包含预期中文标题，无 Unicode replacement character。

## 发布结论

v0.1.0 达到公开 alpha 发布条件。它实现了用户要求的核心闭环，并对尚未实现的检索、正式参考文献排版、学校模板适配和真实模型效果边界作出明确声明。远程 GitHub 发布属于外部写操作，应在用户确认仓库名、公开性并完成 GitHub 授权后执行。
