# 毕业论文绪论与相关技术章节正文母版

本文档是毕业设计论文第 1 章“绪论”和第 2 章“相关技术”的正文母版，用于把当前项目统一到“数据 + Agent + Benchmark”的三贡献口径。文档只整理已有项目产物，不新增实验结论、不更新审计脚本、不重跑 benchmark。

可引用的现有产物包括：

- `gaokaollm_bench/outputs/thesis_agent_benchmark_contribution.md`
- `gaokaollm_bench/outputs/thesis_method_experiment_chapters.md`
- `gaokaollm_bench/outputs/thesis_v1_v2_integration_plan.md`
- `gaokaollm_bench/outputs/thesis_data_agent_benchmark_extension_evidence.md`
- `gaokaollm_bench/outputs/agent_benchmark_major_geo_v1_evidence.md`
- `gaokaollm_bench/outputs/agent_benchmark_risk_band_v1_evidence.md`
- `gaokaollm_bench/outputs/benchmark_methodology.md`
- `gaokaollm_bench/outputs/major_tree_methodology.md`
- `gaokaollm_bench/outputs/dynamic_decision_considerations_roadmap.md`
- `gaokaollm_bench/放宽与跃迁.md`

文中参考文献位置先以“可替换引用占位”保留，迁入正式 LaTeX/BibTeX 时再替换为具体文献条目。

## 第 1 章 绪论

### 1.1 研究背景

高考志愿填报是典型的高风险决策任务。考生需要在有限时间内同时考虑分数、位次、选科、批次线、院校层次、专业方向、地域、学费、风险偏好、专业质量和就业结果等因素。与一般信息检索或开放问答不同，志愿咨询中的错误建议可能直接影响考生的录取机会和未来学习路径。因此，一个面向高考志愿的智能系统不能只追求“回答流畅”，还必须做到事实可核验、证据可追溯、推荐边界可解释。

近年来，大语言模型在自然语言理解、多轮对话和知识整合方面表现出较强能力，为高考志愿咨询提供了新的技术可能。基于检索增强生成的系统可以把招生章程、专业介绍、往年分数和院校资料接入模型，从而缓解模型参数知识过时或不完整的问题；Agent 工作流则进一步允许系统在多轮咨询中维护状态、拆解任务、调用数据库并组织解释性回复。

但是，高考志愿咨询并不是单轮知识问答。真实用户常以强硬红线开场，例如“只考虑本省”“只读这个专业”“只求稳，不想冲”“学费别太贵”“希望就业稳定”。这些表达既可能是真实不可妥协的约束，也可能是由信息不足形成的初始偏好锁定。如果系统只迎合显性红线，就可能错过更优且可达的志愿集合；如果系统脱离真实招生数据进行劝说，又会产生虚假学校、错误分数和不可达推荐等风险。

因此，本文关注的核心问题不是“如何让大模型生成一段看似合理的志愿建议”，而是“如何基于真实招生数据，构建并评测一个能够进行多轮偏好妥协的高考志愿 Agent”。这要求系统既有可核验的数据证据，又有能够组织证据进行 Pareto 谈判的 Agent，也有能够评估隐性妥协是否被触发的 benchmark。

### 1.2 问题定义

本文将高考志愿 Agent 的任务定义为：在真实 PostgreSQL 招生数据约束下，基于用户显式话语抽取出的分数、省份、专业、选科、预算、风险偏好、专业质量偏好和就业导向等条件，发现部分偏好放宽后的可达志愿集合，并通过多轮对话展示可核验的反事实证据，从而触发用户接受更优或更完整的 Pareto 妥协方案。

这个定义包含三个关键变化。

第一，评测对象从静态问答正确率转向多轮偏好启发过程。系统不仅要给出事实正确的学校和专业，还要证明它能否在对话中帮助用户理解放宽部分初始红线后的收益。

第二，推荐依据从泛化语言建议转向真实数据库证据。候选学校、专业、最低分、最低位次、分差、位次差、风险层级、学费、专业质量和就业结果等信息必须来自结构化数据或标准化证据层，而不是模型凭空生成。

第三，用户偏好从完全显式转向“冰山画像”。用户说出口的是显性红线，水面下则是只有在看到充分证据后才可能接受的隐性妥协条件。Benchmark 持有隐藏画像作为 evaluator ground truth，但被测 Agent 不能读取 `implicit_flexibilities` 或 `volunteer_set`，只能通过用户显式话语和 PostgreSQL 查询结果进行推理与谈判。

### 1.3 研究挑战

高考志愿偏好妥协 Agent 面临以下挑战。

| 挑战 | 具体表现 | 本文处理方式 |
|---|---|---|
| 数据证据异构 | 分数、位次、学费、专业质量、就业结果分散在不同表和外部文件中 | 构建 PostgreSQL 招生快照、专业树、专业质量标准化层和就业结果标准化层 |
| 显性红线与隐性妥协并存 | 用户可能先说“只求稳”“只读某专业”，但看到证据后愿意妥协 | 构建冰山画像 benchmark，区分 `explicit_red_lines` 与 `implicit_flexibilities` |
| 事实正确性要求高 | 学校、专业、最低分、位次、学费和质量证据错误会破坏可信度 | 使用结构化 SQL 查询和 deterministic factual judge 控制幻觉 |
| 偏好启发难以评测 | 传统问答指标难以衡量 Agent 是否促成用户接受更优方案 | 使用多轮沙盒、transcript、process judge 和 `pareto_gain` |
| 放宽路径需要可解释 | 专业、地域、风险、预算、质量、就业等放宽不能任意扩展 | 使用专业树、风险分层、预算窗口、质量评分和就业证据字段 |
| 结果需要可审计 | 论文结论需要落到逐例证据，而不能只有聚合指标 | 保存 transcripts、reports、summary 和 evidence 附录 |

这些挑战决定了本文采用“数据 + Agent + Benchmark”的三贡献结构：数据层负责提供可核验事实证据，Agent 层负责将事实证据组织为 Pareto 谈判，Benchmark 层负责把偏好妥协任务变成可生成、可运行、可评价的实验框架。

### 1.4 本文贡献

本文贡献分为数据贡献、Agent 贡献、Benchmark 贡献和 v1 工程原型支撑四部分。

第一，本文构建了面向高考志愿动态决策的结构化数据证据层。基础数据来自本地 PostgreSQL 招生快照，覆盖录取分数、最低位次、批次线、学校信息、专业信息和招生计划学费等字段。在此基础上，项目进一步构建专业树、`school_major_quality_profiles` 专业质量标准化层、`major_employment_outcome_profiles` 就业结果标准化层，以及 `region_geo_tree_reviewed_v1.json` / `region_urban_tier_tree_reviewed_v1.json` 地域树 reviewed v1，使专业质量、就业排名、行业分布、岗位分布、薪资分布和地域树节点等信息可以作为 Agent 输出和 benchmark 裁判的可核验证据。

第二，本文设计了证据驱动的 Pareto 谈判 Agent。业务 Agent 使用 LangGraph 组织为 `gatekeeper -> radar -> negotiator` 三段结构：`gatekeeper` 抽取显式约束并查询 baseline，`radar` 调用确定性 SQL 探针寻找放宽机会，`negotiator` 将真实候选组织为面向用户的证据化回复。当前 Agent 核心能力包括 `major_geo_relax` 专业+地域联合放宽、`risk_band_relax` 风险偏好放宽，以及扩展能力 `tuition_value_relax`、`major_quality_relax`、`employment_outcome_relax`、`region_tree_relax`。同时，`strength_relax` 作为较粗粒度的学校/学科实力过渡实验，帮助说明数据证据维度可以逐步扩展。

第三，本文提出面向高考志愿偏好妥协的冰山画像 Benchmark。该 Benchmark 从真实 DB gap 出发生成 persona，使用多轮沙盒模拟用户互动，并通过事实/过程联合评价计算 `elicitation_success`、`pareto_gain`、`hallucination_rate` 和 `avg_turns`。对照系统 `hard_constraint` 只报告显性硬约束下可达志愿，不主动谈判；目标系统 `app_pareto` 则尝试在事实约束内提出证据驱动的 Pareto 妥协。

第四，本文保留第一版 `gaokaollmmodel` Agentic RAG 原型作为工程基础和问题来源。v1 已实现状态机工作流、意图识别、Redis 用户画像、混合检索、BGE-M3 embedding、BCEmbedding reranker、`1:3:9` 冲稳保推荐、神经-符号一致性校验和 SSE 流式响应等能力。最终论文中，v1 不作为最终主贡献，而作为工程原型与问题诊断；v2 是研究问题收敛后的数据 + Agent + Benchmark 主贡献。

### 1.5 实验概述

本文第一版主实验为 `major_geo_v1 + risk_band_v1`。其中，`major_geo_v1` 验证专业与地域联合放宽，`risk_band_v1` 验证从“只求稳”到 `chong/wen/bao` 冲稳保组合的风险偏好放宽。五组扩展实验 `school_strength_v1`、`tuition_value_v1`、`major_quality_v1`、`employment_outcome_v1`、`region_tree_v1` 用于证明同一框架可以接入新的数据证据维度，支撑“数据贡献可扩展”的论文论点。扩展实验不替代主实验。

斜杠格式依次为：

```text
elicitation_success_rate / mean_pareto_gain / mean_hallucination_rate / avg_turns
```

| 实验 | 类型 | `app_pareto` | `hard_constraint` | 说明 |
|---|---|---:|---:|---|
| `major_geo_v1` | 主实验 | `0.900 / 0.900 / 0.000 / 5.20` | `0.000 / 0.000 / 0.000 / 7.00` | 专业 + 地域联合放宽，Agent 触发 9/10 个隐性妥协 |
| `risk_band_v1` | 主实验 | `1.000 / 3.000 / 0.000 / 5.00` | `0.000 / 0.000 / 0.000 / 15.00` | 从只求稳扩展到冲稳保组合，Agent 触发 10/10 个隐性妥协 |
| `school_strength_v1` | 扩展实验 | `1.000 / 15.000 / 0.000 / 5.00` | `0.000 / 0.000 / 0.000 / 11.00` | 学校/学科实力证据可接入谈判闭环 |
| `tuition_value_v1` | 扩展实验 | `1.000 / 1.000 / 0.000 / 5.00` | `0.000 / 0.000 / 0.000 / 11.00` | `admission_plans.tuition` 支撑预算性价比放宽 |
| `major_quality_v1` | 扩展实验 | `1.000 / 16.000 / 0.000 / 5.00` | `0.000 / 0.000 / 0.050 / 11.00` | `school_major_quality_profiles` 支撑专业质量证据跃迁 |
| `employment_outcome_v1` | 扩展实验 | `1.000 / 49.000 / 0.000 / 3.00` | `0.000 / 0.000 / 0.000 / 11.00` | `major_employment_outcome_profiles` 支撑就业排名、行业、岗位和薪资证据谈判 |
| `region_tree_v1` | 扩展实验 | `1.000 / 1.000 / 0.000 / 3.00` | `0.000 / 0.000 / 0.000 / 11.00` | reviewed 地域树支撑地理板块和城市层级证据谈判 |

需要注意的是，`major_geo_v1` 并非 100% 成功。唯一失败样本为 `real-db-set-浙江-569-009`，该样本需要 Agent 进一步退到更远的 `any_major` 候选才能命中 hidden volunteer set，而当前 Agent 停留在医学相关近邻阶段，因此 deterministic judge 未判定成功。论文中应保留这个失败样本，避免把 0.900 写成完全成功。

### 1.6 论文结构

本文后续章节组织如下。

第 2 章介绍相关技术，包括 RAG、Agent、LangGraph、多轮用户模拟、LLM-as-a-Judge、数据证据标准化、专业树与地域树层级放宽、风险分层和 Pareto 偏好妥协等内容。

第 3 章介绍第一版 `gaokaollmmodel` Agentic RAG 原型系统，说明其状态机编排、混合检索、用户画像、`1:3:9` 冲稳保推荐和一致性校验能力，并分析为什么仅有工程原型不足以证明偏好妥协效果。

第 4 章介绍 Benchmark 与数据生成方法，包括 PostgreSQL 数据快照、专业树、专业质量与就业结果标准化层、`region_geo_tree_reviewed_v1.json` / `region_urban_tier_tree_reviewed_v1.json` 地域树 reviewed v1、冰山画像、真实 DB gap、多轮沙盒和事实/过程联合评价。

第 5 章介绍证据驱动 Pareto Agent，包括 `gatekeeper -> radar -> negotiator` 架构，以及 `major_geo_relax`、`risk_band_relax`、`tuition_value_relax`、`major_quality_relax`、`employment_outcome_relax`、`region_tree_relax` 等能力。其中 `region_tree_relax` 包含 `geo_block_relax` 与 `urban_tier_relax` 两个子策略。

第 6 章给出主实验和扩展实验结果，分析逐例证据与典型失败样本，说明 `app_pareto` 与 `hard_constraint` 的对照关系。主实验为 `major_geo_v1 + risk_band_v1`，五组扩展实验包含 `school_strength_v1`、`tuition_value_v1`、`major_quality_v1`、`employment_outcome_v1` 和 `region_tree_v1`。

第 7 章总结全文，并讨论样本规模、真实用户校准、城市收益指标、概率化录取风险模型、多省份泛化等后续工作。

## 第 2 章 相关技术

### 2.1 检索增强生成与高考志愿问答系统

检索增强生成（Retrieval-Augmented Generation, RAG）通过在生成前引入外部知识检索，缓解大语言模型参数知识过时、事实细节不完整和领域知识不足等问题（可替换引用占位：RAG）。在高考志愿咨询场景中，RAG 可以接入招生章程、专业介绍、学校资料、往年录取分数和就业信息，使模型回答不完全依赖训练语料中的静态记忆。

传统 RAG 系统通常包含查询理解、检索、重排和生成等步骤。对高考志愿任务而言，仅依赖非结构化文本检索是不够的，因为考生的核心问题往往需要精确过滤：分数是否达线、选科是否满足要求、预算是否可接受、专业是否匹配、学校是否在目标地域内。因此，高考志愿 RAG 系统需要将关系型数据库过滤与文本检索结合起来：结构化表负责分数、位次、批次线、招生计划和学费等硬约束，向量检索负责章程、专业介绍和解释性文本。

本文的第一版系统 `gaokaollmmodel` 即可视为 Agentic RAG 原型。它通过状态机工作流、意图识别、Redis 用户画像、混合检索、BGE-M3 embedding、BCEmbedding reranker 和神经-符号一致性校验，使系统能够完成基础问答和推荐任务。该原型证明了大模型可以被工程化接入高考志愿咨询，但也暴露出一个问题：系统能回答问题，并不等于系统能改善用户决策。因此，v2 进一步把研究重点从“可用问答”转向“可评测的偏好妥协”。

### 2.2 数据证据标准化

高考志愿 Agent 的可解释性不仅来自自然语言说明，更来自可追溯的数据证据。本文的数据层首先以 PostgreSQL 招生快照为基础，保存 `admission_scores`、`school_admission_scores`、`score_rank_segments`、`batch_lines`、`admission_plans.tuition`、`schools`、`majors` 等核心表，用于判断候选是否真实可达、是否满足选科与预算等约束。

在基础招生事实之外，本文进一步引入三类标准化证据层。

第一类是专业质量标准化层。`discipline_major_mappings` 将学科评估一级学科或专业类映射到本科专业，`school_major_quality_signals` 统一接入专业排名、第四轮学科评估、特色专业、重点专业和满意度等信号，`school_major_quality_profiles` 按 `school_id + major_id` 聚合出 `quality_score`、`quality_gain`、专业排名、评级和证据来源。这样，Agent 可以说清楚“同样是某专业，为什么这所学校的专业质量证据更强”，而不是只泛泛地说学校更好。

第二类是就业结果标准化层。`major_employment_profiles` 保存原始就业画像，`major_employment_outcome_profiles` 将其中的就业排名、就业最多地区、行业分布、岗位分布、薪资分布和 `outcome_score` 清洗为可比较字段。这样，`employment_outcome_relax` 可以把“好就业”这一模糊偏好转化为 transcript 中可核验的就业排名、行业、岗位和薪资证据。

第三类是地域树 reviewed v1。`region_geo_tree_reviewed_v1.json` 将省份、城市和地理板块组织为可审校的层级节点，支撑 `geo_block_relax`；`region_urban_tier_tree_reviewed_v1.json` 将城市层级和资源密度表达组织为可审校节点，支撑 `urban_tier_relax`。这两棵树共同服务 `region_tree_relax`，使“别太远”“江浙沪可以”“想去好城市”等地域表达能够转化为 transcript 中可核验的源地域节点、目标地域节点和树置信度证据。

数据证据标准化的意义在于，它把“用户可能关心的因素”区分为“当前系统可核验的证据维度”和“暂时只能写入后续工作的偏好维度”。只有能够落到 PostgreSQL 或标准化证据表中的因素，才适合进入当前 benchmark 闭环。

### 2.3 Agent 与 LangGraph 工作流

Agent 技术强调让大语言模型不只是直接生成文本，而是能够维护状态、规划步骤、调用工具并根据中间结果继续决策（可替换引用占位：LLM Agent）。在高考志愿咨询任务中，Agent 的价值主要体现在三个方面：第一，从自然语言中抽取用户约束；第二，调用招生数据库进行精确查询；第三，将查询结果组织为符合用户偏好的解释性建议。

LangGraph 提供图式状态机编排能力，适合表达多步骤、多状态和可回溯的 Agent 工作流（可替换引用占位：LangGraph）。本文 v2 业务 Agent 使用如下工作流：

```text
gatekeeper -> radar -> negotiator
```

其中，`gatekeeper` 面向显式约束抽取和 baseline 查询；`radar` 面向 Pareto 机会探测；`negotiator` 面向证据化对话回复。这种划分使 Agent 的核心行为可以被 benchmark 审计：系统是否正确抽取用户约束，是否在数据库中发现了可谈判候选，是否把候选以事实证据而非泛化说服话术的形式呈现给用户。

当前 Agent 能力覆盖两类主实验放宽和五类扩展实验放宽。主能力包括 `major_geo_relax` 与 `risk_band_relax`；扩展能力包括 `strength_relax`、`tuition_value_relax`、`major_quality_relax`、`employment_outcome_relax` 和 `region_tree_relax`。其中，`tuition_value_relax` 依赖学费字段，`major_quality_relax` 依赖 `school_major_quality_profiles`，`employment_outcome_relax` 依赖 `major_employment_outcome_profiles`，`region_tree_relax` 依赖 reviewed 地域树，并通过 `geo_block_relax` 与 `urban_tier_relax` 组织地理板块和城市层级证据。

### 2.4 多轮用户模拟与 Benchmark 评测

传统问答 benchmark 通常以题目、答案和静态评分为中心，适合评价知识准确率或推理正确率。但高考志愿咨询的关键并不只是某个答案是否正确，而是系统能否在多轮对话中引导用户重新理解自己的偏好。用户可能先坚持某个专业、地域、预算或风险偏好，只有在看到真实可达候选后才接受妥协。因此，本文使用多轮沙盒评测而非单轮问答评测。

本文 benchmark 的核心是冰山画像。每个 persona 都包含用户会说出口的 `explicit_red_lines`，以及只有在看到充分证据后才会接受的 `implicit_flexibilities`。被测 Agent 只能看到模拟用户在对话中说出的内容，Agent 不读取 `implicit_flexibilities` 或 `volunteer_set` 等隐藏字段。模拟用户根据 persona 和对话历史生成下一轮话语，沙盒负责记录所有 turn、内部状态和停止条件，最终输出 transcript、逐例 report 和 summary。

这种设计使偏好妥协成为可评价对象。若 Agent 只重复用户显性红线，即使事实正确，也无法触发隐藏妥协；若 Agent 编造不可达候选，则会被事实裁判惩罚；只有在事实正确且能命中隐藏妥协条件时，才会获得较高的 `elicitation_success` 和 `pareto_gain`。

### 2.5 LLM-as-a-Judge 与事实/过程联合评价

LLM-as-a-Judge 常用于评价开放式文本质量、多轮对话质量和主观偏好匹配程度（可替换引用占位：LLM-as-a-Judge）。但在高考志愿场景中，单纯依赖 LLM judge 存在风险：模型可能忽略分数、位次、学校专业是否真实存在，也可能被流畅的解释性语言误导。

因此，本文采用事实/过程联合评价。事实评价由 deterministic factual judge 完成，重点检查推荐候选是否有学校、专业、最低分、最低位次、学费、专业质量或就业结果证据，并计算 hallucination rate。过程评价关注 Agent 是否成功触发用户隐性妥协，包括是否提出了相应 Pareto opportunities，是否命中隐藏志愿集合，是否把单一保守方案扩展为更完整或更有价值的方案。

这种联合评价能够区分两类系统：一类系统事实正确但不谈判，例如 `hard_constraint` baseline；另一类系统在保持事实正确的同时，通过真实证据触发用户妥协，例如 `app_pareto`。本文主张的提升不是生成更长或更热情的建议，而是在 0.000 hallucination rate 前提下提升多轮偏好启发效果。

### 2.6 专业树层级放宽

专业偏好是高考志愿咨询中最常见、也最难处理的约束之一。用户可能明确说“只读临床医学”，但在真实决策中，看到学校层次、专业质量或就业结果差异后，可能会接受同类医学专业、相关大类专业，甚至在某些情况下接受更远的替代专业。专业放宽不能完全依赖字符串相似度，也不能无解释地跳到任意专业，因此需要层级化专业结构支撑。

本文的专业树用于将 observed major names 归入可解释的专业层级。放宽过程从近到远逐步展开：同叶子簇内的名称变体、同父近邻、上层大类、probe 邻近大类，必要时退化到 `any_major`。这种 staged relaxation 使 `major_geo_relax` 不只是“去掉专业限制”，而是能够呈现从近邻专业到更远替代方案的可解释路径。

专业树和 probe 在本文中属于 Benchmark 基础设施和 Agent 探测支撑，不作为最终论文的单独主贡献中心。它们的作用是让专业放宽具有可复现、可审计和可解释的结构基础。

### 2.7 风险分层与冲稳保组合

高考志愿填报通常会使用“冲、稳、保”等风险层级组织志愿组合。v1 `gaokaollmmodel` 中已经实现过工程化的 `1:3:9` 冲稳保推荐策略，用于生成梯度化志愿建议。这一策略贴近真实填报实践，但在 v1 中主要作为推荐逻辑存在，并未被放入多轮偏好妥协 benchmark 中严格评测。

v2 的 `risk_band_relax` 将这一能力升级为可评测的风险偏好放宽闭环。对于显性表达“只求稳妥、不接受冲刺”的用户，Agent 不改变省份、专业、选科和预算等硬约束，只放宽风险偏好，将单一保守方案扩展为 `chong/wen/bao` 组合。系统优先使用 `rank_gap = min_rank - student_rank` 判定风险层级，位次数据不足时退化到 `score_margin = score - min_score`。每个候选保留学校、城市、专业、最低分、最低位次、分差、位次差和风险标签。

这使 v1 的 `1:3:9` 工程策略在 v2 中转化为“工程策略 -> 可评测数据证据闭环”：不是只生成一个冲稳保列表，而是通过 benchmark 验证该组合是否能触发用户从“只求稳”转向接受适度风险结构。

### 2.8 Pareto 偏好妥协与可扩展证据维度

Pareto 改进通常指在不损害某些条件的前提下，使至少一个目标得到改善。迁移到高考志愿咨询中，Pareto 偏好妥协可以理解为：在保留用户关键事实约束的前提下，放宽部分可能由信息不足形成的初始偏好，从而获得更高层次、更完整、更有价值或风险结构更合理的志愿集合。

本文的 `major_geo_relax` 与 `risk_band_relax` 分别对应两类主实验 Pareto 妥协。`major_geo_relax` 保留分数、选科和预算等硬约束，同时放宽专业与地域，寻找更高质量的可达候选；`risk_band_relax` 保留专业、地域、选科和预算等硬约束，只将“只求稳”的风险偏好扩展为冲稳保组合。

在数据扩展实验中，Pareto 妥协进一步扩展到成本、专业质量、就业结果和地域树维度。`tuition_value_relax` 在 `budget < tuition <= budget + 10000` 的窗口内，用学费增量换取学校层次或排名收益；`major_quality_relax` 在可达约束内寻找 `quality_score` 更高、专业证据更强的学校-专业组合；`employment_outcome_relax` 在同专业或专业树近邻专业中寻找就业排名、行业、岗位或薪资证据更强的方案；`region_tree_relax` 则使用 reviewed 地域树，在不把城市层级直接写成就业机会、生活成本或城市生活质量收益的前提下，呈现地理板块和城市层级放宽证据。`strength_relax` 作为较粗粒度学校/学科实力证据的过渡实验。

需要强调的是，本文不把所有用户偏好都视为可放宽对象。选科要求、真实分数、可达性和部分强约束仍被视为硬约束；城市生活质量、家庭距离、校园文化和个人兴趣匹配等因素，如果缺少可核验数据证据，就不应被写成已实现的 Pareto 放宽。`region_tree_v1` 是扩展实验，不替代 `major_geo_v1 + risk_band_v1` 主实验；其中城市层级只作为 reviewed region-tree 证据，不直接等价于就业机会、生活成本或城市生活质量收益。Agent 的任务不是强行说服用户改变真实偏好，而是在可核验数据中呈现放宽某些初始红线后的收益，由用户模拟器或真实用户根据证据决定是否接受。

### 2.9 本章小结

本章从 RAG、数据证据标准化、Agent、LangGraph、多轮 benchmark、LLM-as-a-Judge、专业树、地域树、风险分层和 Pareto 偏好妥协等角度，梳理了本文方法所依赖的关键技术。总体来看，v1 `gaokaollmmodel` 证明了高考志愿咨询可以被构建为 Agentic RAG 工程系统；v2 则进一步将研究问题收敛到可评测的偏好妥协 Agent，并通过数据贡献、Agent 贡献和 Benchmark 贡献形成最终论文主线。

后续章节将先介绍 v1 原型系统与问题诊断，再展开 v2 的数据层与 Benchmark 构建、证据驱动 Pareto Agent 设计、主实验与扩展实验结果，以及局限性和后续工作。
