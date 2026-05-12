# `v1_hybrid_rag` 基线 Pilot 逐例证据

## 1. 定位

本证据包记录新增 `v1_hybrid_rag` 基线在两个主实验集合上的 pilot 对照结果。它不是七组正式实验主表的一部分，也不替代既有 `hard_constraint` 下界；它的作用是提供一个更接近 v1 `gaokaollmmodel` 的软约束 RAG / 冲稳保推荐系统基线。

`v1_hybrid_rag` 使用显式用户话语进行查询重写/意图归一，在当前 PostgreSQL 招生快照上做关系过滤，再使用远程语义向量召回与二阶重排生成冲/稳/保候选。本轮配置为：

| 环节 | 模型 |
| --- | --- |
| 语义向量召回 | `Qwen/Qwen3-Embedding-8B` |
| 二阶重排 | `Qwen/Qwen3-Reranker-8B` |

边界保持不变：`v1_hybrid_rag` 不读取 `implicit_flexibilities`、`volunteer_set` 或 `axis_flexibilities`；不生成 `pareto_opportunities`；不主动执行分阶段放宽或证据驱动 Pareto 谈判。

## 2. 产物来源

| 集合 | Output dir | Summary |
| --- | --- | --- |
| `major_geo_v1` pilot | `agent_benchmark_major_geo_v1_v1_hybrid_rag_pilot/` | `agent_benchmark_major_geo_v1_v1_hybrid_rag_pilot_summary.md` |
| `risk_band_v1` pilot | `agent_benchmark_risk_band_v1_v1_hybrid_rag_pilot/` | `agent_benchmark_risk_band_v1_v1_hybrid_rag_pilot_summary.md` |

两个 pilot 均为 10 条真实 DB persona，均包含 `app_pareto`、`hard_constraint` 和 `v1_hybrid_rag` 三个 target。运行结果均无 `PreflightFailed`。

## 3. 聚合指标

斜杠格式依次为：`elicitation_success_rate / mean_pareto_gain / mean_hallucination_rate / avg_turns`。

| 集合 | `app_pareto` | `hard_constraint` | `v1_hybrid_rag` |
| --- | --- | --- | --- |
| `major_geo_v1` pilot | `0.900 / 0.900 / 0.000 / 5.80` | `0.000 / 0.000 / 0.000 / 13.00` | `0.100 / 0.100 / 0.000 / 12.40` |
| `risk_band_v1` pilot | `1.000 / 3.000 / 0.000 / 5.00` | `0.000 / 0.000 / 0.000 / 13.00` | `0.000 / 0.000 / 0.025 / 13.00` |

解释：`v1_hybrid_rag` 能给出软约束召回和冲稳保候选，但它不具备 v2 的可谈判偏好轴探测与证据谈判能力。因此，在需要触发隐藏妥协空间的 Benchmark 中，它明显强于“环境接入不可用”的占位基线，但仍不能稳定触发 hidden flexibility。

## 4. `major_geo_v1` 逐例结果

| Case | Success | Pareto gain | Hallucination | Turns | 说明 |
| --- | ---: | ---: | ---: | ---: | --- |
| `real-db-set-浙江-542-001` | false | 0 | 0.000 | 13 | 未命中隐藏妥协学校与分数证据 |
| `real-db-set-浙江-544-002` | false | 0 | 0.000 | 13 | 未命中隐藏妥协学校与分数证据 |
| `real-db-set-浙江-546-003` | false | 0 | 0.000 | 13 | 未命中隐藏妥协学校与分数证据 |
| `real-db-set-浙江-547-004` | false | 0 | 0.000 | 13 | 未命中隐藏妥协学校与分数证据 |
| `real-db-set-浙江-549-005` | false | 0 | 0.000 | 13 | 未命中隐藏妥协学校与分数证据 |
| `real-db-set-浙江-550-006` | false | 0 | 0.000 | 13 | 未命中隐藏妥协学校与分数证据 |
| `real-db-set-浙江-557-007` | true | 1 | 0.000 | 7 | 命中隐藏志愿集合中的学校并给出分数证据 |
| `real-db-set-浙江-568-008` | false | 0 | 0.000 | 13 | 未命中隐藏妥协学校与分数证据 |
| `real-db-set-浙江-569-009` | false | 0 | 0.000 | 13 | 未命中隐藏妥协学校与分数证据；该 case 同时也是 `major_geo_v1` 中 v2 的唯一失败样本 |
| `real-db-set-浙江-575-010` | false | 0 | 0.000 | 13 | 未命中隐藏妥协学校与分数证据 |

## 5. `risk_band_v1` 逐例结果

| Case | Success | Pareto gain | Hallucination | Turns | 说明 |
| --- | ---: | ---: | ---: | ---: | --- |
| `real-db-set-浙江-592-001` | false | 0 | 0.000 | 13 | 未命中风险组合隐藏志愿集合 |
| `real-db-set-浙江-593-002` | false | 0 | 0.000 | 13 | 未命中风险组合隐藏志愿集合 |
| `real-db-set-浙江-594-003` | false | 0 | 0.250 | 13 | 未命中风险组合隐藏志愿集合，且存在少量事实幻觉 |
| `real-db-set-浙江-595-004` | false | 0 | 0.000 | 13 | 未命中风险组合隐藏志愿集合 |
| `real-db-set-浙江-601-005` | false | 0 | 0.000 | 13 | 未命中风险组合隐藏志愿集合 |
| `real-db-set-浙江-602-006` | false | 0 | 0.000 | 13 | 未命中风险组合隐藏志愿集合 |
| `real-db-set-浙江-603-007` | false | 0 | 0.000 | 13 | 未命中风险组合隐藏志愿集合 |
| `real-db-set-浙江-604-008` | false | 0 | 0.000 | 13 | 未命中风险组合隐藏志愿集合 |
| `real-db-set-浙江-605-009` | false | 0 | 0.000 | 13 | 未命中风险组合隐藏志愿集合 |
| `real-db-set-浙江-606-010` | false | 0 | 0.000 | 13 | 未命中风险组合隐藏志愿集合 |

## 6. 论文解释边界

- `hard_constraint` 仍是无谈判能力下界。
- `v1_hybrid_rag` 是软约束 RAG / 冲稳保推荐系统基线，适合用于说明 v1 召回式推荐与 v2 偏好启发式谈判之间的差异。
- `app_pareto` 的优势不应被写成“只击败硬约束基线”，而应写成相对 v1 软约束 RAG 仍能更稳定触发隐藏妥协空间。
- 本 pilot 只作为对照材料和后续论文讨论候选，不进入当前七组正式实验主表。
