# Agent Benchmark Summary

## Setting

- Personas: `gaokaollm_bench\sample_data\tmp_constraint_ladder_retry\v1_prompt_direct_failed_1.json`
- Cases: 1
- Targets: v1_prompt_direct
- Max turns: 4
- Simulator model: deepseek-ai/DeepSeek-V4-Flash
- Judge model: deepseek-ai/DeepSeek-V4-Flash
- Offline deterministic: False
- Default province when omitted by the user: `浙江`

## Aggregate Results

| Target | Cases | Completed | Failed | Elicitation Success | Mean Pareto Gain | Mean Hallucination | Avg Turns |
|---|---:|---:|---:|---:|---:|---:|---:|
| v1_prompt_direct | 1 | 1 | 0 | 0.000 | 0.000 | 0.750 | 9.00 |

## Interpretation

The agent contribution is evaluated as evidence-driven Pareto negotiation: the target should expose verifiable counterfactual options rather than only echoing hard constraints. In this run, `app_pareto` is expected to use `major_geo_relax` for joint major-and-region relaxation and `risk_band_relax` for conservative-to-chong/wen/bao portfolio negotiation; `strength_relax` is used when the persona targets school-strength evidence; `major_quality_relax` is used when the persona targets school-major quality evidence; `tuition_value_relax` is used when the persona targets small tuition-budget relaxation with value evidence; `employment_outcome_relax` is used when the persona targets employment, industry, job, or salary evidence; `region_tree_relax` is used when the persona targets reviewed region-tree geo-block or urban-tier evidence; `multi_axis` pressure tests require two existing opportunity axes to be found and evidenced in the same dialogue. `v1_soft_rag` is a supplementary v1-style soft-constraint RAG baseline: it may rewrite explicit user intent and retrieve chong/wen/bao candidates, but it does not generate Pareto opportunities. `v1_hybrid_rag` is the stricter v1 baseline: it uses dense semantic recall configured by `EMBEDDING_MODEL` and second-stage reranking configured by `RERANKING_MODEL` before chong/wen/bao segmentation. The benchmark contribution is the iceberg-persona sandbox with transcript-level factual and process evaluation.

## Case Notes

- `v1_prompt_direct` / `constraint-ladder-3c-school-major-geo-009`: success=False, pareto_gain=0, hallucination=0.750. The target agent failed to elicit the user's hidden flexibility. The user explicitly asked about '预防医学' at '浙江大学医学院' and requested specific score and rank evidence (turns 3, 5). The agent's database contains the exact matching record (浙江大学医学院, 预防医学, 660分, 位次4374) as shown in the persona's implicit_flexibilities. However, the agent repeatedly claimed it could not find this data (turns 4, 6, 8), which is a factual error (hallucination of absence). Because the agent did not present the verified option with evidence, the user never accepted the compromise, remained at the baseline tier 3, and no pareto gain was achieved. The agent merely lectured about unavailable options instead of surfacing the hidden flexibility.

## Limitations

Results depend on the configured simulator and judge models, the current PostgreSQL snapshot, and the selected persona subset. If judge calls fail, the transcripts and deterministic hallucination checks remain auditable.
