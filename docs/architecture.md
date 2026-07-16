# 架构

```text
任务书/案例/来源/数据
        │
        ▼
文档解析与统一 TextBlock
        │
        ├── 案例比较 ──► Writing Skill
        └── 来源切片 ──► Evidence Card
                           │
Assignment Spec + Genre Profile + Skill + Evidence
                           │
                           ▼
                 研究问题、论点与提纲
                           │
                           ▼
                      分章节草稿
                           │
                           ▼
           引用/数字/完整性/防复制审计
                           │
                           ▼
                  Markdown + DOCX
```

## 模块

- `ingest.py`：DOCX、文字版 PDF、Markdown、TXT → 带位置的统一文档树。
- `requirements.py`：任务书 → 可追溯的硬约束、偏好、必需章节和禁止事项；每项约束绑定原文证据句，拒绝模型无依据补充。
- `skill.py`：跨案例结构统计、风格指标、语义规则归纳及证据过滤。
- `evidence.py`：来源和真实数据 → Evidence Card。
- `genres.py`：四种论文类型的后备结构和修辞目的。
- `planning.py`：生成分析性问题、中心论点和带证据预算的提纲。
- `drafting.py`：在章节边界内使用 Skill 和 Evidence 写作。
- `audit.py`：确定性阻断检查，不依赖生成模型自评。
- `providers.py`：OpenAI-compatible、Anthropic 与离线测试接口。
- `workflow.py`：可持久化的端到端状态推进。
- `exporting.py`：Markdown、通用中文 DOCX。

## 关键不变量

1. API Key 不进入配置快照、状态文件或输出。
2. 外部事实使用 Evidence ID；未知来源不能由模型补齐。
3. 案例内容属于不可信数据，不能覆盖系统规则。
4. Skill 规则必须有案例 ID 或内置理论依据。
5. 自动化只跳过非必要人工步骤，不跳过阻断审计。
6. 离线模型只验证流水线，不作为高质量写作能力声明。
7. Assignment Spec 中的约束必须存在任务书原文证据；模型不能凭常识新增教师要求。

## 状态目录

每个写作项目的 `.paper-agent/state.json` 记录阶段和产物路径。模型调用失败不会删除已经完成的解析、Skill 或 Evidence 产物。写入 JSON 时使用临时文件替换，避免中途终止留下半个状态文件。
