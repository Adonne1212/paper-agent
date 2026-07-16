# Contributing

欢迎修复解析错误、增加可验证的体裁规则、改进审计器和补充脱敏测试夹具。

1. 创建分支并安装开发依赖：`python -m pip install -e ".[dev]"`。
2. 运行 `python -m ruff check src tests`。
3. 运行 `python -m ruff format --check src tests`。
4. 运行 `python -m pytest`。
5. PR 中说明行为变化、测试证据及其对学术诚信边界的影响。

不要提交真实学生文档、未经许可的优秀案例全文、API Key 或声称能够规避查重/AI 检测的功能。
