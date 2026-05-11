# 数据 + Agent + Benchmark 论文贡献与实验结果母版

本文档用于服务毕业论文摘要、绪论、贡献总结和答辩 PPT。当前论文贡献结构不再是单纯的 “Agent + Benchmark”，而是更完整的“数据 + Agent + Benchmark”三层闭环：数据层提供可核验事实证据，Agent 层把事实证据组织成 Pareto 妥协谈判，Benchmark 层用冰山画像、多轮沙盒和事实/过程联合评价检验这种谈判是否真的触发隐藏偏好妥协。

当前论文第一版主实验仍是 `major_geo_v1 + risk_band_v1`。`school_strength_v1`、`tuition_value_v1`、`major_quality_v1`、`employment_outcome_v1`、`region_tree_v1` 作为扩展实验，用于证明同一框架可以接入更多数据证据维度，支撑“数据贡献可扩展”的论文论点。

## 研究目标

本项目面向高考志愿咨询场景，研究目标不是让大模型生成一段看似合理的单轮建议，而是在真实招生数据约束下构建并评测一个能进行多轮偏好启发的决策 Agent。核心问题是：当用户显式表达“只读某个专业”“只考虑本省”“只求稳妥”“学费别太贵”“希望就业稳定”等强硬或保守偏好时，系统能否识别其中可能存在的信息不足型锚定，并用学校、专业、最低分、最低位次、风险层级、学费、专业质量或就业结果证据，引导用户接受更优且可达的志愿集合。

论文贡献采用三层结构：

| 贡献层次 | 核心内容 | 论文作用 |
|---|---|---|
| 数据贡献 | PostgreSQL 招生快照、分数/位次、学费字段、专业树、`school_major_quality_profiles`、`major_employment_outcome_profiles`、`region_geo_tree_reviewed_v1.json`、`region_urban_tier_tree_reviewed_v1.json` | 为推荐、放宽和评测提供可核验事实基础 |
| Agent 贡献 | LangGraph 轻量 MAS `gatekeeper -> radar -> negotiator`，支持多类证据驱动 Pareto 谈判 | 证明业务 Agent 能主动提出有事实依据的偏好妥协方案 |
| Benchmark 贡献 | 冰山画像、多轮沙盒、事实/过程联合评价、`app_pareto` vs `hard_constraint` 对照 | 证明改进不是主观叙事，而是可复现实验结果 |

被测 Agent 不读取 benchmark 的 `implicit_flexibilities` 或 `volunteer_set`。这些 hidden persona 字段只用于模拟用户和 evaluator ground truth；Agent 输入只来自用户显式话语和 PostgreSQL 查询结果。

## 数据贡献

数据层是本文区别于普通大模型问答系统的基础。所有推荐、放宽和评测结论都必须能回到本地 PostgreSQL 快照或标准化数据层中找到证据。

| 数据层 | 主要字段或来源 | 支撑能力 |
|---|---|---|
| 招生事实快照 | `admission_scores`、`school_admission_scores`、`score_rank_segments`、`batch_lines` | 最低分、最低位次、批次、分数可达性 |
| 招生计划学费 | `admission_plans.tuition` | `tuition_value_relax` 的学费增量和预算性价比证据 |
| 学校与专业维表 | `schools`、`majors`、专业树 artifact | 地域、学校 tier/ranking、专业层级放宽 |
| 专业质量标准化层 | `discipline_major_mappings`、`school_major_quality_signals`、`school_major_quality_profiles` | `major_quality_relax` 的质量评分、专业排名、学科评估、特色/重点/满意度证据 |
| 就业结果标准化层 | `major_employment_profiles` -> `major_employment_outcome_profiles` | `employment_outcome_relax` 的就业排名、行业、岗位、薪资和 `outcome_score` 证据 |
| 地域树 reviewed v1 标准化层 | `region_geo_tree_reviewed_v1.json`、`region_urban_tier_tree_reviewed_v1.json`、HITL review packet、coverage report | `region_tree_relax` 的 `geo_block_relax`、`urban_tier_relax`、源/目标地域节点和树置信度证据 |

数据贡献的重点不是把所有表简单堆进数据库，而是把招生事实、专业质量、就业画像和地域树 reviewed 节点转化为 Agent 可表达、Benchmark 可核验、Transcript 可追溯的证据字段。

## Benchmark 贡献

`gaokaollm_bench` 将评测对象从静态问答正确率扩展为多轮偏好妥协过程。它先从真实 DB gap 出发，比较显性约束下的 baseline 候选和受控放宽后的 relaxed 候选，再逆向生成冰山画像。每个 persona 显式区分用户说出口的红线和只有在充分证据下才会接受的隐性妥协条件。

当前 benchmark 覆盖两组主实验画像和五组扩展画像：

| Benchmark 画像 | 类型 | 显性红线 | 隐性妥协 | 评价重点 |
|---|---|---|---|---|
| `major_geo_v1` | 主实验 | 坚持原专业、地域或本省约束 | 看到真实学校、专业和最低分证据后，可接受跨省与跨专业联合放宽 | 学校层次与志愿集合质量提升 |
| `risk_band_v1` | 主实验 | 只求稳妥，不接受冲刺风险 | 看到最低分、最低位次、分差、位次差和风险层级证据后，可接受 `chong/wen/bao` 冲稳保组合 | 志愿组合完整性和风险结构提升 |
| `school_strength_v1` | 扩展实验 | 看重学科实力或专业排名 | 看到最低分、最低位次、排名和评级证据后，可接受跨省实力更强的可达学校 | 学校/学科实力证据提升 |
| `tuition_value_v1` | 扩展实验 | 学费预算保守 | 看到学费增量、最低分和学校收益证据后，可接受小幅超预算方案 | 预算性价比谈判 |
| `major_quality_v1` | 扩展实验 | 优先保持目标专业 | 看到专业质量证据后，可接受跨省或替代学校中的更强学校-专业方案 | 专业质量证据跃迁 |
| `employment_outcome_v1` | 扩展实验 | 希望就业和薪资稳定，但对省外或相近专业保守 | 看到就业排名、行业、岗位、薪资和最低分证据后，可接受就业结果更强的近邻方案 | 就业导向放宽 |
| `region_tree_v1` | 扩展实验 | 坚持杭州/浙江/别太远/想去好城市等地域偏好 | 看到真实最低分/位次和 reviewed 地域树阶段证据后，可接受相邻地理板块或城市层级候选 | 地域树层级放宽 |

Benchmark 的关键设计包括：

- 冰山画像：`explicit_red_lines` 记录显性红线，`implicit_flexibilities` 记录隐藏妥协触发条件。
- 真实 DB gap：样本来自真实录取数据和标准化证据层，而不是人工编造学校、专业和分数。
- 多轮沙盒：被测 Agent 只能看到用户话语，用户模拟器持有完整 persona，通过自然语言逐步反馈。
- 联合评价：确定性事实裁判约束幻觉率，过程裁判评价是否成功启发隐性妥协并产生 Pareto gain。
- Baseline 对照：`hard_constraint` 只报告当前显性硬约束下可达志愿，不主动提出 Pareto opportunities。

专业树和 probe 是 benchmark 的基础设施。专业树最终包含 82 个节点、52 个叶子簇和 19,096 条叶子 observed names；probe 消融用于支撑专业层级放宽的可审计性，不作为本轮 Agent 主贡献。

## Agent 贡献

业务 Agent 使用 LangGraph 编排，主流程为：

```text
gatekeeper -> radar -> negotiator
```

| 节点 | 职责 | 论文作用 |
|---|---|---|
| `gatekeeper` | 从用户话语中抽取分数、省份、专业、预算、选科、风险偏好、质量偏好和就业导向，并查询当前硬约束 baseline | 确认显性约束和当前可达空间 |
| `radar` | 调度确定性 SQL 探针，寻找放宽某个偏好维度后的 Pareto 机会 | 发现可谈判的反事实证据 |
| `negotiator` | 只基于真实查询结果组织回复 | 用学校、专业、最低分、位次、学费、风险、质量和就业证据进行谈判 |

当前 Agent 能力矩阵如下：

| 能力 | 类型 | 放宽对象 | 输出证据 |
|---|---|---|---|
| `major_geo_relax` | 主能力 | 专业 + 地域联合放宽 | 学校、专业、省份、最低分、tier/ranking、专业树阶段 |
| `risk_band_relax` | 主能力 | “只求稳/不要冲”的风险偏好 | `score_margin`、`rank_gap`、`chong/wen/bao` 风险层级、最低分/位次 |
| `strength_relax` | 扩展能力 | 学校/学科实力偏好 | 排名、评级、最低分、最低位次 |
| `tuition_value_relax` | 扩展能力 | 学费预算上限的小幅放宽 | 学费、学费增量、最低分、学校 tier/ranking 改善 |
| `major_quality_relax` | 扩展能力 | 专业质量证据增强 | `quality_score`、`quality_gain`、专业排名/学科评估/特色/重点/满意度证据 |
| `employment_outcome_relax` | 扩展能力 | 就业导向与相近专业就业结果 | `employment_rank`、`top_city`、`top_industry`、`job_distribution`、`salary_distribution`、`outcome_score`、`outcome_gain` |
| `region_tree_relax` | 扩展能力 | 地理板块或城市层级偏好 | `geo_block_relax` / `urban_tier_relax`、源地域节点、目标地域节点、树置信度、最低分/位次、学校 tier/ranking |

对照系统为 `hard_constraint`。它只复用约束抽取和 baseline 查询，报告当前硬约束下的可达志愿，不主动谈判，也不产生上述 Pareto opportunities。这个对照用于衡量“只迎合显性红线”和“证据驱动 Pareto 谈判”之间的差异。`region_tree_v1` 中的城市层级只作为 reviewed region-tree 证据，不直接等价于就业机会、生活成本或城市生活质量；其 Pareto gain 仍按学校 tier/ranking 改善计算。

## 实验设置

所有实验均使用 `app_pareto` 与 `hard_constraint` 两个 target，并采用 offline deterministic judge。结果产物包含 transcripts、逐例 reports、`summary.json` 和 Markdown summary。

| 实验 | 类型 | Persona 数据 | 输出目录 |
|---|---|---|---|
| `major_geo_v1` | 主实验 | `gaokaollm_bench/sample_data/iceberg_personas_major_hierarchy_real_db_10.json` | `gaokaollm_bench/outputs/agent_benchmark_major_geo_v1/` |
| `risk_band_v1` | 主实验 | `gaokaollm_bench/sample_data/iceberg_personas_risk_band_real_db_10.json` | `gaokaollm_bench/outputs/agent_benchmark_risk_band_v1/` |
| `school_strength_v1` | 扩展实验 | `gaokaollm_bench/sample_data/iceberg_personas_school_strength_real_db_10.json` | `gaokaollm_bench/outputs/agent_benchmark_school_strength_v1/` |
| `tuition_value_v1` | 扩展实验 | `gaokaollm_bench/sample_data/iceberg_personas_tuition_value_real_db_10.json` | `gaokaollm_bench/outputs/agent_benchmark_tuition_value_v1/` |
| `major_quality_v1` | 扩展实验 | `gaokaollm_bench/sample_data/iceberg_personas_major_quality_real_db_10.json` | `gaokaollm_bench/outputs/agent_benchmark_major_quality_v1/` |
| `employment_outcome_v1` | 扩展实验 | `gaokaollm_bench/sample_data/iceberg_personas_employment_outcome_real_db_10.json` | `gaokaollm_bench/outputs/agent_benchmark_employment_outcome_v1/` |
| `region_tree_v1` | 扩展实验 | `gaokaollm_bench/sample_data/iceberg_personas_region_tree_real_db_10.json` | `gaokaollm_bench/outputs/agent_benchmark_region_tree_v1/` |

论文引用结果来自：

- `gaokaollm_bench/outputs/agent_benchmark_major_geo_v1_summary.md`
- `gaokaollm_bench/outputs/agent_benchmark_major_geo_v1_evidence.md`
- `gaokaollm_bench/outputs/agent_benchmark_risk_band_v1_summary.md`
- `gaokaollm_bench/outputs/agent_benchmark_risk_band_v1_evidence.md`
- `gaokaollm_bench/outputs/thesis_data_agent_benchmark_extension_evidence.md`
- `gaokaollm_bench/outputs/agent_benchmark_region_tree_v1_summary.md`
- `gaokaollm_bench/outputs/agent_benchmark_region_tree_v1_evidence.md`
- `gaokaollm_bench/outputs/agent_benchmark_multi_axis_v1_summary.md`
- `gaokaollm_bench/outputs/agent_benchmark_multi_axis_v1_evidence.md`
- `gaokaollm_bench/outputs/agent_benchmark_multi_axis_v2_summary.md`
- `gaokaollm_bench/outputs/agent_benchmark_multi_axis_v2_evidence.md`
- `gaokaollm_bench/outputs/thesis_method_experiment_chapters.md`

## Benchmark 压力测试

除七组实验事实表外，论文可单独报告多轴 Benchmark 压力测试。该压力测试不替代主实验 `major_geo_v1 + risk_band_v1`，也不把当前七实验口径改写为第八组主实验；它只组合已有 relax 能力，检查两个隐藏放宽轴同时成立时的证据编排能力。

| 压力测试 | 定位 | 三类 profile | `app_pareto` | `hard_constraint` | profile 成功分布 |
|---|---|---|---:|---:|---|
| `multi_axis_v1` | 历史压力测试版本 | `major_geo_risk`、`quality_tuition`、`employment_region` | `0.533 / 1.133 / 0.029 / 7.67` | `0.000 / 0.000 / 0.000 / 13.00` | 1/10、5/10、10/10 |
| `multi_axis_v2` | 轴一致性修正版 | `major_geo_risk`、`quality_tuition`、`employment_region` | `0.367 / 1.133 / 0.005 / 9.33` | `0.000 / 0.000 / 0.008 / 13.00` | 6/10、5/10、0/10 |

`multi_axis_v2` 的论文价值在于修正 v1 中部分画像轴不一致的问题，使失败分析更清楚：专业-地域与风险组合在一致画像下改善到 6/10，专业质量与预算组合保持 5/10，就业与地域组合则暴露出就业证据与地域树证据联合编排不足。压力测试中的 `axis_flexibilities` 只作为 simulator/evaluator ground truth，Agent 不读取该字段。

## 结果分析

斜杠格式依次为：

```text
elicitation_success_rate / mean_pareto_gain / mean_hallucination_rate / avg_turns
```

| 实验 | 类型 | `app_pareto` | `hard_constraint` | 结论 |
|---|---|---:|---:|---|
| `major_geo_v1` | 主实验 | `0.900 / 0.900 / 0.000 / 5.20` | `0.000 / 0.000 / 0.000 / 7.00` | Agent 能用联合放宽证据触发 9/10 个隐性妥协 |
| `risk_band_v1` | 主实验 | `1.000 / 3.000 / 0.000 / 5.00` | `0.000 / 0.000 / 0.000 / 15.00` | Agent 能把单一保守偏好扩展为冲稳保组合 |
| `school_strength_v1` | 扩展实验 | `1.000 / 15.000 / 0.000 / 5.00` | `0.000 / 0.000 / 0.000 / 11.00` | 学校/学科实力证据可接入同一谈判闭环 |
| `tuition_value_v1` | 扩展实验 | `1.000 / 1.000 / 0.000 / 5.00` | `0.000 / 0.000 / 0.000 / 11.00` | `admission_plans.tuition` 可支撑小幅超预算换收益的谈判 |
| `major_quality_v1` | 扩展实验 | `1.000 / 16.000 / 0.000 / 5.00` | `0.000 / 0.000 / 0.050 / 11.00` | `school_major_quality_profiles` 可支撑专业质量跃迁证据 |
| `employment_outcome_v1` | 扩展实验 | `1.000 / 49.000 / 0.000 / 3.00` | `0.000 / 0.000 / 0.000 / 11.00` | `major_employment_outcome_profiles` 可支撑就业排名、行业、岗位和薪资证据谈判 |
| `region_tree_v1` | 扩展实验 | `1.000 / 1.000 / 0.000 / 3.00` | `0.000 / 0.000 / 0.000 / 11.00` | reviewed 地域树可支撑地理板块和城市层级证据谈判 |

从主实验看，`app_pareto` 在 `major_geo_v1` 中达到 0.900 成功率，在 `risk_band_v1` 中达到 1.000 成功率，而 `hard_constraint` 在两组主实验中均为 0.000。由于两组实验的 `mean_hallucination_rate` 均为 0.000，说明 Agent 的收益并非来自编造学校或分数，而是来自对真实 DB gap 的有效利用。

`major_geo_v1` 不是 100% 成功。失败样本为 `real-db-set-浙江-569-009`，该样本要求 Agent 进一步退到更远的 `any_major` 候选才能命中 hidden volunteer set，而当前回复停留在医学相关近邻阶段，因此 deterministic judge 未判定成功。这一点在 `agent_benchmark_major_geo_v1_evidence.md` 中已记录，避免把 0.900 写成 100% 成功。

五组扩展实验说明，本文框架可以随着数据层扩展而扩展。`tuition_value_v1` 把学费字段转化为预算谈判证据；`major_quality_v1` 把专业排名、学科评估、特色专业、重点专业和满意度聚合为专业质量证据；`employment_outcome_v1` 把专业就业画像转化为就业结果证据；`region_tree_v1` 把 reviewed 地域树接入 `region_tree_relax`，使地理板块和城市层级证据能够进入轻量 MAS 与沙盒评测；`school_strength_v1` 则作为较粗粒度实力证据的过渡实验。扩展实验不替代主实验，而是支撑“数据贡献可扩展”的论文论点。

## 典型 Case 分析

`major_geo_v1` 中，`real-db-set-浙江-542-001` 的用户初始表达为“我542分，只想读临床医学，专业不对的学校再好也不考虑”。`app_pareto` 在对话中通过 `major_geo_relax` 给出真实可达候选，并附带最低分证据。用户模拟器在看到命中隐藏志愿集合的学校和分数证据后接受该方向。

`risk_band_v1` 中，`real-db-set-浙江-592-001` 的用户显性表达为“只想稳妥一点，临床医学不要冲刺太危险的学校”。`app_pareto` 在不改变地域、专业、选科和预算等硬约束的前提下，给出 `chong/wen/bao` 风险组合，并附带最低分、最低位次、分差和位次差证据。用户模拟器在看到完整风险组合后接受适度冲刺。

`employment_outcome_v1` 中，`real-db-set-浙江-520-001` 的用户希望就业和薪资稳定，但对省外或相近专业较保守。`app_pareto` 给出广西师范大学工业设计，最低分 513、最低位次 156857、`outcome_score=100.0`、`outcome_gain=49.0`、`employment_rank=4`、`top_industry=互联网/电子商务` 和薪资分布证据。用户模拟器在看到学校、分数和就业结果证据后接受就业导向的相近专业方案。

`region_tree_v1` 中，`real-db-set-浙江-610-001` 的用户坚持杭州或较近地域偏好。`app_pareto` 通过 `region_tree_relax` 给出宁波大学临床医学，最低分 610、最低位次 40934，并说明该候选来自 `geo_block_relax`：杭州 (`geo:city:hangzhou`) -> 宁波 (`geo:city:ningbo`)，树置信度为 0.95。用户模拟器在看到学校、分数和 reviewed 地域树节点证据后接受相邻地理板块候选。

## 局限性

当前结果是论文第一版闭环结果，仍有以下限制：

- 每组实验样本量为 10，足以证明闭环可复现，但还不是大规模 leaderboard。
- 本次运行使用 offline deterministic judge，适合稳定验收；真实 LLM judge 结果可作为补充实验。
- 数据来自当前浙江 PostgreSQL 快照，跨省份、跨年份和跨批次泛化仍需扩展。
- 当前事实裁判主要验证学校、分数和过程证据，对专业、年份、省份、批次、选科等联合条件的 SQL 核验还可加强。
- `pareto_gain` 仍是确定性指标，未来可引入真实录取概率、用户偏好权重和多目标效用建模；`region_tree_v1` 中城市层级只作为 reviewed 地域树证据，不直接计入城市收益。
- 用户模拟器是受控沙盒用户，尚未用真实咨询日志校准信任、犹豫、反问等细粒度行为。

## 复现命令

启动本地数据库：

```powershell
cd D:\gaokaollm-v2
.\db\start_postgres.ps1
$env:DATABASE_URL = "postgresql://postgres@127.0.0.1:55432/gaokao_recommendation"
```

运行任一实验的命令模板：

```powershell
C:\ProgramData\Anaconda3\envs\gaokao_pg\python.exe -m gaokaollm_bench.tests.manual.agent_benchmark_run `
  --personas <persona-json> `
  --targets app_pareto hard_constraint `
  --max-turns <turns> `
  --limit 10 `
  --output-dir <output-dir> `
  --paper-summary <summary-md> `
  --offline-deterministic `
  --request-timeout 45
```

主实验使用 `major_geo_v1` 与 `risk_band_v1`；扩展实验使用 `school_strength_v1`、`tuition_value_v1`、`major_quality_v1`、`employment_outcome_v1`、`region_tree_v1` 对应的 persona 与输出目录。停止数据库：

```powershell
.\db\stop_postgres.ps1
```

回归测试记录：

```powershell
C:\ProgramData\Anaconda3\envs\gaokao_pg\python.exe -m pytest gaokaollm_bench/tests tests -q
```

当前论文写法建议：把 `major_geo_v1 + risk_band_v1` 写作主实验，把 `school_strength_v1 + tuition_value_v1 + major_quality_v1 + employment_outcome_v1 + region_tree_v1` 写作扩展实验。这样既能保持主贡献清晰，也能说明数据层的持续扩展能力。
