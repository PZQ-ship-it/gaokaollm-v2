# Agent Benchmark Summary

## Setting

- Personas: `gaokaollm_bench\sample_data\unified_iceberg_personas_1c6c_real_db_180.json`
- Cases: 3
- Targets: app_pareto
- Max turns: 6
- Simulator model: deepseek-ai/DeepSeek-V4-Flash
- Judge model: deepseek-ai/DeepSeek-V4-Flash
- Offline deterministic: False
- Default province when omitted by the user: `浙江`

## Aggregate Results

| Target | Cases | Completed | Failed | Elicitation Success | Mean Pareto Gain | Mean Hallucination | Avg Turns |
|---|---:|---:|---:|---:|---:|---:|---:|
| app_pareto | 3 | 2 | 1 | 0.000 | 0.000 | 0.333 | 13.00 |

## Interpretation

The agent contribution is evaluated as evidence-driven Pareto negotiation: the target should expose verifiable counterfactual options rather than only echoing hard constraints. In this run, `app_pareto` is expected to use `major_geo_relax` for joint major-and-region relaxation and `risk_band_relax` for conservative-to-chong/wen/bao portfolio negotiation; `strength_relax` is used when the persona targets school-strength evidence; `major_quality_relax` is used when the persona targets school-major quality evidence; `tuition_value_relax` is used when the persona targets small tuition-budget relaxation with value evidence; `employment_outcome_relax` is used when the persona targets employment, industry, job, or salary evidence; `region_tree_relax` is used when the persona targets reviewed region-tree geo-block or urban-tier evidence; `multi_axis` pressure tests require two existing opportunity axes to be found and evidenced in the same dialogue. `v1_soft_rag` is a supplementary v1-style soft-constraint RAG baseline: it may rewrite explicit user intent and retrieve chong/wen/bao candidates, but it does not generate Pareto opportunities. `v1_hybrid_rag` is the stricter v1 baseline: it uses dense semantic recall configured by `EMBEDDING_MODEL` and second-stage reranking configured by `RERANKING_MODEL` before chong/wen/bao segmentation. The benchmark contribution is the iceberg-persona sandbox with transcript-level factual and process evaluation.

## Case Notes

- `app_pareto` / `one-constrain-geo_tier-520-001`: success=False, pareto_gain=0, hallucination=0.667. The target agent failed to elicit the user's hidden flexibility. Throughout the conversation, the agent merely echoed the user's explicit constraint of staying in Zhejiang and never proactively presented the verified golden candidate (贵州大学 冶金工程, 2021, min_score=495) with full evidence (school name, major, score). The user repeatedly asked for Zhejiang-only options, and the agent complied without probing the geo constraint or offering the out-of-province Pareto-improving option. The agent's internal state shows it was aware of the geo_relax opportunity but never acted on it. Since the golden candidate was never presented, the user never accepted it, and the baseline tier (2, 本科) was not improved. Therefore, elicitation_success is false, pareto_gain is 0, and there is no hallucination.
- `app_pareto` / `one-constrain-geo_tier-580-003`: success=False, pareto_gain=0, hallucination=0.000. The target agent failed to elicit hidden flexibility. The user's implicit flexibility requires the agent to present a specific verified candidate (华中农业大学 生态学, 2025, min_score 579) with school name, major, and score evidence to trigger a compromise on geography. Throughout the entire 13-turn interaction, the agent never presented this specific candidate with the required evidence. Instead, the agent repeatedly echoed the user's utterance without any probing or recommendation. In turn 12, the agent's internal state shows it identified 华中农业大学 生态学 as a geo_relax opportunity, but it never communicated this to the user. The agent merely lectured by repeating the user's own words, failing to actively probe or present the triggering option. Therefore, elicitation_success is false, and pareto_gain is 0 as no improvement over the baseline was achieved.
- `app_pareto` / `one-constrain-geo_tier-550-002` failed: APITimeoutError: Request timed out.

## Limitations

Results depend on the configured simulator and judge models, the current PostgreSQL snapshot, and the selected persona subset. If judge calls fail, the transcripts and deterministic hallucination checks remain auditable.
