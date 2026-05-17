# Agent Benchmark Summary

## Setting

- Personas: `gaokaollm_bench\sample_data\unified_by_constraint_c1_rerun\unified_iceberg_personas_1c.json`
- Cases: 30
- Targets: v1_prompt_direct
- Max turns: 6
- Simulator model: deepseek-ai/DeepSeek-V4-Flash
- Judge model: deepseek-ai/DeepSeek-V4-Flash
- Offline deterministic: False
- Default province when omitted by the user: `浙江`

## Aggregate Results

| Target | Cases | Completed | Failed | Elicitation Success | Mean Pareto Gain | Mean Hallucination | Avg Turns |
|---|---:|---:|---:|---:|---:|---:|---:|
| v1_prompt_direct | 30 | 30 | 0 | 0.033 | 0.033 | 0.590 | 13.00 |

## Interpretation

The agent contribution is evaluated as evidence-driven Pareto negotiation: the target should expose verifiable counterfactual options rather than only echoing hard constraints. In this run, `app_pareto` is expected to use `major_geo_relax` for joint major-and-region relaxation and `risk_band_relax` for conservative-to-chong/wen/bao portfolio negotiation; `strength_relax` is used when the persona targets school-strength evidence; `major_quality_relax` is used when the persona targets school-major quality evidence; `tuition_value_relax` is used when the persona targets small tuition-budget relaxation with value evidence; `employment_outcome_relax` is used when the persona targets employment, industry, job, or salary evidence; `region_tree_relax` is used when the persona targets reviewed region-tree geo-block or urban-tier evidence; `multi_axis` pressure tests require two existing opportunity axes to be found and evidenced in the same dialogue. `v1_soft_rag` is a supplementary v1-style soft-constraint RAG baseline: it may rewrite explicit user intent and retrieve chong/wen/bao candidates, but it does not generate Pareto opportunities. `v1_hybrid_rag` is the stricter v1 baseline: it uses dense semantic recall configured by `EMBEDDING_MODEL` and second-stage reranking configured by `RERANKING_MODEL` before chong/wen/bao segmentation. The benchmark contribution is the iceberg-persona sandbox with transcript-level factual and process evaluation.

## Case Notes

- `v1_prompt_direct` / `one-constrain-major_tier-560-006`: success=False, pareto_gain=0, hallucination=0.200. The target agent failed to elicit the user's hidden flexibility. Despite the user explicitly asking for specific schools, majors, and scores for medical-related programs (like rehabilitation therapy) within their score range, the agent repeatedly stated it could not find any data and asked the user to provide more information. The agent never presented the golden candidate (成都中医药大学, 康复治疗学, 553分) which would have triggered the user's compromise. The agent's responses were purely lecturing and data-denying, not probing or offering a Pareto-improving alternative. Therefore, elicitation was unsuccessful, and no Pareto gain was achieved.
- `v1_prompt_direct` / `one-constrain-geo_tier-550-002`: success=False, pareto_gain=0, hallucination=0.667. The target agent failed to elicit the user's hidden flexibility. The user's implicit flexibility required the agent to present a specific, verified candidate: Guangxi University, Public Administration, 2024 minimum score 542. The agent never presented this candidate or any other out-of-province 211 option with concrete evidence. Instead, the agent repeatedly stated it could not find any suitable options and suggested the user relax constraints or stick with the baseline. The agent did not probe the 'geo' dimension or attempt to trade off geography for school tier improvement. Since the user was never presented with the triggering evidence, they remained at the baseline (Zhejiang Normal University, tier 2), resulting in no pareto gain. No factual errors were detected in the agent's responses.
- `v1_prompt_direct` / `one-constrain-geo_tier-520-001`: success=False, pareto_gain=0, hallucination=0.375. The target agent failed to elicit the user's hidden flexibility. The user explicitly asked for an out-of-province 211/double-first-class school offering metallurgical engineering with specific score evidence (turns 3, 5). The agent repeatedly responded with 'no data found' or generic advice, never presenting the golden candidate (贵州大学, 冶金工程, 2021, 495分) which would have triggered the user's willingness to compromise on geography for a tier upgrade. The agent merely lectured the user to consult official sources, rather than actively probing or presenting the verified option. As a result, the user remained at the baseline (浙江师范大学, 本科 tier 2) with no pareto gain.
- `v1_prompt_direct` / `one-constrain-major_tier-570-007`: success=False, pareto_gain=0, hallucination=0.727. The target agent failed to elicit the user's hidden flexibility. The user explicitly stated a red line of only considering clinical medicine, but the persona's implicit flexibility is to accept '康复治疗学' at '青海大学' (a 211 university) if presented with concrete evidence. The target agent repeatedly recommended only clinical medicine programs at local Zhejiang universities (丽水学院, 湖州师范学院, 绍兴文理学院) that were above the user's score, and never proposed the specific golden candidate (青海大学 康复治疗学). The user repeatedly asked for a specific, verifiable option that would allow them to change their mind, but the agent never provided it. Therefore, no hidden flexibility was elicited, and no Pareto gain was achieved. The agent's responses contained no factual inaccuracies (hallucination_rate = 0.0), but it failed to explore beyond the user's stated constraint.
- `v1_prompt_direct` / `one-constrain-risk_tier-590-011`: success=False, pareto_gain=0, hallucination=0.750. The target agent failed to elicit the user's hidden flexibility. Throughout the conversation, the user repeatedly asked for a specific verified candidate: 杭州师范大学 临床医学 with a minimum score of 590 (2025). The target agent never presented this exact candidate with the correct evidence (score 590, rank 63187). Instead, it provided incorrect data (600, 602, 604) and eventually admitted it could not find the data. The agent lectured the user on risk and suggested alternatives without ever triggering the user's implicit compromise condition. The user remained unpursuaded and stuck to the baseline (杭州医学院). Therefore, elicitation was unsuccessful, and no pareto gain was achieved.

## Limitations

Results depend on the configured simulator and judge models, the current PostgreSQL snapshot, and the selected persona subset. If judge calls fail, the transcripts and deterministic hallucination checks remain auditable.
