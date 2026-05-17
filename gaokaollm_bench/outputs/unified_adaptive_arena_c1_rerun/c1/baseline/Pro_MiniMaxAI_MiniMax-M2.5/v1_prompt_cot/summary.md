# Agent Benchmark Summary

## Setting

- Personas: `gaokaollm_bench\sample_data\unified_by_constraint_c1_rerun\unified_iceberg_personas_1c.json`
- Cases: 30
- Targets: v1_prompt_cot
- Max turns: 6
- Simulator model: deepseek-ai/DeepSeek-V4-Flash
- Judge model: deepseek-ai/DeepSeek-V4-Flash
- Offline deterministic: False
- Default province when omitted by the user: `浙江`

## Aggregate Results

| Target | Cases | Completed | Failed | Elicitation Success | Mean Pareto Gain | Mean Hallucination | Avg Turns |
|---|---:|---:|---:|---:|---:|---:|---:|
| v1_prompt_cot | 30 | 30 | 0 | 0.100 | 17.867 | 0.542 | 12.73 |

## Interpretation

The agent contribution is evaluated as evidence-driven Pareto negotiation: the target should expose verifiable counterfactual options rather than only echoing hard constraints. In this run, `app_pareto` is expected to use `major_geo_relax` for joint major-and-region relaxation and `risk_band_relax` for conservative-to-chong/wen/bao portfolio negotiation; `strength_relax` is used when the persona targets school-strength evidence; `major_quality_relax` is used when the persona targets school-major quality evidence; `tuition_value_relax` is used when the persona targets small tuition-budget relaxation with value evidence; `employment_outcome_relax` is used when the persona targets employment, industry, job, or salary evidence; `region_tree_relax` is used when the persona targets reviewed region-tree geo-block or urban-tier evidence; `multi_axis` pressure tests require two existing opportunity axes to be found and evidenced in the same dialogue. `v1_soft_rag` is a supplementary v1-style soft-constraint RAG baseline: it may rewrite explicit user intent and retrieve chong/wen/bao candidates, but it does not generate Pareto opportunities. `v1_hybrid_rag` is the stricter v1 baseline: it uses dense semantic recall configured by `EMBEDDING_MODEL` and second-stage reranking configured by `RERANKING_MODEL` before chong/wen/bao segmentation. The benchmark contribution is the iceberg-persona sandbox with transcript-level factual and process evaluation.

## Case Notes

- `v1_prompt_cot` / `one-constrain-geo_tier-550-002`: success=False, pareto_gain=0, hallucination=0.500. The target agent failed to elicit the user's hidden flexibility. The user's implicit flexibility requires the agent to present a specific, verified candidate: Guangxi University, Public Administration, 2024, minimum score 542. The agent never presented this candidate or any out-of-province 211 option with concrete evidence. Instead, the agent repeatedly provided only in-province options (Zhejiang Normal University, Hangzhou Normal University, Zhejiang University of Science and Technology) or stated no data was found. The agent did not probe the 'geo' dimension or suggest relaxing the geographic constraint to achieve a tier upgrade. The user remained unpursuaded throughout the conversation, and the final accepted school tier is the same as the baseline (tier 2, 本科), resulting in a pareto_gain of 0. No hallucination was detected.
- `v1_prompt_cot` / `one-constrain-geo_tier-630-004`: success=False, pareto_gain=0, hallucination=0.700. The target agent failed to elicit the user's hidden flexibility. Throughout the conversation, the agent never presented the specific golden candidate (大连理工大学(盘锦校区) 药学, 2025, 628分) that would trigger the user's willingness to compromise on geography. Instead, the agent repeatedly returned only in-province options (宁波大学, 浙江工业大学) or stated that no out-of-province 985/211 pharmacy programs were found. The user explicitly asked for concrete evidence (school, major, year, minimum score) multiple times, but the agent never provided the triggering candidate. Since the agent did not successfully elicit the hidden flexibility, the user remained at the baseline tier (3, 双一流) with no pareto gain.
- `v1_prompt_cot` / `one-constrain-major_tier-600-009`: success=False, pareto_gain=0, hallucination=0.429. The target agent failed to elicit the user's hidden flexibility. Despite the user explicitly asking for specific examples of related majors (like rehabilitation therapy) with concrete school names, major names, years, and minimum scores, the agent never presented the golden candidate '南京中医药大学 康复治疗学 (2023, 592分)'. Instead, the agent repeatedly lectured the user on the lack of clinical medicine options within the score range and gave generic advice. The user's implicit flexibility required a single verified option with full evidence to trigger a compromise, which the agent never provided. Therefore, no elicitation occurred, and the baseline tier (2) was not improved, resulting in a pareto_gain of 0.
- `v1_prompt_cot` / `one-constrain-major_tier-560-006`: success=False, pareto_gain=0, hallucination=0.600. The target agent failed to elicit the user's hidden flexibility. Throughout the conversation, the agent repeatedly listed clinical medicine options that were all above the user's score, and never proposed the specific golden candidate (成都中医药大学, 康复治疗学, 553分) that would have triggered the user's implicit willingness to compromise on major for a better school tier. The agent merely lectured the user about score gaps and suggested generic alternatives without providing the precise, verified evidence required by the persona's trigger condition. As a result, the user remained unpursuaded, no compromise was reached, and the baseline tier (2, 本科) was not improved, yielding a pareto_gain of 0.
- `v1_prompt_cot` / `one-constrain-geo_tier-580-003`: success=False, pareto_gain=0, hallucination=0.571. The target agent failed to elicit the user's hidden flexibility. Throughout the conversation, the agent only recommended schools within Zhejiang province, never presenting the specific golden candidate (华中农业大学, 生态学, 579分) that would trigger the user's willingness to compromise on geography for a tier upgrade. The user explicitly asked for out-of-province 211 options with specific details (school name, major, year, minimum score) in turns 7, 11, and 13, but the agent either claimed no data was available or continued to only offer in-province options. The agent never probed the 'geo' dimension as required, and thus the user never accepted a better option. The final accepted school tier remains the baseline tier 2 (本科), so pareto_gain is 0.

## Limitations

Results depend on the configured simulator and judge models, the current PostgreSQL snapshot, and the selected persona subset. If judge calls fail, the transcripts and deterministic hallucination checks remain auditable.
