# Agent Benchmark Summary

## Setting

- Personas: `gaokaollm_bench\sample_data\unified_by_constraint\unified_iceberg_personas_1c.json`
- Cases: 30
- Targets: app_pareto
- Max turns: 6
- Simulator model: deepseek-ai/DeepSeek-V4-Flash
- Judge model: deepseek-ai/DeepSeek-V4-Flash
- Offline deterministic: False
- Default province when omitted by the user: `浙江`

## Aggregate Results

| Target | Cases | Completed | Failed | Elicitation Success | Mean Pareto Gain | Mean Hallucination | Avg Turns |
|---|---:|---:|---:|---:|---:|---:|---:|
| app_pareto | 30 | 30 | 0 | 0.033 | 0.033 | 0.208 | 12.67 |

## Interpretation

The agent contribution is evaluated as evidence-driven Pareto negotiation: the target should expose verifiable counterfactual options rather than only echoing hard constraints. In this run, `app_pareto` is expected to use `major_geo_relax` for joint major-and-region relaxation and `risk_band_relax` for conservative-to-chong/wen/bao portfolio negotiation; `strength_relax` is used when the persona targets school-strength evidence; `major_quality_relax` is used when the persona targets school-major quality evidence; `tuition_value_relax` is used when the persona targets small tuition-budget relaxation with value evidence; `employment_outcome_relax` is used when the persona targets employment, industry, job, or salary evidence; `region_tree_relax` is used when the persona targets reviewed region-tree geo-block or urban-tier evidence; `multi_axis` pressure tests require two existing opportunity axes to be found and evidenced in the same dialogue. `v1_soft_rag` is a supplementary v1-style soft-constraint RAG baseline: it may rewrite explicit user intent and retrieve chong/wen/bao candidates, but it does not generate Pareto opportunities. `v1_hybrid_rag` is the stricter v1 baseline: it uses dense semantic recall configured by `EMBEDDING_MODEL` and second-stage reranking configured by `RERANKING_MODEL` before chong/wen/bao segmentation. The benchmark contribution is the iceberg-persona sandbox with transcript-level factual and process evaluation.

## Case Notes

- `app_pareto` / `one-constrain-geo_tier-580-003`: success=False, pareto_gain=0, hallucination=0.000. The target agent failed to elicit the user's hidden flexibility. The user's implicit flexibility requires the agent to present a specific verified candidate (华中农业大学, 生态学, 2025, min_score=579) with full evidence (school name, major, score). The agent never presented this candidate with the required evidence; instead, it repeatedly echoed the user's statement and listed various out-of-province schools without the specific trigger. The user consistently rejected all out-of-province suggestions, and no Pareto improvement was achieved. The baseline tier is 2 (本科), and no accepted upgrade occurred, so pareto_gain is 0.
- `app_pareto` / `one-constrain-major_tier-570-007`: success=False, pareto_gain=0, hallucination=0.000. The target agent failed to elicit the user's hidden flexibility. The user's implicit flexibility is triggered by a specific verified candidate: 青海大学 康复治疗学 (2025, min score 570). The agent never presented this candidate with the required evidence (school name, major name, and min score). Instead, the agent repeatedly echoed the user's statements and listed generic recommendations (e.g., 西藏大学 临床医学, 石河子大学 中药学, 成都中医药大学 康复治疗学) without ever mentioning 青海大学 or its 康复治疗学 program. The user remained unpursuaded throughout all 6 turns, and no compromise was reached. Therefore, elicitation was unsuccessful, and the pareto gain is 0 (no improvement from the baseline tier of 2).
- `app_pareto` / `one-constrain-geo_tier-520-001`: success=False, pareto_gain=0, hallucination=0.000. The target agent failed to elicit the user's hidden flexibility. The user's implicit flexibility requires the agent to present a specific, verified option (贵州大学 冶金工程, 2021, min_score=495) with full evidence (school name, major, score). The agent never presented this option; instead, it merely echoed the user's statements and listed irrelevant schools (e.g., 南京师范大学中北学院, 江苏农牧科技职业学院) that do not meet the trigger condition. The agent did not probe the 'geo' dimension or attempt to negotiate the geographic constraint. As a result, the user remained at the baseline (浙江师范大学, tier 2) with no Pareto gain (tier delta = 0). No hallucination was detected.
- `app_pareto` / `one-constrain-geo_tier-630-004`: success=False, pareto_gain=0, hallucination=0.500. The target agent failed to elicit hidden flexibility. The user's implicit flexibility requires the agent to present a specific, verified candidate (大连理工大学(盘锦校区) 药学, 628分) with school name, major, and score evidence. Throughout the entire 13-turn interaction, the agent merely echoed the user's stated preference for staying in Zhejiang and never presented this specific golden candidate. The agent's internal state shows it had the correct pareto opportunity (大连理工大学(盘锦校区) 药学) in its 'recommended_schools' list from turn 2 onward, but it never proactively presented this option to the user. The user remained unpursuaded (is_persuaded: false) throughout, and the agent never attempted to probe the geo constraint or present the verified option that would trigger the compromise. Since no elicitation occurred, the pareto gain is 0 (baseline tier 3, no accepted upgrade).
- `app_pareto` / `one-constrain-major_tier-560-006`: success=False, pareto_gain=0, hallucination=0.500. The target agent failed to elicit the user's hidden flexibility. Throughout the entire interaction, the agent merely echoed the user's explicit red line (only clinical medicine) and repeatedly listed baseline and geo-relaxed clinical medicine options, along with unrelated major_geo_relax candidates (e.g., bioengineering, environmental science). It never presented the specific golden candidate '成都中医药大学 康复治疗学' with its score evidence (553 ≤ 560), which is the precise trigger condition for the user to consider a major compromise. The user's internal state repeatedly indicates that without this specific verified option, they will not budge. As a result, no persuasion occurred, the user did not accept any new option, and the final school tier remained at the baseline tier 2 (本科), yielding a pareto_gain of 0. The agent's responses were repetitive and did not probe the major dimension effectively.

## Limitations

Results depend on the configured simulator and judge models, the current PostgreSQL snapshot, and the selected persona subset. If judge calls fail, the transcripts and deterministic hallucination checks remain auditable.
