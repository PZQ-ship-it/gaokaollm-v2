# 数据 + Agent + Benchmark 动态决策路线图

本文档用于整理毕业论文中“数据 + Agent + Benchmark”三条贡献线的当前状态、实验结果和后续开发优先级。它不新增实验结论，也不替代正式实验报告；它的作用是把动态约束放宽从想法列表整理成可写入论文和后续开发计划的能力矩阵。

当前项目已经形成七组 Agent-vs-Baseline 闭环：

- 主实验：`major_geo_v1`、`risk_band_v1`。
- 扩展实验：`school_strength_v1`、`tuition_value_v1`、`major_quality_v1`、`employment_outcome_v1`、`region_tree_v1`。
- 地域树数据层：`region_geo_tree_reviewed_v1.json`、`region_urban_tier_tree_reviewed_v1.json`、HITL review packet 与 coverage report 已接入 `region_tree_v1` 扩展实验。
- 后续优先方向：多年稳定性风险增强、城市收益指标增强与继续 HITL 审校、真实用户校准、概率化录取风险模型。

## 1. 论文贡献结构

论文主线建议采用“数据 + Agent + Benchmark”。这样可以准确解释 PostgreSQL 招生快照、专业树、专业质量标准化层、就业结果标准化层、地域树 reviewed v1 数据层和多类动态决策实验之间的关系。

| 贡献线 | 当前内容 | 论文作用 |
|---|---|---|
| 数据贡献 | 本地 PostgreSQL 招生快照、`admission_scores`、`school_admission_scores`、`score_rank_segments`、`batch_lines`、`admission_plans.tuition`、专业树、`school_major_quality_profiles`、`major_employment_outcome_profiles`、`region_geo_tree_reviewed_v1.json`、`region_urban_tier_tree_reviewed_v1.json`、HITL review packet、coverage report | 为每一次 Pareto 谈判提供可核验的分数、位次、学费、风险、专业质量、就业结果和地域树证据 |
| Agent 贡献 | LangGraph `gatekeeper -> radar -> negotiator`，以及 `major_geo_relax`、`risk_band_relax`、`tuition_value_relax`、`major_quality_relax`、`employment_outcome_relax`、`region_tree_relax`、`geo_block_relax`、`urban_tier_relax` 等探测能力 | 把用户显式约束转化为证据驱动的动态妥协谈判 |
| Benchmark 贡献 | 冰山画像、多轮沙盒、事实/过程联合评价、`app_pareto` vs `hard_constraint` 对照 | 验证 Agent 是否真的触发隐藏可妥协条件，而不是只生成看似合理的建议 |

需要特别强调：被测 Agent 不读取 benchmark 的 `implicit_flexibilities` 或 `volunteer_set`。Agent 输入只来自用户显式话语抽取出的约束和 PostgreSQL/标准化数据层查询结果；隐藏画像只用于模拟用户与评价。

## 2. 决策考量分类框架

动态放宽不是无条件劝用户降低要求。更稳妥的分类方式是把高考志愿决策变量拆成四层：

| 层级 | 定义 | 当前处理原则 | 例子 |
|---|---|---|---|
| 硬约束 | 不应被 Agent 主动突破的事实或资格条件 | 默认不放宽，只用于过滤候选 | 分数、位次、选科、批次、本科层次 |
| 可谈判偏好 | 用户可能因证据充分而改变的初始偏好 | 可以生成冰山画像并做多轮谈判 | 专业、地域、风险偏好、预算、专业质量、学科实力、就业导向 |
| 证据维度 | 判断放宽是否带来收益的可核验数据 | 必须来自 PostgreSQL 或明确标准化 artifact | 最低分、最低位次、学校 tier/ranking、风险层级、学费、专业质量评分、就业排名、行业、岗位、薪资、地域树节点 |
| 谈判动作 | Agent 在对话中可采取的操作 | 必须留下 transcript 证据 | 约束放宽、替代专业、组合重排、证据校准、追问澄清 |

因此，论文中不应把“用户可能关心的因素”直接等同于“已实现的 Pareto 放宽能力”。只有当某个因素同时满足真实数据、可构造 baseline-vs-relaxed gap、能在对话中表达成证据、能被 judge 验证时，才适合作为当前实验闭环。

## 3. 已闭环能力矩阵

| 实验 | 论文定位 | 决策考量 | Agent 能力 | 关键数据证据 | 结果口径 |
|---|---|---|---|---|---|
| `major_geo_v1` | 主实验 | 专业 + 地域联合放宽 | `major_geo_relax` | 录取最低分、学校 tier/ranking、专业树层级放宽 | `app_pareto 0.900 / 0.900 / 0.000 / 5.20` vs `hard_constraint 0.000 / 0.000 / 0.000 / 7.00` |
| `risk_band_v1` | 主实验 | 风险偏好与冲稳保组合 | `risk_band_relax` | `min_score`、`min_rank`、`score_margin`、`rank_gap`、`chong/wen/bao` | `app_pareto 1.000 / 3.000 / 0.000 / 5.00` vs `hard_constraint 0.000 / 0.000 / 0.000 / 15.00` |
| `school_strength_v1` | 扩展实验 | 学校/学科实力放宽 | `strength_relax` | `school_major_strengths`、最低分、最低位次、排名/评级 | `app_pareto 1.000 / 15.000 / 0.000 / 5.00` vs `hard_constraint 0.000 / 0.000 / 0.000 / 11.00` |
| `tuition_value_v1` | 扩展实验 | 学费/预算性价比放宽 | `tuition_value_relax` | `admission_plans.tuition`、学费增量、最低分、最低位次、学校层次 | `app_pareto 1.000 / 1.000 / 0.000 / 5.00` vs `hard_constraint 0.000 / 0.000 / 0.000 / 11.00` |
| `major_quality_v1` | 扩展实验 | 专业质量证据放宽 | `major_quality_relax` | `school_major_quality_profiles`、`quality_score`、专业排名、学科评估、特色/重点/满意度 | `app_pareto 1.000 / 16.000 / 0.000 / 5.00` vs `hard_constraint 0.000 / 0.000 / 0.050 / 11.00` |
| `employment_outcome_v1` | 扩展实验 | 就业导向放宽 | `employment_outcome_relax` | `major_employment_outcome_profiles`、`outcome_score`、就业排名、行业、岗位、薪资分布 | `app_pareto 1.000 / 49.000 / 0.000 / 3.00` vs `hard_constraint 0.000 / 0.000 / 0.000 / 11.00` |
| `region_tree_v1` | 扩展实验 | 地域树层级放宽 | `region_tree_relax`、`geo_block_relax`、`urban_tier_relax` | `region_geo_tree_reviewed_v1.json`、`region_urban_tier_tree_reviewed_v1.json`、最低分、最低位次、地域树节点、树置信度 | `app_pareto 1.000 / 1.000 / 0.000 / 3.00` vs `hard_constraint 0.000 / 0.000 / 0.000 / 11.00` |

这些结果说明，Pareto gain 不只来自学校层次提升。`risk_band_relax` 证明志愿组合质量也可以成为收益；`tuition_value_relax` 证明预算边界可以被学费增量和学校收益证据校准；`major_quality_relax` 证明补充专业质量标准化层后，Agent 可以从“学校更强”推进到“学校 + 专业证据更强”；`employment_outcome_relax` 证明就业画像可以被清洗成可谈判、可核验的就业结果证据；`region_tree_relax` 证明 reviewed 地域树可以进入同一套 MAS 探测、沙盒模拟和事实评价闭环。

## 3.1 地域树 reviewed v1 与 `region_tree_v1`

地域放宽已经从“纯设计”推进到最小 Agent+Benchmark 扩展实验。需要同时写清两个边界：第一，`region_tree_v1` 已经证明地域树数据层能够接入 `radar` 探测和 benchmark；第二，城市层级只是 reviewed region-tree 证据，不直接等价于就业机会、生活成本、生活质量或城市收益。

| 数据层 | 产物 | 当前作用 | 实验关系 |
|---|---|---|---|
| 地理邻近树 reviewed v1 | `gaokaollm_bench/outputs/region_geo_tree_reviewed_v1.json` | 记录全国、大区/地理板块、省份、城市/都市圈层级 | 支撑 `geo_block_relax`，已进入 `region_tree_v1` |
| 城市层级树 reviewed v1 | `gaokaollm_bench/outputs/region_urban_tier_tree_reviewed_v1.json` | 记录一线、新一线、强省会、普通省会、重要地级市等层级 | 支撑 `urban_tier_relax`，已进入 `region_tree_v1` |
| HITL 审校包 | `gaokaollm_bench/outputs/region_tree_review_packet.csv/jsonl` | 将低置信、未匹配或歧义城市整理成人工审校任务 | 为 reviewed v1 和后续持续审校提供依据 |
| v1 覆盖报告 | `gaokaollm_bench/outputs/region_tree_v1_coverage_report.md/json` | 对比 v0/v1 的覆盖率、剩余 review queue 和城市挂载情况 | 证明地域树数据层具备可验收质量 |
| 地域树实验证据 | `gaokaollm_bench/outputs/agent_benchmark_region_tree_v1_evidence.md` | 汇总 10 个 case 的学校、城市、专业、最低分、地域树节点和策略证据 | 证明 `region_tree_relax` 已形成扩展实验闭环 |

覆盖报告显示，地域树仍需要持续 HITL 审校，尤其是低置信城市、未匹配城市和城市层级争议项。当前 v1 是 reviewed seed，已足够支持最小扩展实验；后续应继续提升地域树质量，并在有可核验证据时再讨论城市收益指标。

`region_tree_v1` 的 Pareto gain 仍按学校 tier/ranking 改善计算，不把“城市层级更高”本身计入收益。这样可以避免把 `schools.city` 或城市层级包装成未被证据支持的城市收益。

## 4. 数据贡献现状

当前数据贡献已经超过原始招生表本身，主要体现在五类可复用证据层。

第一类是招生事实与风险证据。`admission_scores`、`school_admission_scores`、`score_rank_segments` 和 `batch_lines` 支撑分数、位次、批次线、风险层级和是否可达的判断。这部分是所有放宽实验的底座。

第二类是成本与组合证据。`admission_plans.tuition` 使 `tuition_value_relax` 可以在预算红线附近构造“小幅超预算但收益可解释”的冰山画像。该方向已经完成闭环，不应再写成下一步推荐实验。

第三类是专业质量标准化证据。新增的 `discipline_major_mappings`、`school_major_quality_signals` 和 `school_major_quality_profiles` 把专业排名、学科评估、特色专业、重点专业、满意度等来源统一到学校-专业质量画像中，使 `major_quality_relax` 可以返回 `quality_score`、`quality_gain` 和 `evidence_sources`。这部分是论文“数据贡献”最值得突出的环节之一。

第四类是就业结果标准化证据。`major_employment_profiles` 已经被清洗为 `major_employment_outcome_profiles`，将就业排名、热门就业城市、行业分布、岗位分布、薪资分布和 `outcome_score` 转化为 Agent 可表达、Benchmark 可核验的字段。`employment_outcome_v1` 说明就业画像可以进入同一套数据-探测-沙盒-评价闭环。

第五类是地域树 reviewed v1 标准化证据。`region_geo_tree_reviewed_v1.json` 与 `region_urban_tier_tree_reviewed_v1.json` 把 `schools.province` / `schools.city` 从自由城市字段推进到可审校的层级节点；HITL review packet 与 coverage report 记录了低置信映射和人工回填过程。`region_tree_v1` 说明地域树可以进入 Agent+Benchmark 扩展实验，但城市层级不直接证明就业机会、生活成本或生活质量，城市收益指标仍需额外可核验证据。

## 5. 仍需开发或清洗的方向

| 状态 | 决策考量 | 当前数据条件 | 是否适合继续做 benchmark | 建议 |
|---|---|---|---|---|
| 推荐下一步 | 多年稳定性风险增强 | 多年份录取分、学校分数线和批次线可用 | 适合作为 `risk_band_relax` 增强 | 用分数波动、位次波动、近年稳定性增强风险证据，形成“冲稳保 + 稳定性”的可解释组合 |
| 增强方向 | 城市收益指标与地域树持续 HITL | reviewed 地域树与 `region_tree_v1` 已完成，但城市收益缺少独立可核验证据 | 暂不适合直接写成城市收益 Pareto gain | 继续审校低置信城市，同时补充真实距离、就业机会、生活成本、产业匹配等指标 |
| 需谨慎 | 专业就业城市匹配 | 就业数据与城市、行业可能有关，但需要统一口径 | 有条件适合 | 可作为 `employment_outcome_relax` 的二期增强 |
| 仅展望 | 家庭距离 | 当前缺少家庭位置与距离成本数据 | 不适合 | 写入局限性与未来用户画像扩展 |
| 仅展望 | 校园文化 | 当前缺少社团、氛围、校园生活质量证据 | 不适合 | 不进入当前 DB benchmark |
| 仅展望 | 个人兴趣匹配 | 当前缺少稳定兴趣测评与职业测评数据 | 不适合 | 可作为 v3 用户画像方向 |

这里的底线是：如果某个因素不能在 transcript 中落成“学校/专业/分数/位次/学费/质量/就业/地域树节点”等具体证据，就不应进入当前论文主实验。对于地域方向，`region_tree_v1` 已经证明地域树能进入扩展实验；但城市收益指标仍需可核验证据，不能仅凭 `schools.city` 包装。

## 6. 论文写法建议

建议论文采用分层写法，避免把所有实验都放到同一个贡献等级。

`major_geo_v1` 与 `risk_band_v1` 作为主实验，分别证明“约束空间联合放宽”和“风险组合谈判”两种核心动态决策能力。它们直接支撑论文的 Agent 贡献和 Benchmark 贡献。

`school_strength_v1`、`tuition_value_v1`、`major_quality_v1`、`employment_outcome_v1` 与 `region_tree_v1` 作为扩展实验，证明同一套数据-探测-沙盒-评价流程可以接入更多真实证据维度。这些实验更适合支撑论文的数据贡献和可扩展性结论，而不是替代前两组主实验。

可迁入论文的表述如下：

> 本文的核心贡献不是穷尽所有高考志愿偏好，而是提出一条可扩展的验证流程：先判断某个偏好是否能由真实数据库形成可核验 gap，再生成冰山画像，最后通过多轮沙盒和事实/过程联合评价验证 Agent 是否能触发 Pareto 妥协。当前系统已在专业地域、风险组合、学费预算、专业质量、就业结果和地域树等维度完成闭环，说明该框架可以从单一 Agent 策略扩展为数据驱动的动态决策评测体系。

## 7. 可复现依据

本文档引用当前已有产物，不新增实验结果：

- `gaokaollm_bench/outputs/agent_benchmark_major_geo_v1_summary.md`
- `gaokaollm_bench/outputs/agent_benchmark_risk_band_v1_summary.md`
- `gaokaollm_bench/outputs/agent_benchmark_school_strength_v1_summary.md`
- `gaokaollm_bench/outputs/agent_benchmark_tuition_value_v1_summary.md`
- `gaokaollm_bench/outputs/agent_benchmark_major_quality_v1_summary.md`
- `gaokaollm_bench/outputs/agent_benchmark_employment_outcome_v1_summary.md`
- `gaokaollm_bench/outputs/agent_benchmark_region_tree_v1_summary.md`
- `gaokaollm_bench/outputs/agent_benchmark_region_tree_v1_evidence.md`
- `gaokaollm_bench/outputs/thesis_method_experiment_chapters.md`
- `gaokaollm_bench/outputs/thesis_agent_benchmark_contribution.md`
- `gaokaollm_bench/outputs/thesis_data_agent_benchmark_extension_evidence.md`

本轮只更新路线图文档，不更新审计脚本，不启动数据库，不调用外部 LLM，也不重跑 benchmark。
