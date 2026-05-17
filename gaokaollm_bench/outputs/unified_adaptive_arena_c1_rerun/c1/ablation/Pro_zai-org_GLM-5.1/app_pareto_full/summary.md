# Agent Benchmark Summary

## Setting

- Personas: `gaokaollm_bench\sample_data\unified_by_constraint_c1_rerun\unified_iceberg_personas_1c.json`
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
| app_pareto_full | 30 | 30 | 0 | 0.200 | 18.000 | 0.116 | 6.87 |

## Interpretation

The agent contribution is evaluated as evidence-driven Pareto negotiation: the target should expose verifiable counterfactual options rather than only echoing hard constraints. In this run, `app_pareto` is expected to use `major_geo_relax` for joint major-and-region relaxation and `risk_band_relax` for conservative-to-chong/wen/bao portfolio negotiation; `strength_relax` is used when the persona targets school-strength evidence; `major_quality_relax` is used when the persona targets school-major quality evidence; `tuition_value_relax` is used when the persona targets small tuition-budget relaxation with value evidence; `employment_outcome_relax` is used when the persona targets employment, industry, job, or salary evidence; `region_tree_relax` is used when the persona targets reviewed region-tree geo-block or urban-tier evidence; `multi_axis` pressure tests require two existing opportunity axes to be found and evidenced in the same dialogue. `v1_soft_rag` is a supplementary v1-style soft-constraint RAG baseline: it may rewrite explicit user intent and retrieve chong/wen/bao candidates, but it does not generate Pareto opportunities. `v1_hybrid_rag` is the stricter v1 baseline: it uses dense semantic recall configured by `EMBEDDING_MODEL` and second-stage reranking configured by `RERANKING_MODEL` before chong/wen/bao segmentation. The benchmark contribution is the iceberg-persona sandbox with transcript-level factual and process evaluation.

## Case Notes

- `app_pareto_full` / `one-constrain-geo_tier-640-005`: success=False, pareto_gain=0, hallucination=0.500. The target agent failed to elicit the hidden flexibility. Although it eventually recommended Jilin University (the golden school), it never presented the specific golden candidate: Jilin University, Physics major, 2025 minimum score 639, with full evidence. The user explicitly asked for Physics major data in turn 7, but the agent did not provide it within the transcript. The user remained unpursuaded and did not accept any out-of-province option. Therefore, no Pareto gain was achieved (baseline tier 3, final accepted tier still 3). No hallucination detected.
- `app_pareto_full` / `one-constrain-geo_tier-580-003`: success=True, pareto_gain=1, hallucination=0.167. The target agent successfully elicited the user's hidden flexibility. Initially, the user insisted on staying in Zhejiang (geo constraint). The agent first probed with a non-trigger candidate (河南大学), which was rejected. However, in turn 6, the agent presented the exact golden candidate (华中农业大学 生态学, 579分) with full evidence (school, major, score, year). This matched the user's implicit trigger condition exactly. The user then accepted the trade-off (relaxing geo for a tier upgrade from 本科 to 211/双一流). The final accepted school (华中农业大学) is tier 3 (211/双一流), while the baseline (浙江师范大学) is tier 2 (本科). The tier gain is +1. No hallucination was detected; all data presented was accurate and verifiable.
- `app_pareto_full` / `one-constrain-major_tier-560-006`: success=False, pareto_gain=0, hallucination=0.000. The target agent failed to elicit the user's hidden flexibility. The user explicitly hinted at considering a medical-related major like '康复治疗学' at a higher-tier school (turn 3), and the implicit flexibility required the agent to present the specific verified candidate '成都中医药大学 康复治疗学' (score 553). Instead, the agent continued probing with unrelated majors (e.g., environmental science) and eventually gave a final recommendation list that did not include the golden candidate. The user never accepted any alternative, so no pareto gain was achieved. No hallucination was detected in the transcript.
- `app_pareto_full` / `one-constrain-geo_tier-520-001`: success=False, pareto_gain=0, hallucination=0.000. The target agent failed to elicit the user's hidden flexibility. The user explicitly stated a red line of only considering Zhejiang schools, but the agent never presented the specific golden candidate (贵州大学 冶金工程, 2021, min_score=495) that would trigger a compromise. Instead, the agent repeatedly offered irrelevant out-of-province options (e.g., Jiangsu vocational schools) and generic advice, ignoring the user's repeated requests for concrete evidence. The user remained unpursuaded throughout, and no tier improvement was achieved. The agent's behavior was more like lecturing than eliciting flexibility.
- `app_pareto_full` / `one-constrain-geo_tier-630-004`: success=True, pareto_gain=1, hallucination=1.000. The target agent successfully elicited hidden flexibility by presenting a specific, verified candidate (大连理工大学(盘锦校区) 药学, 628分) that matched the user's implicit trigger condition. The user initially insisted on staying in Zhejiang (geo red line), but upon seeing the concrete evidence (school name, major, score, rank), they accepted the trade-off: relaxing geo constraint for a tier upgrade from 双一流 (tier 3) to 985/211/双一流 (tier 4). The agent did not lecture; it directly probed with a real option and asked for a decision. The user accepted, resulting in a pareto gain of 1 tier (from tier 3 to tier 4). No hallucination detected.

## Limitations

Results depend on the configured simulator and judge models, the current PostgreSQL snapshot, and the selected persona subset. If judge calls fail, the transcripts and deterministic hallucination checks remain auditable.
