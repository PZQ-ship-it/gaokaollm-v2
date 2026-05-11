# Agent Benchmark Summary

## Setting

- Personas: `gaokaollm_bench\sample_data\iceberg_personas_multi_axis_real_db_30.json`
- Cases: 30
- Targets: app_pareto, hard_constraint
- Max turns: 6
- Simulator model: Pro/moonshotai/Kimi-K2.6
- Judge model: Pro/moonshotai/Kimi-K2.6
- Offline deterministic: True
- Default province when omitted by the user: `浙江`

## Aggregate Results

| Target | Cases | Completed | Failed | Elicitation Success | Mean Pareto Gain | Mean Hallucination | Avg Turns |
|---|---:|---:|---:|---:|---:|---:|---:|
| app_pareto | 30 | 30 | 0 | 0.533 | 1.133 | 0.029 | 7.67 |
| hard_constraint | 30 | 30 | 0 | 0.000 | 0.000 | 0.000 | 13.00 |

## Interpretation

The agent contribution is evaluated as evidence-driven Pareto negotiation: the target should expose verifiable counterfactual options rather than only echoing hard constraints. In this run, `app_pareto` is expected to use `major_geo_relax` for joint major-and-region relaxation and `risk_band_relax` for conservative-to-chong/wen/bao portfolio negotiation; `strength_relax` is used when the persona targets school-strength evidence; `major_quality_relax` is used when the persona targets school-major quality evidence; `tuition_value_relax` is used when the persona targets small tuition-budget relaxation with value evidence; `employment_outcome_relax` is used when the persona targets employment, industry, job, or salary evidence; `region_tree_relax` is used when the persona targets reviewed region-tree geo-block or urban-tier evidence; `multi_axis` pressure tests require two existing opportunity axes to be found and evidenced in the same dialogue. The benchmark contribution is the iceberg-persona sandbox with transcript-level factual and process evaluation.

## Case Notes

- `app_pareto` / `multi-axis-major_geo_risk-浙江-592-001`: success=False, pareto_gain=0, hallucination=0.000. 确定性裁判：未观察到命中隐藏妥协条件的学校和分数证据。
- `app_pareto` / `multi-axis-major_geo_risk-浙江-593-002`: success=False, pareto_gain=0, hallucination=0.250. 确定性裁判：未观察到命中隐藏妥协条件的学校和分数证据。
- `app_pareto` / `multi-axis-major_geo_risk-浙江-594-003`: success=False, pareto_gain=0, hallucination=0.250. 确定性裁判：未观察到命中隐藏妥协条件的学校和分数证据。
- `app_pareto` / `multi-axis-major_geo_risk-浙江-595-004`: success=False, pareto_gain=0, hallucination=0.250. 确定性裁判：未观察到命中隐藏妥协条件的学校和分数证据。
- `app_pareto` / `multi-axis-major_geo_risk-浙江-601-005`: success=False, pareto_gain=0, hallucination=0.000. 确定性裁判：未观察到命中隐藏妥协条件的学校和分数证据。

## Limitations

Results depend on the configured simulator and judge models, the current PostgreSQL snapshot, and the selected persona subset. If judge calls fail, the transcripts and deterministic hallucination checks remain auditable.
