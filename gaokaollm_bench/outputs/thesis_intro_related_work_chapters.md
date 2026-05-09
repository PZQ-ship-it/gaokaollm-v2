# 毕业论文绪论与相关技术章节正文草稿

本文档是毕业设计论文第 1 章“绪论”和第 2 章“相关技术”的正文母版，用于承接已经完成并通过审计的 Agent+Benchmark 双实验主线。本文不新增实验结论，所有结果均引用现有可审计产物：

- `gaokaollm_bench/outputs/thesis_agent_benchmark_contribution.md`
- `gaokaollm_bench/outputs/thesis_method_experiment_chapters.md`
- `gaokaollm_bench/outputs/thesis_v1_v2_integration_plan.md`
- `gaokaollm_bench/outputs/thesis_artifact_audit.md`
- `gaokaollm_bench/outputs/benchmark_methodology.md`
- `gaokaollm_bench/outputs/major_tree_methodology.md`
- `gaokaollm_bench/放宽与跃迁.md`

文中参考文献位置先以“可替换引用占位”形式保留，后续迁入正式 LaTeX/BibTeX 时再替换为具体文献条目。

## 第 1 章 绪论

### 1.1 研究背景

高考志愿填报是典型的高风险决策任务。考生需要在有限时间内同时考虑分数、位次、选科、批次线、院校层次、专业方向、地域、学费、风险偏好和未来发展等因素。与一般信息检索任务不同，高考志愿咨询中的错误建议会直接影响考生的录取机会和学习路径，因此系统不仅要“能回答”，还必须“答得可核验、可追溯、可解释”。

近年来，大语言模型在自然语言理解、多轮对话和知识整合方面表现出较强能力，为高考志愿咨询系统提供了新的技术可能。基于检索增强生成的问答系统可以把招生章程、专业介绍、往年分数、院校资料等外部知识接入大模型，从而缓解模型纯参数知识过时或不完整的问题。Agent 工作流则进一步允许系统在多轮咨询中拆解任务、维护状态、调用数据库查询和组织解释性回复。

然而，高考志愿咨询并不是一个单轮知识问答问题。真实用户常常会以强硬红线开场，例如“只读临床医学”“专业不对的学校再好也不考虑”“只考虑本省”“只求稳妥，不想冲”。这些表达既可能是真实不可妥协条件，也可能是由于信息不足形成的初始锚定。如果系统只是顺从显性红线，可能会错过更优且可达的志愿集合；如果系统脱离真实数据进行劝说，又会产生虚假学校、错误分数和不可达推荐等风险。

因此，本文关注的核心问题不是“如何让大模型生成一段看似合理的咨询回复”，而是“如何在真实招生数据约束下，评测并构建一个能够进行多轮偏好妥协的高考志愿 Agent”。

### 1.2 问题定义

本文将高考志愿 Agent 的任务定义为：在真实 PostgreSQL 招生数据约束下，基于用户显式话语抽取出的分数、省份、专业、选科、预算和风险偏好等条件，发现部分约束放宽后的可达志愿集合，并通过多轮对话向用户展示可核验的反事实证据，从而触发用户接受更优或更完整的 Pareto 妥协方案。

这个定义包含三个关键变化。

第一，评测对象从静态问答正确率转向多轮偏好启发过程。系统不仅要给出事实正确的学校和专业，还要证明它能否在对话中帮助用户理解放宽部分初始红线后的收益。

第二，推荐依据从泛化语言建议转向真实数据库证据。候选学校、专业、最低分、最低位次、分差、位次差和风险层级等信息必须来自结构化招生数据，而不是模型凭空生成。

第三，用户偏好从完全显式转向“冰山画像”。用户说出口的是显性红线，水面下则是只有在看到充分证据后才可能接受的隐性妥协条件。Benchmark 持有隐藏画像作为评测 ground truth，但被测 Agent 不能读取 `implicit_flexibilities` 或 `volunteer_set`，只能通过用户话语和数据库查询结果进行推理和谈判。

### 1.3 研究挑战

高考志愿偏好妥协 Agent 面临以下挑战。

| 挑战 | 具体表现 | 本文处理方式 |
|---|---|---|
| 显性红线与隐性妥协并存 | 用户可能先说“只求稳”“只读某专业”，但看到证据后愿意妥协 | 构建冰山画像 benchmark，显式区分说出口的红线和隐藏可接受条件 |
| 事实正确性要求高 | 学校、专业、最低分、位次等错误会直接破坏可信度 | 使用 PostgreSQL 招生快照和 deterministic factual judge 约束幻觉 |
| 偏好启发难以评测 | 传统问答指标难以衡量 Agent 是否促成用户接受更好方案 | 使用多轮沙盒、transcript 和 process judge 评价启发成功 |
| 约束放宽需要可解释 | 专业、地域、风险偏好的放宽路径不能随意扩展 | 使用专业树层级放宽和 `score_margin` / `rank_gap` 风险分层 |
| 结果需要可审计 | 论文结论需要落到逐例证据，而不能只有聚合指标 | 保存 transcripts、reports、evidence 附录和 SHA256 审计报告 |

这些挑战决定了本文采用“Agent + Benchmark”的双贡献结构：Benchmark 负责把偏好妥协任务变成可生成、可运行、可评价的实验框架；Agent 负责在该框架下用真实证据进行 Pareto 谈判。

### 1.4 本文贡献

本文贡献分为 Benchmark 贡献、Agent 贡献和工程原型支撑三部分。

第一，本文提出面向高考志愿偏好妥协的冰山画像 Benchmark。该 Benchmark 从真实 PostgreSQL 招生数据库出发，通过专业、地域、风险偏好等约束放宽发现真实 DB gap，再逆向生成包含 `explicit_red_lines`、`implicit_flexibilities` 和隐藏志愿集合的 persona。评测过程使用多轮沙盒、用户模拟器、transcript 持久化、事实裁判和过程裁判，使 Agent 的偏好启发能力可以被逐例追踪和聚合评价。

第二，本文设计证据驱动的 Pareto 谈判 Agent。业务 Agent 使用 LangGraph 组织为 `gatekeeper -> radar -> negotiator` 三段结构：`gatekeeper` 抽取显性约束并查询 baseline，`radar` 调用确定性 SQL 探针寻找放宽机会，`negotiator` 将真实候选组织为面向用户的证据化回复。当前 Agent 核心能力包括 `major_geo_relax` 专业+地域联合放宽，以及 `risk_band_relax` 风险偏好放宽。

第三，本文基于第一版 `gaokaollmmodel` Agentic RAG 原型积累工程基础。v1 已经实现状态机工作流、意图识别、Redis 用户画像、混合检索、重排、`1:3:9` 冲稳保推荐、神经-符号一致性校验和流式响应等能力。最终论文中，v1 不作为最终主贡献，而是作为工程原型与问题来源；v2 是最终主贡献，即研究问题收敛后的 Agent+Benchmark 闭环。

### 1.5 实验概述

本文第一版主实验包含两组 Agent-vs-Baseline 离线评测，对照对象为 `app_pareto` 与 `hard_constraint`。其中，`app_pareto` 表示接入证据驱动 Pareto 谈判能力的业务 Agent，`hard_constraint` 只报告当前显性硬约束下的可达志愿，不主动进行专业、地域或风险偏好谈判。

| 实验 | Target | Cases | Success | Elicitation Success | Mean Pareto Gain | Mean Hallucination | Avg Turns |
|---|---|---:|---:|---:|---:|---:|---:|
| `major_geo_v1` | `app_pareto` | 10 | 9 | 0.900 | 0.900 | 0.000 | 5.20 |
| `major_geo_v1` | `hard_constraint` | 10 | 0 | 0.000 | 0.000 | 0.000 | 7.00 |
| `risk_band_v1` | `app_pareto` | 10 | 10 | 1.000 | 3.000 | 0.000 | 5.00 |
| `risk_band_v1` | `hard_constraint` | 10 | 0 | 0.000 | 0.000 | 0.000 | 15.00 |

也可以将核心结果简写为：

- `major_geo_v1`: `app_pareto 0.900 / 0.900 / 0.000 / 5.20` vs `hard_constraint 0.000 / 0.000 / 0.000 / 7.00`
- `risk_band_v1`: `app_pareto 1.000 / 3.000 / 0.000 / 5.00` vs `hard_constraint 0.000 / 0.000 / 0.000 / 15.00`

上述四个指标依次为 `elicitation_success_rate / mean_pareto_gain / mean_hallucination_rate / avg_turns`。所有指标均来自 `thesis_artifact_audit.md`，审计结果为 `Overall: PASS`。

需要注意的是，`major_geo_v1` 并非 100% 成功。唯一失败样本为 `real-db-set-浙江-569-009`，该样本中 persona 隐藏目标要求退到更远的 `any_major` 集合，而 Agent 实际停留在较近的医学相关大类兜底候选上，因此 deterministic judge 未判定成功。论文中应保留这一失败样本，以避免把 0.900 误写成完全成功。

### 1.6 论文结构

本文后续章节组织如下。

第 2 章介绍相关技术，包括 RAG、Agent、LangGraph、多轮用户模拟、LLM-as-a-Judge、专业树层级放宽、风险分层和 Pareto 偏好妥协等内容。

第 3 章介绍第一版 `gaokaollmmodel` Agentic RAG 原型系统，说明其状态机编排、混合检索、用户画像、`1:3:9` 冲稳保推荐和一致性校验能力，并分析为什么仅有工程原型不足以证明偏好妥协效果。

第 4 章介绍高考志愿偏好妥协 Benchmark，包括冰山画像、真实 DB gap、专业树层级放宽、风险偏好画像、多轮沙盒和事实/过程联合评价。

第 5 章介绍证据驱动 Pareto 谈判 Agent，包括 `gatekeeper -> radar -> negotiator` 架构、`major_geo_relax`、`risk_band_relax` 和 `hard_constraint` baseline。

第 6 章给出实验结果、逐例证据与可复现审计，重点分析 `major_geo_v1`、`risk_band_v1` 两组主实验，以及失败样本 `real-db-set-浙江-569-009`。

第 7 章总结全文，并讨论样本规模、真实用户实验、概率化风险建模、城市/学费/就业/学科实力等更多动态放宽类别。

## 第 2 章 相关技术

### 2.1 检索增强生成与高考志愿问答系统

检索增强生成（Retrieval-Augmented Generation, RAG）通过在生成前引入外部知识检索，缓解大语言模型参数知识过时、事实细节不完整和领域知识不足等问题（可替换引用占位：RAG）。在高考志愿咨询场景中，RAG 可以接入招生章程、专业介绍、学校资料、往年录取分数和就业信息，使模型回答不完全依赖训练语料中的静态记忆。

传统 RAG 系统通常包含查询理解、检索、重排和生成等步骤。对于高考志愿任务，仅依赖非结构化文本检索是不够的，因为考生的核心问题往往需要精确过滤：分数是否达线、选科是否满足要求、预算是否可接受、专业是否匹配、学校是否在目标地域内。因此，高考志愿 RAG 系统需要将关系型数据库过滤与向量检索结合起来：结构化表负责分数、位次、批次线、招生计划等硬约束，向量检索负责章程、专业介绍和解释性文本。

本文的第一版系统 `gaokaollmmodel` 即可视为一个 Agentic RAG 原型。它通过状态机工作流、意图识别、Redis 用户画像、混合检索、BGE-M3 embedding、BCEmbedding reranker 和神经-符号一致性校验，使系统能够完成基础问答和推荐任务。该原型证明了大模型可以被工程化接入高考志愿咨询，但也暴露出一个问题：系统能回答问题，并不等于系统能改善用户决策。因此，v2 进一步把研究重点从“可用问答”转向“可评测的偏好妥协”。

### 2.2 Agent 与 LangGraph 工作流

Agent 技术强调让大语言模型不只是直接生成文本，而是能够维护状态、规划步骤、调用工具并根据中间结果继续决策（可替换引用占位：LLM Agent）。在高考志愿咨询任务中，Agent 的价值主要体现在三个方面：第一，从自然语言中抽取用户约束；第二，调用招生数据库进行精确查询；第三，将查询结果组织为符合用户偏好的解释性建议。

LangGraph 提供了图式状态机编排能力，适合表达多步骤、多状态和可回溯的 Agent 工作流（可替换引用占位：LangGraph）。相比单次 prompt 调用，图式工作流可以明确区分不同节点的职责，降低复杂任务中状态混乱和责任不清的问题。

本文 v2 业务 Agent 使用如下工作流：

```text
gatekeeper -> radar -> negotiator
```

其中，`gatekeeper` 面向显性约束抽取和 baseline 查询；`radar` 面向 Pareto 机会探测；`negotiator` 面向证据化对话回复。这样的划分使 Agent 的核心行为可以被 benchmark 审计：系统是否正确抽取用户约束，是否在数据库中发现了可谈判候选，是否把候选以事实证据而非泛化说服话术的形式呈现给用户。

### 2.3 多轮用户模拟与 Benchmark 评测

传统问答 benchmark 通常以题目、答案和静态评分为中心，适合评价知识准确率或推理正确率。但高考志愿咨询的关键并不只是某个答案是否正确，而是系统能否在多轮对话中引导用户重新理解自己的偏好。用户可能先坚持某个专业或风险偏好，只有在看到真实可达候选后才接受妥协。因此，本文使用多轮沙盒评测而非单轮问答评测。

本文 benchmark 的核心是冰山画像。每个 persona 都包含用户会说出口的 `explicit_red_lines`，以及只有在看到充分证据后才会接受的 `implicit_flexibilities`。被测 Agent 只能看到模拟用户在对话中说出的内容，Agent 不读取 `implicit_flexibilities` 或 `volunteer_set` 等隐藏字段。模拟用户根据 persona 和对话历史生成下一轮话语，沙盒负责记录所有 turn、内部状态和停止条件，最终输出 transcript、逐例 report 和 summary。

这种设计使偏好妥协成为可评价对象。若 Agent 只重复用户显性红线，即使事实正确，也无法触发隐藏妥协；若 Agent 编造不可达候选，则会被事实裁判惩罚；只有在事实正确且能命中隐藏妥协条件时，才会获得较高的 `elicitation_success` 和 `pareto_gain`。

### 2.4 LLM-as-a-Judge 与事实/过程联合评价

LLM-as-a-Judge 常用于评价开放式文本质量、多轮对话质量和主观偏好匹配程度（可替换引用占位：LLM-as-a-Judge）。但在高考志愿场景中，单纯依赖 LLM judge 存在风险：模型可能忽略分数、位次或学校专业是否真实存在，也可能被流畅的解释性语言误导。

因此，本文采用事实/过程联合评价。事实评价由 deterministic factual judge 完成，重点检查学校、专业、最低分、最低位次等证据是否与数据库和 transcript 内部状态一致，并计算 hallucination rate。过程评价则关注 Agent 是否成功触发用户隐藏妥协，包括是否提出了 `major_geo_relax` 或 `risk_band_relax` 候选，是否命中隐藏志愿集合，是否把单一保守方案扩展为冲稳保组合。

这种联合评价的意义在于区分两类系统：一类系统事实正确但不谈判，例如 `hard_constraint` baseline；另一类系统在保持事实正确的同时，通过真实证据触发用户妥协，例如 `app_pareto`。论文主张的提升不是生成更长或更热情的建议，而是在 0.000 hallucination rate 前提下提升多轮偏好启发效果。

### 2.5 专业树层级放宽

专业偏好是高考志愿咨询中最常见、也最难处理的约束之一。用户可能明确说“只读临床医学”，但在真实决策中，看到学校层次、就业方向或可达性差异后，可能会接受同类医学专业、相关大类专业，甚至在某些情况下接受更远的替代专业。专业放宽不能完全依赖字符串相似度，也不能无解释地跳到任意专业，因此需要层级化专业结构支撑。

本文的专业树用于将 observed major names 归入可解释的专业层级。放宽过程从近到远逐步展开：同叶子簇内的名称变体、同父近邻、上层大类、probe 邻近大类，必要时退化到 `any_major`。这种 staged relaxation 使 `major_geo_relax` 不只是“去掉专业限制”，而是能够呈现从近邻专业到更远替代方案的可解释路径。

专业树和 probe 在本文中属于 Benchmark 基础设施和 Agent 探测支撑，不作为最终论文的主贡献中心。它们的作用是让专业放宽具有可复现、可审计和可解释的结构基础。

### 2.6 风险分层与冲稳保组合

高考志愿填报通常会使用“冲、稳、保”等风险层级组织志愿组合。v1 `gaokaollmmodel` 中已经实现过工程化的 `1:3:9` 冲稳保推荐策略，用于生成梯度化志愿建议。这一策略贴近真实填报实践，但在 v1 中主要作为推荐逻辑存在，并未被放入多轮偏好妥协 benchmark 中严格评测。

v2 的 `risk_band_relax` 将这一能力升级为可评测的风险偏好放宽闭环。对于显性表达“只求稳妥、不接受冲刺”的用户，Agent 不改变省份、专业、选科和预算等硬约束，只放宽风险偏好，将单一保守方案扩展为 `chong/wen/bao` 组合。系统优先使用 `rank_gap = min_rank - student_rank` 判定风险层级，位次数据不足时退化到 `score_margin = score - min_score`。每个候选保留学校、城市、专业、最低分、最低位次、分差、位次差和风险标签。

这种设计使风险偏好不再只是推荐排序策略，而成为可被 transcript、逐例 evidence 和 aggregate summary 验证的 Agent 贡献。`risk_band_v1` 结果表明，`app_pareto` 能够将风险偏好放宽任务的启发成功率从 baseline 的 0.000 提升到 1.000，并保持 0.000 的幻觉率。

### 2.7 Pareto 偏好妥协

Pareto 改进通常指在不损害某些条件的前提下，使至少一个目标得到改善。迁移到高考志愿咨询中，Pareto 偏好妥协可以理解为：在保留用户关键事实约束的前提下，放宽部分可能由信息不足形成的初始偏好，从而获得更高层次、更完整或风险结构更合理的志愿集合。

本文中的 `major_geo_relax` 和 `risk_band_relax` 分别对应两类 Pareto 妥协。`major_geo_relax` 保留分数、选科和预算等硬约束，同时放宽专业与地域，寻找更高质量的可达候选；`risk_band_relax` 保留专业、地域、选科和预算等硬约束，只将“只求稳”的风险偏好扩展为冲稳保组合。

需要强调的是，本文不把所有用户偏好都视为可放宽对象。选科要求、真实分数、预算等事实约束仍被视为硬约束；Agent 的任务不是强行说服用户改变真实偏好，而是在可核验数据中呈现放宽某些初始红线后的收益，由用户模拟器或真实用户根据证据决定是否接受。这也是本文使用“证据驱动 Pareto 谈判”作为 Agent 贡献表述的原因。

### 2.8 本章小结

本章从 RAG、Agent、LangGraph、多轮 benchmark、LLM-as-a-Judge、专业树、风险分层和 Pareto 偏好妥协等角度，梳理了本文方法所依赖的关键技术。总体来看，v1 `gaokaollmmodel` 证明了高考志愿咨询可以被构建为 Agentic RAG 工程系统；v2 则进一步将研究问题收敛到可评测的偏好妥协 Agent，通过 Benchmark 贡献和 Agent 贡献形成最终论文主线。

后续章节将先介绍 v1 原型系统与问题诊断，再详细展开 v2 的 Benchmark 构建、Agent 设计、双实验结果和可复现审计。
