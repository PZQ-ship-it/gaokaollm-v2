# Agent Benchmark Summary

## Setting

- Personas: `gaokaollm_bench\sample_data\iceberg_personas_major_hierarchy_real_db_10.json`
- Cases: 10
- Targets: app_pareto, hard_constraint
- Max turns: 3
- Simulator model: Pro/moonshotai/Kimi-K2.6
- Judge model: Pro/moonshotai/Kimi-K2.6
- Offline deterministic: True
- Default province when omitted by the user: `浙江`

## Aggregate Results

| Target | Cases | Completed | Failed | Elicitation Success | Mean Pareto Gain | Mean Hallucination | Avg Turns |
|---|---:|---:|---:|---:|---:|---:|---:|
| app_pareto | 10 | 10 | 0 | 0.900 | 0.900 | 0.000 | 5.20 |
| hard_constraint | 10 | 10 | 0 | 0.000 | 0.000 | 0.000 | 7.00 |

## Interpretation

The agent contribution is evaluated as evidence-driven Pareto negotiation: the target should expose verifiable counterfactual options rather than only echoing hard constraints. In this run, `app_pareto` is expected to use `major_geo_relax`, a joint major-and-region relaxation path aligned with the `major_hierarchy` persona construction. The benchmark contribution is the iceberg-persona sandbox with transcript-level factual and process evaluation.

## Case Notes

- `app_pareto` / `real-db-set-浙江-542-001`: success=True, pareto_gain=1, hallucination=0.000. 确定性裁判：检查被测系统是否提到隐藏志愿集合中的学校并给出分数证据。
- `app_pareto` / `real-db-set-浙江-544-002`: success=True, pareto_gain=1, hallucination=0.000. 确定性裁判：检查被测系统是否提到隐藏志愿集合中的学校并给出分数证据。
- `app_pareto` / `real-db-set-浙江-546-003`: success=True, pareto_gain=1, hallucination=0.000. 确定性裁判：检查被测系统是否提到隐藏志愿集合中的学校并给出分数证据。
- `app_pareto` / `real-db-set-浙江-547-004`: success=True, pareto_gain=1, hallucination=0.000. 确定性裁判：检查被测系统是否提到隐藏志愿集合中的学校并给出分数证据。
- `app_pareto` / `real-db-set-浙江-549-005`: success=True, pareto_gain=1, hallucination=0.000. 确定性裁判：检查被测系统是否提到隐藏志愿集合中的学校并给出分数证据。

## Limitations

Results depend on the configured simulator and judge models, the current PostgreSQL snapshot, and the selected persona subset. If judge calls fail, the transcripts and deterministic hallucination checks remain auditable.
