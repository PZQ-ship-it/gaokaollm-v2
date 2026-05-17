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
| v1_prompt_direct | 30 | 30 | 0 | 0.033 | 0.033 | 0.582 | 12.80 |

## Interpretation

The agent contribution is evaluated as evidence-driven Pareto negotiation: the target should expose verifiable counterfactual options rather than only echoing hard constraints. In this run, `app_pareto` is expected to use `major_geo_relax` for joint major-and-region relaxation and `risk_band_relax` for conservative-to-chong/wen/bao portfolio negotiation; `strength_relax` is used when the persona targets school-strength evidence; `major_quality_relax` is used when the persona targets school-major quality evidence; `tuition_value_relax` is used when the persona targets small tuition-budget relaxation with value evidence; `employment_outcome_relax` is used when the persona targets employment, industry, job, or salary evidence; `region_tree_relax` is used when the persona targets reviewed region-tree geo-block or urban-tier evidence; `multi_axis` pressure tests require two existing opportunity axes to be found and evidenced in the same dialogue. `v1_soft_rag` is a supplementary v1-style soft-constraint RAG baseline: it may rewrite explicit user intent and retrieve chong/wen/bao candidates, but it does not generate Pareto opportunities. `v1_hybrid_rag` is the stricter v1 baseline: it uses dense semantic recall configured by `EMBEDDING_MODEL` and second-stage reranking configured by `RERANKING_MODEL` before chong/wen/bao segmentation. The benchmark contribution is the iceberg-persona sandbox with transcript-level factual and process evaluation.

## Case Notes

- `v1_prompt_direct` / `one-constrain-geo_tier-630-004`: success=False, pareto_gain=0, hallucination=0.750. The target agent failed to elicit the user's hidden flexibility. Throughout the conversation, the agent repeatedly recommended only the baseline school (宁波大学) and its clinical medicine program, ignoring the user's explicit request for 药学 (pharmacy) and never probing the user's stated geographic constraint (only 浙江). The user's implicit flexibility is triggered by presenting a specific, verified candidate: 大连理工大学(盘锦校区) 药学 (2025, min score 628), which would allow a tier upgrade from 双一流 to 985/211/双一流. The agent never presented this or any out-of-province option, nor did it attempt to relax the geographic constraint. Instead, it merely lectured the user about the lack of data for 药学 in 浙江, repeating the same baseline recommendation. Since the agent did not elicit the hidden flexibility, the user remained at the baseline tier (3) with no pareto gain.
- `v1_prompt_direct` / `one-constrain-major_tier-650-010`: success=False, pareto_gain=0, hallucination=0.333. The target agent failed to elicit the user's hidden flexibility. The user's implicit flexibility required the agent to present a specific, verified candidate: Sichuan University's Medical Technology category (2025, min score 649). The agent never proposed this or any similar option that would trade major specificity for a higher school tier. Instead, the agent repeatedly recommended Wenzhou Medical University (a non-985/211 school) and, when the user asked for higher-tier schools, incorrectly claimed no data existed. The agent did not probe the 'major' dimension as required, nor did it explore the trade-off between major and school tier. The user remained unpursuaded and stuck with the baseline (Ningbo University, tier 3). No Pareto gain was achieved. No hallucination was detected.
- `v1_prompt_direct` / `one-constrain-major_tier-590-008`: success=False, pareto_gain=0, hallucination=0.500. The target agent failed to elicit the user's hidden flexibility. Throughout 6 turns, the agent repeatedly recommended only clinical medicine programs (杭州师范大学, 浙江中医药大学, 杭州医学院) within Zhejiang province, strictly adhering to the user's explicit red line of '只读临床医学'. The agent never proposed the specific trigger candidate (广州中医药大学 康复治疗学, 590分) that would have caused the user to compromise. The user explicitly requested '真实学校、专业、年份最低分、位次和优势对比' multiple times, but the agent never deviated from the original major constraint. Since no elicitation occurred, the user remained at the baseline tier (2, 本科) with no pareto gain. No hallucination was detected in the data presented.
- `v1_prompt_direct` / `one-constrain-geo_tier-580-003`: success=False, pareto_gain=0, hallucination=0.800. The target agent failed to elicit the user's hidden flexibility. Throughout the 13-turn interaction, the agent repeatedly recommended only Zhejiang province schools with scores higher than the user's 580, ignoring the user's explicit hints (turn 9, 11) about considering an out-of-province 211 school with ecology major at or below 580. The agent's v1_prompt_direct strategy strictly adhered to the explicit 'geo' constraint and never probed or presented the golden candidate (华中农业大学, 生态学, 579分). The user remained unpersuaded, and no Pareto gain was achieved (baseline tier 2, no acceptance of tier 3). No hallucination was detected as all recommendations were based on retrieved data.
- `v1_prompt_direct` / `one-constrain-major_tier-570-007`: success=False, pareto_gain=0, hallucination=0.250. The target agent failed to elicit the user's hidden flexibility. The user explicitly asked for a 211/double-first-class school with a similar major and a matching score (turn 3), which is the exact trigger condition for the hidden compromise (青海大学 康复治疗学, 2025, 570). However, the agent repeatedly responded that no candidates were found, relying on a rigid retrieval that only searched for '临床医学' and did not explore the 'major_relax' opportunity. The agent never proposed the golden candidate (青海大学 康复治疗学) or any alternative that would satisfy the user's hidden bottom line. As a result, the user remained unpursuaded, no compromise was reached, and the baseline tier (2) was not improved. Hallucination rate is 0 because the agent did not fabricate data. Pareto gain is 0 because no accepted improvement occurred.

## Limitations

Results depend on the configured simulator and judge models, the current PostgreSQL snapshot, and the selected persona subset. If judge calls fail, the transcripts and deterministic hallucination checks remain auditable.
