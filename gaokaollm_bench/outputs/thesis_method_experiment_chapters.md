# 毕业论文方法与实验章节正文母版

本文档是毕业设计论文“方法设计”与“实验验证”章节的正文母版。与早期的 Agent + Benchmark 口径相比，当前项目已经形成更完整的“数据 + Agent + Benchmark”三层贡献：底层使用可查询、可回填、可审计的 PostgreSQL 招生数据与专业质量数据；中层使用 LangGraph Agent 进行证据驱动的 Pareto 谈判；上层使用冰山画像、多轮沙盒和事实/过程联合评价验证 Agent 是否真正触发隐性偏好妥协。

本文不新增实验结论，只整理当前已有产物：

- `gaokaollm_bench/outputs/agent_benchmark_major_geo_v1_summary.md`
- `gaokaollm_bench/outputs/agent_benchmark_major_geo_v1_evidence.md`
- `gaokaollm_bench/outputs/agent_benchmark_risk_band_v1_summary.md`
- `gaokaollm_bench/outputs/agent_benchmark_risk_band_v1_evidence.md`
- `gaokaollm_bench/outputs/agent_benchmark_school_strength_v1_summary.md`
- `gaokaollm_bench/outputs/agent_benchmark_tuition_value_v1_summary.md`
- `gaokaollm_bench/outputs/agent_benchmark_major_quality_v1_summary.md`
- `gaokaollm_bench/outputs/agent_benchmark_employment_outcome_v1_summary.md`
- `gaokaollm_bench/outputs/thesis_data_agent_benchmark_extension_evidence.md`
- `gaokaollm_bench/outputs/benchmark_methodology.md`
- `gaokaollm_bench/outputs/major_tree_methodology.md`
- `gaokaollm_bench/outputs/dynamic_decision_considerations_roadmap.md`
- `gaokaollm_bench/放宽与跃迁.md`

## 1. 研究问题与总体方案

高考志愿咨询不是静态问答任务。真实咨询中，考生往往会先给出强硬的显性条件，例如“只考虑本省”“只读这个专业”“不要冲”“学费别太贵”。这些表达里既有确实不能突破的硬约束，也有由于信息不足而暂时形成的偏好锁定。一个面向志愿填报的大模型系统如果只迎合显性红线，就可能错过更高质量、更合适且仍可达的志愿；如果脱离招生事实盲目劝说，又会引入学校、专业、分数和位次层面的幻觉风险。

因此，本文将研究问题定义为：在真实招生数据约束下，构建并评测一个能够通过多轮对话发现隐性妥协空间的高考志愿 Agent。系统不是简单生成更多学校，而是用可核验的数据证据回答一个反事实问题：如果用户在某个偏好维度上做有限放宽，是否能获得更优的志愿组合或更有价值的专业/学校证据。

论文贡献采用“数据 + Agent + Benchmark”三层结构。

| 贡献层次 | 核心内容 | 论文作用 |
|---|---|---|
| 数据贡献 | PostgreSQL 招生快照、分数/位次、批次线、学费字段、专业树、专业质量标准化层、就业结果标准化层 | 为 Agent 和 benchmark 提供可核验事实基础 |
| Agent 贡献 | `gatekeeper -> radar -> negotiator`，支持 `major_geo_relax`、`risk_band_relax`、`tuition_value_relax`、`major_quality_relax`、`employment_outcome_relax` 等证据驱动 Pareto 谈判 | 证明业务 Agent 能主动提出有事实依据的偏好妥协方案 |
| Benchmark 贡献 | 冰山画像、多轮沙盒、事实/过程联合评价、`app_pareto` vs `hard_constraint` 对照 | 证明改进不是主观叙事，而是可复现实验结果 |

本文第一版主实验仍为 `major_geo_v1 + risk_band_v1`。其中，`major_geo_v1` 验证专业与地域联合放宽，`risk_band_v1` 验证从“只求稳”到 `chong/wen/bao` 冲稳保组合的风险偏好放宽。`school_strength_v1`、`tuition_value_v1`、`major_quality_v1`、`employment_outcome_v1` 作为扩展实验，用于证明同一框架可以接入新的数据证据维度，支撑论文的数据贡献和方法可扩展性。

建议绘图 1：系统总体架构图。图中展示 PostgreSQL 数据层、数据生成器、冰山画像、被测 Agent、多轮沙盒、事实裁判、过程裁判和结果产物之间的数据流。

## 2. 数据层设计

数据层是本文区别于普通大模型问答系统的基础。所有推荐、放宽和评测结论都必须能回到 PostgreSQL 快照、专业树或标准化质量表中找到证据。Agent 不依赖隐藏 persona 字段，不读取 `implicit_flexibilities` 或 `volunteer_set`；这些字段只作为 benchmark evaluator 的 ground truth 使用。

### 2.1 招生事实数据

核心招生事实来自本地 PostgreSQL 快照。其作用如下。

| 数据表或字段 | 主要信息 | 支撑的证据 |
|---|---|---|
| `admission_scores` | 学校-专业录取最低分、最低位次、年份、批次 | 判断某个学校专业是否可达，支撑专业、地域和质量放宽 |
| `school_admission_scores` | 学校层面录取分数线 | 作为学校可达性和 baseline 查询的补充证据 |
| `score_rank_segments` | 分数与位次的对应关系 | 将考生分数转为位次，支撑 `rank_gap` 风险判断 |
| `batch_lines` | 批次线 | 过滤本科等基本录取层次，避免无意义候选 |
| `admission_plans.tuition` | 学校-专业招生计划中的年学费 | 支撑 `tuition_value_relax` 的预算/性价比谈判 |
| `schools` | 学校名称、省份、城市、层次、排名等 | 支撑地域、学校 tier、ranking 和摘要展示 |
| `majors` | 本科专业名称、门类和专业类 | 支撑专业树映射与专业质量聚合 |
| `major_employment_profiles` | 专业就业排名、就业地区、行业、岗位和薪资分布等原始画像 | 支撑就业导向放宽的数据来源 |

这些表共同约束 Agent 的事实边界。例如，风险偏好放宽必须保留省份、专业、选科和预算等硬约束，只改变风险组合；学费放宽必须保留分数、专业和选科等可达性约束，只在 `budget < tuition <= budget + 10000` 的窗口内寻找候选；专业质量放宽必须同时给出最低分/位次和质量证据，不能只说“这个学校更好”。

### 2.2 专业树与专业放宽

专业树用于把“专业放宽”从任意文本扩展变成可解释的层级策略。系统先在同叶子或近邻专业中搜索，再扩展到同父类、同门类和 probe 邻居；当近邻阶段没有可用 gap 时，才退化到更宽泛的 `any_major`。这一策略服务于 `major_geo_relax`，使 Agent 能解释“为什么这些专业是可以谈判的相近方向”，也使 benchmark 可以把放宽阶段本身纳入评估。

`major_geo_v1` 中唯一失败样本 `real-db-set-浙江-569-009` 正说明了放宽阶段选择的重要性：该样本需要退到更远的 `any_major` 才能命中隐藏志愿，而当前 Agent 停在较近的医学相关大类候选，因此没有被 deterministic judge 判为成功。

### 2.3 专业质量标准化层

为支持专业级质量证据，项目新增了不破坏原有 `school_major_strengths` 的标准化层。

| 表或视图 | 作用 | 论文意义 |
|---|---|---|
| `discipline_major_mappings` | 建立学科评估一级学科/专业类到本科专业的映射，记录 `mapping_rule`、`confidence`、`source_file` 和原始信息 | 让学科评估可以落到本科专业集合，而不是停留在粗粒度学科名 |
| `school_major_quality_signals` | 统一接入专业排名、第四轮学科评估、特色专业、重点专业、满意度等学校-专业质量信号 | 把不同来源的质量证据转成同一层事实记录 |
| `school_major_quality_profiles` | 按 `school_id + major_id` 聚合 `quality_score`、`quality_tier`、`best_major_rank`、`best_rating`、`has_key_major`、`has_featured_major`、`satisfaction_score`、`evidence_sources` | 支撑 `major_quality_relax` 的专业质量跃迁证据 |

专业质量标准化层使 Agent 可以说清楚“同样是软件工程，这所学校有什么专业质量证据”，而不仅是泛泛地说学校排名更高。当前 `major_quality_v1` 的结果表明，这一数据层可以被 Agent 和 benchmark 同时使用，从而把数据补充转化为可评测能力。

### 2.4 就业结果标准化层

就业导向放宽使用 `major_employment_profiles` 作为原始数据来源，并将其中的就业排名、就业最多地区、行业分布、岗位分布和薪资分布清洗为 `major_employment_outcome_profiles`。该标准化层保留 `major_id`、`major_name`、`employment_rank`、`top_city`、`top_industry`、`job_distribution`、`salary_distribution`、`outcome_score` 和 `evidence_sources` 等字段。

这一设计避免 Agent 直接使用自由文本作判断，而是把就业证据转化为 transcript 中可核验的结构化字段。`employment_outcome_relax` 因此可以表达为：在分数、选科和预算等硬约束不变的情况下，如果选择同专业或专业树近邻专业中就业证据更强的方案，用户是否愿意接受相应的专业或地域妥协。

## 3. Benchmark 方法

本文 benchmark 不以单轮问答正确率为核心，而是评测 Agent 是否能在多轮对话中发现并触发隐性偏好妥协。其基本样本单位是“冰山画像”：水面上是用户显性红线，水面下是只有在看到足够事实证据后才可能接受的妥协条件。

生成流程从真实 DB gap 出发。数据生成器先在显性硬约束下查询 baseline 候选，再在受控放宽某一偏好维度后查询 relaxed 候选。如果 relaxed set 在学校层次、风险组合、学费性价比、专业质量证据或就业结果证据上明显优于 baseline，则构造 persona，并把 relaxed set 写入 evaluator 使用的隐藏字段。被测 Agent 在对话中只能看到用户话语，不允许读取隐藏字段。

| Benchmark 模块 | 主要职责 | 对应论文贡献 |
|---|---|---|
| 冰山画像 | 区分 `explicit_red_lines` 与 `implicit_flexibilities` | 建模显性红线和隐性妥协 |
| 真实 DB gap | 从 PostgreSQL 数据中发现放宽后的可达跃迁 | 避免人工编造学校、分数和专业 |
| 多轮沙盒 | 让 `app_pareto` 与模拟用户交互，保存 transcript | 评估真实对话过程中的启发能力 |
| 事实裁判 | 检查推荐候选是否有学校、专业、分数、位次、学费、质量或就业证据 | 控制幻觉率 |
| 过程裁判 | 判断是否命中隐藏妥协，计算 `elicitation_success` 和 `pareto_gain` | 衡量 Pareto 谈判效果 |
| Baseline 对照 | `hard_constraint` 只响应显性硬约束，不主动谈判 | 对比“迎合红线”和“证据驱动妥协”的差异 |

建议绘图 2：Benchmark 流程图。图中依次展示真实 DB gap 发现、persona 生成、多轮沙盒、transcript 持久化、report 评分和 summary 聚合。

## 4. Agent 方法

业务 Agent 使用 LangGraph 编排，核心流程为：

```text
gatekeeper -> radar -> negotiator
```

`gatekeeper` 从用户话语中抽取分数、省份、专业、选科、预算、风险偏好、质量偏好和就业导向等约束，并查询当前硬约束下的 baseline 结果。`radar` 调用确定性 SQL 探针，寻找放宽某个偏好维度后的 Pareto 机会。`negotiator` 将候选学校、专业、最低分、最低位次、学费、风险层级、质量评分、就业排名、行业/岗位/薪资分布等证据组织成自然语言回复，引导用户理解“放宽哪一部分条件可以换来什么收益”。

当前 Agent 能力矩阵如下。

| 能力 | 放宽对象 | 保留硬约束 | 输出证据 |
|---|---|---|---|
| `major_geo_relax` | 专业 + 地域联合放宽 | 分数、选科、预算等事实约束 | 学校、专业、省份、最低分、tier/ranking、专业树阶段 |
| `risk_band_relax` | “只求稳/不要冲”的风险偏好 | 省份、专业、选科、预算等硬约束 | `score_margin`、`rank_gap`、`chong/wen/bao` 风险层级、最低分/位次 |
| `strength_relax` | 学校/学科实力偏好 | 分数、专业或相近专业、预算等约束 | 排名、评级、最低分、最低位次 |
| `tuition_value_relax` | 学费预算上限的小幅放宽 | 分数、专业、选科等硬约束 | 学费、学费增量、最低分、学校 tier/ranking 改善 |
| `major_quality_relax` | 专业质量证据增强 | 分数、专业、选科、预算等硬约束 | `quality_score`、`quality_gain`、专业排名/学科评估/特色/重点/满意度证据 |
| `employment_outcome_relax` | 就业导向与相近专业就业结果 | 分数、选科、预算等硬约束 | `employment_rank`、`top_city`、`top_industry`、`job_distribution`、`salary_distribution`、`outcome_score`、`outcome_gain` |

与之对照，`hard_constraint` baseline 只报告当前显性硬约束下的可达志愿，不主动产生 `major_geo_relax`、`risk_band_relax`、`tuition_value_relax`、`major_quality_relax` 或 `employment_outcome_relax`。因此，baseline 代表“只迎合用户显性红线”的保守系统；`app_pareto` 代表“在事实约束内寻找可谈判收益”的证据驱动系统。

## 5. 实验设置

本文第一版主实验是 `major_geo_v1` 与 `risk_band_v1`。四组扩展实验 `school_strength_v1`、`tuition_value_v1`、`major_quality_v1`、`employment_outcome_v1` 用于证明数据层可以继续接入新的证据维度，并通过同一数据 + Agent + Benchmark 管线完成闭环。

| 实验 | 类型 | Persona 数据 | 输出目录 | 主要验证点 |
|---|---|---|---|---|
| `major_geo_v1` | 主实验 | `gaokaollm_bench/sample_data/iceberg_personas_major_hierarchy_real_db_10.json` | `gaokaollm_bench/outputs/agent_benchmark_major_geo_v1/` | 专业 + 地域联合放宽 |
| `risk_band_v1` | 主实验 | `gaokaollm_bench/sample_data/iceberg_personas_risk_band_real_db_10.json` | `gaokaollm_bench/outputs/agent_benchmark_risk_band_v1/` | 从“只求稳”到冲稳保组合 |
| `school_strength_v1` | 扩展实验 | `gaokaollm_bench/sample_data/iceberg_personas_school_strength_real_db_10.json` | `gaokaollm_bench/outputs/agent_benchmark_school_strength_v1/` | 学校/学科实力证据 |
| `tuition_value_v1` | 扩展实验 | `gaokaollm_bench/sample_data/iceberg_personas_tuition_value_real_db_10.json` | `gaokaollm_bench/outputs/agent_benchmark_tuition_value_v1/` | 学费/预算性价比放宽 |
| `major_quality_v1` | 扩展实验 | `gaokaollm_bench/sample_data/iceberg_personas_major_quality_real_db_10.json` | `gaokaollm_bench/outputs/agent_benchmark_major_quality_v1/` | 专业质量标准化证据 |
| `employment_outcome_v1` | 扩展实验 | `gaokaollm_bench/sample_data/iceberg_personas_employment_outcome_real_db_10.json` | `gaokaollm_bench/outputs/agent_benchmark_employment_outcome_v1/` | 就业排名、行业、岗位和薪资证据 |

所有实验均使用 `app_pareto` 与 `hard_constraint` 两个 target。结果产物包含 transcripts、逐例 reports、`summary.json` 和 Markdown summary。主实验另有单独逐例 evidence 附录；前三组扩展实验证据整理在 `thesis_data_agent_benchmark_extension_evidence.md`，`employment_outcome_v1` 当前引用 `agent_benchmark_employment_outcome_v1_summary.md` 与输出目录中的 transcripts/reports。

## 6. 实验结果与分析

六组实验的核心指标如下。斜杠格式依次为：

```text
elicitation_success_rate / mean_pareto_gain / mean_hallucination_rate / avg_turns
```

| 实验 | `app_pareto` | `hard_constraint` | 结论 |
|---|---:|---:|---|
| `major_geo_v1` | `0.900 / 0.900 / 0.000 / 5.20` | `0.000 / 0.000 / 0.000 / 7.00` | Agent 能用联合放宽证据触发 9/10 个隐性妥协 |
| `risk_band_v1` | `1.000 / 3.000 / 0.000 / 5.00` | `0.000 / 0.000 / 0.000 / 15.00` | Agent 能把单一保守偏好扩展为冲稳保组合 |
| `school_strength_v1` | `1.000 / 15.000 / 0.000 / 5.00` | `0.000 / 0.000 / 0.000 / 11.00` | 学校/学科实力证据可接入同一谈判闭环 |
| `tuition_value_v1` | `1.000 / 1.000 / 0.000 / 5.00` | `0.000 / 0.000 / 0.000 / 11.00` | `admission_plans.tuition` 可支撑小幅超预算换收益的谈判 |
| `major_quality_v1` | `1.000 / 16.000 / 0.000 / 5.00` | `0.000 / 0.000 / 0.050 / 11.00` | `school_major_quality_profiles` 可支撑专业质量跃迁证据 |
| `employment_outcome_v1` | `1.000 / 49.000 / 0.000 / 3.00` | `0.000 / 0.000 / 0.000 / 11.00` | `major_employment_outcome_profiles` 可支撑就业排名、行业、岗位和薪资证据谈判 |

从主实验看，`app_pareto` 在 `major_geo_v1` 中达到 0.900 成功率，在 `risk_band_v1` 中达到 1.000 成功率，而 `hard_constraint` 在两组主实验中均为 0.000。由于两组实验的 `mean_hallucination_rate` 均为 0.000，说明 Agent 的收益并非来自编造学校或分数，而是来自对真实 DB gap 的有效利用。

`major_geo_v1` 不是 100% 成功。失败样本为 `real-db-set-浙江-569-009`，该样本要求 Agent 进一步退到更远的 `any_major` 候选才能命中 hidden volunteer set，而当前回复停留在医学相关近邻阶段。这一点说明当前系统虽然形成闭环，但放宽阶段选择策略仍有改进空间。

`risk_band_v1` 的结果说明 Pareto gain 不必只来自学校 tier 提升，也可以来自组合结构改进。用户显性表达“只求稳”时，`app_pareto` 能在保留硬约束的前提下给出 `chong/wen/bao` 风险组合，并用最低分、最低位次、分差和位次差说明为什么适度冲刺是可谈判的。

四组扩展实验进一步说明，本文框架可以随着数据层扩展而扩展。`tuition_value_v1` 把 `admission_plans.tuition` 转化为预算谈判证据；`major_quality_v1` 把专业排名、学科评估、特色专业、重点专业和满意度等数据聚合到 `school_major_quality_profiles`，使 Agent 能输出专业质量证据；`employment_outcome_v1` 把 `major_employment_profiles` 清洗为 `major_employment_outcome_profiles`，使就业排名、行业、岗位和薪资证据能够进入 Pareto 谈判；`school_strength_v1` 则作为较粗粒度实力证据的过渡实验。扩展实验不替代主实验，而是支撑“数据贡献可扩展”的论文论点。

## 7. 逐例证据与可复现材料

主实验逐例证据分别见：

- `gaokaollm_bench/outputs/agent_benchmark_major_geo_v1_evidence.md`
- `gaokaollm_bench/outputs/agent_benchmark_risk_band_v1_evidence.md`

扩展实验逐例证据见：

- `gaokaollm_bench/outputs/thesis_data_agent_benchmark_extension_evidence.md`
- `gaokaollm_bench/outputs/agent_benchmark_employment_outcome_v1_summary.md`
- `gaokaollm_bench/outputs/agent_benchmark_employment_outcome_v1/`

这些 evidence 附录把聚合指标落到每个 case 的 transcript 与候选证据上。对于成功样本，附录列出真实候选学校、专业、最低分、最低位次以及对应的放宽证据；对于 baseline，对照说明其不主动产生相应 Pareto opportunities，因此不能触发隐藏妥协。需要特别强调的是，文档可以引用 hidden persona 作为 evaluator ground truth，但 Agent 输入只来自用户显式话语和 PostgreSQL 查询结果，不读取 `implicit_flexibilities` 或 `volunteer_set`。

## 8. 局限性与后续工作

当前主实验和扩展实验每组均为 10 个 case，足以证明框架闭环、结果可复现和证据链可追溯，但尚不足以作为大规模 leaderboard。后续可扩展更多省份、分数段、专业门类和年份快照，以验证结论稳定性。

当前实验主要使用 offline deterministic judge，优点是稳定、可复现、便于论文核验；局限是无法完全覆盖真实用户在咨询中的细粒度行为。后续可加入多人类标注、真实用户访谈或多裁判一致性分析。

学费放宽、专业质量映射和就业结果放宽已经完成第一版闭环，因此不再作为“未实现能力”描述。更合适的后续方向包括：

- 多年稳定性风险增强：将单年最低分/位次扩展为多年份波动、录取稳定性和风险置信区间。
- 城市收益指标：不能仅凭 `schools.city` 字段写成“城市跃迁”，需要引入可核验的就业机会、生活成本或产业匹配证据。
- 真实用户校准：检验模拟用户的隐性妥协是否符合真实考生和家长的行为。
- 概率化录取风险模型：将当前确定性 `score_margin` / `rank_gap` 风险分层升级为概率化录取风险估计。

## 9. 论文迁移建议

最终论文可按如下方式组织本章材料。

| 论文章节 | 建议标题 | 对应本文内容 |
|---|---|---|
| 第 4 章 | 高考志愿偏好妥协 Benchmark 构建 | 第 2、3 节 |
| 第 5 章 | 证据驱动 Pareto 谈判 Agent 设计 | 第 4 节 |
| 第 6 章 | 实验设置、结果分析与逐例证据 | 第 5、6、7 节 |
| 第 7 章 | 总结与展望 | 第 8 节 |

论文正文中建议把 `major_geo_v1 + risk_band_v1` 写作主实验，把 `school_strength_v1 + tuition_value_v1 + major_quality_v1 + employment_outcome_v1` 写作扩展实验。这样既能保持主贡献清晰，也能说明数据层的持续扩展能力。
