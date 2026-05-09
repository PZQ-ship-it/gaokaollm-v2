# 毕业论文方法与实验章节正文草稿

本文档是毕业设计论文“方法设计”与“实验验证”章节的正文母版，材料来自当前项目中已经完成并通过审计的 Agent+Benchmark 闭环。本文不新增实验结论，所有指标均引用现有可审计产物：

- `gaokaollm_bench/outputs/thesis_agent_benchmark_contribution.md`
- `gaokaollm_bench/outputs/agent_benchmark_major_geo_v1_summary.md`
- `gaokaollm_bench/outputs/agent_benchmark_major_geo_v1_evidence.md`
- `gaokaollm_bench/outputs/thesis_artifact_audit.md`
- `gaokaollm_bench/outputs/benchmark_methodology.md`
- `gaokaollm_bench/outputs/major_tree_methodology.md`

## 1. 研究问题与总体方案

高考志愿咨询并不是一个单轮问答任务。考生在真实咨询中经常会表达强硬的显性偏好，例如“只读临床医学”“专业不对的学校再好也不考虑”“只考虑本省”等。这些偏好中既包含真实不可妥协条件，也包含由于信息不足形成的初始锚定。如果推荐系统只顺从用户显性红线，可能会错过更优且可达的志愿集合；如果系统脱离事实数据进行劝说，又会引入虚假学校、错误分数和不可达推荐等风险。

因此，本研究将任务定义为“真实招生数据约束下的多轮偏好妥协评测”。系统目标不是生成看似合理的泛化建议，而是在真实 PostgreSQL 招生数据中找到可核验的反事实志愿证据，并通过多轮对话帮助用户理解放宽部分约束后的收益。

论文贡献采用“双贡献”结构：

- Benchmark 贡献：构建面向高考志愿 Agent 的冰山画像、多轮沙盒与事实/过程联合评价框架。
- Agent 贡献：构建证据驱动的 Pareto 妥协谈判 Agent，并通过 `major_geo_relax` 支持专业与地域的联合放宽探测。

建议绘图 1：系统总体架构图。图中展示真实招生数据库、benchmark 数据生成、用户模拟器、被测 Agent、事实裁判与过程裁判之间的数据流。

## 2. Benchmark 方法

本研究中的 benchmark 不以静态题目正确率为核心，而是评估 Agent 是否能在多轮对话中发现用户显性偏好背后的隐性妥协空间。其核心思想是“冰山画像”：用户说出口的是显性红线，水面下则是只有在看到充分证据后才可能接受的妥协条件。

Benchmark 的生成过程从真实数据库出发。数据生成器先在当前硬约束下查询可达志愿，再在放宽地域、专业或专业+地域联合约束后查询候选集合。如果放宽后出现学校层次或志愿集合质量上的跃迁，则将该 gap 逆向写入 persona 的隐藏妥协条件。这样得到的测试样本不是人工编造的学校与分数，而是来自真实录取数据的可审计反事实样本。

专业约束放宽使用专业树层级策略。系统先尝试同叶子簇内的真实专业名变体，再扩展到同父近邻、上层大类、probe 邻近大类，最后退化为无专业限制。专业树和 probe 在本论文中属于 benchmark 基础设施，用于支持专业放宽过程的可解释性和可复现性，而不是本轮 Agent 主贡献本身。

| Benchmark 模块 | 主要职责 | 论文作用 |
|---|---|---|
| 冰山画像 | 区分 `explicit_red_lines` 与 `implicit_flexibilities` | 建模显性偏好和隐性妥协 |
| 真实 DB gap | 从 PostgreSQL 招生数据中发现放宽约束后的跃迁 | 降低人工构造样本的幻觉风险 |
| 专业树层级放宽 | 逐级扩展专业约束，支持从近到远的妥协路径 | 提供可解释的专业放宽算法 |
| 多轮沙盒 | 让被测 Agent 与模拟用户进行受控对话 | 评估偏好启发过程 |
| 事实/过程联合评价 | 检查幻觉率、启发成功和 Pareto gain | 同时约束事实正确性与交互质量 |

建议绘图 2：Benchmark 流程图。图中依次展示真实数据库 gap 发现、persona 生成、沙盒对话、transcript 持久化、事实裁判与过程裁判。

## 3. Agent 方法

业务 Agent 采用 LangGraph 编排，核心流程为：

```text
gatekeeper -> radar -> negotiator
```

其中，`gatekeeper` 负责从用户话语中抽取分数、省份、专业、预算和选科等约束，并查询当前硬约束下的 baseline 结果；`radar` 负责调用确定性 SQL 探针，寻找放宽约束后的 Pareto 机会；`negotiator` 负责将真实查询结果组织成可解释的谈判回复，向用户展示学校名、专业名和最低分等可核验证据。

本轮 Agent 贡献的关键算法是 `major_geo_relax`。该能力同时放宽专业与地域约束，但保留分数、预算和选科等事实约束。换言之，系统不会为了劝服用户而无条件扩大搜索空间，而是在“仍然可达”的前提下，探测如果用户同时接受跨省和专业放宽，是否能够获得更高层次的志愿集合。

需要强调的是，`major_geo_relax` 不读取 benchmark 的 `implicit_flexibilities` 或 `volunteer_set`。它只使用用户显式话语抽取出的约束和真实数据库查询结果。因此，Agent 的提升不是因为读取了隐藏答案，而是因为将 benchmark 公开的方法学策略转化为业务 Agent 的推荐探测能力。

| Agent 节点 | 输入 | 输出 | 作用 |
|---|---|---|---|
| `gatekeeper` | 用户自然语言话语 | 结构化约束、baseline 查询结果 | 确认硬约束和当前可达空间 |
| `radar` | 用户约束、baseline 结果 | `geo_relax`、`major_relax`、`major_geo_relax` 等机会 | 探测 Pareto 妥协空间 |
| `negotiator` | 真实候选集合和对话状态 | 面向用户的证据化回复 | 用学校、专业、最低分进行谈判 |

与之对照，`hard_constraint` baseline 只报告当前显性硬约束下的可达志愿，不主动进行专业或地域放宽谈判，也不产生 `major_geo_relax`。因此，它代表“迎合显性红线”的保守系统。

## 4. 实验设置

主实验使用 `agent_benchmark_major_geo_v1` 结果包。该实验在 10 条真实 DB 生成的冰山画像上，对比 `app_pareto` 与 `hard_constraint` 两个目标系统。评测使用 offline deterministic 模式，以保证论文第一版结果稳定可复现。

| 项目 | 设置 |
|---|---|
| Persona 数据 | `gaokaollm_bench/sample_data/iceberg_personas_major_hierarchy_real_db_10.json` |
| Case 数量 | 10 |
| 被测目标 | `app_pareto`、`hard_constraint` |
| 最大轮次 | 3 |
| Simulator model | `Pro/moonshotai/Kimi-K2.6` |
| Judge model | `Pro/moonshotai/Kimi-K2.6` |
| 评测模式 | Offline deterministic |
| 默认省份 | 浙江 |
| 数据库 | 本地 PostgreSQL 快照，`postgresql://postgres@127.0.0.1:55432/gaokao_recommendation` |
| 可审计产物 | transcripts、reports、summary、evidence、audit |

实验产物已经通过 `thesis_artifact_audit.md` 审计。审计结果为 `Overall: PASS`，并确认 README、主实验 summary、逐例报告、transcript、论文母版和逐例证据文档均存在。

## 5. 实验结果与分析

聚合结果如下。该表与 `agent_benchmark_major_geo_v1_summary.md` 和 `thesis_artifact_audit.md` 中的指标一致。

| Target | Cases | Success | Elicitation Success | Mean Pareto Gain | Mean Hallucination | Avg Turns |
|---|---:|---:|---:|---:|---:|---:|
| `app_pareto` | 10 | 9 | 0.900 | 0.900 | 0.000 | 5.20 |
| `hard_constraint` | 10 | 0 | 0.000 | 0.000 | 0.000 | 7.00 |

结果显示，`app_pareto` 在 10 个 case 中成功 9 个，`hard_constraint` 成功 0 个；也就是 10 个 case、9 个 app 成功、1 个 app 失败、baseline 0 成功。`app_pareto` 的 `elicitation_success` 为 0.900，`mean_pareto_gain` 为 0.900，而 `hard_constraint` 两项均为 0.000。这说明仅报告当前硬约束下的可达志愿，无法触发用户隐藏的可妥协条件；相反，基于真实 DB 证据展示联合放宽后的志愿集合，可以显著提升多轮偏好启发效果。

两类系统的 `mean_hallucination_rate` 均为 0.000，说明 `app_pareto` 的收益不是通过虚构学校、错误分数或不可达推荐获得的。平均轮次方面，`app_pareto` 为 5.20，`hard_constraint` 为 7.00，表明有效的反事实证据能够更早结束多轮僵持。

从论文解释角度看，`app_pareto` 的优势来自 `major_geo_relax` 提供的证据驱动谈判路径。当用户坚持“只读临床医学”时，系统不直接否定该偏好，而是展示如果同时放宽专业与地域，可以换取哪些真实可达的高层次学校与专业。该过程符合 Pareto 妥协的定义：在保留分数、选科等事实约束的前提下，寻找相对原始锚定更优且用户可能接受的志愿集合。

## 6. 逐例证据与失败样本

逐例证据见 `agent_benchmark_major_geo_v1_evidence.md`。该附录列出了每个 case 的成功状态、轮次、幻觉率和 `major_geo_relax` 候选。成功 case 中，Agent 的候选均来自 transcript 的 `internal_state.pareto_opportunities.major_geo_relax` 或 `recommended_schools`，包含学校、省份、专业、年份、最低分和 tier 等字段。

例如，在 `real-db-set-浙江-542-001` 中，用户显式表达“542 分，只想读临床医学，专业不对的学校再好也不考虑”。`app_pareto` 给出如东北农业大学动物科学、最低分 541，西南交通大学城市设计、最低分 492 等可达候选。用户模拟器在看到命中隐藏志愿集合的学校和分数证据后接受该方向。

唯一失败样本是 `real-db-set-浙江-569-009`。该样本中，persona 的隐藏目标要求 stage 5，即“去除专业限制”的任意专业志愿集合；但 `app_pareto` 实际停留在 stage 4“大类兜底”，给出了石河子大学预防医学、南京中医药大学护理学、成都中医药大学康复治疗学等医学相关候选。由于这些候选与隐藏 `volunteer_set` 在学校层面和学校-专业二元组层面均未命中，deterministic judge 判定该 case 未成功。

这个失败样本具有论文价值：它表明当前系统已经形成可复现闭环，但并非 100% 成功。后续优化方向不是简单扩大宣传口径，而是改进放宽阶段选择策略，让 Agent 在较近专业大类候选无法命中隐藏妥协时，继续退到更远的 `any_major` 证据集合。

## 7. 局限性与后续工作

当前实验是毕业论文第一版主实验，样本量为 10，足以证明 Agent+Benchmark 闭环可复现，但尚不能作为大规模 leaderboard。后续可扩展更多分数段、专业类型、地域偏好和省份快照，以检验结论的稳健性。

本次实验使用 offline deterministic judge，优点是稳定、可复现、便于论文审计；局限是无法完全覆盖真实 LLM judge 或真实用户咨询中的细粒度行为。后续可以引入多裁判一致性、人类抽样复核和真实咨询日志校准。

事实裁判当前重点检查学校可达性和分数证据，对专业、年份、省份、批次、选科等联合条件的 SQL 校验仍可增强。未来可以将 hallucination 检查从学校级扩展为完整志愿项级别，进一步提高推荐证据的可信度。

此外，当前 `pareto_gain` 主要基于学校 tier 和隐藏志愿集合命中，尚未纳入城市偏好、就业预期、风险梯度和家庭预算等多目标收益。未来可以将 Pareto gain 扩展为多目标评价函数，使 Agent 的妥协谈判更贴近真实高考志愿填报决策。

## 可迁移到论文中的章节安排

| 论文章节 | 建议标题 | 对应本文内容 |
|---|---|---|
| 第三章 | 高考志愿多轮偏好妥协评测框架 | 第 1、2 节 |
| 第四章 | 证据驱动的 Pareto 谈判 Agent 设计 | 第 3 节 |
| 第五章 | 实验设计与结果分析 | 第 4、5、6 节 |
| 第六章 | 总结与展望 | 第 7 节 |

正文写作时，建议将 `benchmark_methodology.md` 作为第三章细节来源，将 `thesis_agent_benchmark_contribution.md` 作为贡献概括来源，将 `agent_benchmark_major_geo_v1_evidence.md` 和 `thesis_artifact_audit.md` 作为第五章实验可信度支撑。
