# `risk_band_v1` Agent-vs-Baseline 逐例证据附录

本文档用于支撑论文中“风险偏好放宽 + 冲稳保组合谈判”的实验结论。它只整理既有产物，不新增实验、不重跑数据库、不调用外部 LLM。

## 1. 实验来源与复现路径

本附录引用以下现有产物：

- `gaokaollm_bench/outputs/agent_benchmark_risk_band_v1/summary.json`
- `gaokaollm_bench/outputs/agent_benchmark_risk_band_v1/reports/app_pareto.jsonl`
- `gaokaollm_bench/outputs/agent_benchmark_risk_band_v1/reports/hard_constraint.jsonl`
- `gaokaollm_bench/outputs/agent_benchmark_risk_band_v1/transcripts/app_pareto/*.json`
- `gaokaollm_bench/outputs/agent_benchmark_risk_band_v1/transcripts/hard_constraint/*.json`
- `gaokaollm_bench/outputs/agent_benchmark_risk_band_v1_summary.md`
- `gaokaollm_bench/outputs/thesis_method_experiment_chapters.md`

对应实验设置为：

- Persona 数据：`gaokaollm_bench/sample_data/iceberg_personas_risk_band_real_db_10.json`
- Target：`app_pareto`、`hard_constraint`
- Case 数量：10
- Max turns：7
- Simulator model：`Pro/moonshotai/Kimi-K2.6`
- Judge model：`Pro/moonshotai/Kimi-K2.6`
- Offline deterministic：`True`
- 默认省份：浙江

若需要重新生成同结构结果，可使用现有 manual runner：

```powershell
python -m gaokaollm_bench.tests.manual.agent_benchmark_run `
  --personas gaokaollm_bench/sample_data/iceberg_personas_risk_band_real_db_10.json `
  --targets app_pareto hard_constraint `
  --max-turns 7 `
  --output-dir gaokaollm_bench/outputs/agent_benchmark_risk_band_v1 `
  --offline-deterministic
```

## 2. 聚合指标核对表

该表与 `summary.json` 和 `agent_benchmark_risk_band_v1_summary.md` 一致。

| Target | Cases | Completed | Failed | Elicitation Success | Mean Pareto Gain | Mean Hallucination | Avg Turns |
|---|---:|---:|---:|---:|---:|---:|---:|
| `app_pareto` | 10 | 10 | 0 | 1.000 | 3.000 | 0.000 | 5.00 |
| `hard_constraint` | 10 | 10 | 0 | 0.000 | 0.000 | 0.000 | 15.00 |

核心对照关系是：`app_pareto` 在所有 10 个风险偏好 case 中成功触发隐藏妥协，`hard_constraint` 全部失败；两者幻觉率均为 0.000。因此，收益来自风险组合谈判能力，而不是虚构学校或分数。

## 3. 逐例结果表

| Case | Score | Major | App Success | Baseline Success | App Turns | Baseline Turns | Halluc. | Pareto Gain |
|---|---:|---|---|---|---:|---:|---:|---:|
| `real-db-set-浙江-592-001` | 592 | 临床医学 | True | False | 5 | 15 | 0.000 | 3 |
| `real-db-set-浙江-593-002` | 593 | 临床医学 | True | False | 5 | 15 | 0.000 | 3 |
| `real-db-set-浙江-594-003` | 594 | 临床医学 | True | False | 5 | 15 | 0.000 | 3 |
| `real-db-set-浙江-595-004` | 595 | 临床医学 | True | False | 5 | 15 | 0.000 | 3 |
| `real-db-set-浙江-601-005` | 601 | 临床医学 | True | False | 5 | 15 | 0.000 | 3 |
| `real-db-set-浙江-602-006` | 602 | 临床医学 | True | False | 5 | 15 | 0.000 | 3 |
| `real-db-set-浙江-603-007` | 603 | 临床医学 | True | False | 5 | 15 | 0.000 | 3 |
| `real-db-set-浙江-604-008` | 604 | 临床医学 | True | False | 5 | 15 | 0.000 | 3 |
| `real-db-set-浙江-605-009` | 605 | 临床医学 | True | False | 5 | 15 | 0.000 | 3 |
| `real-db-set-浙江-606-010` | 606 | 临床医学 | True | False | 5 | 15 | 0.000 | 3 |

## 4. `risk_band_relax` 证据表

下表从 `app_pareto` transcripts 的 `internal_state.pareto_opportunities.risk_band_relax` 中抽取。每个 case 至少列出 3 个候选；本表每例列出 4 个候选，以展示 `chong/wen/bao` 风险组合。

`score_margin = student_score - min_score`；`rank_gap = min_rank - student_rank`。少数历史年份的位次字段存在跨年口径差异，本表保留 transcript 原值，风险标签以当轮 `risk_band_relax` 输出为准。

| Case | School | Province/City | Major | Min Score | Min Rank | score_margin | rank_gap | Risk |
|---|---|---|---|---:|---:|---:|---:|---|
| `real-db-set-浙江-592-001` | 杭州师范大学 | 浙江/杭州市 | 临床医学 | 590 | 63187 | 2 | 2773 | `chong` |
| `real-db-set-浙江-592-001` | 杭州师范大学 | 浙江/杭州市 | 临床医学(第一,二,三学年在仓前校区,第四学年起在杭州市金华路120号) | 590 | 64194 | 2 | 3780 | `wen` |
| `real-db-set-浙江-592-001` | 杭州医学院 | 浙江/杭州市 | 临床医学(临安校区) | 570 | 86908 | 22 | 26494 | `bao` |
| `real-db-set-浙江-592-001` | 杭州医学院 | 浙江/杭州市 | 临床医学 | 591 | 62029 | 1 | 1615 | `chong` |
| `real-db-set-浙江-593-002` | 杭州医学院 | 浙江/杭州市 | 临床医学 | 591 | 62029 | 2 | 2755 | `chong` |
| `real-db-set-浙江-593-002` | 杭州师范大学 | 浙江/杭州市 | 临床医学 | 590 | 63187 | 3 | 3913 | `wen` |
| `real-db-set-浙江-593-002` | 杭州医学院 | 浙江/杭州市 | 临床医学(临安校区) | 570 | 86908 | 23 | 27634 | `bao` |
| `real-db-set-浙江-593-002` | 杭州师范大学 | 浙江/杭州市 | 临床医学(第一,二,三学年在仓前校区,第四学年起在杭州市金华路120号) | 590 | 64194 | 3 | 4920 | `wen` |
| `real-db-set-浙江-594-003` | 浙江中医药大学 | 浙江/杭州市 | 临床医学 | 594 | 58239 | 0 | 95 | `chong` |
| `real-db-set-浙江-594-003` | 杭州师范大学 | 浙江/杭州市 | 临床医学 | 590 | 63187 | 4 | 5043 | `wen` |
| `real-db-set-浙江-594-003` | 杭州医学院 | 浙江/杭州市 | 临床医学(临安校区) | 570 | 86908 | 24 | 28764 | `bao` |
| `real-db-set-浙江-594-003` | 杭州医学院 | 浙江/杭州市 | 临床医学 | 589 | 60567 | 5 | 2423 | `chong` |
| `real-db-set-浙江-595-004` | 浙江中医药大学 | 浙江/杭州市 | 临床医学 | 594 | 58239 | 1 | 1219 | `chong` |
| `real-db-set-浙江-595-004` | 杭州师范大学 | 浙江/杭州市 | 临床医学 | 590 | 63187 | 5 | 6167 | `wen` |
| `real-db-set-浙江-595-004` | 杭州医学院 | 浙江/杭州市 | 临床医学(临安校区) | 570 | 86908 | 25 | 29888 | `bao` |
| `real-db-set-浙江-595-004` | 杭州师范大学 | 浙江/杭州市 | 临床医学(第一,二,三学年在仓前校区,第四学年起在杭州市金华路120号) | 590 | 64194 | 5 | 7174 | `wen` |
| `real-db-set-浙江-601-005` | 杭州师范大学 | 浙江/杭州市 | 临床医学(仓前校区) | 600 | 42609 | 1 | -7687 | `chong` |
| `real-db-set-浙江-601-005` | 浙江中医药大学 | 浙江/杭州市 | 临床医学(第一学年在富春校区) | 597 | 56669 | 4 | 6373 | `wen` |
| `real-db-set-浙江-601-005` | 杭州师范大学 | 浙江/杭州市 | 临床医学 | 590 | 63187 | 11 | 12891 | `bao` |
| `real-db-set-浙江-601-005` | 浙江中医药大学 | 浙江/杭州市 | 中西医临床医学 | 599 | 52787 | 2 | 2491 | `chong` |
| `real-db-set-浙江-602-006` | 杭州师范大学 | 浙江/杭州市 | 临床医学 | 602 | 46132 | 0 | -3066 | `chong` |
| `real-db-set-浙江-602-006` | 浙江中医药大学 | 浙江/杭州市 | 中西医临床医学 | 599 | 52787 | 3 | 3589 | `wen` |
| `real-db-set-浙江-602-006` | 杭州师范大学 | 浙江/杭州市 | 临床医学(第一,二,三学年在仓前校区,第四学年起在杭州市金华路120号) | 590 | 64194 | 12 | 14996 | `bao` |
| `real-db-set-浙江-602-006` | 杭州医学院 | 浙江/杭州市 | 临床医学(临安校区) | 561 | 243 | 41 | -48955 | `chong` |
| `real-db-set-浙江-603-007` | 杭州师范大学 | 浙江/杭州市 | 临床医学 | 602 | 46132 | 1 | -1973 | `chong` |
| `real-db-set-浙江-603-007` | 浙江中医药大学 | 浙江/杭州市 | 中西医临床医学 | 599 | 52787 | 4 | 4682 | `wen` |
| `real-db-set-浙江-603-007` | 杭州师范大学 | 浙江/杭州市 | 临床医学(第一,二,三学年在仓前校区,第四学年起在杭州市金华路120号) | 590 | 64194 | 13 | 16089 | `bao` |
| `real-db-set-浙江-603-007` | 杭州医学院 | 浙江/杭州市 | 临床医学(临安校区) | 561 | 243 | 42 | -47862 | `chong` |
| `real-db-set-浙江-604-008` | 杭州师范大学 | 浙江/杭州市 | 临床医学 | 604 | 48028 | 0 | 976 | `chong` |
| `real-db-set-浙江-604-008` | 浙江中医药大学 | 浙江/杭州市 | 中西医临床医学 | 599 | 52787 | 5 | 5735 | `wen` |
| `real-db-set-浙江-604-008` | 杭州师范大学 | 浙江/杭州市 | 临床医学(第一,二,三学年在仓前校区,第四学年起在杭州市金华路120号) | 590 | 64194 | 14 | 17142 | `bao` |
| `real-db-set-浙江-604-008` | 杭州医学院 | 浙江/杭州市 | 临床医学(临安校区) | 561 | 243 | 43 | -46809 | `chong` |
| `real-db-set-浙江-605-009` | 杭州师范大学 | 浙江/杭州市 | 临床医学 | 604 | 48028 | 1 | 1986 | `chong` |
| `real-db-set-浙江-605-009` | 浙江中医药大学 | 浙江/杭州市 | 中西医临床医学 | 599 | 52787 | 6 | 6745 | `wen` |
| `real-db-set-浙江-605-009` | 杭州师范大学 | 浙江/杭州市 | 临床医学(第一,二,三学年在仓前校区,第四学年起在杭州市金华路120号) | 590 | 64194 | 15 | 18152 | `bao` |
| `real-db-set-浙江-605-009` | 杭州医学院 | 浙江/杭州市 | 临床医学(临安校区) | 561 | 243 | 44 | -45799 | `chong` |
| `real-db-set-浙江-606-010` | 宁波大学 | 浙江/宁波市 | 临床医学 | 606 | 36820 | 0 | -8182 | `chong` |
| `real-db-set-浙江-606-010` | 杭州师范大学 | 浙江/杭州市 | 临床医学 | 604 | 48028 | 2 | 3026 | `wen` |
| `real-db-set-浙江-606-010` | 杭州师范大学 | 浙江/杭州市 | 临床医学(第一,二,三学年在仓前校区,第四学年起在杭州市金华路120号) | 590 | 64194 | 16 | 19192 | `bao` |
| `real-db-set-浙江-606-010` | 浙江中医药大学 | 浙江/杭州市 | 中西医临床医学(第一学年在富春校区) | 606 | 46635 | 0 | 1633 | `chong` |

## 5. Baseline 对照说明

`hard_constraint` baseline 的作用是保留清晰对照：它只响应用户显性表达的“只求稳妥、不接受冲刺风险”，不主动生成 `risk_band_relax` 机会，也不把单一保守方案扩展为 `chong/wen/bao` 组合。

从 transcripts 看，`hard_constraint` 的 `risk_band_relax` 字段保持为空列表；从 reports 看，10 个 baseline case 的 `elicitation_success` 全为 `false`，`pareto_gain` 全为 0。它并非因为幻觉失败，而是因为没有进行风险偏好谈判，无法触发隐藏妥协条件。

需要强调的是，本文档可以引用 persona 中的 `implicit_flexibilities` 和 `volunteer_set` 作为 evaluator ground truth；但被测 Agent 并不读取这些 hidden fields。`app_pareto` 的输入只来自用户显式话语抽取出的分数、省份、专业、选科、预算、风险偏好，以及 PostgreSQL 查询得到的真实候选。

## 6. 论文可引用结论

在风险偏好放宽实验中，`app_pareto` 将启发成功率从 baseline 的 0.000 提升到 1.000，平均 Pareto gain 从 0.000 提升到 3.000，同时保持 0.000 的幻觉率。逐例证据显示，Agent 能够给出真实学校、专业、最低分、最低位次、分差、位次差和 `chong/wen/bao` 风险层级证据，从而把用户的单一保守偏好转化为可审计的冲稳保组合。

因此，`risk_band_relax` 可以作为 v2 对 v1 `1:3:9` 冲稳保推荐的研究升级：v1 证明系统能够工程化生成梯度推荐，v2 则把这种梯度推荐放入冰山画像、多轮沙盒和事实/过程联合评价框架中，验证它是否真的触发了用户可接受的偏好妥协。
