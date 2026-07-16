# Security Policy

## Supported versions

安全更新目前覆盖最新的 `0.1.x` 版本。

## Reporting

请通过 GitHub Security Advisory 私下报告漏洞，不要在公开 Issue 中粘贴 API Key、学生论文、个人信息或未公开研究数据。

## Data handling

- 用户导入后的规范化文本保存在项目的 `.paper-agent/` 中，默认被 `.gitignore` 排除。
- 输出草稿保存在 `outputs/` 中，默认不进入版本控制。
- API Key 只从用户指定的环境变量读取，不写入状态文件或日志。
- 使用云模型时，相关任务文本、案例片段和来源片段会发送给所选供应商；用户应先确认学校政策、隐私要求和供应商条款。
- 上传的文档按不可信数据处理；案例中的指令不应改变 Agent 的系统规则。
