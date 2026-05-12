# v1_hybrid_rag 基线接入与环境配置

## 结论

`v1_hybrid_rag` 已接入 Benchmark runner，用于作为比 `hard_constraint` 更公平的 v1 软约束 RAG 系统基线。它复现 v1 的方法链路：查询重写/意图归一、关系过滤、语义向量召回、二阶重排，以及冲/稳/保分段推荐；同时不产生 `pareto_opportunities`，不主动做分阶段放宽或帕累托谈判。

当前环境已配置远程模型：

| 环节 | 环境变量 | 当前模型 |
|---|---|---|
| 语义向量召回 | `EMBEDDING_MODEL` | `Qwen/Qwen3-Embedding-8B` |
| 二阶重排 | `RERANKING_MODEL` | `Qwen/Qwen3-Reranker-8B` |

如果未配置上述远程模型，代码仍保留本地 BGE-M3 与 BCEmbedding/Cross-Encoder 回退路径，但本地路径需要额外安装 `FlagEmbedding`、`BCEmbedding` 并配置本地模型目录。

## Smoke 结果

- Persona: `gaokaollm_bench/sample_data/iceberg_personas_major_hierarchy_real_db_10.json`
- Target: `v1_hybrid_rag`
- Output dir: `gaokaollm_bench/outputs/agent_benchmark_v1_hybrid_rag_smoke/`
- Report: `reports/v1_hybrid_rag.jsonl`
- Result: completed, no `PreflightFailed`
- Remote backend: `Qwen/Qwen3-Embedding-8B` + `Qwen/Qwen3-Reranker-8B`
- Metrics: `0.000 / 0.000 / 0.000 / 7.00`

该 smoke 的 `elicitation_success = false` 是预期范围内的 baseline 行为：`v1_hybrid_rag` 给出软约束召回和冲稳保候选，但不主动发现隐藏妥协轴，因此不能像 v2 证据谈判 Agent 那样触发专业/地域联合放宽。

## 已完成

| 项目 | 状态 |
|---|---|
| Benchmark target `v1_hybrid_rag` | 已接入 |
| 当前 PostgreSQL 快照适配 | 已接入只读候选查询 |
| 远程 embedding dense recall | 已接入 OpenAI-compatible `/embeddings` |
| 远程 rerank 二阶重排 | 已接入 SiliconFlow-compatible `/rerank` |
| 本地 BGE-M3 / BCE 回退 | 保留，缺依赖时明确 preflight failure |
| fake backend 单元测试 | 已覆盖 |
| hidden persona 边界 | 不读取 `implicit_flexibilities`、`volunteer_set`、`axis_flexibilities` |
| Pareto 谈判边界 | 不产生 `pareto_opportunities` |

## 运行建议

正式发布 `v1_hybrid_rag` pilot 指标前，建议先跑 1 条 smoke，再跑主实验两个集合各 10 条：

```powershell
C:\ProgramData\Anaconda3\envs\gaokao_pg\python.exe -m gaokaollm_bench.tests.manual.agent_benchmark_run --personas gaokaollm_bench/sample_data/iceberg_personas_major_hierarchy_real_db_10.json --targets v1_hybrid_rag --max-turns 3 --limit 1 --output-dir gaokaollm_bench/outputs/agent_benchmark_v1_hybrid_rag_smoke --offline-deterministic --paper-summary gaokaollm_bench/outputs/agent_benchmark_v1_hybrid_rag_smoke_summary.md

C:\ProgramData\Anaconda3\envs\gaokao_pg\python.exe -m gaokaollm_bench.tests.manual.agent_benchmark_run --personas gaokaollm_bench/sample_data/iceberg_personas_major_hierarchy_real_db_10.json --targets app_pareto hard_constraint v1_hybrid_rag --max-turns 6 --limit 10 --output-dir gaokaollm_bench/outputs/agent_benchmark_major_geo_v1_v1_hybrid_rag_pilot --offline-deterministic --paper-summary gaokaollm_bench/outputs/agent_benchmark_major_geo_v1_v1_hybrid_rag_pilot_summary.md

C:\ProgramData\Anaconda3\envs\gaokao_pg\python.exe -m gaokaollm_bench.tests.manual.agent_benchmark_run --personas gaokaollm_bench/sample_data/iceberg_personas_risk_band_real_db_10.json --targets app_pareto hard_constraint v1_hybrid_rag --max-turns 6 --limit 10 --output-dir gaokaollm_bench/outputs/agent_benchmark_risk_band_v1_v1_hybrid_rag_pilot --offline-deterministic --paper-summary gaokaollm_bench/outputs/agent_benchmark_risk_band_v1_v1_hybrid_rag_pilot_summary.md
```

## 论文边界

`hard_constraint` 仍作为无谈判能力下界保留；`v1_hybrid_rag` 是更公平的软约束 RAG 系统基线。只有在 smoke/pilot 无 `PreflightFailed` 后，才应在论文中引用其正式指标。
