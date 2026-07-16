# 学术写作依据与工程结论

更新日期：2026-07-16

本文只记录首版架构需要的写作依据，不试图成为完整的写作教材。

## 1. 写作是递归的认知过程

Flower 与 Hayes 的写作过程模型把写作描述为目标导向的问题解决活动。规划、把想法转化为文本、审阅和修订并非严格的一次性线性步骤，而会在写作过程中反复切换。作者还会受到任务环境、长期记忆和已有文本的共同影响。

工程结论：Agent 不能采用“一次 Prompt 直接生成全文”的主流程。v0.1 保存任务、计划和草稿等阶段产物，并在真实模型路径执行一次有边界修订和再审计；章节/段落级交互式回退与多轮重规划属于后续增强。

参考：

- [Flower & Hayes (1981), A Cognitive Process Theory of Writing](https://publicationsncte.org/content/journals/10.58680/ccc198115885)

## 2. Genre-based pedagogy 与修辞动作

体裁不只是标题和排版模板，而是特定社群为实现交际目的而形成的可辨识结构与语言选择。Genre-based pedagogy 强调分析目标语境中的真实文本，明确文本结构和语言资源，再通过支架逐步完成写作。Swales 的 CARS 模型则展示了研究引言常见的修辞动作：建立研究领域、建立研究空间、占据该空间。

不同学科和任务中的修辞动作存在变化，因此 CARS 不能被机械应用到所有论文。通识论文、综述、调研报告和本科论文需要各自的 Genre Profile，案例 Skill 用于学习目标课程的局部惯例。

工程结论：案例分析应提取“这一部分要完成什么交际目的”，而不只是词频、句长或标题名称；内置规则是可覆盖的后备知识，不是强制统一模板。v0.2 将这些目的保存为每节显式修辞动作，并作为规划、起草和质量评价的共同合同。

参考：

- [Hyland (2007), Genre pedagogy: Language, literacy and L2 writing instruction](https://repository.hku.hk/handle/10722/130161)
- [UMass Amherst Writing Center：Swales CARS 模型](https://www.umass.edu/writing-center/resources/creating-research-space)
- [Samraj (2002), Introductions in research articles: variations across disciplines](https://www.sciencedirect.com/science/article/pii/S0889490600000235)

## 3. Toulmin 论证模型

Toulmin 的实践论证框架区分 Claim、Ground/Data、Warrant、Backing、Qualifier 与 Rebuttal。对本项目最重要的是：列出证据并不自动构成论证，写作者必须说明从证据到主张的推理依据，并控制主张强度、处理适用条件和可能的反驳。

工程结论：内部论证对象至少包括 `Claim → Evidence/Ground → Warrant`，并可附 `Backing`、`Qualifier`、`Counterargument/Rebuttal`。v0.2 在每节提纲中保存 `claims`、`evidence_ids`、`counterargument` 和 `evidence_gap`，起草提示要求把证据与论证担保分开表达。

参考：

- [Toulmin, The Uses of Argument, Cambridge University Press](https://www.cambridge.org/core/books/uses-of-argument/26CF801BC12004587B66778297D5567C)

## 4. 从优秀案例学习的理论边界

高等教育中的范例学习研究表明，优秀案例可以帮助学习者理解质量标准、任务结构和评价期望，但“看过案例”并不稳定地保证成绩提高。范例与评价标准的对照、多个案例之间的比较、对质量判断的解释和反馈过程都很重要。

这意味着 Writing Skill 不能简单模仿一篇范文，也不能把高频特征直接当成优质规则。系统需要比较多个案例，把观察结果转化为显式标准，标出支持证据与反例，并让自动验证或用户反馈修正规则。

工程结论：完整 Skill 生命周期应采用“多案例分解 → 跨案例比较 → 质量规则假设 → 与任务/Rubric 对齐 → 留出验证 → 版本化”的流程。v0.1 已实现最低三案例、结构一致性、规则证据和置信门禁；正式留出验证、跨学科基准和版本比较仍在路线图中，不能用当前置信分数替代这些验证。

参考：

- [Sadler (1989), Formative assessment and the design of instructional systems](https://doi.org/10.1007/BF00117714)
- [Carless & Chan (2017), Managing Dialogic Use of Exemplars](https://eric.ed.gov/?id=EJ1145808)
- [Bouwer et al. (2018), Applying Criteria to Examples or Learning by Comparison](https://www.frontiersin.org/journals/education/articles/10.3389/feduc.2018.00086/full)
- [Students' use of exemplars to support academic writing in higher education: An integrative review](https://www.sciencedirect.com/science/article/pii/S0260691718301102)

## 5. 分析性问题、中心论点与论证

课程论文的核心不应是“把相关知识写出来”，而是围绕一个范围适当、答案不显然的问题提出中心论点。中心论点应当可争辩、可由现有证据支持，并在正文较早出现。正文中的每个主要判断都应当能追溯到证据，且需要解释证据为何支持该判断，而非简单堆放引文。

工程结论：分析性问题和 Thesis 位于 Toulmin 式局部论证图之上；生成段落前先验证全局问题、中心论点和局部支撑链，全文完成后再反向检查每个中心结论。

参考：

- [Harvard College Writing Center：Asking Analytical Questions](https://writingcenter.fas.harvard.edu/asking-analytical-questions)
- [Harvard College Writing Center：Thesis](https://writingcenter.fas.harvard.edu/thesis)
- [Harvard College Writing Center：Counterargument](https://writingcenter.fas.harvard.edu/counterargument)

## 6. 文献综述是综合，不是摘要串联

文献综述要围绕研究问题组织多个来源，呈现主题、方法、立场、共识、分歧和空白。逐篇介绍“作者 A 说……作者 B 说……”通常不构成有效综合。

工程结论：先为每个来源生成证据卡片，再按主题、方法和观点关系组织章节，而不是按来源顺序串联。v0.1 已生成带定位的 Evidence Card，并通过文献综述 Genre 规则要求跨来源综合；显式、可查看的“来源 × 主题/方法/观点”矩阵仍是后续能力。

参考：

- [George Mason University Writing Center：Writing a Literature Review](https://writingcenter.gmu.edu/writing-resources/research-based-writing/writing-a-literature-review)
- [University of Adelaide Writing Centre：Writing a Literature Review](https://www.adelaide.edu.au/writingcentre/sites/default/files/docs/learningguide-writingliteraturereview.pdf)

## 7. 调研报告结构与真实性

调研报告通常需要明确目的、受众和格式，并区分方法、结果和讨论。方法描述“做了什么”，结果描述“发现了什么”，讨论解释结果意味着什么。建议必须能从结果与讨论中推出。

工程结论：方法和结果章节必须绑定用户提供的真实材料；缺少数据时不进入“已完成调研报告”状态，只允许输出调研方案、问卷/访谈提纲或带未完成标记的框架。

参考：

- [University of Adelaide Writing Centre：Writing a Research Report](https://www.adelaide.edu.au/writingcentre/sites/default/files/docs/learningguide-writingaresearchreport.pdf)

## 8. 引用、改写与来源追踪

引用、改写、摘要和作者自己的分析承担不同功能。无论直接引用还是改写，只要使用他人的独特观点、文字、数据或视觉材料，都需要保留来源。模型生成的参考文献不能被视为已核验来源。

工程结论：采用“证据先于正文”的生成策略。v0.1 只有用户导入的来源或真实数据会生成 Evidence ID，并明确区分“可定位到用户文件”与“书目已经外部核验”；工具当前不提供模型候选来源发现或外部元数据核验。

参考：

- [George Mason University Writing Center：Quotation, Paraphrase, Summary, and Analysis](https://writingcenter.gmu.edu/writing-resources/research-based-writing/quotation-paraphrase-summary-and-analysis)
- [Purdue OWL：Plagiarism Overview](https://owl.purdue.edu/owl/avoiding_plagiarism/documents/plagiarism_one_pager.pdf)
- [Crossref REST API 官方文档](https://www.crossref.org/documentation/retrieve-metadata/rest-api/)

## 9. 中文参考文献标准

截至 2026-07-16，GB/T 7714-2025 已于 2026-07-01 实施，GB/T 7714-2015 已废止。不过，学校模板和课程要求可能仍指定 2015 版或自行改写的格式，因此工具必须支持显式选择，并坚持“用户/学校模板优先”。

工程结论：引用样式不能写死；首版至少规划 `gb-t-7714-2025` 和兼容性的 `gb-t-7714-2015`，实际渲染前要求用户确认学校规则。

参考：

- [全国标准信息公共服务平台：GB/T 7714-2025](https://openstd.samr.gov.cn/bzgk/std/newGbInfo?hcno=C6CE52E55AC09B9C79A20AEA77CEDD14)
- [国家标准全文公开系统：GB/T 7714 状态列表](https://openstd.samr.gov.cn/bzgk/std/std_list?p.p1=0&p.p2=GB%2FT7714&p.p90=circulation_date&p.p91=desc)

## 10. 学术诚信与人机责任边界

教育部规章将剽窃、伪造数据或文献以及由他人代写论文等列为学术不端行为。生成式 AI 在教育中的使用还涉及人类主体性、隐私、透明度和机构规则。

工程结论：产品不提供“规避检测”功能。v0.1 保留工作流历史、来源 ID、模型标签、Skill 版本和未核验声明，并在 README 提醒用户遵守课程或学校的 AI 使用及披露政策；更细粒度的人工审批节点属于后续交互能力。

参考：

- [教育部：《高等学校预防与处理学术不端行为办法》](https://www.moe.gov.cn/jyb_xxgk/xxgk/zhengce/guizhang/202112/t20211206_585094.html)
- [UNESCO：Guidance for Generative AI in Education and Research](https://www.unesco.org/en/articles/guidance-generative-ai-education-and-research?hub=66973)
