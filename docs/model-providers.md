# 模型配置

## OpenAI-compatible

适用于实现 `/chat/completions` 的服务，包括很多本地和第三方网关：

```bash
paper-agent run -p PROJECT \
  --provider openai-compatible \
  --model MODEL_ID \
  --base-url https://example.com/v1 \
  --api-key-env PROVIDER_API_KEY
```

## Anthropic

```bash
paper-agent run -p PROJECT \
  --provider anthropic \
  --model MODEL_ID \
  --api-key-env ANTHROPIC_API_KEY
```

## 本地/离线

OpenAI-compatible 本地服务使用相同接口。`deterministic` 是测试替身，只产生固定结构文本：

```bash
paper-agent run -p PROJECT --provider deterministic --model offline
```

## 供应商差异

模型必须能够遵循 JSON 输出要求。部分服务的上下文长度、内容安全规则、温度参数和中文能力不同。当前版本在客户端做 JSON 提取与 Schema 验证；对超时、网络错误、HTTP 408/409/429/5xx 和非法 JSON 默认最多额外重试两次。重试是可靠性保护，不会自动扩大上下文，也不会修复供应商不兼容的响应结构。工具不会自动推断价格或上下文上限；用户应参考所选供应商的当前文档。

## 按职责切换模型

v0.3 支持把 `analysis`、`planning`、`writing` 和 `evaluation` 分别路由到不同供应商或模型。命令行的 provider/model 仍作为后备配置，角色覆盖项从 `--model-config` JSON 读取。完整格式、检查点失效规则和示例见 [运行时文档](runtime-and-recovery.md)。
