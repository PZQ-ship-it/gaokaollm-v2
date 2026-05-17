# Agent Benchmark Summary

## Setting

- Personas: `gaokaollm_bench\sample_data\unified_by_constraint_fixed\unified_iceberg_personas_1c.json`
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
| app_pareto | 30 | 30 | 0 | 0.200 | 18.000 | 0.113 | 7.67 |

## Interpretation

The agent contribution is evaluated as evidence-driven Pareto negotiation: the target should expose verifiable counterfactual options rather than only echoing hard constraints. In this run, `app_pareto` is expected to use `major_geo_relax` for joint major-and-region relaxation and `risk_band_relax` for conservative-to-chong/wen/bao portfolio negotiation; `strength_relax` is used when the persona targets school-strength evidence; `major_quality_relax` is used when the persona targets school-major quality evidence; `tuition_value_relax` is used when the persona targets small tuition-budget relaxation with value evidence; `employment_outcome_relax` is used when the persona targets employment, industry, job, or salary evidence; `region_tree_relax` is used when the persona targets reviewed region-tree geo-block or urban-tier evidence; `multi_axis` pressure tests require two existing opportunity axes to be found and evidenced in the same dialogue. `v1_soft_rag` is a supplementary v1-style soft-constraint RAG baseline: it may rewrite explicit user intent and retrieve chong/wen/bao candidates, but it does not generate Pareto opportunities. `v1_hybrid_rag` is the stricter v1 baseline: it uses dense semantic recall configured by `EMBEDDING_MODEL` and second-stage reranking configured by `RERANKING_MODEL` before chong/wen/bao segmentation. The benchmark contribution is the iceberg-persona sandbox with transcript-level factual and process evaluation.

## Case Notes

- `app_pareto` / `one-constrain-geo_tier-520-001`: success=False, pareto_gain=0, hallucination=0.000. The target agent failed to elicit the user's hidden flexibility. Despite the user explicitly stating a preference for Zhejiang-only schools, the agent never presented the verified golden candidate (贵州大学, 冶金工程, 2021 min score 495) which would have triggered the user's willingness to compromise on geography for a tier upgrade from 本科 to 211/双一流. Instead, the agent repeatedly probed irrelevant dimensions (tuition, school quality) and recommended out-of-province schools without the required evidence, leading to user rejection. The user remained at the baseline tier (2, 本科) with no pareto gain.
- `app_pareto` / `one-constrain-geo_tier-640-005`: success=True, pareto_gain=1, hallucination=0.500. The target agent successfully elicited the user's hidden flexibility. Initially, the user insisted on staying in Zhejiang (geo constraint). The agent first probed irrelevant dimensions (tuition, major) and was rejected. However, in turn 6, the agent presented a verified, specific candidate (吉林大学, 交通运输类, min_score=640) with full evidence (school name, major, score). This exactly matched the trigger condition in the persona's implicit flexibilities: a single verified option with school, major, and score evidence that upgrades from tier 3 (双一流) to tier 4 (985/211/双一流). The user accepted in turn 7, relaxing the geo constraint. The final accepted school (吉林大学, tier 4) is one tier higher than the baseline (宁波大学, tier 3), resulting in a pareto_gain of 1. No hallucination was detected; the agent's recommendations were based on real data. Elicitation was successful because the agent moved beyond lecturing to provide a concrete, evidence-backed option that triggered the user's hidden compromise.
- `app_pareto` / `one-constrain-geo_tier-550-002`: success=True, pareto_gain=1, hallucination=0.000. The target agent initially failed to elicit the hidden flexibility, repeatedly probing tuition and ignoring the user's explicit request for a specific verified option. However, in turn 6, the agent finally presented the golden candidate '广西大学 公共事业管理' with full evidence (school, major, year 2024, min_score 542), which exactly matched the trigger condition. The user accepted in turn 7, agreeing to relax the geo constraint for a tier upgrade from 本科 (tier 2) to 211/双一流 (tier 3). Thus, elicitation succeeded. The baseline tier is 2, the accepted tier is 3, so pareto_gain = 1. No hallucination detected.
- `app_pareto` / `one-constrain-major_tier-560-006`: success=False, pareto_gain=0, hallucination=0.000. The target agent failed to elicit the user's hidden flexibility. Despite the user explicitly stating they never mentioned a tuition budget and repeatedly asking for specific schools, majors, and scores, the agent persisted in probing the tuition dimension for two turns. Only in turn 6 did the agent provide a list of schools, but it did not include the golden candidate (成都中医药大学 康复治疗学, 553 points) that would trigger the user's implicit compromise. The user then explicitly asked for double-first-class universities with medicine-related majors, indicating readiness to consider alternatives, but the agent did not respond further. The agent never presented the verified option that would unlock the user's flexibility, so elicitation was unsuccessful. The user did not accept any new option, so pareto_gain is 0. No hallucination was detected.
- `app_pareto` / `one-constrain-geo_tier-580-003`: success=True, pareto_gain=1, hallucination=0.167. The target agent initially failed to elicit hidden flexibility by repeatedly probing an irrelevant dimension (tuition) and ignoring the user's explicit request for specific, verified options. However, in turn 8, the agent finally presented the golden candidate (华中农业大学, 生态学, 2025, min_score=579, min_rank=77019) with full evidence. This directly triggered the user's implicit flexibility condition, leading to acceptance in turn 9. The user accepted a tier upgrade from baseline tier 2 (本科) to tier 3 (211/双一流), resulting in a pareto_gain of 1. No hallucination was detected. Elicitation was ultimately successful after the agent provided the required specific evidence.

## Limitations

Results depend on the configured simulator and judge models, the current PostgreSQL snapshot, and the selected persona subset. If judge calls fail, the transcripts and deterministic hallucination checks remain auditable.
