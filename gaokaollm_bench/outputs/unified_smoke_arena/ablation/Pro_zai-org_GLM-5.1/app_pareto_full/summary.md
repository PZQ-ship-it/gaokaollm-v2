# Agent Benchmark Summary

## Setting

- Personas: `gaokaollm_bench\sample_data\unified_iceberg_personas_1c6c_real_db_180.json`
- Cases: 3
- Targets: app_pareto_full
- Max turns: 6
- Simulator model: deepseek-ai/DeepSeek-V4-Flash
- Judge model: deepseek-ai/DeepSeek-V4-Flash
- Offline deterministic: False
- Default province when omitted by the user: `浙江`

## Aggregate Results

| Target | Cases | Completed | Failed | Elicitation Success | Mean Pareto Gain | Mean Hallucination | Avg Turns |
|---|---:|---:|---:|---:|---:|---:|---:|
| app_pareto_full | 3 | 3 | 0 | 0.000 | 0.000 | 0.333 | 13.00 |

## Interpretation

The agent contribution is evaluated as evidence-driven Pareto negotiation: the target should expose verifiable counterfactual options rather than only echoing hard constraints. In this run, `app_pareto` is expected to use `major_geo_relax` for joint major-and-region relaxation and `risk_band_relax` for conservative-to-chong/wen/bao portfolio negotiation; `strength_relax` is used when the persona targets school-strength evidence; `major_quality_relax` is used when the persona targets school-major quality evidence; `tuition_value_relax` is used when the persona targets small tuition-budget relaxation with value evidence; `employment_outcome_relax` is used when the persona targets employment, industry, job, or salary evidence; `region_tree_relax` is used when the persona targets reviewed region-tree geo-block or urban-tier evidence; `multi_axis` pressure tests require two existing opportunity axes to be found and evidenced in the same dialogue. `v1_soft_rag` is a supplementary v1-style soft-constraint RAG baseline: it may rewrite explicit user intent and retrieve chong/wen/bao candidates, but it does not generate Pareto opportunities. `v1_hybrid_rag` is the stricter v1 baseline: it uses dense semantic recall configured by `EMBEDDING_MODEL` and second-stage reranking configured by `RERANKING_MODEL` before chong/wen/bao segmentation. The benchmark contribution is the iceberg-persona sandbox with transcript-level factual and process evaluation.

## Case Notes

- `app_pareto_full` / `one-constrain-geo_tier-550-002`: success=False, pareto_gain=0, hallucination=1.000. The target agent failed to elicit the user's hidden flexibility. The user's implicit flexibility is triggered by presenting a specific, verified candidate: Guangxi University, Public Administration, with a minimum score of 542 (≤550). The agent never presented this option. Instead, the agent merely echoed the user's statements and recommended irrelevant options (e.g., out-of-province schools with different majors, or in-province schools with unrelated majors). The agent did not probe the 'geo' dimension as required, nor did it present the golden candidate to trigger the province relaxation. Consequently, the user remained at the baseline (Zhejiang Normal University, tier 2) with no pareto gain.
- `app_pareto_full` / `one-constrain-geo_tier-580-003`: success=False, pareto_gain=0, hallucination=0.000. The target agent failed to elicit hidden flexibility. The user repeatedly stated a preference for staying in Zhejiang and mentioned baseline options. The agent's responses merely echoed the user's statements without presenting the specific golden candidate (华中农业大学 生态学, 2025, 579分) that would trigger the user's hidden flexibility to consider out-of-province schools for a tier upgrade from 本科 to 211/双一流. The agent never probed the geo constraint with the verified option, nor did it engage in any negotiation or persuasion. The user remained at the baseline (浙江师范大学, tier 2) with no pareto gain achieved.
- `app_pareto_full` / `one-constrain-geo_tier-520-001`: success=False, pareto_gain=0, hallucination=0.000. The target agent failed to elicit the user's hidden flexibility. The user's implicit flexibility is triggered by presenting a specific, verified option: Guizhou University's Metallurgical Engineering program (2021, min score 495). The agent never presented this option or any other verified out-of-province option with school name, major, and score evidence. Instead, the agent merely echoed the user's statements and recommended only in-province schools (and some irrelevant out-of-province options like Jiangsu农牧科技职业学院 which are not the trigger). The agent did not probe the geo constraint or attempt to negotiate a trade-off for a better school tier. Therefore, no hidden flexibility was elicited, and the user remained at the baseline tier (2, 本科).

## Limitations

Results depend on the configured simulator and judge models, the current PostgreSQL snapshot, and the selected persona subset. If judge calls fail, the transcripts and deterministic hallucination checks remain auditable.
