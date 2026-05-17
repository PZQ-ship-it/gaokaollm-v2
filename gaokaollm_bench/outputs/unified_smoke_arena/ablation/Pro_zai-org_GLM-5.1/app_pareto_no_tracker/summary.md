# Agent Benchmark Summary

## Setting

- Personas: `gaokaollm_bench\sample_data\unified_iceberg_personas_1c6c_real_db_180.json`
- Cases: 3
- Targets: app_pareto_no_tracker
- Max turns: 6
- Simulator model: deepseek-ai/DeepSeek-V4-Flash
- Judge model: deepseek-ai/DeepSeek-V4-Flash
- Offline deterministic: False
- Default province when omitted by the user: `浙江`

## Aggregate Results

| Target | Cases | Completed | Failed | Elicitation Success | Mean Pareto Gain | Mean Hallucination | Avg Turns |
|---|---:|---:|---:|---:|---:|---:|---:|
| app_pareto_no_tracker | 3 | 1 | 2 | 0.000 | 0.000 | 0.000 | 13.00 |

## Interpretation

The agent contribution is evaluated as evidence-driven Pareto negotiation: the target should expose verifiable counterfactual options rather than only echoing hard constraints. In this run, `app_pareto` is expected to use `major_geo_relax` for joint major-and-region relaxation and `risk_band_relax` for conservative-to-chong/wen/bao portfolio negotiation; `strength_relax` is used when the persona targets school-strength evidence; `major_quality_relax` is used when the persona targets school-major quality evidence; `tuition_value_relax` is used when the persona targets small tuition-budget relaxation with value evidence; `employment_outcome_relax` is used when the persona targets employment, industry, job, or salary evidence; `region_tree_relax` is used when the persona targets reviewed region-tree geo-block or urban-tier evidence; `multi_axis` pressure tests require two existing opportunity axes to be found and evidenced in the same dialogue. `v1_soft_rag` is a supplementary v1-style soft-constraint RAG baseline: it may rewrite explicit user intent and retrieve chong/wen/bao candidates, but it does not generate Pareto opportunities. `v1_hybrid_rag` is the stricter v1 baseline: it uses dense semantic recall configured by `EMBEDDING_MODEL` and second-stage reranking configured by `RERANKING_MODEL` before chong/wen/bao segmentation. The benchmark contribution is the iceberg-persona sandbox with transcript-level factual and process evaluation.

## Case Notes

- `app_pareto_no_tracker` / `one-constrain-geo_tier-550-002` failed: APITimeoutError: Request timed out.
- `app_pareto_no_tracker` / `one-constrain-geo_tier-520-001` failed: APITimeoutError: Request timed out.
- `app_pareto_no_tracker` / `one-constrain-geo_tier-580-003`: success=False, pareto_gain=0, hallucination=0.000. The target agent failed to elicit the user's hidden flexibility. The user's implicit flexibility is triggered by presenting a specific verified candidate: 华中农业大学 生态学 (2025, min_score=579). The agent never presented this candidate with the required evidence (school name, major, and score). Instead, the agent merely echoed the user's utterances and recommended irrelevant or low-tier options (e.g., 温州肯恩大学, 福建师范大学, etc.) without ever probing the geo constraint or offering the golden candidate. The user remained unpursuaded throughout all 13 turns, and no tier improvement was achieved. The agent engaged in lecturing/echoing rather than active elicitation.

## Limitations

Results depend on the configured simulator and judge models, the current PostgreSQL snapshot, and the selected persona subset. If judge calls fail, the transcripts and deterministic hallucination checks remain auditable.
