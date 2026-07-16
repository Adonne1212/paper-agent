# 研究驱动的设计与成功门禁

更新日期：2026-07-16

本文件回答两个问题：成熟 Agent/长文生成代码有哪些可复用机制；写作理论和写作程序如何把这些机制变成课程论文的质量控制。结论只采用能落到代码和验收项的证据，不把论文中的平均效果直接宣传为本项目效果。

## 1. Agent 与长文生成代码

### STORM：先研究和规划，再按章节写作

STORM 把长文生成拆成知识整理、提纲生成、文章生成和润色。其文章生成模块为具体章节构造检索查询，并用与该节相关的资料填充提纲；这比把来源按顺序平均分给章节更合理。STORM 官方也明确说明其输出不是无需修改的出版级文章，因此本项目不会把“流水线完成”写成“可以直接提交”。

对本项目的影响：

- `planning.py` 先为每节建立判断、修辞动作、证据和证据缺口合同。
- 证据按章节语义相关性选择，允许同一关键证据支持多个相关章节。
- 提纲、草稿和审计继续保存为阶段产物，模型失败时可定位到具体阶段。

来源：[STORM 官方仓库](https://github.com/stanford-oval/storm)

### PaperQA2：问题相关的证据摘要、重排和多来源综合

PaperQA2 的官方算法是“搜索候选资料 → 按当前问题收集、概括并重排证据 → 用最佳证据生成答案”，并提供证据数量、最大来源数、超时等配置。它说明证据卡不能只是原文第一句，也不能在不知道章节问题时完成最终相关性判断。

对本项目的影响：

- Evidence Card 保存摘要、位置和轻量关键词；最终选择发生在章节问题已知之后。
- 提纲只接受已经导入且可定位的 Evidence ID；模型返回的未知 ID 被丢弃。
- 审计同时记录引用证据数和引用来源文档数，避免“很多引文其实都来自同一处”的假覆盖。

来源：[PaperQA2 官方仓库与算法说明](https://github.com/Future-House/paper-qa)

### 工作流和 evaluator–optimizer

Anthropic 区分预定义流程与自主 Agent，并把 evaluator–optimizer 作为适合有明确评价标准任务的模式。课程论文有任务书、体裁合同、篇幅和证据约束，适合确定性工作流加一次有边界的评估—修订，而不是默认引入复杂多 Agent 协调。

对本项目的影响：

- 确定性检查掌管假证据、缺节、无依据数字等事实边界。
- 独立模型只评价任务契合、覆盖、推理、体裁动作、连贯和引用使用，不能新增阻断级“事实”。
- 修订反馈按章节路由，只修改有对应问题的章节，并在修订后重新审计。
- 供应商调用对超时、网络故障、429 和 5xx 做有限重试，对非法 JSON 重新请求。

来源：[Anthropic, Building effective agents](https://www.anthropic.com/engineering/building-effective-agents)、[Demystifying evals for AI agents](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents)

## 2. 写作程序与写作研究

### AcaWriter：按语境提供修辞动作反馈

AcaWriter 是开源学术写作形成性反馈工具，核心不是通用“文风分”，而是识别修辞动作，并允许针对具体写作语境定制反馈。这支持把体裁要求表达为每节必须完成的交际功能。

对本项目的影响：四类 Genre Profile 为每个章节提供显式 `rhetorical_moves`；案例 Skill 可以补充课程惯例，但不能覆盖任务书。

来源：[AcaWriter, Journal of Writing Research](https://www.jowr.org/jowr/article/view/578)

### Papers-to-Posts：可检查的 Plan–Draft–Revise

Papers-to-Posts 使用带可调整要点的提纲、分节起草和修订。两项用户研究中，这种工作流相较“整篇初稿 + 自由提示”提高了用户对文本的编辑能力和满意度。任务与课程论文并不相同，所以本项目只采用其可检查的阶段结构，不移植其效果数字。

对本项目的影响：提纲中的 `claims` 是生成前可审计的内容计划；起草提示同时包含全局章节合同和前文连续性记录；审计结果驱动定向修订。

来源：[Radensky et al., Papers-to-Posts](https://arxiv.org/abs/2406.10370)

### 自动写作反馈：有平均收益，但不能替代任务级验收

一项纳入 20 个研究、2,828 名学习者的多层元分析报告自动反馈对写作表现的平均效应为 `g=0.55`，同时存在显著异质性，预测区间也包含负值。因此，“加一个模型自评”不是质量保证；反馈必须与任务、体裁和可验证事实结合，并通过本项目自己的任务集验证。

来源：[Fleckenstein et al., Automated feedback and writing](https://pmc.ncbi.nlm.nih.gov/articles/PMC10351274/)

### 长文综合的评价维度

OpenScholar 的 ScholarQABench 将长文综合拆为正确性、引用准确性、覆盖、连贯、组织和写作质量等维度，并显示检索、重排、自反馈和验证都有价值。课程论文还需增加任务书遵循、体裁动作、篇幅完成和案例防复制。

来源：[OpenScholar / ScholarQABench, Nature](https://www.nature.com/articles/s41586-025-10072-4)

## 3. 一次生成成功的操作性定义

“成功率高”必须可测量。一次运行只有同时满足以下条件，`audit.json` 的 `one_shot_success` 才为 `true`：

1. 没有 blocker 或 important 级问题。
2. 任务要求的章节全部生成。
3. 正文达到目标篇幅的 80%–125%，且不存在明显欠展开章节。
4. 没有未解决占位符、无证据数字、非法 Evidence ID 或过高案例复用。
5. 有规划证据时，草稿实际使用有效证据。
6. 使用真实模型评估时，任务契合、覆盖、推理、体裁动作、连贯和引用使用六项均不低于 70/100。

这个门禁是工程验收信号，不是成绩、学术正确性或学校审核承诺。离线 deterministic 模型只能验证流程和失败门禁，不能证明真实文稿质量；模型版本、案例质量和资料充分性必须在重复试验中单独记录。

## 4. 写作软件互操作路线

正式参考文献管理不应自行发明私有格式。Zotero API 支持 CSL JSON、BibTeX、BibLaTeX 和 RIS，桌面端还提供本地 API；Pandoc 可用 bibliography、CSL 和 citeproc 生成引用与书目。后续版本应优先实现 CSL JSON 台账与 Zotero 本地只读导入，再连接 GB/T 7714 样式，而不是让模型自由生成参考文献字符串。

来源：[Zotero Web API](https://www.zotero.org/support/dev/web_api/v3/basics)、[Pandoc User’s Guide](https://pandoc.org/MANUAL.html)

