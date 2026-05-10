# Agent Benchmark: School Strength Relaxation v1

## 实验定位

本轮补齐 `放宽与跃迁.md` 中尚未闭环的一类动态决策：**学科实力放宽 / 学校实力跃迁**。它和已有 `major_geo_relax`、`risk_band_relax` 一起服务论文主线：Benchmark 构造冰山画像，Agent 在不读取 hidden persona 的前提下，用 PostgreSQL 真实证据触发 Pareto 妥协。

本实验的核心问题是：当用户显性表达“更看重学科实力，普通学校先不考虑”时，`app_pareto` 是否能用真实录取分、位次和学科/专业排名证据，提出比硬约束 baseline 更有吸引力的可达志愿。

## 新增能力

| 模块 | 新增内容 | 可验证产物 |
|---|---|---|
| Agent radar | 新增 `strength_relax` 机会探测 | `app/flows/probers.py` |
| Agent gatekeeper | 抽取 `strength` 约束，如学科实力、专业排名、重点学科 | `app/graphs/nodes/gatekeeper.py` |
| Agent negotiator | 在回复中展示学校、专业、最低分、位次、`major_strength_rank`、评级 | transcripts |
| Benchmark generator | 新增 `school_strength` persona 生成 | `gaokaollm_bench/sample_data/iceberg_personas_school_strength_real_db_10.json` |
| Deterministic judge | 增加 strength evidence 与 strength rank gain 识别 | `gaokaollm_bench/tests/manual/agent_benchmark_run.py` |

## 数据与边界

- 数据库：当前 PostgreSQL 快照。
- 主要使用表：`admission_scores`、`schools`、`plans/subject_requirements` 相关 join、`school_major_strengths`。
- 样本：`gaokaollm_bench/sample_data/iceberg_personas_school_strength_real_db_10.json`。
- Agent 输入边界：只使用用户显式话语抽取出的分数、省份、专业、选科、预算、学科实力偏好，以及 PostgreSQL 查询结果。
- Hidden persona 边界：`implicit_flexibilities` 与 `volunteer_set` 只作为 benchmark evaluator ground truth，不被 Agent 读取。
- 当前实现说明：由于现有 `school_major_strengths` 与 `admission_scores.major_id` 不能稳定直接 join，本轮采用每所学校在 `major_ranking` 来源中的最佳学科/专业排名作为学校实力证据；后续可在数据层补齐专业级标准映射。

## 结果

运行命令：

```powershell
C:\ProgramData\Anaconda3\envs\gaokao_pg\python.exe -m gaokaollm_bench.tests.manual.agent_benchmark_run `
  --personas gaokaollm_bench\sample_data\iceberg_personas_school_strength_real_db_10.json `
  --targets app_pareto hard_constraint `
  --max-turns 5 `
  --limit 10 `
  --output-dir gaokaollm_bench\outputs\agent_benchmark_school_strength_v1 `
  --offline-deterministic
```

| Target | Cases | Completed | Failed | Elicitation Success | Mean Pareto Gain | Mean Hallucination | Avg Turns |
|---|---:|---:|---:|---:|---:|---:|---:|
| `app_pareto` | 10 | 10 | 0 | 1.000 | 15.000 | 0.000 | 5.00 |
| `hard_constraint` | 10 | 10 | 0 | 0.000 | 0.000 | 0.000 | 11.00 |

逐例 transcript 与 report 位于：

- `gaokaollm_bench/outputs/agent_benchmark_school_strength_v1/transcripts/app_pareto/`
- `gaokaollm_bench/outputs/agent_benchmark_school_strength_v1/transcripts/hard_constraint/`
- `gaokaollm_bench/outputs/agent_benchmark_school_strength_v1/reports/`
- `gaokaollm_bench/outputs/agent_benchmark_school_strength_v1/summary.json`
- `gaokaollm_bench/outputs/agent_benchmark_school_strength_v1/summary.md`

## 典型证据

以 `real-db-set-浙江-520-001` 为例，`app_pareto` 在同一轮回复中给出：

| 学校 | 省份 | 专业 | 最低分 | 最低位次 | 学科/专业实力证据 |
|---|---|---|---:|---:|---|
| 黑龙江中医药大学 | 黑龙江 | 中西医临床医学 | 492 | 178059 | `major_strength_rank=1`, `rating=A+` |
| 新疆医科大学 | 新疆 | 中西医临床医学 | 514 | 155875 | `major_strength_rank=1`, `rating=A-` |
| 齐齐哈尔医学院 | 黑龙江 | 临床医学 | 516 | 150607 | `major_strength_rank=5`, `rating=B` |

Baseline `hard_constraint` 只按显性硬约束返回当前可达方案，不产生 `strength_relax` 谈判证据，因此不能触发隐藏妥协。

## 验收记录

- Scoped pytest：`45 passed, 2 skipped`
- `py_compile`：通过
- Scoped `ruff check`：通过
- Scoped `ruff format --check`：`13 files already formatted`

## 论文落点

这组结果可以作为第三个动态放宽闭环：在专业+地域联合放宽、风险偏好放宽之外，证明 Agent 还能利用 PostgreSQL 中的学校/学科实力表，把“学科实力偏好”转化为可审计的证据驱动谈判。论文中应把它写成对 `major_geo_relax` 与 `risk_band_relax` 的扩展实验，而不是替代主实验。
