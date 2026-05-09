# v1/v2 论文整合与最终章节组织方案

本文档用于解决最终毕业论文的一个关键组织问题：如何把 `gaokaollmmodel` 第一版 Agentic RAG 系统，与当前 v2 的 Agent+Benchmark 双实验闭环写成同一条研究主线。结论是：**v1 写成工程原型与问题发现，v2 写成研究问题收敛后的最终主贡献**。

参考材料：

- v1 代码目录：`D:\gaokaollm\gaokaollmmodel`
- v1 中期报告：`D:\毕设\latex-for-zju-master\latex-for-zju-master\body\undergraduate\proposal\midcheck\Midterm_Report_GaokaoLLM.tex`
- v2 方法与实验正文：`gaokaollm_bench/outputs/thesis_method_experiment_chapters.md`
- v2 贡献母版：`gaokaollm_bench/outputs/thesis_agent_benchmark_contribution.md`
- `major_geo_v1` 结果：`gaokaollm_bench/outputs/agent_benchmark_major_geo_v1_summary.md`
- `major_geo_v1` 逐例证据：`gaokaollm_bench/outputs/agent_benchmark_major_geo_v1_evidence.md`
- `risk_band_v1` 结果：`gaokaollm_bench/outputs/agent_benchmark_risk_band_v1_summary.md`
- `risk_band_v1` 逐例证据：`gaokaollm_bench/outputs/agent_benchmark_risk_band_v1_evidence.md`
- v2 双实验可复现审计：`gaokaollm_bench/outputs/thesis_artifact_audit.md`

## 1. 两个版本的定位

`gaokaollmmodel` 是第一版面向高考志愿咨询的 Agentic RAG 原型。它的目标是先做出一个能回答高考志愿问题的端到端系统，重点解决工程可用性：如何接入招生数据、如何识别用户意图、如何做混合检索、如何维持多轮画像、如何降低响应延迟、如何减少大模型在改写和生成中的幻觉。

当前 v2 是研究问题收敛后的版本。它不再把重点放在“系统能否回答问题”，而是进一步追问：在用户显性偏好可能存在信息不足型锚定时，Agent 能否用真实招生数据中的反事实证据，触发用户接受更优或更完整的志愿集合。围绕这个问题，v2 构建了冰山画像 benchmark、多轮沙盒、事实/过程联合评价，并实现了两类可审计的证据驱动 Pareto 谈判能力：

- `major_geo_relax`：在保留分数、预算和选科等事实约束的前提下，同时放宽专业与地域约束。
- `risk_band_relax`：在不改变省份、专业、选科和预算等硬约束的前提下，把“只求稳”扩展为 `chong/wen/bao` 冲稳保组合。

因此，最终论文不应把 v1 和 v2 写成两个并列无关项目，也不应把 v2 写成推翻 v1。更合适的叙事是：

```text
v1：工程原型跑通高考志愿 Agentic RAG
  -> 暴露仅靠问答/RAG 难以严格评测偏好妥协效果
  -> v2：构建 benchmark，并设计可被评测的 Pareto 谈判 Agent
  -> v2 双实验：验证专业+地域联合放宽与风险偏好放宽两类动态决策能力
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

这些内容适合写进论文的“原型系统与问题诊断”章节。它们说明前期已经完成完整工程系统，也自然引出最终研究问题：仅有 Agentic RAG 系统还不足以证明“推荐是否真正改善了用户决策”，还需要 benchmark 与可量化评测。

其中，v1 的 `1:3:9` 冲稳保推荐不应被包装成最终主贡献，而应写成 v2 `risk_band_relax` 的工程来源。v1 证明系统能够生成风险梯度推荐；v2 则把这种梯度推荐放进冰山画像、多轮沙盒和事实/过程联合评价中，验证它是否真的触发了用户可接受的偏好妥协。

## 3. v2 内容概括

v2 的核心是 Agent+Benchmark 闭环，主线比 v1 更聚焦：

- Benchmark 贡献：构建冰山画像、多轮沙盒、真实 DB gap 生成、专业树层级放宽、风险偏好画像、事实/过程联合评价。
- Agent 贡献：构建证据驱动 Pareto 谈判 Agent，通过 `gatekeeper -> radar -> negotiator` 架构发现并表达可谈判机会。
- 双能力贡献：实现 `major_geo_relax` 专业+地域联合放宽，以及 `risk_band_relax` 风险偏好放宽。
- 实验贡献：用 `app_pareto` vs `hard_constraint` 对照验证 Agent 是否优于只迎合显性红线的 baseline。
- 可审计贡献：保留 transcript、逐例 report、summary、逐例证据附录和 SHA256 审计报告。

v2 的实验结果属于最终论文的核心实验，不能混入 v1 成果中。当前第一版主实验为两组：

| 实验 | `app_pareto` | `hard_constraint` | 论文含义 |
|---|---|---|---|
| `major_geo_v1` | `0.900 / 0.900 / 0.000 / 5.20` | `0.000 / 0.000 / 0.000 / 7.00` | 专业+地域联合放宽可显著触发隐藏妥协 |
| `risk_band_v1` | `1.000 / 3.000 / 0.000 / 5.00` | `0.000 / 0.000 / 0.000 / 15.00` | 风险偏好放宽可把只求稳转化为冲稳保组合 |

表中四个指标依次为 `elicitation_success_rate / mean_pareto_gain / mean_hallucination_rate / avg_turns`。两组结果均已纳入 `thesis_artifact_audit.md`，审计结果为 `Overall: PASS`。

## 4. v1/v2 对比表

| 维度 | v1: `gaokaollmmodel` | v2: 当前 Agent+Benchmark |
|---|---|---|
| 核心定位 | 面向高考志愿咨询的 Agentic RAG 原型 | 面向偏好妥协的可评测决策 Agent |
| 主要问题 | 如何让系统能查、能答、能多轮交互 | 如何证明 Agent 能触发更优或更完整的偏好妥协 |
| 数据使用 | MySQL/向量库/Redis 支撑问答与检索 | PostgreSQL 快照支撑真实 DB gap 和评测 |
| Agent 架构 | 状态机式 RAG 工作流，含意图识别、检索、生成 | LangGraph `gatekeeper -> radar -> negotiator` |
| 算法重点 | 混合检索、重排、`1:3:9` 冲稳保、上下文裁剪、一致性校验 | `major_geo_relax` 与 `risk_band_relax` |
| 风险推荐定位 | 工程化梯度推荐策略 | 可被 benchmark 检验的风险偏好谈判能力 |
| 评测方式 | 工程测试、功能验证、延迟与稳定性优化 | 多轮 benchmark、transcript、hallucination、Pareto gain |
| 论文角色 | 原型系统、工程基础、问题来源 | 最终主贡献、方法与实验核心 |
| 风险 | 容易变成工程堆料，缺少统一量化评测 | 样本量较小，但有逐例证据和双实验审计 |

## 5. 最终论文章节建议

| 章节 | 建议标题 | 主要内容 | v1/v2 归属 |
|---|---|---|---|
| 第 1 章 | 绪论 | 高考志愿咨询的高风险性，大模型幻觉与偏好锚定问题，研究目标与贡献 | v1/v2 共同背景 |
| 第 2 章 | 相关技术 | RAG、Agent、LangGraph、向量检索、多轮评测、LLM-as-a-Judge | 方法背景 |
| 第 3 章 | 第一版 Agentic RAG 原型系统与问题诊断 | `gaokaollmmodel` 架构、意图识别、画像缓存、混合检索、`1:3:9` 冲稳保、流式响应、一致性校验；指出评测不足 | v1 正文 |
| 第 4 章 | 高考志愿偏好妥协 Benchmark 构建 | 冰山画像、真实 DB gap、专业+地域联合放宽画像、风险偏好放宽画像、多轮沙盒、事实/过程联合评价 | v2 主贡献 |
| 第 5 章 | 证据驱动 Pareto 谈判 Agent 设计 | `gatekeeper -> radar -> negotiator`，`major_geo_relax`，`risk_band_relax`，baseline 对照 | v2 主贡献 |
| 第 6 章 | 实验结果、逐例证据与可复现审计 | `major_geo_v1`、`risk_band_v1`、`app_pareto` vs `hard_constraint`、失败 case、逐例证据、双实验审计 | v2 主实验 |
| 第 7 章 | 总结与展望 | 总结从工程原型到可评测 Agent 的演进，讨论样本规模、真实用户、事实裁判增强和更多放宽类别 | 综合 |

该结构的好处是：v1 不会被浪费，也不会抢走 v2 的主贡献位置；v2 的 benchmark 与 Agent 结果成为最终论文的学术闭环。

## 6. 贡献取舍表

| 内容 | 是否进入正文 | 建议位置 | 处理方式 |
|---|---|---|---|
| v1 LangGraph/状态机工作流 | 是 | 第 3 章 | 写成原型系统架构，不作为最终评测贡献 |
| v1 意图识别与 Redis 画像 | 是 | 第 3 章 | 说明多轮咨询工程基础 |
| v1 BGE-M3/BCEmbedding 混合检索 | 是 | 第 3 章 | 简述检索链路，避免展开过多模型细节 |
| v1 `1:3:9` 冲稳保推荐 | 是 | 第 3 章 | 作为风险组合谈判的工程来源 |
| v1 SSE 流式响应与 TTFT 优化 | 可选 | 第 3 章或附录 | 若篇幅紧张，放附录或实现细节 |
| v1 Chain of Draft/性能优化 | 可选 | 附录 | 不包装成最终主贡献 |
| v1 神经-符号一致性校验 | 是 | 第 3 章 | 作为问题诊断和防幻觉经验 |
| v2 冰山画像 benchmark | 是 | 第 4 章 | Benchmark 贡献核心 |
| v2 专业树和 probe | 是 | 第 4 章 | 作为 benchmark 基础设施和专业放宽支撑 |
| v2 `major_geo_relax` | 是 | 第 5 章 | Agent 贡献核心能力之一 |
| v2 `risk_band_relax` | 是 | 第 5 章 | Agent 贡献核心能力之一，也是 v1 冲稳保策略的可评测升级 |
| v2 `major_geo_v1` 实验 | 是 | 第 6 章 | 专业+地域联合放宽主实验 |
| v2 `risk_band_v1` 实验 | 是 | 第 6 章 | 风险偏好放宽主实验 |
| v2 审计报告与逐例证据 | 是 | 第 6 章 | 增强可复现和可信度 |

## 7. 过渡叙事模板

论文中可以使用如下过渡逻辑：

第一阶段，本研究实现了一个面向高考志愿咨询的 Agentic RAG 原型系统。该系统通过状态机工作流、动态画像缓存、混合检索和一致性校验等机制，使大模型能够在真实招生数据约束下完成基础问答和推荐任务。这一阶段证明了高考志愿咨询可以被构建为一个可运行的智能体系统。

但是，第一版系统也暴露出一个更核心的问题：系统能回答问题，并不等于系统能改善用户决策。特别是在高考志愿这种偏好强、风险高、约束多的场景中，用户的显性红线可能包含信息不足形成的初始锚定。传统 RAG 指标和单轮功能测试难以评价 Agent 是否真正帮助用户发现更优且可接受的志愿集合。

因此，第二阶段将研究重点从“构建可用问答系统”收敛到“构建可评测的偏好妥协 Agent”。v2 通过冰山画像 benchmark 显式建模显性红线和隐性妥协条件，并设计多轮沙盒和事实/过程联合评价；在 Agent 侧，则通过 `major_geo_relax` 探测专业与地域联合放宽后的真实可达志愿集合，通过 `risk_band_relax` 把用户的单一保守偏好扩展为带有最低分、最低位次、分差和位次差证据的 `chong/wen/bao` 组合。

最终实验表明，在 `major_geo_v1` 中，`app_pareto` 相比 `hard_constraint` 将启发成功率从 0.000 提升到 0.900，同时保持 0.000 的幻觉率；在 `risk_band_v1` 中，`app_pareto` 将启发成功率从 0.000 提升到 1.000，平均 Pareto gain 从 0.000 提升到 3.000，同样保持 0.000 的幻觉率。这说明 v2 不是对 v1 的否定，而是把 v1 的工程能力推进到可评测、可审计、可逐例追溯的研究闭环。

## 8. hidden persona 边界

论文中需要明确写出：v2 Agent 不读取 benchmark persona 的 `implicit_flexibilities` 或 `volunteer_set`。这些字段只作为模拟用户和 evaluator 的 ground truth。被测 Agent 只使用用户显式话语中抽取出的分数、省份、专业、选科、预算、风险偏好等约束，以及 PostgreSQL 查询得到的真实招生证据。

这一点对于 v1/v2 整合尤其重要。v1 是工程系统，主要关注能否查证和回答；v2 是评测系统，必须证明 Agent 的谈判证据来自公开输入和数据库查询，而不是从隐藏画像泄漏而来。`thesis_artifact_audit.md` 已经将这条边界纳入双实验审计。

## 9. 论文写作风险与规避

| 风险 | 表现 | 规避方式 |
|---|---|---|
| 两个项目割裂 | 第 3 章写 v1，第 4-6 章突然切到 v2 | 用“v1 发现评测不足，v2 解决评测与偏好妥协”作为过渡 |
| v1 工程内容过重 | 大量描述流式、缓存、线程池，淹没主贡献 | v1 保留架构和问题诊断，性能优化放附录 |
| v2 像凭空出现 | 没解释为什么需要 benchmark | 从 v1 缺少严格偏好评测自然引出 |
| 风险推荐归属混乱 | 把 v1 `1:3:9` 和 v2 `risk_band_relax` 写成同一件事 | v1 写工程策略，v2 写可评测的多轮偏好谈判 |
| 贡献口径混乱 | 同时说 RAG、性能优化、benchmark、Agent 都是主贡献 | 主贡献固定为 Benchmark 贡献 + Agent 贡献 |
| 实验归属混乱 | 把 `app_pareto 0.900` 或 `app_pareto 1.000` 写成 v1 系统结果 | 明确两组结果只属于 v2 Agent-vs-Baseline 主实验 |
| 成功率夸大 | 把 `major_geo_v1` 写成 100% 成功 | 明确 `real-db-set-浙江-569-009` 是唯一失败样本 |

## 10. 最终贡献表述建议

最终论文摘要和绪论中，建议将贡献写成三点，但前两点是主贡献，第三点是工程支撑：

1. 提出面向高考志愿偏好妥协的冰山画像 benchmark，将评测从静态问答扩展到多轮偏好启发，并结合真实 DB gap、专业树层级放宽、风险偏好画像和事实/过程联合评价。
2. 设计证据驱动的 Pareto 谈判 Agent，通过 `major_geo_relax` 和 `risk_band_relax` 在不读取隐藏 persona 的前提下，基于真实招生数据探测可达的专业+地域联合放宽方案与冲稳保风险组合。
3. 基于第一版 Agentic RAG 原型积累的状态机编排、混合检索、动态画像、`1:3:9` 冲稳保推荐和防幻觉经验，形成完整的高考志愿智能体工程基础。

这样写可以保留 v1 的工作量和工程价值，同时让最终论文的学术主线落在 v2 的 Agent+Benchmark 双实验闭环上。
