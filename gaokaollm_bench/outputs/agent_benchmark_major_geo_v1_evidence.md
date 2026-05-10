# Agent Benchmark Major-Geo v1 逐例证据附录

## 实验来源与复现路径

本附录服务于论文实验章节，用来把 `agent_benchmark_major_geo_v1` 的聚合结果落到逐例 transcript 证据。它只整理现有产物，不新增实验、不重跑 LLM、不修改 benchmark 或 Agent 代码。

引用产物：

- 聚合结果：`gaokaollm_bench/outputs/agent_benchmark_major_geo_v1/summary.json`
- 逐例报告：`gaokaollm_bench/outputs/agent_benchmark_major_geo_v1/reports/app_pareto.jsonl`
- 逐例报告：`gaokaollm_bench/outputs/agent_benchmark_major_geo_v1/reports/hard_constraint.jsonl`
- 对话证据：`gaokaollm_bench/outputs/agent_benchmark_major_geo_v1/transcripts/{target}/`
- 论文母版：`gaokaollm_bench/outputs/thesis_agent_benchmark_contribution.md`
- 方法正文：`gaokaollm_bench/outputs/thesis_method_experiment_chapters.md`
- 层级放宽方法：`gaokaollm_bench/outputs/thesis_hierarchical_relaxation_methodology.md`
- 图表素材：`gaokaollm_bench/outputs/thesis_figures_tables_pack.md`

主实验使用 10 条真实 DB 冰山画像，目标系统为 `app_pareto` 与 `hard_constraint`，最大轮次为 3，评测模式为 offline deterministic。本附录采用当前论文的“三贡献”口径：数据贡献是 PostgreSQL 招生事实、真实最低分/位次和专业树 `major_tree_final_reviewed.json`；Agent 贡献是基于 `major_geo_relax` 的证据驱动 Pareto 谈判；Benchmark 贡献是冰山画像、多轮沙盒与事实/过程联合评价。

## 专业树层级放宽证据链

`major_geo_v1` 的关键并不只是“去掉专业和省份限制”，而是把专业放宽组织成可解释、可审计的 staged relaxation。专业树 `major_tree_final_reviewed.json` 是数据贡献与 Agent 算法之间的桥梁：它把真实招生数据库中的专业文本挂载到面向志愿决策的层级放宽本体上，使 Agent 可以从“最相近专业”逐步扩展到“同父类”“相关大类/probe 邻居”，最后才退到 `any_major`。

该专业树的 reviewed artifact 与 `major_tree_methodology.md` 中统计保持一致：共 82 个节点、8 个 Level 0 大类、22 个 Level 1 节点、52 个叶子簇，叶子簇覆盖 19,096 条 observed names。这说明专业树不是只依赖静态专业目录，而是吸收了 PostgreSQL 录取事实中的真实专业名变体。

构建流程采用 human-in-the-loop 的混合标注路线：

```text
人工本体骨架
  -> PostgreSQL admission_scores.major_name_raw 扫描
  -> include/exclude 规则挂载
  -> probe top-k 候选生成
  -> LLM/人工审校低置信样本
  -> reviewed tree 与审计产物
```

在 `major_geo_relax` 中，这条数据链具体落到以下 staged relaxation 路径：同叶子/近邻专业 -> 同父类 -> 相关大类/probe 邻居 -> `any_major`。因此，逐例 transcript 中的 Stage 字段不仅是候选来源说明，也是论文中评估“放宽是否到达足够远阶段”的过程证据。

需要强调的是，persona 中的 `implicit_flexibilities` 与 `volunteer_set` 只作为 evaluator 的隐藏真值使用；被测 Agent 只能看到用户显式话语和 PostgreSQL/专业树查询结果，不能读取这些 hidden fields。

## 聚合指标核对表

| Target | Cases | Completed | Failed | Elicitation Success | Mean Pareto Gain | Mean Hallucination | Avg Turns |
|---|---:|---:|---:|---:|---:|---:|---:|
| `app_pareto` | 10 | 10 | 0 | 0.900 | 0.900 | 0.000 | 5.20 |
| `hard_constraint` | 10 | 10 | 0 | 0.000 | 0.000 | 0.000 | 7.00 |

核对结论：`app_pareto` 在 10 个 case 中成功 9 个，`hard_constraint` 成功 0 个；两者 hallucination 均为 0.000。因此提升来自真实 DB 证据触发隐性妥协，而不是虚构学校或分数。

## 逐例结果表

| Case | Score | Target major | app success | app turns | app gain | app halluc. | baseline success | baseline turns |
|---|---:|---|---|---:|---:|---:|---|---:|
| `real-db-set-浙江-542-001` | 542 | 临床医学 | true | 5 | 1 | 0.000 | false | 7 |
| `real-db-set-浙江-544-002` | 544 | 临床医学 | true | 5 | 1 | 0.000 | false | 7 |
| `real-db-set-浙江-546-003` | 546 | 临床医学 | true | 5 | 1 | 0.000 | false | 7 |
| `real-db-set-浙江-547-004` | 547 | 临床医学 | true | 5 | 1 | 0.000 | false | 7 |
| `real-db-set-浙江-549-005` | 549 | 临床医学 | true | 5 | 1 | 0.000 | false | 7 |
| `real-db-set-浙江-550-006` | 550 | 临床医学 | true | 5 | 1 | 0.000 | false | 7 |
| `real-db-set-浙江-557-007` | 557 | 临床医学 | true | 5 | 1 | 0.000 | false | 7 |
| `real-db-set-浙江-568-008` | 568 | 临床医学 | true | 5 | 1 | 0.000 | false | 7 |
| `real-db-set-浙江-569-009` | 569 | 临床医学 | false | 7 | 0 | 0.000 | false | 7 |
| `real-db-set-浙江-575-010` | 575 | 临床医学 | true | 5 | 1 | 0.000 | false | 7 |

逐例表说明：10 个 case 都以“临床医学”作为显性红线，考分从 542 到 575。`app_pareto` 的失败不是崩溃或幻觉，而是没有命中该 persona 的隐藏志愿集合；该失败样本在后文单独分析。

## Agent 证据表

以下候选均来自 `app_pareto` transcript 的 `internal_state.pareto_opportunities.major_geo_relax`。字段含义为：学校、省份、专业、年份、最低分、学校层次 tier、专业放宽阶段。

### `real-db-set-浙江-542-001`

| School | Province | Major | Year | Min score | Tier | Stage |
|---|---|---|---:|---:|---:|---|
| 东北农业大学 | 黑龙江 | 动物科学 | 2025 | 541 | 3 | 5 去除专业限制 |
| 西南交通大学 | 四川 | 城市设计(成都东部(国际)校区正式启用前,过渡办学地点在成都犀浦校区) | 2024 | 492 | 3 | 5 去除专业限制 |
| 西南交通大学 | 四川 | 建筑类(犀浦校区.含城乡规划,风景园林专业) | 2024 | 492 | 3 | 5 去除专业限制 |

### `real-db-set-浙江-544-002`

| School | Province | Major | Year | Min score | Tier | Stage |
|---|---|---|---:|---:|---:|---|
| 东北农业大学 | 黑龙江 | 动物科学 | 2025 | 541 | 3 | 5 去除专业限制 |
| 西藏大学 | 西藏 | 土木工程 | 2025 | 544 | 3 | 5 去除专业限制 |
| 青海大学 | 青海 | 生态学 | 2025 | 544 | 3 | 5 去除专业限制 |

### `real-db-set-浙江-546-003`

| School | Province | Major | Year | Min score | Tier | Stage |
|---|---|---|---:|---:|---:|---|
| 东北农业大学 | 黑龙江 | 动物科学 | 2025 | 541 | 3 | 5 去除专业限制 |
| 石河子大学 | 新疆 | 基础医学 | 2025 | 546 | 3 | 5 去除专业限制 |
| 西藏大学 | 西藏 | 土木工程 | 2025 | 544 | 3 | 5 去除专业限制 |

### `real-db-set-浙江-547-004`

| School | Province | Major | Year | Min score | Tier | Stage |
|---|---|---|---:|---:|---:|---|
| 东北农业大学 | 黑龙江 | 动物科学 | 2025 | 541 | 3 | 5 去除专业限制 |
| 石河子大学 | 新疆 | 基础医学 | 2025 | 546 | 3 | 5 去除专业限制 |
| 西藏大学 | 西藏 | 土木工程 | 2025 | 544 | 3 | 5 去除专业限制 |

### `real-db-set-浙江-549-005`

| School | Province | Major | Year | Min score | Tier | Stage |
|---|---|---|---:|---:|---:|---|
| 河南大学 | 河南 | 生物工程 | 2025 | 549 | 3 | 5 去除专业限制 |
| 东北农业大学 | 黑龙江 | 动物科学 | 2025 | 541 | 3 | 5 去除专业限制 |
| 石河子大学 | 新疆 | 基础医学 | 2025 | 546 | 3 | 5 去除专业限制 |

### `real-db-set-浙江-550-006`

| School | Province | Major | Year | Min score | Tier | Stage |
|---|---|---|---:|---:|---:|---|
| 河南大学 | 河南 | 生物工程 | 2025 | 549 | 3 | 5 去除专业限制 |
| 贵州大学 | 贵州 | 环境科学 | 2025 | 550 | 3 | 5 去除专业限制 |
| 东北农业大学 | 黑龙江 | 生物科学 | 2025 | 550 | 3 | 5 去除专业限制 |

### `real-db-set-浙江-557-007`

| School | Province | Major | Year | Min score | Tier | Stage |
|---|---|---|---:|---:|---:|---|
| 河南大学 | 河南 | 生物工程 | 2025 | 549 | 3 | 5 去除专业限制 |
| 山西大学 | 山西 | 智慧建筑与建造 | 2025 | 557 | 3 | 5 去除专业限制 |
| 贵州大学 | 贵州 | 环境科学 | 2025 | 550 | 3 | 5 去除专业限制 |

### `real-db-set-浙江-568-008`

| School | Province | Major | Year | Min score | Tier | Stage |
|---|---|---|---:|---:|---:|---|
| 河南大学 | 河南 | 软件工程 | 2025 | 567 | 3 | 5 去除专业限制 |
| 河南大学 | 河南 | 生物工程 | 2025 | 549 | 3 | 5 去除专业限制 |
| 华南农业大学 | 广东 | 园艺 | 2025 | 568 | 3 | 5 去除专业限制 |

### `real-db-set-浙江-569-009`

| School | Province | Major | Year | Min score | Tier | Stage |
|---|---|---|---:|---:|---:|---|
| 石河子大学 | 新疆 | 预防医学 | 2025 | 558 | 3 | 4 大类兜底 |
| 南京中医药大学 | 江苏 | 护理学 | 2025 | 565 | 3 | 4 大类兜底 |
| 成都中医药大学 | 四川 | 康复治疗学 | 2025 | 553 | 3 | 4 大类兜底 |

### `real-db-set-浙江-575-010`

| School | Province | Major | Year | Min score | Tier | Stage |
|---|---|---|---:|---:|---:|---|
| 石河子大学 | 新疆 | 药学 | 2025 | 571 | 3 | 3 上层大类近邻簇 |
| 石河子大学 | 新疆 | 中药学 | 2025 | 570 | 3 | 3 上层大类近邻簇 |
| 南京中医药大学 | 江苏 | 护理学 | 2025 | 565 | 3 | 3 上层大类近邻簇 |

## 失败 Case 分析

唯一失败样本是 `real-db-set-浙江-569-009`。它不是由于系统未返回候选，也不是由于 hallucination；报告中 `hallucination_rate=0.000`，transcript 中也能看到非空的 `major_geo_relax`。

失败原因在于隐藏妥协目标和 Agent 实际证据之间不匹配：

- persona 的隐藏目标要求 `relaxation_stage=5`，即“去除专业限制”，并给出跨省、专业不限后的更高层次志愿集合。
- 隐藏 `volunteer_set` 包含河南大学软件工程、河南大学生物工程、华南农业大学园艺、山西大学生物科学类、山西大学工商管理、新疆大学纺织工程、新疆大学土木工程、贵州大学环境科学、东北农业大学生物科学、东北农业大学动物科学等。
- `app_pareto` 实际提出的是 stage 4“大类兜底”候选，如石河子大学预防医学、南京中医药大学护理学、成都中医药大学康复治疗学、青海大学药学和青海大学护理学。
- 两组候选在学校层面和学校-专业二元组层面均没有交集，因此 deterministic judge 判定“未观察到命中隐藏妥协条件的学校和分数证据”。

这个失败样本说明当前 `app_pareto` 虽然具备联合专业+地域放宽能力，但 staged relaxation 的阶段选择本身仍是可评估对象：在部分 case 中，Agent 会优先停留在更近的专业大类放宽阶段，没有退到隐藏 persona 所要求的 `any_major` 证据集合。论文中应将 `0.900` 写作当前闭环结果，而不是 100% 成功。

## Baseline 对照说明

`hard_constraint` 的作用是保持论文对照清晰：它只报告当前显性硬约束下的可达志愿，不主动进行 Pareto 谈判。transcript 中 `pareto_opportunities` 的 `geo_relax`、`major_relax` 和 `major_geo_relax` 均为空列表，因此不会向用户展示“同时放宽专业与地域后可获得更高层次志愿”的反事实证据。

这也解释了为什么 baseline 的 `mean_hallucination_rate=0.000` 但 `elicitation_success_rate=0.000`：它没有虚构事实，但也没有触发隐藏妥协。换言之，baseline 是事实保守的硬约束响应系统，而 `app_pareto` 是证据驱动的偏好妥协发现系统。

## 论文可引用结论

在 10 个真实 PostgreSQL 数据库生成的冰山画像样本上，`app_pareto` 相比 `hard_constraint` 明显提升了多轮偏好妥协效果：`elicitation_success_rate` 从 0.000 提升到 0.900，`mean_pareto_gain` 从 0.000 提升到 0.900，同时两者 `mean_hallucination_rate` 均为 0.000。逐例 transcript 显示，该提升来自数据、Agent 与 Benchmark 三层闭环：数据层提供真实最低分/位次和 `major_tree_final_reviewed.json` 的层级放宽本体，Agent 在不读取 hidden persona 的情况下，仅基于用户显式约束和真实 DB 查询结果触发 `major_geo_relax`，Benchmark 则通过冰山画像和 deterministic judge 判断是否命中隐藏妥协集合。唯一失败样本 `real-db-set-浙江-569-009` 表明，当前 Agent 在 staged relaxation 阶段选择上仍可能停留在较近的大类兜底，未命中 persona 要求的任意专业志愿集合，这是后续优化的主要方向。
