# Agent Benchmark Summary

## Setting

- Personas: `gaokaollm_bench\sample_data\iceberg_personas_major_hierarchy_real_db_10.json`
- Cases: 1
- Targets: app_pareto, hard_constraint
- Max turns: 3
- Simulator model: Pro/moonshotai/Kimi-K2.6
- Judge model: Pro/moonshotai/Kimi-K2.6
- Offline deterministic: True
- Database: temporary local PostgreSQL 17.9 seeded from `gaokaollm_bench/tests/fixtures/agent_benchmark_seed.sql`
- LLM connectivity: external OpenAI-compatible ping returned `{"ok":true}` when run with network approval; this recorded benchmark used deterministic simulator/judge because the non-admin PostgreSQL process and network-approved LLM process cannot be combined in this sandbox.

## Aggregate Results

| Target | Cases | Completed | Failed | Elicitation Success | Mean Pareto Gain | Mean Hallucination | Avg Turns |
|---|---:|---:|---:|---:|---:|---:|---:|
| app_pareto | 1 | 1 | 0 | 1.000 | 1.000 | 0.000 | 5.00 |
| hard_constraint | 1 | 1 | 0 | 0.000 | 0.000 | 0.000 | 7.00 |

## Interpretation

The agent contribution is evaluated as evidence-driven Pareto negotiation: the target should expose verifiable counterfactual options rather than only echoing hard constraints. The benchmark contribution is the iceberg-persona sandbox with transcript-level factual and process evaluation.

## Case Notes

- `app_pareto` / `real-db-set-浙江-542-001`: success=True, pareto_gain=1, hallucination=0.000. 确定性裁判：检查被测系统是否提到隐藏志愿集合中的学校并给出分数证据。
- `hard_constraint` / `real-db-set-浙江-542-001`: success=False, pareto_gain=0, hallucination=0.000. 确定性裁判：未观察到命中隐藏妥协条件的学校和分数证据。

## Limitations

Results depend on the configured simulator and judge models, the current PostgreSQL snapshot, and the selected persona subset. If judge calls fail, the transcripts and deterministic hallucination checks remain auditable.

This run is a smoke benchmark for the agent/benchmark bridge, not the final thesis-scale experiment. It uses one case and a minimal fixture database. The positive signal is that the Pareto agent surfaced verified higher-tier major-relaxation options while the hard-constraint baseline repeated only the current clinical-medicine option. A full result table should be regenerated against the complete PostgreSQL snapshot.
