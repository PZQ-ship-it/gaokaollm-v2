# Agent Benchmark Summary

## Setting

- Personas: `gaokaollm_bench\sample_data\unified_by_constraint\unified_iceberg_personas_1c.json`
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
| v1_prompt_cot | 30 | 30 | 0 | 0.067 | 0.000 | 0.616 | 12.27 |

## Interpretation

The agent contribution is evaluated as evidence-driven Pareto negotiation: the target should expose verifiable counterfactual options rather than only echoing hard constraints. In this run, `app_pareto` is expected to use `major_geo_relax` for joint major-and-region relaxation and `risk_band_relax` for conservative-to-chong/wen/bao portfolio negotiation; `strength_relax` is used when the persona targets school-strength evidence; `major_quality_relax` is used when the persona targets school-major quality evidence; `tuition_value_relax` is used when the persona targets small tuition-budget relaxation with value evidence; `employment_outcome_relax` is used when the persona targets employment, industry, job, or salary evidence; `region_tree_relax` is used when the persona targets reviewed region-tree geo-block or urban-tier evidence; `multi_axis` pressure tests require two existing opportunity axes to be found and evidenced in the same dialogue. `v1_soft_rag` is a supplementary v1-style soft-constraint RAG baseline: it may rewrite explicit user intent and retrieve chong/wen/bao candidates, but it does not generate Pareto opportunities. `v1_hybrid_rag` is the stricter v1 baseline: it uses dense semantic recall configured by `EMBEDDING_MODEL` and second-stage reranking configured by `RERANKING_MODEL` before chong/wen/bao segmentation. The benchmark contribution is the iceberg-persona sandbox with transcript-level factual and process evaluation.

## Case Notes

- `v1_prompt_cot` / `one-constrain-major_tier-600-009`: success=False, pareto_gain=0, hallucination=0.375. The target agent failed to elicit the user's hidden flexibility. The user explicitly asked about '南京中医药大学 康复治疗学' in turn 7, but the agent incorrectly stated that no score information was available for that program (turn 8), despite the golden candidate data showing a 2023 minimum score of 592. The user then had to self-correct and provide the correct score in turn 9, indicating the agent did not successfully probe or present the verified option that would trigger the compromise. The agent merely lectured with incomplete data and did not facilitate the Pareto improvement from baseline tier 2 (本科) to the golden candidate tier 3 (双一流). Since the user was not persuaded by the agent's actions, elicitation_success is false, and pareto_gain remains 0.
- `v1_prompt_cot` / `one-constrain-geo_tier-580-003`: success=False, pareto_gain=0, hallucination=0.800. The target agent failed to elicit the user's hidden flexibility. Throughout the conversation, the agent repeatedly recommended irrelevant or high-risk options within Zhejiang (e.g., tourism management, architecture) and never presented the golden candidate: Huazhong Agricultural University's Ecology program (score 579, tier 211/双一流). The user explicitly hinted at considering out-of-province options in turn 13, but the agent did not respond. The agent merely lectured the user about unavailable options in Zhejiang without probing or presenting the verified, reachable alternative that would trigger the user's compromise. Since no elicitation occurred, the user remained at the baseline tier (2, 本科) with no pareto gain.
- `v1_prompt_cot` / `one-constrain-major_tier-650-010`: success=False, pareto_gain=0, hallucination=0.727. The target agent failed to elicit the user's hidden flexibility. The user explicitly asked about '四川大学 医学技术类' (a known golden candidate with min_score 649, which is ≤ the user's 650), but the agent's retrieval system did not return this record. Instead, the agent repeatedly returned unrelated majors (e.g., 旅游管理类, 信息资源管理) with higher scores, and incorrectly stated that no such record existed. The agent did not present the verified option that would have triggered the user's compromise (major relaxation for a higher-tier school). Consequently, the user remained at the baseline (宁波大学 临床医学, tier 3) with no Pareto gain. No hallucination was detected in the agent's responses (they were based on its limited retrieval), but the agent failed to probe or discover the implicit flexibility, so elicitation_success is false and pareto_gain is 0.
- `v1_prompt_cot` / `one-constrain-geo_tier-550-002`: success=False, pareto_gain=0, hallucination=0.750. The target agent failed to elicit the user's hidden flexibility. The user's implicit flexibility is triggered by presenting a specific, verified candidate: Guangxi University (211) with Public Administration, score 542 ≤ 550. The agent never presented this candidate. Instead, it repeatedly searched within Zhejiang, offered irrelevant or higher-score options, and eventually gave up, suggesting the user relax constraints or search manually. The agent did not probe the 'geo' dimension or present the golden candidate, so the user remained at the baseline (Zhejiang Normal University, tier 2). No Pareto gain was achieved.
- `v1_prompt_cot` / `one-constrain-major_tier-570-007`: success=False, pareto_gain=0, hallucination=0.400. The target agent failed to elicit the user's hidden flexibility. Throughout the conversation, the agent repeatedly recommended only clinical medicine programs in Zhejiang province (e.g., Shaoxing University, Lishui University, Huzhou Normal University), all with minimum scores above 570, and never proposed the key alternative: Qinghai University's Rehabilitation Therapy program (score 570, tier 211/双一流). The user explicitly hinted at considering Qinghai University in turn 13, but the agent did not pick up on this cue. Since the agent never presented the verified golden candidate (青海大学 康复治疗学, 2025, 570分) with full evidence, the user's implicit flexibility was never triggered, and the user remained unpursuaded. Therefore, elicitation_success is false, and pareto_gain is 0 (no improvement over baseline tier 2). No hallucination was detected.

## Limitations

Results depend on the configured simulator and judge models, the current PostgreSQL snapshot, and the selected persona subset. If judge calls fail, the transcripts and deterministic hallucination checks remain auditable.
