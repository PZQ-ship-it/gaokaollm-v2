# Agent Benchmark Summary

## Setting

- Personas: `gaokaollm_bench\sample_data\unified_by_constraint_fixed\unified_iceberg_personas_1c.json`
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
| app_pareto_no_tracker | 30 | 30 | 0 | 0.233 | 18.033 | 0.116 | 8.20 |

## Interpretation

The agent contribution is evaluated as evidence-driven Pareto negotiation: the target should expose verifiable counterfactual options rather than only echoing hard constraints. In this run, `app_pareto` is expected to use `major_geo_relax` for joint major-and-region relaxation and `risk_band_relax` for conservative-to-chong/wen/bao portfolio negotiation; `strength_relax` is used when the persona targets school-strength evidence; `major_quality_relax` is used when the persona targets school-major quality evidence; `tuition_value_relax` is used when the persona targets small tuition-budget relaxation with value evidence; `employment_outcome_relax` is used when the persona targets employment, industry, job, or salary evidence; `region_tree_relax` is used when the persona targets reviewed region-tree geo-block or urban-tier evidence; `multi_axis` pressure tests require two existing opportunity axes to be found and evidenced in the same dialogue. `v1_soft_rag` is a supplementary v1-style soft-constraint RAG baseline: it may rewrite explicit user intent and retrieve chong/wen/bao candidates, but it does not generate Pareto opportunities. `v1_hybrid_rag` is the stricter v1 baseline: it uses dense semantic recall configured by `EMBEDDING_MODEL` and second-stage reranking configured by `RERANKING_MODEL` before chong/wen/bao segmentation. The benchmark contribution is the iceberg-persona sandbox with transcript-level factual and process evaluation.

## Case Notes

- `app_pareto_no_tracker` / `one-constrain-geo_tier-630-004`: success=True, pareto_gain=1, hallucination=1.000. The target agent successfully elicited the user's hidden flexibility by presenting a specific, verified candidate (大连理工大学(盘锦校区) 药学, 628分) that met the trigger condition. The user initially insisted on staying in Zhejiang but, upon seeing the concrete evidence (school name, major, score, rank), agreed to consider going out of province for a tier upgrade from 双一流 (tier 3) to 985/211/双一流 (tier 4). The agent did not merely lecture; it probed with a real option and obtained acceptance. The pareto gain is 1 tier (from tier 3 to tier 4). No hallucination detected.
- `app_pareto_no_tracker` / `one-constrain-geo_tier-520-001`: success=False, pareto_gain=0, hallucination=0.000. The target agent failed to elicit the user's hidden flexibility. The user's implicit trigger condition required a specific verified candidate: 贵州大学 冶金工程 (2021, min_score=495). The agent never presented this candidate, instead offering irrelevant options (e.g., 江苏农牧科技职业学院, 南京师范大学中北学院, and a final list of out-of-province schools without the key trigger). The user repeatedly asked for concrete evidence and remained unpursuaded. No relaxation of the geo constraint occurred, so the baseline tier (2) was not improved, resulting in zero pareto gain.
- `app_pareto_no_tracker` / `one-constrain-geo_tier-640-005`: success=True, pareto_gain=1, hallucination=0.500. deterministic transcript backfill after judge/report timeout
- `app_pareto_no_tracker` / `one-constrain-major_tier-560-006`: success=False, pareto_gain=0, hallucination=0.000. The target agent failed to elicit the user's hidden flexibility. The user's implicit compromise condition was to accept '成都中医药大学 康复治疗学' (a specific, verified option with evidence) in exchange for a higher school tier (双一流). However, the agent never presented this specific candidate. Instead, it repeatedly probed with unrelated majors (e.g., 环境科学) and eventually gave up on probing the 'major' dimension, defaulting to a standard recommendation list that did not include the trigger candidate. The user remained unpersuaded and did not accept any alternative, resulting in no pareto gain (baseline tier 2, final accepted tier 2). The agent's responses were repetitive and did not adapt to the user's explicit request for a '医学相关专业' with evidence, thus failing to discover the hidden flexibility.
- `app_pareto_no_tracker` / `one-constrain-major_tier-590-008`: success=False, pareto_gain=0, hallucination=0.000. The target agent never presented the specific golden candidate (广州中医药大学 康复治疗学, 2025, min_score=590) with full evidence (school, major, year, score). Instead, it probed with unrelated options (e.g., 石河子大学 药学) and eventually fell back to recommending only clinical medicine programs, failing to trigger the user's hidden flexibility. The user explicitly requested concrete evidence multiple times but the agent did not deliver the trigger candidate. Thus, no hidden flexibility was elicited, and the user remained at the baseline tier (2) with no pareto gain.

## Limitations

Results depend on the configured simulator and judge models, the current PostgreSQL snapshot, and the selected persona subset. If judge calls fail, the transcripts and deterministic hallucination checks remain auditable.
