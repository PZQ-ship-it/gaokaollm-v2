# 第 7 章 总结与展望

本文档是毕业论文第 7 章“总结与展望”的正文母版，用于收束前文从 v1 工程原型到 v2 Agent+Benchmark 双实验闭环的完整主线。本文不新增实验结论，所有结果均引用已经通过审计的论文产物：

- `gaokaollm_bench/outputs/thesis_intro_related_work_chapters.md`
- `gaokaollm_bench/outputs/thesis_v1_prototype_chapter.md`
- `gaokaollm_bench/outputs/thesis_method_experiment_chapters.md`
- `gaokaollm_bench/outputs/thesis_agent_benchmark_contribution.md`
- `gaokaollm_bench/outputs/thesis_artifact_audit.md`

## 7.1 全文工作总结

本文围绕高考志愿咨询这一高风险、强约束、强偏好的教育决策场景，研究如何构建并评测能够进行多轮偏好妥协的智能体系统。与一般问答任务不同，高考志愿咨询不仅要求系统能回答学校、专业、分数和政策问题，还要求系统在真实招生数据约束下提供可核验、可追溯、可解释的建议。

全文工作可以概括为两个阶段。

第一阶段是 v1 `gaokaollmmodel` Agentic RAG 原型系统。该阶段完成了面向高考志愿咨询的工程闭环，包括 LangGraph/状态机工作流、意图识别、Redis 用户画像、混合检索、BGE-M3 embedding、BCEmbedding 重排、`1:3:9` 冲稳保推荐、神经-符号一致性校验和 SSE 流式响应。v1 证明了高考志愿咨询可以被构建为一个可运行的 Agentic RAG 系统，也暴露出传统工程原型难以严格证明偏好妥协效果的问题。

第二阶段是 v2 Agent+Benchmark 闭环。该阶段将研究重点从“系统能否回答问题”收敛到“Agent 能否在真实数据库约束下，通过证据驱动谈判触发用户可接受的 Pareto 妥协”。v2 构建了冰山画像 Benchmark、多轮沙盒、事实/过程联合评价和逐例审计证据，并实现了 `major_geo_relax` 与 `risk_band_relax` 两类动态放宽能力。

因此，本文最终主线可以表述为：v1 是工程原型与问题发现，v2 是最终主贡献。v1 的价值在于跑通系统和提出问题，v2 的价值在于把问题转化为可生成、可运行、可评价、可审计的 Agent+Benchmark 双贡献。

## 7.2 Benchmark 贡献总结

本文的 Benchmark 贡献是面向高考志愿偏好妥协任务构建了一套冰山画像多轮评测框架。该框架不再把评测对象限制为单轮问答正确率，而是关注 Agent 是否能够在多轮对话中发现用户显性红线背后的隐性妥协空间。

Benchmark 设计包含四个关键部分。

第一，冰山画像将用户偏好拆分为显性红线和隐性妥协条件。用户对 Agent 暴露的是对话中说出的分数、省份、专业、选科、预算和风险偏好，隐藏字段 `implicit_flexibilities` 与 `volunteer_set` 只作为模拟用户和 evaluator 的 ground truth。Agent 不读取 `implicit_flexibilities` 或 `volunteer_set`。

第二，真实 DB gap 生成机制从 PostgreSQL 招生数据中发现约束放宽后的可达志愿集合。这样生成的 persona 不依赖人工编造学校、专业和最低分，而是把真实数据库中的反事实机会写入评测样本。

第三，多轮沙盒连接 target agent 与模拟用户，记录 turn、reply、internal_state、transcript、report 和 summary，使偏好启发过程能够被逐例复盘。

第四，事实/过程联合评价同时检查 factual hallucination 与 elicitation success。事实评价约束学校、专业、最低分、最低位次等证据来源；过程评价检查 Agent 是否真正触发了隐藏妥协，而不是只顺从显性红线。

这些机制共同构成本文的 Benchmark 贡献：冰山画像 + 多轮沙盒 + 事实/过程联合评价 + 逐例 evidence + SHA256 审计。它让“偏好妥协”从一个难以验证的主观叙事变成可运行、可复现、可追溯的实验任务。

## 7.3 Agent 贡献总结

本文的 Agent 贡献是证据驱动 Pareto 谈判。v2 业务 Agent 采用 `gatekeeper -> radar -> negotiator` 三节点架构：`gatekeeper` 抽取用户显式约束并查询当前硬约束下的 baseline，`radar` 使用 PostgreSQL 查询探测可谈判机会，`negotiator` 将真实候选组织为面向用户的证据化回复。

当前 Agent 贡献主要体现在两类动态放宽能力上。

`major_geo_relax` 面向专业+地域联合放宽。它保留分数、选科、预算等事实约束，同时放宽专业和地域限制，结合专业树层级放宽策略查找更高层次或更可达的志愿集合。该能力用于回答“如果同时接受跨省和跨专业，能否换到更好的真实候选”这一问题。

`risk_band_relax` 面向风险偏好放宽。它不改变省份、专业、选科和预算等硬约束，只把“只求稳、不接受冲刺”的显性风险偏好扩展为 `chong/wen/bao` 冲稳保组合。系统优先使用 `rank_gap`，在位次数据不足时退化到 `score_margin`，并向用户展示学校、城市、专业、最低分、最低位次、分差、位次差和风险层级。

这两类能力的共同点是：Agent 不通过泛化说服话术强迫用户改变偏好，而是基于真实数据库证据展示放宽部分初始约束后的收益。用户是否接受妥协由模拟用户或真实用户依据证据决定。由此，Agent 贡献不是“生成更多推荐”，而是“在事实正确前提下进行可审计的 Pareto 谈判”。

## 7.4 实验结果总结

本文第一版主实验包含 `major_geo_v1` 与 `risk_band_v1` 两组 Agent-vs-Baseline 离线评测。对照对象为 `app_pareto` 与 `hard_constraint`。其中，`app_pareto` 表示接入证据驱动 Pareto 谈判能力的业务 Agent，`hard_constraint` 表示只报告当前显性硬约束下可达志愿、不主动谈判的 baseline。

| 实验 | Target | Elicitation Success | Mean Pareto Gain | Mean Hallucination | Avg Turns |
|---|---|---:|---:|---:|---:|
| `major_geo_v1` | `app_pareto` | 0.900 | 0.900 | 0.000 | 5.20 |
| `major_geo_v1` | `hard_constraint` | 0.000 | 0.000 | 0.000 | 7.00 |
| `risk_band_v1` | `app_pareto` | 1.000 | 3.000 | 0.000 | 5.00 |
| `risk_band_v1` | `hard_constraint` | 0.000 | 0.000 | 0.000 | 15.00 |

也可以将核心结果简写为：

- `major_geo_v1`: `app_pareto 0.900 / 0.900 / 0.000 / 5.20` vs `hard_constraint 0.000 / 0.000 / 0.000 / 7.00`
- `risk_band_v1`: `app_pareto 1.000 / 3.000 / 0.000 / 5.00` vs `hard_constraint 0.000 / 0.000 / 0.000 / 15.00`

四个指标依次为 `elicitation_success_rate / mean_pareto_gain / mean_hallucination_rate / avg_turns`。两组实验共同说明，`app_pareto` 相比 `hard_constraint` 的提升来自真实 DB 证据触发隐性妥协，而不是虚构学校、错误分数或不可达推荐。两组实验的 `mean_hallucination_rate` 均为 0.000，说明证据驱动谈判没有以事实可靠性为代价。

需要强调的是，`major_geo_v1` 并非 100% 成功。失败样本为 `real-db-set-浙江-569-009`。该样本中 Agent 停留在较近的医学相关大类兜底候选上，而未命中 hidden `volunteer_set` 所需的更远 `any_major` 集合。保留这一失败样本有助于说明本文实验结论是可审计的，而不是只报告成功案例。

上述 `app_pareto` 双实验结果属于 v2 主实验，不属于 v1 `gaokaollmmodel` 原型系统的直接性能结果。v1 是工程原型与问题发现，v2 是最终主贡献。

## 7.5 局限性

本文仍存在若干局限。

第一，样本规模较小。当前 `major_geo_v1` 与 `risk_band_v1` 均使用 10 条 persona，适合证明 Agent+Benchmark 闭环可复现、可审计，但尚不能作为大规模 leaderboard。后续需要扩展更多分数段、省份、专业类型和用户偏好分布，检验结论稳健性。

第二，当前主实验依赖 offline deterministic judge。该设置的优点是稳定、可重复、便于论文审计；局限是无法完全覆盖真实 LLM judge 或真实用户咨询中的细粒度行为。后续应引入多裁判一致性、人类抽样复核和真实咨询日志校准。

第三，当前数据快照以浙江 PostgreSQL 招生数据为主。高考志愿规则具有省份差异，选科、批次、计划和录取模式在不同地区可能不同。因此，本文结论还需要在更多省份快照和更多年份数据上验证。

第四，事实裁判粒度仍可增强。现阶段事实评价重点约束学校、专业、最低分、最低位次等核心证据，但对年份、省份、批次、选科、风险层级和同校去重等联合条件仍可进一步细化。未来可以将 hallucination 检查从学校级扩展到完整志愿项级别。

第五，当前 Pareto gain 仍是简化指标。它主要基于隐藏志愿集合命中、学校 tier、风险组合覆盖等信息，尚未充分纳入城市偏好、就业预期、家庭预算、学科实力、地域就业机会和多年稳定性等多目标收益。

## 7.6 后续工作

后续工作可以从四个方向展开。

第一，扩展动态放宽类别。当前已实现专业放宽、地域放宽、专业+地域联合放宽和风险偏好放宽。后续可继续实现城市放宽、学费放宽、就业导向、学科实力、地域就业机会、多年分数稳定性等类别，使 Agent 能处理更多真实咨询中的妥协维度。

第二，升级风险建模方法。当前 `risk_band_relax` 基于确定性的 `score_margin` / `rank_gap` 分层，能够提供稳定可解释的 `chong/wen/bao` 组合。未来可以引入概率化录取风险模型，将历年波动、招生计划变化、位次密度和批次线变化纳入估计，使风险层级更接近真实填报决策。

第三，扩展评测规模和用户真实性。后续可以增加 persona 数量、覆盖更多省份和专业，加入真实用户访谈或历史咨询日志，对模拟用户的隐藏妥协条件进行校准，减少 benchmark 与真实咨询行为之间的差距。

第四，增强审计与事实裁判。未来可以将 SQL 级事实裁判扩展到完整志愿项，进一步检查专业、学校、年份、省份、批次、选科、预算和风险标签的一致性；同时保留 transcripts、reports、evidence 和 SHA256 审计，使论文结果能够持续复现。

## 7.7 最终结论

本文最终形成了一条从工程原型到可评测决策 Agent 的研究主线。v1 `gaokaollmmodel` 通过 Agentic RAG 跑通高考志愿咨询系统，积累了状态机编排、混合检索、用户画像、冲稳保推荐和防幻觉校验经验；v2 在此基础上进一步提出冰山画像 Benchmark 和证据驱动 Pareto 谈判 Agent，将高考志愿咨询中的动态约束放宽转化为可运行、可评分、可审计的多轮评测任务。

从贡献结构看，本文的主贡献是双重的：Benchmark 贡献在于冰山画像 + 多轮沙盒 + 事实/过程联合评价；Agent 贡献在于 `major_geo_relax` 与 `risk_band_relax` 支撑的证据驱动 Pareto 谈判。双实验结果表明，在保持 0.000 幻觉率的前提下，`app_pareto` 相比 `hard_constraint` 在专业+地域联合放宽和风险偏好放宽两类任务上均显著提升了偏好启发效果。

因此，本文不是简单构建一个能回答问题的高考志愿问答系统，而是进一步探索了如何让高风险教育决策 Agent 在真实数据约束下被严格评测、被逐例审计，并通过可核验证据帮助用户发现更优或更完整的志愿选择空间。
