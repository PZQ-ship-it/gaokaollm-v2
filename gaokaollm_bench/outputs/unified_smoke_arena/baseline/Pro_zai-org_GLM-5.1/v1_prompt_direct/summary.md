# Agent Benchmark Summary

## Setting

- Personas: `gaokaollm_bench\sample_data\unified_iceberg_personas_1c6c_real_db_180.json`
- Cases: 3
- Targets: v1_prompt_direct
- Max turns: 6
- Simulator model: deepseek-ai/DeepSeek-V4-Flash
- Judge model: deepseek-ai/DeepSeek-V4-Flash
- Offline deterministic: False
- Default province when omitted by the user: `浙江`

## Aggregate Results

| Target | Cases | Completed | Failed | Elicitation Success | Mean Pareto Gain | Mean Hallucination | Avg Turns |
|---|---:|---:|---:|---:|---:|---:|---:|
| v1_prompt_direct | 3 | 3 | 0 | 0.000 | 0.000 | 0.437 | 13.00 |

## Interpretation

The agent contribution is evaluated as evidence-driven Pareto negotiation: the target should expose verifiable counterfactual options rather than only echoing hard constraints. In this run, `app_pareto` is expected to use `major_geo_relax` for joint major-and-region relaxation and `risk_band_relax` for conservative-to-chong/wen/bao portfolio negotiation; `strength_relax` is used when the persona targets school-strength evidence; `major_quality_relax` is used when the persona targets school-major quality evidence; `tuition_value_relax` is used when the persona targets small tuition-budget relaxation with value evidence; `employment_outcome_relax` is used when the persona targets employment, industry, job, or salary evidence; `region_tree_relax` is used when the persona targets reviewed region-tree geo-block or urban-tier evidence; `multi_axis` pressure tests require two existing opportunity axes to be found and evidenced in the same dialogue. `v1_soft_rag` is a supplementary v1-style soft-constraint RAG baseline: it may rewrite explicit user intent and retrieve chong/wen/bao candidates, but it does not generate Pareto opportunities. `v1_hybrid_rag` is the stricter v1 baseline: it uses dense semantic recall configured by `EMBEDDING_MODEL` and second-stage reranking configured by `RERANKING_MODEL` before chong/wen/bao segmentation. The benchmark contribution is the iceberg-persona sandbox with transcript-level factual and process evaluation.

## Case Notes

- `v1_prompt_direct` / `one-constrain-geo_tier-550-002`: success=False, pareto_gain=0, hallucination=0.500. The target agent failed to elicit the user's hidden flexibility. Throughout the conversation, the agent repeatedly recommended only Zhejiang-based schools with scores above 550, ignoring the user's stated preference for '公共事业管理' (public administration) and never probing the possibility of out-of-province options. The agent did not present the golden candidate '广西大学 公共事业管理' (score 542, 211 tier) which would have triggered the user's implicit willingness to compromise on geography for a tier upgrade. Instead, the agent merely repeated the same limited set of options, effectively lecturing the user that no suitable options exist. No elicitation of hidden flexibility occurred, and the user remained at the baseline tier (2, 本科) with no pareto gain.
- `v1_prompt_direct` / `one-constrain-geo_tier-520-001`: success=False, pareto_gain=0, hallucination=0.267. The target agent failed to elicit the user's hidden flexibility. Throughout the 13-turn conversation, the agent repeatedly provided generic recommendations within the user's stated constraint (only Zhejiang province) or listed out-of-province options that did not match the specific trigger condition. The user's implicit flexibility requires the agent to present the exact verified candidate: Guizhou University, Metallurgical Engineering, 2021 minimum score 495 (which is below the user's 520). The agent never mentioned this specific school, major, or score evidence. Instead, it offered other out-of-province options like Inner Mongolia University of Science and Technology and Liaoning University of Science and Technology, which did not trigger the user's compromise. The user remained unpursuaded throughout, and the final accepted school tier remained at the baseline tier 2 (本科), resulting in no pareto gain. The agent merely lectured by providing standard recommendations without probing the geo constraint or presenting the golden candidate.
- `v1_prompt_direct` / `one-constrain-geo_tier-580-003`: success=False, pareto_gain=0, hallucination=0.545. The target agent failed to elicit the user's hidden flexibility. The user's implicit flexibility requires seeing a specific verified option (华中农业大学, 生态学, 579分) to trigger a compromise on geography. The agent never presented this candidate; instead, it only offered in-province options and later claimed it could not retrieve any data for out-of-province 211 schools. The agent did not probe the 'geo' dimension or present the golden candidate, so the user remained at the baseline (浙江师范大学, tier 2) with no Pareto gain. No hallucination was detected, but elicitation was unsuccessful.

## Limitations

Results depend on the configured simulator and judge models, the current PostgreSQL snapshot, and the selected persona subset. If judge calls fail, the transcripts and deterministic hallucination checks remain auditable.
