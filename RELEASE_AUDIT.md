# 发布审查记录

## v0.3.0 本地架构重构

审查日期：2026-07-17

本版本停止依赖远程发布流程，目标是让项目在本地具备可恢复、可替换和可审计的 Agent 运行时。

### 架构变化

- 新增 `ModelRouter`，将 analysis、planning、writing、evaluation 四类职责路由到独立模型；原单模型参数保留为后备配置。
- 新增 `StageRunner` 和 `RunManifest`，为八个核心阶段保存输入指纹、产物哈希、状态、角色模型、尝试次数、复用次数和失败原因。
- 初稿、初审、修订稿和终审使用独立产物，避免修订覆盖初稿后破坏恢复语义。
- 输入指纹包含管线版本、必要配置、上游结构化产物、原始文档 SHA-256 和角色模型；产物被手工修改后不会作为缓存复用。
- `paper-agent status` 展示运行清单；`run --model-config` 支持同一次运行跨供应商/跨模型路由。

### 本地验收

- 旧的单模型 CLI 和四种体裁工作流保持兼容。
- 自动测试验证相同输入二次运行复用八个核心阶段，输入变化会失效重算，失败会持久化且不丢失清单。
- 自动测试验证模型角色覆盖、未知角色拒绝和默认模型回退。
- Ruff、37 项 pytest、83% 覆盖率和严格 mypy 检查全部通过。
- `paper_agent_cli-0.3.0-py3-none-any.whl` 已构建并在隔离环境安装；SHA-256 为 `56a11e91dd12e4385d34bd9d5138cbb31b54b032b5788d96cbdbe6b9359eb440`；CLI 正确显示 `--model-config`。
- 本版本只在本地提交，不执行 GitHub 推送、插件安装、浏览器登录或 MFA。

## v0.2.0 研究驱动质量改造

审查日期：2026-07-16

### 新增设计证据

- 对照 STORM 的预写作—提纲—分节生成结构，把提纲扩展为分节判断、修辞动作、反方观点、证据和证据缺口合同。
- 对照 PaperQA2 的问题相关证据选择，把 Evidence Card 增加为多句抽取摘要和轻量关键词，并在章节问题已知后进行相关性选择和 Evidence ID 白名单验证。
- 对照 AcaWriter 的语境化修辞动作反馈，为四种体裁建立章节级交际动作。
- 对照 Papers-to-Posts 的 Plan–Draft–Revise，把全局提纲和前文连续性记录注入分节起草，并将反馈按章节路由。
- 对照 Anthropic evaluator–optimizer 与 OpenScholar 多维长文评估，保留确定性事实门禁，并新增任务契合、覆盖、推理、体裁动作、连贯、引用使用六维评价。
- 对照自动写作反馈元分析的显著异质性，不将模型自评或离线测试宣传为真实成功率；新增重复试验和人工盲评协议。

### 实现与验收

- 提纲：模型可返回完整分节计划；未知 Evidence ID 被拒绝；模型/JSON 失败时有确定性相关性回退；章节字数预算精确等于总目标。
- 起草：使用全局结构合同、章节判断、修辞动作、证据缺口和最多两个前文章节的连续性记录。
- 修订：只向对应章节发送 actionable feedback；事实 blocker 不自动改写；修订后重新审计。
- 审计：新增总篇幅、分节完成度、证据实际使用、引用来源文档数和严格 `one_shot_success` 门禁。离线模式缺少独立质量评分时绝不会误报严格成功。
- 可靠性：对超时、网络错误、HTTP 408/409/429/5xx 和非法 JSON 做有限重试，不在请求正文或错误信息中暴露 API Key。
- 自动测试：32 项全部通过，覆盖四种体裁成功合同、证据摘要/定位、规划合同、篇幅门禁、独立评分阈值和瞬态重试；总覆盖率 81%。
- 静态检查：Ruff check 和 format check 通过。
- wheel：`paper_agent_cli-0.2.0-py3-none-any.whl` 构建成功，SHA-256 为 `384bb20fe16ec1862745f6cfab1feb2b30436a061889142837142a1e8b50b68f`。
- 隔离安装：wheel 强制安装成功；`paper-agent --help` 展示全部命令；包版本为 `0.2.0`。

### 结论与未声称事项

v0.2.0 的理论、代码和验收标准已经对应；相较 v0.1.0，首次生成的内容规划、证据相关性、跨节连续性、反馈定向性和可观测性均有实质增强。真实模型的跨主题成功率尚未在用户材料上执行重复付费试验和双人盲评，因此本审查不提供未经测量的成功率数字，也不承诺成绩、审核通过或可直接提交。

## v0.1.0 初始发布审查

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
