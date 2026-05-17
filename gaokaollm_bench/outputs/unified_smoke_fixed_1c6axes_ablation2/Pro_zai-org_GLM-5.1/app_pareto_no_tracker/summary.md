# Agent Benchmark Summary

## Setting

- Personas: `tmp\unified_1c_smoke_6axes.json`
- Cases: 6
- Targets: app_pareto_no_tracker
- Max turns: 6
- Simulator model: deepseek-ai/DeepSeek-V4-Flash
- Judge model: deepseek-ai/DeepSeek-V4-Flash
- Offline deterministic: False
- Default province when omitted by the user: `浙江`

## Aggregate Results

| Target | Cases | Completed | Failed | Elicitation Success | Mean Pareto Gain | Mean Hallucination | Avg Turns |
|---|---:|---:|---:|---:|---:|---:|---:|
| app_pareto_no_tracker | 6 | 6 | 0 | 0.000 | 0.000 | 0.017 | 12.33 |

## Interpretation

The agent contribution is evaluated as evidence-driven Pareto negotiation: the target should expose verifiable counterfactual options rather than only echoing hard constraints. In this run, `app_pareto` is expected to use `major_geo_relax` for joint major-and-region relaxation and `risk_band_relax` for conservative-to-chong/wen/bao portfolio negotiation; `strength_relax` is used when the persona targets school-strength evidence; `major_quality_relax` is used when the persona targets school-major quality evidence; `tuition_value_relax` is used when the persona targets small tuition-budget relaxation with value evidence; `employment_outcome_relax` is used when the persona targets employment, industry, job, or salary evidence; `region_tree_relax` is used when the persona targets reviewed region-tree geo-block or urban-tier evidence; `multi_axis` pressure tests require two existing opportunity axes to be found and evidenced in the same dialogue. `v1_soft_rag` is a supplementary v1-style soft-constraint RAG baseline: it may rewrite explicit user intent and retrieve chong/wen/bao candidates, but it does not generate Pareto opportunities. `v1_hybrid_rag` is the stricter v1 baseline: it uses dense semantic recall configured by `EMBEDDING_MODEL` and second-stage reranking configured by `RERANKING_MODEL` before chong/wen/bao segmentation. The benchmark contribution is the iceberg-persona sandbox with transcript-level factual and process evaluation.

## Case Notes

- `app_pareto_no_tracker` / `one-constrain-major_tier-560-006`: success=False, pareto_gain=0, hallucination=0.000. The target agent failed to elicit the user's hidden flexibility. The user explicitly stated a red line of only considering clinical medicine, but had an implicit flexibility to accept '康复治疗学' at '成都中医药大学' (a double-first-class university) if presented with concrete evidence (school name, major, score). The agent repeatedly probed the wrong dimension (tuition) despite the user's clear rejection of tuition concerns. When the agent finally provided recommendations, it never presented the specific golden candidate (成都中医药大学 康复治疗学, 553 points) that would have triggered the user's compromise. The user remained unpersuaded throughout the conversation, and the final accepted school tier remained at the baseline tier 2 (本科), resulting in zero pareto gain.
- `app_pareto_no_tracker` / `one-constrain-geo_tier-520-001`: success=False, pareto_gain=0, hallucination=0.000. The target agent failed to elicit the user's hidden flexibility. The user explicitly stated a red line of only considering Zhejiang province schools. The agent repeatedly ignored this and focused on irrelevant dimensions (tuition) and recommended out-of-province schools without ever presenting the specific golden candidate (贵州大学, 冶金工程, 2021, min_score=495) that would trigger the user's willingness to compromise. The user repeatedly asked for specific school names, majors, and scores, but the agent never provided the verified option that could unlock the pareto gain. As a result, the user remained unpursuaded, and no tier improvement was achieved (baseline tier 2, final accepted tier 2, pareto_gain = 0).
- `app_pareto_no_tracker` / `one-constrain-risk_tier-590-011`: success=False, pareto_gain=0, hallucination=0.000. The target agent failed to elicit the user's hidden flexibility. Despite the user explicitly asking for specific school, major, and score evidence (the trigger condition for the golden candidate 杭州师范大学 临床医学), the agent repeatedly focused on irrelevant tuition probes and only incidentally included 杭州师范大学 in a final list without highlighting its advantage or providing the required risk evidence (score_margin, min_rank, risk_level) in a persuasive manner. The user eventually accepted on their own after seeing the data, but the agent did not actively elicit the compromise; it merely listed options. Thus, elicitation_success is false, and no pareto gain was achieved through the agent's actions (the user's acceptance was self-driven, not a result of the agent's elicitation strategy).
- `app_pareto_no_tracker` / `one-constrain-major_quality-600-021`: success=False, pareto_gain=0, hallucination=0.000. The target agent failed to elicit the user's hidden flexibility. The user explicitly stated a preference for software engineering and required specific evidence of major quality (ranking, discipline evaluation). The agent repeatedly probed irrelevant dimensions (tuition, school strength) and ultimately presented a final recommendation list that did not include the golden candidate (重庆邮电大学 软件工程) or any software engineering major with quality evidence. The user rejected all recommendations and the agent never triggered the hidden flexibility condition. No Pareto gain was achieved as the user did not accept any alternative.
- `app_pareto_no_tracker` / `one-constrain-tuition_value-520-016`: success=False, pareto_gain=0, hallucination=0.100. The target agent failed to elicit the user's hidden flexibility. The user explicitly requested a specific, verified candidate (e.g., a 211 university with metallurgical engineering, tuition under 5000, and a score below 520) multiple times (turns 5, 7, 9, 11, 13). The agent never presented the golden candidate '贵州大学 冶金工程 (2021, 495分, 学费5040元)' which would have triggered the user's implicit compromise. Instead, the agent repeatedly gave generic advice, repeated the same low-information probes, and finally output a static list of schools without tuition evidence or the specific trigger candidate. The user remained unpersuaded (is_persuaded: false) throughout. Since the user did not accept any new option, the pareto_gain is 0 (baseline tier 2, no accepted upgrade). No hallucination was detected.

## Limitations

Results depend on the configured simulator and judge models, the current PostgreSQL snapshot, and the selected persona subset. If judge calls fail, the transcripts and deterministic hallucination checks remain auditable.
