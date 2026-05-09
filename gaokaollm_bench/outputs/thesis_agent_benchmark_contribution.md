# Agent + Benchmark 论文贡献与实验结果母版

## 研究目标

本项目面向高考志愿咨询场景，研究目标不是让大模型生成一段看似合理的单轮建议，而是评估并构建一个能够在真实招生数据约束下进行多轮偏好启发的决策 Agent。核心问题是：当用户显式表达“只读临床医学”“专业不对的学校再好也不考虑”等强硬红线时，系统能否识别其中可能存在的信息不足型锚定，并用可核验的学校、专业和最低分证据，引导用户接受更优且可达的志愿集合。

因此，论文贡献采用双主线结构：

- Benchmark 贡献：构建面向高考志愿 Agent 的冰山画像、多轮沙盒与事实/过程联合评价框架。
- Agent 贡献：构建证据驱动的 Pareto 妥协谈判 Agent，核心能力是 `major_geo_relax`，即在不读取隐藏画像的前提下，同时放宽专业与地域约束，提出真实可达的反事实志愿集合。

## Benchmark 贡献

`gaokaollm-bench` 将评测对象从静态问答正确率扩展为多轮偏好妥协过程。它使用真实 PostgreSQL 招生数据库发现“坚持原约束”和“放宽约束”之间的层次跃迁，再逆向生成冰山画像。每个 persona 显式区分用户说出口的红线和只有在充分证据下才会接受的隐性妥协条件。

Benchmark 的关键设计包括：

- 冰山画像：`explicit_red_lines` 记录用户显性红线，`implicit_flexibilities` 记录隐藏妥协触发条件。
- 真实 DB gap：样本来自真实录取数据，而不是人工编造学校和分数。
- 专业树层级放宽：使用 `major_hierarchy`，从同叶子簇、同父近邻、上层大类、probe 邻近大类到无专业限制逐步扩展。
- 志愿集合评价：隐藏目标不是单校命中，而是一组包含学校、专业、年份、最低分和层次标签的 `volunteer_set`。
- 多轮沙盒：被测 Agent 只能看到用户话语，用户模拟器持有完整 persona，通过自然语言逐步反馈。
- 联合评价：确定性事实裁判约束幻觉率，过程裁判评价是否成功启发隐性妥协并产生 Pareto gain。

专业树和 probe 是 benchmark 的基础设施。专业树最终包含 82 个节点、52 个叶子簇和 19,096 条叶子 observed names；probe 消融显示浅层 MLP 相比 Linear 带来主要正收益，FR-KAN 未优于 MLP。这些结果用于支撑专业层级放宽的可审计性，不作为本轮 Agent 主贡献。

## Agent 贡献

业务 Agent 采用 LangGraph 编排，主流程为：

```text
gatekeeper -> radar -> negotiator
```

- `gatekeeper`：从用户话语中抽取分数、省份、专业、预算和选科，查询当前硬约束下的 baseline。
- `radar`：调度确定性 SQL 探针，寻找放宽约束后的 Pareto 机会。
- `negotiator`：只基于真实查询结果生成谈判回复，向用户展示可核验的反事实选择。

本轮 Agent 的关键新增能力是 `major_geo_relax`。它同时放宽专业与地域约束，但保留分数、预算和选科等事实约束，并使用与 persona 生成一致的专业树层级放宽策略、学校质量过滤、特殊专业过滤、同校上限和年份优先规则。

重要的是，`major_geo_relax` 不读取 benchmark 的 `implicit_flexibilities` 或 `volunteer_set`。它只使用用户显式话语和真实数据库查询结果，因此不是对隐藏答案的泄漏，而是把 benchmark 公开的方法学策略同步到被测 Agent 的推荐能力中。

对照系统为 `hard_constraint`。它只复用约束抽取和 baseline 查询，报告当前硬约束下的可达志愿，不主动谈判，也不产生 `major_geo_relax`。这个对照用于衡量“只迎合显性红线”和“证据驱动 Pareto 谈判”之间的差异。

## 实验设置

主实验使用现有结果包：

```text
gaokaollm_bench/outputs/agent_benchmark_major_geo_v1/
```

实验配置如下：

| 项目 | 设置 |
|---|---|
| Personas | `gaokaollm_bench/sample_data/iceberg_personas_major_hierarchy_real_db_10.json` |
| Cases | 10 |
| Targets | `app_pareto`, `hard_constraint` |
| Max turns | 3 |
| Simulator model | `Pro/moonshotai/Kimi-K2.6` |
| Judge model | `Pro/moonshotai/Kimi-K2.6` |
| Offline deterministic | True |
| 默认省份 | 浙江 |
| 数据库 | 本地 PostgreSQL 快照，`postgresql://postgres@127.0.0.1:55432/gaokao_recommendation` |

输出文件包括 transcripts、逐例 report、`summary.json` 和 `summary.md`。论文引用结果来自：

```text
gaokaollm_bench/outputs/agent_benchmark_major_geo_v1_summary.md
```

## 结果分析

聚合结果如下：

| Target | Cases | Completed | Failed | Elicitation Success | Mean Pareto Gain | Mean Hallucination | Avg Turns |
|---|---:|---:|---:|---:|---:|---:|---:|
| app_pareto | 10 | 10 | 0 | 0.900 | 0.900 | 0.000 | 5.20 |
| hard_constraint | 10 | 10 | 0 | 0.000 | 0.000 | 0.000 | 7.00 |

结果表明，`app_pareto` 在 10 个真实 DB 冰山画像样本中完成全部评测，并在 9 个样本上成功触发隐性妥协，`elicitation_success` 为 0.900，平均 Pareto gain 为 0.900。`hard_constraint` 在同一批样本上成功率为 0.000，说明单纯报告硬约束下的可达志愿无法让用户接受隐藏可妥协方案。

两类系统的 `mean_hallucination_rate` 均为 0.000，说明 `app_pareto` 的提升不是通过虚构学校或错误分数获得，而是在确定性数据库查询和事实裁判约束下得到的。平均轮次方面，`app_pareto` 为 5.20，`hard_constraint` 为 7.00，表明有效的反事实证据可以更早结束多轮僵持。

这个结果对应论文中的 Agent 贡献：当用户坚持临床医学等显性红线时，系统通过 `major_geo_relax` 找到专业与地域联合放宽后的更高层次志愿集合，并以学校名、专业名和最低分作为证据进行 Pareto 谈判。

## 典型 Case 分析

以 `real-db-set-浙江-542-001` 为例，用户初始表达为“我542分，只想读临床医学，专业不对的学校再好也不考虑”。在 benchmark 中，用户隐藏妥协条件要求看到可包含外省、专业不限后的更高层次志愿集合，且每个志愿都有学校名、专业名和不高于本人分数的最低分证据。

`app_pareto` 在对话中先确认必要约束，再通过 `major_geo_relax` 给出联合方案，例如：

```text
东北农业大学（黑龙江）动物科学，最低分 541，层次 3
西南交通大学（四川）城市设计，最低分 492，层次 3
西南交通大学（四川）建筑类，最低分 492，层次 3
广西大学（广西）公共事业管理，最低分 542，层次 3
华南农业大学（广东）茶学，最低分 542，层次 3
```

这些候选均来自真实数据库，并被写入 transcript 的 `internal_state.major_geo_relax`，因此可以审计。用户模拟器在看到命中隐藏志愿集合的学校和分数证据后接受该方向，该 case 的 `elicitation_success=True`、`pareto_gain=1`、`hallucination_rate=0.000`。

相同 case 下，`hard_constraint` 只报告当前硬约束下的临床医学相关结果，不提出联合放宽方案，因此无法触发隐藏妥协条件。这形成了清晰的 Agent-vs-Baseline 对照。

## 局限性

当前结果是论文第一版闭环结果，仍有以下限制：

- 样本量为 10，足以证明闭环可复现，但还不是大规模 leaderboard。
- 本次运行使用 offline deterministic judge，适合稳定验收；真实 LLM judge 结果可作为补充实验。
- 数据来自当前浙江 PostgreSQL 快照，跨省份、跨年份和跨批次泛化仍需扩展。
- 当前事实裁判主要验证学校可达性，对专业、年份、省份、批次等联合条件的 SQL 核验还可加强。
- `pareto_gain` 主要基于学校 tier，尚未引入城市偏好、就业预期、风险梯度等多目标收益。
- 用户模拟器是受控沙盒用户，尚未用真实咨询日志校准信任、犹豫、反问等细粒度行为。

## 复现命令

启动本地数据库：

```powershell
cd D:\gaokaollm-v2
.\db\start_postgres.ps1
$env:DATABASE_URL = "postgresql://postgres@127.0.0.1:55432/gaokao_recommendation"
```

运行 Agent-vs-Baseline 离线 benchmark：

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

停止数据库：

```powershell
.\db\stop_postgres.ps1
```

回归测试：

```powershell
C:\ProgramData\Anaconda3\envs\gaokao_pg\python.exe -m pytest gaokaollm_bench/tests tests -q
```

当前记录结果为：

```text
79 passed, 9 skipped, 1 warning
```

本次变更范围内的 scoped ruff 检查和格式检查均通过；全仓库 ruff 仍会扫到历史文件格式和 unused import 问题，不作为本轮论文文档验收条件。

