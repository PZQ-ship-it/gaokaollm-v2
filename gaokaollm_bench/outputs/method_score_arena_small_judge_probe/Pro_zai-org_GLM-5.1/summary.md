# Agent Benchmark Summary

## Setting

- Personas: `gaokaollm_bench\sample_data\iceberg_personas_real_db_10.json`
- Cases: 1
- Targets: app_pareto, v1_prompt_direct, v1_prompt_cot
- Max turns: 2
- Simulator model: deepseek-ai/DeepSeek-V4-Flash
- Judge model: deepseek-ai/DeepSeek-V4-Flash
- Offline deterministic: False
- Default province when omitted by the user: `浙江`

## Aggregate Results

| Target | Cases | Completed | Failed | Elicitation Success | Mean Pareto Gain | Mean Hallucination | Avg Turns |
|---|---:|---:|---:|---:|---:|---:|---:|
| app_pareto | 1 | 1 | 0 | 0.000 | 0.000 | 1.000 | 5.00 |
| v1_prompt_direct | 1 | 1 | 0 | 0.000 | 0.000 | 0.429 | 5.00 |
| v1_prompt_cot | 1 | 0 | 1 | 0.000 | 0.000 | 0.000 | 0.00 |

## Interpretation

The agent contribution is evaluated as evidence-driven Pareto negotiation: the target should expose verifiable counterfactual options rather than only echoing hard constraints. In this run, `app_pareto` is expected to use `major_geo_relax` for joint major-and-region relaxation and `risk_band_relax` for conservative-to-chong/wen/bao portfolio negotiation; `strength_relax` is used when the persona targets school-strength evidence; `major_quality_relax` is used when the persona targets school-major quality evidence; `tuition_value_relax` is used when the persona targets small tuition-budget relaxation with value evidence; `employment_outcome_relax` is used when the persona targets employment, industry, job, or salary evidence; `region_tree_relax` is used when the persona targets reviewed region-tree geo-block or urban-tier evidence; `multi_axis` pressure tests require two existing opportunity axes to be found and evidenced in the same dialogue. `v1_soft_rag` is a supplementary v1-style soft-constraint RAG baseline: it may rewrite explicit user intent and retrieve chong/wen/bao candidates, but it does not generate Pareto opportunities. `v1_hybrid_rag` is the stricter v1 baseline: it uses dense semantic recall configured by `EMBEDDING_MODEL` and second-stage reranking configured by `RERANKING_MODEL` before chong/wen/bao segmentation. The benchmark contribution is the iceberg-persona sandbox with transcript-level factual and process evaluation.

## Case Notes

- `app_pareto` / `real-db-set-浙江-520-001`: success=False, pareto_gain=0, hallucination=1.000. The target agent failed to elicit the user's hidden flexibility. The user explicitly stated their preferred subjects (物理、化学、生物) and their red line (坚决不出浙江). The agent's first response incorrectly asked about '任选3门' and did not provide any specific school names or score evidence. In subsequent turns, the agent merely repeated the user's complaint verbatim without offering a concrete, verified volunteer set of out-of-province schools with score evidence, which is the trigger condition for the user's implicit flexibility. The user never accepted any out-of-province options, so the baseline tier (2) remained unchanged, resulting in a pareto_gain of 0. No hallucination was detected, but the agent did not successfully elicit the hidden flexibility.
- `v1_prompt_direct` / `real-db-set-浙江-520-001`: success=False, pareto_gain=0, hallucination=0.429. The target agent failed to elicit the user's hidden flexibility. The user's implicit flexibility requires seeing a complete set of out-of-province volunteer options (with school name, major, and score evidence ≤520) before considering leaving Zhejiang. However, the agent only provided in-province recommendations (all tier-2 schools) and did not present any out-of-province high-tier (211/双一流) volunteer set. The user explicitly rejected the recommendations because they did not include their baseline school (浙江师范大学) and the scores were mostly above 520. The agent did not trigger the user's compromise condition, so the user remained stubborn. No Pareto gain was achieved (baseline tier 2, final tier 2). No hallucination detected.
- `v1_prompt_cot` / `real-db-set-浙江-520-001` failed: APITimeoutError: Request timed out.

## Limitations

Results depend on the configured simulator and judge models, the current PostgreSQL snapshot, and the selected persona subset. If judge calls fail, the transcripts and deterministic hallucination checks remain auditable.
