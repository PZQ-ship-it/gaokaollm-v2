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
| app_pareto_full | 6 | 4 | 2 | 0.250 | 35.000 | 0.000 | 7.00 |

## Interpretation

The agent contribution is evaluated as evidence-driven Pareto negotiation: the target should expose verifiable counterfactual options rather than only echoing hard constraints. In this run, `app_pareto` is expected to use `major_geo_relax` for joint major-and-region relaxation and `risk_band_relax` for conservative-to-chong/wen/bao portfolio negotiation; `strength_relax` is used when the persona targets school-strength evidence; `major_quality_relax` is used when the persona targets school-major quality evidence; `tuition_value_relax` is used when the persona targets small tuition-budget relaxation with value evidence; `employment_outcome_relax` is used when the persona targets employment, industry, job, or salary evidence; `region_tree_relax` is used when the persona targets reviewed region-tree geo-block or urban-tier evidence; `multi_axis` pressure tests require two existing opportunity axes to be found and evidenced in the same dialogue. `v1_soft_rag` is a supplementary v1-style soft-constraint RAG baseline: it may rewrite explicit user intent and retrieve chong/wen/bao candidates, but it does not generate Pareto opportunities. `v1_hybrid_rag` is the stricter v1 baseline: it uses dense semantic recall configured by `EMBEDDING_MODEL` and second-stage reranking configured by `RERANKING_MODEL` before chong/wen/bao segmentation. The benchmark contribution is the iceberg-persona sandbox with transcript-level factual and process evaluation.

## Case Notes

- `app_pareto_full` / `micro-oracle-major_tier`: success=True, pareto_gain=140, hallucination=0.000. The target agent initially failed to elicit hidden flexibility by not providing specific evidence. However, after the user explicitly demanded concrete school, major, score, and ranking details, the agent finally presented a verified option (西藏大学, 临床医学, 570分, 位次87189) with clear advantages (211/双一流, ranking gain of 140). This triggered the user's acceptance condition, leading to the user expressing serious consideration. The final accepted school tier (3, 211/双一流) is one tier higher than the original baseline tier (2, 丽水学院), resulting in a pareto_gain of 1. No hallucination was detected. | deterministic candidate-set oracle: success=True, hit_ids=admission:16482.
- `app_pareto_full` / `micro-oracle-geo_tier` failed: APITimeoutError: Request timed out.
- `app_pareto_full` / `micro-oracle-risk_tier` failed: APITimeoutError: Request timed out.
- `app_pareto_full` / `micro-oracle-major_quality`: success=False, pareto_gain=0, hallucination=0.000. The target agent failed to elicit the user's hidden flexibility. The user explicitly stated they require a specific, verified candidate with school name, major, year, minimum score, and evidence of benefit before considering any relaxation. The agent repeatedly responded with abstract discussions about trade-offs and a reference to '西北农林科技大学' without providing the concrete evidence the user demanded. The agent had the necessary data (e.g., 中国矿业大学 with A-rated 土木工程 at 599 points) in its internal state but never presented it to the user. The user remained unpersuaded throughout the 7 turns, and no acceptance or compromise was reached. Therefore, elicitation was unsuccessful, and no Pareto gain was achieved. | deterministic candidate-set oracle: success=False, hit_ids=none.
- `app_pareto_full` / `micro-oracle-tuition_value`: success=False, pareto_gain=0, hallucination=0.000. The target agent failed to elicit hidden flexibility from the user. The user explicitly requested specific evidence (school, major, year, minimum score, rank, and tuition comparison) to consider relaxing the tuition constraint. The agent had the golden candidate (浙江中医药大学, 生物科学, 2025, 548分, 114107位, 学费5300元) in its internal state from turn 2 onward, which exactly matches the user's trigger condition. However, instead of presenting this verified option with the required evidence, the agent repeatedly deflected by discussing 'no verifiable benefit dimensions' and eventually pivoted to recommending tier 3 schools that violated the user's baseline tier preference. The agent never directly presented the acceptable candidate with tuition evidence, so the user remained unpursuaded. No pareto gain was achieved as the user did not accept any alternative. | deterministic candidate-set oracle: success=False, hit_ids=none.

## Limitations

Results depend on the configured simulator and judge models, the current PostgreSQL snapshot, and the selected persona subset. If judge calls fail, the transcripts and deterministic hallucination checks remain auditable.
