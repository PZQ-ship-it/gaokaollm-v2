# v1/v2 论文整合与最终章节组织方案

本文档用于解决最终毕业论文的一个关键组织问题：如何把 `gaokaollmmodel` 第一版 Agentic RAG 系统，与当前 v2 的“数据 + Agent + Benchmark”闭环写成同一条研究主线。结论是：**v1 写成工程原型与问题发现，v2 写成研究问题收敛后的最终主贡献**。

参考材料：

- v1 代码目录：`D:\gaokaollm\gaokaollmmodel`
- v1 中期报告：`D:\毕设\latex-for-zju-master\latex-for-zju-master\body\undergraduate\proposal\midcheck\Midterm_Report_GaokaoLLM.tex`
- v2 方法与实验正文：`gaokaollm_bench/outputs/thesis_method_experiment_chapters.md`
- v2 贡献母版：`gaokaollm_bench/outputs/thesis_agent_benchmark_contribution.md`
- 动态决策路线图：`gaokaollm_bench/outputs/dynamic_decision_considerations_roadmap.md`
- 论文文档总入口：`gaokaollm_bench/outputs/thesis_document_hub.md`
- 论文核心事实清单：`gaokaollm_bench/outputs/thesis_claims_manifest.json`
- 主实验逐例证据：`agent_benchmark_major_geo_v1_evidence.md`、`agent_benchmark_risk_band_v1_evidence.md`
- 扩展实验逐例证据：`gaokaollm_bench/outputs/thesis_data_agent_benchmark_extension_evidence.md`
- 地域树扩展实验证据：`gaokaollm_bench/outputs/agent_benchmark_region_tree_v1_evidence.md`
- 多轴 Benchmark 压力测试：`gaokaollm_bench/outputs/agent_benchmark_multi_axis_v1_summary.md`、`gaokaollm_bench/outputs/agent_benchmark_multi_axis_v1_evidence.md`、`gaokaollm_bench/outputs/agent_benchmark_multi_axis_v2_summary.md`、`gaokaollm_bench/outputs/agent_benchmark_multi_axis_v2_evidence.md`

## 1. 两个版本的定位

`gaokaollmmodel` 是第一版面向高考志愿咨询的 Agentic RAG 原型。它的目标是先做出一个能回答高考志愿问题的端到端系统，重点解决工程可用性：如何接入招生数据、如何识别用户意图、如何做混合检索、如何维持多轮画像、如何降低响应延迟、如何减少大模型在改写和生成中的幻觉。

当前 v2 是研究问题收敛后的版本。它不再把重点放在“系统能否回答问题”，而是进一步追问：在用户显性偏好可能存在信息不足型锚定时，Agent 能否用真实招生数据和标准化证据层中的反事实证据，触发用户接受更优或更完整的志愿集合。围绕这个问题，v2 形成了三层主贡献：

| 贡献层次 | 当前内容 | 论文作用 |
|---|---|---|
| 数据贡献 | PostgreSQL 招生快照、分数/位次、学费、专业树、`school_major_quality_profiles`、`major_employment_outcome_profiles`、`region_geo_tree_reviewed_v1.json`、`region_urban_tier_tree_reviewed_v1.json` | 为每一次推荐、放宽和评测提供可核验事实证据 |
| Agent 贡献 | LangGraph `gatekeeper -> radar -> negotiator`，以及 `major_geo_relax`、`risk_band_relax`、`tuition_value_relax`、`major_quality_relax`、`employment_outcome_relax`、`region_tree_relax` | 把用户显性约束转化为证据驱动的 Pareto 妥协谈判 |
| Benchmark 贡献 | 冰山画像、多轮沙盒、事实/过程联合评价、`app_pareto` vs `hard_constraint` | 验证 Agent 是否真的触发隐藏可妥协条件，而不是只生成看似合理的建议 |

因此，最终论文不应把 v1 和 v2 写成两个并列无关项目，也不应把 v2 写成推翻 v1。更合适的叙事是：

```text
v1：工程原型跑通高考志愿 Agentic RAG
  -> 暴露仅靠问答/RAG 难以严格评测偏好妥协效果
  -> v2：补齐数据证据层、Benchmark 框架和 Pareto 谈判 Agent
  -> v2 主实验：验证专业+地域联合放宽与风险偏好放宽
  -> v2 扩展实验：验证学科实力、学费、专业质量、就业结果和地域树证据可接入同一闭环
```

## 2. v1 内容概括

根据 `gaokaollmmodel` 代码结构和中期报告，v1 可以概括为“面向高考志愿咨询的 Agentic RAG 原型系统”。其主要内容包括：

- LangGraph/状态机工作流：通过图状态机管理安全检测、状态追踪、查询改写、意图识别、检索和生成。
- 意图识别与路由：支持分数、选科、地域、高校、专业等多类查询意图，并处理部分复合查询。
- Redis 用户画像：缓存用户省份、分数、选科等多轮对话状态，缓解上下文漂移。
- 混合检索：结合关系型过滤与向量检索，使用 BGE-M3 embedding 与 BCEmbedding reranker 进行二阶段重排。
- 分层推荐：实现 `1:3:9` 冲、稳、保梯度推荐策略，贴近真实志愿填报逻辑。
- 神经-符号一致性校验：通过规则和正则校验 LLM 改写结果，避免模型篡改用户真实分数。
- SSE 流式响应与低延迟优化：通过流式输出、Flash Attention、Chain of Draft 等方式改善交互体验。

这些内容适合写进论文第 3 章“第一版 Agentic RAG 原型系统与问题诊断”。它们说明前期已经完成完整工程系统，也自然引出最终研究问题：仅有 Agentic RAG 系统还不足以证明“推荐是否真正改善了用户决策”，还需要数据证据、benchmark 与可量化评测。

其中，v1 的 `1:3:9` 冲稳保推荐不应被包装成最终主贡献，而应写成 v2 `risk_band_relax` 的工程来源。v1 证明系统能够生成风险梯度推荐；v2 则把这种梯度推荐放进冰山画像、多轮沙盒和事实/过程联合评价中，验证它是否真的触发了用户可接受的偏好妥协。

## 3. v2 内容概括

v2 的核心是“数据 + Agent + Benchmark”闭环，主线比 v1 更聚焦。

数据层方面，v2 使用本地 PostgreSQL 招生快照承载分数、位次、批次线、学校、专业、招生计划和学费字段，并进一步构建专业树、专业质量标准化层、就业结果标准化层和地域树 reviewed v1。`school_major_quality_profiles` 将专业排名、学科评估、特色专业、重点专业和满意度等信号聚合为学校-专业质量证据；`major_employment_outcome_profiles` 将就业排名、行业、岗位和薪资等就业画像清洗为可比较字段；`region_geo_tree_reviewed_v1.json` 与 `region_urban_tier_tree_reviewed_v1.json` 将学校所在省市映射为可审校的地理板块和城市层级证据。

Agent 层方面，v2 使用 `gatekeeper -> radar -> negotiator` 结构：`gatekeeper` 抽取用户显式约束并查询 baseline，`radar` 调用确定性 SQL 探针寻找 Pareto opportunities，`negotiator` 将真实候选组织为面向用户的证据化回复。当前能力包括两类主能力和五类扩展能力：

- 主能力：`major_geo_relax`、`risk_band_relax`。
- 扩展能力：`strength_relax`、`tuition_value_relax`、`major_quality_relax`、`employment_outcome_relax`、`region_tree_relax`。其中 `region_tree_relax` 包含 `geo_block_relax` 与 `urban_tier_relax` 两个子策略。

Benchmark 层方面，v2 构建冰山画像、多轮沙盒和事实/过程联合评价。`hard_constraint` baseline 只报告显性硬约束下的可达志愿，不主动谈判；`app_pareto` 则在真实数据约束内提出证据驱动的 Pareto 妥协。被测 Agent 不读取 `implicit_flexibilities` 或 `volunteer_set`，这些 hidden persona 字段只用于模拟用户和 evaluator ground truth。

## 4. v1/v2 对比表

| 维度 | v1: `gaokaollmmodel` | v2: 数据 + Agent + Benchmark |
|---|---|---|
| 核心定位 | 面向高考志愿咨询的 Agentic RAG 原型 | 面向偏好妥协的可评测决策 Agent 与 Benchmark |
| 主要问题 | 如何让系统能查、能答、能多轮交互 | 如何证明 Agent 能触发更优或更完整的偏好妥协 |
| 数据使用 | MySQL/向量库/Redis 支撑问答与检索 | PostgreSQL 快照、专业树、专业质量、就业结果和地域树 reviewed v1 支撑真实 DB gap 与评测 |
| Agent 架构 | 状态机式 RAG 工作流，含意图识别、检索、生成 | LangGraph `gatekeeper -> radar -> negotiator` |
| 算法重点 | 混合检索、重排、`1:3:9` 冲稳保、上下文裁剪、一致性校验 | `major_geo_relax`、`risk_band_relax`、`tuition_value_relax`、`major_quality_relax`、`employment_outcome_relax`、`region_tree_relax` |
| 风险推荐定位 | 工程化梯度推荐策略 | 可被 benchmark 检验的风险偏好谈判能力 |
| 数据贡献定位 | 作为系统运行依赖 | 作为论文主贡献之一，提供可核验 Pareto 证据 |
| 评测方式 | 工程测试、功能验证、延迟与稳定性优化 | 多轮 benchmark、transcript、hallucination、Pareto gain、逐例证据 |
| 论文角色 | 工程原型、系统基础、问题来源 | 最终主贡献、方法与实验核心 |
| 风险 | 容易变成工程堆料，缺少统一量化评测 | 样本量较小，但有逐例证据和多组离线结果 |

## 5. 最终论文章节建议

| 章节 | 建议标题 | 主要内容 | v1/v2 归属 |
|---|---|---|---|
| 第 1 章 | 绪论 | 高考志愿咨询的高风险性，大模型幻觉与偏好锚定问题，数据 + Agent + Benchmark 三贡献 | v1/v2 共同背景 |
| 第 2 章 | 相关技术 | RAG、Agent、LangGraph、数据证据标准化、多轮评测、LLM-as-a-Judge | 方法背景 |
| 第 3 章 | 第一版 Agentic RAG 原型系统与问题诊断 | `gaokaollmmodel` 架构、意图识别、画像缓存、混合检索、`1:3:9` 冲稳保、流式响应、一致性校验；指出评测不足 | v1 正文 |
| 第 4 章 | 高考志愿偏好妥协 Benchmark 与数据层构建 | PostgreSQL 快照、专业树、专业质量与就业结果标准化层、地域树 reviewed v1、冰山画像、真实 DB gap、多轮沙盒、事实/过程联合评价 | v2 主贡献 |
| 第 5 章 | 证据驱动 Pareto 谈判 Agent 设计 | `gatekeeper -> radar -> negotiator`，`major_geo_relax`、`risk_band_relax`、`tuition_value_relax`、`major_quality_relax`、`employment_outcome_relax`、`region_tree_relax` | v2 主贡献 |
| 第 6 章 | 实验结果、逐例证据与扩展实验 | 主实验 `major_geo_v1 + risk_band_v1`，扩展实验 `school_strength_v1 + tuition_value_v1 + major_quality_v1 + employment_outcome_v1 + region_tree_v1`，`multi_axis_v1` / `multi_axis_v2` Benchmark 压力测试，失败 case 与逐例证据 | v2 实验 |
| 第 7 章 | 总结与展望 | 总结从工程原型到可评测 Agent 的演进，讨论样本规模、真实用户、事实裁判增强和更多放宽类别 | 综合 |

该结构的好处是：v1 不会被浪费，也不会抢走 v2 的主贡献位置；v2 的数据层、benchmark 与 Agent 结果成为最终论文的学术闭环。

## 6. 贡献取舍表

| 内容 | 是否进入正文 | 建议位置 | 处理方式 |
|---|---|---|---|
| v1 LangGraph/状态机工作流 | 是 | 第 3 章 | 写成原型系统架构，不作为最终评测贡献 |
| v1 意图识别与 Redis 画像 | 是 | 第 3 章 | 说明多轮咨询工程基础 |
| v1 BGE-M3/BCEmbedding 混合检索 | 是 | 第 3 章 | 简述检索链路，避免展开过多模型细节 |
| v1 `1:3:9` 冲稳保推荐 | 是 | 第 3 章 | 作为 `risk_band_relax` 的工程来源 |
| v1 SSE 流式响应与 TTFT 优化 | 可选 | 第 3 章或附录 | 若篇幅紧张，放附录或实现细节 |
| v1 Chain of Draft/性能优化 | 可选 | 附录 | 不包装成最终主贡献 |
| v1 神经-符号一致性校验 | 是 | 第 3 章 | 作为问题诊断和防幻觉经验 |
| v2 PostgreSQL 招生快照 | 是 | 第 4 章 | 数据贡献底座 |
| v2 专业质量标准化层 | 是 | 第 4 章 | 数据贡献核心扩展之一 |
| v2 就业结果标准化层 | 是 | 第 4 章 | 数据贡献核心扩展之一 |
| v2 地域树 reviewed v1 | 是 | 第 4 章 | 数据贡献中的层级地域证据 |
| v2 冰山画像 benchmark | 是 | 第 4 章 | Benchmark 贡献核心 |
| v2 专业树和 probe | 是 | 第 4 章 | Benchmark 基础设施和专业放宽支撑 |
| v2 `major_geo_relax` | 是 | 第 5 章 | Agent 主能力之一 |
| v2 `risk_band_relax` | 是 | 第 5 章 | Agent 主能力之一，也是 v1 冲稳保策略的可评测升级 |
| v2 `tuition_value_relax` | 是 | 第 5 章或第 6 章扩展实验 | 作为数据证据扩展能力 |
| v2 `major_quality_relax` | 是 | 第 5 章或第 6 章扩展实验 | 作为专业质量数据贡献的验证 |
| v2 `employment_outcome_relax` | 是 | 第 5 章或第 6 章扩展实验 | 作为就业结果数据贡献的验证 |
| v2 `region_tree_relax` | 是 | 第 5 章或第 6 章扩展实验 | 作为地域树数据贡献的验证，含 `geo_block_relax` 与 `urban_tier_relax` |
| v2 主实验 | 是 | 第 6 章 | `major_geo_v1 + risk_band_v1` |
| v2 扩展实验 | 是 | 第 6 章 | `school_strength_v1 + tuition_value_v1 + major_quality_v1 + employment_outcome_v1 + region_tree_v1` |

## 7. 实验结果归属

v2 的实验结果属于最终论文的方法与实验章节，不能混入 v1 成果中。当前第一版主实验为 `major_geo_v1 + risk_band_v1`，五组扩展实验用于支撑数据贡献和框架可扩展性。

斜杠格式依次为：

```text
elicitation_success_rate / mean_pareto_gain / mean_hallucination_rate / avg_turns
```

| 实验 | 类型 | `app_pareto` | `hard_constraint` | 论文含义 |
|---|---|---:|---:|---|
| `major_geo_v1` | 主实验 | `0.900 / 0.900 / 0.000 / 5.20` | `0.000 / 0.000 / 0.000 / 7.00` | 专业+地域联合放宽可显著触发隐藏妥协 |
| `risk_band_v1` | 主实验 | `1.000 / 3.000 / 0.000 / 5.00` | `0.000 / 0.000 / 0.000 / 15.00` | 风险偏好放宽可把只求稳转化为冲稳保组合 |
| `school_strength_v1` | 扩展实验 | `1.000 / 15.000 / 0.000 / 5.00` | `0.000 / 0.000 / 0.000 / 11.00` | 学校/学科实力证据可接入同一谈判闭环 |
| `tuition_value_v1` | 扩展实验 | `1.000 / 1.000 / 0.000 / 5.00` | `0.000 / 0.000 / 0.000 / 11.00` | 学费字段可支撑预算性价比谈判 |
| `major_quality_v1` | 扩展实验 | `1.000 / 16.000 / 0.000 / 5.00` | `0.000 / 0.000 / 0.050 / 11.00` | 专业质量标准化层可支撑学校-专业质量跃迁 |
| `employment_outcome_v1` | 扩展实验 | `1.000 / 49.000 / 0.000 / 3.00` | `0.000 / 0.000 / 0.000 / 11.00` | 就业结果标准化层可支撑就业导向放宽 |
| `region_tree_v1` | 扩展实验 | `1.000 / 1.000 / 0.000 / 3.00` | `0.000 / 0.000 / 0.000 / 11.00` | reviewed 地域树可支撑地理板块和城市层级证据谈判 |

`major_geo_v1` 不是 100% 成功。失败样本为 `real-db-set-浙江-569-009`，该样本要求 Agent 进一步退到更远的 `any_major` 候选才能命中 hidden volunteer set，而当前回复停留在医学相关近邻阶段，因此 deterministic judge 未判定成功。论文中应保留该失败样本，以说明系统已经形成闭环但仍存在放宽阶段选择的改进空间。

此外，`multi_axis_v1` 与 `multi_axis_v2` 作为 Benchmark 压力测试单独写入第 6 章或附录，不并入上表的七组实验事实口径。`multi_axis_v1` 是历史压力测试版本，包含 `major_geo_risk`、`quality_tuition`、`employment_region` 三类 profile，各 10 个 case，聚合结果为 `app_pareto 0.533 / 1.133 / 0.029 / 7.67` vs `hard_constraint 0.000 / 0.000 / 0.000 / 13.00`，逐 profile 成功分布为 1/10、5/10、10/10。`multi_axis_v2` 是轴一致性修正版，仍使用三类 profile，但要求两个隐藏放宽轴围绕一致显性需求或可解释正交需求构造；聚合结果为 `app_pareto 0.367 / 1.133 / 0.005 / 9.33` vs `hard_constraint 0.000 / 0.000 / 0.008 / 13.00`，逐 profile 成功分布为 6/10、5/10、0/10。该测试说明，多轴隐藏妥协评测能够暴露单轴实验看不出的证据编排瓶颈，尤其 `employment_region` 暴露出就业证据与地域树证据联合组织不足。七组 `app_pareto` 实验结果和多轴压力测试结果都属于 v2，不混入 v1 成果。

## 8. 过渡叙事模板

论文中可以使用如下过渡逻辑。

第一阶段，本研究实现了一个面向高考志愿咨询的 Agentic RAG 原型系统。该系统通过状态机工作流、动态画像缓存、混合检索和一致性校验等机制，使大模型能够在真实招生数据约束下完成基础问答和推荐任务。这一阶段证明了高考志愿咨询可以被构建为一个可运行的智能体系统。

但是，第一版系统也暴露出一个更核心的问题：系统能回答问题，并不等于系统能改善用户决策。特别是在高考志愿这种偏好强、风险高、约束多的场景中，用户的显性红线可能包含信息不足形成的初始锚定。传统 RAG 指标和单轮功能测试难以评价 Agent 是否真正帮助用户发现更优且可接受的志愿集合。

因此，第二阶段将研究重点从“构建可用问答系统”收敛到“构建可评测的数据驱动偏好妥协 Agent”。v2 首先补齐可核验数据证据层，将分数、位次、学费、专业质量、就业结果和地域树节点转化为 Agent 可表达、Benchmark 可核验的字段；其次通过冰山画像 benchmark 显式建模显性红线和隐性妥协条件；最后在 Agent 侧使用 `major_geo_relax`、`risk_band_relax`、`tuition_value_relax`、`major_quality_relax`、`employment_outcome_relax` 和 `region_tree_relax` 等能力，验证证据驱动 Pareto 谈判是否优于只迎合显性红线的 baseline。

最终实验表明，在主实验中，`app_pareto` 相比 `hard_constraint` 显著提升隐性妥协触发效果，并保持较低幻觉率；在扩展实验中，同一框架也能够接入学科实力、学费预算、专业质量、就业结果和地域树等更多数据证据维度。这说明 v2 不是对 v1 的否定，而是把 v1 的工程能力推进到可评测、可审计、可逐例追溯的数据驱动研究闭环。

`multi_axis_v2` 则进一步作为压力测试修正版说明：当用户同时在两个方面存在隐藏妥协时，Benchmark 可以检验 Agent 是否具备多证据链组织能力，并通过轴一致性约束减少画像构造噪声。它只组合已有 relax 能力，不新增业务放宽算法；Agent 不读取 `implicit_flexibilities`、`volunteer_set` 或 `axis_flexibilities`。`multi_axis_v1` 保留为历史压力测试版本，用于对照说明修正前后的诊断差异。

## 9. hidden persona 边界

论文中需要明确写出：v2 Agent 不读取 benchmark persona 的 `implicit_flexibilities` 或 `volunteer_set`。这些字段只作为模拟用户和 evaluator 的 ground truth。被测 Agent 只使用用户显式话语中抽取出的分数、省份、专业、选科、预算、风险偏好、质量偏好和就业导向等约束，以及 PostgreSQL 查询得到的真实招生证据。

这一点对于 v1/v2 整合尤其重要。v1 是工程系统，主要关注能否查证和回答；v2 是评测系统，必须证明 Agent 的谈判证据来自公开输入和数据库查询，而不是从隐藏画像泄漏而来。论文中可以引用逐例 evidence 附录说明每个成功 case 都能回到 transcript 和候选证据。

## 10. 论文写作风险与规避

| 风险 | 表现 | 规避方式 |
|---|---|---|
| 两个项目割裂 | 第 3 章写 v1，第 4-6 章突然切到 v2 | 用“v1 发现评测不足，v2 解决数据证据、评测与偏好妥协”作为过渡 |
| v1 工程内容过重 | 大量描述流式、缓存、线程池，淹没主贡献 | v1 保留架构和问题诊断，性能优化放附录 |
| v2 像凭空出现 | 没解释为什么需要 benchmark 和数据标准化 | 从 v1 缺少严格偏好评测自然引出 |
| 风险推荐归属混乱 | 把 v1 `1:3:9` 和 v2 `risk_band_relax` 写成同一件事 | v1 写工程策略，v2 写可评测的多轮偏好谈判 |
| 贡献口径混乱 | 同时说 RAG、性能优化、benchmark、Agent 都是主贡献 | 主贡献固定为数据贡献 + Agent 贡献 + Benchmark 贡献 |
| 实验归属混乱 | 把 `app_pareto` 指标写成 v1 系统结果 | 明确七组结果都属于 v2，v1 只提供工程原型与问题来源 |
| 成功率夸大 | 把 `major_geo_v1` 写成 100% 成功 | 明确 `real-db-set-浙江-569-009` 是失败样本 |
| 扩展实验喧宾夺主 | 把七组实验都写成同等主贡献 | 主实验写 `major_geo_v1 + risk_band_v1`，扩展实验写数据贡献可扩展性 |
| 压力测试口径混乱 | 把 `multi_axis_v1` / `multi_axis_v2` 写成新的主实验或新的业务放宽算法 | 写成 Benchmark 压力测试：组合现有 relax 能力，检验双轴隐藏妥协和证据编排；`multi_axis_v2` 是轴一致性修正版 |

## 11. 最终贡献表述建议

最终论文摘要和绪论中，建议将贡献写成三点，并把 v1 作为工程基础补充说明：

1. 构建面向高考志愿动态决策的可核验数据证据层，基于 PostgreSQL 招生快照、专业树、专业质量标准化层、就业结果标准化层和地域树 reviewed v1，为分数、位次、学费、专业质量、就业结果和地域树节点等 Pareto 谈判证据提供数据基础。
2. 设计证据驱动的 Pareto 谈判 Agent，通过 `gatekeeper -> radar -> negotiator` 架构，在不读取 hidden persona 字段的前提下，基于用户显式话语和数据库查询结果提出 `major_geo_relax`、`risk_band_relax`、`tuition_value_relax`、`major_quality_relax`、`employment_outcome_relax`、`region_tree_relax` 等可审计放宽方案。
3. 提出面向高考志愿偏好妥协的冰山画像 benchmark，将评测从静态问答扩展到多轮偏好启发，并通过 `app_pareto` vs `hard_constraint` 对照、事实/过程联合评价、逐例 transcript 和 evidence 附录验证 Agent 是否真的触发隐性妥协。

补充表述：第一版 `gaokaollmmodel` Agentic RAG 原型提供了状态机编排、混合检索、动态画像、`1:3:9` 冲稳保推荐和防幻觉经验，是本文最终方案的工程基础和问题来源，但不承载 `app_pareto` 实验指标，也不作为最终主贡献。
