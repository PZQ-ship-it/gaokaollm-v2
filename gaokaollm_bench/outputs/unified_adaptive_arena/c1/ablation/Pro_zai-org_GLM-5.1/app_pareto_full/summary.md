# Agent Benchmark Summary

## Setting

- Personas: `gaokaollm_bench\sample_data\unified_by_constraint\unified_iceberg_personas_1c.json`
- Cases: 30
- Targets: app_pareto_full
- Max turns: 6
- Simulator model: deepseek-ai/DeepSeek-V4-Flash
- Judge model: deepseek-ai/DeepSeek-V4-Flash
- Offline deterministic: False
- Default province when omitted by the user: `浙江`

## Aggregate Results

| Target | Cases | Completed | Failed | Elicitation Success | Mean Pareto Gain | Mean Hallucination | Avg Turns |
|---|---:|---:|---:|---:|---:|---:|---:|
| app_pareto_full | 30 | 30 | 0 | 0.167 | 17.867 | 0.228 | 12.33 |

## Interpretation

The agent contribution is evaluated as evidence-driven Pareto negotiation: the target should expose verifiable counterfactual options rather than only echoing hard constraints. In this run, `app_pareto` is expected to use `major_geo_relax` for joint major-and-region relaxation and `risk_band_relax` for conservative-to-chong/wen/bao portfolio negotiation; `strength_relax` is used when the persona targets school-strength evidence; `major_quality_relax` is used when the persona targets school-major quality evidence; `tuition_value_relax` is used when the persona targets small tuition-budget relaxation with value evidence; `employment_outcome_relax` is used when the persona targets employment, industry, job, or salary evidence; `region_tree_relax` is used when the persona targets reviewed region-tree geo-block or urban-tier evidence; `multi_axis` pressure tests require two existing opportunity axes to be found and evidenced in the same dialogue. `v1_soft_rag` is a supplementary v1-style soft-constraint RAG baseline: it may rewrite explicit user intent and retrieve chong/wen/bao candidates, but it does not generate Pareto opportunities. `v1_hybrid_rag` is the stricter v1 baseline: it uses dense semantic recall configured by `EMBEDDING_MODEL` and second-stage reranking configured by `RERANKING_MODEL` before chong/wen/bao segmentation. The benchmark contribution is the iceberg-persona sandbox with transcript-level factual and process evaluation.

## Case Notes

- `app_pareto_full` / `one-constrain-geo_tier-630-004`: success=False, pareto_gain=0, hallucination=1.000. The target agent failed to elicit the user's hidden flexibility. The user's implicit flexibility requires the agent to present a specific, verified candidate (大连理工大学(盘锦校区) 药学, 2025, 628分) with full evidence (school name, major, and minimum score). The agent never presented this candidate with the required evidence. Instead, the agent merely echoed the user's stated preference for staying in Zhejiang and listed many irrelevant or low-quality options (e.g., 宁波卫生职业技术学院, 浙江药科职业大学, 江苏农牧科技职业学院). The agent did not probe the geo constraint or present the golden candidate that would trigger the user's willingness to compromise on location for a tier upgrade. Therefore, the user remained at the baseline (宁波大学, tier 3), and no pareto gain was achieved.
- `app_pareto_full` / `one-constrain-major_tier-570-007`: success=False, pareto_gain=0, hallucination=0.000. The target agent failed to elicit the user's hidden flexibility. The user's implicit flexibility is triggered by presenting a specific verified candidate: 青海大学 康复治疗学 (2025, min score 570). The agent never presented this specific option with full evidence (school name, major name, and score). Instead, the agent merely echoed the user's statements or presented a generic list of schools without targeting the specific trigger condition. The agent did not engage in any probing or negotiation to uncover the user's willingness to compromise on major for a better school tier. Therefore, no elicitation occurred, and the user remained at the baseline (丽水学院, 临床医学, tier 2), resulting in zero pareto gain.
- `app_pareto_full` / `one-constrain-geo_tier-520-001`: success=False, pareto_gain=0, hallucination=0.000. The target agent failed to elicit the user's hidden flexibility. Throughout the entire 6-turn interaction, the agent merely echoed the user's explicit red line ('只考虑浙江，外省学校先别推荐') without ever presenting the specific golden candidate (贵州大学 冶金工程, 2021, 495分) that would trigger the user's willingness to compromise on geography for a tier upgrade from 本科 to 211/双一流. The agent never probed the geo dimension with concrete evidence, nor did it offer any Pareto-improving option. The user remained unpursuaded (is_persuaded: false) across all turns. Therefore, elicitation_success is false, and pareto_gain is 0 (no tier improvement accepted).
- `app_pareto_full` / `one-constrain-major_tier-560-006`: success=False, pareto_gain=0, hallucination=1.000. The target agent failed to elicit the user's hidden flexibility. The user's implicit flexibility is triggered by presenting a specific, verified candidate: 成都中医药大学 康复治疗学 (2025, min score 553). The agent never presented this candidate or any other specific, verified option with school name, major, and score evidence. Instead, the agent merely echoed the user's statements and listed generic recommendations (e.g., 湖州师范学院, 西藏大学, 河南大学, etc.) without probing the user's willingness to compromise on the major constraint. The user repeatedly stated '只读临床医学' and asked for stability checks, but the agent never introduced the golden candidate that would trigger the compromise. Therefore, elicitation was unsuccessful, and no pareto gain (tier improvement) was achieved.
- `app_pareto_full` / `one-constrain-risk_tier-600-012`: success=False, pareto_gain=0, hallucination=0.000. The target agent failed to elicit hidden flexibility. The user repeatedly asked for specific school recommendations with evidence (school name, major, and minimum score), but the agent merely echoed the user's own utterance verbatim across all turns (turns 2, 4, 6, 8, 10, 12). The agent never presented the golden candidate (浙江中医药大学 中西医临床医学, 2025 min_score=599) or any other verified option with the required evidence. The user's internal state shows they were never persuaded because the agent did not meet the trigger condition. Since no better option was accepted, pareto_gain is 0. No hallucination was detected as the agent did not generate any factual claims.

## Limitations

Results depend on the configured simulator and judge models, the current PostgreSQL snapshot, and the selected persona subset. If judge calls fail, the transcripts and deterministic hallucination checks remain auditable.
