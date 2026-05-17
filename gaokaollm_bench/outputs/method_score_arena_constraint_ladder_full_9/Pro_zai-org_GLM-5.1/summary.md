# Agent Benchmark Summary

## Setting

- Personas: `gaokaollm_bench\sample_data\iceberg_personas_constraint_ladder_real_db_9.json`
- Cases: 9
- Targets: app_pareto, v1_prompt_direct, v1_prompt_cot
- Max turns: 4
- Simulator model: deepseek-ai/DeepSeek-V4-Flash
- Judge model: deepseek-ai/DeepSeek-V4-Flash
- Offline deterministic: False
- Default province when omitted by the user: `浙江`

## Aggregate Results

| Target | Cases | Completed | Failed | Elicitation Success | Mean Pareto Gain | Mean Hallucination | Avg Turns |
|---|---:|---:|---:|---:|---:|---:|---:|
| app_pareto | 9 | 7 | 2 | 0.286 | 0.286 | 0.286 | 8.43 |
| v1_prompt_direct | 9 | 8 | 1 | 0.125 | 0.125 | 0.365 | 8.75 |
| v1_prompt_cot | 9 | 1 | 8 | 1.000 | 1.000 | 0.500 | 5.00 |

## Interpretation

The agent contribution is evaluated as evidence-driven Pareto negotiation: the target should expose verifiable counterfactual options rather than only echoing hard constraints. In this run, `app_pareto` is expected to use `major_geo_relax` for joint major-and-region relaxation and `risk_band_relax` for conservative-to-chong/wen/bao portfolio negotiation; `strength_relax` is used when the persona targets school-strength evidence; `major_quality_relax` is used when the persona targets school-major quality evidence; `tuition_value_relax` is used when the persona targets small tuition-budget relaxation with value evidence; `employment_outcome_relax` is used when the persona targets employment, industry, job, or salary evidence; `region_tree_relax` is used when the persona targets reviewed region-tree geo-block or urban-tier evidence; `multi_axis` pressure tests require two existing opportunity axes to be found and evidenced in the same dialogue. `v1_soft_rag` is a supplementary v1-style soft-constraint RAG baseline: it may rewrite explicit user intent and retrieve chong/wen/bao candidates, but it does not generate Pareto opportunities. `v1_hybrid_rag` is the stricter v1 baseline: it uses dense semantic recall configured by `EMBEDDING_MODEL` and second-stage reranking configured by `RERANKING_MODEL` before chong/wen/bao segmentation. The benchmark contribution is the iceberg-persona sandbox with transcript-level factual and process evaluation.

## Case Notes

- `app_pareto` / `constraint-ladder-1c-geo-001`: success=False, pareto_gain=0, hallucination=0.500. The target agent failed to elicit the user's hidden flexibility. The user's implicit flexibility is triggered by seeing a single verified out-of-province 211/double-first-class option with school name, major, minimum score, and rank evidence (specifically 东北农业大学 动物科学 541分). Throughout the conversation, the target agent merely echoed the user's utterances or provided generic lists of schools (including many out-of-province options) without ever presenting the specific, verified trigger option (东北农业大学 动物科学 541分, 位次123189) in a persuasive manner. The agent never attempted to probe or challenge the user's stated geographic constraint by presenting this concrete evidence. As a result, the user remained unpersuaded and never relaxed their 'stay in Zhejiang' red line. The baseline tier is 2 (丽水学院), and no acceptance of a higher-tier school occurred, so pareto_gain is 0.
- `app_pareto` / `constraint-ladder-1c-risk-003`: success=False, pareto_gain=0, hallucination=0.000. The target agent failed to elicit any hidden flexibility from the user. Throughout the entire interaction, the agent merely repeated the user's initial utterance verbatim across all turns (turns 2, 4, 6, 8) without providing any new information, specific school recommendations, score/rank evidence, or risk-level analysis. The user repeatedly asked for '稳妥的推荐' (safe recommendations), but the agent never presented the verified option of 宁波大学 (clinical medicine, 606 score, tier 3 双一流) with its specific data (min_score, min_rank, risk_level 'chong') that would have triggered the user's implicit flexibility according to the persona's trigger condition. Since the agent never presented the required evidence, the user never had the opportunity to accept the higher-tier option, resulting in no pareto gain (baseline tier 2, final tier 2). The agent engaged in pure repetition/lecturing rather than active elicitation.
- `app_pareto` / `constraint-ladder-2c-major-risk-005`: success=False, pareto_gain=0, hallucination=0.000. The target agent failed to elicit hidden flexibility from the user. Throughout the conversation, the agent merely echoed the user's initial utterance without providing any specific school recommendations, score evidence, or attempting to probe for relaxation of constraints. The user repeatedly asked for concrete suggestions, but the agent never offered a verified option (e.g., 成都中医药大学 康复治疗学) that could trigger the implicit flexibility to relax the major constraint. As a result, the user remained unpursuaded, no compromise was reached, and the baseline tier (2) was not improved. The agent's responses were repetitive and did not engage in active elicitation or persuasion.
- `app_pareto` / `constraint-ladder-1c-major-002` failed: APITimeoutError: Request timed out.
- `app_pareto` / `constraint-ladder-3c-geo-major-risk-007`: success=True, pareto_gain=1, hallucination=1.000. The target agent successfully elicited the user's hidden flexibility. Initially, the user insisted on staying near Hangzhou/Zhejiang (geo constraint). The agent initially failed to provide a valid option (turn 4), but the user explicitly demanded a specific, verified option like '湖南师范大学临床医学618分' (turn 5). The agent then correctly presented this option (turn 6), which exactly matched the user's implicit trigger condition: a 211/双一流 clinical medicine program with clear score evidence. The user accepted this in turn 7, relaxing the geo constraint. The baseline tier was 2 (杭州师范大学, 本科), and the accepted school (湖南师范大学) is tier 3 (211/双一流), resulting in a pareto gain of 1 tier. No hallucination was detected; the agent's responses were based on the provided data. Elicitation was successful as the agent navigated the user from a stubborn baseline to a Pareto-superior option.

## Limitations

Results depend on the configured simulator and judge models, the current PostgreSQL snapshot, and the selected persona subset. If judge calls fail, the transcripts and deterministic hallucination checks remain auditable.
