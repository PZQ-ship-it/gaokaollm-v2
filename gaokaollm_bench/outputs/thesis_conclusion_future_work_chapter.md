# 第 7 章 总结与展望

本文档是毕业论文第 7 章“总结与展望”的正文母版，用于收束前文从 v1 工程原型到 v2 数据 + Agent + Benchmark 闭环的完整主线。本文不新增实验结论，只整理当前已有论文材料和七组 Agent-vs-Baseline 实验结果。

当前论文最终主线为：v1 `gaokaollmmodel` 是 Agentic RAG 工程原型与问题发现；v2 是最终主贡献，形成“数据贡献 + Agent 贡献 + Benchmark 贡献”的三层闭环。`major_geo_v1 + risk_band_v1` 是论文第一版主实验，`school_strength_v1`、`tuition_value_v1`、`major_quality_v1`、`employment_outcome_v1`、`region_tree_v1` 是扩展实验，用于证明数据证据层和 Agent 框架的可扩展性。

## 7.1 全文工作总结

本文围绕高考志愿咨询这一高风险、强约束、强偏好的教育决策场景，研究如何构建一个既能利用真实招生数据，又能通过多轮对话发现偏好妥协空间的智能体系统。与一般大模型问答任务不同，高考志愿咨询不仅要求回答自然语言问题，还要求系统在学校、专业、分数、位次、选科、学费、风险、质量和就业等约束下，给出可核验、可追溯、可解释的建议。

全文工作可以分为两个阶段。

第一阶段是 v1 `gaokaollmmodel` Agentic RAG 原型系统。该阶段完成了面向高考志愿咨询的工程闭环，包括 LangGraph/状态机工作流、意图识别、Redis 用户画像、混合检索、BGE-M3 embedding、BCEmbedding 重排、`1:3:9` 冲稳保推荐、神经-符号一致性校验和 SSE 流式响应。v1 证明了高考志愿咨询可以被构建为一个可运行的 Agentic RAG 系统，也暴露出传统工程原型难以严格证明偏好妥协效果的问题。

第二阶段是 v2 数据 + Agent + Benchmark 闭环。该阶段将研究重点从“系统能否回答志愿问题”推进到“系统能否在真实数据库约束下，通过证据驱动谈判触发用户可接受的 Pareto 妥协”。v2 构建了 PostgreSQL 招生事实与标准化证据层，设计了 前置语义归一层、约束解析器、LLM 引导的机会规划器、确定性证据探针和证据谈判器组成的轻量 MAS/多角色 Agent，并用冰山画像、多轮沙盒、事实/过程联合评价和逐例 evidence 验证 Agent 相对 `hard_constraint` baseline 的提升。

因此，本文最终不是两个割裂项目的简单拼接，而是一条自然演进的研究主线：v1 解决工程可用性并发现评测缺口，v2 将该缺口收敛为可生成、可运行、可评价、可审计的数据驱动偏好妥协任务。

## 7.2 数据贡献总结

本文的数据贡献在于将高考志愿咨询所需的多源事实整理为 Agent 可查询、Benchmark 可验证、Transcript 可追溯的证据层。它不是简单堆叠数据库表，而是围绕 Pareto 谈判需要，将录取事实、风险、成本、专业质量、就业结果和地域树节点转化为结构化证据。

| 数据层 | 核心对象 | 支撑能力 |
| --- | --- | --- |
| 招生事实快照 | `admission_scores`、`school_admission_scores`、`score_rank_segments`、`batch_lines` | 最低分、最低位次、批次线、分数/位次可达性 |
| 招生计划与学费 | `admission_plans.tuition` | `tuition_value_relax` 的学费增量与预算性价比证据 |
| 学校与专业基础维表 | `schools`、`majors`、专业树 | 地域、学校层次、专业层级放宽和相近专业搜索 |
| 专业质量标准化层 | `school_major_quality_profiles` | `major_quality_relax` 的 `quality_score`、`quality_gain`、专业排名、学科评估、特色/重点/满意度证据 |
| 就业结果标准化层 | `major_employment_outcome_profiles` | `employment_outcome_relax` 的 `outcome_score`、`outcome_gain`、就业排名、行业、岗位和薪资证据 |
| 地域树 reviewed v1 | `region_geo_tree_reviewed_v1.json`、`region_urban_tier_tree_reviewed_v1.json` | `region_tree_relax` 的 `geo_block_relax`、`urban_tier_relax`、地域树节点和树置信度证据 |

数据贡献的核心价值是使 Agent 的每一次谈判都有事实来源，也使 Benchmark 可以检查推荐是否真实存在、是否满足硬约束、是否提供了足够证据。没有这层数据基础，所谓“偏好妥协”就容易退化为不可验证的说服话术。

## 7.3 Agent 贡献总结

本文的 Agent 贡献是证据驱动 Pareto 谈判。v2 业务 Agent 采用 `前置语义归一层 -> 约束解析器 -> LLM 引导的机会规划器 -> 确定性证据探针 -> 证据谈判器` 的轻量 MAS/多角色 Agent 架构，但论文中需要谨慎表述：它是基于角色分工的工作流式 MAS，而不是完全自治的多智能体系统。

| 角色 | 主要职责 | 论文意义 |
| --- | --- | --- |
| `gatekeeper` | 从用户显式话语中抽取分数、省份、专业、选科、预算、风险、质量和就业偏好，并查询硬约束 baseline | 确认用户显性约束和当前可达空间 |
| `radar` | 调用确定性 SQL probe，寻找各类 Pareto opportunities | 将数据证据转化为可谈判机会 |
| `negotiator` | 对比 baseline 与 opportunities，用真实候选组织解释性回复 | 将候选证据转化为用户可理解的妥协建议 |

当前 Agent 支持七类动态放宽或证据探测能力。

| 能力 | 论文定位 | 放宽或探测对象 | 输出证据 |
| --- | --- | --- | --- |
| `major_geo_relax` | 主能力 | 专业 + 地域联合放宽 | 学校、专业、省份、最低分、最低位次、学校层次、专业树阶段 |
| `risk_band_relax` | 主能力 | “只求稳/不要冲”的风险偏好 | `score_margin`、`rank_gap`、`chong/wen/bao` 风险层级、最低分/位次 |
| `strength_relax` | 扩展能力 | 学校/学科实力 | 排名、评级、最低分、最低位次 |
| `tuition_value_relax` | 扩展能力 | 学费预算上限的小幅放宽 | 学费、学费增量、最低分、学校层次或排名收益 |
| `major_quality_relax` | 扩展能力 | 专业质量证据增强 | `quality_score`、`quality_gain`、专业排名/学科评估/特色/重点/满意度证据 |
| `employment_outcome_relax` | 扩展能力 | 就业导向与相近专业就业结果 | `employment_rank`、`top_industry`、`job_distribution`、`salary_distribution`、`outcome_score`、`outcome_gain` |
| `region_tree_relax` | 扩展能力 | reviewed 地域树层级放宽 | `geo_block_relax`、`urban_tier_relax`、源/目标地域节点、树置信度、最低分/位次 |

这些能力的共同点是：Agent 不通过泛化说服话术强迫用户改变偏好，而是在保留分数、选科、资格等硬约束的前提下，展示“如果放宽某个可谈判偏好，可以换来什么真实收益”。用户是否接受妥协由多轮对话中的证据触发过程决定。

## 7.4 Benchmark 贡献总结

本文的 Benchmark 贡献是面向高考志愿偏好妥协任务构建了一套冰山画像多轮评测框架。该框架不再把评测对象限制为单轮问答正确率，而是关注 Agent 是否能在多轮对话中发现用户显性红线背后的隐性妥协空间。

Benchmark 设计包含四个关键部分。

第一，冰山画像将用户偏好拆分为显性红线和隐性妥协条件。用户对 Agent 暴露的是对话中说出的分数、省份、专业、选科、预算、风险和就业偏好；隐藏字段 `implicit_flexibilities` 与 `volunteer_set` 只作为 simulator 与 evaluator 的 ground truth。Agent 不读取 `implicit_flexibilities` 或 `volunteer_set`。

第二，真实 DB gap 生成机制从 PostgreSQL 招生数据和标准化证据层中发现约束放宽后的可达志愿集合。这样生成的 persona 不依赖人工编造学校、专业、最低分或就业证据，而是把真实数据库中的反事实机会写入评测样本。

第三，多轮沙盒连接 target agent 与模拟用户，记录 turn、reply、internal_state、transcript、report 和 summary，使偏好启发过程能够被逐例复盘。

第四，事实/过程联合评价同时检查 factual hallucination 与 elicitation success。事实评价约束学校、专业、最低分、最低位次、学费、质量、就业和地域树证据；过程评价检查 Agent 是否真正触发了隐藏妥协，而不是只顺从显性红线。

这些机制共同构成本文的 Benchmark 贡献：冰山画像 + 多轮沙盒 + 事实/过程联合评价 + 逐例 evidence。它让“偏好妥协”从一个难以验证的主观叙事变成可运行、可复现、可追溯的实验任务。

## 7.5 实验结果总结

本文第一版主实验包含 `major_geo_v1` 与 `risk_band_v1` 两组 Agent-vs-Baseline 离线评测。扩展实验包含 `school_strength_v1`、`tuition_value_v1`、`major_quality_v1`、`employment_outcome_v1`、`region_tree_v1` 五组数据证据维度实验。所有实验均对比 `app_pareto` 与 `hard_constraint`：前者表示接入证据驱动 Pareto 谈判能力的业务 Agent，后者表示只报告当前显性硬约束下可达志愿、不主动谈判的 baseline。

斜杠格式依次为：

```text
elicitation_success_rate / mean_pareto_gain / mean_hallucination_rate / avg_turns
```

| 实验 | 类型 | `app_pareto` | `hard_constraint` | 结论 |
| --- | --- | ---: | ---: | --- |
| `major_geo_v1` | 主实验 | `0.900 / 0.900 / 0.000 / 5.20` | `0.000 / 0.000 / 0.000 / 7.00` | Agent 能用专业+地域联合放宽证据触发 9/10 个隐性妥协 |
| `risk_band_v1` | 主实验 | `1.000 / 3.000 / 0.000 / 5.00` | `0.000 / 0.000 / 0.000 / 15.00` | Agent 能把单一保守偏好扩展为冲稳保组合 |
| `school_strength_v1` | 扩展实验 | `1.000 / 15.000 / 0.000 / 5.00` | `0.000 / 0.000 / 0.000 / 11.00` | 学校/学科实力证据可接入同一谈判闭环 |
| `tuition_value_v1` | 扩展实验 | `1.000 / 1.000 / 0.000 / 5.00` | `0.000 / 0.000 / 0.000 / 11.00` | 学费字段可支撑小幅超预算换收益的谈判 |
| `major_quality_v1` | 扩展实验 | `1.000 / 16.000 / 0.000 / 5.00` | `0.000 / 0.000 / 0.050 / 11.00` | 专业质量标准化层可支撑专业级跃迁证据 |
| `employment_outcome_v1` | 扩展实验 | `1.000 / 49.000 / 0.000 / 3.00` | `0.000 / 0.000 / 0.000 / 11.00` | 就业结果标准化层可支撑就业排名、行业、岗位和薪资证据谈判 |
| `region_tree_v1` | 扩展实验 | `1.000 / 1.000 / 0.000 / 3.00` | `0.000 / 0.000 / 0.000 / 11.00` | reviewed 地域树可支撑地理板块和城市层级证据谈判 |

从主实验看，`app_pareto` 在 `major_geo_v1` 中达到 0.900 成功率，在 `risk_band_v1` 中达到 1.000 成功率，而 `hard_constraint` 在两组主实验中均为 0.000。由于两组主实验的 `mean_hallucination_rate` 均为 0.000，说明 Agent 的收益并非来自编造学校或分数，而是来自对真实 DB gap 的有效利用。

`major_geo_v1` 并非 100% 成功。失败样本为 `real-db-set-浙江-569-009`。该样本中 Agent 停留在较近的医学相关大类兜底候选上，而未命中 hidden `volunteer_set` 所需的更远 `any_major` 集合。保留这一失败样本有助于说明本文实验结论是可审计的，而不是只报告成功案例。

五组扩展实验说明，本文框架可以随着数据层扩展而扩展。`tuition_value_v1` 把 `admission_plans.tuition` 转化为预算谈判证据；`major_quality_v1` 把专业排名、学科评估、特色专业、重点专业和满意度聚合到 `school_major_quality_profiles`；`employment_outcome_v1` 把专业就业画像转化为 `major_employment_outcome_profiles`；`region_tree_v1` 把 reviewed 地域树接入 `region_tree_relax`；`school_strength_v1` 则作为较粗粒度实力证据的过渡实验。扩展实验不替代主实验，而是支撑“数据贡献可扩展”的论文论点。

在七组实验之外，`multi_axis_v1` 与 `multi_axis_v2` 作为 Benchmark 压力测试补充检验多轴隐藏妥协。两者均包含 `major_geo_risk`、`quality_tuition`、`employment_region` 三类 profile，各 10 个 case，要求两个隐藏放宽轴都命中才算成功。`multi_axis_v1` 是历史压力测试版本，结果为 `app_pareto 0.533 / 1.133 / 0.029 / 7.67` vs `hard_constraint 0.000 / 0.000 / 0.000 / 13.00`，逐 profile 成功分布为 1/10、5/10、10/10。`multi_axis_v2` 是轴一致性修正版，结果为 `app_pareto 0.367 / 1.133 / 0.005 / 9.33` vs `hard_constraint 0.000 / 0.000 / 0.008 / 13.00`，逐 profile 成功分布为 6/10、5/10、0/10。该结果说明，多轴 benchmark 能暴露单轴实验看不出的证据编排瓶颈；v2 尤其揭示了 `employment_region` 中就业证据与地域树证据的联合组织不足。

上述七组 `app_pareto` 实验结果均属于 v2 主线，不属于 v1 `gaokaollmmodel` 原型系统的直接性能结果。v1 是工程原型与问题发现，v2 是最终主贡献。

## 7.6 局限性

本文仍存在若干局限。

第一，样本规模较小。当前每组实验均使用 10 条 persona，适合证明数据 + Agent + Benchmark 闭环可复现、可审计，但尚不能作为大规模 leaderboard。后续需要扩展更多分数段、省份、专业类型和用户偏好分布，检验结论稳健性。

第二，当前实验主要依赖 offline deterministic judge。该设置的优点是稳定、可重复、便于论文核验；局限是无法完全覆盖真实 LLM judge 或真实用户咨询中的细粒度行为。后续应引入多裁判一致性、人类抽样复核和真实咨询日志校准。

第三，当前数据快照以浙江 PostgreSQL 招生数据为主。高考志愿规则具有省份差异，选科、批次、计划和录取模式在不同地区可能不同。因此，本文结论还需要在更多省份快照和更多年份数据上验证。

第四，事实裁判粒度仍可增强。现阶段事实评价重点约束学校、专业、最低分、最低位次、学费、质量和就业等核心证据，但对年份、省份、批次、选科、同校去重和组合风险等联合条件仍可进一步细化。未来可以将 hallucination 检查从学校级扩展到完整志愿项级别。

第五，当前 Pareto gain 仍是确定性指标。它主要基于隐藏志愿集合命中、学校 tier、风险组合覆盖、质量得分、就业结果等信息，尚未充分纳入真实用户效用、家庭预算弹性、长期职业偏好和录取概率等多目标因素。

第六，多轴隐藏妥协的证据编排仍不充分。`multi_axis_v2` 在修正画像轴一致性后，`major_geo_risk` 提升到 6/10，`quality_tuition` 保持 5/10，但 `employment_region` 为 0/10，说明现有 negotiator 在同时表达就业结果证据与地域树证据时仍容易遗漏其中一条轴。这不是新的业务放宽算法问题，而是多证据链组织、排序和对话节奏控制问题。

## 7.7 后续工作

后续工作可以从四个方向展开。

第一，构造城市收益指标。当前系统不能仅凭 `schools.city` 字段把城市偏好写成 Pareto gain。后续如果要做城市跃迁，需要引入可核验的城市就业机会、生活成本、产业匹配或地域发展指标。

第二，扩展真实用户校准。当前冰山画像由真实 DB gap 反推生成，适合可控实验；后续可通过真实咨询日志、问卷或访谈校准用户在专业、地域、预算和就业之间的真实妥协行为。

第三，升级概率化录取风险模型。当前风险层级是确定性规则，优点是可解释、易审计；未来可在保持可解释性的前提下，研究录取概率估计、位次密度和计划变动是否能被透明解释。

第四，扩展多省份泛化验证。当前结果基于浙江数据快照，后续可接入更多省份和更多批次，验证数据标准化层、Agent probe 和 Benchmark 画像生成是否具有跨区域适应性。

第五，改进多轴证据编排。`multi_axis_v2` 已经说明两个隐藏妥协轴同时存在时，Agent 不只需要“发现机会”，还需要在一轮或多轮回复中清晰组织两条证据链。后续可围绕 opportunity 选择、回复结构、轴间优先级和 process judge 诊断做优化，但不需要把它包装成新的数据维度。

需要强调的是，学费放宽、专业质量映射、就业导向放宽和地域树放宽已经完成第一版闭环，不再作为“未实现能力”描述。它们在论文中应写作扩展实验，用于支撑数据贡献和框架可扩展性。

## 7.8 最终结论

本文最终形成了一条从工程原型到可评测决策 Agent 的研究主线。v1 `gaokaollmmodel` 通过 Agentic RAG 跑通高考志愿咨询系统，积累了状态机编排、混合检索、用户画像、冲稳保推荐和防幻觉校验经验；v2 在此基础上进一步提出数据 + Agent + Benchmark 三层闭环，将高考志愿咨询中的动态约束放宽转化为可运行、可评分、可审计的多轮评测任务。

从贡献结构看，本文的最终贡献包括三部分：数据贡献在于构建 PostgreSQL 招生事实、专业质量和就业结果等可核验证据层；Agent 贡献在于基于 `前置语义归一层 -> 约束解析器 -> LLM 引导的机会规划器 -> 确定性证据探针 -> 证据谈判器` 的轻量 MAS/多角色 Agent 执行证据驱动 Pareto 谈判；Benchmark 贡献在于用冰山画像、多轮沙盒和事实/过程联合评价检验 Agent 是否真正触发隐藏偏好妥协。

主实验 `major_geo_v1 + risk_band_v1` 表明，在保持 0.000 幻觉率的前提下，`app_pareto` 相比 `hard_constraint` 在专业+地域联合放宽和风险偏好放宽两类任务上均显著提升了偏好启发效果。五组扩展实验进一步说明，同一框架可以接入学校/学科实力、学费预算、专业质量、就业结果和地域树等数据证据维度。

`multi_axis_v2` 进一步表明，Benchmark 不仅可以验证单一放宽轴，也可以构造更接近真实咨询的多轴隐藏妥协压力测试。该测试不替代主实验，也不改变七组实验主线；它作为诊断工具揭示了多证据链编排仍是后续 Agent 改进重点。`multi_axis_v1` 保留为历史压力测试版本，用于说明修正轴一致性前后的诊断差异。

因此，本文不是简单构建一个能回答问题的高考志愿问答系统，而是探索了如何让高风险教育决策 Agent 在真实数据约束下被严格评测、被逐例追溯，并通过可核验证据帮助用户发现更优或更完整的志愿选择空间。
