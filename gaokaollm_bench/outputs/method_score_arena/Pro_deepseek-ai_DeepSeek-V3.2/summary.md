# Agent Benchmark Summary

## Setting

- Personas: `gaokaollm_bench\sample_data\iceberg_personas_real_db_10.json`
- Cases: 10
- Targets: app_pareto, v1_prompt_direct, v1_prompt_cot
- Max turns: 6
- Simulator model: Pro/deepseek-ai/DeepSeek-V3.2
- Judge model: Pro/deepseek-ai/DeepSeek-V3.2
- Offline deterministic: False
- Default province when omitted by the user: `浙江`

## Aggregate Results

| Target | Cases | Completed | Failed | Elicitation Success | Mean Pareto Gain | Mean Hallucination | Avg Turns |
|---|---:|---:|---:|---:|---:|---:|---:|
| app_pareto | 10 | 0 | 10 | 0.000 | 0.000 | 0.000 | 0.00 |
| v1_prompt_direct | 10 | 0 | 10 | 0.000 | 0.000 | 0.000 | 0.00 |
| v1_prompt_cot | 10 | 0 | 10 | 0.000 | 0.000 | 0.000 | 0.00 |

## Interpretation

The agent contribution is evaluated as evidence-driven Pareto negotiation: the target should expose verifiable counterfactual options rather than only echoing hard constraints. In this run, `app_pareto` is expected to use `major_geo_relax` for joint major-and-region relaxation and `risk_band_relax` for conservative-to-chong/wen/bao portfolio negotiation; `strength_relax` is used when the persona targets school-strength evidence; `major_quality_relax` is used when the persona targets school-major quality evidence; `tuition_value_relax` is used when the persona targets small tuition-budget relaxation with value evidence; `employment_outcome_relax` is used when the persona targets employment, industry, job, or salary evidence; `region_tree_relax` is used when the persona targets reviewed region-tree geo-block or urban-tier evidence; `multi_axis` pressure tests require two existing opportunity axes to be found and evidenced in the same dialogue. `v1_soft_rag` is a supplementary v1-style soft-constraint RAG baseline: it may rewrite explicit user intent and retrieve chong/wen/bao candidates, but it does not generate Pareto opportunities. `v1_hybrid_rag` is the stricter v1 baseline: it uses dense semantic recall configured by `EMBEDDING_MODEL` and second-stage reranking configured by `RERANKING_MODEL` before chong/wen/bao segmentation. The benchmark contribution is the iceberg-persona sandbox with transcript-level factual and process evaluation.

## Case Notes

- `app_pareto` / `real-db-set-浙江-520-001` failed: PreflightFailed: database is not reachable: 127.0.0.1:55432 (TimeoutError: timed out)
- `app_pareto` / `real-db-set-浙江-530-002` failed: PreflightFailed: database is not reachable: 127.0.0.1:55432 (TimeoutError: timed out)
- `app_pareto` / `real-db-set-浙江-540-003` failed: PreflightFailed: database is not reachable: 127.0.0.1:55432 (TimeoutError: timed out)
- `app_pareto` / `real-db-set-浙江-550-004` failed: PreflightFailed: database is not reachable: 127.0.0.1:55432 (TimeoutError: timed out)
- `app_pareto` / `real-db-set-浙江-560-005` failed: PreflightFailed: database is not reachable: 127.0.0.1:55432 (TimeoutError: timed out)

## Limitations

Results depend on the configured simulator and judge models, the current PostgreSQL snapshot, and the selected persona subset. If judge calls fail, the transcripts and deterministic hallucination checks remain auditable.
