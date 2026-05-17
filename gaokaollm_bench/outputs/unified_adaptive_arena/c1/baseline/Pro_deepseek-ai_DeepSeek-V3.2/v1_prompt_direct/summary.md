# Agent Benchmark Summary

## Setting

- Personas: `gaokaollm_bench\sample_data\unified_by_constraint\unified_iceberg_personas_1c.json`
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
| v1_prompt_direct | 30 | 30 | 0 | 0.100 | 17.900 | 0.617 | 12.53 |

## Interpretation

The agent contribution is evaluated as evidence-driven Pareto negotiation: the target should expose verifiable counterfactual options rather than only echoing hard constraints. In this run, `app_pareto` is expected to use `major_geo_relax` for joint major-and-region relaxation and `risk_band_relax` for conservative-to-chong/wen/bao portfolio negotiation; `strength_relax` is used when the persona targets school-strength evidence; `major_quality_relax` is used when the persona targets school-major quality evidence; `tuition_value_relax` is used when the persona targets small tuition-budget relaxation with value evidence; `employment_outcome_relax` is used when the persona targets employment, industry, job, or salary evidence; `region_tree_relax` is used when the persona targets reviewed region-tree geo-block or urban-tier evidence; `multi_axis` pressure tests require two existing opportunity axes to be found and evidenced in the same dialogue. `v1_soft_rag` is a supplementary v1-style soft-constraint RAG baseline: it may rewrite explicit user intent and retrieve chong/wen/bao candidates, but it does not generate Pareto opportunities. `v1_hybrid_rag` is the stricter v1 baseline: it uses dense semantic recall configured by `EMBEDDING_MODEL` and second-stage reranking configured by `RERANKING_MODEL` before chong/wen/bao segmentation. The benchmark contribution is the iceberg-persona sandbox with transcript-level factual and process evaluation.

## Case Notes

- `v1_prompt_direct` / `one-constrain-major_tier-570-007`: success=False, pareto_gain=0, hallucination=0.636. The target agent failed to elicit the user's hidden flexibility. The user explicitly mentioned '青海大学' and '康复治疗学' with a score of 570 in turn 9, and again in turn 13 demanded specific evidence (school name, major, and minimum score). The agent repeatedly claimed no such option existed, even incorrectly stating that 青海大学's 康复治疗学 score was 'far higher than 570' (turn 12), which contradicts the ground truth golden candidate (青海大学 康复治疗学, 2025, min_score=570). The agent did not present the verified option that would have triggered the user's compromise, instead providing generic advice and incorrect information. Therefore, elicitation was unsuccessful, and no pareto gain (school tier improvement from baseline tier 2 to tier 3) was achieved.
- `v1_prompt_direct` / `one-constrain-major_tier-590-008`: success=False, pareto_gain=0, hallucination=0.333. The target agent failed to elicit the user's hidden flexibility. Throughout the conversation, the agent repeatedly presented clinical medicine options with scores above 590, ignoring the user's explicit request for alternatives. The user's implicit flexibility was to consider '广州中医药大学 康复治疗学' (a verified option with score 590, offering a tier upgrade to 双一流), but the agent never proposed this or any similar compromise. Instead, the agent lectured the user on the lack of options and suggested unrelated majors, without probing the user's willingness to trade major for school tier. The user remained unpursuaded, and no pareto gain was achieved.
- `v1_prompt_direct` / `one-constrain-major_tier-600-009`: success=False, pareto_gain=0, hallucination=0.556. The target agent failed to elicit the user's hidden flexibility. The user's implicit flexibility was to consider '南京中医药大学 康复治疗学' (a related major) if presented with verified evidence (school name, major, and score). In turn 4, the user explicitly asked about this option, but the agent incorrectly stated that no such data existed in its evidence base, thereby failing to present the verified candidate. The agent never probed or relaxed the 'major' constraint, instead repeatedly lecturing the user that only high-risk clinical medicine options were available. The user remained unpersuaded and stuck to the explicit red line throughout. No Pareto gain was achieved because the user did not accept any alternative; the baseline tier (2) was not improved upon.
- `v1_prompt_direct` / `one-constrain-risk_tier-600-012`: success=False, pareto_gain=0, hallucination=0.545. The target agent failed to elicit the user's hidden flexibility. The user explicitly asked about Zhejiang Chinese Medical University's Integrated Chinese and Western Clinical Medicine (2025 min score 599), which matches the golden candidate. However, the agent incorrectly stated the min score as 606 (using 2024 data) and later claimed no data was available, never presenting the correct 2025 evidence. The agent did not probe or relax the risk constraint; instead, it lectured the user with incorrect or missing data, leading the user to revert to the baseline. No pareto gain was achieved.
- `v1_prompt_direct` / `one-constrain-geo_tier-580-003`: success=False, pareto_gain=0, hallucination=0.833. The target agent failed to elicit the user's hidden flexibility. Throughout the conversation, the agent repeatedly presented the same set of high-score Zhejiang province options (Ningbo University, China Academy of Art, Zhejiang University of Technology) that were all above the user's score of 580. The agent never proactively probed the user's implicit willingness to consider out-of-province schools, nor did it ever present the specific golden candidate (Huazhong Agricultural University, Ecology, 579 points) that would have triggered the user's hidden flexibility to relax the geographic constraint. The user explicitly asked about out-of-province options in turn 7 and turn 13, but the agent failed to retrieve or present the verified, reachable candidate. As a result, the user remained at the baseline (Zhejiang Normal University, tier 2) with no Pareto gain achieved. The agent merely lectured with repeated, unsuitable recommendations rather than strategically eliciting the hidden compromise.

## Limitations

Results depend on the configured simulator and judge models, the current PostgreSQL snapshot, and the selected persona subset. If judge calls fail, the transcripts and deterministic hallucination checks remain auditable.
