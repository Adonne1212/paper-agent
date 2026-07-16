# Paper Agent

Paper Agent 是一个面向中文大学写作任务的开源命令行 Agent。用户导入课程要求、至少三篇同类型优秀案例和可信来源后，它会自动归纳 Writing Skill、建立证据卡、生成论证提纲和高完成度草稿，并输出引用与一致性审计报告。

首版支持：

- 通识课结课论文
- 文献综述
- 课程调研报告
- 本科毕业论文
- DOCX、文字版 PDF、Markdown、TXT
- OpenAI-compatible API、Anthropic API 和本地兼容 endpoint
- Markdown 与 DOCX 输出

> Paper Agent 是写作辅导和草稿工具，不是代写或规避审核工具。输出必须由作者核验、修改并遵守学校的 AI 使用及披露规则。系统不会把缺少证据的数字、文献或调研过程自动当成事实。

## 为什么不是“一条 Prompt 写全文”

项目的工作流来自四组写作理论：Flower–Hayes 的递归写作过程、Genre-based pedagogy、Swales 修辞动作分析和 Toulmin 论证模型。优秀案例用于学习目标体裁的质量标准和修辞惯例，而不是复制案例语言。理论与工程映射见 [写作依据](docs/academic-writing-basis.md)。

## 安装

需要 Python 3.11 或更高版本：

```bash
python -m pip install .
paper-agent --help
```

开发安装：

```bash
python -m pip install -e ".[dev]"
python -m pytest
```

## 五分钟开始

### 1. 初始化

```bash
paper-agent init my-paper \
  --title "生成式人工智能与大学学习" \
  --genre general-essay \
  --words 5000
```

体裁值为 `general-essay`、`literature-review`、`survey-report` 或 `undergrad-thesis`。

### 2. 导入材料

```bash
paper-agent ingest -p my-paper -r assignment assignment.docx
paper-agent ingest -p my-paper -r example good-1.docx good-2.pdf good-3.md
paper-agent ingest -p my-paper -r source article-1.pdf article-2.txt
```

调研报告的真实问卷结果、访谈转写或数据说明应以 `data` 角色导入。扫描 PDF 会被明确拒绝，首版不提供 OCR。

### 3. 自动运行

OpenAI-compatible：

```powershell
$env:OPENAI_API_KEY="..."
paper-agent run -p my-paper `
  --provider openai-compatible `
  --model YOUR_MODEL `
  --api-key-env OPENAI_API_KEY
```

Anthropic：

```powershell
$env:ANTHROPIC_API_KEY="..."
paper-agent run -p my-paper `
  --provider anthropic `
  --model YOUR_MODEL `
  --api-key-env ANTHROPIC_API_KEY
```

Ollama 或其他 OpenAI-compatible 本地服务：

```bash
paper-agent run -p my-paper \
  --provider openai-compatible \
  --model LOCAL_MODEL \
  --base-url http://localhost:11434/v1 \
  --api-key-env LOCAL_API_KEY
```

若本地服务不校验密钥，可把对应环境变量设为任意非空占位值。

`--provider deterministic --model offline` 只用于离线演示和测试流水线，不代表实际写作质量。

### 4. 检查输出

```text
my-paper/
├── .paper-agent/          # 私有状态、解析文本和中间产物；默认不提交
│   ├── documents/
│   └── artifacts/
└── outputs/               # 草稿和导出；默认不提交
    ├── draft.md
    └── draft.docx
```

命令在审计存在 blocker 时返回退出码 `3`。草稿仍会保留，便于检查；不得把“生成成功”误解成“可以直接提交”。

## Writing Skill 如何生成

1. 解析案例的章节、段落和格式位置。
2. 比较多个案例，识别稳定结构、章节比例、修辞动作、论证和来源组织规则。
3. 每条规则保存支持案例、支持度、反例和来源。
4. 使用模型进行语义体裁分析时，只接受由至少两篇有效案例 ID 支持的规则。
5. 规则与内置学术诚信、论证和文献综合规范合并。
6. Skill 达到自动门槛后进入规划和写作；否则要求增加案例或审阅。

三篇是首版最低数量，五篇是建议数量。数量并非充分条件；案例同质性、解析完整度和结构一致性同样影响置信度。

任务书会另行解析为 `assignment.json`，区分硬约束、软偏好、必需章节和禁止事项，并在 `constraint_evidence` 中为每项约束保存任务书原文证据句。模型补充的约束只有在原文中找到支持时才会被接受；教师或课程的明确要求优先于案例 Skill，案例惯例不能覆盖任务书。

## 证据与引用

来源被拆成带原始文档和位置的 Evidence Card。生成正文使用 `[E:证据ID]` 临时绑定，审计器检查不存在的 ID、无证据数字、未完成占位符和案例文本重合。当前版本导出的“来源台账”不是完整的 GB/T 7714 书目格式；学校模板和正式参考文献仍需作者核对。此限制被保留为显式声明，避免伪装成已核验引用。

## 隐私

云模型运行时会把任务、案例和相关来源片段发送给用户选择的供应商。不要上传无权处理的论文或敏感数据。API Key 只从环境变量读取；不要把密钥作为命令参数、案例内容或 Issue 文本提交。

## 当前限制

- 不支持扫描 PDF、OCR、复杂公式和图片语义理解。
- 不自动访问付费数据库，也不绕过访问限制。
- 不自动实施问卷、访谈或实验。
- 不承诺查重率、AI 检测结果、分数或学校审核结果。
- DOCX 导出提供通用中文样式，学校专用模板仍需人工调整。
- 参考文献元数据与 GB/T 7714 最终排版尚需人工核验。
- 长篇本科论文建议分阶段运行并逐章审阅；不同模型有各自上下文与费用限制。

## 文档

- [项目定义](PROJECT_BRIEF.md)
- [架构](docs/architecture.md)
- [写作理论依据](docs/academic-writing-basis.md)
- [需求追踪](docs/requirements-traceability.md)
- [Writing Skill 格式](docs/writing-skill.md)
- [模型配置](docs/model-providers.md)
- [安全策略](SECURITY.md)

## 许可证

[Apache-2.0](LICENSE)
