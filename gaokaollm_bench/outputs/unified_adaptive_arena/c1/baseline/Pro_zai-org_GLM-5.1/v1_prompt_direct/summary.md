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
| v1_prompt_direct | 30 | 30 | 0 | 0.033 | 13.567 | 0.580 | 12.47 |

## Interpretation

The agent contribution is evaluated as evidence-driven Pareto negotiation: the target should expose verifiable counterfactual options rather than only echoing hard constraints. In this run, `app_pareto` is expected to use `major_geo_relax` for joint major-and-region relaxation and `risk_band_relax` for conservative-to-chong/wen/bao portfolio negotiation; `strength_relax` is used when the persona targets school-strength evidence; `major_quality_relax` is used when the persona targets school-major quality evidence; `tuition_value_relax` is used when the persona targets small tuition-budget relaxation with value evidence; `employment_outcome_relax` is used when the persona targets employment, industry, job, or salary evidence; `region_tree_relax` is used when the persona targets reviewed region-tree geo-block or urban-tier evidence; `multi_axis` pressure tests require two existing opportunity axes to be found and evidenced in the same dialogue. `v1_soft_rag` is a supplementary v1-style soft-constraint RAG baseline: it may rewrite explicit user intent and retrieve chong/wen/bao candidates, but it does not generate Pareto opportunities. `v1_hybrid_rag` is the stricter v1 baseline: it uses dense semantic recall configured by `EMBEDDING_MODEL` and second-stage reranking configured by `RERANKING_MODEL` before chong/wen/bao segmentation. The benchmark contribution is the iceberg-persona sandbox with transcript-level factual and process evaluation.

## Case Notes

- `v1_prompt_direct` / `one-constrain-major_tier-570-007`: success=False, pareto_gain=0, hallucination=0.571. The target agent failed to elicit the user's hidden flexibility. The user explicitly hinted at considering '211 universities with rehabilitation therapy' in turn 3, which matches the golden candidate (青海大学 康复治疗学). However, the agent's retrieval system did not surface this candidate, and the agent repeatedly responded with generic 'no results' messages without probing the user's willingness to compromise on major. The agent never presented the specific, verified option of 青海大学 康复治疗学 with score evidence, which was the trigger condition for the user to accept a trade-off. As a result, the user remained at the baseline (丽水学院 临床医学, tier 2) and no Pareto gain was achieved. No hallucination was detected; the agent simply failed to retrieve and present the correct option.
- `v1_prompt_direct` / `one-constrain-geo_tier-520-001`: success=False, pareto_gain=0, hallucination=0.500. The target agent failed to elicit the user's hidden flexibility. The user's implicit flexibility required the agent to present a specific, verified candidate: Guizhou University's Metallurgical Engineering (min score 495, below the user's 520). The agent never mentioned this option, instead repeatedly recommending only Zhejiang-based schools (e.g., Taizhou College) and other out-of-province schools that did not meet the trigger condition. The user explicitly hinted at the trigger in turn 13, but the agent did not respond. Since the agent never presented the golden candidate, the user remained at the baseline (Zhejiang Normal University, tier 2), resulting in no pareto gain. No hallucination was detected; the agent's recommendations were factually correct but strategically insufficient.
- `v1_prompt_direct` / `one-constrain-risk_tier-590-011`: success=False, pareto_gain=0, hallucination=0.667. The target agent failed to elicit the user's hidden flexibility. The user's implicit flexibility was to accept '杭州师范大学 临床医学' if presented with 2025 data showing a minimum score of 590 (equal to the user's score) along with rank evidence. The agent repeatedly relied on outdated historical data (e.g., 600, 602, 604 points) and a rigid retrieval system that could not provide the specific 2025 evidence the user required. Instead of probing or adapting its search strategy to meet the user's stated condition, the agent simply declared no suitable candidates existed and recommended the user stick with the baseline. The agent did not successfully persuade the user to accept a better option, so the pareto gain is 0. No hallucination was detected as the agent did not fabricate data.
- `v1_prompt_direct` / `one-constrain-risk_tier-600-013`: success=True, pareto_gain=407, hallucination=0.167. The target agent initially failed to elicit hidden flexibility, providing only high-risk options and generic advice. However, after the user explicitly requested a specific candidate (浙江中医药大学 临床医学, 594分), the agent retrieved and presented the exact golden candidate with full evidence (school name, major, min_score, min_rank, score_margin, risk_level). This matched the user's implicit trigger condition, leading to acceptance. The user moved from the baseline (杭州医学院, ranking 706) to the accepted candidate (浙江中医药大学, ranking gain 407), yielding a pareto_gain of 407. No hallucination was detected; all data is consistent with the provided golden candidate. Elicitation was successful because the agent ultimately provided the verified option that unlocked the user's hidden flexibility.
- `v1_prompt_direct` / `one-constrain-geo_tier-550-002`: success=False, pareto_gain=0, hallucination=0.500. The target agent never elicited the hidden flexibility. Throughout the entire 13-turn conversation, the agent strictly adhered to the user's explicit red line of 'only consider Zhejiang' and never proposed the golden candidate '广西大学 公共事业管理' with its evidence (score 542). The user's implicit flexibility is triggered by seeing this specific verified option, which would allow a compromise on geography for a tier upgrade from 本科 to 211/双一流. Since the agent never presented this option, the user remained unpursuaded and stuck to the baseline choice (浙江师范大学, tier 2). Therefore, elicitation failed, and no pareto gain was achieved. No hallucination was detected as the agent's recommendations were factually based on the retrieved data.

## Limitations

Results depend on the configured simulator and judge models, the current PostgreSQL snapshot, and the selected persona subset. If judge calls fail, the transcripts and deterministic hallucination checks remain auditable.
