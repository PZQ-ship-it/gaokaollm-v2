# region_tree_v1 地域树逐例证据附录

## 实验来源与复现路径

本附录整理 `region_tree_v1` 地域树扩展实验的逐例证据。该实验验证 reviewed 地域树数据层能否接入轻量 MAS Agent 的 `gatekeeper -> radar -> negotiator` 流程，并在 benchmark 沙盒中触发可核验的地域偏好妥协。

- Personas: `gaokaollm_bench/sample_data/iceberg_personas_region_tree_real_db_10.json`
- 输出目录: `gaokaollm_bench/outputs/agent_benchmark_region_tree_v1/`
- Summary: `gaokaollm_bench/outputs/agent_benchmark_region_tree_v1/summary.json`
- Reports: `reports/app_pareto.jsonl`, `reports/hard_constraint.jsonl`
- Transcripts: `transcripts/app_pareto/*.json`, `transcripts/hard_constraint/*.json`
- 数据层: `region_geo_tree` 与 `region_urban_tier_tree` 的 reviewed v1 artifact

论文定位：`region_tree_v1` 是数据层扩展实验，用于证明地域树标准化层可以进入数据 + Agent + Benchmark 闭环；主实验仍是 `major_geo_v1 + risk_band_v1`。城市层级只作为 reviewed region-tree 证据，不直接计入 Pareto gain，收益仍按学校 tier/ranking 改善计算。

## 聚合指标核对表

指标口径为 `elicitation_success_rate / mean_pareto_gain / mean_hallucination_rate / avg_turns`。

- `app_pareto`: `1.000 / 1.000 / 0.000 / 3.00`
- `hard_constraint`: `0.000 / 0.000 / 0.000 / 11.00`

| Target | Cases | Success | Mean Pareto Gain | Mean Hallucination | Avg Turns |
|---|---:|---:|---:|---:|---:|
| `app_pareto` | 10 | 1.000 | 1.000 | 0.000 | 3.00 |
| `hard_constraint` | 10 | 0.000 | 0.000 | 0.000 | 11.00 |

结论：`app_pareto` 覆盖 10 个 app case，10 个成功；`hard_constraint` 覆盖 10 个 baseline case，10 个全失败；两者幻觉率均为 0.000。

## 逐例结果表

| case_id | 分数 | 目标专业 | app | baseline | app turns | baseline turns | hallucination | pareto_gain |
|---|---:|---|---|---|---:|---:|---:|---:|
| `real-db-set-浙江-610-001` | 610 | 临床医学 | 成功 | 失败 | 3 | 11 | 0.000 | 1 |
| `real-db-set-浙江-612-002` | 612 | 临床医学 | 成功 | 失败 | 3 | 11 | 0.000 | 1 |
| `real-db-set-浙江-614-003` | 614 | 临床医学 | 成功 | 失败 | 3 | 11 | 0.000 | 1 |
| `real-db-set-浙江-616-004` | 616 | 临床医学 | 成功 | 失败 | 3 | 11 | 0.000 | 1 |
| `real-db-set-浙江-618-005` | 618 | 临床医学 | 成功 | 失败 | 3 | 11 | 0.000 | 1 |
| `real-db-set-浙江-620-006` | 620 | 临床医学 | 成功 | 失败 | 3 | 11 | 0.000 | 1 |
| `real-db-set-浙江-622-007` | 622 | 临床医学 | 成功 | 失败 | 3 | 11 | 0.000 | 1 |
| `real-db-set-浙江-624-008` | 624 | 临床医学 | 成功 | 失败 | 3 | 11 | 0.000 | 1 |
| `real-db-set-浙江-626-009` | 626 | 临床医学 | 成功 | 失败 | 3 | 11 | 0.000 | 1 |
| `real-db-set-浙江-628-010` | 628 | 临床医学 | 成功 | 失败 | 3 | 11 | 0.000 | 1 |

## 地域树证据表

下表逐例列出来自 transcript 内部状态的 `region_tree_relax` 真实候选。每个候选同时给出学校、城市、专业、最低分/位次、地域树策略、source/target region node 与置信度。

| case_id | 学校 | 省份/城市 | 专业 | 最低分 | 最低位次 | 策略 | 地域树节点 | confidence |
|---|---|---|---|---:|---:|---|---|---:|
| `real-db-set-浙江-610-001` | 宁波大学 | 浙江/宁波市 | 临床医学 | 610 | 40934 | `geo_block_relax` | 杭州 (`geo:city:hangzhou`) -> 宁波 (`geo:city:ningbo`) | 0.95 |
| `real-db-set-浙江-612-002` | 宁波大学 | 浙江/宁波市 | 临床医学 | 610 | 40934 | `geo_block_relax` | 杭州 (`geo:city:hangzhou`) -> 宁波 (`geo:city:ningbo`) | 0.95 |
| `real-db-set-浙江-614-003` | 宁波大学 | 浙江/宁波市 | 临床医学 | 610 | 40934 | `geo_block_relax` | 杭州 (`geo:city:hangzhou`) -> 宁波 (`geo:city:ningbo`) | 0.95 |
| `real-db-set-浙江-614-003` | 南京中医药大学 | 江苏/南京 | 临床医学(老年医学)(仙林校区) | 613 | 30507 | `urban_tier_relax` | 杭州 (`urban:city:hangzhou`) -> 南京 (`urban:city:nanjing`) | 0.90 |
| `real-db-set-浙江-616-004` | 宁波大学 | 浙江/宁波市 | 临床医学 | 616 | 37411 | `geo_block_relax` | 杭州 (`geo:city:hangzhou`) -> 宁波 (`geo:city:ningbo`) | 0.95 |
| `real-db-set-浙江-616-004` | 成都中医药大学 | 四川/成都市 | 中西医临床医学 | 616 | 35347 | `urban_tier_relax` | 杭州 (`urban:city:hangzhou`) -> 成都 (`urban:city:chengdu`) | 0.90 |
| `real-db-set-浙江-618-005` | 宁波大学 | 浙江/宁波市 | 临床医学 | 616 | 37411 | `geo_block_relax` | 杭州 (`geo:city:hangzhou`) -> 宁波 (`geo:city:ningbo`) | 0.95 |
| `real-db-set-浙江-618-005` | 成都中医药大学 | 四川/成都市 | 中西医临床医学 | 616 | 35347 | `urban_tier_relax` | 杭州 (`urban:city:hangzhou`) -> 成都 (`urban:city:chengdu`) | 0.90 |
| `real-db-set-浙江-620-006` | 宁波大学 | 浙江/宁波市 | 临床医学 | 616 | 37411 | `geo_block_relax` | 杭州 (`geo:city:hangzhou`) -> 宁波 (`geo:city:ningbo`) | 0.95 |
| `real-db-set-浙江-620-006` | 成都中医药大学 | 四川/成都市 | 中西医临床医学(唐容川班) | 620 | 33198 | `urban_tier_relax` | 杭州 (`urban:city:hangzhou`) -> 成都 (`urban:city:chengdu`) | 0.90 |
| `real-db-set-浙江-622-007` | 宁波大学 | 浙江/宁波市 | 临床医学 | 621 | 32839 | `geo_block_relax` | 杭州 (`geo:city:hangzhou`) -> 宁波 (`geo:city:ningbo`) | 0.95 |
| `real-db-set-浙江-622-007` | 广州中医药大学 | 广东/广州市 | 中西医临床医学 | 622 | 30086 | `urban_tier_relax` | 杭州 (`urban:city:hangzhou`) -> 广州 (`urban:city:guangzhou`) | 0.90 |
| `real-db-set-浙江-624-008` | 宁波大学 | 浙江/宁波市 | 临床医学 | 621 | 32839 | `geo_block_relax` | 杭州 (`geo:city:hangzhou`) -> 宁波 (`geo:city:ningbo`) | 0.95 |
| `real-db-set-浙江-624-008` | 广州中医药大学 | 广东/广州市 | 中医骨伤科学(第二临床医学院) | 623 | 31175 | `urban_tier_relax` | 杭州 (`urban:city:hangzhou`) -> 广州 (`urban:city:guangzhou`) | 0.90 |
| `real-db-set-浙江-626-009` | 宁波大学 | 浙江/宁波市 | 临床医学 | 621 | 32839 | `geo_block_relax` | 杭州 (`geo:city:hangzhou`) -> 宁波 (`geo:city:ningbo`) | 0.95 |
| `real-db-set-浙江-626-009` | 广州中医药大学 | 广东/广州市 | 中医骨伤科学(第二临床医学院) | 623 | 31175 | `urban_tier_relax` | 杭州 (`urban:city:hangzhou`) -> 广州 (`urban:city:guangzhou`) | 0.90 |
| `real-db-set-浙江-628-010` | 宁波大学 | 浙江/宁波市 | 临床医学 | 621 | 32839 | `geo_block_relax` | 杭州 (`geo:city:hangzhou`) -> 宁波 (`geo:city:ningbo`) | 0.95 |
| `real-db-set-浙江-628-010` | 广州中医药大学 | 广东/广州市 | 中医骨伤科学(第二临床医学院) | 623 | 31175 | `urban_tier_relax` | 杭州 (`urban:city:hangzhou`) -> 广州 (`urban:city:guangzhou`) | 0.90 |

## Baseline 对照说明

`hard_constraint` baseline 只报告当前显性硬约束下的可达志愿，不主动提出 `geo_block_relax`、`urban_tier_relax` 或 `region_tree_relax`。因此它不能触发 persona 中“如果有地域树阶段证据和最低分证据，可以接受相邻地理板块或城市层级候选”的隐藏妥协条件。

本附录可以引用 hidden persona 字段作为 evaluator ground truth，但被测 Agent 的输入只来自用户显式话语和 PostgreSQL / reviewed 地域树查询结果；Agent 不读取 `implicit_flexibilities` 或 `volunteer_set`。

## 论文可引用结论

`region_tree_v1` 表明，在已经建立 `region_geo_tree` 与 `region_urban_tier_tree` reviewed v1 数据层后，地域偏好可以从自由文本城市字段推进为可审计的层级放宽证据。`app_pareto` 能在保持分数、专业等事实约束的前提下，给出学校、城市、最低分、最低位次和地域树节点证据，从而触发 10/10 的隐藏妥协；`hard_constraint` 因不主动生成地域树机会而 0/10 成功。该实验不宣称城市层级本身等价于就业机会、生活成本或城市生活质量，只证明地域树数据层可以进入 MAS Agent 与 Benchmark 的最小闭环。
