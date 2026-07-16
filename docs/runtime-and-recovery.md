# 运行时、模型路由与检查点恢复

更新日期：2026-07-17

## 为什么需要独立运行时

论文生成包含多个昂贵且失败模式不同的步骤。把所有步骤写在一个 `run()` 函数里会造成三个问题：无法知道失败发生在哪个输入版本；重试时重复调用已经成功的模型；规划模型、写作模型和评估模型无法独立替换。

v0.3 将“论文功能模块”和“运行控制”分开：

- `workflow.py` 只定义阶段依赖和论文业务规则。
- `runtime.py` 管理输入指纹、阶段状态、产物哈希、失败记录和恢复。
- `providers.py` 的 `ModelRouter` 按职责选择模型，不让业务模块理解供应商细节。

## 显式阶段图

```text
assignment ─┐
skill ──────┼─► outline ─► draft-initial ─► audit-initial ─► revision ─► audit-final ─► export
evidence ───┘
```

前三个阶段只依赖各自必要输入，可以独立复用。`draft-initial` 与最终 `draft.json` 分开保存，防止修订覆盖初稿后破坏检查点语义。

## 检查点判定

每个阶段的输入指纹包含：

1. 管线版本。
2. 对该阶段有影响的配置和上游结构化产物。
3. 输入文档的 SHA-256，而不是文件修改时间。
4. 该职责实际使用的模型标签。

只有输入指纹相同、阶段状态为 `completed`、产物文件存在且产物 SHA-256 未变化时才能复用。任一条件不满足都会重新执行。失败阶段记录异常类型和截断后的消息，但不会删除已完成的其他阶段。

运行清单位于：

```text
.paper-agent/runs/latest.json
```

它包含每个阶段的 `status`、`attempts`、`reused`、`model_label`、输入/输出哈希和时间。`paper-agent status` 会显示这些运行信息。

## 多模型路由

默认 `--provider` 与 `--model` 是所有角色的后备模型。`--model-config` 可以覆盖四个角色中的任意部分：

```json
{
  "analysis": {
    "provider": "openai-compatible",
    "model": "analysis-model",
    "api_key_env": "ANALYSIS_API_KEY"
  },
  "planning": {
    "provider": "openai-compatible",
    "model": "planning-model",
    "api_key_env": "PLANNING_API_KEY"
  },
  "writing": {
    "provider": "anthropic",
    "model": "writing-model",
    "api_key_env": "WRITING_API_KEY"
  },
  "evaluation": {
    "provider": "openai-compatible",
    "model": "review-model",
    "api_key_env": "REVIEW_API_KEY"
  }
}
```

运行方式：

```bash
paper-agent run -p my-paper \
  --provider openai-compatible \
  --model fallback-model \
  --api-key-env FALLBACK_API_KEY \
  --model-config models.json
```

配置文件只保存环境变量名称，不保存 API Key 值。更换 `writing` 模型只会使初稿、修订和依赖它们的审计阶段失效；不需要重新解析任务书和来源。

## 恢复边界

- 进程或供应商在某阶段失败：修复问题后再次运行同一命令，已完成阶段自动复用。
- 用户修改任务书、案例、来源或数据：对应文档哈希变化，相关阶段重新执行。
- 用户手工修改中间 JSON：产物哈希不匹配，阶段重新执行；不要把手改中间产物当成可信缓存。
- 升级管线版本：所有阶段输入指纹变化，避免旧语义产物被新代码误用。
- 输出 Markdown/DOCX：导出成本低，当前每次运行都会重新生成，确保与最终审计一致。

