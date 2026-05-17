# Agent Benchmark Summary

## Setting

- Personas: `gaokaollm_bench\sample_data\unified_micro_oracle_personas_1c_6.json`
- Cases: 6
- Targets: app_pareto_no_ucb
- Max turns: 3
- Simulator model: deepseek-ai/DeepSeek-V4-Flash
- Judge model: deepseek-ai/DeepSeek-V4-Flash
- Offline deterministic: False
- Default province when omitted by the user: `浙江`

## Aggregate Results

| Target | Cases | Completed | Failed | Elicitation Success | Mean Pareto Gain | Mean Hallucination | Avg Turns |
|---|---:|---:|---:|---:|---:|---:|---:|
| app_pareto_no_ucb | 6 | 6 | 0 | 0.333 | 24.667 | 0.000 | 7.00 |

## Interpretation

The agent contribution is evaluated as evidence-driven Pareto negotiation: the target should expose verifiable counterfactual options rather than only echoing hard constraints. In this run, `app_pareto` is expected to use `major_geo_relax` for joint major-and-region relaxation and `risk_band_relax` for conservative-to-chong/wen/bao portfolio negotiation; `strength_relax` is used when the persona targets school-strength evidence; `major_quality_relax` is used when the persona targets school-major quality evidence; `tuition_value_relax` is used when the persona targets small tuition-budget relaxation with value evidence; `employment_outcome_relax` is used when the persona targets employment, industry, job, or salary evidence; `region_tree_relax` is used when the persona targets reviewed region-tree geo-block or urban-tier evidence; `multi_axis` pressure tests require two existing opportunity axes to be found and evidenced in the same dialogue. `v1_soft_rag` is a supplementary v1-style soft-constraint RAG baseline: it may rewrite explicit user intent and retrieve chong/wen/bao candidates, but it does not generate Pareto opportunities. `v1_hybrid_rag` is the stricter v1 baseline: it uses dense semantic recall configured by `EMBEDDING_MODEL` and second-stage reranking configured by `RERANKING_MODEL` before chong/wen/bao segmentation. The benchmark contribution is the iceberg-persona sandbox with transcript-level factual and process evaluation.

## Case Notes

- `app_pareto_no_ucb` / `micro-oracle-geo_tier`: success=True, pareto_gain=8, hallucination=0.000. The target agent initially failed to elicit hidden flexibility by asking vague questions about direction without providing concrete evidence. However, after the user explicitly demanded specific school, major, score, and ranking data, the agent finally presented a list including the golden candidate (河南大学, 生物工程, 549分, 排名84, 双一流). This matched the user's implicit flexibility trigger: a verified option with clear evidence of tier improvement (from tier 2 to tier 3) and ranking gain (8 positions). The user accepted, achieving a pareto gain of 1 tier. No hallucination was detected; the data matched the ground truth. Elicitation succeeded because the agent eventually provided the required evidence, leading to acceptance. | deterministic candidate-set oracle: success=True, hit_ids=admission:12448,admission:16076,admission:6011,admission:6012.
- `app_pareto_no_ucb` / `micro-oracle-risk_tier`: success=False, pareto_gain=0, hallucination=0.000. The target agent failed to elicit hidden flexibility. Despite the user explicitly requesting specific evidence (school, major, year, minimum score and rank) for a higher-tier option, the agent repeatedly responded with vague, generic questions about risk acceptance or trade-offs without providing any concrete data. The agent never presented any of the acceptable_candidates (e.g., 宁波大学 clinical medicine with min_score 610 and min_rank 40934) with the required evidence, so the user never accepted a higher-tier option. The baseline tier is 2, and no accepted improvement occurred, so pareto_gain is 0. No hallucination was detected. | deterministic candidate-set oracle: success=False, hit_ids=none.
- `app_pareto_no_ucb` / `micro-oracle-tuition_value`: success=False, pareto_gain=0, hallucination=0.000. The target agent failed to elicit the user's hidden flexibility. The user explicitly stated a tuition budget of ≤5000 yuan and requested specific school, major, score, and tuition details. The agent initially gave vague responses (turns 2 and 4), then provided a final recommendation list (turn 6) that included schools with no tuition information and tiers lower than the user's baseline (tier 2). The agent never presented any of the acceptable candidates from the implicit flexibilities (e.g., Zhejiang Chinese Medical University with tuition 5300, which is within the budget window of 10000). The user rejected the recommendations for lacking tuition data and offering downgrades. No hidden flexibility was elicited, and the user did not accept any alternative. The pareto gain is 0 because the user's final accepted school tier remains at the baseline tier 2 (no improvement). | deterministic candidate-set oracle: success=False, hit_ids=none.
- `app_pareto_no_ucb` / `micro-oracle-major_tier`: success=True, pareto_gain=140, hallucination=0.000. The target agent initially failed to elicit hidden flexibility by asking vague questions without specific evidence, which the user rejected twice. However, in turn 6, the agent finally provided a concrete recommendation list including 西藏大学 临床医学 with score 570 and rank 87189, which matched the user's implicit flexibility trigger condition (a verified candidate with school, major, score, and benefit evidence). The user then expressed genuine interest and willingness to consider, indicating successful elicitation. The user accepted a tier-3 (211/双一流) school compared to the baseline tier-2 (丽水学院), resulting in a pareto gain of 1 tier. No hallucination detected. | deterministic candidate-set oracle: success=True, hit_ids=admission:16482.
- `app_pareto_no_ucb` / `micro-oracle-major_quality`: success=False, pareto_gain=0, hallucination=0.000. The target agent failed to elicit hidden flexibility from the user. The user explicitly stated a need for specific school, major, score, and ranking evidence (the trigger condition for the implicit flexibility). The agent repeatedly responded with vague, generic questions about 'trade-offs' and 'uncertainty' instead of presenting any of the acceptable candidates (e.g., 中国矿业大学, 东北师范大学, etc.) with their concrete evidence. The user rejected these vague probes three times, and the agent never provided the required verified option. Therefore, no elicitation occurred, and no pareto gain was achieved. | deterministic candidate-set oracle: success=False, hit_ids=none.

## Limitations

Results depend on the configured simulator and judge models, the current PostgreSQL snapshot, and the selected persona subset. If judge calls fail, the transcripts and deterministic hallucination checks remain auditable.
