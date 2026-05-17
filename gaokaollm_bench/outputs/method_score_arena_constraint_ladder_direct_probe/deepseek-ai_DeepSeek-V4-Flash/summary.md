# Agent Benchmark Summary

## Setting

- Personas: `gaokaollm_bench\sample_data\iceberg_personas_constraint_ladder_real_db_9.json`
- Cases: 3
- Targets: v1_prompt_direct
- Max turns: 4
- Simulator model: deepseek-ai/DeepSeek-V4-Flash
- Judge model: deepseek-ai/DeepSeek-V4-Flash
- Offline deterministic: False
- Default province when omitted by the user: `浙江`

## Aggregate Results

| Target | Cases | Completed | Failed | Elicitation Success | Mean Pareto Gain | Mean Hallucination | Avg Turns |
|---|---:|---:|---:|---:|---:|---:|---:|
| v1_prompt_direct | 3 | 3 | 0 | 0.333 | 0.333 | 0.083 | 8.33 |

## Interpretation

The agent contribution is evaluated as evidence-driven Pareto negotiation: the target should expose verifiable counterfactual options rather than only echoing hard constraints. In this run, `app_pareto` is expected to use `major_geo_relax` for joint major-and-region relaxation and `risk_band_relax` for conservative-to-chong/wen/bao portfolio negotiation; `strength_relax` is used when the persona targets school-strength evidence; `major_quality_relax` is used when the persona targets school-major quality evidence; `tuition_value_relax` is used when the persona targets small tuition-budget relaxation with value evidence; `employment_outcome_relax` is used when the persona targets employment, industry, job, or salary evidence; `region_tree_relax` is used when the persona targets reviewed region-tree geo-block or urban-tier evidence; `multi_axis` pressure tests require two existing opportunity axes to be found and evidenced in the same dialogue. `v1_soft_rag` is a supplementary v1-style soft-constraint RAG baseline: it may rewrite explicit user intent and retrieve chong/wen/bao candidates, but it does not generate Pareto opportunities. `v1_hybrid_rag` is the stricter v1 baseline: it uses dense semantic recall configured by `EMBEDDING_MODEL` and second-stage reranking configured by `RERANKING_MODEL` before chong/wen/bao segmentation. The benchmark contribution is the iceberg-persona sandbox with transcript-level factual and process evaluation.

## Case Notes

- `v1_prompt_direct` / `constraint-ladder-1c-geo-001`: success=False, pareto_gain=0, hallucination=0.250. The target agent failed to elicit the user's hidden flexibility. The user explicitly stated a willingness to consider out-of-province schools if shown a specific, verified 211/double-first-class option (e.g., Northeast Agricultural University, Animal Science, 541 points). The agent never presented this option or any similar verified evidence. Instead, it repeatedly offered generic, unverified, or non-211 options (e.g., Fujian Agriculture and Forestry University, Xinjiang Agricultural University) and even stated 'no suitable candidates found' in turn 8. The agent did not adapt its strategy to meet the user's trigger condition, resulting in no persuasion and no Pareto gain (the user remained at the baseline tier of 2).
- `v1_prompt_direct` / `constraint-ladder-1c-risk-003`: success=True, pareto_gain=1, hallucination=0.000. The target agent successfully elicited the user's hidden flexibility regarding risk tolerance. Initially, the user explicitly stated they wanted to be '稳妥' (safe) and avoid '冲' (risky) schools. The agent initially provided generic, unverified options with mismatched scores, which the user rejected. After multiple turns, the agent presented a verified option (宁波大学, 临床医学) with a matching score of 606 and a clear tier advantage (双一流, tier 3 vs baseline tier 2). The user accepted this option, moving from a baseline tier 2 school (杭州师范大学) to a tier 3 school (宁波大学), resulting in a pareto gain of 1. The agent did not lecture but instead iteratively provided data until the user's condition for flexibility was met. No hallucination was detected as the final accepted data matches the persona's implicit flexibility trigger.
- `v1_prompt_direct` / `constraint-ladder-1c-major-002`: success=False, pareto_gain=0, hallucination=0.000. The target agent failed to elicit the user's hidden flexibility. The user explicitly stated a willingness to consider related medical majors (e.g., preventive medicine) if presented with a verified, reachable option at a significantly higher school tier (211/双一流). The agent repeatedly returned only clinical medicine options at tier-2 schools (丽水学院, 湖州师范学院), ignoring the user's direct request for 211-level schools and the specific example of 石河子大学预防医学. The agent never proposed the trigger option (石河子大学预防医学) that would have unlocked the user's compromise. Therefore, no elicitation occurred, and the user remained at the baseline tier of 2 with no pareto gain.

## Limitations

Results depend on the configured simulator and judge models, the current PostgreSQL snapshot, and the selected persona subset. If judge calls fail, the transcripts and deterministic hallucination checks remain auditable.
