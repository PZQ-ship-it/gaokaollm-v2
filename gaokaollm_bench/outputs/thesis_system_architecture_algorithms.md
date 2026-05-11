# 系统架构与算法设计正文母版

本文档用于支撑毕业论文中“系统架构与算法设计”章节。其作用是把项目中已经完成的数据层、轻量 MAS/多角色 Agent、Benchmark 评测层和七组实验结果集中组织起来，形成可直接迁入论文正文的架构说明。

本文不新增实验结论，不替代已有逐例证据附录和 summary 结果。当前论文主贡献采用“数据 + Agent + Benchmark”三贡献结构：数据层提供可核验事实证据，Agent 层执行证据驱动 Pareto 谈判，Benchmark 层用冰山画像和多轮沙盒验证效果。

## 1. 总体系统架构

本系统面向高考志愿咨询中的多轮偏好妥协任务。与普通问答系统不同，系统不只生成建议文本，而是在真实招生数据约束下发现可谈判空间，并用学校、专业、最低分、最低位次、学费、专业质量、就业结果和地域树节点等证据支持用户重新考虑约束。

总体架构可以分为四层：

| 层次 | 核心模块 | 主要职责 | 论文贡献对应 |
| --- | --- | --- | --- |
| 数据层 | PostgreSQL 招生快照、专业树、专业质量标准化层、就业结果标准化层、地域树 reviewed v1 | 提供录取事实、风险、成本、质量、就业和地域树证据 | 数据贡献 |
| MAS/多角色 Agent 层 | `前置语义归一层 -> 约束解析器 -> LLM 引导的机会规划器 -> 确定性证据探针 -> 证据谈判器` | 抽取显式约束、探测 Pareto 机会、组织谈判回复 | Agent 贡献 |
| Benchmark 评测层 | 冰山画像、simulator、target agent、evaluator | 生成隐藏妥协需求，运行多轮对话，评价事实与过程 | Benchmark 贡献 |
| 论文产物层 | summary、reports、transcripts、evidence 附录 | 保存聚合结果、逐例证据和可复现材料 | 结果支撑 |

论文中可将该结构画为“数据层 -> 多角色 Agent 层 -> Benchmark 层 -> 实验产物层”的流水线图。数据层是基础，Agent 层是方法主体，Benchmark 层是验证环境，论文产物层保证实验结果可追溯。

## 2. 数据层设计

数据层的目标不是简单存储学校和专业，而是把用户约束和可谈判收益转化为可查询、可比较、可审计的证据。

### 2.1 招生事实与风险证据

PostgreSQL 招生快照提供高考志愿推荐的基础事实约束，主要包括：

| 数据表或字段 | 作用 |
| --- | --- |
| `admission_scores` | 专业层面的最低分、最低位次等录取事实 |
| `school_admission_scores` | 学校层面的录取分数与位次证据 |
| `score_rank_segments` | 分数与位次换算，用于风险分层 |
| `batch_lines` | 批次线与分数边界参考 |
| `admission_plans` | 招生计划、选科要求、学费等信息 |
| `admission_plans.tuition` | 支撑 `tuition_value_relax` 的预算放宽证据 |
| `schools`、`majors` | 学校、专业标准实体与基础属性 |

这些表支持两类核心判断：第一，候选是否真实可达；第二，候选相对当前约束是否带来 Pareto 改善。

### 2.2 专业树与专业质量标准化层

专业相关决策需要解决两个问题：专业相近性和专业质量证据。系统使用专业树和专业质量标准化层分别处理这两类问题。

| 数据资产 | 作用 |
| --- | --- |
| `major_tree_final_reviewed.json` | 支撑专业层级放宽与相近专业搜索 |
| `discipline_major_mappings` | 记录学科评估、专业类与本科专业之间的映射关系 |
| `school_major_quality_signals` | 汇总专业排名、学科评估、特色专业、重点专业、满意度等原始信号 |
| `school_major_quality_profiles` | 聚合学校-专业质量画像，输出 `quality_score`、`quality_gain`、`evidence_sources` |

`school_major_quality_profiles` 使 Agent 能从“学校更好”推进到“该学校在该专业上有明确质量证据”。这也是 `major_quality_relax` 相比粗粒度 `strength_relax` 的主要改进。

### 2.3 就业结果标准化层

就业导向放宽使用 `major_employment_profiles` 的原始就业信息，并标准化为 `major_employment_outcome_profiles`。该层保留就业排名、就业城市、行业、岗位、薪资等可落到 transcript 的证据。

| 字段 | 作用 |
| --- | --- |
| `employment_rank` | 专业就业结果排序信号 |
| `top_city` | 主要就业城市证据 |
| `top_industry` | 主要就业行业证据 |
| `job_distribution` | 岗位分布证据 |
| `salary_distribution` | 薪资分布证据 |
| `outcome_score` | 就业结果综合分 |
| `evidence_sources` | 证据来源与原始字段追踪 |

该设计避免把“就业好”写成不可验证的口号，而是要求 Agent 给出结构化就业证据。

### 2.4 地域树 reviewed v1

地域放宽不能只依赖 `schools.city` 字段直接宣称“城市更好”。系统因此引入两份 reviewed 地域树数据资产：`region_geo_tree_reviewed_v1.json` 与 `region_urban_tier_tree_reviewed_v1.json`。前者用于地理板块、相邻省市和“别太远”等偏好，后者用于城市层级、城市资源和“想去好城市”等偏好。

地域树节点保留源节点、目标节点、映射规则、置信度和审校状态。它们只提供可审计的地域树证据，不直接等价于就业机会、生活成本或城市生活质量收益。`region_tree_v1` 的 Pareto gain 仍按学校 tier/ranking 改善计算。

## 3. 轻量 MAS / 多角色 Agent 设计

### 3.1 新 MAS 架构与 v1 能力融合

业务 Agent 的论文主叙述为：`前置语义归一层 -> 约束解析器 -> LLM 引导的机会规划器 -> 确定性证据探针 -> 证据谈判器`。其中，前置语义归一层继承 v1 查询重写能力，只对用户显式话语做语义归一、偏好轴拆解、歧义提示和查询压缩；约束解析器形成硬约束基线；LLM 引导的机会规划器只负责探针计划、机会排序和澄清提示；事实候选仍由确定性证据探针通过 PostgreSQL 与标准化证据层产生；证据谈判器负责组织候选证据并生成可审计回复。LLM 不生成学校、专业、分数、位次等事实候选，也不读取 `implicit_flexibilities`、`volunteer_set` 或 `axis_flexibilities`。

该结构不是完全自治的多智能体系统，而是基于角色分工的轻量 MAS / 多角色 Agent 工作流。实现层名称可追溯为 `semantic_normalizer -> gatekeeper -> llm-guided radar planner -> deterministic probes -> negotiator`，但论文正文优先使用学术化角色名。

| 论文角色 | 实现层名称 | 输入 | 输出 |
| --- | --- | --- | --- |
| 前置语义归一层 | `semantic_normalizer` | 用户显式话语 | 标准化意图、偏好轴、澄清提示 |
| 约束解析器 | `gatekeeper` | 标准化意图 | 硬约束参数字典、baseline |
| LLM 引导的机会规划器 | `radar` planner | 显式约束、baseline、意图轴 | `probe_plan`、`opportunity_rankings`、`clarification_hint` |
| 确定性证据探针 | SQL probes / evidence profiles | 探针计划与结构化约束 | 可审计 Pareto opportunities 与事实候选 |
| 证据谈判器 | `negotiator` | baseline、机会集合和证据字段 | 面向用户的证据化谈判回复 |

## 4. Benchmark 评测层

Benchmark 的目标是评估 Agent 是否能在真实招生数据约束下发现隐藏妥协空间，而不是只看它是否能生成流畅文本。

评测流程如下：

1. 构造冰山画像：显性画像记录用户明面上的分数、专业、地域、预算、风险偏好等约束；隐藏画像记录在证据充分时可接受的妥协条件。
2. simulator 根据 persona 与 target agent 多轮对话。
3. target agent 可以是 `app_pareto` 或 `hard_constraint`。
4. transcript 保存每轮用户话语、Agent 回复与 `internal_state`。
5. evaluator 同时进行事实评价和过程评价。
6. summary、reports、evidence 文档汇总聚合指标和逐例证据。

`hard_constraint` 是论文中的关键对照。它只按显性硬约束返回可达志愿，不主动提出 Pareto 妥协。`app_pareto` 则使用数据证据主动提出约束放宽或组合重排方案。二者对照体现“迎合显性红线”和“证据驱动妥协谈判”的差异。

### 4.1 多轴隐藏妥协压力测试

除七组单轴或单类闭环实验外，Benchmark 层还加入 `multi_axis_v1` 与 `multi_axis_v2` 压力测试，用于检验用户同时存在两个隐藏妥协轴时，Agent 是否能把多个 opportunity group 同时组织成有效证据链。压力测试不新增业务 relax 算法，而是组合现有 `major_geo_relax`、`risk_band_relax`、`major_quality_relax`、`tuition_value_relax`、`employment_outcome_relax` 和 `region_tree_relax`。

`multi_axis_v1` 是历史压力测试版本；`multi_axis_v2` 是轴一致性修正版，在画像生成时要求两个 required axes 围绕一致显性需求或可解释正交需求构造。persona 使用 `relaxation_axes` 与 `axis_flexibilities` 描述两个 required axes。Agent 不读取 `implicit_flexibilities`、`volunteer_set` 或 `axis_flexibilities`；这些字段只作为 simulator/evaluator ground truth。deterministic judge 逐轴检查证据，只有两个轴都命中时才判定 elicitation success，并额外保留 `axis_successes` 与 `axis_pareto_gains` 便于分析证据编排瓶颈。

## 5. 关键算法设计

### 5.1 通用 Pareto Opportunity Detection

多类动态放宽共享同一个抽象流程：

```text
用户话语
  -> 显式约束抽取
  -> baseline 查询
  -> 单维或联合放宽探测
  -> 候选过滤、去重、排序
  -> 证据组织与谈判回复
  -> transcript 与 evaluator 评分
```

在算法层面，系统只放宽可谈判偏好，不放宽分数、选科等硬约束。每个 opportunity 必须返回可审计证据，而不仅是自然语言判断。

### 5.2 `major_geo_relax`

`major_geo_relax` 处理专业和地域联合放宽。它保留分数、选科、预算等硬约束，同时去掉省份限制并放宽原专业限制。专业放宽优先使用专业树 staged relaxation：先查同专业，再查相近专业类，必要时扩展到更宽的专业集合。

该算法解决的问题是：用户显性上可能坚持本省和某专业，但隐藏上可能接受“跨省 + 相近专业”换取更高层次志愿。主实验 `major_geo_v1` 验证了该能力。

### 5.3 `risk_band_relax`

`risk_band_relax` 处理风险偏好放宽。它保留专业、省份、选科、预算等硬约束，只放宽“只求稳、不接受冲”的风险偏好。系统根据 `score_margin` 和 `rank_gap` 将候选划分为 `chong/wen/bao` 风险层级；位次数据不足时退化为分差规则。

该算法把 v1 中工程化的 `1:3:9` 冲稳保推荐推进为可评测闭环：Agent 不只是给出梯度推荐，而是在 Benchmark 中用最低分和最低位次证据触发隐藏妥协。

### 5.4 `tuition_value_relax`

`tuition_value_relax` 处理预算性价比放宽。它保留分数、专业、选科等硬约束，只放宽学费上限，默认窗口为：

```text
budget < tuition <= budget + 10000
```

候选需要同时给出学费、学费增量、最低分、最低位次和学校层次或排名收益。该算法适合表达“如果每年多接受一定学费，可以换到仍可达且收益更高的方案”。

### 5.5 `major_quality_relax`

`major_quality_relax` 使用 `school_major_quality_profiles`。算法保留分数、专业、选科、预算等硬约束，寻找同专业或相近专业中 `quality_score` 更高的候选，并输出 `quality_gain` 与专业质量证据。

证据可以来自专业排名、学科评估、特色专业、重点专业、满意度等标准化信号。该算法避免只用学校综合层次代替专业质量，使论文的数据贡献更加具体。

### 5.6 `employment_outcome_relax`

`employment_outcome_relax` 使用 `major_employment_outcome_profiles`。算法保留分数、选科、预算等硬约束，允许在同专业或专业树近邻专业中寻找就业结果证据更强的候选，并输出 `outcome_score`、`outcome_gain`、就业排名、行业、岗位和薪资证据。

该算法说明系统的数据证据可以从录取事实、成本和专业质量继续扩展到就业结果。但论文中仍应把它定位为扩展实验，不替代主实验。

### 5.7 `region_tree_relax`

`region_tree_relax` 使用 `region_geo_tree_reviewed_v1.json` 与 `region_urban_tier_tree_reviewed_v1.json`。算法保留分数、专业、选科、预算等硬约束，只放宽用户显式表达中的地域偏好，例如“只看杭州/浙江”“别太远”“想去好城市”。其中 `geo_block_relax` 按地理板块或相邻地域节点扩展候选，`urban_tier_relax` 按 reviewed 城市层级节点扩展候选。

候选必须同时返回学校、省份、城市、专业、最低分、最低位次、学校 tier/ranking、源地域节点、目标地域节点、放宽策略和树置信度。城市层级只作为 reviewed region-tree 证据，不直接代表就业机会、生活成本或生活质量收益；`region_tree_v1` 的 Pareto gain 仍按学校 tier/ranking 改善计算。

### 5.8 `strength_relax`

`strength_relax` 是较粗粒度的学校或学科实力放宽实验。它在专业质量标准化层完全形成之前提供了“实力证据可驱动妥协”的过渡结果。最终论文可将其作为扩展实验，用于说明从学校级实力到专业级质量证据的演进。

## 6. 算法、数据与实验结果映射

下表中的四个指标依次为：`elicitation_success_rate / mean_pareto_gain / mean_hallucination_rate / avg_turns`。

| 实验 | 类型 | 核心算法 | 关键数据证据 | `app_pareto` | `hard_constraint` | 论文含义 |
| --- | --- | --- | --- | --- | --- | --- |
| `major_geo_v1` | 主实验 | `major_geo_relax` | 专业树、最低分、最低位次、学校层次 | `0.900 / 0.900 / 0.000 / 5.20` | `0.000 / 0.000 / 0.000 / 7.00` | 证明专业+地域联合放宽可触发隐藏妥协 |
| `risk_band_v1` | 主实验 | `risk_band_relax` | `score_margin`、`rank_gap`、`chong/wen/bao` 风险层级 | `1.000 / 3.000 / 0.000 / 5.00` | `0.000 / 0.000 / 0.000 / 15.00` | 证明冲稳保组合质量也是 Pareto gain |
| `school_strength_v1` | 扩展实验 | `strength_relax` | 学校或学科实力、排名、评级 | `1.000 / 15.000 / 0.000 / 5.00` | `0.000 / 0.000 / 0.000 / 11.00` | 证明实力证据可以接入同一谈判框架 |
| `tuition_value_v1` | 扩展实验 | `tuition_value_relax` | `admission_plans.tuition`、学费增量、最低分 | `1.000 / 1.000 / 0.000 / 5.00` | `0.000 / 0.000 / 0.000 / 11.00` | 证明成本约束可被小幅放宽并形成性价比谈判 |
| `major_quality_v1` | 扩展实验 | `major_quality_relax` | `school_major_quality_profiles`、`quality_score`、专业质量证据 | `1.000 / 16.000 / 0.000 / 5.00` | `0.000 / 0.000 / 0.050 / 11.00` | 证明专业级质量标准化层可支撑更细粒度妥协 |
| `employment_outcome_v1` | 扩展实验 | `employment_outcome_relax` | `major_employment_outcome_profiles`、`outcome_score`、就业证据 | `1.000 / 49.000 / 0.000 / 3.00` | `0.000 / 0.000 / 0.000 / 11.00` | 证明就业结果证据可扩展到 Agent+Benchmark 闭环 |
| `region_tree_v1` | 扩展实验 | `region_tree_relax` | `region_geo_tree_reviewed_v1.json`、`region_urban_tier_tree_reviewed_v1.json`、地域树节点 | `1.000 / 1.000 / 0.000 / 3.00` | `0.000 / 0.000 / 0.000 / 11.00` | 证明 reviewed 地域树可扩展到同一闭环 |

其中 `major_geo_v1 + risk_band_v1` 是当前论文第一版主实验。`school_strength_v1`、`tuition_value_v1`、`major_quality_v1`、`employment_outcome_v1`、`region_tree_v1` 是扩展实验，用于证明数据贡献和 Agent 框架的可扩展性。

`major_geo_v1` 不是 100% 成功，失败样本为 `real-db-set-浙江-569-009`。论文中应保留该失败样本，避免把 `0.900` 写成完全成功。

`multi_axis_v1` 与 `multi_axis_v2` 作为 Benchmark 压力测试单独报告，不并入上表的七组实验事实口径。v1 的三类 profile 为 `major_geo_risk`、`quality_tuition`、`employment_region`，聚合结果为 `app_pareto 0.533 / 1.133 / 0.029 / 7.67` vs `hard_constraint 0.000 / 0.000 / 0.000 / 13.00`，逐 profile 结果分别为 1/10、5/10、10/10。v2 是轴一致性修正版，聚合结果为 `app_pareto 0.367 / 1.133 / 0.005 / 9.33` vs `hard_constraint 0.000 / 0.000 / 0.008 / 13.00`，逐 profile 结果为 6/10、5/10、0/10，说明修正后可以更清楚地区分画像构造问题与 Agent 证据编排瓶颈，尤其 `employment_region` 暴露出就业证据与地域树证据联合组织不足。

| 压力测试 | 定位 | 组合 profile | `app_pareto` | `hard_constraint` | 论文含义 |
| --- | --- | --- | --- | --- | --- |
| `multi_axis_v1` | 历史压力测试版本 | `major_geo_risk`、`quality_tuition`、`employment_region` | `0.533 / 1.133 / 0.029 / 7.67` | `0.000 / 0.000 / 0.000 / 13.00` | 暴露多轴证据编排问题，但部分画像存在轴一致性不足 |
| `multi_axis_v2` | 轴一致性修正版 | `major_geo_risk`、`quality_tuition`、`employment_region` | `0.367 / 1.133 / 0.005 / 9.33` | `0.000 / 0.000 / 0.008 / 13.00` | 检验一致画像下两个隐藏放宽轴同时成立时的证据编排能力 |

## 7. 论文图表建议

本章节适合配合以下图表进入论文：

| 图表 | 内容 |
| --- | --- |
| 系统总体架构图 | 数据层 -> MAS/多角色 Agent 层 -> Benchmark 层 -> 论文产物层 |
| 多角色 Agent 工作流图 | `前置语义归一层 -> 约束解析器 -> LLM 引导的机会规划器 -> 确定性证据探针 -> 证据谈判器` 的输入输出关系 |
| Benchmark 流程图 | persona -> simulator -> target agent -> transcript -> evaluator -> summary |
| 算法-数据-实验映射表 | 七组实验如何对应不同数据证据维度与 Pareto 放宽算法 |

章节安排上，可将数据层与 Benchmark 构建放入第 4 章，将 MAS/多角色 Agent 与关键算法放入第 5 章，将七组实验映射和结果分析放入第 6 章。

## 8. 边界与写作注意

第一，MAS 需要使用谨慎表述。本文系统是“基于角色分工的轻量 MAS/多角色 Agent 架构”，而不是完全自治的多智能体社会。该口径既能体现架构设计，也避免过度夸大。

第二，Agent 不读取 `implicit_flexibilities` 或 `volunteer_set`。这些字段只用于 Benchmark 评价，不进入业务 Agent 输入。

第三，主实验与扩展实验要分层书写。`major_geo_v1 + risk_band_v1` 证明核心偏好妥协能力，五组扩展实验证明数据证据维度可扩展。

第四，城市生活质量、家庭距离、校园文化、个人兴趣匹配等因素目前缺少稳定可核验的 PostgreSQL 证据，不应写成已实现 Pareto 放宽能力。它们可以作为后续工作，前提是先建立可审计的数据标准化层。

第五，所有算法效果都应回到 transcript、report、summary 和 evidence 文档，而不是只引用自然语言观察。这样才能服务毕业论文的可复现性和答辩追问。
