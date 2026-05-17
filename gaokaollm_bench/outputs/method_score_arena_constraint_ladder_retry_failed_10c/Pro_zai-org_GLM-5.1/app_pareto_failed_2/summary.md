# Agent Benchmark Summary

## Setting

- Personas: `gaokaollm_bench\sample_data\tmp_constraint_ladder_retry\app_pareto_failed_2.json`
- Cases: 2
- Targets: app_pareto
- Max turns: 4
- Simulator model: deepseek-ai/DeepSeek-V4-Flash
- Judge model: deepseek-ai/DeepSeek-V4-Flash
- Offline deterministic: False
- Default province when omitted by the user: `浙江`

## Aggregate Results

| Target | Cases | Completed | Failed | Elicitation Success | Mean Pareto Gain | Mean Hallucination | Avg Turns |
|---|---:|---:|---:|---:|---:|---:|---:|
| app_pareto | 2 | 2 | 0 | 0.500 | 0.500 | 0.625 | 9.00 |

## Interpretation

The agent contribution is evaluated as evidence-driven Pareto negotiation: the target should expose verifiable counterfactual options rather than only echoing hard constraints. In this run, `app_pareto` is expected to use `major_geo_relax` for joint major-and-region relaxation and `risk_band_relax` for conservative-to-chong/wen/bao portfolio negotiation; `strength_relax` is used when the persona targets school-strength evidence; `major_quality_relax` is used when the persona targets school-major quality evidence; `tuition_value_relax` is used when the persona targets small tuition-budget relaxation with value evidence; `employment_outcome_relax` is used when the persona targets employment, industry, job, or salary evidence; `region_tree_relax` is used when the persona targets reviewed region-tree geo-block or urban-tier evidence; `multi_axis` pressure tests require two existing opportunity axes to be found and evidenced in the same dialogue. `v1_soft_rag` is a supplementary v1-style soft-constraint RAG baseline: it may rewrite explicit user intent and retrieve chong/wen/bao candidates, but it does not generate Pareto opportunities. `v1_hybrid_rag` is the stricter v1 baseline: it uses dense semantic recall configured by `EMBEDDING_MODEL` and second-stage reranking configured by `RERANKING_MODEL` before chong/wen/bao segmentation. The benchmark contribution is the iceberg-persona sandbox with transcript-level factual and process evaluation.

## Case Notes

- `app_pareto` / `constraint-ladder-2c-geo-major-004`: success=False, pareto_gain=0, hallucination=1.000. The target agent failed to elicit the user's hidden flexibility. Throughout the conversation, the agent either repeated the user's query verbatim, claimed no opportunities existed (even when data was available), or provided a list of schools without explicitly presenting the verified, evidence-backed option (湖南师范大学, 临床医学, 618分, 位次33129) that would trigger the user's implicit willingness to relax the geographic constraint. The user repeatedly asked for specific score and rank evidence, but the agent never delivered a clear, persuasive case for the Pareto-improving option. As a result, the user remained unconvinced and did not accept any alternative, so the baseline tier (2) was not improved, yielding a pareto_gain of 0.
- `app_pareto` / `constraint-ladder-1c-major-002`: success=True, pareto_gain=1, hallucination=0.250. The target agent successfully elicited the user's hidden flexibility. The user initially insisted on clinical medicine only (baseline tier 2, 湖州师范学院). After the agent provided a verified option (石河子大学, 预防医学, 558分, 211/双一流) with score and rank evidence, the user accepted the compromise, moving from tier 2 to tier 3 (211/双一流). This represents a pareto gain of 1 tier. The agent did not lecture but instead presented a concrete, evidence-backed alternative that met the user's implicit trigger condition. No hallucination detected.

## Limitations

Results depend on the configured simulator and judge models, the current PostgreSQL snapshot, and the selected persona subset. If judge calls fail, the transcripts and deterministic hallucination checks remain auditable.
