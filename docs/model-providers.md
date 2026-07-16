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

模型必须能够遵循 JSON 输出要求。部分服务的上下文长度、内容安全规则、温度参数和中文能力不同。当前版本在客户端做 JSON 提取与 Schema 验证，但不会自动推断价格或上下文上限；用户应参考所选供应商的当前文档。
