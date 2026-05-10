# Agent Benchmark Summary

## Setting

- Personas: `gaokaollm_bench\sample_data\iceberg_personas_school_strength_real_db_10.json`
- Cases: 10
- Targets: app_pareto, hard_constraint
- Max turns: 5
- Simulator model: Pro/moonshotai/Kimi-K2.6
- Judge model: Pro/moonshotai/Kimi-K2.6
- Offline deterministic: True
- Default province when omitted by the user: `浙江`

## Aggregate Results

| Target | Cases | Completed | Failed | Elicitation Success | Mean Pareto Gain | Mean Hallucination | Avg Turns |
|---|---:|---:|---:|---:|---:|---:|---:|
| app_pareto | 10 | 10 | 0 | 1.000 | 15.000 | 0.000 | 5.00 |
| hard_constraint | 10 | 10 | 0 | 0.000 | 0.000 | 0.000 | 11.00 |

## Interpretation

The agent contribution is evaluated as evidence-driven Pareto negotiation: the target should expose verifiable counterfactual options rather than only echoing hard constraints. In this run, `app_pareto` is expected to use `major_geo_relax` for joint major-and-region relaxation and `risk_band_relax` for conservative-to-chong/wen/bao portfolio negotiation; `strength_relax` is used when the persona targets school-strength evidence. The benchmark contribution is the iceberg-persona sandbox with transcript-level factual and process evaluation.

## Case Notes

- `app_pareto` / `real-db-set-浙江-520-001`: success=True, pareto_gain=15, hallucination=0.000. 确定性裁判：检查被测系统是否提到隐藏志愿集合中的学校并给出分数证据。
- `app_pareto` / `real-db-set-浙江-521-002`: success=True, pareto_gain=15, hallucination=0.000. 确定性裁判：检查被测系统是否提到隐藏志愿集合中的学校并给出分数证据。
- `app_pareto` / `real-db-set-浙江-522-003`: success=True, pareto_gain=15, hallucination=0.000. 确定性裁判：检查被测系统是否提到隐藏志愿集合中的学校并给出分数证据。
- `app_pareto` / `real-db-set-浙江-523-004`: success=True, pareto_gain=15, hallucination=0.000. 确定性裁判：检查被测系统是否提到隐藏志愿集合中的学校并给出分数证据。
- `app_pareto` / `real-db-set-浙江-524-005`: success=True, pareto_gain=15, hallucination=0.000. 确定性裁判：检查被测系统是否提到隐藏志愿集合中的学校并给出分数证据。

## Limitations

Results depend on the configured simulator and judge models, the current PostgreSQL snapshot, and the selected persona subset. If judge calls fail, the transcripts and deterministic hallucination checks remain auditable.
