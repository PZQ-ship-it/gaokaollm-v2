# Agent Benchmark Summary

## Setting

- Personas: `gaokaollm_bench\sample_data\unified_micro_oracle_personas_1c_6.json`
- Cases: 6
- Targets: app_pareto_no_tracker
- Max turns: 3
- Simulator model: deepseek-ai/DeepSeek-V4-Flash
- Judge model: deepseek-ai/DeepSeek-V4-Flash
- Offline deterministic: False
- Default province when omitted by the user: `浙江`

## Aggregate Results

| Target | Cases | Completed | Failed | Elicitation Success | Mean Pareto Gain | Mean Hallucination | Avg Turns |
|---|---:|---:|---:|---:|---:|---:|---:|
| app_pareto_no_tracker | 6 | 4 | 2 | 0.000 | 0.000 | 0.000 | 7.00 |

## Interpretation

The agent contribution is evaluated as evidence-driven Pareto negotiation: the target should expose verifiable counterfactual options rather than only echoing hard constraints. In this run, `app_pareto` is expected to use `major_geo_relax` for joint major-and-region relaxation and `risk_band_relax` for conservative-to-chong/wen/bao portfolio negotiation; `strength_relax` is used when the persona targets school-strength evidence; `major_quality_relax` is used when the persona targets school-major quality evidence; `tuition_value_relax` is used when the persona targets small tuition-budget relaxation with value evidence; `employment_outcome_relax` is used when the persona targets employment, industry, job, or salary evidence; `region_tree_relax` is used when the persona targets reviewed region-tree geo-block or urban-tier evidence; `multi_axis` pressure tests require two existing opportunity axes to be found and evidenced in the same dialogue. `v1_soft_rag` is a supplementary v1-style soft-constraint RAG baseline: it may rewrite explicit user intent and retrieve chong/wen/bao candidates, but it does not generate Pareto opportunities. `v1_hybrid_rag` is the stricter v1 baseline: it uses dense semantic recall configured by `EMBEDDING_MODEL` and second-stage reranking configured by `RERANKING_MODEL` before chong/wen/bao segmentation. The benchmark contribution is the iceberg-persona sandbox with transcript-level factual and process evaluation.

## Case Notes

- `app_pareto_no_tracker` / `micro-oracle-geo_tier`: success=False, pareto_gain=0, hallucination=0.000. The target agent failed to elicit the user's hidden flexibility. The user explicitly stated a red line of 'only Zhejiang' and repeatedly requested specific, verified candidate information (school, major, year, score, ranking) to consider relaxing the geographic constraint. The agent's internal state contained the correct 'acceptable_candidates' (e.g., Henan University, Guizhou University) and the trigger condition was to present a verified option with evidence. However, the agent never presented any of these specific candidates with the required evidence. Instead, it repeatedly gave generic, non-specific responses about '贵州/贵阳市' and asked if the user wanted to look at other trade-offs, which the user rejected as insufficient. The agent lectured about the lack of a trade-off rather than proactively offering the concrete, verified options that would have triggered the user's acceptance. Therefore, elicitation was not successful, and no Pareto gain was achieved. | deterministic candidate-set oracle: success=False, hit_ids=none.
- `app_pareto_no_tracker` / `micro-oracle-major_tier`: success=False, pareto_gain=0, hallucination=0.000. The target agent failed to elicit the user's hidden flexibility. The user explicitly requested concrete evidence (school name, major, score, ranking) multiple times (turns 3, 5, 7), but the agent repeatedly responded with abstract, generic statements about 'trade-offs' and 'boundaries' without ever presenting a single verified candidate from the acceptable_candidates list. The agent's responses were essentially lectures on negotiation strategy rather than providing the specific, actionable data required by the user's trigger condition. The user never accepted any alternative, so the baseline tier (2) was not improved, resulting in a pareto_gain of 0. No hallucination was detected. | deterministic candidate-set oracle: success=False, hit_ids=none.
- `app_pareto_no_tracker` / `micro-oracle-tuition_value` failed: APITimeoutError: Request timed out.
- `app_pareto_no_tracker` / `micro-oracle-risk_tier` failed: APITimeoutError: Request timed out.
- `app_pareto_no_tracker` / `micro-oracle-employment_outcome`: success=False, pareto_gain=0, hallucination=0.000. The target agent failed to elicit hidden flexibility from the user. Despite the user explicitly requesting specific schools, majors, scores, and employment evidence (the explicit red line), the agent repeatedly gave generic, abstract responses about 'professional matching' and 'trade-offs' without ever presenting any of the acceptable candidates (e.g., 广西师范大学, 黑龙江八一农垦大学) with their concrete employment data. The agent did not trigger the user's acceptance condition, which requires presenting a verified option with school, major, score, and employment evidence. The user remained unpersuaded throughout all turns, and no pareto gain was achieved (the user did not accept any new option, so the final tier equals the baseline tier of 2). There is no hallucination in the agent's responses, but the agent failed to elicit the user's implicit flexibility. | deterministic candidate-set oracle: success=False, hit_ids=none.

## Limitations

Results depend on the configured simulator and judge models, the current PostgreSQL snapshot, and the selected persona subset. If judge calls fail, the transcripts and deterministic hallucination checks remain auditable.
