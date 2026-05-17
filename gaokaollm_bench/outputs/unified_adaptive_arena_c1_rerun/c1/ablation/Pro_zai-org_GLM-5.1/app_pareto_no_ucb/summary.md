# Agent Benchmark Summary

## Setting

- Personas: `gaokaollm_bench\sample_data\unified_by_constraint_c1_rerun\unified_iceberg_personas_1c.json`
- Cases: 30
- Targets: app_pareto_no_ucb
- Max turns: 6
- Simulator model: deepseek-ai/DeepSeek-V4-Flash
- Judge model: deepseek-ai/DeepSeek-V4-Flash
- Offline deterministic: False
- Default province when omitted by the user: `浙江`

## Aggregate Results

| Target | Cases | Completed | Failed | Elicitation Success | Mean Pareto Gain | Mean Hallucination | Avg Turns |
|---|---:|---:|---:|---:|---:|---:|---:|
| app_pareto_no_ucb | 30 | 30 | 0 | 0.167 | 17.967 | 0.118 | 7.80 |

## Interpretation

The agent contribution is evaluated as evidence-driven Pareto negotiation: the target should expose verifiable counterfactual options rather than only echoing hard constraints. In this run, `app_pareto` is expected to use `major_geo_relax` for joint major-and-region relaxation and `risk_band_relax` for conservative-to-chong/wen/bao portfolio negotiation; `strength_relax` is used when the persona targets school-strength evidence; `major_quality_relax` is used when the persona targets school-major quality evidence; `tuition_value_relax` is used when the persona targets small tuition-budget relaxation with value evidence; `employment_outcome_relax` is used when the persona targets employment, industry, job, or salary evidence; `region_tree_relax` is used when the persona targets reviewed region-tree geo-block or urban-tier evidence; `multi_axis` pressure tests require two existing opportunity axes to be found and evidenced in the same dialogue. `v1_soft_rag` is a supplementary v1-style soft-constraint RAG baseline: it may rewrite explicit user intent and retrieve chong/wen/bao candidates, but it does not generate Pareto opportunities. `v1_hybrid_rag` is the stricter v1 baseline: it uses dense semantic recall configured by `EMBEDDING_MODEL` and second-stage reranking configured by `RERANKING_MODEL` before chong/wen/bao segmentation. The benchmark contribution is the iceberg-persona sandbox with transcript-level factual and process evaluation.

## Case Notes

- `app_pareto_no_ucb` / `one-constrain-geo_tier-630-004`: success=False, pareto_gain=0, hallucination=0.900. The target agent failed to elicit the user's hidden flexibility. Despite the user repeatedly stating a strict preference for Zhejiang-only schools, the agent never presented the specific golden candidate (大连理工大学(盘锦校区) 药学, 628分) that would trigger the user's willingness to compromise on geography. Instead, the agent gave generic probes and recommended irrelevant out-of-province schools (including Malaysia campuses), which the user rejected. The user remained at the baseline (宁波大学, tier 3) with no acceptance of any improved option, so pareto_gain is 0. No hallucination was detected; the agent simply did not execute the correct elicitation strategy.
- `app_pareto_no_ucb` / `one-constrain-major_tier-560-006`: success=False, pareto_gain=0, hallucination=0.000. The target agent failed to elicit the user's hidden flexibility. Despite the user explicitly asking for a specific, verified candidate (成都中医药大学 康复治疗学, 553 points) that would trigger a major compromise for a higher-tier school, the agent never presented this option. Instead, it gave generic probes, random relaxation suggestions, and a final recommendation list that did not include the golden candidate. The user remained unpursuaded, and no tier improvement was accepted. The agent did not successfully elicit the hidden flexibility, so elicitation_success is false and pareto_gain is 0.
- `app_pareto_no_ucb` / `one-constrain-major_tier-590-008`: success=False, pareto_gain=0, hallucination=0.000. The target agent never elicited the hidden flexibility. Despite the user explicitly asking for a higher-tier school with a related major like rehabilitation therapy at a double-first-class university, the agent failed to present the golden candidate (广州中医药大学 康复治疗学, 590分) which would have triggered the user's compromise. Instead, the agent only recommended clinical medicine programs, including 西藏大学 (a distant location) and 杭州师范大学 (the baseline). The agent did not probe the 'major' dimension as required, and the user's final turn shows readiness to consider the golden candidate, but the agent did not seize the opportunity. Thus, elicitation_success is false, and pareto_gain remains 0 since no better option was accepted.
- `app_pareto_no_ucb` / `one-constrain-geo_tier-550-002`: success=True, pareto_gain=1, hallucination=0.000. The target agent initially failed to elicit hidden flexibility by giving vague, generic probes (turns 2, 4, 6) that the user repeatedly rejected. However, in turn 8, the agent finally presented a concrete, verified option: '广西大学 (广西/南宁市) 公共事业管理 min_score=542 min_rank=120511 tier=3 ranking=83'. This exactly matched the user's implicit trigger condition (a real, reachable candidate with school name, major, and score evidence). The user then explicitly accepted this option in turn 9, agreeing to relax the geo constraint for a tier upgrade from 本科 (tier 2) to 211/双一流 (tier 3). Thus, elicitation was successful. The baseline tier was 2 (本科), and the accepted option (广西大学) is tier 3 (211/双一流), so the pareto_gain is 1. No hallucination was detected.
- `app_pareto_no_ucb` / `one-constrain-major_tier-650-010`: success=False, pareto_gain=0, hallucination=0.000. The target agent never presented the specific golden candidate (四川大学 医学技术类, 2025, 649分) that would trigger the user's hidden flexibility. Instead, it asked generic questions and eventually recommended only clinical medicine programs (吉林大学, 兰州大学, etc.), which did not match the trigger condition. The user explicitly requested concrete evidence (school, major, score) multiple times, but the agent failed to provide the verified option that would elicit a compromise. Therefore, no hidden flexibility was elicited, and the user remained at the baseline tier 3 (宁波大学).

## Limitations

Results depend on the configured simulator and judge models, the current PostgreSQL snapshot, and the selected persona subset. If judge calls fail, the transcripts and deterministic hallucination checks remain auditable.
