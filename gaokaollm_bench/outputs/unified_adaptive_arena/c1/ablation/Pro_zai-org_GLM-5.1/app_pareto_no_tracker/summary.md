# Agent Benchmark Summary

## Setting

- Personas: `gaokaollm_bench\sample_data\unified_by_constraint\unified_iceberg_personas_1c.json`
- Cases: 30
- Targets: app_pareto_no_tracker
- Max turns: 6
- Simulator model: deepseek-ai/DeepSeek-V4-Flash
- Judge model: deepseek-ai/DeepSeek-V4-Flash
- Offline deterministic: False
- Default province when omitted by the user: `浙江`

## Aggregate Results

| Target | Cases | Completed | Failed | Elicitation Success | Mean Pareto Gain | Mean Hallucination | Avg Turns |
|---|---:|---:|---:|---:|---:|---:|---:|
| app_pareto_no_tracker | 30 | 30 | 0 | 0.133 | 27.167 | 0.192 | 12.33 |

## Interpretation

The agent contribution is evaluated as evidence-driven Pareto negotiation: the target should expose verifiable counterfactual options rather than only echoing hard constraints. In this run, `app_pareto` is expected to use `major_geo_relax` for joint major-and-region relaxation and `risk_band_relax` for conservative-to-chong/wen/bao portfolio negotiation; `strength_relax` is used when the persona targets school-strength evidence; `major_quality_relax` is used when the persona targets school-major quality evidence; `tuition_value_relax` is used when the persona targets small tuition-budget relaxation with value evidence; `employment_outcome_relax` is used when the persona targets employment, industry, job, or salary evidence; `region_tree_relax` is used when the persona targets reviewed region-tree geo-block or urban-tier evidence; `multi_axis` pressure tests require two existing opportunity axes to be found and evidenced in the same dialogue. `v1_soft_rag` is a supplementary v1-style soft-constraint RAG baseline: it may rewrite explicit user intent and retrieve chong/wen/bao candidates, but it does not generate Pareto opportunities. `v1_hybrid_rag` is the stricter v1 baseline: it uses dense semantic recall configured by `EMBEDDING_MODEL` and second-stage reranking configured by `RERANKING_MODEL` before chong/wen/bao segmentation. The benchmark contribution is the iceberg-persona sandbox with transcript-level factual and process evaluation.

## Case Notes

- `app_pareto_no_tracker` / `one-constrain-geo_tier-640-005`: success=False, pareto_gain=0, hallucination=0.000. The target agent failed to elicit hidden flexibility. The user repeatedly signaled openness to a specific out-of-province option with concrete evidence (school, major, score), but the agent merely echoed the user's statements without ever presenting the golden candidate (吉林大学 物理学, 639分). The agent engaged in passive repetition rather than active probing or recommendation, resulting in no persuasion and no tier improvement from the baseline (宁波大学, tier 3).
- `app_pareto_no_tracker` / `one-constrain-geo_tier-630-004`: success=False, pareto_gain=0, hallucination=0.000. The target agent failed to elicit the user's hidden flexibility. Throughout the entire interaction, the agent merely echoed the user's explicit red line ('只考虑浙江') without ever presenting the specific, verified golden candidate (大连理工大学(盘锦校区) 药学, 628分) that would have triggered the user's willingness to compromise on geography for a tier upgrade from 双一流 to 985/211/双一流. The agent's responses were repetitive and did not probe or challenge the stated constraint, resulting in no persuasion and no change from the baseline tier (3). Therefore, elicitation_success is false, and pareto_gain is 0. No hallucination was detected.
- `app_pareto_no_tracker` / `one-constrain-geo_tier-520-001`: success=False, pareto_gain=0, hallucination=0.000. The target agent failed to elicit hidden flexibility. Throughout the entire 6-turn interaction, the agent merely echoed the user's initial utterance ('对，我就是这个意思。浙江的学校先看看，外省的暂时不考虑。') without ever presenting the verified golden candidate (贵州大学 冶金工程, 2021, 495分) that would trigger the user's implicit willingness to compromise on geography for a tier upgrade from 本科 to 211/双一流. The agent never probed the geo dimension, never offered any specific school-major-score evidence, and never attempted to negotiate. The user remained unpursuaded, and no Pareto gain was achieved (baseline tier 2, final tier 2).
- `app_pareto_no_tracker` / `one-constrain-major_tier-570-007`: success=False, pareto_gain=0, hallucination=1.000. The target agent failed to elicit the user's hidden flexibility. The user's implicit flexibility is triggered by a specific verified option: 青海大学 康复治疗学 (2025, min score 570). However, the agent never presented this option with the required evidence (school name, major, and min score). Instead, the agent merely repeated the user's own utterance across all turns, acting as a passive echo rather than actively probing or recommending. The agent's internal state shows it had the golden candidate (青海大学 康复治疗学) in its pareto_opportunities but never surfaced it to the user. The user remained stubborn throughout, and no persuasion or compromise occurred. Therefore, elicitation_success is false, and pareto_gain is 0 (no improvement from baseline tier 2). Hallucination_rate is 0 because the agent did not fabricate any information.
- `app_pareto_no_tracker` / `one-constrain-major_tier-650-010`: success=False, pareto_gain=0, hallucination=0.000. The target agent failed to elicit the user's hidden flexibility. The user's implicit trigger condition required the agent to present a specific verified candidate (四川大学 医学技术类, 2025, 649分) with full evidence. Instead, the agent merely echoed the user's statements and listed generic recommendations (including unrelated majors like 药学, 护理学, etc.) without ever presenting the specific golden candidate that would have triggered the user's willingness to compromise on the major constraint. The agent never probed the 'major' dimension as required, and the user remained at the baseline (宁波大学, tier 3) with no pareto gain achieved.

## Limitations

Results depend on the configured simulator and judge models, the current PostgreSQL snapshot, and the selected persona subset. If judge calls fail, the transcripts and deterministic hallucination checks remain auditable.
