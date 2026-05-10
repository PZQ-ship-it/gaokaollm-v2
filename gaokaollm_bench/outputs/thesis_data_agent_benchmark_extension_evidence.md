# 数据 + Agent + Benchmark 扩展实验逐例证据附录

本文档服务毕业论文“数据 + Agent + Benchmark”贡献结构，整理四组扩展实验的逐例证据链：`school_strength_v1`、`tuition_value_v1`、`major_quality_v1`、`employment_outcome_v1`。

当前论文主实验仍是 `major_geo_v1 + risk_band_v1`。本附录中的四组实验不替代主实验，而是证明同一套数据生成、Agent 探测、Benchmark 沙盒和事实/过程评价流程，可以接入更多真实 PostgreSQL 证据维度。

## 1. 实验来源与复现路径

本附录只引用现有产物，不新增实验、不改代码、不启动数据库、不调用 LLM：

| 实验 | 数据来源 | 输出目录 | 关键证据 |
|---|---|---|---|
| `school_strength_v1` | `gaokaollm_bench/sample_data/iceberg_personas_school_strength_real_db_10.json` | `gaokaollm_bench/outputs/agent_benchmark_school_strength_v1/` | `school_major_strengths`、最低分、最低位次、排名/评级 |
| `tuition_value_v1` | `gaokaollm_bench/sample_data/iceberg_personas_tuition_value_real_db_10.json` | `gaokaollm_bench/outputs/agent_benchmark_tuition_value_v1/` | `admission_plans.tuition`、学费增量、最低分、学校 ranking/tier |
| `major_quality_v1` | `gaokaollm_bench/sample_data/iceberg_personas_major_quality_real_db_10.json` | `gaokaollm_bench/outputs/agent_benchmark_major_quality_v1/` | `school_major_quality_profiles`、`quality_score`、专业排名、学科评估、特色/重点/满意度 |
| `employment_outcome_v1` | `gaokaollm_bench/sample_data/iceberg_personas_employment_outcome_real_db_10.json` | `gaokaollm_bench/outputs/agent_benchmark_employment_outcome_v1/` | `major_employment_outcome_profiles`、`outcome_score`、就业排名、行业、岗位、薪资分布 |

四组实验均使用 `app_pareto` 与 `hard_constraint` 对照。`app_pareto` 表示接入证据驱动 Pareto 谈判的业务 Agent；`hard_constraint` 表示只报告当前显性硬约束下可达志愿、不主动提出放宽谈判的 baseline。

被测 Agent 不读取 `implicit_flexibilities` 或 `volunteer_set`。这些 hidden persona 字段只用于模拟用户和 evaluator ground truth；Agent 输入只来自用户显式话语和 PostgreSQL 查询结果。

## 2. 聚合指标核对表

| 实验 | Target | Cases | Success | Elicitation Success | Mean Pareto Gain | Mean Hallucination | Avg Turns |
|---|---|---:|---:|---:|---:|---:|---:|
| `school_strength_v1` | `app_pareto` | 10 | 10 | 1.000 | 15.000 | 0.000 | 5.00 |
| `school_strength_v1` | `hard_constraint` | 10 | 0 | 0.000 | 0.000 | 0.000 | 11.00 |
| `tuition_value_v1` | `app_pareto` | 10 | 10 | 1.000 | 1.000 | 0.000 | 5.00 |
| `tuition_value_v1` | `hard_constraint` | 10 | 0 | 0.000 | 0.000 | 0.000 | 11.00 |
| `major_quality_v1` | `app_pareto` | 10 | 10 | 1.000 | 16.000 | 0.000 | 5.00 |
| `major_quality_v1` | `hard_constraint` | 10 | 0 | 0.000 | 0.000 | 0.050 | 11.00 |
| `employment_outcome_v1` | `app_pareto` | 10 | 10 | 1.000 | 49.000 | 0.000 | 3.00 |
| `employment_outcome_v1` | `hard_constraint` | 10 | 0 | 0.000 | 0.000 | 0.000 | 11.00 |

指标速记：

- `school_strength_v1`: `app_pareto 1.000 / 15.000 / 0.000 / 5.00` vs `hard_constraint 0.000 / 0.000 / 0.000 / 11.00`。
- `tuition_value_v1`: `app_pareto 1.000 / 1.000 / 0.000 / 5.00` vs `hard_constraint 0.000 / 0.000 / 0.000 / 11.00`。
- `major_quality_v1`: `app_pareto 1.000 / 16.000 / 0.000 / 5.00` vs `hard_constraint 0.000 / 0.000 / 0.050 / 11.00`。
- `employment_outcome_v1`: `app_pareto 1.000 / 49.000 / 0.000 / 3.00` vs `hard_constraint 0.000 / 0.000 / 0.000 / 11.00`。

论文写作时建议把这四组称为扩展实验：它们证明“数据证据维度可扩展”，而不是把主实验从 `major_geo_v1 + risk_band_v1` 改写为六组并列主实验。

## 3. `school_strength_v1` 逐例结果

该组实验考察 `strength_relax`。显性用户偏好是更看重学科或专业实力；隐藏弹性是如果 Agent 给出真实最低分、最低位次和排名/评级证据，用户可接受跨省实力更强的可达学校。

### 3.1 逐例结果表

| case_id | 分数 | 目标专业 | app 成功 | baseline 成功 | app turns | baseline turns | app/base hallucination | pareto_gain |
|---|---:|---|---|---|---:|---:|---|---:|
| `real-db-set-浙江-520-001` | 520 | 临床医学 | True | False | 5 | 11 | 0.0 / 0.0 | 15 |
| `real-db-set-浙江-521-002` | 521 | 临床医学 | True | False | 5 | 11 | 0.0 / 0.0 | 15 |
| `real-db-set-浙江-522-003` | 522 | 临床医学 | True | False | 5 | 11 | 0.0 / 0.0 | 15 |
| `real-db-set-浙江-523-004` | 523 | 临床医学 | True | False | 5 | 11 | 0.0 / 0.0 | 15 |
| `real-db-set-浙江-524-005` | 524 | 临床医学 | True | False | 5 | 11 | 0.0 / 0.0 | 15 |
| `real-db-set-浙江-525-006` | 525 | 临床医学 | True | False | 5 | 11 | 0.0 / 0.0 | 15 |
| `real-db-set-浙江-526-007` | 526 | 临床医学 | True | False | 5 | 11 | 0.0 / 0.0 | 15 |
| `real-db-set-浙江-527-008` | 527 | 临床医学 | True | False | 5 | 11 | 0.0 / 0.0 | 15 |
| `real-db-set-浙江-528-009` | 528 | 临床医学 | True | False | 5 | 11 | 0.0 / 0.0 | 15 |
| `real-db-set-浙江-529-010` | 529 | 临床医学 | True | False | 5 | 11 | 0.0 / 0.0 | 15 |

### 3.2 `strength_relax` 证据表

每个成功 case 至少有一个来自 transcript `internal_state.pareto_opportunities.strength_relax` 的真实候选：

| case_id | 学校 | 省份/城市 | 专业 | 最低分 | 最低位次 | 排名/评级证据 |
|---|---|---|---|---:|---:|---|
| `real-db-set-浙江-520-001` | 黑龙江中医药大学 | 黑龙江/哈尔滨市 | 中西医临床医学 | 492 | 178059 | `major_strength_rank=1`, `rating=A+` |
| `real-db-set-浙江-521-002` | 黑龙江中医药大学 | 黑龙江/哈尔滨市 | 中西医临床医学 | 492 | 178059 | `major_strength_rank=1`, `rating=A+` |
| `real-db-set-浙江-522-003` | 黑龙江中医药大学 | 黑龙江/哈尔滨市 | 中西医临床医学 | 492 | 178059 | `major_strength_rank=1`, `rating=A+` |
| `real-db-set-浙江-523-004` | 黑龙江中医药大学 | 黑龙江/哈尔滨市 | 中西医临床医学 | 492 | 178059 | `major_strength_rank=1`, `rating=A+` |
| `real-db-set-浙江-524-005` | 黑龙江中医药大学 | 黑龙江/哈尔滨市 | 中西医临床医学 | 492 | 178059 | `major_strength_rank=1`, `rating=A+` |
| `real-db-set-浙江-525-006` | 黑龙江中医药大学 | 黑龙江/哈尔滨市 | 中西医临床医学 | 492 | 178059 | `major_strength_rank=1`, `rating=A+` |
| `real-db-set-浙江-526-007` | 黑龙江中医药大学 | 黑龙江/哈尔滨市 | 中西医临床医学 | 492 | 178059 | `major_strength_rank=1`, `rating=A+` |
| `real-db-set-浙江-527-008` | 黑龙江中医药大学 | 黑龙江/哈尔滨市 | 中西医临床医学 | 492 | 178059 | `major_strength_rank=1`, `rating=A+` |
| `real-db-set-浙江-528-009` | 黑龙江中医药大学 | 黑龙江/哈尔滨市 | 中西医临床医学 | 492 | 178059 | `major_strength_rank=1`, `rating=A+` |
| `real-db-set-浙江-529-010` | 黑龙江中医药大学 | 黑龙江/哈尔滨市 | 中西医临床医学 | 492 | 178059 | `major_strength_rank=1`, `rating=A+` |

该结果说明：当用户显性强调专业实力时，`app_pareto` 能把“实力更强”落成最低分、最低位次和排名/评级证据，而 `hard_constraint` 不主动生成 `strength_relax` 谈判机会。

## 4. `tuition_value_v1` 逐例结果

该组实验考察 `tuition_value_relax`。显性用户偏好是学费预算保守；隐藏弹性是如果 Agent 给出学费增量、最低分和学校收益证据，用户可接受小幅超预算方案。

### 4.1 逐例结果表

| case_id | 分数 | 目标专业 | app 成功 | baseline 成功 | app turns | baseline turns | app/base hallucination | pareto_gain |
|---|---:|---|---|---|---:|---:|---|---:|
| `real-db-set-浙江-553-001` | 553 | 软件 | True | False | 5 | 11 | 0.0 / 0.0 | 1 |
| `real-db-set-浙江-554-002` | 554 | 软件 | True | False | 5 | 11 | 0.0 / 0.0 | 1 |
| `real-db-set-浙江-555-003` | 555 | 软件 | True | False | 5 | 11 | 0.0 / 0.0 | 1 |
| `real-db-set-浙江-556-004` | 556 | 软件 | True | False | 5 | 11 | 0.0 / 0.0 | 1 |
| `real-db-set-浙江-567-005` | 567 | 软件 | True | False | 5 | 11 | 0.0 / 0.0 | 1 |
| `real-db-set-浙江-568-006` | 568 | 软件 | True | False | 5 | 11 | 0.0 / 0.0 | 1 |
| `real-db-set-浙江-569-007` | 569 | 软件 | True | False | 5 | 11 | 0.0 / 0.0 | 1 |
| `real-db-set-浙江-570-008` | 570 | 软件 | True | False | 5 | 11 | 0.0 / 0.0 | 1 |
| `real-db-set-浙江-571-009` | 571 | 软件 | True | False | 5 | 11 | 0.0 / 0.0 | 1 |
| `real-db-set-浙江-572-010` | 572 | 软件 | True | False | 5 | 11 | 0.0 / 0.0 | 1 |

### 4.2 `tuition_value_relax` 证据表

每个成功 case 至少有一个来自 transcript `internal_state.pareto_opportunities.tuition_value_relax` 的真实候选：

| case_id | 学校 | 省份/城市 | 专业 | 最低分 | 学费 | 学费增量 | ranking/tier |
|---|---|---|---|---:|---:|---:|---|
| `real-db-set-浙江-553-001` | 西北师范大学 | 甘肃/兰州市 | 软件工程 | 553 | 9750 | 3750 | ranking=131, tier=2 |
| `real-db-set-浙江-554-002` | 西北师范大学 | 甘肃/兰州市 | 软件工程 | 553 | 9750 | 3750 | ranking=131, tier=2 |
| `real-db-set-浙江-555-003` | 西北师范大学 | 甘肃/兰州市 | 软件工程 | 553 | 9750 | 3750 | ranking=131, tier=2 |
| `real-db-set-浙江-556-004` | 西北师范大学 | 甘肃/兰州市 | 软件工程 | 553 | 9750 | 3750 | ranking=131, tier=2 |
| `real-db-set-浙江-567-005` | 河南大学 | 河南/郑州市 | 软件工程 | 567 | 15000 | 9000 | ranking=84, tier=3 |
| `real-db-set-浙江-568-006` | 河南大学 | 河南/郑州市 | 软件工程 | 567 | 15000 | 9000 | ranking=84, tier=3 |
| `real-db-set-浙江-569-007` | 河南大学 | 河南/郑州市 | 软件工程 | 567 | 15000 | 9000 | ranking=84, tier=3 |
| `real-db-set-浙江-570-008` | 河南大学 | 河南/郑州市 | 软件工程 | 567 | 15000 | 9000 | ranking=84, tier=3 |
| `real-db-set-浙江-571-009` | 河南大学 | 河南/郑州市 | 软件工程 | 567 | 15000 | 9000 | ranking=84, tier=3 |
| `real-db-set-浙江-572-010` | 河南大学 | 河南/郑州市 | 软件工程 | 567 | 15000 | 9000 | ranking=84, tier=3 |

该结果说明：`admission_plans.tuition` 可以作为数据贡献的一部分进入 Pareto 谈判。Agent 不是泛泛建议“多花钱”，而是把学费增量、最低分和学校 ranking/tier 收益一起呈现给用户。

## 5. `major_quality_v1` 逐例结果

该组实验考察 `major_quality_relax`。显性用户偏好是优先保持目标专业；隐藏弹性是如果 Agent 给出专业质量证据，用户可接受跨省或替代学校中的更强学校-专业方案。

### 5.1 逐例结果表

| case_id | 分数 | 目标专业 | app 成功 | baseline 成功 | app turns | baseline turns | app/base hallucination | pareto_gain |
|---|---:|---|---|---|---:|---:|---|---:|
| `real-db-set-浙江-600-001` | 600 | 软件 | True | False | 5 | 11 | 0.0 / 0.5 | 16 |
| `real-db-set-浙江-601-002` | 601 | 软件 | True | False | 5 | 11 | 0.0 / 0.0 | 16 |
| `real-db-set-浙江-602-003` | 602 | 软件 | True | False | 5 | 11 | 0.0 / 0.0 | 16 |
| `real-db-set-浙江-603-004` | 603 | 软件 | True | False | 5 | 11 | 0.0 / 0.0 | 16 |
| `real-db-set-浙江-604-005` | 604 | 软件 | True | False | 5 | 11 | 0.0 / 0.0 | 16 |
| `real-db-set-浙江-605-006` | 605 | 软件 | True | False | 5 | 11 | 0.0 / 0.0 | 16 |
| `real-db-set-浙江-606-007` | 606 | 软件 | True | False | 5 | 11 | 0.0 / 0.0 | 16 |
| `real-db-set-浙江-607-008` | 607 | 软件 | True | False | 5 | 11 | 0.0 / 0.0 | 16 |
| `real-db-set-浙江-608-009` | 608 | 软件 | True | False | 5 | 11 | 0.0 / 0.0 | 16 |
| `real-db-set-浙江-609-010` | 609 | 软件 | True | False | 5 | 11 | 0.0 / 0.0 | 16 |

### 5.2 `major_quality_relax` 证据表

每个成功 case 至少有一个来自 transcript `internal_state.pareto_opportunities.major_quality_relax` 的真实候选。该表必须包含专业质量证据，不能只写“学校更好”。

| case_id | 学校 | 省份/城市 | 专业 | 最低分 | 最低位次 | quality_score / gain | evidence_sources |
|---|---|---|---|---:|---:|---|---|
| `real-db-set-浙江-600-001` | 重庆邮电大学 | 重庆/南岸区 | 软件工程 | 600 | 51826 | 97.0 / 16.0 | 重点专业 国家级；专业排名 46, 评级 B+ |
| `real-db-set-浙江-601-002` | 重庆邮电大学 | 重庆/南岸区 | 软件工程 | 600 | 51826 | 97.0 / 16.0 | 重点专业 国家级；专业排名 46, 评级 B+ |
| `real-db-set-浙江-602-003` | 重庆邮电大学 | 重庆/南岸区 | 软件工程 | 600 | 51826 | 97.0 / 16.0 | 重点专业 国家级；专业排名 46, 评级 B+ |
| `real-db-set-浙江-603-004` | 重庆邮电大学 | 重庆/南岸区 | 软件工程 | 600 | 51826 | 97.0 / 16.0 | 重点专业 国家级；专业排名 46, 评级 B+ |
| `real-db-set-浙江-604-005` | 重庆邮电大学 | 重庆/南岸区 | 软件工程 | 600 | 51826 | 97.0 / 16.0 | 重点专业 国家级；专业排名 46, 评级 B+ |
| `real-db-set-浙江-605-006` | 重庆邮电大学 | 重庆/南岸区 | 软件工程 | 600 | 51826 | 97.0 / 16.0 | 重点专业 国家级；专业排名 46, 评级 B+ |
| `real-db-set-浙江-606-007` | 重庆邮电大学 | 重庆/南岸区 | 软件工程 | 600 | 51826 | 97.0 / 16.0 | 重点专业 国家级；专业排名 46, 评级 B+ |
| `real-db-set-浙江-607-008` | 重庆邮电大学 | 重庆/南岸区 | 软件工程 | 600 | 51826 | 97.0 / 16.0 | 重点专业 国家级；专业排名 46, 评级 B+ |
| `real-db-set-浙江-608-009` | 重庆邮电大学 | 重庆/南岸区 | 软件工程 | 600 | 51826 | 97.0 / 16.0 | 重点专业 国家级；专业排名 46, 评级 B+ |
| `real-db-set-浙江-609-010` | 重庆邮电大学 | 重庆/南岸区 | 软件工程 | 600 | 51826 | 97.0 / 16.0 | 重点专业 国家级；专业排名 46, 评级 B+ |

该结果说明：`school_major_quality_profiles` 可以把专业排名、重点专业、特色专业、满意度等来源统一为可谈判证据。`major_quality_relax` 的价值不在于泛化地说“这所学校更好”，而在于给出学校-专业层面的 `quality_score`、`quality_gain` 和来源标签。

## 6. `employment_outcome_v1` 逐例结果

该组实验考察 `employment_outcome_relax`。显性用户偏好是希望就业和薪资稳定，但对省外或相近专业较保守；隐藏弹性是如果 Agent 给出真实最低分、最低位次和就业排名、行业、岗位或薪资证据，用户可接受就业结果更强的同专业或近邻专业方案。

### 6.1 逐例结果表

| case_id | 分数 | 目标专业 | app 成功 | baseline 成功 | app turns | baseline turns | app/base hallucination | pareto_gain |
|---|---:|---|---|---|---:|---:|---|---:|
| `real-db-set-浙江-520-001` | 520 | 机械设计制造及其自动化 | True | False | 3 | 11 | 0.0 / 0.0 | 49 |
| `real-db-set-浙江-522-002` | 522 | 机械设计制造及其自动化 | True | False | 3 | 11 | 0.0 / 0.0 | 49 |
| `real-db-set-浙江-524-003` | 524 | 机械设计制造及其自动化 | True | False | 3 | 11 | 0.0 / 0.0 | 49 |
| `real-db-set-浙江-526-004` | 526 | 机械设计制造及其自动化 | True | False | 3 | 11 | 0.0 / 0.0 | 49 |
| `real-db-set-浙江-528-005` | 528 | 机械设计制造及其自动化 | True | False | 3 | 11 | 0.0 / 0.0 | 49 |
| `real-db-set-浙江-530-006` | 530 | 机械设计制造及其自动化 | True | False | 3 | 11 | 0.0 / 0.0 | 49 |
| `real-db-set-浙江-532-007` | 532 | 机械设计制造及其自动化 | True | False | 3 | 11 | 0.0 / 0.0 | 49 |
| `real-db-set-浙江-534-008` | 534 | 机械设计制造及其自动化 | True | False | 3 | 11 | 0.0 / 0.0 | 49 |
| `real-db-set-浙江-536-009` | 536 | 机械设计制造及其自动化 | True | False | 3 | 11 | 0.0 / 0.0 | 49 |
| `real-db-set-浙江-538-010` | 538 | 机械设计制造及其自动化 | True | False | 3 | 11 | 0.0 / 0.0 | 49 |

### 6.2 `employment_outcome_relax` 证据表

每个成功 case 至少有一个来自 transcript `internal_state.pareto_opportunities.employment_outcome_relax` 的真实候选。候选必须包含就业结果证据，不能只写“就业更好”。

| case_id | 学校 | 省份/城市 | 专业 | 最低分 | 最低位次 | outcome_score / gain | employment_rank | top_industry | salary_distribution |
|---|---|---|---|---:|---:|---|---:|---|---|
| `real-db-set-浙江-520-001` | 广西师范大学 | 广西/桂林市 | 工业设计 | 513 | 156857 | 100.0 / 49.0 | 4 | 互联网/电子商务 | items=["面议 ","50000以上 ","4500-5999 "]; ratios=[66%,16%,16%] |
| `real-db-set-浙江-522-002` | 广西师范大学 | 广西/桂林市 | 工业设计 | 513 | 156857 | 100.0 / 49.0 | 4 | 互联网/电子商务 | items=["面议 ","50000以上 ","4500-5999 "]; ratios=[66%,16%,16%] |
| `real-db-set-浙江-524-003` | 广西师范大学 | 广西/桂林市 | 工业设计 | 513 | 156857 | 100.0 / 49.0 | 4 | 互联网/电子商务 | items=["面议 ","50000以上 ","4500-5999 "]; ratios=[66%,16%,16%] |
| `real-db-set-浙江-526-004` | 广西师范大学 | 广西/桂林市 | 工业设计 | 513 | 156857 | 100.0 / 49.0 | 4 | 互联网/电子商务 | items=["面议 ","50000以上 ","4500-5999 "]; ratios=[66%,16%,16%] |
| `real-db-set-浙江-528-005` | 广西师范大学 | 广西/桂林市 | 工业设计 | 513 | 156857 | 100.0 / 49.0 | 4 | 互联网/电子商务 | items=["面议 ","50000以上 ","4500-5999 "]; ratios=[66%,16%,16%] |
| `real-db-set-浙江-530-006` | 广西师范大学 | 广西/桂林市 | 工业设计 | 513 | 156857 | 100.0 / 49.0 | 4 | 互联网/电子商务 | items=["面议 ","50000以上 ","4500-5999 "]; ratios=[66%,16%,16%] |
| `real-db-set-浙江-532-007` | 广西师范大学 | 广西/桂林市 | 工业设计 | 513 | 156857 | 100.0 / 49.0 | 4 | 互联网/电子商务 | items=["面议 ","50000以上 ","4500-5999 "]; ratios=[66%,16%,16%] |
| `real-db-set-浙江-534-008` | 广西师范大学 | 广西/桂林市 | 工业设计 | 513 | 156857 | 100.0 / 49.0 | 4 | 互联网/电子商务 | items=["面议 ","50000以上 ","4500-5999 "]; ratios=[66%,16%,16%] |
| `real-db-set-浙江-536-009` | 广西师范大学 | 广西/桂林市 | 工业设计 | 513 | 156857 | 100.0 / 49.0 | 4 | 互联网/电子商务 | items=["面议 ","50000以上 ","4500-5999 "]; ratios=[66%,16%,16%] |
| `real-db-set-浙江-538-010` | 广西师范大学 | 广西/桂林市 | 工业设计 | 513 | 156857 | 100.0 / 49.0 | 4 | 互联网/电子商务 | items=["面议 ","50000以上 ","4500-5999 "]; ratios=[66%,16%,16%] |

该结果说明：`major_employment_outcome_profiles` 可以把专业就业画像转化为可谈判证据。`employment_outcome_relax` 的价值不在于泛泛地说“这个方向好就业”，而在于给出可达学校、相近专业、最低分、最低位次、`outcome_score`、`outcome_gain`、就业排名、行业和薪资分布。

## 7. Baseline 对照说明

四组扩展实验中，`hard_constraint` 都没有成功触发隐藏妥协：

- `school_strength_v1`: baseline 成功 0/10，不主动产生 `strength_relax`。
- `tuition_value_v1`: baseline 成功 0/10，不主动产生 `tuition_value_relax`。
- `major_quality_v1`: baseline 成功 0/10，不主动产生有效 `major_quality_relax`，且聚合幻觉率为 0.050。
- `employment_outcome_v1`: baseline 成功 0/10，不主动产生 `employment_outcome_relax`。

这说明扩展实验中的收益来自 Agent 的证据探测和谈判机制，而不是 baseline 也能自然完成的事实问答。

## 8. 论文可引用结论

扩展实验支持“数据 + Agent + Benchmark”的论文贡献结构：数据层提供可核验的分数、位次、学费、专业质量和就业结果证据；Agent 层通过 `radar` 探测 `strength_relax`、`tuition_value_relax`、`major_quality_relax`、`employment_outcome_relax` 等 Pareto 机会；Benchmark 层用冰山画像、多轮沙盒和事实/过程联合评价检验这些机会是否真的触发用户隐藏妥协。

因此，`school_strength_v1`、`tuition_value_v1`、`major_quality_v1` 和 `employment_outcome_v1` 适合作为扩展实验写入论文，证明当前框架不只适用于专业/地域和风险组合，也可以接入新的数据证据维度。主实验结论仍应以 `major_geo_v1 + risk_band_v1` 为中心，扩展实验用于说明框架的可扩展性和数据贡献价值。
