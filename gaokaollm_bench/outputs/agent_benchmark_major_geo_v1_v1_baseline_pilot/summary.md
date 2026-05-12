# Agent Benchmark Summary

## Setting

- Personas: `gaokaollm_bench\sample_data\iceberg_personas_real_db_10.json`
- Cases: 10
- Targets: app_pareto, hard_constraint, v1_soft_rag
- Max turns: 6
- Simulator model: Pro/deepseek-ai/DeepSeek-R1
- Judge model: Pro/deepseek-ai/DeepSeek-R1
- Offline deterministic: True
- Default province when omitted by the user: `浙江`

## Aggregate Results

| Target | Cases | Completed | Failed | Elicitation Success | Mean Pareto Gain | Mean Hallucination | Avg Turns |
|---|---:|---:|---:|---:|---:|---:|---:|
| app_pareto | 10 | 10 | 0 | 0.700 | 0.700 | 0.060 | 7.40 |
| hard_constraint | 10 | 10 | 0 | 0.000 | 0.000 | 0.100 | 13.00 |
| v1_soft_rag | 10 | 10 | 0 | 0.000 | 0.000 | 0.250 | 13.00 |

## Interpretation

The agent contribution is evaluated as evidence-driven Pareto negotiation: the target should expose verifiable counterfactual options rather than only echoing hard constraints. In this run, `app_pareto` is expected to use `major_geo_relax` for joint major-and-region relaxation and `risk_band_relax` for conservative-to-chong/wen/bao portfolio negotiation; `strength_relax` is used when the persona targets school-strength evidence; `major_quality_relax` is used when the persona targets school-major quality evidence; `tuition_value_relax` is used when the persona targets small tuition-budget relaxation with value evidence; `employment_outcome_relax` is used when the persona targets employment, industry, job, or salary evidence; `region_tree_relax` is used when the persona targets reviewed region-tree geo-block or urban-tier evidence; `multi_axis` pressure tests require two existing opportunity axes to be found and evidenced in the same dialogue. `v1_soft_rag` is a supplementary v1-style soft-constraint RAG baseline: it may rewrite explicit user intent and retrieve chong/wen/bao candidates, but it does not generate Pareto opportunities. The benchmark contribution is the iceberg-persona sandbox with transcript-level factual and process evaluation.

## Case Notes

- `app_pareto` / `real-db-set-浙江-520-001`: success=False, pareto_gain=0, hallucination=0.000. 确定性裁判：未观察到命中隐藏妥协条件的学校和分数证据。
- `app_pareto` / `real-db-set-浙江-530-002`: success=False, pareto_gain=0, hallucination=0.000. 确定性裁判：未观察到命中隐藏妥协条件的学校和分数证据。
- `app_pareto` / `real-db-set-浙江-540-003`: success=False, pareto_gain=0, hallucination=0.000. 确定性裁判：未观察到命中隐藏妥协条件的学校和分数证据。
- `app_pareto` / `real-db-set-浙江-550-004`: success=True, pareto_gain=1, hallucination=0.000. 确定性裁判：检查被测系统是否提到隐藏志愿集合中的学校并给出分数证据。
- `app_pareto` / `real-db-set-浙江-560-005`: success=True, pareto_gain=1, hallucination=0.000. 确定性裁判：检查被测系统是否提到隐藏志愿集合中的学校并给出分数证据。

## Limitations

Results depend on the configured simulator and judge models, the current PostgreSQL snapshot, and the selected persona subset. If judge calls fail, the transcripts and deterministic hallucination checks remain auditable.
