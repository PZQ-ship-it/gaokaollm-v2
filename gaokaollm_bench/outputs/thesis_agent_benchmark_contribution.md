# Agent + Benchmark 论文贡献与实验结果母版

本文档用于服务毕业论文摘要、绪论、贡献总结和答辩 PPT。它不新增实验结论，只把当前已经完成并通过双实验审计的 Agent+Benchmark 闭环收束成可直接引用的贡献表述。

## 研究目标

本项目面向高考志愿咨询场景，研究目标不是让大模型生成一段看似合理的单轮建议，而是评估并构建一个能够在真实招生数据约束下进行多轮偏好启发的决策 Agent。核心问题是：当用户显式表达“只读临床医学”“专业不对的学校再好也不考虑”“只求稳妥，不想冲”等强硬红线时，系统能否识别其中可能存在的信息不足型锚定，并用可核验的学校、专业、最低分、最低位次和风险层级证据，引导用户接受更优且可达的志愿集合。

论文贡献采用双主线结构：

- Benchmark 贡献：构建面向高考志愿 Agent 的冰山画像、多轮沙盒与事实/过程联合评价框架。
- Agent 贡献：构建证据驱动的 Pareto 妥协谈判 Agent，核心能力包括 `major_geo_relax` 专业+地域联合放宽，以及 `risk_band_relax` 风险偏好放宽。

## Benchmark 贡献

`gaokaollm_bench` 将评测对象从静态问答正确率扩展为多轮偏好妥协过程。它使用真实 PostgreSQL 招生数据库发现“坚持原约束”和“放宽约束”之间的跃迁，再逆向生成冰山画像。每个 persona 显式区分用户说出口的红线和只有在充分证据下才会接受的隐性妥协条件。

当前论文第一版包含两类主实验画像：

| Benchmark 画像 | 显性红线 | 隐性妥协 | 评价重点 |
|---|---|---|---|
| `major_geo_v1` | 坚持原专业、地域或本省约束 | 看到真实学校、专业和最低分证据后，可接受跨省与跨专业联合放宽 | 学校层次与志愿集合质量提升 |
| `risk_band_v1` | 只求稳妥，不接受冲刺风险 | 看到最低分、最低位次、分差、位次差和风险层级证据后，可接受 `chong/wen/bao` 冲稳保组合 | 志愿组合完整性和风险结构提升 |

Benchmark 的关键设计包括：

- 冰山画像：`explicit_red_lines` 记录用户显性红线，`implicit_flexibilities` 记录隐藏妥协触发条件。
- 真实 DB gap：样本来自真实录取数据，而不是人工编造学校和分数。
- 专业树层级放宽：使用 `major_hierarchy`，从同叶子簇、同父近邻、上层大类、probe 邻近大类到无专业限制逐步扩展。
- 风险组合画像：从“只求稳”构造到 `chong/wen/bao` 组合的隐藏接受条件。
- 多轮沙盒：被测 Agent 只能看到用户话语，用户模拟器持有完整 persona，通过自然语言逐步反馈。
- 联合评价：确定性事实裁判约束幻觉率，过程裁判评价是否成功启发隐性妥协并产生 Pareto gain。

专业树和 probe 是 benchmark 的基础设施。专业树最终包含 82 个节点、52 个叶子簇和 19,096 条叶子 observed names；probe 消融显示浅层 MLP 相比 Linear 带来主要正收益，FR-KAN 未优于 MLP。这些结果用于支撑专业层级放宽的可审计性，不作为本轮 Agent 主贡献。

## Agent 贡献

业务 Agent 采用 LangGraph 编排，主流程为：

```text
gatekeeper -> radar -> negotiator
```

| 节点 | 职责 | 论文作用 |
|---|---|---|
| `gatekeeper` | 从用户话语中抽取分数、省份、专业、预算、选科和风险偏好，并查询当前硬约束 baseline | 确认显性约束和当前可达空间 |
| `radar` | 调度确定性 SQL 探针，寻找放宽约束后的 Pareto 机会 | 发现可谈判的反事实证据 |
| `negotiator` | 只基于真实查询结果组织回复 | 用学校、专业、最低分、位次和风险层级进行谈判 |

`major_geo_relax` 用于专业与地域联合放宽。它同时放宽专业与地域约束，但保留分数、预算和选科等事实约束，并使用与 persona 生成一致的专业树层级放宽策略、学校质量过滤、特殊专业过滤、同校上限和年份优先规则。

`risk_band_relax` 用于风险偏好放宽。它不改变省份、专业、选科、预算等硬约束，只把“只求稳、不接受冲”的显性风险偏好扩展为冲稳保组合，并输出学校、专业、最低分、最低位次、`score_margin`、`rank_gap` 和 `chong/wen/bao` 风险层级。

重要的是，被测 Agent 不读取 benchmark 的 `implicit_flexibilities` 或 `volunteer_set`。它只使用用户显式话语和真实数据库查询结果，因此不是对隐藏答案的泄漏，而是把 benchmark 公开的方法学策略同步到被测 Agent 的推荐能力中。

对照系统为 `hard_constraint`。它只复用约束抽取和 baseline 查询，报告当前硬约束下的可达志愿，不主动谈判，也不产生 `major_geo_relax` 或 `risk_band_relax`。这个对照用于衡量“只迎合显性红线”和“证据驱动 Pareto 谈判”之间的差异。

## 实验设置

论文第一版主实验包含两组 Agent-vs-Baseline 离线评测：

| 项目 | `major_geo_v1` | `risk_band_v1` |
|---|---|---|
| Personas | `gaokaollm_bench/sample_data/iceberg_personas_major_hierarchy_real_db_10.json` | `gaokaollm_bench/sample_data/iceberg_personas_risk_band_real_db_10.json` |
| Cases | 10 | 10 |
| Targets | `app_pareto`, `hard_constraint` | `app_pareto`, `hard_constraint` |
| Max turns | 3 | 7 |
| Simulator model | `Pro/moonshotai/Kimi-K2.6` | `Pro/moonshotai/Kimi-K2.6` |
| Judge model | `Pro/moonshotai/Kimi-K2.6` | `Pro/moonshotai/Kimi-K2.6` |
| Offline deterministic | True | True |
| 数据库 | 本地 PostgreSQL 快照 | 本地 PostgreSQL 快照 |

输出文件包括 transcripts、逐例 report、summary、逐例 evidence 和双实验审计报告。论文引用结果来自：

- `gaokaollm_bench/outputs/agent_benchmark_major_geo_v1_summary.md`
- `gaokaollm_bench/outputs/agent_benchmark_major_geo_v1_evidence.md`
- `gaokaollm_bench/outputs/agent_benchmark_risk_band_v1_summary.md`
- `gaokaollm_bench/outputs/agent_benchmark_risk_band_v1_evidence.md`
- `gaokaollm_bench/outputs/thesis_artifact_audit.md`

## 结果分析

### `major_geo_v1`

| Target | Cases | Completed | Failed | Elicitation Success | Mean Pareto Gain | Mean Hallucination | Avg Turns |
|---|---:|---:|---:|---:|---:|---:|---:|
| `app_pareto` | 10 | 10 | 0 | 0.900 | 0.900 | 0.000 | 5.20 |
| `hard_constraint` | 10 | 10 | 0 | 0.000 | 0.000 | 0.000 | 7.00 |

结果表明，`app_pareto` 在 10 个真实 DB 冰山画像样本中完成全部评测，并在 9 个样本上成功触发隐性妥协。`hard_constraint` 在同一批样本上成功率为 0.000，说明单纯报告硬约束下的可达志愿无法让用户接受隐藏可妥协方案。

`major_geo_v1` 的唯一失败样本是 `real-db-set-浙江-569-009`。该 case 中，persona 隐藏目标要求退到更远的 `any_major` 集合，而 Agent 实际停留在较近的医学相关大类兜底候选上，因此 deterministic judge 未判定成功。这一点在 `agent_benchmark_major_geo_v1_evidence.md` 和 `thesis_artifact_audit.md` 中均已记录，避免把 0.900 写成 100% 成功。

### `risk_band_v1`

| Target | Cases | Completed | Failed | Elicitation Success | Mean Pareto Gain | Mean Hallucination | Avg Turns |
|---|---:|---:|---:|---:|---:|---:|---:|
| `app_pareto` | 10 | 10 | 0 | 1.000 | 3.000 | 0.000 | 5.00 |
| `hard_constraint` | 10 | 10 | 0 | 0.000 | 0.000 | 0.000 | 15.00 |

结果表明，`app_pareto` 在 10 个风险偏好 case 中全部成功，将单一保守偏好扩展为包含 `chong/wen/bao` 的冲稳保组合；`hard_constraint` 虽然同样保持 0.000 幻觉率，但由于不进行风险组合谈判，无法触发隐藏妥协。平均轮次方面，`app_pareto` 为 5.00，baseline 为 15.00，说明充分的风险证据可以更早结束多轮僵持。

两组实验的共同结论是：Agent 的收益不是通过虚构学校或错误分数获得，而是在真实数据库查询、事实裁判和过程裁判共同约束下得到的。`app_pareto` 相比 `hard_constraint` 的优势来自证据驱动 Pareto 谈判，而不是模型自由发挥。

## 典型 Case 分析

`major_geo_v1` 中，`real-db-set-浙江-542-001` 的用户初始表达为“我542分，只想读临床医学，专业不对的学校再好也不考虑”。`app_pareto` 在对话中通过 `major_geo_relax` 给出东北农业大学动物科学、西南交通大学城市设计、广西大学公共事业管理等真实可达候选，并附带最低分证据。用户模拟器在看到命中隐藏志愿集合的学校和分数证据后接受该方向。

`risk_band_v1` 中，`real-db-set-浙江-592-001` 的用户显性表达为“只想稳妥一点，临床医学不要冲刺太危险的学校”。`app_pareto` 在不改变地域、专业、选科和预算等硬约束的前提下，给出杭州师范大学临床医学 `chong`、杭州师范大学临床医学长专业名 `wen`、杭州医学院临床医学(临安校区) `bao` 等候选，并附带最低分、最低位次、分差和位次差证据。用户模拟器在看到完整风险组合后接受适度冲刺。

## 局限性

当前结果是论文第一版闭环结果，仍有以下限制：

- 每组实验样本量为 10，足以证明闭环可复现，但还不是大规模 leaderboard。
- 本次运行使用 offline deterministic judge，适合稳定验收；真实 LLM judge 结果可作为补充实验。
- 数据来自当前浙江 PostgreSQL 快照，跨省份、跨年份和跨批次泛化仍需扩展。
- 当前事实裁判主要验证学校、分数和过程证据，对专业、年份、省份、批次、选科等联合条件的 SQL 核验还可加强。
- `pareto_gain` 主要基于隐藏志愿集合命中、学校 tier 和风险组合覆盖，尚未充分纳入城市偏好、就业预期、学费预算、学科实力和多年稳定性等多目标收益。
- 用户模拟器是受控沙盒用户，尚未用真实咨询日志校准信任、犹豫、反问等细粒度行为。

## 复现命令

启动本地数据库：

```powershell
cd D:\gaokaollm-v2
.\db\start_postgres.ps1
$env:DATABASE_URL = "postgresql://postgres@127.0.0.1:55432/gaokao_recommendation"
```

运行 `major_geo_v1`：

```powershell
C:\ProgramData\Anaconda3\envs\gaokao_pg\python.exe -m gaokaollm_bench.tests.manual.agent_benchmark_run `
  --personas gaokaollm_bench/sample_data/iceberg_personas_major_hierarchy_real_db_10.json `
  --targets app_pareto hard_constraint `
  --max-turns 3 `
  --limit 10 `
  --output-dir gaokaollm_bench/outputs/agent_benchmark_major_geo_v1 `
  --paper-summary gaokaollm_bench/outputs/agent_benchmark_major_geo_v1_summary.md `
  --offline-deterministic `
  --request-timeout 45
```

运行 `risk_band_v1`：

```powershell
C:\ProgramData\Anaconda3\envs\gaokao_pg\python.exe -m gaokaollm_bench.tests.manual.agent_benchmark_run `
  --personas gaokaollm_bench/sample_data/iceberg_personas_risk_band_real_db_10.json `
  --targets app_pareto hard_constraint `
  --max-turns 7 `
  --limit 10 `
  --output-dir gaokaollm_bench/outputs/agent_benchmark_risk_band_v1 `
  --paper-summary gaokaollm_bench/outputs/agent_benchmark_risk_band_v1_summary.md `
  --offline-deterministic `
  --request-timeout 45
```

运行双实验审计：

```powershell
C:\ProgramData\Anaconda3\envs\gaokao_pg\python.exe -m gaokaollm_bench.tests.manual.thesis_artifact_audit
```

停止数据库：

```powershell
.\db\stop_postgres.ps1
```

回归测试记录：

```powershell
C:\ProgramData\Anaconda3\envs\gaokao_pg\python.exe -m pytest gaokaollm_bench/tests tests -q
```

当前记录结果为：

```text
79 passed, 9 skipped, 1 warning
```

本次变更范围内的 scoped ruff 检查和格式检查均通过；全仓库历史格式问题不作为本轮论文文档验收条件。
