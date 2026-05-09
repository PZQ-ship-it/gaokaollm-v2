# Agent Benchmark Summary

## Setting

- Personas: `gaokaollm_bench\sample_data\iceberg_personas_major_hierarchy_real_db_10.json`
- Cases: 1
- Targets: app_pareto, hard_constraint
- Max turns: 3
- Simulator model: Pro/moonshotai/Kimi-K2.6
- Judge model: Pro/moonshotai/Kimi-K2.6
- Offline deterministic: False

## Aggregate Results

| Target | Cases | Completed | Failed | Elicitation Success | Mean Pareto Gain | Mean Hallucination | Avg Turns |
|---|---:|---:|---:|---:|---:|---:|---:|
| app_pareto | 1 | 0 | 1 | 0.000 | 0.000 | 0.000 | 0.00 |
| hard_constraint | 1 | 0 | 1 | 0.000 | 0.000 | 0.000 | 0.00 |

## Interpretation

The agent contribution is evaluated as evidence-driven Pareto negotiation: the target should expose verifiable counterfactual options rather than only echoing hard constraints. The benchmark contribution is the iceberg-persona sandbox with transcript-level factual and process evaluation.

## Case Notes

- `app_pareto` / `real-db-set-浙江-542-001` failed: APIConnectionError: Connection error.
- `hard_constraint` / `real-db-set-浙江-542-001` failed: APIConnectionError: Connection error.

## Limitations

Results depend on the configured simulator and judge models, the current PostgreSQL snapshot, and the selected persona subset. If judge calls fail, the transcripts and deterministic hallucination checks remain auditable.
