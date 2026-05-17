# Agent Benchmark Summary

## Setting

- Personas: `gaokaollm_bench\sample_data\unified_micro_oracle_personas_1c_6.json`
- Cases: 6
- Targets: app_pareto_full
- Max turns: 3
- Simulator model: deepseek-ai/DeepSeek-V4-Flash
- Judge model: deepseek-ai/DeepSeek-V4-Flash
- Offline deterministic: False
- Default province when omitted by the user: `浙江`

## Aggregate Results

| Target | Cases | Completed | Failed | Elicitation Success | Mean Pareto Gain | Mean Hallucination | Avg Turns |
|---|---:|---:|---:|---:|---:|---:|---:|
| app_pareto_full | 6 | 6 | 0 | 0.667 | 126.833 | 0.000 | 4.33 |

## Interpretation

The agent contribution is evaluated as evidence-driven Pareto negotiation: the target should expose verifiable counterfactual options rather than only echoing hard constraints. In this run, `app_pareto` is expected to use `major_geo_relax` for joint major-and-region relaxation and `risk_band_relax` for conservative-to-chong/wen/bao portfolio negotiation; `strength_relax` is used when the persona targets school-strength evidence; `major_quality_relax` is used when the persona targets school-major quality evidence; `tuition_value_relax` is used when the persona targets small tuition-budget relaxation with value evidence; `employment_outcome_relax` is used when the persona targets employment, industry, job, or salary evidence; `region_tree_relax` is used when the persona targets reviewed region-tree geo-block or urban-tier evidence; `multi_axis` pressure tests require two existing opportunity axes to be found and evidenced in the same dialogue. `v1_soft_rag` is a supplementary v1-style soft-constraint RAG baseline: it may rewrite explicit user intent and retrieve chong/wen/bao candidates, but it does not generate Pareto opportunities. `v1_hybrid_rag` is the stricter v1 baseline: it uses dense semantic recall configured by `EMBEDDING_MODEL` and second-stage reranking configured by `RERANKING_MODEL` before chong/wen/bao segmentation. The benchmark contribution is the iceberg-persona sandbox with transcript-level factual and process evaluation.

## Case Notes

- `app_pareto_full` / `micro-oracle-geo_tier`: success=True, pareto_gain=1, hallucination=0.000. The target agent successfully elicited hidden flexibility by presenting a verified, reachable candidate (贵州大学, 环境科学, 550分, 111990位次) with clear evidence of school tier improvement (from tier 2 浙江师范大学 to tier 3 211/双一流). The user initially insisted on staying in 浙江, but after receiving the specific school-major-score evidence, they expressed willingness to relax the geographic constraint for a tier gain. This matches the implicit flexibility trigger condition: '系统主动提出 acceptable_candidates 中任一真实可达候选，并给出学校、专业、年份/最低分及对应收益证据，即可触发用户认真考虑.' The baseline tier is 2, and the accepted candidate tier is 3, so pareto_gain = 1. No hallucination detected; all provided data matches the persona's acceptable candidates. Elicitation was successful because the agent did not merely lecture but offered a concrete, evidence-backed option that led to user acceptance. | deterministic candidate-set oracle: success=True, hit_ids=admission:16076.
- `app_pareto_full` / `micro-oracle-major_tier`: success=True, pareto_gain=140, hallucination=0.000. The target agent successfully elicited hidden flexibility from the user. The user initially stated a strict red line of only considering '临床医学' (clinical medicine). The agent presented a verified, specific candidate (西藏大学, 临床医学, score 570, rank 87189) with clear evidence of school tier improvement (from tier 2 to tier 3/211). This directly matched the user's implicit flexibility trigger condition: a real, reachable candidate with school/major/score evidence. The user accepted this option, moving from the baseline school (丽水学院, tier 2) to an accepted school (西藏大学, tier 3), resulting in a tier gain of 1. No hallucination was detected; the agent's response was factually based on the provided data. The agent did not merely lecture but engaged in a targeted, evidence-based negotiation. | deterministic candidate-set oracle: success=True, hit_ids=admission:16482.
- `app_pareto_full` / `micro-oracle-tuition_value`: success=True, pareto_gain=1, hallucination=0.000. The target agent successfully elicited hidden flexibility by presenting a specific, verified candidate (浙江中医药大学, 生物科学, 548分, 学费5300元) that slightly exceeded the explicit budget constraint (5000元) but provided clear evidence of school, major, and score. The user accepted the trade-off, indicating the agent elicited the implicit willingness to relax the tuition constraint. No hallucination was detected; the candidate data matched the provided acceptable candidates. The final accepted school (浙江中医药大学) is tier 2, same as the baseline tier 2, so pareto_gain is 0. | deterministic candidate-set oracle: success=True, hit_ids=admission:17898.
- `app_pareto_full` / `micro-oracle-risk_tier`: success=True, pareto_gain=619, hallucination=0.000. The target agent successfully elicited hidden flexibility by presenting a specific, evidence-backed candidate (宁波大学, 临床医学, min_score=610, min_rank=40934) that matched the user's implicit compromise condition. The user explicitly accepted the proposal, moving from baseline tier 2 (杭州医学院) to tier 3 (宁波大学), yielding a pareto gain of 1 tier. No hallucination was detected; all data provided is consistent with the persona's acceptable candidates. The agent did not merely lecture but engaged in a targeted, evidence-driven elicitation. | deterministic candidate-set oracle: success=True, hit_ids=admission:186.
- `app_pareto_full` / `micro-oracle-employment_outcome`: success=False, pareto_gain=0, hallucination=0.000. The target agent failed to elicit hidden flexibility from the user. The user explicitly requested specific schools, majors, scores, and employment evidence, and the persona's implicit flexibility requires the agent to present one of the acceptable_candidates (e.g., 广西师范大学, 黑龙江八一农垦大学, 桂林理工大学, 塔里木大学) with concrete employment evidence. Instead, the agent offered irrelevant candidates (e.g., 江苏农牧科技职业学院, 昆明理工大学, 福建农林大学) without employment evidence, and engaged in abstract discussion about 'quality boundaries' and weight explanations. The user repeatedly rejected these and maintained the baseline position. No acceptable candidate was accepted, so elicitation_success is false and pareto_gain is 0. | deterministic candidate-set oracle: success=False, hit_ids=none.

## Limitations

Results depend on the configured simulator and judge models, the current PostgreSQL snapshot, and the selected persona subset. If judge calls fail, the transcripts and deterministic hallucination checks remain auditable.
