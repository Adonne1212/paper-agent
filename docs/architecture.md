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
        StageRunner + ModelRouter
        │ 输入指纹 / 产物哈希 / 角色模型
        ▼
Assignment Spec + Genre Profile + Skill + Evidence
                           │
                           ▼
       研究问题、论点、分节判断/修辞动作/证据合同
                           │
                           ▼
                      分章节草稿
                           │
                           ▼
      确定性事实审计 + 独立质量量表 + 定向修订
                           │
                           ▼
                  Markdown + DOCX
```

## 模块

- `ingest.py`：DOCX、文字版 PDF、Markdown、TXT → 带位置的统一文档树。
- `requirements.py`：任务书 → 可追溯的硬约束、偏好、必需章节和禁止事项；每项约束绑定原文证据句，拒绝模型无依据补充。
- `skill.py`：跨案例结构统计、风格指标、语义规则归纳及证据过滤。
- `evidence.py`：来源和真实数据 → 带位置、摘要和检索关键词的 Evidence Card。
- `genres.py`：四种论文类型的后备结构、章节目的和修辞动作。
- `planning.py`：生成研究问题、中心论点和分节判断—证据合同；验证模型 Evidence ID，并以相关性检索回退。
- `drafting.py`：使用全局合同、前文连续性记录和章节证据分节写作，再按章节反馈定向修订。
- `audit.py`：确定性事实门禁，加独立模型六维质量量表和一次生成成功门禁。
- `providers.py`：OpenAI-compatible、Anthropic 与离线测试接口；支持有限瞬态错误和非法 JSON 重试。
- `runtime.py`：阶段清单、输入指纹、产物哈希、失败记录与检查点恢复。
- `workflow.py`：声明端到端阶段依赖；按 analysis/planning/writing/evaluation 路由模型。
- `exporting.py`：Markdown、通用中文 DOCX。

## 关键不变量

1. API Key 不进入配置快照、状态文件或输出。
2. 外部事实使用 Evidence ID；未知来源不能由模型补齐。
3. 案例内容属于不可信数据，不能覆盖系统规则。
4. Skill 规则必须有案例 ID 或内置理论依据。
5. 自动化只跳过非必要人工步骤，不跳过阻断审计。
6. 离线模型只验证流水线，不作为高质量写作能力声明。
7. Assignment Spec 中的约束必须存在任务书原文证据；模型不能凭常识新增教师要求。
8. 模型质量评价不能新增 blocker；事实与完整性阻断只由确定性检查产生。
9. 检查点只有在输入指纹和产物哈希同时匹配时才能复用；代码管线版本参与指纹。
10. 初稿和修订稿是不同产物，修订不得覆盖初稿检查点。

## 状态目录

每个写作项目的 `.paper-agent/state.json` 记录阶段和产物路径。模型调用失败不会删除已经完成的解析、Skill 或 Evidence 产物。写入 JSON 时使用临时文件替换，避免中途终止留下半个状态文件。

`.paper-agent/runs/latest.json` 记录更细粒度的运行清单。恢复和模型路由细节见 [运行时、模型路由与检查点恢复](runtime-and-recovery.md)。
