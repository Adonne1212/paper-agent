# Writing Skill 格式

Writing Skill 是 JSON 产物，默认位于写作项目的 `.paper-agent/artifacts/skill.json`。

核心字段：

- `genre`：适用体裁。
- `sample_count`：参与归纳的案例数量。
- `confidence` 与 `status`：自动门禁结果。
- `section_sequence`：稳定章节/功能段序列。
- `section_word_ratios`：案例推导或体裁后备的篇幅分配。
- `style`：段落长度、句长和引用密度等描述性指标。
- `rules`：结构、修辞、论证、来源和诚信规则。
- `source_document_ids`：案例来源 ID，不嵌入案例全文。
- `validation`：门槛、模型语义分析和失败说明。

每条规则包含 `statement`、`support`、`evidence`、`counterexamples` 和 `required`。模型建议的规则如果不能给出至少两个真实案例 ID，会被丢弃。内置的“不伪造”和证据—推理规则不能被案例覆盖。

Skill 学到的是写作规范，不是题材答案。项目不会把案例中的事实观点自动迁移到新论文，也不会把大段案例文本保存进 Skill。
